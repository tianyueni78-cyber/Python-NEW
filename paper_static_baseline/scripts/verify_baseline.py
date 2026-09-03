"""独立验收静态QNSGA-II A0冻结包并生成验证证据。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = REPO / "paper_static_baseline"
REQUIRED = (
    "BASELINE_SPEC.md",
    "BASELINE_ACCEPTANCE_CHECKLIST.md",
    "README.md",
    "config/paper_static_v1.json",
    "dfjspt/qnsga2.py",
    "dfjspt/decoder.py",
    "scripts/run_a0.py",
    "evidence/baseline_identity.md",
    "evidence/source_and_isolation.md",
    "evidence/deterministic_validation.md",
    "evidence/A0_与新方法差异表.md",
)
TEST_MODULES = (
    "paper_static_baseline.tests.test_static_identity",
    "paper_static_baseline.tests.test_unified_objectives",
    "paper_static_baseline.tests.test_a0_contract",
    "paper_static_baseline.tests.test_run_a0",
    "paper_static_baseline.tests.test_innovation_firewall",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    return parser.parse_args()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    root = parse_args().root.resolve()
    missing = [relative for relative in REQUIRED if not (root / relative).is_file()]
    if missing:
        print("缺少P02验收文件：" + "、".join(missing), file=sys.stderr)
        return 1
    if root != DEFAULT_ROOT.resolve():
        print("非默认冻结包仅执行完整性检查。")
        return 0

    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    test_command = [sys.executable, "-m", "unittest", *TEST_MODULES, "-v"]
    tested = subprocess.run(
        test_command, cwd=REPO, capture_output=True, text=True, encoding="utf-8",
        env=environment,
    )
    if tested.returncode:
        print(tested.stdout, file=sys.stderr)
        print(tested.stderr, file=sys.stderr)
        return tested.returncode

    runtime = root / "tests" / "_runtime"
    token = uuid.uuid4().hex
    first = runtime / f"verify-first-{token}"
    second = runtime / f"verify-second-{token}"
    base_command = [
        sys.executable, str(root / "scripts" / "run_a0.py"),
        "--instance", "Mk01", "--population", "10", "--generations", "2",
        "--seed", "20260817",
    ]
    for output in (first, second):
        completed = subprocess.run(
            [*base_command, "--output", str(output)], cwd=REPO,
            capture_output=True, text=True, encoding="utf-8", env=environment,
        )
        if completed.returncode:
            print(completed.stderr, file=sys.stderr)
            return completed.returncode
    left = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
    right = json.loads((second / "manifest.json").read_text(encoding="utf-8"))
    if left != right:
        print("固定种子重复运行结果不一致。", file=sys.stderr)
        return 1

    excluded = {"evidence/manifest.sha256", "evidence/validation_report.md"}
    records = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in excluded or "/_runtime/" in f"/{relative}" or "__pycache__" in relative:
            continue
        records.append(f"{digest(path)}  {relative}")
    (root / "evidence" / "manifest.sha256").write_text("\n".join(records) + "\n", encoding="utf-8")
    report = f"""# P02 A0独立验证报告

## 结论

静态QNSGA-II A0冻结包通过独立自动验收：{len(TEST_MODULES)}个测试模块全部通过；同一固定种子双次完整运行的清单逐字段一致；冻结文件已生成SHA-256记录。

## 验证范围

- 静态边界与动态代码隔离；
- 40/30/30初始化、五段染色体、完整解码和统一目标；
- 遗传、多目标选择、Q-learning与N1–N6行为；
- 可重复运行命令、随机种子和真实完整解码次数记录；
- A0与Top-K、`(K,N,b)`新方法的创新防火墙；
- 文件完整性记录。

## 运行结果

- 测试模块数：{len(TEST_MODULES)}
- 固定种子：20260817
- 实例：Mk01
- 种群：10
- 代数：2
- 完整解码次数：{left['full_decode_evaluations']}
- Pareto解数量：{len(left['pareto_objectives'])}
- 验收状态：通过
"""
    (root / "evidence" / "validation_report.md").write_text(report, encoding="utf-8")
    print(root / "evidence" / "validation_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
