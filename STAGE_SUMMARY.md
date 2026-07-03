# EM Window Optimization — Stage Summary

> 从 MATLAB GA 到三算法互证 + BO-LGBM 代理模型。

---

## 1. 评估函数演进

| 阶段 | 权重 | 高度 | 自阻塞 | 与 Markov 极限偏差 |
|---|---|---|---|---|
| Gaussian (旧) | 0.7·N(σ=2.5) | z=1.5 单层 | 无 | Δ=3%, R²=0.78 |
| **KDE (新)** | RWP 100ks→KDE | 5 层 [1.5..2.0] | 4 方向 E[Se] | **Δ=0.67%, R²=0.994** |

---

## 2. 优化算法升级

NSGA-II 用 Pareto dominance 将面积和 outage 作为两个独立目标优化，消除惩罚权重的任意性。产出完整 Pareto 前沿而非单点。

---

## 3. 算法对比（AGE-MOEA + MOEA/D）

同一物理引擎上运行三种机制不同的多目标算法：

```
NSGA-II:  1.6456 m² @ 9.97%  (Pareto dominance)
AGE-MOEA: 1.6973 m² @ 9.96%  (自适应几何估计)
MOEA/D:   1.6557 m² @ 9.92%  (标量化分解)
max Δ < 6%, max Δoutage < 0.05pp
```

三算法互证排除局部最优。附带平行坐标图、幕墙立面图、3D 决策空间图。

---

## 4. BO-LGBM 代理模型

LightGBM 树模型平替物理引擎，对齐顶刊 BO-LGBM + AGE-MOEA 范式。

**数据**：5000 LHS + 300 NSGA-II 真实 Pareto 前沿点 + 2000 边界过采样 = 7300 样本。  
**训练**：Optuna 50 轮贝叶斯超参搜索，5-Fold CV 以 feasible-MAE 为目标。

| 指标 | 值 |
|---|---|
| Feasible MAE | 0.52% |
| R² all | 0.995 |
| R² feasible | 0.908 |
| 代理→物理 Knee | 1.74 m² @ 9.95% |
| 真实 NSGA-II Knee | 1.64 m² @ 9.97% |
| 代理 gap | **6%** |

---

## 5. Pareto 前沿特征

### 5.1 Knee 解

```
xc=5.29, zc=1.28, Lx=9.33, Lz=0.18
Area=1.642 m², Outage=9.88%
```

### 5.2 形态突变

Jump A（~7.6%, Lz 十字転置）和 Jump B（~10.0%, Lx 同向极限压缩）。两跳在 Gaussian 和 KDE 两套权重下均被证实——是衍射物理的鲁棒特征。

---

## 6. 与 MATLAB 对比

| | MATLAB | 当前 |
|---|---|---|
| 评估方式 | 随机轨迹 150 点 | KDE 网格 200,000 点 |
| 自阻塞 | 未建模 | 4 方向几何 E[Se] |
| 优化算法 | GA 单目标 | NSGA-II + AGE-MOEA + MOEA/D |
| 代理模型 | 无 | BO-LGBM (MAE 0.52%) |
| 产出 | 1 个不可靠点 | 三算法互证 + 代理验证 |
