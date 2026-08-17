"""第11步 Gate 6 动态事件验收入口。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    command = [sys.executable, "-m", "unittest", "tests.test_gate6_dynamic_rescheduling", "-v"]
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode:
        return result.returncode
    print("Gate 6 PASS: dynamic state, failure constraints, and IS/RS/CS boundaries verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
