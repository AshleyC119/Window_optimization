# EM Window Optimization

> 电磁窗口在建筑幕墙上的最优配置 — 多目标 Pareto 前沿 + 双阶段代理优化。

## 核心结果

```
物理 NSGA-II (ground truth):  1.64 m² @ 9.97%  (60,000 evals)
双阶段 BO-LGBM + Warm-Start:  1.66 m² @ 9.92%  (6,000 evals, gap 1%)
三算法互证 (NSGA2/AGE/MOEA):  max Δ < 3%
```

## 方法概要

| 组件 | 说明 |
|---|---|
| 评估引擎 | 200×200×5 层 KDE 网格 + 4 方向几何自阻塞 |
| 权重 | RWP 100ks → KDE 经验稳态分布 (Δ vs Markov: 0.67%) |
| 优化算法 | NSGA-II / AGE-MOEA / MOEA/D (三算法互证) |
| 代理模型 | BO-LGBM (Optuna 调参, feasible MAE 0.52%) |
| 最终方案 | LGBM 代理粗筛 → 物理 warm-start 精炼 (gap 1%) |

## 文档

| 文件 | 内容 |
|---|---|
| `STAGE_SUMMARY.md` | 全项目阶段总结 |
| `REPORT.md` | 面向导师的详细汇报 (从 AGE-MOEA 讲起) |
| `python_optimization/METHODOLOGY.md` | 方法论详解 |
| `Reference.md` | 五篇论文数学模型 |

## 目录

```
python_optimization/    物理模型优化 (NSGA-II, AGE-MOEA, MOEA/D, Jump 诊断)
surrogate_lgbm/         BO-LGBM 代理模型 + 两阶段精炼 + RBF 尝试
legacy/                 已弃用文件
```
