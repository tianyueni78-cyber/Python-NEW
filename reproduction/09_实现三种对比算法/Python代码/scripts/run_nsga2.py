"""运行第9步NSGA-II对比入口。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from python_baseline.dfjspt.data import load_experiment_input
from python_baseline.dfjspt.nsga2 import run_nsga2


def main() -> None:
    parser = argparse.ArgumentParser(description="运行NSGA-II对比算法")
    parser.add_argument("--instance", default="Mk05")
    parser.add_argument("--population", type=int, default=100)
    parser.add_argument("--generations", type=int)
    parser.add_argument("--time-limit", type=float)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data_root = REPO_ROOT / "python_baseline" / "data"
    data = load_experiment_input(
        data_root / "brandimarte" / f"{args.instance}.fjs",
        data_root / "resources" / "static_algorithm_comparison.json",
    )
    result = run_nsga2(
        data, population_size=args.population, generations=args.generations,
        time_limit_seconds=args.time_limit, seed=args.seed
    )
    payload = {
        "算法": "NSGA-II", "实例": args.instance, "随机种子": args.seed,
        "完成代数": result.generations, "评价次数": result.evaluations,
        "Pareto目标": [list(row) for row in result.pareto_objectives],
        "Pareto染色体_MATLAB_1起始": [row.to_matlab_row() for row in result.pareto_chromosomes],
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
