"""合并并审计第14步两批MATLAB活动代码口径静态结果。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_baseline.dfjspt.metrics import (
    coverage, hypervolume_2d, igd, normalize_groups, reference_front, spacing,
)
from python_baseline.dfjspt.experiments import matlab_objective_profile
from scripts.check_gate7 import ORIGINAL_ALGORITHMS, RERUN_ALGORITHMS


COMPARABLE_GROUPS = {
    "comparator_same_objectives": ("nsga2", "moead", "mopso"),
    "ablation_machine_energy": ("ablation_B", "ablation_C", "ablation_full"),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_csv(path: Path, header: tuple[str, ...], rows) -> None:
    with path.open("x", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def _read_selected(root: Path, allowed: set[str], source_batch: str) -> list[dict]:
    manifest = json.loads((root / "manifest.json").read_text("utf-8"))
    rows = []
    for item in manifest["runs"]:
        folder = root / item["run_id"]
        config = json.loads((folder / "config.json").read_text("utf-8"))
        if config["algorithm"] not in allowed:
            continue
        result = json.loads((folder / "result.json").read_text("utf-8"))
        objective_profile = matlab_objective_profile(config["algorithm"]) | config.get("objective_profile", {})
        rows.append({
            "run_id": item["run_id"], "status": item["status"],
            "seed": item["seed"], "algorithm": config["algorithm"],
            "instance": config["instance"], "repeat": config["repeat"],
            "scenario": config["scenario"], "objective_profile": objective_profile,
            "elapsed_seconds": result.get("elapsed_seconds"),
            "evaluations": result.get("evaluations"),
            "pareto_objectives": result.get("pareto_objectives", []),
            "source_batch": source_batch, "source_root": str(root),
            "source_folder": str(folder),
            "config_sha256": _sha256(folder / "config.json"),
            "result_sha256": _sha256(folder / "result.json"),
        })
    return rows


def _mean_rank(values: dict[str, float], higher_is_better: bool) -> dict[str, float]:
    ordered = sorted(values, key=values.get, reverse=higher_is_better)
    return {name: float(ordered.index(name) + 1) for name in ordered}


def build_static_audit(
    original: Path, rerun: Path, output: Path, *, expected_per_algorithm: int = 200,
) -> dict:
    """选择两批有效运行，输出唯一索引和同目标子组统计。"""
    if output.exists():
        raise FileExistsError(f"禁止覆盖已有审计目录：{output}")
    rows = (
        _read_selected(original, ORIGINAL_ALGORITHMS, "preserved_original")
        + _read_selected(rerun, RERUN_ALGORITHMS, "matlab_observed_rerun")
    )
    counts = Counter(row["algorithm"] for row in rows if row["status"] == "success")
    expected_algorithms = ORIGINAL_ALGORITHMS | RERUN_ALGORITHMS
    if set(counts) != expected_algorithms or set(counts.values()) != {expected_per_algorithm}:
        raise ValueError(f"静态运行数量不完整：{dict(sorted(counts.items()))}")
    if any(row["status"] != "success" for row in rows):
        raise ValueError("选中结果含失败运行")
    keys = [(row["instance"], row["repeat"], row["algorithm"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("实例、重复和算法组合不唯一")
    paired = defaultdict(set)
    for row in rows:
        paired[(row["instance"], row["repeat"])].add(row["seed"])
    if any(len(seeds) != 1 for seeds in paired.values()):
        raise ValueError("配对实验种子不一致")

    output.mkdir(parents=True)
    index_header = (
        "instance", "repeat", "algorithm", "scenario", "seed", "status",
        "objective_f1", "objective_f2", "elapsed_seconds", "evaluations",
        "pareto_solutions", "source_batch", "source_root", "source_folder",
        "config_sha256", "result_sha256",
    )
    _write_csv(output / "static_run_index.csv", index_header, (
        (
            row["instance"], row["repeat"], row["algorithm"], row["scenario"],
            row["seed"], row["status"], row["objective_profile"].get("f1", ""),
            row["objective_profile"].get("f2", ""), row["elapsed_seconds"],
            row["evaluations"], len(row["pareto_objectives"]), row["source_batch"],
            row["source_root"], row["source_folder"], row["config_sha256"],
            row["result_sha256"],
        ) for row in sorted(rows, key=lambda x: (x["instance"], x["repeat"], x["algorithm"]))
    ))

    summary_rows = []
    for algorithm in sorted(expected_algorithms):
        group = [row for row in rows if row["algorithm"] == algorithm]
        min_f1 = [min(point[0] for point in row["pareto_objectives"]) for row in group]
        min_f2 = [min(point[1] for point in row["pareto_objectives"]) for row in group]
        summary_rows.append((
            algorithm, group[0]["objective_profile"].get("f1", ""),
            group[0]["objective_profile"].get("f2", ""), len(group),
            statistics.fmean(min_f1), statistics.median(min_f1),
            statistics.fmean(min_f2), statistics.median(min_f2),
            statistics.fmean(row["elapsed_seconds"] for row in group),
            statistics.fmean(row["evaluations"] for row in group),
            statistics.fmean(len(row["pareto_objectives"]) for row in group),
        ))
    _write_csv(
        output / "algorithm_descriptive_summary.csv",
        ("algorithm", "objective_f1", "objective_f2", "runs", "mean_run_min_f1",
         "median_run_min_f1", "mean_run_min_f2", "median_run_min_f2",
         "mean_elapsed_seconds", "mean_evaluations", "mean_pareto_solutions"),
        summary_rows,
    )

    metric_rows, coverage_rows = [], []
    rank_accumulator = defaultdict(lambda: defaultdict(list))
    by_key_algorithm = {(row["instance"], row["repeat"], row["algorithm"]): row for row in rows}
    for group_name, algorithms in COMPARABLE_GROUPS.items():
        for instance, repeat in sorted(paired):
            groups = [by_key_algorithm[(instance, repeat, name)]["pareto_objectives"] for name in algorithms]
            normalized = normalize_groups(groups)
            front = reference_front([point for points in normalized for point in points])
            metrics = {
                name: {"hv": hypervolume_2d(points), "igd": igd(front, points), "spacing": spacing(points)}
                for name, points in zip(algorithms, normalized)
            }
            for metric, higher in (("hv", True), ("igd", False), ("spacing", False)):
                ranks = _mean_rank({name: metrics[name][metric] for name in algorithms}, higher)
                for name in algorithms:
                    rank_accumulator[(group_name, name)][metric].append(ranks[name])
                    rank_accumulator[(group_name, name)][f"{metric}_value"].append(metrics[name][metric])
            for name in algorithms:
                metric_rows.append((group_name, instance, repeat, name, metrics[name]["hv"], metrics[name]["igd"], metrics[name]["spacing"]))
            for left_index, left in enumerate(algorithms):
                for right_index, right in enumerate(algorithms):
                    if left != right:
                        coverage_rows.append((group_name, instance, repeat, left, right, coverage(normalized[left_index], normalized[right_index])))
    _write_csv(output / "comparable_metrics.csv", ("group", "instance", "repeat", "algorithm", "hv", "igd", "spacing"), metric_rows)
    _write_csv(output / "comparable_coverage.csv", ("group", "instance", "repeat", "left", "right", "coverage"), coverage_rows)
    ranking_rows = []
    for (group_name, algorithm), metrics in sorted(rank_accumulator.items()):
        ranking_rows.append((
            group_name, algorithm,
            *(statistics.fmean(metrics[f"{name}_value"]) for name in ("hv", "igd", "spacing")),
            *(statistics.fmean(metrics[name]) for name in ("hv", "igd", "spacing")),
        ))
    _write_csv(
        output / "comparable_rankings.csv",
        ("group", "algorithm", "mean_hv", "mean_igd", "mean_spacing",
         "mean_hv_rank", "mean_igd_rank", "mean_spacing_rank"),
        ranking_rows,
    )

    evidence = {
        "status": "pass", "definition": "MATLAB活动代码口径静态1600次",
        "selected_runs": len(rows), "failed_runs": 0,
        "runs_by_algorithm": dict(sorted(counts.items())),
        "paired_instance_repeat_groups": len(paired),
        "source_manifests": {
            "preserved_original": {"path": str(original / "manifest.json"), "sha256": _sha256(original / "manifest.json")},
            "matlab_observed_rerun": {"path": str(rerun / "manifest.json"), "sha256": _sha256(rerun / "manifest.json")},
        },
        "ranked_groups": COMPARABLE_GROUPS,
        "cross_profile_ranking": "not_permitted",
        "reason": "活动MATLAB目录使用两套不同f1/f2，八算法统一排名不具备同目标可比性",
    }
    (output / "static_audit_evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), "utf-8")
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="合并审计第14步静态活动代码结果")
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--rerun", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_static_audit(args.original, args.rerun, args.output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
