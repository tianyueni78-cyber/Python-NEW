import json
import unittest
from pathlib import Path

from python_baseline.dfjspt.chromosome import Chromosome
from python_baseline.dfjspt.data import load_experiment_input
from python_baseline.dfjspt.decoder import decode_static
from python_baseline.dfjspt.dynamic import (
    DynamicEvent,
    analyze_event,
    build_rescheduling_plan,
    execute_is,
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


if __name__ == "__main__":
    unittest.main()
