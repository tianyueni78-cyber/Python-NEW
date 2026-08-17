"""静态完整QNSGA-II主入口。"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .chromosome import Chromosome
from .data import ExperimentInput
from .decoder import decode_static
from .genetic import variation
from .initialization import hybrid_population
from .multiobjective import rank_and_crowding, tournament_selection
from .neighborhoods import apply_neighborhood
from .qlearning import epsilon, reward_value, select_action, state_of, update_q


Objective = tuple[float, float]


@dataclass(frozen=True)
class QNSGA2Result:
    pareto_chromosomes: tuple[Chromosome, ...]
    pareto_objectives: tuple[Objective, ...]
    qtable: tuple[tuple[float, ...], ...]
    curve_min: tuple[Objective, ...]
    curve_average: tuple[Objective, ...]
    evaluations: int
    seed: int


def _evaluate(data: ExperimentInput, chromosome: Chromosome) -> Objective:
    result = decode_static(data, chromosome)
    return result.makespan, result.machine_energy


def _qnsga_order(objectives: list[Objective]) -> tuple[list[int], list[int], list[float]]:
    ranks, crowding = rank_and_crowding(objectives)
    indices = sorted(
        range(len(objectives)), key=lambda index: (ranks[index], -crowding[index])
    )
    return indices, ranks, crowding


def run_qnsga2(
    data: ExperimentInput,
    *,
    population_size: int = 100,
    generations: int = 200,
    seed: int,
    crossover_probability: float = 0.8,
    mutation_probability: float = 0.1,
    alpha: float = 0.1,
    gamma: float = 0.9,
) -> QNSGA2Result:
    """按initial_NSGA-II/initial_INSGA_II.m的活动顺序运行。"""
    if generations <= 0:
        raise ValueError("迭代代数必须为正")
    rng = random.Random(seed)
    population = list(
        hybrid_population(data, population_size, len(data.agv.speeds), rng).chromosomes
    )
    objectives = [_evaluate(data, chromosome) for chromosome in population]
    evaluations = len(population)
    qtable = [[0.0] * 6 for _ in range(4)]
    current_state = 3
    ranks: list[float] = [objective[0] for objective in objectives]
    crowding: list[float] = [objective[1] for objective in objectives]
    curve_min: list[Objective] = []
    curve_average: list[Objective] = []

    for generation in range(generations):
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
        order, candidate_ranks, candidate_crowding = _qnsga_order(candidate_objectives)
        selected = order[:population_size]
        population = [candidates[index] for index in selected]
        objectives = [candidate_objectives[index] for index in selected]

        time_median = sorted(value[0] for value in objectives)[population_size // 2 - 1 : population_size // 2 + 1]
        energy_median = sorted(value[1] for value in objectives)[population_size // 2 - 1 : population_size // 2 + 1]
        time_boundary = sum(time_median) / len(time_median)
        energy_boundary = sum(energy_median) / len(energy_median)
        maximum = [max(row[column] for row in objectives) for column in range(2)]
        minimum = [min(row[column] for row in objectives) for column in range(2)]
        time_order = sorted(range(population_size), key=lambda index: objectives[index][0])
        state_groups = [[], [], [], []]
        for index in time_order:
            state_groups[state_of(objectives[index], time_boundary, energy_boundary)].append(index)

        accepted_chromosomes: list[Chromosome] = []
        accepted_objectives: list[Objective] = []
        epsilon_value = epsilon(generation, generations)
        for state, group in enumerate(state_groups):
            for index in group:
                action = select_action(qtable, current_state, epsilon_value, rng)
                neighbor = apply_neighborhood(data, population[index], action, rng)
                new_objective = _evaluate(data, neighbor)
                evaluations += 1
                old_objective = objectives[index]
                if not all(old <= new for old, new in zip(old_objective, new_objective)):
                    accepted_chromosomes.append(neighbor)
                    accepted_objectives.append(new_objective)
                current_state = state
                reward = reward_value(old_objective, new_objective, maximum, minimum)
                next_state = state_of(new_objective, time_boundary, energy_boundary)
                update_q(qtable, current_state, action, reward, next_state, alpha, gamma)

        candidates = population + accepted_chromosomes
        candidate_objectives = objectives + accepted_objectives
        order, candidate_ranks, candidate_crowding = _qnsga_order(candidate_objectives)
        selected = order[:population_size]
        population = [candidates[index] for index in selected]
        objectives = [candidate_objectives[index] for index in selected]
        ranks = [candidate_ranks[index] for index in selected]
        crowding = [candidate_crowding[index] for index in selected]
        curve_min.append(
            (min(row[0] for row in objectives), min(row[1] for row in objectives))
        )
        curve_average.append(
            (
                sum(row[0] for row in objectives) / population_size,
                sum(row[1] for row in objectives) / population_size,
            )
        )

    pareto = [
        (objective, chromosome)
        for objective, chromosome, rank in zip(objectives, population, ranks)
        if rank == 1
    ]
    unique = {}
    for objective, chromosome in pareto:
        unique.setdefault(objective, chromosome)
    sorted_objectives = tuple(sorted(unique))
    return QNSGA2Result(
        tuple(unique[objective] for objective in sorted_objectives),
        sorted_objectives,
        tuple(tuple(row) for row in qtable),
        tuple(curve_min),
        tuple(curve_average),
        evaluations,
        seed,
    )
