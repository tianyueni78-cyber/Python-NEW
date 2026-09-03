"""运行一次可追溯的静态QNSGA-II A0实验。"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
BASELINE = REPO / "paper_static_baseline"
CONFIG = BASELINE / "config" / "paper_static_v1.json"
RESOURCE = BASELINE / "data" / "resources" / "static_algorithm_comparison.json"
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from paper_static_baseline.dfjspt.data import load_experiment_input
from paper_static_baseline.dfjspt.qnsga2 import run_qnsga2


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True,
        encoding="utf-8", check=True,
    )
    return completed.stdout.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", required=True, choices=[f"Mk{i:02d}" for i in range(1, 11)])
    parser.add_argument("--population", required=True, type=int)
    parser.add_argument("--generations", required=True, type=int)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = parse_args()
    if args.population <= 0 or args.population % 10:
        print("种群规模必须为正数且能被10整除，以保持40/30/30初始化比例。", file=sys.stderr)
        return 2
    if args.generations <= 0:
        print("迭代代数必须为正数。", file=sys.stderr)
        return 2
    if args.output.exists():
        print(f"输出目录已存在：{args.output}", file=sys.stderr)
        return 2

    args.output.mkdir(parents=True)
    instance_path = BASELINE / "data" / "brandimarte" / f"{args.instance}.fjs"
    manifest = {
        "algorithm": "A0-QNSGA-II",
        "config_sha256": sha256(CONFIG),
        "generations": args.generations,
        "instance": args.instance,
        "instance_sha256": sha256(instance_path),
        "population": args.population,
        "python_version": sys.version.split()[0],
        "seed": args.seed,
        "source_commit": source_commit(),
    }
    try:
        data = load_experiment_input(instance_path, RESOURCE)
        result = run_qnsga2(
            data,
            population_size=args.population,
            generations=args.generations,
            seed=args.seed,
        )
        manifest.update({
            "chromosomes_matlab_1_based": [row.to_matlab_row() for row in result.pareto_chromosomes],
            "full_decode_evaluations": result.evaluations,
            "pareto_objectives": result.pareto_objectives,
            "qtable": result.qtable,
            "status": "completed",
            "trajectory_average": result.curve_average,
            "trajectory_minimum": result.curve_min,
        })
        return_code = 0
    except KeyboardInterrupt:
        manifest.update({"status": "interrupted", "error_type": "KeyboardInterrupt"})
        return_code = 130
    except Exception as error:
        manifest.update({
            "status": "failed",
            "error_type": type(error).__name__,
            "error_message": str(error),
        })
        return_code = 1
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if return_code:
        print(f"运行未完成，记录见：{args.output / 'manifest.json'}", file=sys.stderr)
    else:
        print(args.output / "manifest.json")
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
