"""静态MATLAB对比算法NSGA-II。"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass

from .chromosome import Chromosome
from .data import ExperimentInput
from .decoder import decode_static
from .genetic import variation
from .initialization import random_population
from .multiobjective import environmental_select, rank_and_crowding, tournament_selection


Objective = tuple[float, float]


@dataclass(frozen=True)
class NSGA2Result:
    pareto_chromosomes: tuple[Chromosome, ...]
    pareto_objectives: tuple[Objective, ...]
    curve_min: tuple[Objective, ...]
    curve_average: tuple[Objective, ...]
    evaluations: int
    generations: int
    seed: int


def _evaluate(data: ExperimentInput, chromosome: Chromosome) -> Objective:
    result = decode_static(data, chromosome)
    return result.makespan, result.machine_energy


def _continue(generation: int, generations: int | None, started: float, seconds: float | None) -> bool:
    return (generations is None or generation < generations) and (
        seconds is None or time.perf_counter() - started < seconds
    )


def run_nsga2(
    data: ExperimentInput,
    *,
    population_size: int = 100,
    generations: int | None = None,
    time_limit_seconds: float | None = None,
    seed: int,
    crossover_probability: float = 0.8,
    mutation_probability: float = 0.1,
) -> NSGA2Result:
    """按NSGA-II/NSGA2.m运行，评价统一使用Gate 3静态目标。"""
    if population_size < 2:
        raise ValueError("种群规模至少为2")
    if (generations is None or generations <= 0) and (
        time_limit_seconds is None or time_limit_seconds <= 0
    ):
        raise ValueError("必须提供正的代数或CPU时间上限")
    rng = random.Random(seed)
    population = list(
        random_population(data, population_size, len(data.agv.speeds), rng).chromosomes
    )
    objectives = [_evaluate(data, chromosome) for chromosome in population]
    evaluations = population_size
    curve_min: list[Objective] = []
    curve_average: list[Objective] = []
    generation = 0
    started = time.perf_counter()

    while _continue(generation, generations, started, time_limit_seconds):
        ranks, crowding = rank_and_crowding(objectives)
        parent_indices = tournament_selection(
            ranks, crowding, round(population_size / 2), 2, rng
        )
        parents = [population[index] for index in parent_indices]
        offspring = list(
            variation(
                parents,
                crossover_probability,
                mutation_probability,
                data.instance,
                data.agv.count,
                len(data.agv.speeds),
                rng,
            )
        )
        offspring_objectives = [_evaluate(data, chromosome) for chromosome in offspring]
        evaluations += len(offspring)
        candidates = population + offspring
        candidate_objectives = objectives + offspring_objectives
        selected = environmental_select(candidate_objectives, population_size)
        population = [candidates[index] for index in selected]
        objectives = [candidate_objectives[index] for index in selected]
        curve_min.append(
            (min(row[0] for row in objectives), min(row[1] for row in objectives))
        )
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
    return NSGA2Result(
        tuple(unique[objective] for objective in ordered),
        ordered,
        tuple(curve_min),
        tuple(curve_average),
        evaluations,
        generation,
        seed,
    )
