# 风格：极简学术汇报风格

---

## Slide 1 — 封面

**主标题**：基于代理辅助演化算法的建筑电磁窗口多目标优化设计研究

**副标题**：从跨算法互证到 BO-LGBM 代理模型混合搜索框架

汇报人：成雨鸣

工作流示意：[物理降噪] → [算法互证] → [代理模型] → [两阶段 Pipeline]

---

## Slide 2 — 课题背景与确定性降噪

### 左栏

高频毫米波室外-室内穿透 Low-E 幕墙引入 20–30 dB 路径损耗，物理建模包含*8天线阵列均匀菲涅尔衍射信道(LoS + NLoS)、人群行为模型、四方向用户自阻塞模型* 等。控制向量为 4D 连续空间：

$$\boldsymbol{\theta} = [x_c,\; z_c,\; L_x,\; L_z]^T$$

$$\min_{\boldsymbol{\theta}}\; f_1 = \text{Area},\quad \min_{\boldsymbol{\theta}}\; f_2 = \text{Outage}$$

### 右栏上

对于人群行为模型，MATLAB 基准以 300s 短时 RWP 轨迹评估，引入 σ≈4.5% 随机噪声，易诱导遗传算法早停于伪收敛点。重构方案：200×200×5 确定性空间网格积分（KDE 静态积分）。

配图：`fig_exp1_convergence.png`

### 右栏下

仿真延长至 20,000s 后，网格积分与 Markov 长时极限偏差仅 0.67%。100 组随机窗口配置：MAE=1.22%, R²=0.9941——数学上确证静态网格等价于 Markov 稳态分布。

配图：`fig_exp2_discrepancy.png`

---

## Slide 3 — 三算法交叉互证

### 左栏

引入机制截然不同的三种启发性算法——NSGA-II（Pareto 支配度）、AGE-MOEA（自适应几何估计）、MOEA/D（切比雪夫标量化分解）——以减少单一算法局部最优的可能。

互证结论：三条独立搜索路径收敛至同一拓扑流形，最优解集最大空间偏差 <3%。在 ≤10% 中断率约束下，关键 Knee 解开窗面积仅 **1.646 m²**。

### 右图

`algo_comparison.png` —— 三算法前沿高度重合。

### 左下

`viz_wall_canvas.png` —— 幕墙立面精英解几何分布。

### 右下

`viz_parallel_coords.png` —— 4D 决策空间至目标空间的平行坐标映射。

### 底部【黑色小字文献引用】

- _Panichella, A. (2019). An adaptive evolutionary algorithm based on non-euclidean geometry for many-objective optimization. In Proceedings of the 2019 GECCO (pp. 595–603)._

---

## Slide 4 — 拓扑跳变

### 左栏

Knee 解规律：xc≈5.26, zc≈1.29 精确收敛于衍射物理与 KDE 人群密度叠加的最优质心。

两种拓扑突变机制：

**Knee Jump（~9.7%）** —— 正交轴向“转置”。Lz 从 0.54m 收缩至 0.20m (−63%)，触及衍射下限；Lx 从 7.32m 扩张至 9.31m (+27%)，以水平展宽补偿垂直压缩的能量损失。

**Jump B（~13.0%）** —— 单轴压缩。Lz 锁定不变，Lx 从 2.22m 骤降至 0.15m (−93%)，窗口从面透射体退化为狭缝波导机构。

### 右图

`jump_wall_canvas.png` —— 窗口形状跨越跳变点的立面演进。

---

## Slide 5 — BO-LGBM 代理模型

### 左栏

- 混合数据集：5,000 LHS + 300 NSGA-II 真实 Pareto 前沿 + 2,000 边界过采样 = 7,300 样本
- 模型：LightGBM（树分裂天然适配 sinc 衍射的非连续响应面）
- 超参调优：Optuna 50 轮, 5-Fold CV, feasible-MAE 为优化目标
- 交叉切片验证：以 Knee 点为锚, 4 维各扫 60 步, 模型与物理引擎曲线紧密贴合

### 右上图

`validation_sweeps.png`

### 右下表

| 指标           | 值          | 阈值     |
| ------------ | ---------- | ------ |
| Feasible MAE | 0.52%      | —      |
| HV Deviation | **1.19%**  | <5%    |
| IGD          | **0.0120** | <0.05  |

---

## Slide 6 — 两阶段 Warm-Start

### 左栏

代理悖论：全局 MAE 仅 0.5%，但树模型在可行域边界存在过光滑导致的局部系统性偏差。演化算法在两阶段接力中系统性利用该偏差——纯代理 Knee 面积 1.755 m²，偏离物理真值 1.646 m² 达 6.7%。

### 右栏

**Phase 1 —— 代理粗筛**：NSGA-II 在 LGBM 上完整演化 200 代（12s）。剪除 90% 不可行空间，输出 300 个近似 Pareto 候选。

↓

**Phase 2 —— 物理精炼**：取 250 代理精英 + 50 随机个体混合注入（防止种群退化）。物理 AGE-MOEA/NSGA-II 仅跑 20 代在线精炼，以真实物理流形校正局部偏误泡沫，种群滑回可行域边界。

### 底部【黑色小字文献引用】

- _Shen, Y., & Pan, Y. (2023). BIM-supported automatic energy performance analysis for green building design using explainable machine learning and multi-objective optimization. Applied Energy, 333, 120575._
    
- _Panichella, A. (2022). An improved Pareto front modeling algorithm for large-scale many-objective optimization. In Proceedings of the 2022 GECCO (pp. 565–573)._

---

## Slide 7 — 消融分析

### 上半幅：基因多样性消融

纯物理迭代（深蓝线）缓慢下降收敛；Warm-Start 管线（黄、绿线）从第 0 代起 σ 即收缩至极小值——AI 先验知识在演化启动前已剪除冗余搜索空间。

配图：`angle1_diversity.png`

### 下半幅：约束违规率拦截

纯物理 NSGA-II 早期违规率高达 60–70%，大量交叉子代越界造成无效算力损耗。Warm-Start 自第 0 代起违规率趋近于 0——LGBM 离线已将硬性边界约束固化为不可违反的判定规则。

配图：`angle3_violations.png`

---

## Slide 8 — 四条路线 Pareto 对比

### 左栏

| Arm | 时间 | Knee |
|---|---|---|
| Pure Physics | 217s | 1.646 m² |
| Pure Surrogate | 12s | 1.755 m² |
| Dual NSGA-II | 45s | 1.692 m² |
| **Dual AGE-MOEA** | **84s** | **1.658 m²** |

Dual AGE-MOEA 面积仅偏离 ground truth 0.7%，物理评估次数削减 90%。纯代理（12s）和 Dual NSGA-II（45s）在算力受限场景中构成高性价比备选。

### 右图

`angle4_pareto.png` —— 深蓝（物理真值）、红（纯代理）、绿（Dual NSGA2）、橙（Dual AGE）四线同台。

---

## Slide 9 — 全链路闭环复盘

### 流程图

① **物理网格化降噪**（→Slide 2）：消除轨迹随机抖动，R²=0.9941

② **三算法机制互证**（→Slide 3）：独立搜索路径收敛至同一前沿，max Δ<3%

③ **拓扑特征解耦**（→Slide 4）：Knee Jump（正交转置）+ Jump B（单轴压缩）

④ **代理平替与流形验证**（→Slide 5）：R²=0.995, IGD=0.0120

⑤ **两阶段混合管线落地**（→Slide 6-8）：12s 离线剪枝 + 20 代在线精炼，90% 算力节省, 0.7% 精度逼近

---

## Slide 10 — 负结果与收敛上界

### 左栏：四条失败路线

| 方法 | 失败原因 |
|---|---|
| RBF 局部精炼 | 30/300/500 点三版迭代无一改进 |
| 置信域序列优化 | 3 轮 FAILURE, 半径砍至 1.25% |
| Ridge+LGBM Stacking | 全局 MAE 优化但 Knee 劣化 1.66→1.73 |
| GP+LGBM Stacking | O(n³) 算力限制, feasible MAE 退化至 1.04% |

### 右栏：收官结论

四项进阶技术路线均未突破当前 Pipeline 的最优解——这并非方法缺陷，而是物理空间本身的约束极限。负结果从反面构成了逻辑闭环：**BO-LGBM 两阶段 Warm-Start 混合管线已探明该电磁约束下的全局收敛上界。**
