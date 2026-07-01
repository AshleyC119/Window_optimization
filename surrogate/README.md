# Surrogate Model Pipeline — Status Report

> 目标：训练一个 μs 级推理的神经网络，替代 ms 级 GPU 网格积分，
> 嵌入 NSGA-II 后实现超大规模（>100k 次）Pareto 搜索。

---

## 1. 已完成的工作

### 1.1 数据采集 (`data_generator.py`)

| 项目 | 值 |
|---|---|
| 抽样方法 | 拉丁超立方 (LHS, 4D) |
| 样本量 | 10,000 组 |
| 评估引擎 | 确定性 GPU 网格积分（与 `pareto_front.ipynb` 相同） |
| 输出 | `X[N×4]` (xc,zc,Lx,Lz) → `Y[N×2]` (area, grid_outage) |
| 格式 | CSV + PyTorch .pt |

### 1.2 模型训练 (`train_surrogate.py`)

| 项目 | 值 |
|---|---|
| 架构 | 残差 MLP, 4×256×256×256×256→1, ReLU+BN+Skip |
| 参数量 | 330k |
| 损失函数 | 可行域加权 MSE（outage<10% 样本权重 ×3） |
| 训练/验证 | 80/20, 300 epochs, CosineAnnealing |
| **R²** | **0.9858** |
| **MAE** | **1.68% outage** |

### 1.3 代理模型应用

| 文件 | 内容 | 结果 |
|---|---|---|
| `surrogate_analysis.ipynb` | 敏感性热力图 + 代理 NSGA-II | 代理 Pareto 未捕获小窗区域 |
| `two_phase_pareto.ipynb` | 代理粗筛 + 物理验证 | area=0.032 m², 劣于纯物理 0.021 m² |

---

## 2. 当前问题

### 2.1 可行域样本严重不足

LHS 在 4D 空间中均匀抽样，但可行域（outage < 10%）只占总搜索体积的 ~6%：

```
10,000 samples → 603 feasible (6.0%)
```

代理模型在这 6% 的稀疏区域学得不够好。极小窗口（< 0.1 m²）的样本更少，模型系统性高估 outage → NSGA-II 不敢往小窗区域探索 → 代理 Pareto 前沿在小窗段完全缺失。

### 2.2 代理 Pareto 劣于纯物理 Pareto

```
纯物理 NSGA-II (60k evals):   Knee area = 0.021 m²
代理+物理验证 (两阶段):       Knee area = 0.032 m²  (差 50%)
```

两阶段的逻辑是"代理筛选 → 物理验证top candidates"，但如果代理模型在关键区域（小窗+低 outage）的排序本身就是错的，筛选阶段就会丢掉真正的好解。

### 2.3 模型对 zc 的敏感度可能不够

物理上 zc 是 outage 的最强预测因子（相关系数 0.81），但代理模型只有 4 层 256 维——对于 4D 输入来说已经够大，问题不在容量，而在训练数据的覆盖密度。

---

## 3. 改进方向

| 方向 | 方法 | 预期收益 |
|---|---|---|
| **A. 主动学习** | 用物理 NSGA-II 的 Pareto 前沿解作为额外训练样本 | 精准增加可行域边界的样本密度 |
| **B. 目标采样** | 第二轮 LHS 限定在 outage < 30% 的区域 | 提高小窗区的样本比例 |
| **C. 分类+回归级联** | 先训一个二分类器（feasible?），再训回归器 | 两阶段解耦，各自优化 |
| **D. 更大的模型** | 增加深度/宽度 | 边际收益，不是根本问题 |

推荐优先做 **A**：`pareto_front.ipynb` 已经产出了 300 个高质量的 Pareto-optimal 样本，全部落在可行域边界上。把这 300 个样本加入训练集（并大幅提高它们的权重），代理模型立刻就能学会小窗区域的行为。成本极低——不需要重新采样，不需要改架构。

---

## 4. 文件清单

| 文件 | 用途 |
|---|---|
| `data_generator.py` | LHS 数据采集脚本 |
| `em_window_dataset/` | 10k 训练数据 (CSV + PT) |
| `train_surrogate.py` | 模型训练脚本 |
| `surrogate_model.pt` | 训练好的模型 (330k params) |
| `training_diagnostics.png` | 训练诊断图 (loss + pred/true + error dist) |
| `surrogate_analysis.ipynb` | 敏感性热力图 + 代理 NSGA-II |
| `two_phase_pareto.ipynb` | 代理粗筛 + 物理验证 |
| `two_phase_pareto.png` | 双面板对比图 |
