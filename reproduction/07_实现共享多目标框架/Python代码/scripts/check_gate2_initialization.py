"""检查Gate 2中属于第5步的染色体与初始化范围。"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from python_baseline.dfjspt.chromosome import Chromosome
from python_baseline.dfjspt.data import load_experiment_input
from python_baseline.dfjspt.initialization import hybrid_population, random_population


def check_initialization(population_size: int = 100) -> dict[str, object]:
    data_root = REPO_ROOT / "python_baseline" / "data"
    valid_instances = 0
    for index in range(1, 11):
        data = load_experiment_input(
            data_root / "brandimarte" / f"Mk{index:02d}.fjs",
            data_root / "resources" / "static_algorithm_comparison.json",
        )
        for population in (
            hybrid_population(data, population_size, 4, random.Random(1000 + index)),
            random_population(data, population_size, 4, random.Random(2000 + index)),
        ):
            for chromosome in population.chromosomes:
                chromosome.validate(data.instance, data.agv.count, 4)
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
        "当前已完成范围": "五段编码、MATLAB边界转换、纯随机初始化、40/30/30混合初始化、交叉、变异",
        "结论": "第5步范围通过",
        "Python合法实例数": valid_instances,
        "每实例每种初始化种群规模": population_size,
        "MATLAB参照实例": "Mk05",
        "MATLAB参照种子": matlab["seed"],
        "MATLAB参照合法染色体数": matlab_valid,
        "Gate2全部通过": False,
        "Gate2尚缺": ["N1-N6邻域算子"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="检查第5步对应的Gate 2范围")
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
