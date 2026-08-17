from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CrossLanguageAuditTests(unittest.TestCase):
    def test_unified_audit_runs_all_six_gates_and_metric_parity(self):
        completed = subprocess.run(
            [sys.executable, "scripts/check_step13.py", "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={key: value for key, value in os.environ.items() if key != "PYTHONIOENCODING"},
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "pass")
        self.assertEqual([item["gate"] for item in report["checks"]], [1, 2, 3, 4, 5, 6, "metrics"])
        self.assertTrue(all(item["status"] == "pass" for item in report["checks"]))
        self.assertEqual(report["reference_files"], 7)
        self.assertEqual(report["random_boundary"], "统计分布待第14步验证")


if __name__ == "__main__":
    unittest.main()
