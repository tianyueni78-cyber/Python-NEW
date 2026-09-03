# 数据来源与预处理

## 结论

A0使用Mk01—Mk10 Brandimarte柔性作业车间实例和静态机器–AGV资源参数。数据进入A0后只进行确定性的索引转换和结构化读取，不改变加工时间、可选机器或资源参数。

## 文件

- `data/brandimarte/Mk01.fjs`至`Mk10.fjs`：工件、工序、可选机器和加工时间；
- `data/resources/static_algorithm_comparison.json`：机器、AGV、运输、电量和充电参数；
- `data/matlab_reference/*.json`：由MATLAB固定输入运行形成的回归参考，不参与优化输入。

## 预处理

`.fjs`读取器把MATLAB/数据文件的一基编号转换为Python内部零基编号；输出染色体时由`to_matlab_row()`恢复一基格式。资源JSON直接解析为不可变数据对象。输入内容、冻结配置和全部冻结文件的SHA-256见`manifest.sha256`；每次运行另在`manifest.json`记录具体实例哈希。
