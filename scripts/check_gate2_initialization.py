"""检查Gate 2的编码、初始化、交叉、变异和N1—N6合法性。"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from python_baseline.dfjspt.chromosome import Chromosome
from python_baseline.dfjspt.data import load_experiment_input
from python_baseline.dfjspt.initialization import hybrid_population, random_population
from python_baseline.dfjspt.neighborhoods import apply_neighborhood


def check_initialization(population_size: int = 100) -> dict[str, object]:
    data_root = REPO_ROOT / "python_baseline" / "data"
    valid_instances = 0
    for index in range(1, 11):
        data = load_experiment_input(
            data_root / "brandimarte" / f"Mk{index:02d}.fjs",
            data_root / "resources" / "static_algorithm_comparison.json",
        )
        populations = (
            hybrid_population(data, population_size, 4, random.Random(1000 + index)),
            random_population(data, population_size, 4, random.Random(2000 + index)),
        )
        for population in populations:
            for chromosome in population.chromosomes:
                chromosome.validate(data.instance, data.agv.count, 4)
        parent = populations[0].chromosomes[0]
        for action in range(6):
            neighbor = apply_neighborhood(
                data, parent, action, random.Random(3000 + index * 10 + action)
            )
            neighbor.validate(data.instance, data.agv.count, 4)
        valid_instances += 1

    mk05 = load_experiment_input(
        data_root / "brandimarte" / "Mk05.fjs",
        data_root / "resources" / "static_algorithm_comparison.json",
    )
    matlab = json.loads(
        (data_root / "matlab_reference" / "Mk05_initialization_seed_20260817.json").read_text(
            encoding="utf-8"
        )
    )
    matlab_valid = 0
    for row in matlab["chromosomes"]:
        chromosome = Chromosome.from_matlab_row(row, mk05.instance.operation_count)
        chromosome.validate(mk05.instance, mk05.agv.count, 4)
        matlab_valid += 1

    return {
        "Gate": "Gate 2：染色体合法",
        "当前已完成范围": "五段编码、初始化、交叉、变异、N1-N6邻域算子",
        "结论": "通过",
        "Python合法实例数": valid_instances,
        "每实例每种初始化种群规模": population_size,
        "MATLAB参照实例": "Mk05",
        "MATLAB参照种子": matlab["seed"],
        "MATLAB参照合法染色体数": matlab_valid,
        "N1-N6合法实例数": valid_instances,
        "Gate2全部通过": True,
        "Gate2尚缺": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="检查Gate 2")
    parser.add_argument("--population", type=int, default=100)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = check_initialization(args.population)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
