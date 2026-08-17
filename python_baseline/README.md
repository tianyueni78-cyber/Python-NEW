# Python baseline

这里保存忠实的 Python 复现。当前已完成第6步静态解码与目标函数。

```powershell
python scripts/run_decoder.py --instance Mk05 --seed 20260817 --output results/Mk05_decoder_step6.json
python scripts/check_gate3.py
```

读取一个完整实验输入：

```powershell
python -m python_baseline.dfjspt python_baseline/data/brandimarte/Mk05.fjs python_baseline/data/resources/static_algorithm_comparison.json
```

重新执行 Gate 1：

```powershell
python scripts/check_gate1.py
python -m unittest discover -s tests -v
```

只有重新转换原“机器数据.xlsx”时才需要 `requirements-convert.txt` 中的 `openpyxl`；正常读取已转换数据不依赖第三方包。

生成第5步初始种群：

```powershell
python scripts/run_initialization.py --instance Mk05 --mode hybrid --population 100 --speed-count 4 --seed 20260817 --output results/Mk05_initial_population.json
```
