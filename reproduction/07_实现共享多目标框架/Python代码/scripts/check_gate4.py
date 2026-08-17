"""检查Gate 4：共享多目标算子是否与MATLAB固定参照一致。"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from python_baseline.dfjspt.multiobjective import (
    environmental_select,
    matlab_order,
    tournament_winner,
)
from python_baseline.dfjspt.chromosome import Chromosome
from python_baseline.dfjspt.genetic import matlab_crossover, matlab_mutation


def _restore(values, infinite):
    return [
        [math.inf if marker else value for value, marker in zip(row, mask)]
        for row, mask in zip(values, infinite)
    ]


def _rows_match(actual, expected, tolerance=1e-12):
    if len(actual) != len(expected):
        return False
    for actual_row, expected_row in zip(actual, expected):
        if len(actual_row) != len(expected_row):
            return False
        for left, right in zip(actual_row, expected_row):
            if math.isinf(right):
                if not math.isinf(left):
                    return False
            elif abs(left - right) > tolerance:
                return False
    return True


def check_gate4() -> dict[str, object]:
    reference_path = (
        REPO_ROOT
        / "python_baseline"
        / "data"
        / "matlab_reference"
        / "multiobjective_step7.json"
    )
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    objectives = reference["objectives"]
    qnsga_actual = matlab_order(objectives, True)
    nsga_actual = matlab_order(objectives, False)
    qnsga_expected = _restore(
        reference["qnsga_sorted"], reference["qnsga_sorted_infinite"]
    )
    nsga_expected = _restore(
        reference["nsga_ranked"], reference["nsga_ranked_infinite"]
    )

    ranks_match = [row[2] for row in qnsga_actual] == [
        row[2] for row in qnsga_expected
    ] and [row[2] for row in nsga_actual] == [row[2] for row in nsga_expected]
    crowding_match = _rows_match(qnsga_actual, qnsga_expected) and _rows_match(
        nsga_actual, nsga_expected
    )

    selected = environmental_select(objectives, reference["population_size"])
    selected_objectives = [objectives[index] for index in selected]
    qnsga_elite = [row[:2] for row in reference["qnsga_elite"]]
    nsga_elite = [row[:2] for row in reference["nsga_elite"]]
    elite_match = selected_objectives == qnsga_elite and sorted(
        selected_objectives
    ) == sorted(nsga_elite)

    ordered_ranks = [row[2] for row in qnsga_actual]
    ordered_crowding = [row[3] for row in qnsga_actual]
    winners = [
        tournament_winner(
            ordered_ranks,
            ordered_crowding,
            [candidate - 1 for candidate in pair],
        )
        + 1
        for pair in reference["candidate_pairs"]
    ]
    tournament_match = (
        winners == reference["tournament_winners_matlab_1_based"]
    )
    operation_count = len(reference["genetic_parent_rows"][0]) // 5
    parents = [
        Chromosome.from_matlab_row(row, operation_count)
        for row in reference["genetic_parent_rows"]
    ]
    children = matlab_crossover(
        parents[0],
        parents[1],
        {job - 1 for job in reference["selected_jobs_matlab_1_based"]},
        [
            position - 1
            for position in reference["selected_rs_positions_matlab_1_based"]
        ],
    )
    crossover_match = [child.to_matlab_row() for child in children] == reference[
        "crossover_children"
    ]
    mutated = matlab_mutation(
        children[0],
        tuple(
            position - 1
            for position in reference["mutation_os_positions_matlab_1_based"]
        ),
        {
            position - 1: value - 1
            for position, value in zip(
                reference["mutation_rs_positions_matlab_1_based"],
                reference["mutation_rs_values_matlab_1_based"],
            )
        },
    )
    mutation_match = mutated.to_matlab_row() == reference["mutated_child"]
    passed = all(
        (
            ranks_match,
            crowding_match,
            elite_match,
            tournament_match,
            crossover_match,
            mutation_match,
        )
    )
    return {
        "Gate": "Gate 4：多目标算子一致",
        "结论": "通过" if passed else "未通过",
        "固定目标行数": len(objectives),
        "非支配等级一致": ranks_match,
        "拥挤距离一致": crowding_match,
        "QNSGA-II与NSGA-II中间顺序均已核查": True,
        "精英保留一致": elite_match,
        "锦标赛判优一致": tournament_match,
        "固定交叉一致": crossover_match,
        "固定变异一致": mutation_match,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="检查Gate 4")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = check_gate4()
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    if report["结论"] != "通过":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
