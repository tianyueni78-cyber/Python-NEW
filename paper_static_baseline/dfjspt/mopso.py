"""静态MATLAB对比算法MOPSO（含其活动VNS）。"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from typing import Sequence

from .chromosome import Chromosome
from .data import ExperimentInput
from .decoder import decode_static
from .multiobjective import dominates, rank_and_crowding
from .objectives import evaluate_objectives


Objective = tuple[float, float]
Position = tuple[float, ...]


@dataclass(frozen=True)
class MOPSOResult:
    pareto_chromosomes: tuple[Chromosome, ...]
    pareto_objectives: tuple[Objective, ...]
    curve_min: tuple[Objective, ...]
    curve_average: tuple[Objective, ...]
    evaluations: int
    generations: int
    seed: int


def _matlab_round_nonnegative(value: float) -> int:
    return math.floor(value + 0.5)


def real_position_to_chromosome(
    position: Sequence[float],
    operation_counts: Sequence[int],
    candidate_counts: Sequence[int],
    agv_count: int,
    speed_count: int,
) -> Chromosome:
    operation_count = sum(operation_counts)
    if len(position) != 5 * operation_count or len(candidate_counts) != operation_count:
        raise ValueError("MOPSO连续位置维数不合法")
    job_count = len(operation_counts)
    base_os = [job for job, count in enumerate(operation_counts) for _ in range(count)]
    ascending = sorted(range(operation_count), key=lambda index: position[index])
    inverse = sorted(range(operation_count), key=lambda index: ascending[index])
    os = tuple(base_os[index] for index in inverse)

    def map_gene(value: float, upper: int) -> int:
        matlab = _matlab_round_nonnegative(
            (value + job_count) / (2 * job_count) * (upper - 1) + 1
        )
        return min(upper, max(1, matlab)) - 1

    ms_start = operation_count
    as_start = 2 * operation_count
    ss_start = 3 * operation_count
    ms = tuple(map_gene(position[ms_start + i], candidate_counts[i]) for i in range(operation_count))
    agv = tuple(map_gene(position[as_start + i], agv_count) for i in range(operation_count))
    speed = tuple(map_gene(position[ss_start + i], speed_count) for i in range(2 * operation_count))
    return Chromosome(os, ms, agv, speed[::2], speed[1::2])


def domination_flags(objectives: Sequence[Sequence[float]]) -> tuple[bool, ...]:
    return tuple(
        any(i != j and dominates(other, objective) for j, other in enumerate(objectives))
        for i, objective in enumerate(objectives)
    )


def local_search_position(
    position: Sequence[float],
    operation_count: int,
    agv_count: int,
    action: int,
    rng: random.Random,
) -> Position:
    values = list(position)
    if action == 0:
        left = rng.randrange(operation_count - 1)
        pair = [values[left + 1], values[left]]
        del values[left : left + 2]
        insert = rng.randrange(1, operation_count - 1)
        values[insert:insert] = pair
    elif action == 1:
        selected = rng.sample(range(operation_count), 2)
        removed = [values[index] for index in selected]
        for index in sorted(selected, reverse=True):
            del values[index]
        insert = rng.randrange(1, operation_count - 1)
        values[insert:insert] = removed
    elif action == 2:
        index = 2 * operation_count + rng.randrange(operation_count)
        new_value = rng.randrange(1, agv_count + 1)
        while new_value == values[index]:
            new_value = rng.randrange(1, agv_count + 1)
        values[index] = float(new_value)
    else:
        raise ValueError("MOPSO活动VNS只包含N1-N3")
    return tuple(values)


def _evaluate(data: ExperimentInput, position: Sequence[float]) -> tuple[Objective, Chromosome]:
    chromosome = real_position_to_chromosome(
        position,
        data.instance.operation_counts,
        [len(operation.options) for job in data.instance.jobs for operation in job.operations],
        data.agv.count,
        len(data.agv.speeds),
    )
    decoded = decode_static(data, chromosome)
    return evaluate_objectives(decoded), chromosome


def _grid_indices(objectives: Sequence[Objective], grid_count: int) -> tuple[int, ...]:
    minimum = [min(row[column] for row in objectives) for column in range(2)]
    maximum = [max(row[column] for row in objectives) for column in range(2)]
    result = []
    for row in objectives:
        subs = []
        for column in range(2):
            if maximum[column] == minimum[column]:
                sub = 1
            else:
                step = (maximum[column] - minimum[column]) / grid_count
                sub = max(1, math.ceil((row[column] - minimum[column]) / step))
            subs.append(min(grid_count, sub))
        result.append(subs[0] + (subs[1] - 1) * grid_count)
    return tuple(result)


def _archive(
    positions: Sequence[Position], objectives: Sequence[Objective], capacity: int, grid_count: int
) -> tuple[list[Position], list[Objective]]:
    flags = domination_flags(objectives)
    kept_positions = [row for row, flag in zip(positions, flags) if not flag]
    kept_objectives = [row for row, flag in zip(objectives, flags) if not flag]
    if len(kept_positions) <= capacity:
        return kept_positions, kept_objectives
    crowding = [0.0] * len(kept_positions)
    for column in range(2):
        order = sorted(range(len(kept_positions)), key=lambda index: kept_objectives[index][column])
        span = kept_objectives[order[-1]][column] - kept_objectives[order[0]][column]
        for offset, index in enumerate(order):
            if offset == 0 or offset == len(order) - 1 or span == 0:
                crowding[index] = math.inf
            elif not math.isinf(crowding[index]):
                crowding[index] += (
                    kept_objectives[order[offset + 1]][column]
                    - kept_objectives[order[offset - 1]][column]
                ) / span
    keep = sorted(range(len(kept_positions)), key=lambda index: crowding[index], reverse=True)[:capacity]
    return [kept_positions[i] for i in keep], [kept_objectives[i] for i in keep]


def _leader_index(objectives: Sequence[Objective], grid_count: int, rng: random.Random) -> int:
    grids = _grid_indices(objectives, grid_count)
    occupied = sorted(set(grids))
    qualities = [10 / grids.count(grid) for grid in occupied]
    target = rng.random() * sum(qualities)
    cumulative = 0.0
    selected_grid = occupied[-1]
    for grid, quality in zip(occupied, qualities):
        cumulative += quality
        if target <= cumulative:
            selected_grid = grid
            break
    candidates = [index for index, grid in enumerate(grids) if grid == selected_grid]
    return rng.choice(candidates)


def _mutate_positions(
    positions: list[list[float]], lower: float, upper: float, progress: float, fraction: float, rng: random.Random
) -> None:
    size = len(positions)
    dimension = len(positions[0])
    base = size // 3
    remainder = size - 3 * base
    groups = [base, base, base]
    for index in range(remainder):
        groups[index] += 1
    first_end = groups[0]
    second_end = first_end + groups[1]
    uniform_count = _matlab_round_nonnegative(fraction * groups[1])
    for index in rng.sample(range(first_end, second_end), uniform_count):
        positions[index] = [rng.uniform(lower, upper) for _ in range(dimension)]
    nonuniform_count = _matlab_round_nonnegative((1 - progress) ** (5 * dimension) * groups[2])
    for index in rng.sample(range(second_end, size), nonuniform_count):
        positions[index] = [rng.uniform(lower, upper) for _ in range(dimension)]


def run_mopso(
    data: ExperimentInput,
    *,
    population_size: int = 100,
    generations: int | None = None,
    time_limit_seconds: float | None = None,
    seed: int,
    inertia: float = 0.4,
    cognitive: float = 2.0,
    social: float = 2.0,
    grid_count: int = 20,
    repository_capacity: int = 200,
    mutation_fraction: float = 0.4,
) -> MOPSOResult:
    if population_size < 3:
        raise ValueError("MOPSO种群规模至少为3")
    if (generations is None or generations <= 0) and (
        time_limit_seconds is None or time_limit_seconds <= 0
    ):
        raise ValueError("必须提供正的代数或CPU时间上限")
    rng = random.Random(seed)
    dimension = 5 * data.instance.operation_count
    lower = -float(data.instance.job_count)
    upper = float(data.instance.job_count)
    positions: list[Position] = [
        tuple(rng.uniform(lower, upper) for _ in range(dimension))
        for _ in range(population_size)
    ]
    velocities = [[0.0] * dimension for _ in range(population_size)]
    evaluated = [_evaluate(data, position) for position in positions]
    objectives = [row[0] for row in evaluated]
    evaluations = population_size
    personal_positions = positions.copy()
    personal_objectives = objectives.copy()
    flags = domination_flags(objectives)
    repository_positions, repository_objectives = _archive(
        [row for row, flag in zip(positions, flags) if not flag],
        [row for row, flag in zip(objectives, flags) if not flag],
        repository_capacity,
        grid_count,
    )
    max_velocity = (upper - lower) * 0.06
    curve_min: list[Objective] = []
    curve_average: list[Objective] = []
    generation = 0
    started = time.perf_counter()
    while (generations is None or generation < generations) and (
        time_limit_seconds is None or time.perf_counter() - started <= time_limit_seconds
    ):
        leader = repository_positions[_leader_index(repository_objectives, grid_count, rng)]
        moved: list[list[float]] = []
        for particle in range(population_size):
            row = []
            for gene in range(dimension):
                velocity = (
                    inertia * velocities[particle][gene]
                    + cognitive * rng.random() * (personal_positions[particle][gene] - positions[particle][gene])
                    + social * rng.random() * (leader[gene] - positions[particle][gene])
                )
                velocities[particle][gene] = max(-max_velocity, min(max_velocity, velocity))
                row.append(positions[particle][gene] + velocities[particle][gene])
            moved.append(row)
        if generations is not None:
            progress = generation / generations
        else:
            progress = min(1.0, (time.perf_counter() - started) / time_limit_seconds)
        _mutate_positions(moved, lower, upper, progress, mutation_fraction, rng)
        for particle, row in enumerate(moved):
            for gene, value in enumerate(row):
                if value > upper:
                    velocities[particle][gene] *= -1
                    row[gene] = upper
                elif value < lower:
                    velocities[particle][gene] *= -1
                    row[gene] = lower
        positions = [tuple(row) for row in moved]
        evaluated = [_evaluate(data, position) for position in positions]
        objectives = [row[0] for row in evaluated]
        evaluations += population_size
        repository_positions, repository_objectives = _archive(
            repository_positions + positions,
            repository_objectives + objectives,
            repository_capacity,
            grid_count,
        )
        better = [dominates(current, best) for current, best in zip(objectives, personal_objectives)]
        random_best = [
            not dominates(best, current) and rng.random() < 0.5
            for current, best in zip(objectives, personal_objectives)
        ]
        if sum(better) > 1:
            for index, update in enumerate(better):
                if update:
                    personal_positions[index] = positions[index]
                    personal_objectives[index] = objectives[index]
        if sum(random_best) > 1:
            for index, update in enumerate(random_best):
                if update:
                    personal_positions[index] = positions[index]
                    personal_objectives[index] = objectives[index]

        accepted_positions: list[Position] = []
        accepted_objectives: list[Objective] = []
        for position, old_objective in zip(positions, objectives):
            neighbor = local_search_position(
                position, data.instance.operation_count, data.agv.count, rng.randrange(3), rng
            )
            new_objective, _ = _evaluate(data, neighbor)
            evaluations += 1
            if not all(old <= new for old, new in zip(old_objective, new_objective)):
                accepted_positions.append(neighbor)
                accepted_objectives.append(new_objective)
        candidates = positions + accepted_positions
        candidate_objectives = objectives + accepted_objectives
        ranks, crowding = rank_and_crowding(candidate_objectives)
        order = sorted(range(len(candidates)), key=lambda index: (ranks[index], -crowding[index]))
        positions = [candidates[index] for index in order[:population_size]]
        curve_min.append(
            (min(row[0] for row in repository_objectives), min(row[1] for row in repository_objectives))
        )
        curve_average.append(
            tuple(sum(row[column] for row in repository_objectives) / len(repository_objectives) for column in range(2))
        )
        generation += 1

    unique: dict[Objective, Chromosome] = {}
    for position, objective in zip(repository_positions, repository_objectives):
        _, chromosome = _evaluate(data, position)
        unique.setdefault(objective, chromosome)
    ordered = tuple(sorted(unique))
    return MOPSOResult(
        tuple(unique[row] for row in ordered), ordered, tuple(curve_min),
        tuple(curve_average), evaluations, generation, seed
    )
