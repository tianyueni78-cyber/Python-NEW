# Experiments

This directory will hold reproducible command-line entry points for:

- parameter analysis;
- algorithm ablation;
- QNSGA-II versus NSGA-II, MOEA/D, and MOPSO;
- order cancellation, machine failure, and AGV failure;
- IS, RS, and CS comparisons;
- repeated runs with recorded seeds and raw outputs.

Experiment scripts must not contain hidden algorithm changes.

## 第12步批处理入口

```powershell
python scripts/run_experiments.py --config experiments/step12_smoke.json --output results/runs/<唯一目录>
```

配置按运行列出实例、算法、重复号、种群规模和代数。同一实例与重复号在不同算法中共享配对种子。输出目录已存在时拒绝覆盖。
