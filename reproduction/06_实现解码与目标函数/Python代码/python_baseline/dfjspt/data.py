"""与 MATLAB 输入语义一致的 DFJSP-T 数据层。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class DataFormatError(ValueError):
    """输入文件的结构或数值违反论文源码约定。"""


@dataclass(frozen=True)
class MachineOption:
    machine_id: int
    processing_time: float


@dataclass(frozen=True)
class Operation:
    options: tuple[MachineOption, ...]


@dataclass(frozen=True)
class Job:
    operations: tuple[Operation, ...]


@dataclass(frozen=True)
class FJSPInstance:
    name: str
    machine_count: int
    jobs: tuple[Job, ...]

    @property
    def job_count(self) -> int:
        return len(self.jobs)

    @property
    def operation_counts(self) -> tuple[int, ...]:
        return tuple(len(job.operations) for job in self.jobs)

    @property
    def operation_count(self) -> int:
        return sum(self.operation_counts)

    def validate(self) -> None:
        if self.machine_count <= 0 or not self.jobs:
            raise DataFormatError("工件数和机器数必须为正数")
        for job_id, job in enumerate(self.jobs, start=1):
            if not job.operations:
                raise DataFormatError(f"工件 {job_id} 没有工序")
            for operation_id, operation in enumerate(job.operations, start=1):
                if not operation.options:
                    raise DataFormatError(f"工件 {job_id} 工序 {operation_id} 没有候选机器")
                machine_ids = [option.machine_id for option in operation.options]
                if len(machine_ids) != len(set(machine_ids)):
                    raise DataFormatError(f"工件 {job_id} 工序 {operation_id} 存在重复机器")
                for option in operation.options:
                    if not 1 <= option.machine_id <= self.machine_count:
                        raise DataFormatError(f"机器编号 {option.machine_id} 超出范围")
                    if option.processing_time <= 0:
                        raise DataFormatError("加工时间必须为正数")

    def to_matlab_dict(self) -> dict[str, Any]:
        """生成不含 Inf、可稳定 JSON 化的 MATLAB 对照表示。"""
        operations: list[dict[str, Any]] = []
        for job_id, job in enumerate(self.jobs, start=1):
            for operation_id, operation in enumerate(job.operations, start=1):
                operations.append(
                    {
                        "job_id": job_id,
                        "operation_id": operation_id,
                        "candidate_machines": [item.machine_id for item in operation.options],
                        "processing_times": [item.processing_time for item in operation.options],
                    }
                )
        return {
            "job_count": self.job_count,
            "machine_count": self.machine_count,
            "operation_counts": list(self.operation_counts),
            "operations": operations,
        }


@dataclass(frozen=True)
class ResourceParameters:
    load_to_machine: tuple[float, ...]
    machine_to_unload: tuple[float, ...]
    machine_to_machine: tuple[tuple[float, ...], ...]
    load_to_unload: float
    machine_work_energy: tuple[float, ...]
    machine_idle_energy: tuple[float, ...]

    def for_machine_count(self, count: int) -> "ResourceParameters":
        if count > len(self.machine_work_energy):
            raise DataFormatError(f"资源参数只有 {len(self.machine_work_energy)} 台机器，实例需要 {count} 台")
        return ResourceParameters(
            self.load_to_machine[:count],
            self.machine_to_unload[:count],
            tuple(row[:count] for row in self.machine_to_machine[:count]),
            self.load_to_unload,
            self.machine_work_energy[:count],
            self.machine_idle_energy[:count],
        )

    def validate(self) -> None:
        count = len(self.machine_work_energy)
        vectors = (self.load_to_machine, self.machine_to_unload, self.machine_idle_energy)
        if count == 0 or any(len(vector) != count for vector in vectors):
            raise DataFormatError("机器资源向量长度不一致")
        if len(self.machine_to_machine) != count or any(
            len(row) != count for row in self.machine_to_machine
        ):
            raise DataFormatError("机器距离矩阵不是与机器数一致的方阵")
        values = (
            *self.load_to_machine,
            *self.machine_to_unload,
            *self.machine_work_energy,
            *self.machine_idle_energy,
        )
        if any(value < 0 for value in values) or self.load_to_unload < 0:
            raise DataFormatError("距离和能耗不能为负数")


@dataclass(frozen=True)
class AGVParameters:
    count: int
    speeds: tuple[float, ...]
    idle_energy: tuple[float, ...]
    loaded_energy: tuple[float, ...]
    minimum_energy: float = 16.8
    maximum_energy: float = 100.0
    charging_power: float = 20.0

    def validate(self) -> None:
        if self.count <= 0:
            raise DataFormatError("AGV 数量必须为正数")
        if not self.speeds or any(
            len(values) != len(self.speeds)
            for values in (self.idle_energy, self.loaded_energy)
        ):
            raise DataFormatError("AGV速度和两类能耗档位长度必须一致")
        if any(speed <= 0 for speed in self.speeds):
            raise DataFormatError("AGV 速度必须为正数")
        if not 0 <= self.minimum_energy < self.maximum_energy:
            raise DataFormatError("AGV 能量上下限无效")


@dataclass(frozen=True)
class ExperimentInput:
    instance: FJSPInstance
    resources: ResourceParameters
    agv: AGVParameters

    def validate(self) -> None:
        self.instance.validate()
        self.resources.validate()
        self.agv.validate()

    def source_minimum_energy_check(self) -> float:
        """返回 dif_main.m 用于检查 AGV 下限的原始表达式计算值。"""
        max_distance = max(
            self.resources.load_to_unload,
            *self.resources.load_to_machine,
            *self.resources.machine_to_unload,
            *(value for row in self.resources.machine_to_machine for value in row),
        )
        return max_distance / self.agv.speeds[-1] * (
            self.agv.idle_energy[-1] + self.agv.loaded_energy[-1]
        )


def _integer(token: str, label: str) -> int:
    try:
        value = int(token)
    except ValueError as error:
        raise DataFormatError(f"{label} 不是整数：{token}") from error
    return value


def load_brandimarte(path: str | Path) -> FJSPInstance:
    """按 benchmarkRead.m 的“一行一个工件”规则读取 Brandimarte 文件。"""
    source = Path(path)
    lines = [line.split() for line in source.read_text(encoding="ascii").splitlines() if line.strip()]
    if not lines or len(lines[0]) < 2:
        raise DataFormatError("首行缺少工件数或机器数")
    job_count = _integer(lines[0][0], "工件数")
    machine_count = _integer(lines[0][1], "机器数")
    if len(lines) != job_count + 1:
        raise DataFormatError(f"声明 {job_count} 个工件，实际读取到 {len(lines) - 1} 行")

    jobs: list[Job] = []
    for job_id, tokens in enumerate(lines[1:], start=1):
        operation_count = _integer(tokens[0], f"工件 {job_id} 工序数")
        cursor = 1
        operations: list[Operation] = []
        for operation_id in range(1, operation_count + 1):
            if cursor >= len(tokens):
                raise DataFormatError(f"工件 {job_id} 工序 {operation_id} 数据截断")
            option_count = _integer(tokens[cursor], "候选机器数")
            cursor += 1
            options: list[MachineOption] = []
            for _ in range(option_count):
                if cursor + 1 >= len(tokens):
                    raise DataFormatError(f"工件 {job_id} 工序 {operation_id} 候选数据截断")
                machine_id = _integer(tokens[cursor], "机器编号")
                try:
                    processing_time = float(tokens[cursor + 1])
                except ValueError as error:
                    raise DataFormatError(f"加工时间不是数值：{tokens[cursor + 1]}") from error
                options.append(MachineOption(machine_id, processing_time))
                cursor += 2
            # benchmarkRead.m 先写入机器列，再用 find(... < Inf) 生成候选集；
            # find 会按机器编号升序返回，后续染色体索引依赖这个顺序。
            options.sort(key=lambda item: item.machine_id)
            operations.append(Operation(tuple(options)))
        if cursor != len(tokens):
            raise DataFormatError(f"工件 {job_id} 行末存在 {len(tokens) - cursor} 个多余字段")
        jobs.append(Job(tuple(operations)))

    instance = FJSPInstance(source.stem, machine_count, tuple(jobs))
    instance.validate()
    return instance


def load_resource_parameters(path: str | Path) -> ResourceParameters:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    resources = ResourceParameters(
        tuple(payload["load_to_machine"]),
        tuple(payload["machine_to_unload"]),
        tuple(tuple(row) for row in payload["machine_to_machine"]),
        payload["load_to_unload"],
        tuple(payload["machine_work_energy"]),
        tuple(payload["machine_idle_energy"]),
    )
    resources.validate()
    return resources


def _agv_parameters(job_count: int) -> AGVParameters:
    count_by_jobs = {10: 3, 15: 4, 20: 5}
    try:
        count = count_by_jobs[job_count]
    except KeyError as error:
        raise DataFormatError(f"实验协议未定义 {job_count} 个工件对应的 AGV 数量") from error
    return AGVParameters(
        count=count,
        speeds=(1.0,) * 4,
        idle_energy=(0.6,) * 4,
        loaded_energy=(1.5,) * 4,
    )


def load_experiment_input(instance_path: str | Path, resource_path: str | Path) -> ExperimentInput:
    instance = load_brandimarte(instance_path)
    resources = load_resource_parameters(resource_path).for_machine_count(instance.machine_count)
    data = ExperimentInput(instance, resources, _agv_parameters(instance.job_count))
    data.validate()
    return data
