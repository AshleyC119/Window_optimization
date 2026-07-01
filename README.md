# EM Window Optimization

> 电磁窗口（Electromagnetic Window）在玻璃幕墙上的最优配置——多目标 Pareto 前沿 + 形态突变物理归因。

## 概览

在 10m×3m 的建筑幕墙上寻找最优开窗位置和尺寸，使得室内 5 个用户的加权断网率 < 10% 的前提下面积最小。

| 方法 | 笔记本 | 说明 |
|---|---|---|
| **NSGA-II Pareto** ⭐ | `python_optimization/pareto_front.ipynb` | 多目标前沿，KDE+多高度网格，权威结果 |
| 网格 GA + Adam | `python_optimization/grid_search.ipynb` | 单目标确定性优化 + PyTorch 精调 |
| 双跳诊断 | `python_optimization/pareto_jump_diagnostic.ipynb` | 十字転置 + 同向压缩物理归因 |
| 各态历经验证 | `python_optimization/ergodicity_validation.ipynb` | Markov 长时极限 vs 网格积分，Δ=0.67% |
| MATLAB 交叉验证 | `python_optimization/cross_validate_matlab.ipynb` | 独立评估 MATLAB 解的统计可靠性 |
| 代理模型流水线 | `surrogate/` | LHS 采样 → MLP 训练 → 两阶段 Pareto |

## 核心结果

```
NSGA-II (pop=300, gen=200, KDE weights + 5-height grid):

Knee 解 (outage ≤ 10%, 最小面积):
  xc=5.346 m   zc=1.297 m
  Lx=2.043 m   Lz=0.178 m
  Area = 0.363 m²
  Grid Outage = 9.97%

Pareto 前沿范围: area [0.01, 19.19] m², outage [0.04%, 15.51%]
```

Pareto 前沿上存在两个形态突变：Jump A (7.6%) 为 Lz 十字転置，Jump B (10.0%) 为 Lx 同向极限压缩。两个突变在两套独立权重模型下均被证实——是衍射物理的鲁棒特征，不是建模 artifact。

## 方法演进

```
MATLAB (search_channel.m)
  RWP 随机轨迹 150 点 → 高方差 → GA 2代早停
    ↓
确定性网格积分 (旧)
  200×200 @ z=1.5m, Gaussian σ=2.5 权重 → 系统性低估 outage 3%
    ↓
KDE + 多高度网格 (新) ⭐
  200×200 × 5层z [1.5..2.0], RWP 100ks→KDE 经验权重
  与 Markov 长时极限 Δ=0.67%, R²=0.994
```

## 目录结构

```
├── search_channel.m                 MATLAB 原版 GA
├── Reference.md                     五篇论文数学模型
│
├── python_optimization/
│   ├── pareto_front.ipynb           NSGA-II ⭐
│   ├── grid_search.ipynb            网格 GA+Adam
│   ├── pareto_jump_diagnostic.ipynb 双跳归因
│   ├── ergodicity_validation.ipynb  各态历经验证
│   ├── cross_validate_matlab.ipynb  MATLAB 交叉验证
│   ├── README.md                    优化工作收尾报告
│   └── METHODOLOGY.md               方法论详解
│
├── surrogate/
│   ├── data_generator.py            LHS 数据采集
│   ├── train_surrogate.py           MLP 训练
│   ├── surrogate_analysis.ipynb     代理模型分析
│   ├── two_phase_pareto.ipynb       代理粗筛+物理验证
│   └── README.md                    代理管线状态
│
└── legacy/                          已弃用文件
```

## 运行

所有 notebook 在 Kaggle (GPU T4×2) 上测试通过。单个 cell 执行，需 `!pip install pymoo -q`。
