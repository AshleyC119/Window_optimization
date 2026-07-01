# Python Optimization — Final Report

> 核心产出：KDE 经验权重 + 多高度网格 + NSGA-II Pareto 前沿 + 双跳形态突变归因。
> 详细方法论见 `METHODOLOGY.md`。

---

## 1. 方法论演进

| 阶段 | 评估方式 | 优化算法 | Knee 面积 | 可靠性 |
|---|---|---|---|---|
| MATLAB | RWP 150 点随机轨迹 | GA (单目标标量) | 0.012 m² | 不可靠 (σ=4.5%) |
| Grid GA (旧) | 40k 网格, Gaussian 权重 | GA (单目标) | 0.024 m² | 有偏 (Δ=3%) |
| **NSGA-II (新)** ⭐ | 200k 网格, KDE+5z 权重 | NSGA-II (双目标) | **0.363 m²** | **可靠 (Δ=0.67%, R²=0.99)** |

Gaussian 权重已被 KDE 经验权重取代——`ergodicity_validation.ipynb` 证明了 KDE 网格积分与 Markov 长时极限在统计上一致。

---

## 2. `pareto_front.ipynb` 设计

### 2.1 物理引擎

```
200×200 空间网格 × 5 层 z [1.5..2.0] → 200,000 采样点
权重: RWP 100,000s → KDE 经验稳态分布
信道: equivalent_farfield_channel_2 (L1=2, LoS+NLoS, sinc 衍射)
NLoS 参数: seed=42, 确定性预生成
全部驻留 GPU 显存
```

### 2.2 NSGA-II 配置

```
n_var=4 (xc,zc,Lx,Lz), n_obj=2 (area, outage)
pop=300, gen=200 = 60,000 次确定性评估
```

### 2.3 结果

```
Knee: xc=5.35, zc=1.30, Lx=2.04, Lz=0.18, area=0.363 m², outage=9.97%
Pareto: area [0.01, 19.19] m², outage [0.04%, 15.51%]
```

---

## 3. Pareto 前沿上的两个形态突变

| | Jump A (7.6%) | Jump B (10.0%) |
|---|---|---|
| 突变轴 | Lz −65% | Lx −95% |
| 物理 | 十字転置（衍射模式切换） | 同向极限压缩 |
| 机制 | Lz 骤降 → 垂直衍射角暴增 → 模式质变 | Lz 触及衍射底线 → Lx 被迫骤降 |

两跳在两套独立权重模型（Gaussian 和 KDE）下均被证实——是衍射物理的鲁棒特征。

---

## 4. 文件说明

| 文件 | 用途 |
|---|---|
| `pareto_front.ipynb` | NSGA-II Pareto 前沿 ⭐ 权威 |
| `grid_search.ipynb` | 确定性网格 GA+Adam (单目标) |
| `pareto_jump_diagnostic.ipynb` | 双跳三步归因 (决策追踪+扫描+sigmoid) |
| `ergodicity_validation.ipynb` | 各态历经收敛测试 (KDE vs Markov) |
| `cross_validate_matlab.ipynb` | MATLAB 解 MC200 交叉验证 |
| `METHODOLOGY.md` | 方法论详细报告 |
