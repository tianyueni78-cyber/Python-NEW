# paper-static-baseline-v1 设计规格

## 目标

在`Python-NEW`中新建独立的`paper_static_baseline/`，冻结本文可执行的静态QNSGA-II基线A0，同时保留现有`python_baseline/`和原MATLAB材料不变。

## 已确认身份

- 原论文提出的主算法是QNSGA-II；普通NSGA-II、MOEA/D和MOPSO是对照算法。
- 既有论文成果不在本任务中重新评价；不同历史代码目录只作为来源材料。
- A0继承原QNSGA-II的静态方法：OS–MS–AS及速度段、混合初始化、完整解码、NSGA-II遗传与环境选择、原Q-learning及N1–N6。
- 本文统一目标为`(makespan, TEC)`，其中`TEC=E_busy+E_idle=machine_energy`。AGV能耗、电量和充电仍由解码器计算，但AGV能耗不进入第二目标。
- A0不包含Top-K、K、b、三元动作、新状态、新奖励或其他创新机制。

## 目录边界

```text
paper_static_baseline/
├─ README.md
├─ BASELINE_SPEC.md
├─ config/paper_static_v1.json
├─ data/
├─ dfjspt/
├─ scripts/run_a0.py
├─ scripts/verify_baseline.py
├─ tests/
└─ evidence/
```

静态数据和实现从当前权威Python代码机械复制后再做最小修改；不复制`dynamic.py`、`dynamic_experiments.py`或动态实验配置。`python_baseline/`、`original_matlab/`及历史结果只读。

## 统一接口

`paper_static_baseline/dfjspt/objectives.py`提供唯一目标入口：

```python
def evaluate_objectives(schedule: ScheduleResult) -> tuple[float, float]:
    return schedule.makespan, schedule.machine_energy
```

QNSGA-II、三种对照算法、消融及实验记录不得自行拼接第二目标。优化器入口保持分离，共享已经验证为一致的数据、染色体、解码、目标和多目标工具。

## 验证门

1. 身份门：目录、规格和配置明确静态A0及排除项。
2. 静态边界门：包内不存在动态模块或Top-K、K/b联合动作。
3. 确定性门：固定输入、染色体、排程、Makespan和TEC通过测试。
4. 算法门：原Q-learning、N1–N6、多目标算子和固定种子通过测试。
5. 统一目标门：A0、NSGA-II、MOEA/D和MOPSO对同一染色体返回相同目标。
6. 运行门：一条命令完成A0小规模端到端运行并保存种子、配置和结果。
7. 冻结门：生成验证报告和SHA-256清单，工作树干净后创建`paper-static-baseline-v1.0`标签。

单元测试通过只证明代码门通过，不代表论文规模统计复现或新方法有效。

## 节省成本原则

- 机械复制已验证静态模块，不重新手写算法。
- 新行为仅集中在统一目标入口及其调用点。
- 复用现有固定参照数据和测试逻辑，只新增静态身份与统一目标所需测试。
- 本阶段只运行小规模端到端验证；正式多次实验留给A5/A6。

