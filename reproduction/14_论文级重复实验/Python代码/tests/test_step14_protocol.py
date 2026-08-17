import unittest
import json
import shutil
import uuid
from pathlib import Path

from python_baseline.dfjspt.experiments import (
    ExperimentSpec, formal_static_specs, run_batch,
)
from python_baseline.dfjspt.dynamic_experiments import formal_dynamic_scenarios


ROOT = Path(__file__).resolve().parents[1]


class Step14ProtocolTests(unittest.TestCase):
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
            self.assertEqual(
                n_config["time_limit_seconds"], q_result["elapsed_seconds"]
            )
            second = run_batch(
                specs, output, ROOT / "python_baseline" / "data", resume=True
            )
            self.assertEqual(first, second)
        finally:
            shutil.rmtree(output, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
