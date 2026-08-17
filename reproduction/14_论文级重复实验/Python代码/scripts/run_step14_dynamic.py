"""运行第14步20个动态场景，支持按场景和重复编号分片恢复。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_baseline.dfjspt.dynamic_experiments import (
    formal_dynamic_scenarios, run_dynamic_batch,
)


def main() -> int:
    scenarios = formal_dynamic_scenarios()
    parser = argparse.ArgumentParser(description="第14步动态论文规模重复实验")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scenario", choices=[item.scenario_id for item in scenarios])
    parser.add_argument("--repeat", type=int, choices=range(1, 21))
    args = parser.parse_args()
    if args.scenario:
        scenarios = [item for item in scenarios if item.scenario_id == args.scenario]
    repeats = [args.repeat] if args.repeat else list(range(1, 21))
    print(
        f"准备运行或恢复 {len(scenarios) * len(repeats)} 个动态场景重复。",
        flush=True,
    )
    completed = run_dynamic_batch(
        scenarios, repeats, args.output, ROOT / "python_baseline" / "data"
    )
    print(f"当前目录累计成功 {completed} 个动态场景重复。", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
