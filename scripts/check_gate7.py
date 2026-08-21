"""验收第14步论文规模静态与动态原始运行是否完整。"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


ORIGINAL_ALGORITHMS = {"qnsga2", "ablation_B", "ablation_C", "ablation_full"}
RERUN_ALGORITHMS = {"nsga2", "moead", "mopso", "ablation_A"}


def _read_runs(root: Path, allowed: set[str] | None = None) -> list[dict]:
    manifest = json.loads((root / "manifest.json").read_text("utf-8"))
    selected = []
    for run in manifest["runs"]:
        config = json.loads(
            (root / run["run_id"] / "config.json").read_text("utf-8")
        )
        algorithm = config["algorithm"]
        if allowed is None or algorithm in allowed:
            selected.append({**run, "algorithm": algorithm, "source": str(root)})
    return selected


def collect_static_evidence(original: Path, rerun: Path) -> list[dict]:
    """组合未受影响的旧结果与目标口径改变后的新结果。"""
    return (
        _read_runs(original, ORIGINAL_ALGORITHMS)
        + _read_runs(rerun, RERUN_ALGORITHMS)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate 7统计复现完整性验收")
    parser.add_argument("--static", type=Path)
    parser.add_argument("--static-original", type=Path)
    parser.add_argument("--static-rerun", type=Path)
    parser.add_argument("--dynamic", type=Path, required=True)
    args = parser.parse_args()

    if args.static:
        if args.static_original or args.static_rerun:
            parser.error("--static不能与拆分静态目录参数同时使用")
        static_runs = _read_runs(args.static)
        static_summary_exists = (args.static / "aggregate_summary.json").is_file()
    else:
        if not args.static_original or not args.static_rerun:
            parser.error("请提供--static，或同时提供--static-original和--static-rerun")
        static_runs = collect_static_evidence(args.static_original, args.static_rerun)
        static_summary_exists = all(
            (root / "aggregate_summary.json").is_file()
            for root in (args.static_original, args.static_rerun)
        )
    static_success = [run for run in static_runs if run["status"] == "success"]
    static_failed = [run for run in static_runs if run["status"] != "success"]
    static_by_algorithm = Counter(run["algorithm"] for run in static_success)
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
        "static_success_by_algorithm": dict(sorted(static_by_algorithm.items())),
        "dynamic_scenario_repeats_success": len(dynamic_success),
        "dynamic_scenario_repeats_expected": 400,
        "dynamic_failed": len(dynamic_failed),
        "static_summary_exists": static_summary_exists,
        "dynamic_summary_exists": (args.dynamic / "dynamic_summary.json").is_file(),
    }
    passed = (
        checks["static_success"] == checks["static_expected"]
        and checks["static_failed"] == 0
        and set(static_by_algorithm.values()) == {200}
        and len(static_by_algorithm) == 8
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
