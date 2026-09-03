# paper-static-baseline-v1 设计规格

## 目标

在`Python-NEW`中新建独立的`paper_static_baseline/`，冻结本文可执行的静态QNSGA-II基线A0，同时保留现有`python_baseline/`和原MATLAB材料不变。

## 已确认身份与行为

- 原论文提出的主算法是QNSGA-II；普通NSGA-II、MOEA/D和MOPSO是对照算法。
- 既有论文成果不在本任务中重新评价；不同历史代码目录只作为来源材料。
- A0继承原QNSGA-II的静态方法：OS–MS–AS及空载/载货速度段、完整解码、NSGA-II遗传与环境选择、原Q-learning结构及N1–N6基本语义。
- A0以公开MATLAB代码的Python复现行为为准，不以重新复现原论文历史排名作为冻结条件。
- 染色体固定为五段；混合初始化固定为代码实际40%随机/TCM、30%最短时间、30%低能耗。
- epsilon固定为当前Python复现的MATLAB活动公式及其利用/探索分支；Makespan固定为最后加工完成时间。
- TEC固定为`E_busy+E_idle=machine_energy`。AGV能耗、电量和充电仍由解码器计算，但AGV能耗不进入第二目标。
- A0不包含Top-K、K、b、三元动作、新状态、新奖励或其他创新机制。
- 论文与发布代码的差异只作中性来源记录，不作为A0行为选择题，也不表述为原论文错误。

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

A0统一从此入口读取目标。后续新方法必须复用同一入口；三种对照算法和消融属于后续实验准备，不是A0冻结的前置条件。

## 验证门

1. 身份门：目录、规格和配置明确静态A0及排除项。
2. 静态边界门：包内不存在动态模块或Top-K、K/b联合动作。
3. 确定性门：固定输入、五段染色体、40/30/30初始化、最后加工完成Makespan和机器TEC通过测试。
4. 算法门：当前epsilon、原Q-learning结构、N1–N6、多目标算子和固定种子通过测试。
5. 运行门：一条命令完成A0小规模端到端运行，保存真实完整解码数、种子、配置、提交和结果。
6. 比较防火墙门：A0与后续新方法除局部搜索资源分配与学习控制外共享全部不变量。
7. 冻结门：验收清单全部必需项有证据并通过，生成中文报告和SHA-256清单，最终提交复验且工作树干净后创建`paper-static-baseline-v1.0`标签。

单元测试通过只证明相应代码门通过，不代表原论文历史结论已经复现，也不代表新方法有效。

## 节省成本原则

- 机械复制已验证静态模块，不重新手写算法。
- A0不新增算法行为；只允许静态隔离、统一记录入口和验证所需的最小改动。
- 复用现有固定参照数据和测试逻辑，只新增静态身份与统一目标所需测试。
- 本阶段只运行小规模端到端验证；正式多次实验留给A5/A6。
