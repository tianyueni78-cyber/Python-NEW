import json
import unittest
from pathlib import Path

from python_baseline.dfjspt.data import (
    DataFormatError,
    load_brandimarte,
    load_experiment_input,
    load_resource_parameters,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "python_baseline" / "data"


class BrandimarteInputTests(unittest.TestCase):
    def test_mk01_matches_matlab_reference(self):
        instance = load_brandimarte(DATA_ROOT / "brandimarte" / "Mk01.fjs")
        reference = json.loads(
            (DATA_ROOT / "matlab_reference" / "Mk01.json").read_text(encoding="utf-8")
        )

        self.assertEqual(instance.to_matlab_dict(), reference)
        self.assertEqual(instance.job_count, 10)
        self.assertEqual(instance.machine_count, 6)
        self.assertEqual(instance.operation_counts, (6, 5, 5, 5, 6, 6, 5, 5, 6, 6))

    def test_all_ten_instances_match_matlab_reference(self):
        for index in range(1, 11):
            name = f"Mk{index:02d}"
            with self.subTest(instance=name):
                instance = load_brandimarte(DATA_ROOT / "brandimarte" / f"{name}.fjs")
                reference = json.loads(
                    (DATA_ROOT / "matlab_reference" / f"{name}.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(instance.to_matlab_dict(), reference)

    def test_rejects_truncated_operation(self):
        with self.assertRaises(DataFormatError):
            load_brandimarte(REPO_ROOT / "tests" / "fixtures" / "truncated.fjs")


class UnifiedExperimentInputTests(unittest.TestCase):
    def test_full_resource_library_matches_coordinate_conversion(self):
        resources = load_resource_parameters(
            DATA_ROOT / "resources" / "static_algorithm_comparison.json"
        )
        self.assertEqual(len(resources.machine_work_energy), 15)
        self.assertEqual(resources.load_to_machine[:6], (20.0, 40.0, 60.0, 80.0, 60.0, 40.0))
        self.assertEqual(resources.machine_to_machine[0][:6], (0.0, 20.0, 40.0, 60.0, 40.0, 20.0))

    def test_all_instances_form_valid_unified_inputs(self):
        for index in range(1, 11):
            with self.subTest(instance=index):
                data = load_experiment_input(
                    DATA_ROOT / "brandimarte" / f"Mk{index:02d}.fjs",
                    DATA_ROOT / "resources" / "static_algorithm_comparison.json",
                )
                data.validate()

    def test_mk05_resource_dimensions_and_fixed_agv_parameters(self):
        data = load_experiment_input(
            DATA_ROOT / "brandimarte" / "Mk05.fjs",
            DATA_ROOT / "resources" / "static_algorithm_comparison.json",
        )

        self.assertEqual(data.instance.job_count, 15)
        self.assertEqual(data.agv.count, 4)
        self.assertEqual(data.agv.speeds, (1.0, 1.0, 1.0, 1.0))
        self.assertEqual(len(data.resources.machine_work_energy), 4)
        self.assertEqual(len(data.resources.machine_to_machine), 4)
        data.validate()


if __name__ == "__main__":
    unittest.main()
