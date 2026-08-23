import json
import math
import random
import subprocess
import sys
import unittest
from pathlib import Path

from python_baseline.dfjspt.multiobjective import (
    dominates,
    environmental_select,
    matlab_order,
    pareto_indices,
    rank_and_crowding,
    tournament_selection,
    tournament_winner,
)
from python_baseline.dfjspt.chromosome import Chromosome
from python_baseline.dfjspt.data import load_experiment_input
from python_baseline.dfjspt.genetic import matlab_crossover, matlab_mutation, variation


REFERENCE_PATH = (
    Path(__file__).resolve().parents[1]
    / "python_baseline"
    / "data"
    / "matlab_reference"
    / "multiobjective_step7.json"
)


def restore_infinity(values, infinite):
    return [
        [math.inf if marker else value for value, marker in zip(row, mask)]
        for row, mask in zip(values, infinite)
    ]


class MultiobjectiveParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
        cls.objectives = cls.reference["objectives"]

    def assertRowsEqual(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        for actual_row, expected_row in zip(actual, expected):
            self.assertEqual(actual_row[:3], expected_row[:3])
            if math.isinf(expected_row[3]):
                self.assertTrue(math.isinf(actual_row[3]))
            else:
                self.assertAlmostEqual(actual_row[3], expected_row[3], places=12)

    def test_dominance_is_strict_pareto_minimization(self):
        self.assertTrue(dominates((1, 2), (1, 3)))
        self.assertFalse(dominates((1, 2), (1, 2)))
        self.assertFalse(dominates((1, 3), (2, 2)))

    def test_qnsga_and_nsga_intermediate_orders_match_matlab(self):
        qnsga_expected = restore_infinity(
            self.reference["qnsga_sorted"],
            self.reference["qnsga_sorted_infinite"],
        )
        nsga_expected = restore_infinity(
            self.reference["nsga_ranked"],
            self.reference["nsga_ranked_infinite"],
        )
        self.assertRowsEqual(matlab_order(self.objectives, True), qnsga_expected)
        self.assertRowsEqual(matlab_order(self.objectives, False), nsga_expected)

    def test_rank_and_crowding_preserve_input_alignment(self):
        ranks, crowding = rank_and_crowding(self.objectives)
        keyed = {}
        for row in matlab_order(self.objectives, False):
            keyed.setdefault(tuple(row[:2]), []).append(row[2:])
        for objective, rank, distance in zip(self.objectives, ranks, crowding):
            expected_rank, expected_distance = keyed[tuple(objective)].pop(0)
            self.assertEqual(rank, expected_rank)
            if math.isinf(expected_distance):
                self.assertTrue(math.isinf(distance))
            else:
                self.assertAlmostEqual(distance, expected_distance, places=12)

    def test_environmental_selection_matches_both_matlab_paths(self):
        selected = environmental_select(
            self.objectives, self.reference["population_size"]
        )
        selected_rows = [self.objectives[index] for index in selected]
        expected = [row[:2] for row in self.reference["qnsga_elite"]]
        self.assertEqual(selected_rows, expected)
        self.assertEqual(
            sorted(selected_rows),
            sorted(row[:2] for row in self.reference["nsga_elite"]),
        )

    def test_fixed_candidate_tournaments_match_matlab(self):
        ordered = matlab_order(self.objectives, True)
        ranks = [row[2] for row in ordered]
        crowding = [row[3] for row in ordered]
        actual = [
            tournament_winner(
                ranks, crowding, [candidate - 1 for candidate in pair]
            )
            + 1
            for pair in self.reference["candidate_pairs"]
        ]
        self.assertEqual(
            actual, self.reference["tournament_winners_matlab_1_based"]
        )

    def test_tournament_selection_is_seed_reproducible(self):
        ranks, crowding = rank_and_crowding(self.objectives)
        first = tournament_selection(
            ranks, crowding, 5, 2, random.Random(20260817)
        )
        second = tournament_selection(
            ranks, crowding, 5, 2, random.Random(20260817)
        )
        self.assertEqual(first, second)
        self.assertEqual(len(first), 5)

    def test_pareto_filter_keeps_duplicates_like_matlab(self):
        self.assertEqual(pareto_indices(self.objectives), [0, 1, 2, 3, 4, 7])

    def test_constant_objective_front_gets_infinite_crowding(self):
        ranks, crowding = rank_and_crowding([[2, 2], [2, 2], [2, 2]])
        self.assertEqual(ranks, [1, 1, 1])
        self.assertTrue(all(math.isinf(value) for value in crowding))

    def test_rejects_invalid_input_and_population_size(self):
        with self.assertRaises(ValueError):
            rank_and_crowding([])
        with self.assertRaises(ValueError):
            rank_and_crowding([[1, math.inf]])
        with self.assertRaises(ValueError):
            environmental_select([[1, 2]], 2)

    def test_gate4_audit_reports_matlab_parity(self):
        from scripts.check_gate4 import check_gate4

        report = check_gate4()
        self.assertEqual(report["结论"], "通过")
        self.assertTrue(report["非支配等级一致"])
        self.assertTrue(report["拥挤距离一致"])
        self.assertTrue(report["精英保留一致"])
        self.assertTrue(report["锦标赛判优一致"])
        self.assertTrue(report["固定交叉一致"])
        self.assertTrue(report["固定变异一致"])


class SharedGeneticOperatorParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
        data_root = REFERENCE_PATH.parents[1]
        cls.data = load_experiment_input(
            data_root / "brandimarte" / "Mk05.fjs",
            data_root / "resources" / "static_algorithm_comparison.json",
        )
        operation_count = cls.data.instance.operation_count
        cls.parents = [
            Chromosome.from_matlab_row(row, operation_count)
            for row in cls.reference["genetic_parent_rows"]
        ]

    def test_fixed_ipox_mpx_crossover_matches_matlab(self):
        children = matlab_crossover(
            self.parents[0],
            self.parents[1],
            {job - 1 for job in self.reference["selected_jobs_matlab_1_based"]},
            [
                position - 1
                for position in self.reference[
                    "selected_rs_positions_matlab_1_based"
                ]
            ],
        )
        self.assertEqual(
            [child.to_matlab_row() for child in children],
            self.reference["crossover_children"],
        )
        for child in children:
            child.validate(self.data.instance, self.data.agv.count, 4)

    def test_fixed_swap_and_rs_reset_mutation_matches_matlab(self):
        child = Chromosome.from_matlab_row(
            self.reference["crossover_children"][0],
            self.data.instance.operation_count,
        )
        mutated = matlab_mutation(
            child,
            tuple(
                position - 1
                for position in self.reference[
                    "mutation_os_positions_matlab_1_based"
                ]
            ),
            {
                position - 1: value - 1
                for position, value in zip(
                    self.reference["mutation_rs_positions_matlab_1_based"],
                    self.reference["mutation_rs_values_matlab_1_based"],
                )
            },
        )
        self.assertEqual(mutated.to_matlab_row(), self.reference["mutated_child"])
        mutated.validate(self.data.instance, self.data.agv.count, 4)

    def test_crossover_and_mutation_reject_invalid_fixed_choices(self):
        with self.assertRaises(ValueError):
            matlab_crossover(self.parents[0], self.parents[1], set(), [])
        with self.assertRaises(ValueError):
            matlab_mutation(self.parents[0], (0, 0), {})

    def test_random_variation_is_reproducible_and_legal(self):
        population = variation(
            self.parents,
            0.8,
            0.1,
            self.data.instance,
            self.data.agv.count,
            4,
            random.Random(20260817),
        )
        repeated = variation(
            self.parents,
            0.8,
            0.1,
            self.data.instance,
            self.data.agv.count,
            4,
            random.Random(20260817),
        )
        self.assertEqual(population, repeated)
        self.assertGreaterEqual(len(population), len(self.parents))
        self.assertLessEqual(len(population), 2 * len(self.parents))
        for chromosome in population:
            chromosome.validate(self.data.instance, self.data.agv.count, 4)

    def test_variation_terminates_when_every_parent_is_identical(self):
        code = f"""
import json, random
from pathlib import Path
from python_baseline.dfjspt.chromosome import Chromosome
from python_baseline.dfjspt.data import load_experiment_input
from python_baseline.dfjspt.genetic import variation
root = Path({str(REFERENCE_PATH.parents[1])!r})
reference = json.loads((root / 'matlab_reference' / 'multiobjective_step7.json').read_text('utf-8'))
data = load_experiment_input(root / 'brandimarte' / 'Mk05.fjs', root / 'resources' / 'static_algorithm_comparison.json')
parent = Chromosome.from_matlab_row(reference['genetic_parent_rows'][0], data.instance.operation_count)
result = variation((parent, parent), 1.0, 0.0, data.instance, data.agv.count, 4, random.Random(7))
assert result == (parent, parent)
"""
        try:
            completed = subprocess.run(
                [sys.executable, "-c", code], text=True, capture_output=True,
                timeout=2,
            )
        except subprocess.TimeoutExpired:
            self.fail("全部父代相同时variation进入非终止选父代循环")
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
