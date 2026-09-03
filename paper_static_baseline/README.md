# 本文静态baseline

本目录将原QNSGA-II静态方法冻结为本文A0，并为后续新方法、消融和对照算法提供统一的问题、解码器和目标口径。

当前处于建立与验证阶段；在验证脚本、证据清单和Git标签生成前，不得称为已经完成冻结。

正式定义见[BASELINE_SPEC.md](BASELINE_SPEC.md)，机器可读身份见[paper_static_v1.json](config/paper_static_v1.json)。

## 最小复现命令

在仓库根目录运行：

```powershell
python paper_static_baseline/scripts/run_a0.py --instance Mk01 --population 10 --generations 1 --seed 1 --output paper_static_baseline/results/Mk01-seed-1
```

程序拒绝覆盖已有输出目录。运行结果保存在输出目录的`manifest.json`中，其中包含输入和配置哈希、Git提交、随机种子、完整解码次数、Pareto目标、染色体、Q表及收敛轨迹。

正式实验应在固定提交上使用批准的种群、迭代代数和独立运行次数；上面的命令只用于快速验证完整调用链。
