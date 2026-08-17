"""把原 MATLAB 使用的“机器数据.xlsx”转换为稳定的 JSON 输入。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def convert_workbook(source: str | Path, output: str | Path) -> None:
    try:
        from openpyxl import load_workbook
    except ImportError as error:
        raise RuntimeError("转换 xlsx 需要安装 openpyxl；运行 baseline 本身不需要") from error

    workbook = load_workbook(source, data_only=True, read_only=True)
    coordinates = [
        (float(row[0]), float(row[1]))
        for row in workbook["机器仓库坐标"].values
        if isinstance(row[0], (int, float)) and isinstance(row[1], (int, float))
    ]
    machine_count = len(coordinates) - 2

    def distance(left: tuple[float, float], right: tuple[float, float]) -> float:
        return abs(left[0] - right[0]) + abs(left[1] - right[1])

    machines = coordinates[2:]
    payload = {
        "source_workbook": Path(source).name,
        "source_sha256": hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        "distance_rule": "distance_from_xy.m: Manhattan distance from machine warehouse coordinates",
        # distance_from_xy.m 每次运行都会由坐标覆盖这两个工作表，
        # 因而不能使用工作簿中上一次（可能机器数不同）的残留矩阵。
        "load_to_machine": [distance(coordinates[0], machine) for machine in machines],
        "machine_to_unload": [distance(coordinates[1], machine) for machine in machines],
        "machine_to_machine": [
            [distance(left, right) for right in machines] for left in machines
        ],
        "load_to_unload": float(next(workbook["装载站到卸载站距离"].values)[0]),
        "machine_work_energy": [float(row[0]) for row in workbook["机器加工能耗"].values if isinstance(row[0], (int, float))],
        "machine_idle_energy": [float(row[0]) for row in workbook["机器空载能耗"].values if isinstance(row[0], (int, float))],
    }
    if machine_count != len(payload["machine_work_energy"]):
        raise ValueError("机器坐标数与机器能耗参数数不一致")
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="转换 MATLAB 机器资源工作簿")
    parser.add_argument("source")
    parser.add_argument("output")
    args = parser.parse_args()
    convert_workbook(args.source, args.output)


if __name__ == "__main__":
    main()
