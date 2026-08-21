# MATLAB原样baseline规格

## 冻结口径

- 正式实验全部运行Python；MATLAB仅作为只读源码证据。
- 染色体为`5N`：`OS | MS | AS | 逐工序交错的空载速度、负载速度`。
- 不统一不同MATLAB活动目录的目标函数。
- MATLAB注释代码视为不执行。
- 已有统一目标与动态六邻域结果不删除、不覆盖，不冒充原样baseline。

## 静态算法目标

| 算法 | MATLAB活动入口 | f1 | f2 | 成品返回卸载站 |
|---|---|---|---|---|
| QNSGA-II | `initial_NSGA-II/initial_INSGA_II.m` | 最后加工完成时间 | 机器运行能耗＋机器空闲能耗 | 否 |
| NSGA-II | `NSGA-II/NSGA2.m` | 成品返回卸载站完成时间 | 机器能耗＋AGV能耗 | 是 |
| MOEA/D | `MOEAD/MOEAD.m` | 成品返回卸载站完成时间 | 机器能耗＋AGV能耗 | 是 |
| MOPSO | `MOPSO/MOPSO.m` | 成品返回卸载站完成时间 | 机器能耗＋AGV能耗 | 是 |
| 消融A | `NSGA-II/NSGA2.m` | 成品返回卸载站完成时间 | 机器能耗＋AGV能耗 | 是 |
| 消融B | `Multi-NSGA-II/initial_INSGA_II.m` | 最后加工完成时间 | 机器能耗 | 否 |
| 消融C | `QNSGA-II/initial_INSGA_II.m` | 最后加工完成时间 | 机器能耗 | 否 |
| 消融full | `initial_NSGA-II/initial_INSGA_II.m` | 最后加工完成时间 | 机器能耗 | 否 |

机器能耗均指机器运行能耗与机器空闲能耗之和。

## 动态搜索模式

正式原样模式为`matlab_observed`：

- 订单取消：仅执行N1单动作及其Q值更新；
- 机器故障：不执行Q-learning邻域块；
- AGV故障：不执行Q-learning邻域块；
- 三类事件仍执行各自活动代码中的初始化、交叉、变异、解码、非支配排序和环境选择；
- 动态主目标均为Makespan与机器能耗，AGV能耗另作记录或进入RSI分量。

原Python统一六邻域模式保留为`full_qlearning`，不纳入原样baseline的Gate 7。

## 结果解释边界

由于不同静态算法优化的f1/f2并不完全相同，原样结果只能用于复现各MATLAB目录的实际行为，不能直接解释为同一目标下的严格公平算法排名。统一目标结果作为独立扩展证据保留。
