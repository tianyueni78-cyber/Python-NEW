# A0确定性行为核验

## 结论

固定输入测试共15项，全部通过。测试覆盖A0身份、静态隔离、40/30/30初始化、五个基因块、固定染色体解码、Makespan、机器TEC、Q-learning、N1—N6、多目标选择、统一目标入口和固定种子重复。

## 固定参照

- 实例：Brandimarte Mk05；
- 固定染色体与MATLAB结果：`data/matlab_reference/Mk05_decoder_reference.json`；
- Q-learning与N1—N6参照：`data/matlab_reference/qnsga_step8.json`；
- 小规模完整运行：Mk01、种群10、2代、种子20260817。

## 核验结果

| 对象 | 核验内容 | 结果 |
|---|---|---|
| 初始化 | 4个随机/TCM、3个最短累计时间、3个最低能耗个体 | 通过 |
| 染色体 | OS、MS、AS、空载速度、载货速度均为$O$位，总长$5O$ | 通过 |
| 完整解码 | 机器表、AGV表、电量记录和充电次数与固定MATLAB参照一致 | 通过 |
| 目标 | Makespan为2972.52，机器TEC为11647.883999999998；AGV能耗不进入第二目标 | 通过 |
| Q-learning | 四状态、六动作、三类奖励、epsilon、探索/利用和Q更新与参照一致 | 通过 |
| N1—N6 | 六个邻域均生成合法五段染色体 | 通过 |
| 多目标选择 | Pareto支配、等级、拥挤距离和环境截断行为固定 | 通过 |
| 可重复性 | 同一Mk01配置和种子两次返回完全相同的结果对象，且Q表实际更新 | 通过 |

## 执行命令

```text
python -m unittest discover -s paper_static_baseline/tests -v
```

执行结果：`Ran 15 tests`，`OK`。

## 适用范围

这些结果证明固定输入下的A0行为和小规模固定种子执行可复核；不证明论文规模性能、历史算法排名或新方法有效。
