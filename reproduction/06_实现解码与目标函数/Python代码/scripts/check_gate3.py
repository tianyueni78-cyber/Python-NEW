"""检查Gate 3：Python解码是否与MATLAB固定参照一致。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from python_baseline.dfjspt.chromosome import Chromosome
from python_baseline.dfjspt.data import load_experiment_input
from python_baseline.dfjspt.decoder import decode_static, validate_schedule


def check_gate3() -> dict[str, object]:
    data_root = REPO_ROOT / "python_baseline" / "data"
    reference = json.loads((data_root / "matlab_reference" / "Mk05_decoder_reference.json").read_text(encoding="utf-8"))
    data = load_experiment_input(
        data_root / "brandimarte" / "Mk05.fjs",
        data_root / "resources" / "static_algorithm_comparison.json",
    )
    chromosome = Chromosome.from_matlab_row(reference["chromosome_matlab_1_based"], data.instance.operation_count)
    result = decode_static(data, chromosome)
    validate_schedule(data, chromosome, result)
    actual = result.to_matlab_dict()
    objectives_match = all(abs(left - right) <= 1e-9 for left, right in (
        (result.makespan, reference["makespan"]),
        (result.machine_energy, reference["machine_energy"]),
        (result.agv_energy, reference["agv_energy"]),
    ))
    tables_match = actual == {
        "machine_tables": reference["machine_tables"],
        "agv_tables": reference["agv_tables"],
        "battery_records": reference["battery_records"],
    }
    passed = objectives_match and tables_match
    return {
        "Gate": "Gate 3：解码一致",
        "结论": "通过" if passed else "未通过",
        "固定实例": "Mk05",
        "目标值一致": objectives_match,
        "机器时间表一致": actual["machine_tables"] == reference["machine_tables"],
        "AGV时间表一致": actual["agv_tables"] == reference["agv_tables"],
        "电量轨迹一致": actual["battery_records"] == reference["battery_records"],
        "makespan": result.makespan,
        "machine_energy": result.machine_energy,
        "agv_energy（记录但不属于论文第二目标）": result.agv_energy,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="检查Gate 3")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = check_gate3()
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    if report["结论"] != "通过":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
