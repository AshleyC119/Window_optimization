# EM Window Optimization — Part 1: Fixed-Room (10×10m)

> KDE 经验权重 + 多高度网格 + 自阻塞模型 + NSGA-II Pareto 前沿 + 双阶段代理优化。

---

## 1. 算法互证：NSGA-II vs AGE-MOEA vs MOEA/D

同一物理引擎上运行三种机制不同的多目标算法。

| 算法 | 核心机制 | 种群/代数 |
|---|---|---|
| NSGA-II | Pareto dominance + crowding distance | 300 × 200 |
| AGE-MOEA | 自适应几何估计 | 300 × 200 |
| MOEA/D | 标量化分解 (299 子问题, Tchebycheff) | 按子问题数 |

```
NSGA-II:  1.6456 m² @ 9.97%  (300 pts)
AGE-MOEA: 1.6973 m² @ 9.96%  (300 pts)
MOEA/D:   1.6557 m² @ 9.92%  (167 pts)
max Δarea = 0.05 m² (3%), max Δoutage = 0.05pp
```

三算法收敛到同一前沿，排除局部最优。附带平行坐标图、幕墙立面图、3D 决策空间图。

---

## 2. BO-LGBM 代理模型

构建物理引擎的 μs 级替代。

| 来源 | 数量 | 说明 |
|---|---|---|
| LHS 全域 | 5,000 | 4D 均匀覆盖 |
| NSGA-II 真实前沿 | 300 | Pareto 边界全覆盖 |
| 边界过采样 | 2,000 | xc≈5, zc≈1.3 |
| **合计** | **7,300** | |

- 模型: LightGBM (树天然适配 sinc 非连续响应面)
- 训练: Optuna 50 轮 × 5-Fold CV, feasible-MAE 为目标
- 结果: `Feasible MAE = 0.52%, R² all = 0.995, R² feasible = 0.908`

---

## 3. 代理悖论与 Warm-Start 解法

纯代理 NSGA-II 在可行域边界有局部系统性偏差，演化算法放大为 6-7% gap。

**Phase 1** — NSGA-II 在 LGBM 上 200 代 (~12s)。**Phase 2** — 250 精英 + 50 随机混合, 物理 NSGA-II/AGE-MOEA 仅跑 20 代。

```
评估次数           墙钟
纯物理 NSGA-II      60,000     134s
纯代理 LGBM              0      12s
双阶段 NSGA-II       6,000      45s
双阶段 AGE-MOEA      6,000      84s
```

---

## 4. Pareto 前沿特征

### Knee 解

```
xc=5.22, zc=1.29, Lx=9.26, Lz=0.18
Area=1.682 m², Outage=9.93%
```

### 双跳变

**Knee Jump @ 9.7%**：Lz 0.54→0.20 (−63%), Lx 7.32→9.31 (+27%)——十字転置。

**Jump B @ 13.0%**：Lx 2.22→0.15 (−93%)——同向极限压缩。

两跳在 Gaussian 和 KDE 两套权重均被证实。

---

## 5. 代理全维度对比（四臂 + 四角度）

| Arm | 评估器 | 墙钟 | Knee |
|---|---|---|---|
| Pure Physics | 物理引擎 | 134s | **1.6456 m²** |
| Pure Surrogate | LGBM | 12s | 1.7554 m² |
| Dual-Stage NSGA2 | LGBM + Physics NSGA2 20g | 45s | 1.6915 m² |
| **Dual AGE-MOEA** | LGBM + Physics AGE-MOEA 20g | 84s | **1.6578 m²** |

四角度分析（配图 `full_comparison.ipynb` 产出）：
- **Angle 1 (基因多样性坍塌)**：代理 warm-start 种群从 gen 0 即收敛，纯物理需 80 代
- **Angle 2 (虚假最优退潮)**：代理初始解大面积越界，物理引擎接管后 5→15 代滑回 10% 红线
- **Angle 3 (约束违规率)**：纯物理早期 ~65% 违规，代理 warm-start 从 gen 0 起 ≈0%
- **Angle 4 (Pareto 四线对比)**：灰(物理)、红(纯代理)、绿(Dual NSGA2)、橙(Dual AGE) 同台

AGE-MOEA warm-start (1.658 m²) 优于 NSGA-II warm-start (1.692 m²)，距 ground truth (1.682 m²) 差 1.4%。

---

## 6. 代理模型验证

**交叉切片**：4 维各扫 60 步，LGBM 与物理引擎紧密贴合。

**Pareto 拓扑指标**：

| 指标 | 值 | 阈值 |
|---|---|---|
| HV Deviation | 1.19% | < 10% 发表级 |
| IGD | 0.0120 | < 0.05 优秀级 |

---

## 7. Bonus：负结果

| 方法 | 结论 |
|---|---|
| RBF 局部精炼 | 三版迭代无一改进 |
| 置信域序列优化 | 三轮全部 FAILURE |
| Ridge+LGBM Stacking | 全局 MAE 优化但优化效果更差 |
| GP+LGBM Stacking | O(n³) 限制, feasible MAE 退化 |
| 纯代理 AGE-MOEA (第四臂) | 不如 NSGA-II |

---

## 8. 最终总结

| 方法 | Knee | 评估次数 | 墙钟 |
|---|---|---|---|
| 纯物理 NSGA-II | 1.682 m² | 60,000 | 134s |
| 纯代理 LGBM | 1.755 m² | 0 | 12s |
| Dual NSGA-II | 1.692 m² | 6,000 | 45s |
| **Dual AGE-MOEA** | **1.658 m²** | **6,000** | **84s** |

## 文件索引

| 目录 | 核心文件 |
|---|---|
| `python_optimization/` | `pareto_front.ipynb`, `algorithm_comparison.ipynb`, `pareto_jump_diagnostic.ipynb` |
| `surrogate_lgbm/` | `train_lgbm_surrogate.ipynb`, `full_comparison.ipynb`, `final_validation.ipynb` |
| `legacy/` | Trust-Region, RBF, Stacking 实验归档 |
