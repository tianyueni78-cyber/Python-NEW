# paper-static-baseline-v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在独立目录中建立、验证并冻结本文统一目标的静态QNSGA-II基线A0。

**Architecture:** 从现有权威Python实现机械复制静态核心，删除动态入口，以单一`evaluate_objectives`函数统一A0和对照算法的目标。原实现不修改；新目录用自身数据、测试、运行入口、验证报告和哈希形成可独立冻结的快照。

**Tech Stack:** Python 3标准库、`unittest`、Git、SHA-256。

**Spec:** `docs/superpowers/specs/2026-09-03-paper-static-baseline-v1-design.md`

## Global Constraints

- 不修改`python_baseline/`、`original_matlab/`和历史结果。
- A0为原QNSGA-II静态方法，不含任何Top-K或`(K,N,b)`创新。
- 所有算法统一使用`(makespan, machine_energy)`。
- AGV电量、运输和充电行为保留；`agv_energy`只记录、不优化。
- 不复制动态调度模块；不新增依赖；不运行论文规模正式实验。

---

### Task 1: 建立静态包与身份合同

**Files:**
- Create: `paper_static_baseline/README.md`
- Create: `paper_static_baseline/BASELINE_SPEC.md`
- Create: `paper_static_baseline/config/paper_static_v1.json`
- Create: `paper_static_baseline/tests/test_static_identity.py`
- Copy: `python_baseline/data/` to `paper_static_baseline/data/`
- Copy selected static modules from `python_baseline/dfjspt/` to `paper_static_baseline/dfjspt/`

**Interfaces:**
- Consumes: existing static Python modules and data at commit `22a4da5`.
- Produces: importable package `paper_static_baseline.dfjspt` and a machine-readable static configuration.

- [ ] Write `test_static_identity.py` first to require the package, configuration identity `paper-static-baseline-v1`, algorithm identity `A0=QNSGA-II`, static scope, and absence of dynamic modules.
- [ ] Run `python -m unittest paper_static_baseline.tests.test_static_identity -v`; expect failure because the directory does not exist.
- [ ] Create the three contract files and mechanically copy only `__init__.py`, `data.py`, `chromosome.py`, `initialization.py`, `decoder.py`, `genetic.py`, `multiobjective.py`, `neighborhoods.py`, `qlearning.py`, `qnsga2.py`, `nsga2.py`, `moead.py`, `mopso.py`, `ablations.py`, `metrics.py` and static data.
- [ ] Run the identity test; expect pass.
- [ ] Commit: `feat: establish paper static baseline identity`.

### Task 2: 建立唯一TEC目标入口

**Files:**
- Create: `paper_static_baseline/dfjspt/objectives.py`
- Modify: `paper_static_baseline/dfjspt/qnsga2.py`
- Modify: `paper_static_baseline/dfjspt/nsga2.py`
- Modify: `paper_static_baseline/dfjspt/moead.py`
- Modify: `paper_static_baseline/dfjspt/mopso.py`
- Create: `paper_static_baseline/tests/test_unified_objectives.py`

**Interfaces:**
- Produces: `evaluate_objectives(schedule: ScheduleResult) -> tuple[float, float]`.
- All four optimizer entry points consume this function.

- [ ] Write tests requiring `evaluate_objectives` to return `(makespan, machine_energy)` and requiring all four `_evaluate` paths to agree for one fixed chromosome.
- [ ] Run the target test; expect import failure for missing `objectives.py`.
- [ ] Implement the two-line objective function and replace only the four objective call sites.
- [ ] Run the target tests; expect pass.
- [ ] Search `paper_static_baseline/` for optimizer expressions adding `agv_energy`; expect zero production matches.
- [ ] Commit: `fix: unify paper static TEC objective`.

### Task 3: 验证静态解码与A0行为

**Files:**
- Create: `paper_static_baseline/tests/test_a0_contract.py`
- Reuse: existing fixed MATLAB/Python reference JSON copied under `paper_static_baseline/data/matlab_reference/`

**Interfaces:**
- Consumes: `decode_static`, `run_qnsga2`, original Q-learning and N1–N6.
- Produces: executable evidence that A0 retains the inherited static method.

- [ ] Write tests for fixed-chromosome schedule feasibility, Makespan/TEC reference values, six actions, original Q update, legal N1–N6 outputs and fixed-seed reproducibility.
- [ ] Include explicit assertions that A0 exposes no K, b or Top-K configuration.
- [ ] Run tests and confirm any failure reflects a missing copied dependency or changed behavior.
- [ ] Make only the smallest import/data-path corrections needed; do not alter scheduling behavior.
- [ ] Run all `paper_static_baseline/tests`; expect pass.
- [ ] Commit: `test: verify static qnsga2 A0 contract`.

### Task 4: 建立单命令运行与不可覆盖记录

**Files:**
- Create: `paper_static_baseline/scripts/run_a0.py`
- Create: `paper_static_baseline/tests/test_run_a0.py`
- Create at runtime: `paper_static_baseline/results/<run-id>/manifest.json`

**Interfaces:**
- `run_a0.py --instance MK01 --population 20 --generations 2 --seed 1 --output <path>`.
- Produces: Pareto objectives, chromosomes, Q-table, evaluation count, seed, config hash and commit identity.

- [ ] Write a subprocess test requiring a successful small run and refusing an existing output directory.
- [ ] Run it; expect failure because the runner is missing.
- [ ] Implement the minimal runner using only standard library and `run_qnsga2`.
- [ ] Run the target test twice; expect deterministic content except explicit creation metadata.
- [ ] Commit: `feat: add reproducible A0 runner`.

### Task 5: 自动验证、哈希与冻结报告

**Files:**
- Create: `paper_static_baseline/scripts/verify_baseline.py`
- Create: `paper_static_baseline/tests/test_verify_baseline.py`
- Generate: `paper_static_baseline/evidence/validation_report.md`
- Generate: `paper_static_baseline/evidence/manifest.sha256`

**Interfaces:**
- `verify_baseline.py` runs the static test suite, one A0 smoke run, forbidden-term scan and SHA-256 generation.
- Exit code is zero only when every required check passes.

- [ ] Write a subprocess test requiring nonzero exit when a required file is absent and zero exit for a complete tree.
- [ ] Run it; expect failure because the verifier is missing.
- [ ] Implement deterministic file enumeration and SHA-256 output; exclude generated run directories and the manifest itself.
- [ ] Generate the report with source commit, Python version, command, test count and limitations.
- [ ] Run `python paper_static_baseline/scripts/verify_baseline.py`; expect exit 0.
- [ ] Commit: `chore: add baseline verification evidence`.

### Task 6: 最终冻结

**Files:**
- Modify: `paper_static_baseline/README.md`
- Modify: A2 evidence/status documents only after checks actually pass.

**Interfaces:**
- Produces: one reviewed commit suitable for tag `paper-static-baseline-v1.0`.

- [ ] Run the complete original 101-test suite after ensuring `results/runs` exists.
- [ ] Run the complete new static verifier.
- [ ] Run `git diff --check` and confirm clean generated evidence.
- [ ] Record the final commit and SHA manifest in README and A2 evidence mapping.
- [ ] Re-run both verification suites after the documentation-only commit.
- [ ] Do not create the tag until all gates pass; then present integration choices required by `finishing-a-development-branch`.

