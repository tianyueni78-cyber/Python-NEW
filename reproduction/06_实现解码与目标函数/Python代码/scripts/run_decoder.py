"""独立运行第6步静态解码器。"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from python_baseline.dfjspt.data import load_experiment_input
from python_baseline.dfjspt.decoder import decode_static, validate_schedule
from python_baseline.dfjspt.initialization import hybrid_population


def run_decoder(instance_name: str, seed: int) -> dict[str, object]:
    if not re.fullmatch(r"Mk(?:0[1-9]|10)", instance_name):
        raise ValueError("实例名称必须是 Mk01—Mk10")
    data_root = REPO_ROOT / "python_baseline" / "data"
    data = load_experiment_input(
        data_root / "brandimarte" / f"{instance_name}.fjs",
        data_root / "resources" / "static_algorithm_comparison.json",
    )
    chromosome = hybrid_population(data, 10, 4, random.Random(seed)).chromosomes[0]
    result = decode_static(data, chromosome)
    validate_schedule(data, chromosome, result)
    return {
        "instance": instance_name,
        "seed": seed,
        "chromosome_matlab_1_based": chromosome.to_matlab_row(),
        "makespan": result.makespan,
        "machine_energy": result.machine_energy,
        "agv_energy": result.agv_energy,
        "job_completion": list(result.job_completion),
        "charge_counts": list(result.charge_counts),
        **result.to_matlab_dict(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="运行静态DFJSP-T解码和目标函数")
    parser.add_argument("--instance", default="Mk05")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_decoder(args.instance, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"解码完成：makespan={result['makespan']}，machine_energy={result['machine_energy']}")


if __name__ == "__main__":
    main()
