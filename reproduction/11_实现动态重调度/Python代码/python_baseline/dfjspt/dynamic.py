"""三类动态事件的状态继承与 MATLAB IS/RS/CS 策略边界。"""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import inf, isinf

from .chromosome import Chromosome
from .data import ExperimentInput
from .decoder import AGVBlock, MachineBlock, ScheduleResult


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
