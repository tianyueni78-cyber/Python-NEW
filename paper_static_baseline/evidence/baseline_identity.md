# A0身份与行为

## 身份

A0是基于公开MATLAB活动代码实现的Python静态QNSGA-II基线。它用于回答后续新方法相对于“不改变局部搜索控制方式的静态QNSGA-II”是否产生增益。

## MATLAB活动路径

```text
第2篇代码 - 静态算法对比/dif_main.m
  → initial_NSGA-II/initial_INSGA_II.m
  → init.m
  → fitness.m
  → sorting.m
  → variation.m / non_domination.m / improved_elitism.m
  → getState.m / VNS.m（N1—N6）
```

目录名不作为算法身份依据；`dif_main.m`中的实际调用决定本基线采用的Q-learning版本。

## 固定行为

| 项目 | A0行为 |
|---|---|
| 范围 | 静态机器—AGV联合调度 |
| 染色体 | OS、MS、AS、空载速度、载货速度，共$5O$位 |
| 初始化 | 40%随机/TCM、30%最短时间、30%最低能耗 |
| 解码 | 机器与AGV协同排程，包含空载、载货、位置、电量和充电 |
| Makespan | 最后一道加工完成时间 |
| TEC | 机器加工能耗加机器空闲能耗 |
| 学习控制 | 四状态、六个N1—N6动作、活动epsilon公式、运行内Q更新 |
| Q表生命周期 | 每次独立运行重新初始化 |

## 不属于A0的内容

订单取消、机器故障、AGV故障、动态重调度、Top-K、K、b、`(K,N,b)`联合动作、新状态和新奖励均不属于A0。

普通NSGA-II、MOEA/D、MOPSO、消融和论文规模统计比较属于后续实验阶段，不作为A0冻结条件。A0冻结只证明身份、实现正确性、可运行性、可重复性和创新隔离。

## 来源记录

- Python来源提交：`22a4da57162c202c138d2add461e04aa81e4a72d`。
- MATLAB来源：`第2篇代码 - 静态算法对比/`。
- 原论文：R. Chen等，*A Q-Learning based NSGA-II for dynamic flexible job shop scheduling with limited transportation resources*，2024。
- 论文与代码在初始化比例和编码结构上的差异只登记，不改变A0按活动代码执行的口径。
