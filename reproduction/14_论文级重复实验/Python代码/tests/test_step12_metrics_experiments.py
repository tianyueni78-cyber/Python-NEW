import csv
import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import python_baseline.dfjspt.experiments as experiments
from python_baseline.dfjspt.experiments import ExperimentSpec, paired_seed, run_batch
from python_baseline.dfjspt.metrics import (
    coverage,
    dynamic_rsi_components,
    hypervolume_2d,
    igd,
    normalize_groups,
    reference_front,
    rsi,
    spacing,
)


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "python_baseline" / "data"
TEMP_ROOT = ROOT / "results" / "runs"


class MetricParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = json.loads(
            (DATA / "matlab_reference" / "metrics_step12.json").read_text("utf-8")
        )

    def test_normalization_hv_igd_spacing_and_c_match_matlab(self):
        groups = self.reference["groups"]
        normalized = normalize_groups(groups)
        for actual, expected in zip(normalized, self.reference["normalized"]):
            for left, right in zip(actual, expected):
                self.assertAlmostEqual(left[0], right[0], places=12)
                self.assertAlmostEqual(left[1], right[1], places=12)
        front = reference_front([row for group in normalized for row in group])
        self.assertEqual([list(row) for row in front], self.reference["reference_front"])
        for index, group in enumerate(normalized):
            self.assertAlmostEqual(hypervolume_2d(group), self.reference["hv"][index], 12)
            self.assertAlmostEqual(igd(front, group), self.reference["igd"][index], 12)
            self.assertAlmostEqual(spacing(group), self.reference["spacing"][index], 12)
        self.assertAlmostEqual(coverage(normalized[0], normalized[1]), self.reference["c_ab"], 12)
        self.assertAlmostEqual(coverage(normalized[1], normalized[0]), self.reference["c_ba"], 12)

    def test_rsi_uses_locked_equal_weights(self):
        self.assertAlmostEqual(rsi((0.3, 0.6, 0.9)), 0.59994, places=12)

    def test_dynamic_components_follow_active_matlab_fitness(self):
        from python_baseline.dfjspt.chromosome import Chromosome
        from python_baseline.dfjspt.data import load_experiment_input
        from python_baseline.dfjspt.decoder import decode_static
        decoder_ref = json.loads((DATA / "matlab_reference" / "Mk05_decoder_reference.json").read_text("utf-8"))
        data = load_experiment_input(DATA / "brandimarte" / "Mk05.fjs", DATA / "resources" / "static_algorithm_comparison.json")
        chromosome = Chromosome.from_matlab_row(decoder_ref["chromosome_matlab_1_based"], data.instance.operation_count)
        schedule = decode_static(data, chromosome, speeds=(1, 1, 1, 1))
        components = dynamic_rsi_components(schedule, schedule, data.instance.operation_count)
        self.assertEqual(components[0], 0.0)
        self.assertAlmostEqual(components[1], schedule.agv_energy / data.instance.operation_count)
        self.assertEqual(components[2], 0.0)

    def test_dynamic_apsd_preserves_matlab_col_typo_by_default(self):
        from dataclasses import replace
        from python_baseline.dfjspt.decoder import MachineBlock, ScheduleResult
        original = ScheduleResult(0, 0, 0, (), (), ((MachineBlock(10, 11, 1, 1), MachineBlock(20, 21, 1, 2)),), (), ())
        changed = replace(original, machine_tables=((MachineBlock(11, 12, 1, 1), MachineBlock(24, 25, 1, 2)),))
        self.assertEqual(dynamic_rsi_components(original, changed, 2)[2], 4.0)
        self.assertEqual(dynamic_rsi_components(original, changed, 2, False)[2], 2.5)

    def test_constant_objective_column_is_rejected_not_silently_divided(self):
        with self.assertRaises(ValueError):
            normalize_groups([[(1, 2)], [(1, 3)]])


class ExperimentTrackingTests(unittest.TestCase):
    def setUp(self):
        self.temp_roots = []

    def tearDown(self):
        for path in self.temp_roots:
            shutil.rmtree(path, ignore_errors=True)

    def temporary_root(self):
        path = TEMP_ROOT / f"test_step12_{uuid.uuid4().hex}"
        path.mkdir()
        self.temp_roots.append(path)
        return path

    def test_paired_seed_is_same_across_algorithms(self):
        self.assertEqual(paired_seed("Mk01", 3), paired_seed("Mk01", 3))
        self.assertNotEqual(paired_seed("Mk01", 3), paired_seed("Mk01", 4))

    def test_small_batch_is_reproducible_and_fully_traced(self):
        specs = [
            ExperimentSpec("qnsga2", "Mk01", 0, 10, 1),
            ExperimentSpec("nsga2", "Mk01", 0, 10, 1),
        ]
        first, second = self.temporary_root(), self.temporary_root()
        a = run_batch(specs, first, DATA)
        b = run_batch(specs, second, DATA)
        self.assertEqual([r.seed for r in a], [r.seed for r in b])
        self.assertEqual([r.pareto_objectives for r in a], [r.pareto_objectives for r in b])
        for root in (first, second):
            manifest = json.loads((root / "manifest.json").read_text("utf-8"))
            self.assertEqual(len(manifest["runs"]), 2)
            self.assertTrue((root / "summary.json").is_file())
            self.assertTrue((root / "summary.csv").is_file())
            self.assertTrue((root / "pareto_plot_data.csv").is_file())
            self.assertTrue((root / "boxplot_data.csv").is_file())
            self.assertTrue((root / "aggregate_summary.json").is_file())
            self.assertTrue((root / "aggregate_summary.csv").is_file())
            for run in manifest["runs"]:
                folder = root / run["run_id"]
                self.assertTrue((folder / "config.json").is_file())
                self.assertTrue((folder / "result.json").is_file())
                self.assertTrue((folder / "pareto.csv").is_file())
                self.assertTrue((folder / "curves.csv").is_file())
                config = json.loads((folder / "config.json").read_text("utf-8"))
                self.assertIn("git_commit", config)
                self.assertIn("seed", config)
                self.assertIn("input_sha256", config)
                with (folder / "pareto.csv").open(newline="", encoding="utf-8") as handle:
                    self.assertGreater(len(list(csv.reader(handle))), 1)

    def test_existing_output_directory_is_never_overwritten(self):
        spec = [ExperimentSpec("nsga2", "Mk01", 0, 8, 1)]
        temp = self.temporary_root()
        run_batch(spec, temp, DATA)
        with self.assertRaises(FileExistsError):
            run_batch(spec, temp, DATA)

    def test_failed_run_is_written_to_manifest_before_error_returns(self):
        temp = self.temporary_root()
        with self.assertRaises(ValueError):
            run_batch([ExperimentSpec("unknown", "Mk01", 0, 8, 1)], temp, DATA)
        manifest = json.loads((temp / "manifest.json").read_text("utf-8"))
        self.assertEqual(manifest["runs"][0]["status"], "failed")
        result = json.loads(next(temp.glob("*/result.json")).read_text("utf-8"))
        self.assertEqual(result["status"], "failed")

    def test_success_is_checkpointed_before_later_interruption(self):
        temp = self.temporary_root()
        specs = [
            ExperimentSpec("qnsga2", "Mk01", 0, 10, 1),
            ExperimentSpec("nsga2", "Mk01", 0, 10, 1),
        ]
        original_run = experiments._run
        call_count = 0

        def interrupt_second_run(data, spec, seed):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise KeyboardInterrupt
            return original_run(data, spec, seed)

        with patch.object(experiments, "_run", side_effect=interrupt_second_run):
            with self.assertRaises(KeyboardInterrupt):
                run_batch(specs, temp, DATA)

        manifest = json.loads((temp / "manifest.json").read_text("utf-8"))
        self.assertEqual(len(manifest["runs"]), 1)
        self.assertEqual(manifest["runs"][0]["status"], "success")


if __name__ == "__main__":
    unittest.main()
