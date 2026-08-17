"""第14步论文动态场景清单与可恢复运行。"""

from __future__ import annotations

import json
import csv
import platform
import statistics
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .data import load_dynamic_experiment_input
from .decoder import decode_static
from .dynamic import DynamicEvent, execute_is, execute_rescheduling
from .experiments import paired_seed
from .metrics import dynamic_rsi_components, rsi
from .qnsga2 import run_qnsga2


@dataclass(frozen=True)
class DynamicScenario:
    scenario_id: str
    kind: str
    instance: str
    event_time: float
    target: int
    duration: float


def formal_dynamic_scenarios() -> list[DynamicScenario]:
    scenarios = [
        DynamicScenario("OC_Mk02_t20", "order_cancellation", "Mk02", 20, 2, 0),
        DynamicScenario("OC_Mk02_t50", "order_cancellation", "Mk02", 50, 2, 0),
        DynamicScenario("OC_Mk07_t50", "order_cancellation", "Mk07", 50, 2, 0),
        DynamicScenario("OC_Mk07_t100", "order_cancellation", "Mk07", 100, 2, 0),
    ]
    for instance, times, durations in (
        ("Mk01", (20, 50), (5, 10)),
        ("Mk06", (100, 200), (15, 25)),
    ):
        scenarios.extend(
            DynamicScenario(
                f"MF_{instance}_t{moment}_d{duration}", "machine_failure",
                instance, moment, 2, duration,
            )
            for moment in times for duration in durations
        )
    for instance, times, durations in (
        ("Mk04", (20, 50), (5, 10)),
        ("Mk10", (200, 300), (15, 25)),
    ):
        scenarios.extend(
            DynamicScenario(
                f"AF_{instance}_t{moment}_d{duration}", "agv_failure",
                instance, moment, 1, duration,
            )
            for moment in times for duration in durations
        )
    return scenarios


def _git_commit(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True,
    ).stdout.strip()


def run_dynamic_batch(
    scenarios: list[DynamicScenario], repeats: list[int], output: Path,
    data_root: Path, *, population_size: int = 100, generations: int = 200,
) -> int:
    """逐场景保存初始解和IS/RS/CS原始结果；已有成功目录直接跳过。"""
    output.mkdir(parents=True, exist_ok=True)
    repo_root = Path(__file__).resolve().parents[2]
    commit = _git_commit(repo_root)
    base_resource = data_root / "resources" / "static_algorithm_comparison.json"
    profile = data_root / "resources" / "dynamic_event_profiles.json"
    completed = 0
    for scenario in scenarios:
        for repeat in repeats:
            seed = paired_seed(scenario.scenario_id, repeat)
            run_id = f"{scenario.scenario_id}_r{repeat:02d}_s{seed}"
            folder = output / run_id
            result_path = folder / "result.json"
            if result_path.exists():
                payload = json.loads(result_path.read_text("utf-8"))
                if payload.get("status") == "success":
                    completed += 1
                    continue
                raise RuntimeError(f"存在失败运行，请保留证据并单独处理：{run_id}")
            folder.mkdir()
            config = {
                **asdict(scenario), "repeat": repeat, "seed": seed,
                "population_size": population_size, "generations": generations,
                "git_commit": commit, "python": platform.python_version(),
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            (folder / "config.json").write_text(
                json.dumps(config, ensure_ascii=False, indent=2), "utf-8"
            )
            started = time.perf_counter()
            try:
                data = load_dynamic_experiment_input(
                    data_root / "brandimarte" / f"{scenario.instance}.fjs",
                    base_resource, profile, scenario.kind,
                )
                initial_started = time.perf_counter()
                initial = run_qnsga2(
                    data, population_size=population_size,
                    generations=generations, seed=seed,
                )
                initial_elapsed = time.perf_counter() - initial_started
                chromosome = initial.pareto_chromosomes[0]
                original = decode_static(data, chromosome)
                event = DynamicEvent(
                    scenario.kind, scenario.event_time, scenario.target,
                    scenario.duration,
                )
                is_schedule = execute_is(data, chromosome, original, event)
                budget = initial_elapsed / 2
                strategy_payload = {
                    "IS": [{
                        "objective": [is_schedule.makespan, is_schedule.machine_energy],
                        "agv_energy": is_schedule.agv_energy,
                        "rsi_components": dynamic_rsi_components(
                            original, is_schedule, data.instance.operation_count
                        ),
                    }],
                }
                strategy_payload["IS"][0]["rsi_raw"] = rsi(
                    strategy_payload["IS"][0]["rsi_components"]
                )
                for strategy in ("RS", "CS"):
                    result = execute_rescheduling(
                        data, chromosome, original, event, strategy,
                        population_size=population_size, generations=generations,
                        seed=seed, time_limit_seconds=budget,
                    )
                    rows = []
                    for objective, schedule, candidate in zip(
                        result.pareto_objectives[:10], result.pareto_schedules[:10],
                        result.pareto_chromosomes[:10],
                    ):
                        components = dynamic_rsi_components(
                            original, schedule, data.instance.operation_count
                        )
                        rows.append({
                            "objective": objective,
                            "agv_energy": schedule.agv_energy,
                            "rsi_components": components,
                            "rsi_raw": rsi(components),
                            "chromosome_matlab": candidate.to_matlab_row(),
                        })
                    strategy_payload[strategy] = rows
                payload = {
                    "status": "success",
                    "elapsed_seconds": time.perf_counter() - started,
                    "initial_elapsed_seconds": initial_elapsed,
                    "rescheduling_budget_seconds": budget,
                    "initial_pareto_objectives": initial.pareto_objectives,
                    "selected_initial_chromosome_matlab": chromosome.to_matlab_row(),
                    "strategies": strategy_payload,
                }
                result_path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2), "utf-8"
                )
                completed += 1
            except Exception as error:
                result_path.write_text(json.dumps({
                    "status": "failed",
                    "elapsed_seconds": time.perf_counter() - started,
                    "error": repr(error),
                }, ensure_ascii=False, indent=2), "utf-8")
                raise
    summarize_dynamic(output)
    return completed


def summarize_dynamic(output: Path) -> dict[str, object]:
    rows: list[tuple[object, ...]] = []
    successful_runs = 0
    for result_path in sorted(output.glob("*/result.json")):
        result = json.loads(result_path.read_text("utf-8"))
        if result.get("status") != "success":
            continue
        successful_runs += 1
        config = json.loads((result_path.parent / "config.json").read_text("utf-8"))
        for strategy, solutions in result["strategies"].items():
            for solution_index, solution in enumerate(solutions, start=1):
                objective = solution["objective"]
                components = solution["rsi_components"]
                rows.append((
                    config["scenario_id"], config["kind"], config["instance"],
                    config["repeat"], strategy, solution_index,
                    objective[0], objective[1], solution["agv_energy"],
                    components[0], components[1], components[2],
                    solution.get("rsi_raw", rsi(components)),
                ))
    with (output / "dynamic_long.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "scenario_id", "kind", "instance", "repeat", "strategy", "solution",
            "makespan", "machine_energy", "agv_energy", "change_rate",
            "agv_efficiency", "apsd", "rsi_raw",
        ])
        writer.writerows(rows)
    grouped: dict[tuple[str, str], list[tuple[object, ...]]] = {}
    for row in rows:
        grouped.setdefault((str(row[0]), str(row[4])), []).append(row)
    aggregate = []
    for (scenario_id, strategy), group in sorted(grouped.items()):
        aggregate.append({
            "scenario_id": scenario_id,
            "strategy": strategy,
            "solutions": len(group),
            "makespan_mean": statistics.fmean(float(row[6]) for row in group),
            "machine_energy_mean": statistics.fmean(float(row[7]) for row in group),
            "rsi_raw_mean": statistics.fmean(float(row[12]) for row in group),
        })
    summary = {"successful_runs": successful_runs, "groups": aggregate}
    (output / "dynamic_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), "utf-8"
    )
    return summary
