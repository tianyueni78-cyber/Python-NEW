# 第2步差异裁决状态

本阶段只完成规格提取，不擅自改变行为。下列项目全部标记为“需要双配置或运行证据后由用户确认”。

1. 三段编码与五段速度编码：baseline-invalidating，建议保留`paper_3segment`和`matlab_static_5segment`候选规格。
2. TEC定义：baseline-invalidating，必须通过论文原始结果或固定染色体输出判断实际实验使用版本。
3. 初始化60/20/20与40/30/30：configuration difference，不能合并。
4. epsilon两种Sigmoid：implementation difference，直接影响动作学习。
5. 迭代停止与等CPU时间停止：comparison-protocol difference。
6. MOPSO附加VNS：comparison implementation difference；Python不能用库默认MOPSO替代。
7. MOEA/D评价削减：comparison budget difference；必须忠实保留或形成单独修正版。
8. 动态目录版本漂移与AGV入口语法错误：baseline-invalidating，进入实现前必须先建立可运行MATLAB参考副本。
9. 随机种子缺失：statistical reproducibility difference；组件测试使用固定随机输入，完整实验保存Python种子。
10. 所有疑似缺陷遵循“双轨”：`matlab_compat`保存观察行为，任何`paper_corrected`版本单独存在且需批准。

第2步没有替用户选择上述行为，因此不会造成baseline被静默改写。
