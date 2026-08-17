# 论文—MATLAB规格映射

| 论文概念 | 论文证据 | MATLAB运行证据 | 状态 |
|---|---|---|---|
| DFJSP-T输入 | 第3节、表2 | `benchmarkRead.m`与各`dif_main.m` | 已定位 |
| 三段编码 | §5.1 | 静态主链为五段，动态另有三段 | 冲突，禁止静默裁决 |
| 左移主动解码 | Algorithm 5 | `fitness -> sorting -> table_insert` | 已定位，需第6步逐状态验证 |
| AGV充电 | Eq.9–12、Algorithm 5 | `sorting.m`电量阈值、前往充电和充满逻辑 | 已定位 |
| Makespan | Eq.1 | `fitness.m: max(jobCompleteUnLoad)` | 一致 |
| TEC | Eq.2–4 | 不同`fitness.m`为机器能耗或机器+AGV能耗 | 冲突 |
| 混合初始化 | Algorithm 6，60/20/20 | 静态主`init.m`为40/30/30 | 冲突 |
| 选择/交叉/变异 | §5.3 | `tournament_selection.m`, `variation.m` | 已定位 |
| 非支配排序 | §5.4 | `non_domination.m`, `replace_chrom.m` | 已定位 |
| 4状态 | 表3、§5.5 | `initial_NSGA-II/initial_INSGA_II.m`按双目标中位数分区 | 已定位 |
| 奖励 | Eq.20 | 同一主入口的三分支奖励 | 已定位；零分母需保留原行为 |
| epsilon | Eq.21 | 静态主代码使用另一Sigmoid | 冲突 |
| N1–N6 | §5.5 | `initial_NSGA-II/VNS.m` | 已定位 |
| 完整QNSGA-II | §5.6 | `initial_NSGA-II/initial_INSGA_II.m` | 已确认 |
| 消融A | §6.3 | `NSGA-II/NSGA2.m`+普通初始化 | 已确认 |
| 消融B | §6.3 | `Multi-NSGA-II/initial_INSGA_II.m` | 已确认 |
| 消融C | §6.3 | `QNSGA-II/initial_INSGA_II.m`随机动作、无Q更新 | 已确认 |
| NSGA-II对比 | §6.4 | `NSGA-II/NSGA2.m`时间停止版本 | 已定位 |
| MOEA/D对比 | §6.4、表9 | `MOEAD/MOEAD.m` | 已定位，含特殊评价削减 |
| MOPSO对比 | §6.4、表9 | `MOPSO/MOPSO.m` | 已定位，含VNS |
| 订单撤销RS1 | Algorithm 2、§6.5 | `OD_INSGA-II`, `CRS_OD_INSGA-II`, `initial_OD...` | 多版本，待运行真值确认 |
| 机器故障RS2 | Algorithm 3、§6.5 | `MF_INSGA-II`, `CRS_MF_INSGA-II`, `initial_MF...` | 多版本，待运行真值确认 |
| AGV故障RS3 | Algorithm 4、§6.5 | `AF_INSGA-II`, `CRS_AF_INSGA-II`, `initial_AF...` | 入口有语法错误 |
| RSI | Eq.13–17 | `object3value.m`, `opera_time.m`及动态fitness版本 | 指标命名/组合存在漂移 |
| HV/IGD/C | §6.1 | `HV/`, `IGD/`, `C-metric/`, `Spacing/` | 已定位 |

## 真实主循环

`dif_main -> initial_INSGA_II -> init -> fitness -> sorting -> tournament_selection -> variation -> fitness -> non_domination -> VNS -> fitness -> Q更新 -> non_domination`。

目录名称不能用来判断算法身份：名为`QNSGA-II`的入口是随机邻域消融C；完整Q-learning版本在`initial_NSGA-II`目录。
