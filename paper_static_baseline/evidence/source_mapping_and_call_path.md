# 来源映射与活动调用路径

## 结论

A0是公开MATLAB静态QNSGA-II活动实现的独立Python冻结副本。论文负责界定研究问题；MATLAB静态算法对比活动路径补足论文未展开的实现细节；Python逐模块实现并用固定参考数据回归。

| 内容 | MATLAB活动实现类别 | Python A0 |
| --- | --- | --- |
| 数据与资源 | 静态算法对比输入及初始化入口 | `dfjspt/data.py` |
| 五段染色体 | 静态QNSGA-II初始化与种群表示 | `dfjspt/chromosome.py`、`initialization.py` |
| 完整解码 | 静态排程解码调用链 | `dfjspt/decoder.py` |
| Makespan与TEC | 静态解码输出与目标评价 | `dfjspt/objectives.py` |
| 遗传操作 | QNSGA-II活动交叉、变异路径 | `dfjspt/genetic.py` |
| 多目标选择 | 非支配排序、拥挤距离、精英选择 | `dfjspt/multiobjective.py` |
| Q-learning | 状态、六动作、奖励、epsilon与更新 | `dfjspt/qlearning.py` |
| N1–N6 | 六个邻域函数 | `dfjspt/neighborhoods.py` |
| 主流程 | 静态QNSGA-II主循环 | `dfjspt/qnsga2.py` |

详细的原始文件级映射保存在`reproduction/02_提取完整算法规格/论文-MATLAB映射.md`；Gate 1—5历史证据分别保存在`reproduction/04_实现统一数据层`至`reproduction/08_实现完整QNSGA-II`。本冻结包没有修改原MATLAB文件和旧`python_baseline`。
