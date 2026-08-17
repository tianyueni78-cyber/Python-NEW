"""第13步：统一执行MATLAB–Python固定输入逐层对照。"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ROOT = ROOT / "python_baseline" / "data" / "matlab_reference"
REFERENCE_GROUPS = {
    "input": tuple(REFERENCE_ROOT / f"Mk{i:02d}.json" for i in range(1, 11)),
    "initialization": (REFERENCE_ROOT / "Mk05_initialization_seed_20260817.json",),
    "decoder": (REFERENCE_ROOT / "Mk05_decoder_reference.json",),
    "multiobjective": (REFERENCE_ROOT / "multiobjective_step7.json",),
    "q_learning": (REFERENCE_ROOT / "qnsga_step8.json",),
    "dynamic": (REFERENCE_ROOT / "dynamic_step11.json",),
    "metrics": (REFERENCE_ROOT / "metrics_step12.json",),
}
COMMANDS = (
    (1, (sys.executable, "scripts/check_gate1.py")),
    (2, (sys.executable, "scripts/check_gate2_initialization.py", "--population", "100")),
    (3, (sys.executable, "scripts/check_gate3.py")),
    (4, (sys.executable, "scripts/check_gate4.py")),
    (5, (sys.executable, "scripts/check_gate5.py")),
    (6, (sys.executable, "scripts/check_gate6.py")),
    ("metrics", (sys.executable, "scripts/check_step12.py")),
)


def run_audit() -> dict[str, object]:
    missing = [str(path.relative_to(ROOT)) for paths in REFERENCE_GROUPS.values() for path in paths if not path.is_file()]
    if missing:
        return {"status": "fail", "missing_references": missing, "checks": []}
    checks = []
    for gate, command in COMMANDS:
        started = time.perf_counter()
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=env)
        checks.append({
            "gate": gate,
            "status": "pass" if completed.returncode == 0 else "fail",
            "duration_seconds": round(time.perf_counter() - started, 6),
            "command": " ".join(command[1:]),
            "returncode": completed.returncode,
        })
        if completed.returncode:
            break
    return {
        "status": "pass" if len(checks) == len(COMMANDS) and all(item["status"] == "pass" for item in checks) else "fail",
        "checks": checks,
        "reference_files": len(REFERENCE_GROUPS),
        "reference_groups": list(REFERENCE_GROUPS),
        "deterministic_boundary": "固定输入逐项对照",
        "random_boundary": "统计分布待第14步验证",
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="仅输出JSON")
    args = parser.parse_args()
    report = run_audit()
    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
