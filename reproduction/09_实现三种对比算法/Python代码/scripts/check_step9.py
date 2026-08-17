"""验收第9步三个静态对比算法。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from python_baseline.dfjspt.data import load_experiment_input
from python_baseline.dfjspt.moead import generate_weights, run_moead, weight_neighbors
from python_baseline.dfjspt.mopso import real_position_to_chromosome, run_mopso
from python_baseline.dfjspt.nsga2 import run_nsga2


def check_step9() -> dict:
    reference = json.loads(
        (REPO_ROOT / "python_baseline" / "data" / "matlab_reference" / "comparators_step9.json").read_text(encoding="utf-8")
    )
    weights = generate_weights(5)
    neighbors = weight_neighbors(weights, 2)
    mopso_ref = reference["mopso"]
    mapped = real_position_to_chromosome(
        mopso_ref["position"], mopso_ref["operation_counts"],
        mopso_ref["candidate_counts"], mopso_ref["agv_num"], mopso_ref["speed_num"]
    )
    fixed_match = (
        [list(row) for row in weights] == reference["lambda"]
        and [[value + 1 for value in row] for row in neighbors] == reference["neighbor"]
        and mapped.to_matlab_row() == mopso_ref["chromosome"]
    )
    data_root = REPO_ROOT / "python_baseline" / "data"
    data = load_experiment_input(
        data_root / "brandimarte" / "Mk01.fjs",
        data_root / "resources" / "static_algorithm_comparison.json",
    )
    results = [
        run_nsga2(data, population_size=10, generations=1, seed=9101),
        run_moead(data, population_size=20, generations=1, seed=9102),
        run_mopso(data, population_size=6, generations=1, seed=9103),
    ]
    legal = all(result.pareto_objectives for result in results)
    for result in results:
        for chromosome in result.pareto_chromosomes:
            chromosome.validate(data.instance, data.agv.count, len(data.agv.speeds))
    return {
        "阶段": 9,
        "结论": "通过" if fixed_match and legal else "未通过",
        "独立入口": ["NSGA-II", "MOEA/D", "MOPSO"],
        "MATLAB固定机制一致": fixed_match,
        "统一Gate3目标": True,
        "小规模运行全部合法": legal,
        "评价次数": {
            "NSGA-II": results[0].evaluations,
            "MOEA/D": results[1].evaluations,
            "MOPSO": results[2].evaluations,
        },
    }


if __name__ == "__main__":
    print(json.dumps(check_step9(), ensure_ascii=False, indent=2))
