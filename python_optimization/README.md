# Python Optimization — Final Report

> 本报告总结 `python_optimization/` 目录下所有工作的最终结果。
> 核心产出：物理 NSGA-II Pareto 前沿 + 双跳形态突变归因分析。

---

## 1. 方法论演进

| 阶段 | 文件 | 目标函数 | 评估方式 | 产出 |
|---|---|---|---|---|
| MATLAB 原版 | `search_channel.m` | `area + 500×max(0, outage−10%)` | 随机轨迹（每次 rand） | 单点，不可靠 |
| 网格 GA | `grid_search.ipynb` | 同上 | 确定性空间网格积分 | 单点，可靠 |
| **多目标 NSGA-II** | **`pareto_front.ipynb`** | **f1=area, f2=outage（独立）** | **同上** | **Pareto 前沿** |
| 交叉验证 | `cross_validate_matlab.ipynb` | MC200 均值 | 同上 | MATLAB 解的真实 outage |
| 双跳诊断 | `pareto_jump_diagnostic.ipynb` | 同上 | 同上 + 一维扫描 | 形态突变物理归因 |

核心跃迁发生在第三步：把"面积和 outage 揉成一个加权标量"升级为"两个独立目标交给 NSGA-II 做非支配排序"。这消除了惩罚权重的人为偏置，让搜索过程直接探索两个维度的 trade-off 全貌。

---

## 2. `pareto_front.ipynb` 设计

### 2.1 物理引擎

```
200×200 空间网格 @ z=1.5m  →  40,000 个采样点
热点权重: f_hr(r) = 0.7·Gaussian(μ=(5,5), σ=2.5) + 0.3·Uniform
信道: equivalent_farfield_channel_2 (L1=2, LoS+NLoS, sinc 衍射)
NLoS 路径参数: seed=42, 确定性预生成
全部驻留 GPU 显存
```

评估函数 `compute_grid_outage(xc,zc,Lx,Lz)` 是**完全确定性**的——同输入永远同输出。这消除了 MATLAB 原版中随机轨迹带来的评估噪声，是后续所有方法收敛性的基础。

### 2.2 NSGA-II 配置

```python
n_var = 4       # xc, zc, Lx, Lz
n_obj = 2       # f1 = area,  f2 = grid_outage（独立，不求加权和）
n_ieq_constr = 4  # 边界约束，对齐 MATLAB nonlcon

pop_size = 300
n_offsprings = 150
n_gen = 200       # 共 60,000 次物理评估
```

关键：`out["F"] = [area, outage]` 不加权、不求和、不惩罚。NSGA-II 用 Pareto dominance（A 支配 B iff A 在所有目标上 ≤ B 且至少一个 <）决定个体胜负。

### 2.3 最终产出

**Pareto 前沿**：一条"面积越大 outage 越低"的非支配曲线，覆盖面积 0.01–17 m²，outage 0.05%–15%。

**Knee 解**（outage ≤ 10% 下面积最小的点）：

```
xc = 4.809 m    zc = 1.070 m
Lx = 0.100 m    Lz = 0.207 m
Area = 0.0207 m²
Grid Outage = 9.96%
```

xc 稳定在 ~5.1 m（房间 x 方向正中心），zc 稳定在 ~1.05 m（幕墙中低部），这与 MATLAB、Grid GA、随机轨迹 GA 完全一致——最优位置已被多个独立方法确认。

---

## 3. Pareto 前沿上的两个形态突变

NSGA-II 的 Pareto 前沿并非光滑连续——在 outage ≈ 6.1% 和 ≈ 9.5% 两处，面积出现了不连续的垂直跌落。`pareto_jump_diagnostic.ipynb` 对此做了三步归因分析。

### 3.1 Jump A @ 6.1% — 十字转置

```
A:  Lx=7.74m  Lz=0.65m  area=5.00m²  Lx/Lz=12.0
B:  Lx=9.49m  Lz=0.26m  area=2.48m²  Lx/Lz=36.3
    Lz −60%  ← 突变轴
    Lx +23%  ← 补偿拉伸
```

**物理机制**：Lz 骤降 60%，根据菲涅耳衍射 $\sin\theta \propto \lambda/a$，垂直方向的衍射角度扩大了 2.5 倍。衍射主瓣从"垂直准直"突变为"垂直发散"——功能上等同于主瓣旋转了 90°。这是真正的**模式切换**（十字転置）。水平方向的 Lx 被反向拉长来补偿垂直能量的损失，面积净降 50%。

### 3.2 Jump B @ 9.5% — 同向压缩

```
A:  Lx=1.99m  Lz=0.23m  area=0.46m²  Lx/Lz=8.7
B:  Lx=0.17m  Lz=0.24m  area=0.04m²  Lx/Lz=0.7
    Lx −91%  ← 突变轴
    Lz +6%   ← 几乎冻结
```

**物理机制**：与 Jump A 不同——Lz 从未改变策略（始终在 0.23–0.24m），突变仅发生在 Lx。这是水平丝带模式被榨干了全部潜力后的极限压缩，不是模式切换。aspect ratio 翻了 12 倍（8.7→0.7）是 Lx 骤降的数学副产物，而非物理策略的变更。

### 3.3 两跳对比

| | Jump A (6.1%) | Jump B (9.5%) |
|---|---|---|
| 突变轴 | **Lz** (垂直) | Lx (水平) |
| 突变幅度 | −60% | −91% |
| 物理本质 | 十字転置，模式切换 | 同向极限压缩 |
| 衍射变化 | 垂直发散角扩 2.5 倍 | 水平发散角扩 11 倍 |
| xc, zc | 始终 (~5.2, ~1.0) | 始终 (~5.2, ~1.0) |

---

## 4. 最终结论

1. **窗口位置已锁定**。多个独立方法一致指向 xc ≈ 5.1m, zc ≈ 1.05m——房间 x 正中心、幕墙中低部。这是衍射物理决定的唯一最优位置，不受优化算法或评估方式影响。

2. **窗口尺寸存在两条 Pareto 通路**。大开窗时（outage < 6%）用水平丝带策略（Lx >> Lz），小开窗时（outage > 9.5%）切换到垂直狭缝策略（Lx << Lz）。最优可行解坐落在后者的末端——Lx=0.10m, Lz=0.21m, area=0.021m²。

3. **确定性网格积分是正确的方法论基石**。它消除了 MATLAB 原版随机轨迹带来的评估噪声，使 NSGA-II 的 60,000 次评估都面对同一个确定的 loss landscape，这才暴露了上面两个形态突变的物理本质。

4. **10% outage 下的物理下限**。在当前信道模型、高斯热点分布和 200×200 网格精度下，area ≈ 0.02–0.03 m² 是 outage < 10% 的真实 Pareto 前沿位置。MATLAB 报告的 0.012 m² 经过交叉验证确认为单样本统计假象。
