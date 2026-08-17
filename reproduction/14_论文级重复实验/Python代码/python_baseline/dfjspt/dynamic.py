"""三类动态事件的状态继承与 MATLAB IS/RS/CS 策略边界。"""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import inf, isinf
import random
import time

from .chromosome import Chromosome
from .data import ExperimentInput
from .decoder import (
    AGVBlock, MachineBlock, ScheduleResult, _append_agv, _distance, _insert_machine,
)
from .genetic import variation
from .initialization import hybrid_population
from .multiobjective import environmental_select, pareto_indices, rank_and_crowding
from .neighborhoods import apply_neighborhood
from .qlearning import epsilon, reward_value, select_action, state_of, update_q


OperationKey = tuple[int, int]


@dataclass(frozen=True)
class DynamicEvent:
    kind: str
    time: float
    target: int
    duration: float = 0.0

    def __post_init__(self) -> None:
        if self.kind not in {"order_cancellation", "machine_failure", "agv_failure"}:
            raise ValueError("动态事件必须是订单取消、机器故障或AGV故障")
        if self.time < 0 or self.duration < 0 or self.target <= 0:
            raise ValueError("事件时间、持续时间和目标编号无效")


@dataclass(frozen=True)
class DynamicState:
    completed_operations: frozenset[OperationKey]
    in_process_operations: frozenset[OperationKey]
    remaining_operations: frozenset[OperationKey]
    machine_available: tuple[float, ...]
    agv_available: tuple[float, ...]
    agv_locations: tuple[int, ...]
    agv_battery: tuple[float, ...]
    unavailable_interval: tuple[float, float] | None


@dataclass(frozen=True)
class ReschedulingPlan:
    strategy: str
    event: DynamicEvent
    fixed_operations: frozenset[OperationKey]
    rescheduled_operations: frozenset[OperationKey]
    mutable_segments: frozenset[str]

    @property
    def signature(self) -> tuple[str, tuple[str, ...]]:
        return self.strategy, tuple(sorted(self.mutable_segments))


@dataclass(frozen=True)
class DynamicOptimizationResult:
    strategy: str
    pareto_chromosomes: tuple[Chromosome, ...]
    pareto_objectives: tuple[tuple[float, float], ...]
    pareto_schedules: tuple[ScheduleResult, ...]
    evaluations: int
    seed: int
    qtable: tuple[tuple[float, ...], ...]


def _active_end(table, moment: float) -> float:
    ends = [b.end for b in table if not isinf(b.end) and b.end <= moment]
    return max(ends, default=0.0)


def analyze_event(schedule: ScheduleResult, event: DynamicEvent) -> DynamicState:
    operations = {
        (block.job, block.opera): block
        for table in schedule.machine_tables for block in table if block.job
    }
    completed = frozenset(key for key, block in operations.items() if block.end <= event.time)
    in_process = frozenset(
        key for key, block in operations.items() if block.start < event.time < block.end
    )
    remaining = frozenset(operations) - completed
    machine_available = tuple(_active_end(table, event.time) for table in schedule.machine_tables)
    agv_available = tuple(_active_end(table, event.time) for table in schedule.agv_tables)
    locations: list[int] = []
    for table in schedule.agv_tables:
        prior = [block for block in table if block.start <= event.time]
        block = prior[-1] if prior else table[0]
        locations.append(block.to_machine if block.end <= event.time else block.from_machine)
    battery = tuple(
        next((value for time, value in reversed(records) if time <= event.time), records[0][1])
        for records in schedule.battery_records
    )
    unavailable = (
        (event.time, event.time + event.duration)
        if event.kind.endswith("failure") else None
    )
    return DynamicState(
        completed, in_process, remaining, machine_available, agv_available,
        tuple(locations), battery, unavailable,
    )


def build_rescheduling_plan(
    schedule: ScheduleResult, chromosome: Chromosome, event: DynamicEvent, strategy: str,
) -> ReschedulingPlan:
    del chromosome  # 策略边界由事件及已执行时间表决定。
    if strategy not in {"IS", "RS", "CS"}:
        raise ValueError("重调度策略必须是IS、RS或CS")
    state = analyze_event(schedule, event)
    fixed = state.completed_operations | state.in_process_operations
    residual = set(state.remaining_operations - state.in_process_operations)
    if event.kind == "order_cancellation":
        fixed = frozenset(key for key in fixed if key[0] != event.target)
        residual = {key for key in residual if key[0] != event.target}
    if strategy == "IS":
        mutable = frozenset()
    elif strategy == "CS":
        mutable = frozenset({"OS", "MS", "AS", "VS"})
    elif event.kind == "order_cancellation":
        mutable = frozenset({"OS", "AS", "VS"})
    elif event.kind == "machine_failure":
        mutable = frozenset({"OS", "MS_FAULT_ONLY", "AS", "VS"})
    else:
        mutable = frozenset({"OS", "AS", "VS"})
    return ReschedulingPlan(strategy, event, frozenset(fixed), frozenset(residual), mutable)


def _delay(start: float, end: float, moment: float, duration: float) -> tuple[float, float]:
    if isinf(end) or end <= moment:
        return start, end
    return (start + duration if start >= moment else start, end + duration)


def _rebuild_machine(blocks: list[MachineBlock]) -> tuple[MachineBlock, ...]:
    work = sorted((b for b in blocks if b.job), key=lambda b: (b.start, b.end))
    result: list[MachineBlock] = []
    cursor = 0.0
    for block in work:
        if block.start > cursor:
            result.append(MachineBlock(cursor, block.start, 0, 0))
        result.append(block)
        cursor = block.end
    result.append(MachineBlock(cursor, inf, 0, 0))
    return tuple(result)


def _rebuild_agv(blocks: list[AGVBlock]) -> tuple[AGVBlock, ...]:
    finite = sorted((b for b in blocks if not isinf(b.end)), key=lambda b: (b.start, b.end))
    if not finite:
        return (AGVBlock(0, inf, 0, 0, 0, -1, 0, 0),)
    result: list[AGVBlock] = []
    cursor = 0.0
    location = finite[0].from_machine
    for block in finite:
        if block.start > cursor:
            result.append(AGVBlock(cursor, block.start, 0, 0, 0, location, location, 0))
        result.append(block)
        cursor, location = block.end, block.to_machine
    result.append(AGVBlock(cursor, inf, 0, 0, 0, location, 0, 0))
    return tuple(result)


def execute_is(
    data: ExperimentInput, chromosome: Chromosome, schedule: ScheduleResult,
    event: DynamicEvent,
) -> ScheduleResult:
    """执行 MATLAB initial_* 的不重排策略；故障时整体右移未完成部分。"""
    del data, chromosome
    cancelled = event.target if event.kind == "order_cancellation" else None
    delay = event.duration if event.kind.endswith("failure") else 0.0
    machines = []
    for table in schedule.machine_tables:
        blocks = []
        for block in table:
            if not block.job or block.job == cancelled:
                continue
            start, end = _delay(block.start, block.end, event.time, delay)
            blocks.append(replace(block, start=start, end=end))
        machines.append(_rebuild_machine(blocks))
    agvs = []
    for table in schedule.agv_tables:
        blocks = []
        for block in table:
            if isinf(block.end) or block.job == cancelled:
                continue
            start, end = _delay(block.start, block.end, event.time, delay)
            blocks.append(replace(block, start=start, end=end))
        agvs.append(_rebuild_agv(blocks))
    records = tuple(
        tuple((time + delay if time > event.time else time, power) for time, power in row)
        for row in schedule.battery_records
    )
    completion = []
    for job in range(1, len(schedule.job_completion) + 1):
        ends = [b.end for table in machines for b in table if b.job == job]
        completion.append(max(ends, default=0.0))
    makespan = max(completion, default=0.0)
    return ScheduleResult(
        makespan, schedule.machine_energy, schedule.agv_energy, tuple(completion),
        schedule.charge_counts, tuple(machines), tuple(agvs), records,
    )


def _fixed_machine_table(
    original: ScheduleResult, machine_index: int, fixed: frozenset[OperationKey],
    event: DynamicEvent,
) -> list[MachineBlock]:
    blocks: list[MachineBlock] = []
    split_failure = False
    for block in original.machine_tables[machine_index]:
        if not block.job or (block.job, block.opera) not in fixed:
            continue
        if (
            event.kind == "machine_failure" and machine_index == event.target - 1
            and block.start < event.time < block.end
        ):
            remaining = block.end - event.time
            blocks.extend((
                replace(block, end=event.time),
                MachineBlock(event.time, event.time + event.duration, -1, 0),
                replace(
                    block,
                    start=event.time + event.duration,
                    end=event.time + event.duration + remaining,
                ),
            ))
            split_failure = True
        else:
            blocks.append(replace(block))
    if event.kind == "machine_failure" and machine_index == event.target - 1:
        if not split_failure:
            blocks.append(MachineBlock(event.time, event.time + event.duration, -1, 0))
    blocks.sort(key=lambda block: (block.start, block.end))
    table: list[MachineBlock] = []
    cursor = 0.0
    for block in blocks:
        if block.start > cursor:
            table.append(MachineBlock(cursor, block.start, 0, 0))
        table.append(block)
        cursor = max(cursor, block.end)
    table.append(MachineBlock(cursor, inf, 0, 0))
    return table


def _residual_os(
    data: ExperimentInput, chromosome: Chromosome, residual: frozenset[OperationKey],
) -> list[tuple[int, int]]:
    next_operation = [0] * data.instance.job_count
    result: list[tuple[int, int]] = []
    for job_index in chromosome.os:
        operation_index = next_operation[job_index]
        next_operation[job_index] += 1
        if (job_index + 1, operation_index + 1) in residual:
            result.append((job_index, operation_index))
    return result


def _decode_dynamic(
    data: ExperimentInput, chromosome: Chromosome, original: ScheduleResult,
    event: DynamicEvent,
) -> ScheduleResult:
    state = analyze_event(original, event)
    fixed = state.completed_operations | state.in_process_operations
    residual = state.remaining_operations - state.in_process_operations
    if event.kind == "order_cancellation":
        fixed = frozenset(key for key in fixed if key[0] != event.target)
        residual = frozenset(key for key in residual if key[0] != event.target)

    machines = [
        _fixed_machine_table(original, index, fixed, event)
        for index in range(data.instance.machine_count)
    ]
    job_time = [event.time] * data.instance.job_count
    job_position = [-1] * data.instance.job_count
    for key in fixed:
        block = next(
            block for table in original.machine_tables for block in table
            if (block.job, block.opera) == key
        )
        index = block.job - 1
        if block.end >= job_time[index]:
            job_time[index] = block.end
            job_position[index] = next(
                machine_index + 1 for machine_index, table in enumerate(original.machine_tables)
                if block in table
            )

    agvs: list[list[AGVBlock]] = []
    batteries = list(state.agv_battery)
    battery_records: list[list[tuple[float, float]]] = []
    charge_counts = [0] * data.agv.count
    for agv_index, original_table in enumerate(original.agv_tables):
        prefix: list[AGVBlock] = []
        for block in original_table:
            if isinf(block.end) or block.start >= event.time:
                continue
            if (
                event.kind == "agv_failure" and agv_index == event.target - 1
                and block.end > event.time
            ):
                prefix.append(replace(block, end=event.time))
                prefix.append(AGVBlock(
                    event.time, event.time + event.duration, 0, 0, 0,
                    block.to_machine, block.to_machine, 0,
                ))
            else:
                prefix.append(replace(block))
        availability = max(event.time, max((block.end for block in prefix), default=0.0))
        if event.kind == "agv_failure" and agv_index == event.target - 1:
            availability = max(availability, event.time + event.duration)
        location = state.agv_locations[agv_index]
        if prefix and prefix[-1].end <= availability:
            location = prefix[-1].to_machine
        if prefix and prefix[-1].end < availability:
            prefix.append(AGVBlock(prefix[-1].end, availability, 0, 0, 0, location, location, 0))
        elif not prefix and availability > 0:
            prefix.append(AGVBlock(0.0, availability, 0, 0, 0, location, location, 0))
        for block in prefix:
            if block.job and block.load_status == -2:
                job_index = block.job - 1
                if block.end >= job_time[job_index]:
                    job_time[job_index] = block.end
                    job_position[job_index] = block.to_machine
        prefix.append(AGVBlock(availability, inf, 0, 0, 0, location, 0, 0))
        agvs.append(prefix)
        records = [record for record in original.battery_records[agv_index] if record[0] <= event.time]
        if not records or records[-1][0] != availability:
            records.append((availability, batteries[agv_index]))
        battery_records.append(records)

    offsets: list[int] = []
    total = 0
    for count in data.instance.operation_counts:
        offsets.append(total)
        total += count
    completion = [0.0] * data.instance.job_count
    speed_values = data.agv.speeds
    for job_index, operation_index in _residual_os(data, chromosome, frozenset(residual)):
        flat = offsets[job_index] + operation_index
        option = data.instance.jobs[job_index].operations[operation_index].options[chromosome.ms[flat]]
        machine = option.machine_id
        agv_index = chromosome.agv[flat]
        for current in range(data.agv.count):
            if batteries[current] > data.agv.minimum_energy:
                continue
            table = agvs[current]
            start_machine = table[-1].from_machine
            if start_machine != -2:
                start = table[-1].start
                charging_speed = data.agv.charging_travel_speed or speed_values[2]
                duration = _distance(data, start_machine, -2) / charging_speed
                _append_agv(table, start, start + duration, 0, 0, -1, -2, 2)
                charging_energy = (
                    data.agv.idle_energy[0]
                    if data.agv.charging_travel_speed is not None
                    else data.agv.idle_energy[2]
                )
                batteries[current] -= duration * charging_energy
                battery_records[current].append((start + duration, batteries[current]))
            start = table[-1].start
            duration = (data.agv.maximum_energy - batteries[current]) / data.agv.charging_power
            _append_agv(table, start, start + duration, 0, 0, 0, -2, 1)
            batteries[current] = data.agv.maximum_energy
            battery_records[current].append((start + duration, batteries[current]))
            charge_counts[current] += 1

        table = agvs[agv_index]
        source = job_position[job_index]
        agv_complete = job_time[job_index]
        if source != machine:
            speed_index = chromosome.empty_speed[flat]
            start = table[-1].start
            duration = _distance(data, table[-1].from_machine, source) / speed_values[speed_index]
            if duration > 1e-6:
                _append_agv(table, start, start + duration, job_index + 1, operation_index + 1, -1, source)
                batteries[agv_index] -= duration * data.agv.idle_energy[speed_index]
                battery_records[agv_index].append((start + duration, batteries[agv_index]))
            speed_index = chromosome.loaded_speed[flat]
            start = max(job_time[job_index], table[-1].start)
            duration = _distance(data, table[-1].from_machine, machine) / speed_values[speed_index]
            _append_agv(table, start, start + duration, job_index + 1, operation_index + 1, -2, machine)
            batteries[agv_index] -= duration * data.agv.loaded_energy[speed_index]
            battery_records[agv_index].append((start + duration, batteries[agv_index]))
            agv_complete = start + duration
        finish = _insert_machine(
            machines[machine - 1], agv_complete, option.processing_time,
            job_index + 1, operation_index + 1,
        )
        job_time[job_index] = finish
        job_position[job_index] = machine
        completion[job_index] = finish

    for table in machines:
        for index, block in enumerate(table):
            if block.job == -1:
                table[index] = replace(block, job=0)
    for key in fixed:
        block = next(block for table in machines for block in table if (block.job, block.opera) == key)
        completion[block.job - 1] = max(completion[block.job - 1], block.end)
    makespan = max(completion, default=0.0)
    machine_energy = sum(
        (block.end - block.start) * (
            data.resources.machine_idle_energy[index] if block.job == 0
            else data.resources.machine_work_energy[index]
        )
        for index, table in enumerate(machines) for block in table if not isinf(block.end)
    )
    agv_energy = sum(
        max(0.0, before[1] - after[1]) for records in battery_records
        for before, after in zip(records, records[1:])
    )
    return ScheduleResult(
        makespan, machine_energy, agv_energy, tuple(completion), tuple(charge_counts),
        tuple(tuple(table) for table in machines), tuple(tuple(table) for table in agvs),
        tuple(tuple(records) for records in battery_records),
    )


def _constrain_chromosome(
    data: ExperimentInput, candidate: Chromosome, original_chromosome: Chromosome,
    original_schedule: ScheduleResult, event: DynamicEvent, strategy: str,
) -> Chromosome:
    if strategy == "CS":
        return candidate
    ms = list(original_chromosome.ms)
    if event.kind == "machine_failure":
        offsets = []
        total = 0
        for count in data.instance.operation_counts:
            offsets.append(total)
            total += count
        for table in original_schedule.machine_tables[event.target - 1:event.target]:
            for block in table:
                if block.job and block.start >= event.time:
                    flat = offsets[block.job - 1] + block.opera - 1
                    ms[flat] = candidate.ms[flat]
    return Chromosome(candidate.os, tuple(ms), candidate.agv, candidate.empty_speed, candidate.loaded_speed)


def execute_rescheduling(
    data: ExperimentInput, original_chromosome: Chromosome,
    original_schedule: ScheduleResult, event: DynamicEvent, strategy: str, *,
    population_size: int = 100, generations: int = 200, seed: int,
    alpha: float = 0.1, gamma: float = 0.9,
    time_limit_seconds: float | None = None,
) -> DynamicOptimizationResult:
    """运行活动 MATLAB RS/CS 共同采用的动态 NSGA-II 主循环。"""
    if strategy not in {"RS", "CS"}:
        raise ValueError("动态优化策略必须是RS或CS")
    if generations <= 0 or population_size <= 0 or population_size % 10:
        raise ValueError("代数必须为正，种群规模必须是10的正整数倍")
    rng = random.Random(seed)
    population = [
        _constrain_chromosome(data, chromosome, original_chromosome, original_schedule, event, strategy)
        for chromosome in hybrid_population(data, population_size, len(data.agv.speeds), rng).chromosomes
    ]
    schedules = [_decode_dynamic(data, chromosome, original_schedule, event) for chromosome in population]
    objectives = [(schedule.makespan, schedule.machine_energy) for schedule in schedules]
    evaluations = len(population)
    qtable = [[0.0] * 6 for _ in range(4)]
    current_state = 3
    started = time.perf_counter()
    iteration_limit = generations if time_limit_seconds is None else 2_147_483_647
    for generation in range(iteration_limit):
        if time_limit_seconds is not None and generation > 0:
            if time.perf_counter() - started >= time_limit_seconds:
                break
        ranks, crowding = rank_and_crowding(objectives)
        parents = [
            population[index] for index in sorted(
                range(len(population)), key=lambda index: (ranks[index], -crowding[index])
            )[: max(2, population_size // 2)]
        ]
        offspring = [
            _constrain_chromosome(data, chromosome, original_chromosome, original_schedule, event, strategy)
            for chromosome in variation(
                parents, 0.8, 0.1, data.instance, data.agv.count, len(data.agv.speeds), rng
            )
        ]
        offspring_schedules = [
            _decode_dynamic(data, chromosome, original_schedule, event) for chromosome in offspring
        ]
        evaluations += len(offspring)
        candidates = population + offspring
        candidate_schedules = schedules + offspring_schedules
        candidate_objectives = [
            (schedule.makespan, schedule.machine_energy) for schedule in candidate_schedules
        ]
        selected = environmental_select(candidate_objectives, population_size)
        population = [candidates[index] for index in selected]
        schedules = [candidate_schedules[index] for index in selected]
        objectives = [candidate_objectives[index] for index in selected]

        middle = population_size // 2
        time_values = sorted(value[0] for value in objectives)
        energy_values = sorted(value[1] for value in objectives)
        time_boundary = sum(time_values[middle - 1:middle + 1]) / 2
        energy_boundary = sum(energy_values[middle - 1:middle + 1]) / 2
        maximum = [max(row[column] for row in objectives) for column in range(2)]
        minimum = [min(row[column] for row in objectives) for column in range(2)]
        groups = [[], [], [], []]
        for index in sorted(range(population_size), key=lambda item: objectives[item][0]):
            groups[state_of(objectives[index], time_boundary, energy_boundary)].append(index)
        accepted_chromosomes: list[Chromosome] = []
        accepted_schedules: list[ScheduleResult] = []
        for state, group in enumerate(groups):
            for index in group:
                action = select_action(
                    qtable, current_state,
                    epsilon(min(generation, generations - 1), generations), rng,
                )
                neighbor = _constrain_chromosome(
                    data,
                    apply_neighborhood(data, population[index], action, rng),
                    original_chromosome,
                    original_schedule,
                    event,
                    strategy,
                )
                neighbor_schedule = _decode_dynamic(
                    data, neighbor, original_schedule, event
                )
                evaluations += 1
                new_objective = (
                    neighbor_schedule.makespan, neighbor_schedule.machine_energy
                )
                old_objective = objectives[index]
                if not all(old <= new for old, new in zip(old_objective, new_objective)):
                    accepted_chromosomes.append(neighbor)
                    accepted_schedules.append(neighbor_schedule)
                current_state = state
                reward = reward_value(old_objective, new_objective, maximum, minimum)
                next_state = state_of(new_objective, time_boundary, energy_boundary)
                update_q(qtable, current_state, action, reward, next_state, alpha, gamma)
        candidates = population + accepted_chromosomes
        candidate_schedules = schedules + accepted_schedules
        candidate_objectives = [
            (schedule.makespan, schedule.machine_energy) for schedule in candidate_schedules
        ]
        selected = environmental_select(candidate_objectives, population_size)
        population = [candidates[index] for index in selected]
        schedules = [candidate_schedules[index] for index in selected]
        objectives = [candidate_objectives[index] for index in selected]
    pareto = pareto_indices(objectives)
    unique: dict[tuple[float, float], int] = {}
    for index in pareto:
        unique.setdefault(objectives[index], index)
    ordered = [unique[objective] for objective in sorted(unique)]
    return DynamicOptimizationResult(
        strategy,
        tuple(population[index] for index in ordered),
        tuple(objectives[index] for index in ordered),
        tuple(schedules[index] for index in ordered),
        evaluations,
        seed,
        tuple(tuple(row) for row in qtable),
    )


def validate_dynamic_schedule(
    data: ExperimentInput, chromosome: Chromosome, original: ScheduleResult,
    result: ScheduleResult, event: DynamicEvent,
) -> None:
    del data, chromosome
    cancelled = event.target if event.kind == "order_cancellation" else None
    original_ops = {
        (b.job, b.opera): b for table in original.machine_tables for b in table if b.job
    }
    result_ops = {
        (b.job, b.opera): b for table in result.machine_tables for b in table if b.job
    }
    expected = {key for key in original_ops if key[0] != cancelled}
    if set(result_ops) != expected:
        raise AssertionError("动态时间表的工序集合不正确")
    for key, block in original_ops.items():
        if key[0] != cancelled and block.end <= event.time:
            if result_ops[key] != block:
                raise AssertionError("已完成工序未保持固定")
    for tables in (result.machine_tables, result.agv_tables):
        for table in tables:
            previous = 0.0
            for block in table:
                if abs(block.start - previous) > 1e-8 or block.end < block.start:
                    raise AssertionError("动态资源时间表不连续或倒置")
                previous = block.end
    if event.kind.endswith("failure"):
        table = (
            result.machine_tables[event.target - 1]
            if event.kind == "machine_failure" else result.agv_tables[event.target - 1]
        )
        repair_end = event.time + event.duration
        if any(event.time <= block.start < repair_end and getattr(block, "job", 0) for block in table):
            raise AssertionError("故障资源在维修区间启动了新任务")
