"""从JSON配置运行可追溯批量实验。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_baseline.dfjspt.experiments import ExperimentSpec, run_batch


def main() -> int:
    parser = argparse.ArgumentParser(description="运行论文Python baseline批量实验")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.config.read_text("utf-8"))
    specs = [ExperimentSpec(**row) for row in payload["runs"]]
    results = run_batch(specs, args.output, ROOT / "python_baseline" / "data")
    print(f"Completed {len(results)} tracked runs in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
