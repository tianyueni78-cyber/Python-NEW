import subprocess
import sys
import unittest
import uuid
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "paper_static_baseline" / "scripts" / "verify_baseline.py"
RUNTIME = Path(__file__).resolve().parent / "_runtime"


class BaselineVerifierTests(unittest.TestCase):
    def test_incomplete_root_is_rejected(self):
        incomplete = RUNTIME / f"incomplete-{uuid.uuid4().hex}"
        incomplete.mkdir(parents=True)
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(incomplete)],
            cwd=REPO, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("缺少", completed.stderr)


if __name__ == "__main__":
    unittest.main()
