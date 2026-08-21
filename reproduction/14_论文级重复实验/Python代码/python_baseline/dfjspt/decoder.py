"""按原 MATLAB sorting.m/fitness.m 实现静态解码与目标函数。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import inf, isinf
from typing import Any, Sequence

from .chromosome import Chromosome
from .data import ExperimentInput


@dataclass
class MachineBlock:
    start: float
    end: float
    job: int
    opera: int


@dataclass
class AGVBlock:
    start: float
    end: float
    job: int
    opera: int
    load_status: int
    from_machine: int
    to_machine: int
    charge: int


@dataclass(frozen=True)
class ScheduleResult:
    makespan: float
    machine_energy: float
    agv_energy: float
    job_completion: tuple[float, ...]
    charge_counts: tuple[int, ...]
    machine_tables: tuple[tuple[MachineBlock, ...], ...]
    agv_tables: tuple[tuple[AGVBlock, ...], ...]
    battery_records: tuple[tuple[tuple[float, float], ...], ...]

    def to_matlab_dict(self) -> dict[str, Any]:
        def block_dict(block: MachineBlock | AGVBlock) -> dict[str, Any]:
            payload = asdict(block)
            if isinf(payload["end"]):
                payload["end"] = None
            return payload

        return {
            "machine_tables": [[block_dict(b) for b in table] for table in self.machine_tables],
            "agv_tables": [[block_dict(b) for b in table] for table in self.agv_tables],
            "battery_records": [[list(record) for record in table] for table in self.battery_records],
        }


def _tick(value: float) -> int | float:
    return value if isinf(value) else round(value * 1_000_000)


def _distance(data: ExperimentInput, start: int, destination: int) -> float:
    resources = data.resources
    if start == destination:
        return 0.0
    if start == -1 and destination == -2:
        return resources.load_to_unload
    if start == -2 and destination == -1:
        return resources.load_to_unload
    if start == -1:
        return resources.load_to_machine[destination - 1]
    if destination == -1:
        return resources.load_to_machine[start - 1]
    if start == -2:
        return resources.machine_to_unload[destination - 1]
    if destination == -2:
        return resources.machine_to_unload[start - 1]
    return resources.machine_to_machine[start - 1][destination - 1]


def _append_agv(
    table: list[AGVBlock], start: float, end: float, job: int, opera: int,
    load_status: int, destination: int, charge: int = 0,
) -> None:
    idle = table.pop()
    if _tick(start) > _tick(idle.start):
        table.append(AGVBlock(idle.start, start, 0, 0, 0, idle.from_machine, idle.from_machine, 0))
    table.append(AGVBlock(start, end, job, opera, load_status, idle.from_machine, destination, charge))
    table.append(AGVBlock(end, inf, 0, 0, 0, destination, 0, 0))


def _insert_machine(
    table: list[MachineBlock], ready: float, duration: float, job: int, opera: int,
) -> float:
    for index, block in enumerate(table):
        if block.job != 0:
            continue
        start = max(block.start, ready)
        end = start + duration
        if end > block.end:
            continue
        parts: list[MachineBlock] = []
        if _tick(start) > _tick(block.start):
            parts.append(MachineBlock(block.start, start, 0, 0))
        parts.append(MachineBlock(start, end, job, opera))
        if _tick(end) < _tick(block.end):
            parts.append(MachineBlock(end, block.end, 0, 0))
        table[index:index + 1] = parts
        return end
    raise RuntimeError("未找到可插入机器工序的空闲块")


def decode_static(
    data: ExperimentInput,
    chromosome: Chromosome,
    speeds: Sequence[float] | None = None,
    *,
    return_finished_jobs: bool = False,
) -> ScheduleResult:
    """复现静态源码的左移解码、充电逻辑与两个论文目标。"""
    speed_values = tuple(data.agv.speeds if speeds is None else speeds)
    chromosome.validate(data.instance, data.agv.count, len(speed_values))
    if len(speed_values) != len(data.agv.idle_energy):
        raise ValueError("速度档位数量必须与AGV能耗档位数量一致")
    if return_finished_jobs and len(speed_values) < 3:
        raise ValueError("成品返回卸载站需要MATLAB固定第三速度档位")

    machines = [[MachineBlock(0.0, inf, 0, 0)] for _ in range(data.instance.machine_count)]
    agvs = [[AGVBlock(0.0, inf, 0, 0, 0, -1, 0, 0)] for _ in range(data.agv.count)]
    batteries = [data.agv.maximum_energy] * data.agv.count
    battery_records: list[list[tuple[float, float]]] = [
        [(0.0, data.agv.maximum_energy)] for _ in range(data.agv.count)
    ]
    charge_counts = [0] * data.agv.count
    job_time = [0.0] * data.instance.job_count
    job_position = [-1] * data.instance.job_count
    job_next_operation = [0] * data.instance.job_count
    completion = [0.0] * data.instance.job_count
    offsets: list[int] = []
    total = 0
    for count in data.instance.operation_counts:
        offsets.append(total)
        total += count

    for job_index in chromosome.os:
        operation_index = job_next_operation[job_index]
        flat = offsets[job_index] + operation_index
        option = data.instance.jobs[job_index].operations[operation_index].options[chromosome.ms[flat]]
        machine = option.machine_id
        agv_index = chromosome.agv[flat]
        job_number = job_index + 1
        operation_number = operation_index + 1

        # sorting.m 在解码每道工序前遍历并充满所有低电量AGV。
        for current in range(data.agv.count):
            if batteries[current] > data.agv.minimum_energy:
                continue
            table = agvs[current]
            start_machine = table[-1].from_machine
            if start_machine != -2:
                start = table[-1].start
                charging_speed = data.agv.charging_travel_speed or speed_values[2]
                duration = _distance(data, start_machine, -2) / charging_speed
                end = start + duration
                _append_agv(table, start, end, 0, 0, -1, -2, 2)
                charging_energy = (
                    data.agv.idle_energy[0]
                    if data.agv.charging_travel_speed is not None
                    else data.agv.idle_energy[2]
                )
                batteries[current] -= duration * charging_energy
                battery_records[current].append((end, batteries[current]))
            start = agvs[current][-1].start
            duration = (data.agv.maximum_energy - batteries[current]) / data.agv.charging_power
            end = start + duration
            _append_agv(agvs[current], start, end, 0, 0, 0, -2, 1)
            batteries[current] = data.agv.maximum_energy
            battery_records[current].append((end, batteries[current]))
            charge_counts[current] += 1

        agv_table = agvs[agv_index]
        source = job_position[job_index]
        if source != machine:
            speed_index = chromosome.empty_speed[flat]
            start = agv_table[-1].start
            duration = _distance(data, agv_table[-1].from_machine, source) / speed_values[speed_index]
            if duration > 1e-6:
                end = start + duration
                _append_agv(agv_table, start, end, job_number, operation_number, -1, source)
                batteries[agv_index] -= duration * data.agv.idle_energy[speed_index]
                battery_records[agv_index].append((end, batteries[agv_index]))

            speed_index = chromosome.loaded_speed[flat]
            start = max(job_time[job_index], agv_table[-1].start)
            duration = _distance(data, agv_table[-1].from_machine, machine) / speed_values[speed_index]
            end = start + duration
            _append_agv(agv_table, start, end, job_number, operation_number, -2, machine)
            batteries[agv_index] -= duration * data.agv.loaded_energy[speed_index]
            battery_records[agv_index].append((end, batteries[agv_index]))
            agv_complete = end
        else:
            agv_complete = job_time[job_index]

        finish = _insert_machine(
            machines[machine - 1], agv_complete, option.processing_time,
            job_number, operation_number,
        )
        job_time[job_index] = finish
        job_position[job_index] = machine
        job_next_operation[job_index] += 1
        if job_next_operation[job_index] == data.instance.operation_counts[job_index]:
            if not return_finished_jobs:
                completion[job_index] = finish
                continue

            arrivals = [
                table[-1].start
                + _distance(data, table[-1].from_machine, machine) / speed_values[2]
                for table in agvs
            ]
            leave_times = [max(finish, arrival) for arrival in arrivals]
            earliest = min(leave_times)
            candidates = [
                index for index, leave in enumerate(leave_times)
                if _tick(leave) == _tick(earliest)
            ]
            return_agv = max(candidates, key=lambda index: arrivals[index])
            return_table = agvs[return_agv]
            if return_table[-1].from_machine != machine:
                start = return_table[-1].start
                end = arrivals[return_agv]
                _append_agv(
                    return_table, start, end, job_number, -1, -1, machine
                )
                batteries[return_agv] -= (end - start) * data.agv.idle_energy[2]
                battery_records[return_agv].append((end, batteries[return_agv]))
            start = max(arrivals[return_agv], finish)
            end = start + _distance(data, machine, -2) / speed_values[2]
            _append_agv(return_table, start, end, job_number, -1, -2, -2)
            batteries[return_agv] -= (end - start) * data.agv.loaded_energy[2]
            battery_records[return_agv].append((end, batteries[return_agv]))
            completion[job_index] = end

    machine_energy = 0.0
    for machine_index, table in enumerate(machines):
        for block in table:
            if isinf(block.end):
                continue
            rate = (
                data.resources.machine_idle_energy[machine_index]
                if block.job == 0 else data.resources.machine_work_energy[machine_index]
            )
            machine_energy += (block.end - block.start) * rate
    agv_energy = sum(
        max(0.0, before[1] - after[1])
        for records in battery_records
        for before, after in zip(records, records[1:])
    )
    return ScheduleResult(
        max(completion), machine_energy, agv_energy, tuple(completion), tuple(charge_counts),
        tuple(tuple(table) for table in machines), tuple(tuple(table) for table in agvs),
        tuple(tuple(records) for records in battery_records),
    )


def validate_schedule(
    data: ExperimentInput, chromosome: Chromosome, result: ScheduleResult,
) -> None:
    """检查工序完整性、加工时长、工件优先约束及资源不重叠。"""
    chromosome.validate(data.instance, data.agv.count, len(data.agv.speeds))
    seen: dict[tuple[int, int], MachineBlock] = {}
    for table in result.machine_tables:
        previous = 0.0
        for block in table:
            if _tick(block.start) != _tick(previous):
                raise AssertionError("机器时间块不连续")
            if block.end < block.start:
                raise AssertionError("机器时间块倒置")
            previous = block.end
            if block.job:
                key = (block.job, block.opera)
                if key in seen:
                    raise AssertionError("工序被重复加工")
                seen[key] = block
    expected_count = data.instance.operation_count
    if len(seen) != expected_count:
        raise AssertionError(f"加工工序数应为 {expected_count}，实际为 {len(seen)}")
    for job_index, job in enumerate(data.instance.jobs, start=1):
        prior_end = 0.0
        for operation_index, operation in enumerate(job.operations, start=1):
            block = seen[(job_index, operation_index)]
            if block.start + 1e-9 < prior_end:
                raise AssertionError("工件工序优先关系被破坏")
            durations = {option.processing_time for option in operation.options}
            if not any(abs((block.end - block.start) - duration) <= 1e-9 for duration in durations):
                raise AssertionError("加工持续时间不属于该工序候选时间")
            prior_end = block.end
    for table in result.agv_tables:
        previous = 0.0
        for block in table:
            if _tick(block.start) != _tick(previous) or block.end < block.start:
                raise AssertionError("AGV时间块不连续或倒置")
            previous = block.end
