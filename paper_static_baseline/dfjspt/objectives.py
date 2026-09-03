"""本文静态baseline的唯一目标定义。"""

from .decoder import ScheduleResult


def evaluate_objectives(schedule: ScheduleResult) -> tuple[float, float]:
    """返回Makespan与机器加工、空闲能耗之和。"""
    return schedule.makespan, schedule.machine_energy

