"""静态实验使用的HV、IGD、Spacing、C指标。"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence

from .multiobjective import dominates, pareto_indices


Point = tuple[float, ...]


def _rows(values: Sequence[Sequence[float]]) -> list[Point]:
    if not values or not values[0]:
        raise ValueError("目标矩阵不能为空")
    width = len(values[0])
    rows = [tuple(float(value) for value in row) for row in values]
    if any(len(row) != width for row in rows):
        raise ValueError("目标矩阵列数不一致")
    if any(not math.isfinite(value) for row in rows for value in row):
        raise ValueError("指标输入必须是有限实数")
    return rows


def normalize_groups(groups: Sequence[Sequence[Sequence[float]]]) -> tuple[tuple[Point, ...], ...]:
    """按MATLAB dif_main.m对同一比较组逐目标统一min-max归一化。"""
    if not groups:
        raise ValueError("比较组不能为空")
    checked = [_rows(group) for group in groups]
    width = len(checked[0][0])
    if any(len(group[0]) != width for group in checked):
        raise ValueError("各算法目标维数必须相同")
    merged = [row for group in checked for row in group]
    minimum = [min(row[i] for row in merged) for i in range(width)]
    maximum = [max(row[i] for row in merged) for i in range(width)]
    if any(high == low for low, high in zip(minimum, maximum)):
        raise ValueError("MATLAB min-max归一化遇到常量目标列")
    return tuple(
        tuple(tuple((value - minimum[i]) / (maximum[i] - minimum[i]) for i, value in enumerate(row)) for row in group)
        for group in checked
    )


def hypervolume_2d(points: Sequence[Sequence[float]], reference: Sequence[float] = (1.1, 1.1)) -> float:
    rows = _rows(points)
    if len(rows[0]) != 2 or len(reference) != 2:
        raise ValueError("该MATLAB入口仅使用二维HV")
    if any(any(value > bound for value, bound in zip(row, reference)) for row in rows):
        raise ValueError("HV参考点必须逐目标不优于全部解")
    upper_y = float(reference[1])
    measure = 0.0
    for x, y in sorted(rows, key=lambda row: row[0]):
        measure += (x - reference[0]) * (y - upper_y)
        upper_y = y
    return measure


def reference_front(points: Sequence[Sequence[float]]) -> tuple[Point, ...]:
    rows = _rows(points)
    unique = list(dict.fromkeys(rows))
    return tuple(unique[index] for index in pareto_indices(unique))


def igd(reference: Sequence[Sequence[float]], approximation: Sequence[Sequence[float]]) -> float:
    front = _rows(reference)
    candidate = _rows(approximation)
    if len(front[0]) != len(candidate[0]):
        raise ValueError("IGD两组目标维数不同")
    return sum(min(math.dist(point, other) for other in candidate) for point in front) / len(front)


def coverage(left: Sequence[Sequence[float]], right: Sequence[Sequence[float]]) -> float:
    a, b = _rows(left), _rows(right)
    if len(a[0]) != len(b[0]):
        raise ValueError("C指标两组目标维数不同")
    return sum(any(dominates(source, target) for source in a) for target in b) / len(b)


def spacing(points: Sequence[Sequence[float]]) -> float:
    rows = _rows(points)
    if len(rows) < 2:
        return 0.0
    nearest = [
        min(sum(abs(a - b) for a, b in zip(row, other)) for j, other in enumerate(rows) if i != j)
        for i, row in enumerate(rows)
    ]
    return statistics.stdev(nearest)


def rsi(components: Sequence[float], weights: Sequence[float] = (0.3333, 0.3333, 0.3333)) -> float:
    """论文锁定权重的加权RSI；分指标归一化在比较组聚合阶段完成。"""
    if len(components) != 3 or len(weights) != 3:
        raise ValueError("RSI必须包含三个分指标和三个权重")
    return sum(float(value) * float(weight) for value, weight in zip(components, weights))
