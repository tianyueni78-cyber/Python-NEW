"""可追溯、不可覆盖的论文批量实验运行与原始结果记录。"""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import statistics
import subprocess
import time
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .ablations import run_ablation
from .data import load_experiment_input
from .moead import run_moead
from .mopso import run_mopso
from .nsga2 import run_nsga2
from .qnsga2 import run_qnsga2
from .metrics import coverage, hypervolume_2d, igd, normalize_groups, reference_front, spacing


@dataclass(frozen=True)
class ExperimentSpec:
    algorithm: str
    instance: str
    repeat: int
    population_size: int
    generations: int
    scenario: str = "static"
    strategy: str = "none"
    time_limit_seconds: float | None = None
    budget_source_algorithm: str | None = None


@dataclass(frozen=True)
class TrackedRun:
    run_id: str
    seed: int
    elapsed_seconds: float
    evaluations: int
    pareto_objectives: tuple[tuple[float, float], ...]


def paired_seed(instance: str, repeat: int, base_seed: int = 20260817) -> int:
    payload = f"{base_seed}:{instance}:{repeat}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "big")


def matlab_objective_profile(algorithm: str) -> dict[str, object]:
    comparator = algorithm in {"nsga2", "moead", "mopso", "ablation_A"}
    return {
        "f1": "makespan_after_unload" if comparator else "last_processing_completion",
        "f2": "machine_energy_plus_agv_energy" if comparator else "machine_energy",
        "finished_jobs_return_to_unload": comparator,
    }


def formal_static_specs() -> list[ExperimentSpec]:
    """生成论文静态算法对比与消融的1600个正式运行。"""
    specs: list[ExperimentSpec] = []
    for instance_index in range(1, 11):
        instance = f"Mk{instance_index:02d}"
        for repeat in range(1, 21):
            specs.append(ExperimentSpec(
                "qnsga2", instance, repeat, 100, 200,
                scenario="static_comparison",
            ))
            for algorithm in ("nsga2", "moead", "mopso"):
                specs.append(ExperimentSpec(
                    algorithm, instance, repeat, 100, 0,
                    scenario="static_comparison",
                    budget_source_algorithm="qnsga2",
                ))
            for algorithm in (
                "ablation_A", "ablation_B", "ablation_C", "ablation_full",
            ):
                specs.append(ExperimentSpec(
                    algorithm, instance, repeat, 100, 200,
                    scenario="ablation",
                ))
    return specs


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True,
    ).stdout.strip()


def _run(data, spec: ExperimentSpec, seed: int):
    generations = None if spec.time_limit_seconds is not None else spec.generations
    common = dict(population_size=spec.population_size, generations=generations, seed=seed)
    if spec.algorithm == "qnsga2":
        return run_qnsga2(data, **common)
    if spec.algorithm == "nsga2":
        return run_nsga2(data, **common, time_limit_seconds=spec.time_limit_seconds)
    if spec.algorithm == "moead":
        return run_moead(data, **common, time_limit_seconds=spec.time_limit_seconds)
    if spec.algorithm == "mopso":
        return run_mopso(data, **common, time_limit_seconds=spec.time_limit_seconds)
    if spec.algorithm in {"ablation_A", "ablation_B", "ablation_C", "ablation_full"}:
        return run_ablation(data, spec.algorithm.removeprefix("ablation_"), **common)
    raise ValueError(f"未知算法入口：{spec.algorithm}")


def _write_csv(path: Path, header: list[str], rows, *, replace_existing: bool = False) -> None:
    with path.open("w" if replace_existing else "x", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def run_batch(
    specs: list[ExperimentSpec], output: Path, data_root: Path, *, resume: bool = False,
    budget_source_output: Path | None = None,
) -> tuple[TrackedRun, ...]:
    if not specs:
        raise ValueError("批量实验不能为空")
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.json"
    if manifest_path.exists() and not resume:
        raise FileExistsError("实验目录已有清单，禁止覆盖原始结果")
    repo_root = Path(__file__).resolve().parents[2]
    commit = _git_commit(repo_root)
    resource_path = data_root / "resources" / "static_algorithm_comparison.json"
    tracked: list[TrackedRun] = []
    elapsed_by_key: dict[tuple[str, int, str, str], float] = {}
    if budget_source_output is not None:
        source_manifest = json.loads(
            (budget_source_output / "manifest.json").read_text("utf-8")
        )
        for item in source_manifest["runs"]:
            if item["status"] != "success":
                continue
            folder = budget_source_output / item["run_id"]
            config = json.loads((folder / "config.json").read_text("utf-8"))
            result = json.loads((folder / "result.json").read_text("utf-8"))
            elapsed_by_key[(
                config["instance"], config["repeat"], config["scenario"],
                config["algorithm"],
            )] = result["elapsed_seconds"]
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text("utf-8"))
        for item in manifest["runs"]:
            if item["status"] != "success":
                continue
            folder = output / item["run_id"]
            config = json.loads((folder / "config.json").read_text("utf-8"))
            result = json.loads((folder / "result.json").read_text("utf-8"))
            record = TrackedRun(
                item["run_id"], item["seed"], result["elapsed_seconds"],
                result["evaluations"],
                tuple(tuple(row) for row in result["pareto_objectives"]),
            )
            tracked.append(record)
            elapsed_by_key[(
                config["instance"], config["repeat"], config["scenario"],
                config["algorithm"],
            )] = record.elapsed_seconds
    else:
        manifest = {
            "protocol_version": "1.0",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "git_commit": commit,
            "python": platform.python_version(),
            "runs": [],
        }
    completed_ids = {item["run_id"] for item in manifest["runs"]}
    for spec in specs:
        seed = paired_seed(spec.instance, spec.repeat)
        suffix = "" if spec.scenario == "static" and spec.strategy == "none" else f"_{spec.scenario}_{spec.strategy}"
        run_id = f"{spec.instance}_{spec.algorithm}{suffix}_r{spec.repeat:02d}_s{seed}"
        if run_id in completed_ids:
            continue
        if spec.budget_source_algorithm:
            key = (
                spec.instance, spec.repeat, spec.scenario,
                spec.budget_source_algorithm,
            )
            if key not in elapsed_by_key:
                raise ValueError(f"公平时间预算来源尚未完成：{key}")
            spec = replace(spec, time_limit_seconds=elapsed_by_key[key])
        folder = output / run_id
        folder.mkdir()
        instance_path = data_root / "brandimarte" / f"{spec.instance}.fjs"
        config = asdict(spec) | {
            "run_id": run_id, "seed": seed, "git_commit": commit,
            "protocol_version": "1.0",
            "input_sha256": _sha256(instance_path),
            "resource_sha256": _sha256(resource_path),
            "objective_profile": matlab_objective_profile(spec.algorithm),
        }
        (folder / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), "utf-8")
        started = time.perf_counter()
        try:
            data = load_experiment_input(instance_path, resource_path)
            result = _run(data, spec, seed)
            elapsed = time.perf_counter() - started
            objectives = tuple(tuple(row) for row in result.pareto_objectives)
            record = TrackedRun(run_id, seed, elapsed, result.evaluations, objectives)
            payload = {
                "status": "success", "elapsed_seconds": elapsed,
                "evaluations": result.evaluations, "seed": seed,
                "pareto_objectives": objectives,
                "pareto_chromosomes_matlab": [chromosome.to_matlab_row() for chromosome in result.pareto_chromosomes],
                "curve_min": result.curve_min,
                "curve_average": result.curve_average,
                "qtable": getattr(result, "qtable", None),
            }
            (folder / "result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
            _write_csv(
                folder / "pareto.csv",
                ["makespan", "energy_objective", "chromosome_matlab_1_based_json"],
                ((objective[0], objective[1], json.dumps(chromosome.to_matlab_row())) for objective, chromosome in zip(objectives, result.pareto_chromosomes)),
            )
            _write_csv(
                folder / "curves.csv",
                ["generation", "min_makespan", "min_energy", "avg_makespan", "avg_energy"],
                ((i + 1, *minimum, *average) for i, (minimum, average) in enumerate(zip(result.curve_min, result.curve_average))),
            )
            tracked.append(record)
            elapsed_by_key[(
                spec.instance, spec.repeat, spec.scenario, spec.algorithm,
            )] = elapsed
            manifest["runs"].append({"run_id": run_id, "status": "success", "seed": seed})
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8")
        except Exception as error:
            elapsed = time.perf_counter() - started
            (folder / "result.json").write_text(json.dumps({"status": "failed", "elapsed_seconds": elapsed, "error": repr(error)}, ensure_ascii=False, indent=2), "utf-8")
            manifest["runs"].append({"run_id": run_id, "status": "failed", "seed": seed})
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8")
            raise
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8")
    summarize_batch(output, tracked)
    return tuple(tracked)


def summarize_batch(output: Path, runs: list[TrackedRun]) -> dict[str, Any]:
    """生成指标汇总和论文作图所需的原始长表，不绘制或筛选结果。"""
    run_config: dict[str, dict[str, Any]] = {}
    for item in json.loads((output / "manifest.json").read_text("utf-8"))["runs"]:
        config = json.loads((output / item["run_id"] / "config.json").read_text("utf-8"))
        run_config[item["run_id"]] = config
    grouped: dict[tuple[str, int, str], list[TrackedRun]] = {}
    for run in runs:
        config = run_config[run.run_id]
        grouped.setdefault((config["instance"], config["repeat"], config["scenario"]), []).append(run)
    summaries: dict[str, Any] = {}
    summary_rows = []
    for key, group_runs in grouped.items():
        by_algorithm = {run_config[run.run_id]["algorithm"]: list(run.pareto_objectives) for run in group_runs}
        names = list(by_algorithm)
        normalization_error = None
        try:
            normalized = normalize_groups([by_algorithm[name] for name in names])
            front = reference_front([point for group in normalized for point in group])
            metrics = {name: {"hv": hypervolume_2d(group), "igd": igd(front, group), "spacing": spacing(group), "solutions": len(group)} for name, group in zip(names, normalized)}
            c_metric = {f"C({left},{right})": coverage(normalized[i], normalized[j]) for i, left in enumerate(names) for j, right in enumerate(names) if i != j}
        except ValueError as error:
            front, c_metric, normalization_error = (), {}, str(error)
            metrics = {name: {"hv": None, "igd": None, "spacing": None, "solutions": len(by_algorithm[name])} for name in names}
        group_id = f"{key[0]}_r{key[1]:02d}_{key[2]}"
        summaries[group_id] = {"metrics": metrics, "c_metric": c_metric, "reference_front": front, "normalization_error": normalization_error}
        summary_rows.extend((key[0], key[1], key[2], name, row["hv"], row["igd"], row["spacing"], row["solutions"]) for name, row in metrics.items())
    summary = {"groups": summaries}
    _write_csv(
        output / "summary.csv", ["instance", "repeat", "scenario", "algorithm", "hv", "igd", "spacing", "solutions"], summary_rows,
        replace_existing=True,
    )
    _write_csv(
        output / "pareto_plot_data.csv", ["algorithm", "makespan", "energy_objective"],
        ((run_config[run.run_id]["algorithm"], *point) for run in runs for point in run.pareto_objectives),
        replace_existing=True,
    )
    _write_csv(
        output / "boxplot_data.csv", ["run_id", "algorithm", "makespan", "energy_objective"],
        ((run.run_id, run_config[run.run_id]["algorithm"], *point) for run in runs for point in run.pareto_objectives),
        replace_existing=True,
    )
    aggregate: dict[str, dict[str, dict[str, float | int]]] = {}
    algorithms = sorted({config["algorithm"] for config in run_config.values()})
    for algorithm in algorithms:
        aggregate[algorithm] = {}
        for metric in ("hv", "igd", "spacing"):
            values = [group["metrics"][algorithm][metric] for group in summaries.values() if algorithm in group["metrics"] and group["metrics"][algorithm][metric] is not None]
            if not values:
                continue
            quartiles = statistics.quantiles(values, n=4, method="inclusive") if len(values) > 1 else [values[0]] * 3
            aggregate[algorithm][metric] = {
                "mean": statistics.fmean(values),
                "std": statistics.stdev(values) if len(values) > 1 else 0.0,
                "median": statistics.median(values),
                "q1": quartiles[0], "q3": quartiles[2], "valid_runs": len(values),
            }
    (output / "aggregate_summary.json").write_text(json.dumps(aggregate, ensure_ascii=False, indent=2), "utf-8")
    _write_csv(
        output / "aggregate_summary.csv",
        ["algorithm", "metric", "mean", "std", "median", "q1", "q3", "valid_runs"],
        ((algorithm, metric, row["mean"], row["std"], row["median"], row["q1"], row["q3"], row["valid_runs"]) for algorithm, metrics in aggregate.items() for metric, row in metrics.items()),
        replace_existing=True,
    )
    summary["aggregate"] = aggregate
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), "utf-8")
    return summary
