"""与静态MATLAB主链一致的共享多目标基础操作。"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence


ObjectiveRow = Sequence[float]


def _validated(objectives: Sequence[ObjectiveRow]) -> list[tuple[float, ...]]:
    if not objectives:
        raise ValueError("目标矩阵不能为空")
    width = len(objectives[0])
    if width == 0:
        raise ValueError("目标矩阵必须至少包含一列")
    rows = [tuple(float(value) for value in row) for row in objectives]
    if any(len(row) != width for row in rows):
        raise ValueError("目标矩阵各行长度必须一致")
    if any(not math.isfinite(value) for row in rows for value in row):
        raise ValueError("目标值必须为有限实数")
    return rows


def dominates(left: ObjectiveRow, right: ObjectiveRow) -> bool:
    """当且仅当left按最小化Pareto规则严格支配right。"""
    if len(left) == 0 or len(left) != len(right):
        raise ValueError("比较目标必须非空且维数相同")
    return all(a <= b for a, b in zip(left, right)) and any(
        a < b for a, b in zip(left, right)
    )


def rank_and_crowding(
    objectives: Sequence[ObjectiveRow],
) -> tuple[list[int], list[float]]:
    """返回与输入行对齐、从1开始的rank和MATLAB式拥挤距离。"""
    rows = _validated(objectives)
    size = len(rows)
    domination_counts = [0] * size
    dominated_sets: list[list[int]] = [[] for _ in rows]
    fronts: list[list[int]] = [[]]

    for i, left in enumerate(rows):
        for j, right in enumerate(rows):
            if dominates(left, right):
                dominated_sets[i].append(j)
            elif dominates(right, left):
                domination_counts[i] += 1
        if domination_counts[i] == 0:
            fronts[0].append(i)

    ranks = [0] * size
    front_number = 1
    while fronts[-1]:
        next_front: list[int] = []
        for index in fronts[-1]:
            ranks[index] = front_number
            for dominated_index in dominated_sets[index]:
                domination_counts[dominated_index] -= 1
                if domination_counts[dominated_index] == 0:
                    next_front.append(dominated_index)
        fronts.append(next_front)
        front_number += 1

    crowding = [0.0] * size
    for front in fronts[:-1]:
        for objective_index in range(len(rows[0])):
            ordered = sorted(front, key=lambda index: rows[index][objective_index])
            crowding[ordered[0]] = math.inf
            crowding[ordered[-1]] = math.inf
            minimum = rows[ordered[0]][objective_index]
            maximum = rows[ordered[-1]][objective_index]
            for position in range(1, len(ordered) - 1):
                index = ordered[position]
                if maximum == minimum:
                    crowding[index] = math.inf
                elif not math.isinf(crowding[index]):
                    previous_value = rows[ordered[position - 1]][objective_index]
                    next_value = rows[ordered[position + 1]][objective_index]
                    crowding[index] += (next_value - previous_value) / (
                        maximum - minimum
                    )
    return ranks, crowding


def matlab_order(
    objectives: Sequence[ObjectiveRow], order_within_front: bool
) -> list[list[float]]:
    """复现两份MATLAB non_domination.m的可观察返回顺序。"""
    rows = _validated(objectives)
    ranks, crowding = rank_and_crowding(rows)
    indices = sorted(range(len(rows)), key=lambda index: ranks[index])
    if order_within_front:
        ordered: list[int] = []
        for rank in range(1, max(ranks) + 1):
            front = [index for index in indices if ranks[index] == rank]
            ordered.extend(sorted(front, key=lambda index: crowding[index], reverse=True))
        indices = ordered
    return [list(rows[index]) + [ranks[index], crowding[index]] for index in indices]


def environmental_select(
    objectives: Sequence[ObjectiveRow], population_size: int
) -> list[int]:
    """按rank依次保留，截断前沿按拥挤距离降序选择。"""
    rows = _validated(objectives)
    if population_size <= 0 or population_size > len(rows):
        raise ValueError("种群规模必须为正且不能超过候选数量")
    ranks, crowding = rank_and_crowding(rows)
    selected: list[int] = []
    for rank in range(1, max(ranks) + 1):
        front = [index for index, value in enumerate(ranks) if value == rank]
        remaining = population_size - len(selected)
        if len(front) <= remaining:
            selected.extend(front)
        else:
            selected.extend(
                sorted(front, key=lambda index: crowding[index], reverse=True)[:remaining]
            )
            break
        if len(selected) == population_size:
            break
    return selected


def tournament_winner(
    ranks: Sequence[int], crowding: Sequence[float], candidates: Sequence[int]
) -> int:
    """复现MATLAB锦标赛的rank、拥挤距离和首个并列者规则。"""
    if len(ranks) != len(crowding) or not candidates:
        raise ValueError("rank、拥挤距离和候选索引不合法")
    if any(index < 0 or index >= len(ranks) for index in candidates):
        raise ValueError("候选索引越界")
    return min(candidates, key=lambda index: (ranks[index], -crowding[index]))


def tournament_selection(
    ranks: Sequence[int],
    crowding: Sequence[float],
    pool_size: int,
    tournament_size: int,
    rng: random.Random,
) -> list[int]:
    """按MATLAB的round(pop*rand)采样不重复候选并返回胜者索引。"""
    population_size = len(ranks)
    if (
        population_size != len(crowding)
        or pool_size <= 0
        or tournament_size <= 0
        or tournament_size > population_size
    ):
        raise ValueError("锦标赛规模参数不合法")
    winners: list[int] = []
    for _ in range(pool_size):
        candidates: list[int] = []
        while len(candidates) < tournament_size:
            candidate = max(
                1, math.floor(population_size * rng.random() + 0.5)
            ) - 1
            if candidate not in candidates:
                candidates.append(candidate)
        winners.append(tournament_winner(ranks, crowding, candidates))
    return winners


def pareto_indices(objectives: Sequence[ObjectiveRow]) -> list[int]:
    """返回rank为1的输入行索引；与MATLAB一样保留重复目标行。"""
    ranks, _ = rank_and_crowding(objectives)
    return [index for index, rank in enumerate(ranks) if rank == 1]
