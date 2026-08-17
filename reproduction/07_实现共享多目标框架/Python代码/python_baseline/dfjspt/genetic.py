"""静态NSGA系列真实共享的确定性交叉与变异核心。"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence, Set
import math
import random

from .chromosome import Chromosome
from .data import FJSPInstance


def _rs(chromosome: Chromosome) -> list[int]:
    speed = [gene for pair in zip(chromosome.empty_speed, chromosome.loaded_speed) for gene in pair]
    return [*chromosome.ms, *chromosome.agv, *speed]


def _from_os_rs(os: Sequence[int], rs: Sequence[int]) -> Chromosome:
    operation_count = len(os)
    if len(rs) != 4 * operation_count:
        raise ValueError("RS长度必须为总工序数的4倍")
    speed = rs[2 * operation_count :]
    return Chromosome(
        tuple(os),
        tuple(rs[:operation_count]),
        tuple(rs[operation_count : 2 * operation_count]),
        tuple(speed[::2]),
        tuple(speed[1::2]),
    )


def matlab_crossover(
    parent_1: Chromosome,
    parent_2: Chromosome,
    selected_jobs: Set[int],
    selected_rs_positions: Sequence[int],
) -> tuple[Chromosome, Chromosome]:
    """使用固定作业集和RS位置复现MATLAB的IPOX/MPX。"""
    if parent_1.operation_count != parent_2.operation_count:
        raise ValueError("父代染色体长度必须相同")
    if Counter(parent_1.os) != Counter(parent_2.os):
        raise ValueError("父代OS必须描述同一组工序")
    if not selected_jobs or not selected_rs_positions:
        raise ValueError("MATLAB交叉至少选择一个作业和一个RS位置")

    child_1_os = list(parent_1.os)
    child_2_os = list(parent_2.os)
    source_2 = iter(gene for gene in parent_2.os if gene in selected_jobs)
    source_1 = iter(gene for gene in parent_1.os if gene in selected_jobs)
    for index, gene in enumerate(child_1_os):
        if gene in selected_jobs:
            child_1_os[index] = next(source_2)
    for index, gene in enumerate(child_2_os):
        if gene in selected_jobs:
            child_2_os[index] = next(source_1)

    parent_1_rs = _rs(parent_1)
    parent_2_rs = _rs(parent_2)
    if any(index < 0 or index >= len(parent_1_rs) for index in selected_rs_positions):
        raise ValueError("RS交叉位置越界")
    child_1_rs = parent_2_rs.copy()
    child_2_rs = parent_1_rs.copy()
    for index in selected_rs_positions:
        child_1_rs[index] = parent_1_rs[index]
        child_2_rs[index] = parent_2_rs[index]

    return (
        _from_os_rs(child_1_os, child_2_rs),
        _from_os_rs(child_2_os, child_1_rs),
    )


def matlab_mutation(
    chromosome: Chromosome,
    os_positions: tuple[int, int],
    rs_replacements: Mapping[int, int],
) -> Chromosome:
    """使用固定位置复现MATLAB的异作业OS交换和RS重置。"""
    first, second = os_positions
    if (
        first == second
        or first < 0
        or second < 0
        or first >= chromosome.operation_count
        or second >= chromosome.operation_count
    ):
        raise ValueError("OS变异必须选择两个不同的合法位置")
    if chromosome.os[first] == chromosome.os[second]:
        raise ValueError("MATLAB会持续采样直到两个OS位置属于不同作业")

    os = list(chromosome.os)
    os[first], os[second] = os[second], os[first]
    rs = _rs(chromosome)
    for position, value in rs_replacements.items():
        if position < 0 or position >= len(rs) or value < 0:
            raise ValueError("RS变异位置或基因值不合法")
        rs[position] = value
    return _from_os_rs(os, rs)


def _matlab_rounded_parent_index(size: int, rng: random.Random) -> int:
    return max(1, math.floor(size * rng.random() + 0.5)) - 1


def variation(
    parents: Sequence[Chromosome],
    crossover_probability: float,
    mutation_probability: float,
    instance: FJSPInstance,
    agv_count: int,
    speed_count: int,
    rng: random.Random,
) -> tuple[Chromosome, ...]:
    """复现共享variation.m的随机编排；随机流不要求与MATLAB逐值相同。"""
    if not parents:
        raise ValueError("父代种群不能为空")
    if not 0 <= crossover_probability <= 1 or not 0 <= mutation_probability <= 1:
        raise ValueError("交叉和变异概率必须位于[0, 1]")
    operation_count = instance.operation_count
    if any(parent.operation_count != operation_count for parent in parents):
        raise ValueError("父代染色体与实例工序数不一致")

    rs_upper = [
        *(len(operation.options) for job in instance.jobs for operation in job.operations),
        *([agv_count] * operation_count),
        *([speed_count] * (2 * operation_count)),
    ]
    offspring: list[Chromosome] = []
    for _ in parents:
        parent_1_index = _matlab_rounded_parent_index(len(parents), rng)
        children = (parents[parent_1_index],)
        if rng.random() < crossover_probability:
            parent_2_index = _matlab_rounded_parent_index(len(parents), rng)
            while parents[parent_2_index] == parents[parent_1_index]:
                parent_2_index = _matlab_rounded_parent_index(len(parents), rng)
            selected_job_count = rng.randrange(1, instance.job_count + 1)
            selected_jobs = set(rng.sample(range(instance.job_count), selected_job_count))
            selected_rs_count = rng.randrange(1, len(rs_upper) + 1)
            selected_rs_positions = sorted(
                rng.sample(range(len(rs_upper)), selected_rs_count)
            )
            children = matlab_crossover(
                parents[parent_1_index],
                parents[parent_2_index],
                selected_jobs,
                selected_rs_positions,
            )

        for child in children:
            if rng.random() < mutation_probability:
                first = rng.randrange(operation_count)
                second = rng.randrange(operation_count)
                while child.os[first] == child.os[second]:
                    second = rng.randrange(operation_count)
                maximum_reset_count = math.floor(0.05 * len(rs_upper) + 0.5)
                reset_count = rng.randrange(1, maximum_reset_count + 1)
                reset_positions = rng.sample(range(len(rs_upper)), reset_count)
                replacements = {
                    position: rng.randrange(rs_upper[position])
                    for position in reset_positions
                }
                child = matlab_mutation(child, (first, second), replacements)
            offspring.append(child)
    return tuple(offspring)
