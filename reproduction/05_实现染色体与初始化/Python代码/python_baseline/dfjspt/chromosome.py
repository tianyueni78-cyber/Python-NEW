"""静态 MATLAB 五段染色体的 Python 表示。"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from .data import FJSPInstance


class ChromosomeError(ValueError):
    """染色体的长度、计数或基因范围不合法。"""


@dataclass(frozen=True)
class Chromosome:
    """内部统一使用0起始索引；MATLAB边界显式转换为1起始。"""

    os: tuple[int, ...]
    ms: tuple[int, ...]
    agv: tuple[int, ...]
    empty_speed: tuple[int, ...]
    loaded_speed: tuple[int, ...]

    @property
    def operation_count(self) -> int:
        return len(self.os)

    @property
    def length(self) -> int:
        return sum(len(segment) for segment in self.segments)

    @property
    def segments(self) -> tuple[tuple[int, ...], ...]:
        return self.os, self.ms, self.agv, self.empty_speed, self.loaded_speed

    @classmethod
    def from_matlab_row(cls, row: Sequence[int | float], operation_count: int) -> "Chromosome":
        if len(row) != 5 * operation_count:
            raise ChromosomeError(
                f"MATLAB染色体长度应为 {5 * operation_count}，实际为 {len(row)}"
            )
        values = tuple(int(value) - 1 for value in row)
        segments = tuple(
            values[index * operation_count : (index + 1) * operation_count]
            for index in range(5)
        )
        return cls(*segments)

    def to_matlab_row(self) -> list[int]:
        return [gene + 1 for segment in self.segments for gene in segment]

    def validate(self, instance: FJSPInstance, agv_count: int, speed_count: int) -> None:
        operation_count = instance.operation_count
        if any(len(segment) != operation_count for segment in self.segments):
            raise ChromosomeError("五个染色体分段长度必须都等于总工序数")

        expected = Counter(
            job_id
            for job_id, count in enumerate(instance.operation_counts)
            for _ in range(count)
        )
        if Counter(self.os) != expected:
            raise ChromosomeError("OS中的工件出现次数与各工件工序数不一致")

        operation_index = 0
        for job in instance.jobs:
            for operation in job.operations:
                if not 0 <= self.ms[operation_index] < len(operation.options):
                    raise ChromosomeError(f"MS位置 {operation_index} 超出候选机器索引范围")
                operation_index += 1

        if any(not 0 <= gene < agv_count for gene in self.agv):
            raise ChromosomeError("AS中存在超出AGV编号范围的基因")
        if any(
            not 0 <= gene < speed_count
            for segment in (self.empty_speed, self.loaded_speed)
            for gene in segment
        ):
            raise ChromosomeError("速度段中存在超出速度档位范围的基因")
