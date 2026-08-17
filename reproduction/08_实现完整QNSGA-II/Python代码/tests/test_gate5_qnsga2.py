import json
import math
import random
import unittest
from pathlib import Path

from python_baseline.dfjspt.chromosome import Chromosome
from python_baseline.dfjspt.data import load_experiment_input
from python_baseline.dfjspt.neighborhoods import (
    apply_neighborhood,
    n1_reinsert_reversed_pair,
    n2_remove_and_reinsert,
    replace_agv_gene,
    replace_machine_gene,
    n6_waiting_agv_reassignment,
)
from python_baseline.dfjspt.qnsga2 import run_qnsga2
from python_baseline.dfjspt.qlearning import (
    assign_states,
    epsilon,
    reward_value,
    select_action,
    update_q,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "python_baseline" / "data"
REFERENCE = json.loads(
    (DATA_ROOT / "matlab_reference" / "qnsga_step8.json").read_text(encoding="utf-8")
)


class NeighborhoodParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_experiment_input(
            DATA_ROOT / "brandimarte" / "Mk05.fjs",
            DATA_ROOT / "resources" / "static_algorithm_comparison.json",
        )
        cls.parent = Chromosome.from_matlab_row(
            REFERENCE["chromosome"], cls.data.instance.operation_count
        )
        cls.expected = {
            item["strategy"]: item for item in REFERENCE["neighborhoods"]
        }

    def assertLegalMatch(self, actual, strategy):
        actual.validate(self.data.instance, self.data.agv.count, 4)
        self.assertEqual(actual.to_matlab_row(), self.expected[strategy]["chromosome"])

    def test_n1_fixed_reversed_pair_reinsertion_matches_matlab(self):
        self.assertLegalMatch(n1_reinsert_reversed_pair(self.parent, 96, 91), "N1")

    def test_n2_fixed_removal_reinsertion_matches_matlab(self):
        self.assertLegalMatch(n2_remove_and_reinsert(self.parent, (59, 35), 81), "N2")

    def test_n3_fixed_machine_change_matches_matlab(self):
        self.assertLegalMatch(replace_machine_gene(self.parent, 93, 1), "N3")

    def test_n4_fixed_load_based_machine_change_matches_matlab(self):
        self.assertLegalMatch(replace_machine_gene(self.parent, 9, 0), "N4")

    def test_n5_fixed_agv_change_matches_matlab(self):
        self.assertLegalMatch(replace_agv_gene(self.parent, 103, 3), "N5")

    def test_n6_waiting_interval_reassignment_matches_matlab(self):
        self.assertLegalMatch(
            n6_waiting_agv_reassignment(self.data, self.parent, random.Random(1)),
            "N6",
        )

    def test_all_random_neighborhoods_keep_chromosome_legal(self):
        for action in range(6):
            with self.subTest(action=action + 1):
                result = apply_neighborhood(
                    self.data, self.parent, action, random.Random(700 + action)
                )
                result.validate(self.data.instance, self.data.agv.count, 4)

    def test_n3_tenth_attempt_preserves_matlab_no_change_behavior(self):
        class FixedRng:
            def __init__(self):
                self.values = iter([0, 3] * 9 + [0, 0])

            def randrange(self, _stop):
                return next(self.values, 1)

        result = apply_neighborhood(self.data, self.parent, 2, FixedRng())
        self.assertEqual(result, self.parent)

    def test_all_instances_and_neighborhoods_keep_chromosome_legal(self):
        from python_baseline.dfjspt.initialization import hybrid_population

        for instance_index in range(1, 11):
            data = load_experiment_input(
                DATA_ROOT / "brandimarte" / f"Mk{instance_index:02d}.fjs",
                DATA_ROOT / "resources" / "static_algorithm_comparison.json",
            )
            parent = hybrid_population(
                data, 10, 4, random.Random(8000 + instance_index)
            ).chromosomes[0]
            for action in range(6):
                with self.subTest(instance=instance_index, action=action + 1):
                    result = apply_neighborhood(
                        data, parent, action, random.Random(9000 + action)
                    )
                    result.validate(data.instance, data.agv.count, 4)


class QLearningParityTests(unittest.TestCase):
    def test_state_partition_matches_matlab_medians_and_boundaries(self):
        states, time_median, energy_median = assign_states(
            REFERENCE["state_objectives"]
        )
        self.assertEqual(states, [value - 1 for value in REFERENCE["states"]])
        self.assertEqual(time_median, REFERENCE["time_median"])
        self.assertEqual(energy_median, REFERENCE["energy_median"])

    def test_reward_three_branches_match_matlab(self):
        actual = [
            reward_value(
                REFERENCE["reward_old_objective"],
                new,
                REFERENCE["reward_maximum"],
                REFERENCE["reward_minimum"],
            )
            for new in REFERENCE["reward_new_objectives"]
        ]
        self.assertEqual(actual, REFERENCE["rewards"])

    def test_q_update_matches_matlab(self):
        q = [[0.0] * 6 for _ in range(4)]
        q[1] = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        update_q(q, 0, 2, REFERENCE["rewards"][0], 1, 0.1, 0.9)
        self.assertEqual(q, REFERENCE["updated_qtable"])

    def test_epsilon_and_action_rule_follow_active_matlab_code(self):
        self.assertAlmostEqual(epsilon(0, 200), 1 / (1 + math.exp(2.96)))
        zero_q = [[0.0] * 6 for _ in range(4)]
        self.assertIn(select_action(zero_q, 3, 1.0, random.Random(4)), range(6))
        q = [[0.0] * 6 for _ in range(4)]
        q[0] = [0, 1, 2, 5, 3, 4]
        self.assertEqual(select_action(q, 0, 1.0, random.Random(4)), 3)


class QNSGA2IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_experiment_input(
            DATA_ROOT / "brandimarte" / "Mk01.fjs",
            DATA_ROOT / "resources" / "static_algorithm_comparison.json",
        )

    def test_small_complete_run_is_reproducible_and_updates_qtable(self):
        first = run_qnsga2(
            self.data, population_size=10, generations=2, seed=20260817
        )
        second = run_qnsga2(
            self.data, population_size=10, generations=2, seed=20260817
        )
        self.assertEqual(first, second)
        self.assertTrue(first.pareto_objectives)
        self.assertTrue(any(value != 0 for row in first.qtable for value in row))
        self.assertEqual(len(first.curve_min), 2)
        for chromosome in first.pareto_chromosomes:
            chromosome.validate(self.data.instance, self.data.agv.count, 4)

    def test_gate5_audit_reports_pass(self):
        from scripts.check_gate5 import check_gate5

        report = check_gate5()
        self.assertEqual(report["结论"], "通过")
        self.assertTrue(report["N1-N6固定参考一致"])
        self.assertTrue(report["Q表已更新"])


if __name__ == "__main__":
    unittest.main()
