"""论文静态QNSGA-II消融A、B、C与完整版本。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .chromosome import Chromosome
from .data import ExperimentInput
from .nsga2 import run_nsga2
from .qnsga2 import run_qnsga2


Objective = tuple[float, float]


class AblationVariant(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    FULL = "full"


@dataclass(frozen=True)
class AblationResult:
    variant: AblationVariant
    pareto_chromosomes: tuple[Chromosome, ...]
    pareto_objectives: tuple[Objective, ...]
    qtable: tuple[tuple[float, ...], ...]
    curve_min: tuple[Objective, ...]
    curve_average: tuple[Objective, ...]
    evaluations: int
    generations: int
    seed: int


def ablation_features() -> dict[str, dict[str, bool | int | str]]:
    """返回与四个锁定MATLAB入口对应的显式模块矩阵。"""
    return {
        "A": {
            "random_initialization": True,
            "hybrid_initialization": False,
            "initial_nondomination_sort": True,
            "has_local_search": False,
            "neighborhood_count": 0,
            "random_action": False,
            "q_action": False,
            "q_update": False,
            "python_stop": "same_generations",
        },
        "B": {
            "random_initialization": False,
            "hybrid_initialization": True,
            "initial_nondomination_sort": False,
            "has_local_search": False,
            "neighborhood_count": 0,
            "random_action": False,
            "q_action": False,
            "q_update": False,
            "python_stop": "same_generations",
        },
        "C": {
            "random_initialization": False,
            "hybrid_initialization": True,
            "initial_nondomination_sort": False,
            "has_local_search": True,
            "neighborhood_count": 6,
            "random_action": True,
            "q_action": False,
            "q_update": False,
            "python_stop": "same_generations",
        },
        "full": {
            "random_initialization": False,
            "hybrid_initialization": True,
            "initial_nondomination_sort": False,
            "has_local_search": True,
            "neighborhood_count": 6,
            "random_action": True,
            "q_action": True,
            "q_update": True,
            "python_stop": "same_generations",
        },
    }


def run_ablation(
    data: ExperimentInput,
    variant: AblationVariant | str,
    *,
    population_size: int = 100,
    generations: int = 200,
    seed: int,
    crossover_probability: float = 0.8,
    mutation_probability: float = 0.1,
    alpha: float = 0.1,
    gamma: float = 0.9,
) -> AblationResult:
    variant = AblationVariant(variant)
    if variant is AblationVariant.A:
        result = run_nsga2(
            data,
            population_size=population_size,
            generations=generations,
            seed=seed,
            crossover_probability=crossover_probability,
            mutation_probability=mutation_probability,
        )
        return AblationResult(
            variant,
            result.pareto_chromosomes,
            result.pareto_objectives,
            tuple((0.0,) * 6 for _ in range(4)),
            result.curve_min,
            result.curve_average,
            result.evaluations,
            result.generations,
            seed,
        )

    mode = {
        AblationVariant.B: "hybrid_only",
        AblationVariant.C: "random_neighborhood",
        AblationVariant.FULL: "full",
    }[variant]
    result = run_qnsga2(
        data,
        population_size=population_size,
        generations=generations,
        seed=seed,
        crossover_probability=crossover_probability,
        mutation_probability=mutation_probability,
        alpha=alpha,
        gamma=gamma,
        mode=mode,
    )
    return AblationResult(
        variant,
        result.pareto_chromosomes,
        result.pareto_objectives,
        result.qtable,
        result.curve_min,
        result.curve_average,
        result.evaluations,
        len(result.curve_min),
        seed,
    )
