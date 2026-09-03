import json
import subprocess
import sys
import unittest
import uuid
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "paper_static_baseline" / "scripts" / "run_a0.py"
RUNTIME_ROOT = Path(__file__).resolve().parent / "_runtime"
RUNTIME_ROOT.mkdir(exist_ok=True)


class A0RunnerTests(unittest.TestCase):
    def output_path(self, name):
        return RUNTIME_ROOT / f"{name}-{uuid.uuid4().hex}"

    def run_a0(self, output, seed="1"):
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--instance", "Mk01",
                "--population", "10",
                "--generations", "1",
                "--seed", seed,
                "--output", str(output),
            ],
            cwd=REPO,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_small_run_writes_complete_manifest(self):
        output = self.output_path("run")
        completed = self.run_a0(output)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "completed")
        self.assertEqual(manifest["instance"], "Mk01")
        self.assertEqual(manifest["seed"], 1)
        self.assertEqual(manifest["population"], 10)
        self.assertEqual(manifest["generations"], 1)
        self.assertGreater(manifest["full_decode_evaluations"], 10)
        self.assertTrue(manifest["pareto_objectives"])
        self.assertEqual(len(manifest["qtable"]), 4)
        self.assertEqual(len(manifest["source_commit"]), 40)
        self.assertEqual(len(manifest["config_sha256"]), 64)

    def test_existing_output_directory_is_rejected(self):
        output = self.output_path("existing")
        output.mkdir()
        completed = self.run_a0(output)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("已存在", completed.stderr)

    def test_same_seed_produces_identical_scientific_results(self):
        first = self.output_path("first")
        second = self.output_path("second")
        self.assertEqual(self.run_a0(first).returncode, 0)
        self.assertEqual(self.run_a0(second).returncode, 0)
        left = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
        right = json.loads((second / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(left, right)


if __name__ == "__main__":
    unittest.main()
