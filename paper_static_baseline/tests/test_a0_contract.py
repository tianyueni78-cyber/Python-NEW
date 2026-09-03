import json
import math
import random
import unittest
from collections import Counter
from pathlib import Path

from paper_static_baseline.dfjspt.chromosome import Chromosome
from paper_static_baseline.dfjspt.data import load_experiment_input
from paper_static_baseline.dfjspt.decoder import decode_static, validate_schedule
from paper_static_baseline.dfjspt.initialization import hybrid_population
from paper_static_baseline.dfjspt.multiobjective import environmental_select, rank_and_crowding
from paper_static_baseline.dfjspt.neighborhoods import apply_neighborhood
from paper_static_baseline.dfjspt.objectives import evaluate_objectives
from paper_static_baseline.dfjspt.qlearning import (
    assign_states,
    epsilon,
    reward_value,
    select_action,
    update_q,
)
from paper_static_baseline.dfjspt.qnsga2 import run_qnsga2


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESOURCE = DATA / "resources" / "static_algorithm_comparison.json"


def load_data(name):
    return load_experiment_input(DATA / "brandimarte" / f"{name}.fjs", RESOURCE)


class A0ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data("Mk05")
        cls.decoder_reference = json.loads(
            (DATA / "matlab_reference" / "Mk05_decoder_reference.json").read_text(encoding="utf-8")
        )
        cls.q_reference = json.loads(
            (DATA / "matlab_reference" / "qnsga_step8.json").read_text(encoding="utf-8")
        )
        cls.chromosome = Chromosome.from_matlab_row(
            cls.decoder_reference["chromosome_matlab_1_based"],
            cls.data.instance.operation_count,
        )

    def test_hybrid_population_is_40_30_30_and_five_blocks(self):
        population = hybrid_population(self.data, 10, 4, random.Random(20260817))
        self.assertEqual(
            Counter(population.origins),
            {"chaotic_random": 4, "minimum_accumulated_time": 3, "minimum_energy": 3},
        )
        for chromosome in population.chromosomes:
            self.assertEqual(chromosome.length, 5 * self.data.instance.operation_count)
            chromosome.validate(self.data.instance, self.data.agv.count, 4)

    def test_fixed_chromosome_matches_matlab_schedule_and_objectives(self):
        result = decode_static(self.data, self.chromosome, speeds=(1.0,) * 4)
        validate_schedule(self.data, self.chromosome, result)
        self.assertAlmostEqual(result.makespan, self.decoder_reference["makespan"], places=9)
        self.assertAlmostEqual(result.machine_energy, self.decoder_reference["machine_energy"], places=9)
        self.assertEqual(evaluate_objectives(result), (result.makespan, result.machine_energy))
        self.assertEqual(list(result.charge_counts), self.decoder_reference["charge_counts"])
        actual = result.to_matlab_dict()
        self.assertEqual(actual["machine_tables"], self.decoder_reference["machine_tables"])
        self.assertEqual(actual["agv_tables"], self.decoder_reference["agv_tables"])
        self.assertEqual(actual["battery_records"], self.decoder_reference["battery_records"])

    def test_qlearning_rules_match_fixed_matlab_reference(self):
        states, time_median, energy_median = assign_states(self.q_reference["state_objectives"])
        self.assertEqual(states, [value - 1 for value in self.q_reference["states"]])
        self.assertEqual((time_median, energy_median), (self.q_reference["time_median"], self.q_reference["energy_median"]))
        rewards = [
            reward_value(self.q_reference["reward_old_objective"], new, self.q_reference["reward_maximum"], self.q_reference["reward_minimum"])
            for new in self.q_reference["reward_new_objectives"]
        ]
        self.assertEqual(rewards, self.q_reference["rewards"])
        qtable = [[0.0] * 6 for _ in range(4)]
        qtable[1] = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        update_q(qtable, 0, 2, rewards[0], 1, 0.1, 0.9)
        self.assertEqual(qtable, self.q_reference["updated_qtable"])

    def test_epsilon_and_action_selection_follow_active_code(self):
        self.assertAlmostEqual(epsilon(0, 200), 1 / (1 + math.exp(2.96)))
        zero = [[0.0] * 6 for _ in range(4)]
        self.assertIn(select_action(zero, 3, 1.0, random.Random(4)), range(6))
        qtable = [[0.0] * 6 for _ in range(4)]
        qtable[0] = [0, 1, 2, 5, 3, 4]
        self.assertEqual(select_action(qtable, 0, 1.0, random.Random(4)), 3)

    def test_each_neighborhood_preserves_legality(self):
        parent = Chromosome.from_matlab_row(
            self.q_reference["chromosome"], self.data.instance.operation_count
        )
        for action in range(6):
            with self.subTest(action=action + 1):
                neighbor = apply_neighborhood(self.data, parent, action, random.Random(700 + action))
                neighbor.validate(self.data.instance, self.data.agv.count, 4)

    def test_multiobjective_ranking_and_selection_are_fixed(self):
        objectives = [(1, 4), (2, 3), (3, 2), (4, 1), (4, 4)]
        ranks, crowding = rank_and_crowding(objectives)
        self.assertEqual(ranks, [1, 1, 1, 1, 2])
        self.assertTrue(math.isinf(crowding[0]))
        self.assertTrue(math.isinf(crowding[3]))
        self.assertEqual(len(environmental_select(objectives, 3)), 3)

    def test_fixed_seed_complete_run_is_reproducible_and_updates_qtable(self):
        data = load_data("Mk01")
        first = run_qnsga2(data, population_size=10, generations=2, seed=20260817)
        second = run_qnsga2(data, population_size=10, generations=2, seed=20260817)
        self.assertEqual(first, second)
        self.assertTrue(first.pareto_objectives)
        self.assertTrue(any(value != 0 for row in first.qtable for value in row))
        self.assertGreater(first.evaluations, 10)


if __name__ == "__main__":
    unittest.main()
