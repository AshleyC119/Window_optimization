# EM Window Optimization — Comprehensive Report

> KDE 经验权重 + 多高度网格 + 自阻塞模型 + NSGA-II Pareto 前沿 + 双阶段代理优化。

---

## 1. 算法互证：NSGA-II vs AGE-MOEA vs MOEA/D

**维度**：同一物理引擎，不同算法。

### 动机

NSGA-II 产出 Pareto 前沿后，引入两个机制完全不同的多目标算法在同一物理引擎上运行对比，排除"NSGA-II 特有局部最优"的质疑。

### 实验设计

| 算法 | 核心机制 | 种群/代数 |
|---|---|---|
| NSGA-II | Pareto dominance + crowding distance | 300 × 200 |
| AGE-MOEA | 自适应几何估计 | 300 × 200 |
| MOEA/D | 标量化分解 (299 子问题, Tchebycheff) | 按子问题数 |

### 结果

```
NSGA-II:  1.6456 m² @ 9.97%  (300 pts)
AGE-MOEA: 1.6973 m² @ 9.96%  (300 pts)
MOEA/D:   1.6557 m² @ 9.92%  (167 pts)
max Δarea = 0.05 m² (3%), max Δoutage = 0.05pp
```

三算法收敛到同一前沿——Pareto dominance、几何流形估计、标量化分解三个底层搜索机制排除局部最优。附带平行坐标图、幕墙立面图、3D 决策空间图。

---

## 2. BO-LGBM 代理模型

### 动机

构建物理引擎的 μs 级替代（Optuna 调参 LightGBM）。

### 训练数据

| 来源 | 数量 | 说明 |
|---|---|---|
| LHS 全域 | 5,000 | 拉丁超立方, 4D 均匀覆盖 |
| NSGA-II 真实前沿 | 300 | 物理引擎精算, Pareto 边界全覆盖 |
| 边界过采样 | 2,000 | xc≈5, zc≈1.3, Lx∈[0.05,3], Lz∈[0.1,0.6] |
| **合计** | **7,300** | feasible (<10%) 比例提升 |

### 训练

- 模型: LightGBM（树模型天然处理 sinc 衍射的非连续响应面）
- 超参搜索: Optuna 50 轮, 5-Fold CV, 目标 feasible-region MAE
- 结果: `Feasible MAE = 0.52%, R² all = 0.995, R² feasible = 0.908`

---

## 3. 代理悖论与 Warm-Start 解法

### 问题：MAE 0.5% 为何优化 Gap 达 6-7%？

纯代理 NSGA-II（200 代 LGBM）产出的候选经物理验证后，Knee 从代理预测的较小面积偏移到物理真值——代理模型在可行域边界有局部系统性偏差，演化算法放大为约 6-7% 的 gap。

### 解法：两阶段 Warm-Start

**Phase 1** — NSGA-II 在 LGBM 上跑 200 代（μs 推理, ~12s），产出 300 个粗筛候选。  
**Phase 2** — 250 精英 + 50 随机混合注入物理 NSGA-II/AGE-MOEA，仅跑 20 代精炼。

```
评估次数           墙钟
纯物理 NSGA-II      60,000     217s
纯代理 LGBM              0      12s
双阶段 NSGA-II       6,000      45s
双阶段 AGE-MOEA      6,000      84s
```

---

## 4. Pareto 前沿特征

### Knee 解

```
xc=5.26, zc=1.29, Lx=9.01, Lz=0.18
Area=1.646 m², Outage=9.97%
```

### 双跳变特征

**Knee Jump @ 9.7%**：Lz 0.54→0.20 (−63%), Lx 7.32→9.31 (+27%)——十字転置，垂直维度突破衍射极限，水平补偿拉伸。

**Jump B @ 13.0%**：Lx 2.22→0.15 (−93%), Lz 几乎不变——同向极限压缩。两跳在 Gaussian 和 KDE 两套权重均被证实。

---

## 5. 代理全维度对比（四臂 + 四角度）

### 实验设计

| Arm | 算法 | 评估器 | 墙钟 | Knee |
|---|---|---|---|---|
| Pure Physics | NSGA-II 200g | 物理引擎 | 217s | **1.6456 m²** |
| Pure Surrogate | NSGA-II 200g | LGBM | 12s | 1.7554 m² |
| Dual-Stage NSGA2 | LGBM 200g + Physics NSGA2 20g | 混合 | 45s | 1.6915 m² |
| **Dual-Stage AGE** | LGBM 200g + **Physics AGE-MOEA 20g** | 混合 | 84s | **1.6578 m²** |

### Angle 1 — 基因多样性坍塌

四变量标准差随代数演化：纯物理 NSGA-II 缓慢下降至 80 代方收敛；代理 warm-start 从第 0 代即坍塌到极小值——代理模型已预先剪枝。

### Angle 2 — 虚假最优泡沫退潮

物理精炼阶段每隔 5 代截取种群散点。代理初始解大面积越界（假可行），随着物理引擎接管在第 5→15 代优雅滑回 10% 红线左侧。

### Angle 3 — 约束违规率

纯物理 NSGA-II 早期违规率高达 60-70%（大部分交叉子代越界）；代理 warm-start 从第 0 代违规率接近 0%——LGBM 离线已将边界硬约束固化。

### Angle 4 — Pareto 前沿对比

四条 Pareto 曲线同台：灰(物理真值)、红(纯代理, 向右偏移)、绿(Dual NSGA2)、橙(Dual AGE-MOEA, 最贴近灰线)。

### 结论

AGE-MOEA warm-start (1.658 m²) 优于 NSGA-II warm-start (1.692 m²)——AGE-MOEA 在短代际精炼场景下收敛更快。但两者均未超越纯物理 ground truth (1.646 m²)，差距 0.7%。

---

## 6. 代理模型验证

### 交叉切片

以 Knee 点为锚，4 维各扫 60 步。LGBM 与物理引擎曲线紧密贴合——模型学到了物理趋势而非记忆离散点。

### Pareto 拓扑指标

| 指标 | 值 | 阈值 |
|---|---|---|
| Hypervolume Deviation | 1.19% | < 10% 发表级 |
| IGD | 0.0120 | < 0.05 优秀级 |

---

## 7. Bonus：负结果汇总

| 方法 | 结果 |
|---|---|
| RBF 局部精炼 | 三版迭代无一改进（30/300/500 点） |
| 置信域序列优化 | 三轮全部 FAILURE |
| Ridge+LGBM Stacking | 全局 MAE 更好但优化效果更差 |

三项负结果从反面验证：双阶段 warm-start 框架已触及当前物理模型下 10% 边界的全局极限。

---

## 8. 多房间 Pareto Scale 规律

在 7 组房间尺寸（5×5 至 20×20m）上运行纯 NSGA-II (pop=200, gen=200)：

| Room | 时间 | Knee | 面积占比 | xc | Lx | Lz |
|---|---|---|---|---|---|---|
| 5×5m | 74s | 0.22 m² | 1.4% | 2.82 | 1.84 | 0.12 |
| 8×6m | 75s | 1.10 m² | 4.6% | 4.10 | 7.79 | 0.14 |
| 10×10m | 84s | 1.62 m² | 5.4% | 5.18 | 8.80 | 0.18 |
| 12×10m | 88s | 5.80 m² | 16.1% | 6.25 | 10.52 | 0.55 |
| 15×12m | 97s | 8.69 m² | 19.3% | 7.59 | 9.53 | 0.91 |
| 18×14m | 122s | 12.29 m² | 22.8% | 9.06 | 10.87 | 1.13 |
| 20×20m | 193s | 14.83 m² | 24.7% | 9.94 | 11.77 | 1.26 |

**规律**：xc≈room_x/2（窗口始终居中）；Lx 随宽度增长至 ~12m 饱和；Lz 从 0.12m 增至 1.26m；面积占比从 1.4% 升至 25%；所有房间 outage 稳定 ~9.9%。配图 multi_room_pareto.png。

## 9. 最终总结

| 方法 | 面积 | 评估次数 | 墙钟 |
|---|---|---|---|
| 纯物理 NSGA-II | 1.646 m² | 60,000 | 217s |
| 纯代理 LGBM | 1.755 m² | 0 | 12s |
| Dual NSGA-II | 1.692 m² | 6,000 | 45s |
| **Dual AGE-MOEA** | **1.658 m²** | **6,000** | **84s** |

最佳性价比：Dual AGE-MOEA，面积距 ground truth 仅 0.7%，物理评估节省 90%。

---

## 附录：文件索引

| 目录 | 核心文件 |
|---|---|
| `python_optimization/` | `pareto_front.ipynb`, `algorithm_comparison.ipynb`, `pareto_jump_diagnostic.ipynb` |
| `surrogate_lgbm/` | `train_lgbm_surrogate.ipynb`, `full_comparison.ipynb`, `final_validation.ipynb` |
| `legacy/` | Trust-Region, RBF, Stacking 实验归档 |
