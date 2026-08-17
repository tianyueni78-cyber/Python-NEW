"""静态MATLAB对比算法MOEA/D。"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from typing import Sequence

from .chromosome import Chromosome
from .data import ExperimentInput
from .decoder import decode_static
from .genetic import matlab_crossover, matlab_mutation
from .initialization import random_population
from .multiobjective import rank_and_crowding


Objective = tuple[float, float]


@dataclass(frozen=True)
class MOEADResult:
    pareto_chromosomes: tuple[Chromosome, ...]
    pareto_objectives: tuple[Objective, ...]
    curve_min: tuple[Objective, ...]
    curve_average: tuple[Objective, ...]
    evaluations: int
    generations: int
    seed: int


def generate_weights(population_size: int) -> tuple[Objective, ...]:
    if population_size < 2:
        raise ValueError("MOEA/D种群规模至少为2")
    return tuple(
        (index / (population_size - 1), 1 - index / (population_size - 1))
        for index in range(population_size)
    )


def weight_neighbors(weights: Sequence[Sequence[float]], size: int) -> tuple[tuple[int, ...], ...]:
    if size <= 0 or size > len(weights):
        raise ValueError("邻域规模不合法")
    return tuple(
        tuple(
            sorted(
                range(len(weights)),
                key=lambda other: math.dist(weight, weights[other]),
            )[:size]
        )
        for weight in weights
    )


def reciprocal_tchebycheff(
    objective: Sequence[float], weight: Sequence[float], ideal: Sequence[float]
) -> float:
    if len(objective) != len(weight) or len(weight) != len(ideal):
        raise ValueError("目标、权重与理想点维数必须一致")
    return max(
        abs(value - best) / (component if component != 0 else 1e-5)
        for value, component, best in zip(objective, weight, ideal)
    )


def replacement_mask(
    objectives: Sequence[Sequence[float]],
    offspring: Sequence[float],
    neighbors: Sequence[int],
    weights: Sequence[Sequence[float]],
    ideal: Sequence[float],
) -> tuple[int, ...]:
    return tuple(
        index
        for index in neighbors
        if reciprocal_tchebycheff(offspring, weights[index], ideal)
        <= reciprocal_tchebycheff(objectives[index], weights[index], ideal)
    )


def _evaluate(data: ExperimentInput, chromosome: Chromosome) -> Objective:
    result = decode_static(data, chromosome)
    return result.makespan, result.machine_energy


def _variation_pair(
    first: Chromosome,
    second: Chromosome,
    data: ExperimentInput,
    crossover_probability: float,
    mutation_probability: float,
    rng: random.Random,
) -> tuple[Chromosome, ...]:
    operation_count = data.instance.operation_count
    rs_upper = [
        *(len(operation.options) for job in data.instance.jobs for operation in job.operations),
        *([data.agv.count] * operation_count),
        *([len(data.agv.speeds)] * (2 * operation_count)),
    ]
    children: tuple[Chromosome, ...] = (first,)
    if rng.random() < crossover_probability:
        job_count = rng.randrange(1, data.instance.job_count + 1)
        jobs = set(rng.sample(range(data.instance.job_count), job_count))
        count = rng.randrange(1, len(rs_upper) + 1)
        positions = sorted(rng.sample(range(len(rs_upper)), count))
        children = matlab_crossover(first, second, jobs, positions)
    output = []
    for child in children:
        if rng.random() < mutation_probability:
            left = rng.randrange(operation_count)
            right = rng.randrange(operation_count)
            while child.os[left] == child.os[right]:
                right = rng.randrange(operation_count)
            maximum = math.floor(0.05 * len(rs_upper) + 0.5)
            reset_count = rng.randrange(1, maximum + 1)
            reset_positions = rng.sample(range(len(rs_upper)), reset_count)
            child = matlab_mutation(
                child,
                (left, right),
                {position: rng.randrange(rs_upper[position]) for position in reset_positions},
            )
        output.append(child)
    return tuple(output)


def run_moead(
    data: ExperimentInput,
    *,
    population_size: int = 100,
    generations: int | None = None,
    time_limit_seconds: float | None = None,
    seed: int,
    crossover_probability: float = 0.8,
    mutation_probability: float = 0.2,
    local_probability: float = 0.8,
) -> MOEADResult:
    if (generations is None or generations <= 0) and (
        time_limit_seconds is None or time_limit_seconds <= 0
    ):
        raise ValueError("必须提供正的代数或CPU时间上限")
    neighborhood_size = math.floor(population_size / 20 + 0.5)
    weights = generate_weights(population_size)
    neighbors = weight_neighbors(weights, neighborhood_size)
    rng = random.Random(seed)
    population = list(
        random_population(data, population_size, len(data.agv.speeds), rng).chromosomes
    )
    objectives = [_evaluate(data, chromosome) for chromosome in population]
    ideal = [min(row[column] for row in objectives) for column in range(2)]
    best = ideal.copy()
    evaluations = population_size
    curve_min: list[Objective] = []
    curve_average: list[Objective] = []
    generation = 0
    started = time.perf_counter()
    while (generations is None or generation < generations) and (
        time_limit_seconds is None or time.perf_counter() - started < time_limit_seconds
    ):
        for index in range(population_size):
            source = (
                rng.choice(neighbors[index])
                if rng.random() < local_probability
                else rng.randrange(population_size)
            )
            for child in _variation_pair(
                population[index],
                population[source],
                data,
                crossover_probability,
                mutation_probability,
                rng,
            ):
                if rng.random() < 0.5:
                    continue
                objective = _evaluate(data, child)
                evaluations += 1
                ideal = [min(ideal[column], objective[column]) for column in range(2)]
                for replace in replacement_mask(objectives, objective, neighbors[index], weights, ideal):
                    population[replace] = child
                    objectives[replace] = objective
        best = [min(best[column], *(row[column] for row in objectives)) for column in range(2)]
        curve_min.append((best[0], best[1]))
        curve_average.append(
            tuple(sum(row[column] for row in objectives) / population_size for column in range(2))
        )
        generation += 1
    ranks, _ = rank_and_crowding(objectives)
    unique: dict[Objective, Chromosome] = {}
    for chromosome, objective, rank in zip(population, objectives, ranks):
        if rank == 1:
            unique.setdefault(objective, chromosome)
    ordered = tuple(sorted(unique))
    return MOEADResult(
        tuple(unique[row] for row in ordered), ordered, tuple(curve_min),
        tuple(curve_average), evaluations, generation, seed
    )
