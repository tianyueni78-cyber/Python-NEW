"""运行第10步QNSGA-II具名消融版本。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from python_baseline.dfjspt.ablations import AblationVariant, run_ablation
from python_baseline.dfjspt.data import load_experiment_input


def create_result(
    instance: str, variant: str, population: int, generations: int, seed: int
) -> dict:
    data_root = REPO_ROOT / "python_baseline" / "data"
    data = load_experiment_input(
        data_root / "brandimarte" / f"{instance}.fjs",
        data_root / "resources" / "static_algorithm_comparison.json",
    )
    result = run_ablation(
        data,
        AblationVariant(variant),
        population_size=population,
        generations=generations,
        seed=seed,
    )
    return {
        "算法": f"QNSGA-II消融-{variant}",
        "实例": instance,
        "种群规模": population,
        "代数": result.generations,
        "随机种子": seed,
        "评价次数": result.evaluations,
        "Pareto目标": [list(row) for row in result.pareto_objectives],
        "Pareto染色体_MATLAB_1起始": [
            row.to_matlab_row() for row in result.pareto_chromosomes
        ],
        "Q表": [list(row) for row in result.qtable],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="运行QNSGA-II消融版本")
    parser.add_argument("--instance", default="Mk05")
    parser.add_argument("--variant", choices=[item.value for item in AblationVariant], required=True)
    parser.add_argument("--population", type=int, default=100)
    parser.add_argument("--generations", type=int, default=200)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = create_result(
        args.instance, args.variant, args.population, args.generations, args.seed
    )
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
