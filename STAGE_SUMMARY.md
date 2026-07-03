# EM Window Optimization — Stage Summary

> 从 MATLAB GA 到三算法互证的 Pareto 前沿：评估函数、物理建模、优化算法的全链路升级。

---

## 1. 评估函数演进

### 1.1 随机轨迹 → 确定性网格积分

MATLAB `search_channel.m` 每次 GA 评估时用 RWP 生成 5 用户 × 300 秒 = 150 个随机轨迹点。150 个点远不够做统计——同一窗口两次评估 outage 差 7pp。GA 被噪声淹没，2 代早停。

**修正**：200×200 空间网格 × 5 层 z [1.5..2.0] = 200,000 个确定性格点。每格点独立计算 SINR → rate → outage，加权求和。完全确定性——同输入永远同输出。

### 1.2 Gaussian 权重 → KDE 经验权重

初始网格使用 0.7·Gaussian(σ=2.5) + 0.3·Uniform 作为空间权重。经验证（`ergodicity_validation.ipynb`），Gaussian 权重对 Markov 长时极限偏差 3%，R²=0.78——系统性低估 outage，因为它把权重过度集中在房间中心 2m 半径内。

**修正**：RWP 运行 100,000 秒 → 50,000 轨迹点 → KDE 高斯核密度估计 → 在 200×200 xy 网格上求值 → 复制到 5 个 z 层。KDE 权重与 Markov 长时极限偏差 0.67%，R²=0.994。

### 1.3 自阻塞建模

补充 Reference.md C.3 节的人体 60° 盲区模型。对每格点采样 4 个均匀朝向（绕 Z 轴），计算窗口→用户向量与后背的夹角 φ，信号衰减因子 Se = (π − max(0, 2π/3−φ))/π ∈ [1/3, 1]。四朝向平均后修正 SINR：Se·dp/(Se·intf+N0)。

自阻塞将 Knee 面积从 0.36 m² 推至 1.64 m²——是物理模型的正确行为，非过度惩罚。

---

## 2. 优化算法升级

### 2.1 单目标标量 → 多目标 NSGA-II

MATLAB 使用 `area + 500×max(0, outage−10%)` 的标量加权。NSGA-II 用 Pareto dominance 将面积和 outage 作为两个独立目标同时优化，消除惩罚权重的任意性，产出完整 Pareto 前沿而非单点。

### 2.2 三算法互证

在同一物理引擎上运行 NSGA-II（Pareto dominance）、AGE-MOEA（自适应几何估计）、MOEA/D（标量化分解）：

```
NSGA-II:  1.6456 m² @ 9.97%  (300 pts)
AGE-MOEA: 1.6973 m² @ 9.96%  (300 pts)
MOEA/D:   1.6557 m² @ 9.92%  (167 pts)

max Δarea = 0.05 m² (3%), max Δoutage = 0.05pp
```

三个机制完全不同的算法收敛到同一条前沿，排除了局部最优的可能。这条前沿即当前物理模型下的全局 Pareto 极限。

---

## 3. Pareto 前沿特征

### 3.1 Knee 解

```
xc=5.29, zc=1.28, Lx=9.33, Lz=0.18
Area=1.642 m², Outage=9.88%
```

xc 稳定在 ~5.3m（房间 x 正中心），zc 稳定在 ~1.3m（幕墙中低部）。Lx 近满墙宽（9.33/10）对抗自阻塞，Lz 被压至衍射极限（0.18m）。

### 3.2 两个形态突变

Pareto 前沿上存在 Jump A（~7.6%，Lz 十字転置）和 Jump B（~10.0%，Lx 同向极限压缩）。两跳在 Gaussian 和 KDE 两套独立权重模型下均被证实——是衍射物理的鲁棒特征，非建模 artifact。

---

## 4. 文件清单

| 文件 | 用途 |
|---|---|
| `python_optimization/pareto_front.ipynb` | NSGA-II Pareto 前沿 ⭐ 权威 |
| `python_optimization/algorithm_comparison.ipynb` | 三算法对比 |
| `python_optimization/pareto_jump_diagnostic.ipynb` | 双跳三步归因 |
| `python_optimization/ergodicity_validation.ipynb` | KDE vs Markov 收敛验证 |
| `python_optimization/cross_validate_matlab.ipynb` | MATLAB 解 MC200 验证 |
| `python_optimization/grid_search.ipynb` | 单目标 GA+Adam |
| `python_optimization/searcher_v2.ipynb` | MC 轨迹 GA+Adam |
| `python_optimization/METHODOLOGY.md` | 方法论详解 |
| `python_optimization/README.md` | 本目录收尾报告 |
| `surrogate/` | 代理模型管线（WIP） |

---

## 5. 与 MATLAB 的对比

| 维度 | MATLAB | 当前 |
|---|---|---|
| 评估方式 | 随机轨迹 150 点 | KDE 网格 200,000 点 |
| 确定性 | 每次不同 (σ=4.5%) | 完全确定 |
| 与长时极限偏差 | 无法验证 | Δ=0.67%, R²=0.994 |
| 自阻塞 | 未建模 | 4 方向 E[Se], XY 面朝向 |
| 权重 | RWP 时间平均 | RWP 100ks → KDE |
| 高度 | 1.5+0.5×rand | 5 层 [1.5..2.0] |
| 优化算法 | GA 单目标 | NSGA-II + AGE-MOEA + MOEA/D |
| 产出 | 1 个点（不可靠） | 三算法互证 Pareto 前沿 |
| Knee 面积 | 0.012 m²（假象） | 1.642 m²（可靠） |
