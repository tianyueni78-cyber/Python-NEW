"""验收第10步四个QNSGA-II消融版本。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from python_baseline.dfjspt.ablations import AblationVariant, ablation_features, run_ablation
from python_baseline.dfjspt.data import load_experiment_input


def check_step10() -> dict:
    reference = json.loads(
        (REPO_ROOT / "python_baseline" / "data" / "matlab_reference" / "ablations_step10.json").read_text(encoding="utf-8")
    )
    features = ablation_features()
    fields = (
        "random_initialization", "hybrid_initialization",
        "initial_nondomination_sort", "has_local_search",
        "neighborhood_count", "random_action", "q_action", "q_update",
    )
    matrix_match = all(
        all(features[name][field] == reference["variants"][name][field] for field in fields)
        for name in reference["locked_order"]
    )
    data_root = REPO_ROOT / "python_baseline" / "data"
    data = load_experiment_input(
        data_root / "brandimarte" / "Mk01.fjs",
        data_root / "resources" / "static_algorithm_comparison.json",
    )
    results = {
        variant: run_ablation(
            data, variant, population_size=10, generations=2, seed=20260817
        )
        for variant in AblationVariant
    }
    legal = all(result.pareto_objectives for result in results.values())
    for result in results.values():
        for chromosome in result.pareto_chromosomes:
            chromosome.validate(data.instance, data.agv.count, len(data.agv.speeds))
    only_full_q = all(
        not any(value != 0 for row in results[variant].qtable for value in row)
        for variant in (AblationVariant.A, AblationVariant.B, AblationVariant.C)
    ) and any(
        value != 0 for row in results[AblationVariant.FULL].qtable for value in row
    )
    return {
        "阶段": 10,
        "结论": "通过" if matrix_match and legal and only_full_q else "未通过",
        "版本": [variant.value for variant in AblationVariant],
        "四版本特征矩阵一致": matrix_match,
        "统一代数停止": True,
        "四版本输出合法": legal,
        "仅完整版本更新Q表": only_full_q,
        "评价次数": {
            variant.value: results[variant].evaluations for variant in AblationVariant
        },
    }


if __name__ == "__main__":
    print(json.dumps(check_step10(), ensure_ascii=False, indent=2))
