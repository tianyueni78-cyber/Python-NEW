"""运行 Gate 1：比较 Python 输入与原 MATLAB benchmarkRead 输出。"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from python_baseline.dfjspt.data import load_brandimarte, load_experiment_input


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(data_root: Path) -> dict[str, object]:
    results: list[dict[str, object]] = []
    for index in range(1, 11):
        name = f"Mk{index:02d}"
        source = data_root / "brandimarte" / f"{name}.fjs"
        reference_path = data_root / "matlab_reference" / f"{name}.json"
        instance = load_brandimarte(source)
        reference = json.loads(reference_path.read_text(encoding="utf-8"))
        matched = instance.to_matlab_dict() == reference
        results.append(
            {
                "实例": name,
                "工件数": instance.job_count,
                "机器数": instance.machine_count,
                "工序数": instance.operation_count,
                "FJS_SHA256": sha256(source),
                "MATLAB逐项一致": matched,
            }
        )

    mk05 = load_experiment_input(
        data_root / "brandimarte" / "Mk05.fjs",
        data_root / "resources" / "static_algorithm_comparison.json",
    )
    return {
        "Gate": "Gate 1：输入一致",
        "结论": "通过" if all(item["MATLAB逐项一致"] for item in results) else "不通过",
        "比较范围": "工件数、机器数、各工件工序数、每道工序候选机器及对应加工时间",
        "实例结果": results,
        "资源层检查": {
            "Mk05机器数": mk05.instance.machine_count,
            "截取后距离矩阵阶数": len(mk05.resources.machine_to_machine),
            "AGV数": mk05.agv.count,
            "源码最低能量检查计算值": mk05.source_minimum_energy_check(),
            "源码AGV最低能量": mk05.agv.minimum_energy,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="执行 Gate 1 输入一致性检查")
    parser.add_argument("--data-root", type=Path, default=Path("python_baseline/data"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = check(args.data_root)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    if report["结论"] != "通过":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
