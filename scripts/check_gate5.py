"""检查Gate 5：N1—N6、Q-learning和完整主循环。"""

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
from python_baseline.dfjspt.neighborhoods import (
    n1_reinsert_reversed_pair,
    n2_remove_and_reinsert,
    n6_waiting_agv_reassignment,
    replace_agv_gene,
    replace_machine_gene,
)
from python_baseline.dfjspt.qlearning import assign_states, reward_value, update_q
from python_baseline.dfjspt.qnsga2 import run_qnsga2


def check_gate5() -> dict[str, object]:
    data_root = REPO_ROOT / "python_baseline" / "data"
    reference = json.loads(
        (data_root / "matlab_reference" / "qnsga_step8.json").read_text(
            encoding="utf-8"
        )
    )
    data = load_experiment_input(
        data_root / "brandimarte" / "Mk05.fjs",
        data_root / "resources" / "static_algorithm_comparison.json",
    )
    parent = Chromosome.from_matlab_row(
        reference["chromosome"], data.instance.operation_count
    )
    expected = {item["strategy"]: item["chromosome"] for item in reference["neighborhoods"]}
    actual = {
        "N1": n1_reinsert_reversed_pair(parent, 96, 91),
        "N2": n2_remove_and_reinsert(parent, (59, 35), 81),
        "N3": replace_machine_gene(parent, 93, 1),
        "N4": replace_machine_gene(parent, 9, 0),
        "N5": replace_agv_gene(parent, 103, 3),
        "N6": n6_waiting_agv_reassignment(data, parent, random.Random(1)),
    }
    neighborhoods_match = all(
        chromosome.to_matlab_row() == expected[name]
        for name, chromosome in actual.items()
    )
    states, time_median, energy_median = assign_states(reference["state_objectives"])
    states_match = (
        states == [value - 1 for value in reference["states"]]
        and time_median == reference["time_median"]
        and energy_median == reference["energy_median"]
    )
    rewards = [
        reward_value(
            reference["reward_old_objective"],
            new,
            reference["reward_maximum"],
            reference["reward_minimum"],
        )
        for new in reference["reward_new_objectives"]
    ]
    rewards_match = rewards == reference["rewards"]
    qtable = [[0.0] * 6 for _ in range(4)]
    qtable[1] = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    update_q(qtable, 0, 2, rewards[0], 1, 0.1, 0.9)
    q_update_match = qtable == reference["updated_qtable"]
    small_data = load_experiment_input(
        data_root / "brandimarte" / "Mk01.fjs",
        data_root / "resources" / "static_algorithm_comparison.json",
    )
    result = run_qnsga2(small_data, population_size=10, generations=2, seed=20260817)
    q_updated = any(value != 0 for row in result.qtable for value in row)
    passed = all((neighborhoods_match, states_match, rewards_match, q_update_match, q_updated))
    return {
        "Gate": "Gate 5：Q-learning行为正确",
        "结论": "通过" if passed else "未通过",
        "N1-N6固定参考一致": neighborhoods_match,
        "四状态与中位数边界一致": states_match,
        "三类奖励一致": rewards_match,
        "Q更新公式一致": q_update_match,
        "Q表已更新": q_updated,
        "完整主循环可运行": bool(result.pareto_objectives),
        "小规模运行评价次数": result.evaluations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="检查Gate 5")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = check_gate5()
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    if report["结论"] != "通过":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
