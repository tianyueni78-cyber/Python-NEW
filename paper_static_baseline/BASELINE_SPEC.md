# paper-static-baseline-v1

## 结论

本文基线A0固定为原QNSGA-II的静态方法。它保留OS–MS–AS及速度段、混合初始化、完整解码、遗传与多目标选择、原Q-learning和N1–N6，不包含本文创新。

## 目标

所有算法统一优化：

\[
f_1=C_{max},\qquad f_2=TEC=E_{busy}+E_{idle}.
\]

代码中第二目标对应`machine_energy`。AGV运输、电量和充电仍由完整解码器处理，`agv_energy`仅用于可行性和诊断，不进入第二目标。

## 范围

- 只处理静态机器–AGV协同调度；
- 不处理订单取消、机器故障、AGV故障和动态重调度；
- A0只有原六个邻域动作，不包含Top-K、K、b或三元动作；
- 原MATLAB、`python_baseline/`和历史结果保持不变；
- 正式大规模实验及新方法实现不属于本冻结包。

