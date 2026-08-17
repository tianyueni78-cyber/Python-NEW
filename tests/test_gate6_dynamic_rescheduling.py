import json
import random
import unittest
from pathlib import Path

from python_baseline.dfjspt.chromosome import Chromosome
from python_baseline.dfjspt.data import load_dynamic_experiment_input, load_experiment_input
from python_baseline.dfjspt.decoder import decode_static
from python_baseline.dfjspt.initialization import hybrid_population
from python_baseline.dfjspt.dynamic import (
    DynamicEvent,
    analyze_event,
    build_rescheduling_plan,
    execute_is,
    execute_rescheduling,
    validate_dynamic_schedule,
)


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "python_baseline" / "data"


class DynamicReschedulingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_experiment_input(
            DATA / "brandimarte" / "Mk05.fjs",
            DATA / "resources" / "static_algorithm_comparison.json",
        )
        ref = json.loads(
            (DATA / "matlab_reference" / "Mk05_decoder_reference.json").read_text("utf-8")
        )
        cls.chromosome = Chromosome.from_matlab_row(
            ref["chromosome_matlab_1_based"], cls.data.instance.operation_count
        )
        cls.schedule = decode_static(cls.data, cls.chromosome, speeds=(1, 1, 1, 1))

    def test_state_inherits_completed_operations_and_resource_state(self):
        state = analyze_event(self.schedule, DynamicEvent("machine_failure", 100.0, 3, 20.0))
        reference = json.loads(
            (DATA / "matlab_reference" / "dynamic_step11.json").read_text("utf-8")
        )
        self.assertEqual(len(state.completed_operations), reference["completed_operations"])
        self.assertEqual(len(state.in_process_operations), reference["in_process_operations"])
        self.assertEqual(len(state.remaining_operations), reference["remaining_operations"])
        self.assertTrue(state.completed_operations)
        self.assertTrue(state.remaining_operations)
        self.assertEqual(len(state.agv_locations), self.data.agv.count)
        self.assertEqual(len(state.agv_battery), self.data.agv.count)
        self.assertEqual(state.unavailable_interval, (100.0, 120.0))

    def test_three_active_event_chains_keep_independent_resource_profiles(self):
        profile = DATA / "resources" / "dynamic_event_profiles.json"
        base = DATA / "resources" / "static_algorithm_comparison.json"
        expected = {
            "order_cancellation": ((1.0, 1.0, 1.0), 16.8, 4.2, 2.0),
            "machine_failure": ((90.0,), 3.6, 8.2, 20.0),
            "agv_failure": ((900.0, 900.0, 900.0), 0.63, 8.2, 20.0),
        }
        for kind, values in expected.items():
            data = load_dynamic_experiment_input(
                DATA / "brandimarte" / "Mk01.fjs", base, profile, kind
            )
            self.assertEqual(data.agv.speeds, values[0])
            self.assertEqual(data.agv.minimum_energy, values[1])
            self.assertEqual(data.resources.machine_work_energy[0], values[2])
            self.assertEqual(data.resources.load_to_machine[0], values[3])

    def test_machine_failure_single_speed_uses_90_for_charging_return(self):
        data = load_dynamic_experiment_input(
            DATA / "brandimarte" / "Mk01.fjs",
            DATA / "resources" / "static_algorithm_comparison.json",
            DATA / "resources" / "dynamic_event_profiles.json",
            "machine_failure",
        )
        chromosome = hybrid_population(data, 10, 1, random.Random(7)).chromosomes[0]
        schedule = decode_static(data, chromosome)
        self.assertGreater(schedule.makespan, 0.0)
        self.assertEqual(data.agv.speeds, (90.0,))
        self.assertEqual(data.agv.charging_travel_speed, 90.0)

    def test_completed_operations_remain_fixed_and_failure_interval_is_respected(self):
        event = DynamicEvent("machine_failure", 100.0, 3, 20.0)
        result = execute_is(self.data, self.chromosome, self.schedule, event)
        validate_dynamic_schedule(self.data, self.chromosome, self.schedule, result, event)
        before = {
            (b.job, b.opera): (b.start, b.end)
            for table in self.schedule.machine_tables for b in table
            if b.job and b.end <= event.time
        }
        after = {
            (b.job, b.opera): (b.start, b.end)
            for table in result.machine_tables for b in table if b.job
        }
        for key, interval in before.items():
            self.assertEqual(after[key], interval)

    def test_machine_failure_splits_and_resumes_in_process_operation(self):
        machine_index, block = next(
            (index, block)
            for index, table in enumerate(self.schedule.machine_tables)
            for block in table
            if block.job and block.end - block.start > 2.0
        )
        moment = (block.start + block.end) / 2
        duration = 5.0
        event = DynamicEvent("machine_failure", moment, machine_index + 1, duration)
        result = execute_rescheduling(
            self.data, self.chromosome, self.schedule, event, "RS",
            population_size=10, generations=1, seed=17,
        )
        pieces = [
            piece for piece in result.pareto_schedules[0].machine_tables[machine_index]
            if (piece.job, piece.opera) == (block.job, block.opera)
        ]
        self.assertEqual(len(pieces), 2)
        self.assertEqual(pieces[0].end, moment)
        self.assertEqual(pieces[1].start, moment + duration)

    def test_order_cancellation_removes_every_operation_of_cancelled_job(self):
        event = DynamicEvent("order_cancellation", 100.0, 4, 0.0)
        result = execute_is(self.data, self.chromosome, self.schedule, event)
        self.assertFalse(any(b.job == 4 for t in result.machine_tables for b in t))
        validate_dynamic_schedule(self.data, self.chromosome, self.schedule, result, event)

    def test_agv_failure_inherits_location_and_battery_and_delays_future_work(self):
        event = DynamicEvent("agv_failure", 100.0, 1, 15.0)
        state = analyze_event(self.schedule, event)
        result = execute_is(self.data, self.chromosome, self.schedule, event)
        self.assertIsInstance(state.agv_locations[0], int)
        self.assertGreaterEqual(state.agv_battery[0], -200.0)
        self.assertGreater(result.makespan, self.schedule.makespan)
        validate_dynamic_schedule(self.data, self.chromosome, self.schedule, result, event)

    def test_is_rs_cs_have_distinct_matlab_constraints(self):
        cases = [
            DynamicEvent("order_cancellation", 100.0, 4, 0.0),
            DynamicEvent("machine_failure", 100.0, 3, 20.0),
            DynamicEvent("agv_failure", 100.0, 1, 15.0),
        ]
        for event in cases:
            plans = [build_rescheduling_plan(self.schedule, self.chromosome, event, s)
                     for s in ("IS", "RS", "CS")]
            self.assertEqual(len({p.signature for p in plans}), 3)
            self.assertFalse(plans[0].mutable_segments)
            self.assertEqual(plans[2].mutable_segments, frozenset({"OS", "MS", "AS", "VS"}))
        machine_rs = build_rescheduling_plan(
            self.schedule, self.chromosome, cases[1], "RS"
        )
        agv_rs = build_rescheduling_plan(
            self.schedule, self.chromosome, cases[2], "RS"
        )
        self.assertIn("MS_FAULT_ONLY", machine_rs.mutable_segments)
        self.assertNotIn("MS", agv_rs.mutable_segments)

    def test_rs_and_cs_return_actual_pareto_schedules(self):
        events = (
            DynamicEvent("order_cancellation", 100.0, 4),
            DynamicEvent("machine_failure", 100.0, 3, 20.0),
            DynamicEvent("agv_failure", 100.0, 1, 15.0),
        )
        for event in events:
            for strategy in ("RS", "CS"):
                result = execute_rescheduling(
                    self.data,
                    self.chromosome,
                    self.schedule,
                    event,
                    strategy,
                    population_size=10,
                    generations=1,
                    seed=20260817,
                )
                self.assertTrue(result.pareto_objectives)
                self.assertEqual(len(result.pareto_objectives), len(result.pareto_schedules))
                self.assertTrue(any(value != 0.0 for row in result.qtable for value in row))
                for candidate in result.pareto_schedules:
                    validate_dynamic_schedule(
                        self.data, self.chromosome, self.schedule, candidate, event
                    )


if __name__ == "__main__":
    unittest.main()
