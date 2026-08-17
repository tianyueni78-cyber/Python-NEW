import json
import random
import unittest
from pathlib import Path

from python_baseline.dfjspt.chromosome import Chromosome, ChromosomeError
from python_baseline.dfjspt.data import load_experiment_input
from python_baseline.dfjspt.initialization import (
    hybrid_population,
    random_population,
    tent_chaos,
)
from scripts.run_initialization import create_initialization_result
from scripts.check_gate2_initialization import check_initialization


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "python_baseline" / "data"
RESOURCE_PATH = DATA_ROOT / "resources" / "static_algorithm_comparison.json"


def load_instance(index: int):
    return load_experiment_input(
        DATA_ROOT / "brandimarte" / f"Mk{index:02d}.fjs",
        RESOURCE_PATH,
    )


class ChromosomeTests(unittest.TestCase):
    def test_matlab_speed_genes_are_interleaved_by_operation(self):
        chromosome = Chromosome(
            os=(0, 0),
            ms=(0, 1),
            agv=(1, 0),
            empty_speed=(0, 1),
            loaded_speed=(2, 3),
        )
        self.assertEqual(
            chromosome.to_matlab_row(),
            [1, 1, 1, 2, 2, 1, 1, 3, 2, 4],
        )

    def test_matlab_row_round_trip_preserves_five_segments(self):
        data = load_instance(1)
        operation_count = data.instance.operation_count
        row = (
            [job_id + 1 for job_id, count in enumerate(data.instance.operation_counts) for _ in range(count)]
            + [1] * operation_count
            + [1] * operation_count
            + [1] * operation_count
            + [1] * operation_count
        )
        chromosome = Chromosome.from_matlab_row(row, operation_count)

        self.assertEqual(chromosome.to_matlab_row(), row)
        self.assertEqual(chromosome.length, 5 * operation_count)
        chromosome.validate(data.instance, data.agv.count, speed_count=4)

    def test_rejects_wrong_os_multiplicity(self):
        data = load_instance(1)
        chromosome = Chromosome(
            os=(0,) * data.instance.operation_count,
            ms=(0,) * data.instance.operation_count,
            agv=(0,) * data.instance.operation_count,
            empty_speed=(0,) * data.instance.operation_count,
            loaded_speed=(0,) * data.instance.operation_count,
        )
        with self.assertRaises(ChromosomeError):
            chromosome.validate(data.instance, data.agv.count, speed_count=4)


class InitializationTests(unittest.TestCase):
    def test_gate2_audit_reports_complete_pass(self):
        report = check_initialization(population_size=10)
        self.assertEqual(report["结论"], "通过")
        self.assertEqual(report["Python合法实例数"], 10)
        self.assertEqual(report["MATLAB参照合法染色体数"], 10)
        self.assertTrue(report["Gate2全部通过"])
        self.assertEqual(report["Gate2尚缺"], [])

    def test_run_entry_returns_reproducible_serializable_population(self):
        first = create_initialization_result("Mk01", "hybrid", 10, 4, 77)
        second = create_initialization_result("Mk01", "hybrid", 10, 4, 77)
        self.assertEqual(first, second)
        self.assertEqual(first["chromosome_length"], 275)
        self.assertEqual(len(first["chromosomes_matlab_1_based"]), 10)

    def test_original_matlab_hybrid_rows_are_accepted_by_python_validator(self):
        data = load_instance(5)
        reference = json.loads(
            (DATA_ROOT / "matlab_reference" / "Mk05_initialization_seed_20260817.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(reference["population_size"], 10)
        self.assertEqual(reference["operation_count"], data.instance.operation_count)
        for row in reference["chromosomes"]:
            chromosome = Chromosome.from_matlab_row(row, data.instance.operation_count)
            chromosome.validate(data.instance, data.agv.count, speed_count=4)

    def test_tent_mapping_matches_matlab_recurrence_without_special_points(self):
        values = tent_chaos(3, (0.1, 0.3, 0.8), random.Random(9))
        self.assertEqual(values[0], (0.1, 0.3, 0.8))
        self.assertEqual(values[1], (0.2, 0.6, 0.3999999999999999))
        self.assertAlmostEqual(values[2][0], 0.4)
        self.assertAlmostEqual(values[2][1], 0.8)
        self.assertAlmostEqual(values[2][2], 0.8)

    def test_random_population_is_seed_reproducible_and_legal(self):
        data = load_instance(1)
        first = random_population(data, size=10, speed_count=4, rng=random.Random(17))
        second = random_population(data, size=10, speed_count=4, rng=random.Random(17))

        self.assertEqual(first, second)
        self.assertEqual(first.origins, ("random",) * 10)
        for chromosome in first.chromosomes:
            chromosome.validate(data.instance, data.agv.count, speed_count=4)

    def test_hybrid_population_has_matlab_40_30_30_groups(self):
        data = load_instance(5)
        population = hybrid_population(data, size=10, speed_count=4, rng=random.Random(23))

        self.assertEqual(
            population.origins,
            ("chaotic_random",) * 4
            + ("minimum_accumulated_time",) * 3
            + ("minimum_energy",) * 3,
        )
        for chromosome in population.chromosomes:
            chromosome.validate(data.instance, data.agv.count, speed_count=4)

    def test_hybrid_population_rejects_size_incompatible_with_matlab_ratios(self):
        data = load_instance(1)
        with self.assertRaises(ValueError):
            hybrid_population(data, size=11, speed_count=4, rng=random.Random(1))

    def test_all_paper_instances_produce_legal_hybrid_population(self):
        for index in range(1, 11):
            with self.subTest(instance=index):
                data = load_instance(index)
                population = hybrid_population(
                    data, size=10, speed_count=4, rng=random.Random(100 + index)
                )
                self.assertEqual(len(population.chromosomes), 10)
                for chromosome in population.chromosomes:
                    chromosome.validate(data.instance, data.agv.count, speed_count=4)


if __name__ == "__main__":
    unittest.main()
