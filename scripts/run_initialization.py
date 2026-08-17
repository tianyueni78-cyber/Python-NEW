"""独立运行第5步染色体初始化。"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from python_baseline.dfjspt.data import load_experiment_input
from python_baseline.dfjspt.initialization import hybrid_population, random_population


def create_initialization_result(
    instance_name: str,
    mode: str,
    population_size: int,
    speed_count: int,
    seed: int,
) -> dict[str, object]:
    if not re.fullmatch(r"Mk(?:0[1-9]|10)", instance_name):
        raise ValueError("实例名称必须是 Mk01—Mk10")
    data_root = REPO_ROOT / "python_baseline" / "data"
    data = load_experiment_input(
        data_root / "brandimarte" / f"{instance_name}.fjs",
        data_root / "resources" / "static_algorithm_comparison.json",
    )
    rng = random.Random(seed)
    if mode == "hybrid":
        population = hybrid_population(data, population_size, speed_count, rng)
    elif mode == "random":
        population = random_population(data, population_size, speed_count, rng)
    else:
        raise ValueError("初始化模式只能是 hybrid 或 random")
    return {
        "instance": instance_name,
        "mode": mode,
        "seed": seed,
        "population_size": len(population),
        "operation_count": data.instance.operation_count,
        "chromosome_length": 5 * data.instance.operation_count,
        "origins": list(population.origins),
        "chromosomes_matlab_1_based": [
            chromosome.to_matlab_row() for chromosome in population.chromosomes
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="生成DFJSP-T初始染色体种群")
    parser.add_argument("--instance", default="Mk05")
    parser.add_argument("--mode", choices=("hybrid", "random"), default="hybrid")
    parser.add_argument("--population", type=int, default=100)
    parser.add_argument("--speed-count", type=int, default=4)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = create_initialization_result(
        args.instance, args.mode, args.population, args.speed_count, args.seed
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"已生成 {result['instance']} 的 {result['population_size']} 条染色体："
        f"{result['chromosome_length']} 列，seed={result['seed']}"
    )


if __name__ == "__main__":
    main()
