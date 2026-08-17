import json
import random
import unittest
from pathlib import Path

from python_baseline.dfjspt.chromosome import Chromosome
from python_baseline.dfjspt.data import load_experiment_input
from python_baseline.dfjspt.decoder import decode_static, validate_schedule
from python_baseline.dfjspt.initialization import hybrid_population


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "python_baseline" / "data"
RESOURCE_PATH = DATA_ROOT / "resources" / "static_algorithm_comparison.json"


def load_data(name: str):
    return load_experiment_input(
        DATA_ROOT / "brandimarte" / f"{name}.fjs", RESOURCE_PATH
    )


class DecoderParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_data("Mk05")
        cls.reference = json.loads(
            (DATA_ROOT / "matlab_reference" / "Mk05_decoder_reference.json").read_text(
                encoding="utf-8"
            )
        )
        cls.chromosome = Chromosome.from_matlab_row(
            cls.reference["chromosome_matlab_1_based"],
            cls.data.instance.operation_count,
        )
        cls.result = decode_static(cls.data, cls.chromosome, speeds=(1.0, 1.0, 1.0, 1.0))

    def assertNestedAlmostEqual(self, actual, expected, places=9):
        if isinstance(expected, dict):
            self.assertEqual(actual.keys(), expected.keys())
            for key in expected:
                self.assertNestedAlmostEqual(actual[key], expected[key], places)
        elif isinstance(expected, list):
            self.assertEqual(len(actual), len(expected))
            for left, right in zip(actual, expected):
                self.assertNestedAlmostEqual(left, right, places)
        elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
            self.assertAlmostEqual(actual, expected, places=places)
        else:
            self.assertEqual(actual, expected)

    def test_fixed_chromosome_objectives_match_matlab(self):
        self.assertAlmostEqual(self.result.makespan, self.reference["makespan"], places=9)
        self.assertAlmostEqual(
            self.result.machine_energy, self.reference["machine_energy"], places=9
        )
        self.assertAlmostEqual(self.result.agv_energy, self.reference["agv_energy"], places=9)
        self.assertNestedAlmostEqual(
            list(self.result.job_completion), self.reference["job_completion"]
        )
        self.assertEqual(list(self.result.charge_counts), self.reference["charge_counts"])

    def test_fixed_chromosome_machine_and_agv_tables_match_matlab(self):
        actual = self.result.to_matlab_dict()
        self.assertNestedAlmostEqual(actual["machine_tables"], self.reference["machine_tables"])
        self.assertNestedAlmostEqual(actual["agv_tables"], self.reference["agv_tables"])
        self.assertNestedAlmostEqual(actual["battery_records"], self.reference["battery_records"])

    def test_fixed_chromosome_schedule_is_feasible(self):
        validate_schedule(self.data, self.chromosome, self.result)

    def test_all_instances_decode_a_legal_hybrid_chromosome(self):
        for index in range(1, 11):
            with self.subTest(instance=index):
                data = load_data(f"Mk{index:02d}")
                chromosome = hybrid_population(
                    data, 10, 4, random.Random(3000 + index)
                ).chromosomes[0]
                result = decode_static(data, chromosome, speeds=(1.0, 1.0, 1.0, 1.0))
                validate_schedule(data, chromosome, result)


if __name__ == "__main__":
    unittest.main()
