"""静态完整QNSGA-II的N1—N6邻域。"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence

from .chromosome import Chromosome
from .data import ExperimentInput
from .decoder import decode_static


def _with(
    chromosome: Chromosome,
    *,
    os: Sequence[int] | None = None,
    ms: Sequence[int] | None = None,
    agv: Sequence[int] | None = None,
) -> Chromosome:
    return Chromosome(
        tuple(chromosome.os if os is None else os),
        tuple(chromosome.ms if ms is None else ms),
        tuple(chromosome.agv if agv is None else agv),
        chromosome.empty_speed,
        chromosome.loaded_speed,
    )


def n1_reinsert_reversed_pair(
    chromosome: Chromosome, adjacent_start: int, insert_after: int
) -> Chromosome:
    os = list(chromosome.os)
    if not 0 <= adjacent_start < len(os) - 1 or not 1 <= insert_after <= len(os) - 2:
        raise ValueError("N1位置越界")
    pair = [os[adjacent_start + 1], os[adjacent_start]]
    del os[adjacent_start : adjacent_start + 2]
    os[insert_after:insert_after] = pair
    return _with(chromosome, os=os)


def n2_remove_and_reinsert(
    chromosome: Chromosome, delete_positions: tuple[int, int], insert_after: int
) -> Chromosome:
    first, second = delete_positions
    if first == second or any(not 0 <= value < len(chromosome.os) for value in delete_positions):
        raise ValueError("N2删除位置不合法")
    if not 1 <= insert_after <= len(chromosome.os) - 2:
        raise ValueError("N2插入位置越界")
    removed = [chromosome.os[first], chromosome.os[second]]
    deleted = set(delete_positions)
    os = [gene for index, gene in enumerate(chromosome.os) if index not in deleted]
    os[insert_after:insert_after] = removed
    return _with(chromosome, os=os)


def replace_machine_gene(chromosome: Chromosome, position: int, value: int) -> Chromosome:
    ms = list(chromosome.ms)
    if not 0 <= position < len(ms) or value < 0:
        raise ValueError("机器基因位置或值不合法")
    ms[position] = value
    return _with(chromosome, ms=ms)


def replace_agv_gene(chromosome: Chromosome, position: int, value: int) -> Chromosome:
    agv = list(chromosome.agv)
    if not 0 <= position < len(agv) or value < 0:
        raise ValueError("AGV基因位置或值不合法")
    agv[position] = value
    return _with(chromosome, agv=agv)


def _offsets(data: ExperimentInput) -> list[int]:
    offsets = []
    total = 0
    for count in data.instance.operation_counts:
        offsets.append(total)
        total += count
    return offsets


def n6_waiting_agv_reassignment(
    data: ExperimentInput, chromosome: Chromosome, rng: random.Random
) -> Chromosome:
    schedule = decode_static(data, chromosome)
    waits: list[tuple[int, float, float]] = []
    for agv_index, table in enumerate(schedule.agv_tables):
        for index in range(1, len(table)):
            current = table[index]
            previous = table[index - 1]
            if (
                current.job == 0
                and current.charge == 0
                and previous.load_status == -1
                and not math.isinf(current.end)
            ):
                waits.append((agv_index, previous.start, current.end - current.start))
    if not waits:
        return replace_agv_gene(
            chromosome,
            rng.randrange(chromosome.operation_count),
            rng.randrange(data.agv.count),
        )
    use_agv, threshold, _ = max(waits, key=lambda row: row[2])
    records: list[tuple[int, int, int, float]] = []
    for agv_index, table in enumerate(schedule.agv_tables):
        if agv_index == use_agv:
            continue
        for block in table:
            if (
                block.job != 0
                and block.charge == 0
                and block.load_status == -1
                and block.start >= threshold
            ):
                records.append((agv_index, block.job, block.opera, block.start))
                break
    if not records:
        return replace_agv_gene(
            chromosome,
            rng.randrange(chromosome.operation_count),
            rng.randrange(data.agv.count),
        )
    _, job, operation, _ = min(records, key=lambda row: row[3])
    position = _offsets(data)[job - 1] + operation - 1
    return replace_agv_gene(chromosome, position, use_agv)


def _n3(data: ExperimentInput, chromosome: Chromosome, rng: random.Random) -> Chromosome:
    position = 0
    option_count = 0
    attempt = 0
    for attempt in range(1, 11):
        job = rng.randrange(data.instance.job_count)
        operation = rng.randrange(data.instance.operation_counts[job])
        position = _offsets(data)[job] + operation
        option_count = len(data.instance.jobs[job].operations[operation].options)
        if option_count > 1:
            break
    old = chromosome.ms[position]
    new = old
    if option_count > 1 and attempt < 10:
        while new == old:
            new = rng.randrange(option_count)
    return replace_machine_gene(chromosome, position, new)


def _n4(data: ExperimentInput, chromosome: Chromosome, rng: random.Random) -> Chromosome:
    schedule = decode_static(data, chromosome)
    counts = [sum(block.job != 0 for block in table) for table in schedule.machine_tables]
    maximum_machine = max(range(len(counts)), key=lambda index: counts[index])
    operations = [
        (block.job - 1, block.opera - 1)
        for block in schedule.machine_tables[maximum_machine]
        if block.job != 0
    ]
    selected = operations[0]
    options = ()
    for _ in range(10):
        selected = rng.choice(operations)
        options = data.instance.jobs[selected[0]].operations[selected[1]].options
        if len(options) > 1:
            break
    loads = [counts[option.machine_id - 1] for option in options]
    new_code = min(range(len(loads)), key=lambda index: loads[index])
    position = _offsets(data)[selected[0]] + selected[1]
    return replace_machine_gene(chromosome, position, new_code)


def apply_neighborhood(
    data: ExperimentInput,
    chromosome: Chromosome,
    action: int,
    rng: random.Random,
) -> Chromosome:
    """按0起始动作编号执行活动MATLAB路径的N1—N6。"""
    operation_count = chromosome.operation_count
    if action == 0:
        return n1_reinsert_reversed_pair(
            chromosome, rng.randrange(operation_count - 1), rng.randrange(1, operation_count - 1)
        )
    if action == 1:
        positions = tuple(rng.sample(range(operation_count), 2))
        return n2_remove_and_reinsert(
            chromosome, positions, rng.randrange(1, operation_count - 1)
        )
    if action == 2:
        return _n3(data, chromosome, rng)
    if action == 3:
        return _n4(data, chromosome, rng)
    if action == 4:
        position = rng.randrange(operation_count)
        old = chromosome.agv[position]
        new = old
        while new == old:
            new = rng.randrange(data.agv.count)
        return replace_agv_gene(chromosome, position, new)
    if action == 5:
        return n6_waiting_agv_reassignment(data, chromosome, rng)
    raise ValueError("邻域动作必须位于0至5")
