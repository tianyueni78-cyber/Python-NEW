"""复现静态 MATLAB 入口使用的随机与40/30/30混合初始化。"""

from __future__ import annotations

import random
import math
from dataclasses import dataclass

from .chromosome import Chromosome
from .data import ExperimentInput, FJSPInstance


@dataclass(frozen=True)
class InitializedPopulation:
    chromosomes: tuple[Chromosome, ...]
    origins: tuple[str, ...]

    def __len__(self) -> int:
        return len(self.chromosomes)


def tent_chaos(
    rows: int, initial: tuple[float, ...], rng: random.Random
) -> tuple[tuple[float, ...], ...]:
    """复现 init.m 内部 chaos 函数，包括特殊点和四步重复扰动。"""
    if rows <= 0 or not initial:
        raise ValueError("混沌矩阵行数和维数必须为正数")
    values = [tuple(initial)]
    special = {0.0, 0.25, 0.5, 0.75}
    for row_index in range(1, rows):
        row: list[float] = []
        for column, previous in enumerate(values[-1]):
            value = 2.0 * previous if previous < 0.5 else 2.0 * (1.0 - previous)
            if value in special:
                value = rng.random() * value
            history_start = max(0, row_index - 4)
            if any(value == values[index][column] for index in range(history_start, row_index)):
                value = rng.random() * value
            row.append(value)
        values.append(tuple(row))
    return tuple(values)


def _chaos(rows: int, columns: int, rng: random.Random) -> tuple[tuple[float, ...], ...]:
    return tent_chaos(rows, tuple(rng.random() for _ in range(columns)), rng)


def _operation_bounds(instance: FJSPInstance) -> tuple[int, ...]:
    return tuple(len(operation.options) for job in instance.jobs for operation in job.operations)


def _chaotic_os(instance: FJSPInstance, size: int, rng: random.Random) -> list[tuple[int, ...]]:
    base = tuple(
        job_id
        for job_id, count in enumerate(instance.operation_counts)
        for _ in range(count)
    )
    chaos = _chaos(size, len(base), rng)
    return [
        tuple(base[index] for index in sorted(range(len(base)), key=lambda index: (row[index], index)))
        for row in chaos
    ]


def _ceil_gene(value: float, upper_bound: int) -> int:
    # MATLAB基因为 ceil(z*upper_bound)，内部转为0起始。
    return max(0, min(upper_bound - 1, math.ceil(value * upper_bound) - 1))


def _chaotic_bounded(
    size: int, bounds: tuple[int, ...], rng: random.Random
) -> list[tuple[int, ...]]:
    chaos = _chaos(size, len(bounds), rng)
    return [
        tuple(_ceil_gene(value, bound) for value, bound in zip(row, bounds))
        for row in chaos
    ]


def _random_speed_segments(
    size: int, operation_count: int, speed_count: int, rng: random.Random
) -> tuple[list[tuple[int, ...]], list[tuple[int, ...]]]:
    combined = _chaotic_bounded(size, (speed_count,) * (2 * operation_count), rng)
    empty = [row[:operation_count] for row in combined]
    loaded = [row[operation_count:] for row in combined]
    return empty, loaded


def random_population(
    data: ExperimentInput, size: int, speed_count: int, rng: random.Random
) -> InitializedPopulation:
    """复现 NSGA-II 与 MOEA/D 的纯随机 init.m。"""
    if size <= 0 or speed_count <= 0:
        raise ValueError("种群规模和速度档位数必须为正数")
    instance = data.instance
    base_os = [
        job_id
        for job_id, count in enumerate(instance.operation_counts)
        for _ in range(count)
    ]
    bounds = _operation_bounds(instance)
    chromosomes: list[Chromosome] = []
    for _ in range(size):
        chromosome = Chromosome(
            os=tuple(rng.sample(base_os, len(base_os))),
            ms=tuple(rng.randrange(bound) for bound in bounds),
            agv=tuple(rng.randrange(data.agv.count) for _ in bounds),
            empty_speed=tuple(rng.randrange(speed_count) for _ in bounds),
            loaded_speed=tuple(rng.randrange(speed_count) for _ in bounds),
        )
        chromosome.validate(instance, data.agv.count, speed_count)
        chromosomes.append(chromosome)
    return InitializedPopulation(tuple(chromosomes), ("random",) * size)


def _random_group(
    data: ExperimentInput,
    os_rows: list[tuple[int, ...]],
    speed_count: int,
    rng: random.Random,
) -> list[Chromosome]:
    size = len(os_rows)
    bounds = _operation_bounds(data.instance)
    ms_rows = _chaotic_bounded(size, bounds, rng)
    agv_rows = _chaotic_bounded(size, (data.agv.count,) * len(bounds), rng)
    empty_rows, loaded_rows = _random_speed_segments(size, len(bounds), speed_count, rng)
    return [
        Chromosome(os_rows[index], ms_rows[index], agv_rows[index], empty_rows[index], loaded_rows[index])
        for index in range(size)
    ]


def _flat_index(instance: FJSPInstance, job_id: int, operation_id: int) -> int:
    return sum(instance.operation_counts[:job_id]) + operation_id


def _machine_for(data: ExperimentInput, job_id: int, operation_id: int, ms_gene: int) -> int:
    return data.instance.jobs[job_id].operations[operation_id].options[ms_gene].machine_id - 1


def _agv_assignments(
    data: ExperimentInput,
    os_row: tuple[int, ...],
    ms_row: tuple[int, ...],
    choose_by_energy: bool,
) -> tuple[int, ...]:
    instance = data.instance
    agv_count = data.agv.count
    agv_positions: list[int | None] = [None] * agv_count
    job_positions: list[int | None] = [None] * instance.job_count
    battery = [data.agv.maximum_energy] * agv_count
    # 忠实保留MATLAB唯一的temp_position变量，而不是为每辆AGV分别保存。
    temp_position: int | None = None
    next_operation = [0] * instance.job_count
    assignments = [0] * instance.operation_count

    for job_id in os_row:
        operation_id = next_operation[job_id]
        flat_index = _flat_index(instance, job_id, operation_id)
        target_machine = _machine_for(data, job_id, operation_id, ms_row[flat_index])
        empty_distances = [0.0] * agv_count
        for agv_id in range(agv_count):
            if battery[agv_id] < data.agv.minimum_energy:
                temp_position = agv_positions[agv_id]
                battery[agv_id] = data.agv.maximum_energy
                agv_positions[agv_id] = -1

            agv_position = agv_positions[agv_id]
            job_position = job_positions[job_id]
            if agv_position is None and job_position is None:
                empty_distances[agv_id] = 0.0
            elif agv_position == -1 and job_position is None:
                if temp_position is None or temp_position == -1:
                    raise ValueError("MATLAB充电分支缺少充电前机器位置")
                empty_distances[agv_id] = (
                    data.resources.load_to_unload
                    + data.resources.machine_to_unload[temp_position]
                )
            elif agv_position is not None and agv_position != -1 and job_position is None:
                empty_distances[agv_id] = data.resources.load_to_machine[agv_position]
            elif agv_position is None and job_position is not None:
                empty_distances[agv_id] = data.resources.load_to_machine[job_position]
            elif agv_position == -1 and job_position is not None:
                if temp_position is None or temp_position == -1:
                    raise ValueError("MATLAB充电分支缺少充电前机器位置")
                empty_distances[agv_id] = (
                    data.resources.machine_to_unload[job_position]
                    + data.resources.machine_to_unload[temp_position]
                )
            else:
                assert agv_position is not None and job_position is not None
                empty_distances[agv_id] = data.resources.machine_to_machine[agv_position][job_position]

        loaded_distance = (
            data.resources.load_to_machine[target_machine]
            if job_positions[job_id] is None
            else data.resources.machine_to_machine[job_positions[job_id]][target_machine]
        )
        energy = [
            empty_distances[agv_id] * data.agv.idle_energy[-1]
            + loaded_distance * data.agv.loaded_energy[-1]
            for agv_id in range(agv_count)
        ]
        criterion = energy if choose_by_energy else empty_distances
        chosen = min(range(agv_count), key=lambda agv_id: criterion[agv_id])
        agv_positions[chosen] = target_machine
        job_positions[job_id] = target_machine
        assignments[flat_index] = chosen
        battery[chosen] -= energy[chosen]
        next_operation[job_id] += 1
    return tuple(assignments)


def _minimum_time_group(
    data: ExperimentInput,
    os_rows: list[tuple[int, ...]],
    speed_count: int,
    rng: random.Random,
) -> list[Chromosome]:
    instance = data.instance
    machine_time = [0.0] * instance.machine_count
    ms_rows: list[tuple[int, ...]] = []
    for os_row in os_rows:
        next_operation = [0] * instance.job_count
        ms = [0] * instance.operation_count
        for job_id in os_row:
            operation_id = next_operation[job_id]
            flat_index = _flat_index(instance, job_id, operation_id)
            options = instance.jobs[job_id].operations[operation_id].options
            scores = [
                machine_time[option.machine_id - 1] + option.processing_time
                for option in options
            ]
            chosen = min(range(len(options)), key=lambda index: scores[index])
            machine_id = options[chosen].machine_id - 1
            # 忠实保留MATLAB：跨个体累计，且把累计完成量再次加到machine_time。
            machine_time[machine_id] += scores[chosen]
            ms[flat_index] = chosen
            next_operation[job_id] += 1
        ms_rows.append(tuple(ms))

    empty_rows, loaded_rows = _random_speed_segments(
        len(os_rows), instance.operation_count, speed_count, rng
    )
    return [
        Chromosome(
            os_rows[index],
            ms_rows[index],
            _agv_assignments(data, os_rows[index], ms_rows[index], choose_by_energy=False),
            empty_rows[index],
            loaded_rows[index],
        )
        for index in range(len(os_rows))
    ]


def _minimum_energy_group(
    data: ExperimentInput,
    os_rows: list[tuple[int, ...]],
    speed_count: int,
    rng: random.Random,
) -> list[Chromosome]:
    instance = data.instance
    ms_rows: list[tuple[int, ...]] = []
    for os_row in os_rows:
        next_operation = [0] * instance.job_count
        ms = [0] * instance.operation_count
        for job_id in os_row:
            operation_id = next_operation[job_id]
            flat_index = _flat_index(instance, job_id, operation_id)
            options = instance.jobs[job_id].operations[operation_id].options
            energy = [
                option.processing_time
                * data.resources.machine_work_energy[option.machine_id - 1]
                for option in options
            ]
            greedy = min(range(len(options)), key=lambda index: energy[index])
            ms[flat_index] = greedy if rng.random() > 0.5 else rng.randrange(len(options))
            next_operation[job_id] += 1
        ms_rows.append(tuple(ms))

    empty_rows, loaded_rows = _random_speed_segments(
        len(os_rows), instance.operation_count, speed_count, rng
    )
    return [
        Chromosome(
            os_rows[index],
            ms_rows[index],
            _agv_assignments(data, os_rows[index], ms_rows[index], choose_by_energy=True),
            empty_rows[index],
            loaded_rows[index],
        )
        for index in range(len(os_rows))
    ]


def hybrid_population(
    data: ExperimentInput, size: int, speed_count: int, rng: random.Random
) -> InitializedPopulation:
    """复现 QNSGA-II 活动静态代码的40%/30%/30%混合初始化。"""
    if size <= 0 or size % 10 != 0:
        raise ValueError("MATLAB的0.4/0.3/0.3切片要求种群规模为10的正整数倍")
    if speed_count <= 0:
        raise ValueError("速度档位数必须为正数")
    os_rows = _chaotic_os(data.instance, size, rng)
    first = size * 4 // 10
    second = size * 3 // 10
    random_group = _random_group(data, os_rows[:first], speed_count, rng)
    time_group = _minimum_time_group(
        data, os_rows[first : first + second], speed_count, rng
    )
    energy_group = _minimum_energy_group(
        data, os_rows[first + second :], speed_count, rng
    )
    chromosomes = random_group + time_group + energy_group
    for chromosome in chromosomes:
        chromosome.validate(data.instance, data.agv.count, speed_count)
    origins = (
        ("chaotic_random",) * first
        + ("minimum_accumulated_time",) * second
        + ("minimum_energy",) * (size - first - second)
    )
    return InitializedPopulation(tuple(chromosomes), origins)
