# paper-static-baseline-v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有Python QNSGA-II实现静态化并冻结为稳定、可重复、无创新混入的A0，供后续局部搜索创新进行公平对照。

**Architecture:** 以`python_baseline`已经验证的实际代码行为为来源，在独立`paper_static_baseline/`中机械保留静态核心，删除动态入口，不重写算法。A0验收只验证身份、正确性、可运行性、可重复性和创新隔离；原论文历史排名、新方法效果和论文规模实验不进入冻结门。

**Tech Stack:** Python 3标准库、`unittest`、Git、SHA-256、Markdown。

**Spec:** `docs/superpowers/specs/2026-09-03-paper-static-baseline-v1-design.md`

**Acceptance Checklist:** `paper_static_baseline/BASELINE_ACCEPTANCE_CHECKLIST.md`

## Global Constraints

- 原MATLAB、`python_baseline/`、输入数据和历史结果只读。
- A0只含静态QNSGA-II，不含动态事件与重调度。
- A0不含Top-K、K、b、`(K,N,b)`或本文其他创新。
- A0按实际代码固定：五段染色体、40/30/30初始化、当前epsilon、最后加工完成Makespan、机器加工与空闲TEC。
- 只进行固定输入测试和小规模端到端验证，不运行论文规模正式实验。
- 不新增依赖；优先复用已有数据、代码、测试和验证材料。
- 所有完成声明必须有最新运行输出；“能运行”不替代正确性和可重复性。

---

### Task 1：校准A0合同与现有A2管理边界

**Files:**
- Modify: `docs/superpowers/specs/2026-09-03-paper-static-baseline-v1-design.md`
- Modify: `paper_static_baseline/BASELINE_SPEC.md`
- Modify: `paper_static_baseline/config/paper_static_v1.json`
- Create: `paper_static_baseline/evidence/baseline_identity.md`
- Read: `paper-explaination/研究管理/A2成果/当前阶段说明.md`

**Interfaces:**
- Consumes: 来源提交`22a4da57162c202c138d2add461e04aa81e4a72d`及公开MATLAB静态QNSGA-II路径。
- Produces: 唯一A0合同和A2管理调整建议。

- [ ] 将A0身份固定为“基于公开代码实现的Python静态QNSGA-II基线”，不称为论文逐项重建版。
- [ ] 在规格和JSON中写死五段编码、40/30/30初始化、当前epsilon、最后加工完成Makespan和机器TEC。
- [ ] 写明论文与代码差异只作中性来源记录，不是A0行为选择题，也不是A0验收失败。
- [ ] 将“复现原论文排名、三个比较算法、消融结果”列为后续实验任务，不作为A0冻结门。
- [ ] 对照现有A2的38项矩阵，形成管理调整建议；未正式更新唯一矩阵前，不虚构A2已经关闭。
- [ ] 运行JSON解析和规格关键词检查。
- [ ] Commit: `docs: fix static QNSGA-II A0 contract`。

### Task 2：核查静态代码隔离和机械继承

**Files:**
- Modify only if required: `paper_static_baseline/dfjspt/`
- Modify: `paper_static_baseline/tests/test_static_identity.py`
- Create: `paper_static_baseline/evidence/source_and_isolation.md`

**Interfaces:**
- Consumes: `python_baseline/dfjspt`静态模块。
- Produces: 不含动态和创新入口的可导入A0包。

- [ ] 列出A0实际调用链：数据→初始化→解码→目标→遗传→环境选择→Q-learning→N1–N6。
- [ ] 比较A0与来源模块；除导入路径、静态包路径和记录接口外，不接受未说明的行为差异。
- [ ] 扫描并阻止`dynamic.py`、动态配置、事件类型、Top-K、K/b联合动作进入A0。
- [ ] 检查原MATLAB、`python_baseline/`和历史结果没有被本分支修改。
- [ ] 运行`python -m unittest paper_static_baseline.tests.test_static_identity -v`。
- [ ] Commit: `test: verify A0 source isolation`。

### Task 3：固定A0算法行为并建立回归测试

**Files:**
- Create: `paper_static_baseline/tests/test_a0_contract.py`
- Modify: `paper_static_baseline/tests/test_unified_objectives.py`
- Create: `paper_static_baseline/evidence/deterministic_validation.md`

**Interfaces:**
- Consumes: A0的`hybrid_population`、`decode_static`、Q-learning、N1–N6、遗传和多目标选择。
- Produces: 固定输入下可复核的A0行为证据。

- [ ] 先写测试锁定40/30/30初始化及五段染色体合法性。
- [ ] 写固定染色体测试，核查工序优先、机器资格、资源不重叠、AGV移动/位置/电量/充电。
- [ ] 锁定最后加工完成Makespan和`TEC=machine_energy`回归值。
- [ ] 锁定当前epsilon代表值、利用/探索分支、四状态、六动作、奖励、Q更新和Q表生命周期。
- [ ] 分别验证N1–N6输出合法且没有改变基本修改语义。
- [ ] 验证遗传操作、非支配排序、拥挤距离和环境选择的继承行为。
- [ ] 运行全部`paper_static_baseline/tests`并把命令、测试数、结果和限制写入证据文档。
- [ ] Commit: `test: freeze static QNSGA-II behavior`。

### Task 4：建立一键运行、真实解码计数和运行清单

**Files:**
- Create: `paper_static_baseline/scripts/run_a0.py`
- Create: `paper_static_baseline/tests/test_run_a0.py`
- Modify: `paper_static_baseline/README.md`
- Runtime: `paper_static_baseline/results/<run-id>/manifest.json`

**Interfaces:**
- Command: `python paper_static_baseline/scripts/run_a0.py --instance Mk01 --population 20 --generations 2 --seed 1 --output <path>`
- Produces: Pareto目标、染色体、Q表、真实完整解码数、配置、种子和提交信息。

- [ ] 先写子进程测试，要求最小运行成功并拒绝覆盖已有输出目录。
- [ ] 在唯一解码入口增加或复用评价计数，覆盖初始化、遗传评价和邻域内部真实解码。
- [ ] 实现最小运行器，不增加新的实验框架或配置抽象。
- [ ] manifest记录实例、参数、种子、配置哈希、源码提交、Python版本、开始/结束状态和失败信息。
- [ ] 相同参数和种子运行两次，比较除时间戳等明确元数据外的结果一致性。
- [ ] README提供完整命令、输入、输出和结果读取说明。
- [ ] Commit: `feat: add reproducible static A0 runner`。

### Task 5：建立A0与新方法的公平比较防火墙

**Files:**
- Create: `paper_static_baseline/evidence/A0_与新方法差异表.md`
- Create: `paper_static_baseline/tests/test_innovation_firewall.py`

**Interfaces:**
- Consumes: 冻结A0合同。
- Produces: 后续创新必须遵守的共享项和唯一修改点。

- [ ] 差异表将数据、编码、初始化、解码、Makespan、TEC、遗传、环境选择、种子政策和真实解码预算标为共享不变量。
- [ ] 唯一创新位置写为“根据完整排程反馈确定Top-K区域，由Q-learning联合选择`(K,N,b)`”。
- [ ] 测试确认关闭创新配置时恢复A0入口和A0行为。
- [ ] 写明后续比较必须使用同一机器、同一实例、同一目标及预先固定的真实解码预算。
- [ ] 写明A0冻结不证明新方法有效；性能主张只能由后续正式实验支持。
- [ ] Commit: `docs: define A0 innovation firewall`。

### Task 6：自动验证和中文验收报告

**Files:**
- Create: `paper_static_baseline/scripts/verify_baseline.py`
- Create: `paper_static_baseline/tests/test_verify_baseline.py`
- Generate: `paper_static_baseline/evidence/validation_report.md`
- Generate: `paper_static_baseline/evidence/manifest.sha256`
- Modify: `paper_static_baseline/BASELINE_ACCEPTANCE_CHECKLIST.md`

**Interfaces:**
- Command: `python paper_static_baseline/scripts/verify_baseline.py`
- Produces: 非零失败码、中文逐项判定和可复核哈希。

- [ ] 先写验证器失败测试：缺文件、测试失败、出现动态/创新入口、运行失败或哈希不完整时返回非零。
- [ ] 验证器依次执行身份扫描、A0测试、小规模运行、可重复性比较和SHA-256生成。
- [ ] 重跑原`python_baseline`完整测试，证明A0建立过程没有破坏来源实现。
- [ ] 按验收清单逐项填写“通过／不通过／证据不足”，并链接实际文件和运行输出。
- [ ] 报告明确区分：A0技术验收、原论文历史结论复现、新方法效果验证。
- [ ] 运行`git diff --check`和清单自校验。
- [ ] Commit: `chore: add A0 verification evidence`。

### Task 7：最终复验、冻结和交付

**Files:**
- Modify: `paper_static_baseline/README.md`
- Modify after contract calibration: A2/P03/P04/P10对应管理文档

**Interfaces:**
- Produces: 可创建`paper-static-baseline-v1.0`标签的最终提交。

- [ ] 在最终提交候选上运行原测试、A0验证器和`git diff --check`。
- [ ] 核对冻结文件哈希、提交号、数据版本、运行命令和已知限制。
- [ ] 只有清单全部必需项通过时，才把A0判为可验收；结果好坏不是判定条件。
- [ ] 更新管理文档时只勾选有证据支持的条目；比较算法、消融和原论文排名不冒充A0证据。
- [ ] 文档提交后再次完整复验。
- [ ] 工作树干净后创建`paper-static-baseline-v1.0`标签。
- [ ] 使用`superpowers:verification-before-completion`审核完成声明。
- [ ] 使用`superpowers:finishing-a-development-branch`处理合并、推送分支和标签。

## 完成标准

A0满足以下条件即可冻结：

1. 身份和实际行为明确；
2. 静态范围正确且没有创新混入；
3. 固定输入正确性和固定种子可重复性通过；
4. 一键运行、真实解码计数、manifest、README和限制完整；
5. 来源实现未被破坏；
6. A0与新方法的共享项和唯一差异明确；
7. 中文验收报告、SHA-256、最终提交和标签完整。

不要求A0重新产生原论文历史排名，也不要求A0本身优于其他算法。后续论文只主张新方法在统一协议下相对这个冻结A0的增益。
