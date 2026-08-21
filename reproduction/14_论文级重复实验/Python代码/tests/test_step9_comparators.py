import json
import random
import unittest
from pathlib import Path

from python_baseline.dfjspt.chromosome import Chromosome


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "python_baseline" / "data"
REFERENCE = json.loads(
    (DATA_ROOT / "matlab_reference" / "comparators_step9.json").read_text(
        encoding="utf-8"
    )
)


class MOEADMechanismTests(unittest.TestCase):
    def test_weights_and_neighbors_match_matlab_reference(self):
        from python_baseline.dfjspt.moead import generate_weights, weight_neighbors

        weights = generate_weights(5)
        self.assertEqual([list(row) for row in weights], REFERENCE["lambda"])
        actual = weight_neighbors(weights, 2)
        self.assertEqual(
            [[index + 1 for index in row] for row in actual], REFERENCE["neighbor"]
        )

    def test_reciprocal_tchebycheff_matches_matlab_reference(self):
        from python_baseline.dfjspt.moead import reciprocal_tchebycheff

        actual = [
            reciprocal_tchebycheff(
                REFERENCE["fit"], weight, REFERENCE["objective_min"]
            )
            for weight in REFERENCE["lambda"]
        ]
        for value, expected in zip(actual, REFERENCE["chebyshev"]):
            self.assertAlmostEqual(value, expected)

    def test_neighbor_replacement_matches_matlab_reference(self):
        from python_baseline.dfjspt.moead import replacement_mask

        objectives = [row[2:] for row in REFERENCE["update_neighbor_input"]]
        offspring = REFERENCE["update_neighbor_offspring"][2:]
        indices = [value - 1 for value in REFERENCE["update_neighbor_indices"]]
        mask = replacement_mask(
            objectives,
            offspring,
            indices,
            REFERENCE["lambda"],
            REFERENCE["objective_min"],
        )
        actual = [row[:] for row in REFERENCE["update_neighbor_input"]]
        for index in mask:
            actual[index] = REFERENCE["update_neighbor_offspring"][:]
        self.assertEqual(actual, REFERENCE["update_neighbor_output"])


class MOPSOMechanismTests(unittest.TestCase):
    def test_real_position_mapping_matches_matlab_reference(self):
        from python_baseline.dfjspt.mopso import real_position_to_chromosome

        ref = REFERENCE["mopso"]
        chromosome = real_position_to_chromosome(
            ref["position"],
            ref["operation_counts"],
            ref["candidate_counts"],
            ref["agv_num"],
            ref["speed_num"],
        )
        self.assertEqual(chromosome.to_matlab_row(), ref["chromosome"])

    def test_domination_flags_match_matlab_reference(self):
        from python_baseline.dfjspt.mopso import domination_flags

        ref = REFERENCE["mopso"]
        self.assertEqual(
            [int(value) for value in domination_flags(ref["dominance_objectives"])],
            ref["dominated"],
        )

    def test_fixed_local_search_preserves_continuous_dimension(self):
        from python_baseline.dfjspt.mopso import local_search_position

        position = tuple(REFERENCE["mopso"]["position"])
        for action in range(3):
            with self.subTest(action=action):
                result = local_search_position(
                    position, 5, 3, action, random.Random(30 + action)
                )
                self.assertEqual(len(result), len(position))
                self.assertNotEqual(result, position)


class ComparatorIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from python_baseline.dfjspt.data import load_experiment_input

        cls.data = load_experiment_input(
            DATA_ROOT / "brandimarte" / "Mk01.fjs",
            DATA_ROOT / "resources" / "static_algorithm_comparison.json",
        )

    def assert_legal_result(self, result):
        self.assertTrue(result.pareto_objectives)
        self.assertEqual(
            len(result.pareto_chromosomes), len(result.pareto_objectives)
        )
        self.assertGreater(result.evaluations, 0)
        for chromosome in result.pareto_chromosomes:
            self.assertIsInstance(chromosome, Chromosome)
            chromosome.validate(self.data.instance, self.data.agv.count, 4)

    def test_matlab_comparator_objective_includes_agv_energy(self):
        from python_baseline.dfjspt.decoder import decode_static
        from python_baseline.dfjspt.initialization import random_population
        from python_baseline.dfjspt.moead import _evaluate as evaluate_moead
        from python_baseline.dfjspt.nsga2 import _evaluate as evaluate_nsga2

        chromosome = random_population(
            self.data, 1, 4, random.Random(904)
        ).chromosomes[0]
        decoded = decode_static(self.data, chromosome, return_finished_jobs=True)
        expected = (decoded.makespan, decoded.machine_energy + decoded.agv_energy)
        self.assertEqual(evaluate_nsga2(self.data, chromosome), expected)
        self.assertEqual(evaluate_moead(self.data, chromosome), expected)

    def test_matlab_mopso_objective_includes_agv_energy(self):
        from python_baseline.dfjspt.decoder import decode_static
        from python_baseline.dfjspt.mopso import _evaluate

        objective, mapped = _evaluate(
            self.data, (0.0,) * (5 * self.data.instance.operation_count)
        )
        decoded = decode_static(self.data, mapped, return_finished_jobs=True)
        self.assertEqual(
            objective,
            (decoded.makespan, decoded.machine_energy + decoded.agv_energy),
        )

    def test_matlab_comparator_decoder_returns_finished_jobs_to_unload(self):
        from python_baseline.dfjspt.decoder import decode_static
        from python_baseline.dfjspt.initialization import random_population

        chromosome = random_population(
            self.data, 1, 4, random.Random(906)
        ).chromosomes[0]
        main = decode_static(self.data, chromosome)
        comparator = decode_static(
            self.data, chromosome, return_finished_jobs=True
        )
        self.assertGreater(comparator.makespan, main.makespan)
        returned_jobs = {
            block.job
            for table in comparator.agv_tables
            for block in table
            if block.opera == -1 and block.load_status == -2 and block.to_machine == -2
        }
        self.assertEqual(returned_jobs, set(range(1, self.data.instance.job_count + 1)))

    def test_nsga2_small_run_is_reproducible_and_legal(self):
        from python_baseline.dfjspt.nsga2 import run_nsga2

        first = run_nsga2(self.data, population_size=10, generations=2, seed=901)
        second = run_nsga2(self.data, population_size=10, generations=2, seed=901)
        self.assertEqual(first, second)
        self.assert_legal_result(first)

    def test_moead_small_run_is_reproducible_and_legal(self):
        from python_baseline.dfjspt.moead import run_moead

        first = run_moead(self.data, population_size=20, generations=1, seed=902)
        second = run_moead(self.data, population_size=20, generations=1, seed=902)
        self.assertEqual(first, second)
        self.assert_legal_result(first)

    def test_mopso_small_run_is_reproducible_and_legal(self):
        from python_baseline.dfjspt.mopso import run_mopso

        first = run_mopso(self.data, population_size=6, generations=1, seed=903)
        second = run_mopso(self.data, population_size=6, generations=1, seed=903)
        self.assertEqual(first, second)
        self.assert_legal_result(first)

    def test_three_algorithms_have_independent_result_types(self):
        from python_baseline.dfjspt.moead import MOEADResult
        from python_baseline.dfjspt.mopso import MOPSOResult
        from python_baseline.dfjspt.nsga2 import NSGA2Result

        self.assertEqual(len({NSGA2Result, MOEADResult, MOPSOResult}), 3)

    def test_step9_audit_reports_three_independent_passes(self):
        from scripts.check_step9 import check_step9

        report = check_step9()
        self.assertEqual(report["结论"], "通过")
        self.assertEqual(report["独立入口"], ["NSGA-II", "MOEA/D", "MOPSO"])
        self.assertTrue(report["MATLAB固定机制一致"])
        self.assertTrue(report["MATLAB目录目标已保留"])


if __name__ == "__main__":
    unittest.main()
