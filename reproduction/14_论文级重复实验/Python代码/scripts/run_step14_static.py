"""运行第14步静态对比与消融正式网格，支持按实例分片和断点续跑。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_baseline.dfjspt.experiments import formal_static_specs, run_batch


def select_specs(specs, *, instance=None, repeat=None, algorithms=None):
    if instance:
        specs = [spec for spec in specs if spec.instance == instance]
    if repeat:
        specs = [spec for spec in specs if spec.repeat == repeat]
    if algorithms:
        specs = [spec for spec in specs if spec.algorithm in algorithms]
    return specs


def main() -> int:
    parser = argparse.ArgumentParser(description="第14步静态论文规模重复实验")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--instance", choices=[f"Mk{i:02d}" for i in range(1, 11)])
    parser.add_argument("--repeat", type=int, choices=range(1, 21))
    parser.add_argument(
        "--algorithm", action="append",
        choices=[
            "qnsga2", "nsga2", "moead", "mopso", "ablation_A",
            "ablation_B", "ablation_C", "ablation_full",
        ],
    )
    parser.add_argument("--budget-source", type=Path)
    args = parser.parse_args()
    specs = select_specs(
        formal_static_specs(), instance=args.instance, repeat=args.repeat,
        algorithms=set(args.algorithm) if args.algorithm else None,
    )
    print(f"准备运行或恢复 {len(specs)} 个静态正式实验。", flush=True)
    results = run_batch(
        specs, args.output, ROOT / "python_baseline" / "data", resume=True,
        budget_source_output=args.budget_source,
    )
    print(f"当前目录累计成功 {len(results)} 个实验：{args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
