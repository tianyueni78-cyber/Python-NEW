# A0来源与隔离

## 实际调用链

```text
Brandimarte .fjs与静态资源JSON
  → data.load_experiment_input
  → initialization.hybrid_population
  → decoder.decode_static
  → objectives.evaluate_objectives
  → genetic.variation
  → multiobjective排序与选择
  → qlearning状态、动作、奖励与Q更新
  → neighborhoods.apply_neighborhood（N1—N6）
  → qnsga2.run_qnsga2
  → Pareto染色体、目标、Q表、收敛记录和评价次数
```

## 机械继承

`chromosome.py`、`decoder.py`、`genetic.py`、`initialization.py`、`multiobjective.py`、`neighborhoods.py`和`qlearning.py`从来源`python_baseline`机械继承。A0删除`data.py`和`metrics.py`中未被静态主链调用的动态辅助函数；`__init__.py`不导出动态对象；`qnsga2.py`只把目标读取集中到`evaluate_objectives`，未改变排程、遗传、Q-learning或邻域逻辑。

`nsga2.py`、`moead.py`、`mopso.py`和`ablations.py`不属于A0运行入口，也不作为本次冻结证据；它们的正式对照与消融测试归入后续P06。

## 静态边界

A0包不存在`dynamic.py`、`dynamic_experiments.py`和动态资源配置。生产代码不提供订单取消、机器故障、AGV故障、重调度、Top-K或联合`(K,N,b)`动作入口。

## 只读来源

本分支相对来源提交`22a4da57162c202c138d2add461e04aa81e4a72d`未修改`python_baseline/`、原MATLAB目录和历史结果。全部A0改动位于`paper_static_baseline/`及其规格和计划文件中。

## 核查命令

```text
python -m unittest paper_static_baseline.tests.test_static_identity -v
git diff --name-status 22a4da5 -- python_baseline original_matlab results
```

身份测试共5项，全部通过；来源目录差异命令没有输出。
