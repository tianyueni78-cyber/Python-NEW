# 一致性测试

`test_gate1_input.py` 比较 Python 解析结果与原 MATLAB `benchmarkRead.m` 生成的十个参照文件，并检查非法输入与统一资源参数。

MATLAB 参照不是人工抄写；可在安装 MATLAB 的机器上重新生成：

```matlab
addpath('tests/matlab_reference')
export_brandimarte_reference('<原静态算法对比目录>', ...
    '<仓库>/python_baseline/data/matlab_reference')
```
