# 运行环境与依赖

## 结论

A0只使用Python标准库，不需要新增第三方Python包。当前验收环境为Windows、CPython 3.13.5；测试与运行均从仓库根目录执行。

## 环境

- 操作系统：Windows；
- Python：3.13.5；
- 测试框架：标准库`unittest`；
- 随机数：标准库`random.Random`，每次运行显式传入种子；
- 文件格式：UTF-8 JSON、Markdown和Brandimarte `.fjs`文本。

A0没有NumPy、pandas、SciPy或外部优化库依赖，避免由库默认算法替代MATLAB专用行为。
