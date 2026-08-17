"""第12步指标与实验系统专项验收。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    return subprocess.run(
        [sys.executable, "-m", "unittest", "tests.test_step12_metrics_experiments", "-v"],
        cwd=ROOT, check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
