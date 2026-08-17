"""验收第14步论文规模静态与动态原始运行是否完整。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate 7统计复现完整性验收")
    parser.add_argument("--static", type=Path, required=True)
    parser.add_argument("--dynamic", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads((args.static / "manifest.json").read_text("utf-8"))
    static_success = [run for run in manifest["runs"] if run["status"] == "success"]
    static_failed = [run for run in manifest["runs"] if run["status"] != "success"]
    dynamic_results = [
        json.loads(path.read_text("utf-8"))
        for path in args.dynamic.glob("*/result.json")
    ]
    dynamic_success = [row for row in dynamic_results if row.get("status") == "success"]
    dynamic_failed = [row for row in dynamic_results if row.get("status") != "success"]
    checks = {
        "static_success": len(static_success),
        "static_expected": 1600,
        "static_failed": len(static_failed),
        "dynamic_scenario_repeats_success": len(dynamic_success),
        "dynamic_scenario_repeats_expected": 400,
        "dynamic_failed": len(dynamic_failed),
        "static_summary_exists": (args.static / "aggregate_summary.json").is_file(),
        "dynamic_summary_exists": (args.dynamic / "dynamic_summary.json").is_file(),
    }
    passed = (
        checks["static_success"] == checks["static_expected"]
        and checks["static_failed"] == 0
        and checks["dynamic_scenario_repeats_success"]
        == checks["dynamic_scenario_repeats_expected"]
        and checks["dynamic_failed"] == 0
        and checks["static_summary_exists"]
        and checks["dynamic_summary_exists"]
    )
    print(json.dumps({"status": "pass" if passed else "fail", **checks}, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
