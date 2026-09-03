"""完整QNSGA-II活动MATLAB路径中的Q-learning规则。"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from statistics import median


def epsilon(generation: int, maximum_generations: int) -> float:
    if maximum_generations <= 0:
        raise ValueError("最大代数必须为正")
    return 1.0 / (
        1.0 + math.exp(-((8.0 * (generation + 1) / maximum_generations) - 3.0))
    )


def state_of(objective: Sequence[float], time_median: float, energy_median: float) -> int:
    if objective[0] <= time_median:
        return 0 if objective[1] <= energy_median else 1
    return 2 if objective[1] <= energy_median else 3


def assign_states(
    objectives: Sequence[Sequence[float]],
) -> tuple[list[int], float, float]:
    if not objectives:
        raise ValueError("目标矩阵不能为空")
    time_median = median(row[0] for row in objectives)
    energy_median = median(row[1] for row in objectives)
    return (
        [state_of(row, time_median, energy_median) for row in objectives],
        float(time_median),
        float(energy_median),
    )


def reward_value(
    old: Sequence[float],
    new: Sequence[float],
    maximum: Sequence[float],
    minimum: Sequence[float],
) -> float:
    normalized = 0.0
    for value, upper, lower in zip(new, maximum, minimum):
        denominator = upper - lower
        if denominator == 0:
            term = math.nan if upper == value else math.copysign(math.inf, upper - value)
        else:
            term = (upper - value) / denominator
        normalized += term
    if all(new_value < old_value for new_value, old_value in zip(new, old)):
        return 2.0 + normalized
    if all(new_value > old_value for new_value, old_value in zip(new, old)):
        return 0.0
    return 1.0 + normalized


def select_action(
    qtable: Sequence[Sequence[float]],
    current_state: int,
    epsilon_value: float,
    rng: random.Random,
) -> int:
    row = qtable[current_state]
    if rng.random() > epsilon_value or all(value == 0 for value in row):
        return rng.randrange(len(row))
    return max(range(len(row)), key=lambda index: row[index])


def update_q(
    qtable: list[list[float]],
    current_state: int,
    action: int,
    reward: float,
    next_state: int,
    alpha: float,
    gamma: float,
) -> None:
    current = qtable[current_state][action]
    target = reward + gamma * max(qtable[next_state])
    qtable[current_state][action] = current + alpha * (target - current)
