import unittest
import csv
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from python_baseline.dfjspt.experiments import (
    ExperimentSpec, formal_static_specs, run_batch,
)
from python_baseline.dfjspt.dynamic_experiments import formal_dynamic_scenarios
from scripts.run_step14_static import select_specs
from scripts.check_gate7 import collect_static_evidence
from scripts.audit_step14_static import build_static_audit


ROOT = Path(__file__).resolve().parents[1]


class Step14ProtocolTests(unittest.TestCase):
    def test_static_audit_script_runs_directly(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "audit_step14_static.py"), "--help"],
            cwd=ROOT, text=True, capture_output=True,
            env={**os.environ, "PYTHONUTF8": "1"},
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_static_audit_selects_observed_runs_and_only_ranks_comparable_groups(self):
        original = ROOT / "results" / "runs" / f"test_audit_original_{uuid.uuid4().hex}"
        rerun = ROOT / "results" / "runs" / f"test_audit_rerun_{uuid.uuid4().hex}"
        output = ROOT / "results" / "runs" / f"test_audit_output_{uuid.uuid4().hex}"
        algorithms = (
            "qnsga2", "nsga2", "moead", "mopso", "ablation_A",
            "ablation_B", "ablation_C", "ablation_full",
        )
        try:
            for root in (original, rerun):
                root.mkdir()
            manifests = {original: [], rerun: []}
            for index, algorithm in enumerate(algorithms):
                root = original if algorithm in {
                    "qnsga2", "ablation_B", "ablation_C", "ablation_full",
                } else rerun
                run_id = f"Mk01_{algorithm}_r01"
                folder = root / run_id
                folder.mkdir()
                config = {
                    "algorithm": algorithm, "instance": "Mk01", "repeat": 1,
                    "scenario": "ablation" if algorithm.startswith("ablation_") else "static_comparison",
                    "objective_profile": {"f2": "machine_energy_plus_agv_energy" if algorithm in {
                        "nsga2", "moead", "mopso", "ablation_A",
                    } else "machine_energy"},
                }
                result = {
                    "status": "success", "elapsed_seconds": index + 1,
                    "evaluations": 100, "seed": 7,
                    "pareto_objectives": [[10 + index, 20 + index], [11 + index, 19 + index]],
                }
                (folder / "config.json").write_text(json.dumps(config), "utf-8")
                (folder / "result.json").write_text(json.dumps(result), "utf-8")
                manifests[root].append({"run_id": run_id, "status": "success", "seed": 7})
            for root, runs in manifests.items():
                (root / "manifest.json").write_text(json.dumps({"runs": runs}), "utf-8")

            evidence = build_static_audit(original, rerun, output, expected_per_algorithm=1)

            self.assertEqual(evidence["selected_runs"], 8)
            self.assertEqual(evidence["runs_by_algorithm"], {algorithm: 1 for algorithm in sorted(algorithms)})
            self.assertEqual(
                set(evidence["ranked_groups"]),
                {"comparator_same_objectives", "ablation_machine_energy"},
            )
            self.assertTrue((output / "static_run_index.csv").is_file())
            self.assertTrue((output / "comparable_rankings.csv").is_file())
            with (output / "comparable_rankings.csv").open(encoding="utf-8-sig") as handle:
                ranking = next(csv.DictReader(handle))
            self.assertIn("mean_hv", ranking)
            self.assertIn("mean_igd", ranking)
            with (output / "algorithm_descriptive_summary.csv").open(encoding="utf-8-sig") as handle:
                summaries = {row["algorithm"]: row for row in csv.DictReader(handle)}
            self.assertEqual(summaries["qnsga2"]["objective_f1"], "last_processing_completion")
            self.assertEqual(summaries["qnsga2"]["objective_f2"], "machine_energy")
        finally:
            for path in (original, rerun, output):
                shutil.rmtree(path, ignore_errors=True)

    def test_gate7_combines_only_reusable_original_and_changed_reruns(self):
        original = ROOT / "results" / "runs" / f"test_gate7_original_{uuid.uuid4().hex}"
        rerun = ROOT / "results" / "runs" / f"test_gate7_rerun_{uuid.uuid4().hex}"
        original.mkdir()
        rerun.mkdir()
        try:
            original_runs = []
            rerun_runs = []
            for algorithm in (
                "qnsga2", "nsga2", "moead", "mopso", "ablation_A",
                "ablation_B", "ablation_C", "ablation_full",
            ):
                run_id = f"Mk01_{algorithm}_r01"
                folder = original / run_id
                folder.mkdir()
                (folder / "config.json").write_text(
                    json.dumps({"algorithm": algorithm}), "utf-8"
                )
                original_runs.append({"run_id": run_id, "status": "success"})
                if algorithm in {"nsga2", "moead", "mopso", "ablation_A"}:
                    rerun_folder = rerun / run_id
                    rerun_folder.mkdir()
                    (rerun_folder / "config.json").write_text(
                        json.dumps({"algorithm": algorithm}), "utf-8"
                    )
                    rerun_runs.append({"run_id": run_id, "status": "success"})
            (original / "manifest.json").write_text(
                json.dumps({"runs": original_runs}), "utf-8"
            )
            (rerun / "manifest.json").write_text(
                json.dumps({"runs": rerun_runs}), "utf-8"
            )

            selected = collect_static_evidence(original, rerun)

            self.assertEqual(len(selected), 8)
            self.assertEqual(len({row["algorithm"] for row in selected}), 8)
        finally:
            shutil.rmtree(original, ignore_errors=True)
            shutil.rmtree(rerun, ignore_errors=True)

    def test_formal_dynamic_grid_has_20_scenarios_and_1200_strategy_runs(self):
        scenarios = formal_dynamic_scenarios()
        self.assertEqual(len(scenarios), 20)
        self.assertEqual(len(scenarios) * 20 * 3, 1200)
        self.assertEqual(
            {scenario.kind for scenario in scenarios},
            {"order_cancellation", "machine_failure", "agv_failure"},
        )
        self.assertEqual(
            {scenario.target for scenario in scenarios if scenario.kind == "machine_failure"},
            {2},
        )
    def test_formal_static_grid_has_1600_paired_runs(self):
        specs = formal_static_specs()
        self.assertEqual(len(specs), 1600)
        group = [spec for spec in specs if spec.instance == "Mk01" and spec.repeat == 1]
        self.assertEqual(len(group), 8)
        comparison = [spec for spec in group if spec.scenario == "static_comparison"]
        self.assertEqual(
            [spec.algorithm for spec in comparison],
            ["qnsga2", "nsga2", "moead", "mopso"],
        )
        for spec in comparison[1:]:
            self.assertEqual(spec.budget_source_algorithm, "qnsga2")
            self.assertEqual(spec.generations, 0)
        ablations = [spec for spec in group if spec.scenario == "ablation"]
        self.assertTrue(all(spec.generations == 200 for spec in ablations))

    def test_static_runner_can_select_only_changed_matlab_objective_algorithms(self):
        selected = select_specs(
            formal_static_specs(),
            algorithms={"nsga2", "moead", "mopso", "ablation_A"},
        )
        self.assertEqual(len(selected), 800)
        self.assertEqual(
            {spec.algorithm for spec in selected},
            {"nsga2", "moead", "mopso", "ablation_A"},
        )

    def test_time_budget_is_inherited_and_successful_runs_resume(self):
        specs = [
            ExperimentSpec("qnsga2", "Mk01", 1, 10, 1, scenario="budget_test"),
            ExperimentSpec(
                "nsga2", "Mk01", 1, 10, 0, scenario="budget_test",
                budget_source_algorithm="qnsga2",
            ),
        ]
        output = ROOT / "results" / "runs" / f"test_step14_{uuid.uuid4().hex}"
        output.mkdir()
        try:
            first = run_batch(
                specs, output, ROOT / "python_baseline" / "data", resume=True
            )
            self.assertEqual(len(first), 2)
            manifest = json.loads((output / "manifest.json").read_text("utf-8"))
            q_folder = output / manifest["runs"][0]["run_id"]
            n_folder = output / manifest["runs"][1]["run_id"]
            q_result = json.loads((q_folder / "result.json").read_text("utf-8"))
            n_config = json.loads((n_folder / "config.json").read_text("utf-8"))
            n_result = json.loads((n_folder / "result.json").read_text("utf-8"))
            self.assertEqual(
                n_config["time_limit_seconds"], q_result["elapsed_seconds"]
            )
            self.assertGreater(n_result["evaluations"], 10)
            second = run_batch(
                specs, output, ROOT / "python_baseline" / "data", resume=True
            )
            self.assertEqual(first, second)
        finally:
            shutil.rmtree(output, ignore_errors=True)

    def test_time_budget_can_be_reused_from_preserved_result_directory(self):
        source_specs = [
            ExperimentSpec("qnsga2", "Mk01", 1, 10, 1, scenario="budget_reuse")
        ]
        target_specs = [
            ExperimentSpec(
                "nsga2", "Mk01", 1, 10, 0, scenario="budget_reuse",
                budget_source_algorithm="qnsga2",
            )
        ]
        source = ROOT / "results" / "runs" / f"test_step14_source_{uuid.uuid4().hex}"
        target = ROOT / "results" / "runs" / f"test_step14_target_{uuid.uuid4().hex}"
        source.mkdir()
        target.mkdir()
        try:
            run_batch(source_specs, source, ROOT / "python_baseline" / "data", resume=True)
            runs = run_batch(
                target_specs,
                target,
                ROOT / "python_baseline" / "data",
                resume=True,
                budget_source_output=source,
            )
            self.assertEqual(len(runs), 1)
            config = json.loads(next(target.glob("*/config.json")).read_text("utf-8"))
            self.assertGreater(config["time_limit_seconds"], 0)
        finally:
            shutil.rmtree(source, ignore_errors=True)
            shutil.rmtree(target, ignore_errors=True)

    def test_calibration_budget_overrides_only_matching_old_budget(self):
        spec = ExperimentSpec(
            "nsga2", "Mk01", 1, 10, 0, scenario="budget_override",
            budget_source_algorithm="qnsga2",
        )
        old_source = ROOT / "results" / "runs" / f"test_old_{uuid.uuid4().hex}"
        calibration = ROOT / "results" / "runs" / f"test_cal_{uuid.uuid4().hex}"
        target = ROOT / "results" / "runs" / f"test_target_{uuid.uuid4().hex}"
        for path in (old_source, calibration, target):
            path.mkdir()
        try:
            qspec = [ExperimentSpec("qnsga2", "Mk01", 1, 10, 1, scenario="budget_override")]
            run_batch(qspec, old_source, ROOT / "python_baseline" / "data", resume=True)
            run_batch(qspec, calibration, ROOT / "python_baseline" / "data", resume=True)
            calibration_result = json.loads(
                next(calibration.glob("*/result.json")).read_text("utf-8")
            )
            run_batch(
                [spec], target, ROOT / "python_baseline" / "data", resume=True,
                budget_source_output=old_source,
                budget_override_output=calibration,
            )
            config = json.loads(next(target.glob("*/config.json")).read_text("utf-8"))
            self.assertEqual(
                config["time_limit_seconds"], calibration_result["elapsed_seconds"]
            )
        finally:
            for path in (old_source, calibration, target):
                shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
