# EM Window Optimization

> 电磁窗口在建筑幕墙上的最优配置 — 多目标 Pareto 前沿 + 双阶段代理优化。

## 核心结果

```
物理 NSGA-II:  1.646 m² @ 9.97%  (227s, 60k evals)
代理辅助:      1.655 m² @ 9.92%  (89s,  6k evals, gap 0.5%)
```

## 目录

```
Window_optimization/
├── 📄 search_channel.m                    MATLAB 原版
├── 📄 README.md / REPORT.md              入口 + 详细汇报
├── 📄 STAGE_SUMMARY.md / Reference.md     阶段总结 + 文献
│
├── 📁 python_optimization/              物理模型 + 多目标优化
│   ├── pareto_front.ipynb               NSGA-II Pareto 前沿 ⭐
│   │   └── pareto_front.png
│   ├── algorithm_comparison.ipynb       三算法互证 (NSGA2/AGE/MOEA)
│   │   └── algo_comparison.png + viz_*.png
│   ├── pareto_jump_diagnostic.ipynb     Knee Jump + Jump B 归因
│   │   └── jump_tracking.png + jump_wall_canvas.png
│   ├── ergodicity_validation.ipynb      KDE vs Markov 收敛验证
│   │   └── fig_exp1/2_convergence.png
│   ├── cross_validate_matlab.ipynb      MATLAB 交叉验证
│   ├── grid_search.ipynb                单目标 GA+Adam
│   ├── searcher_v2.ipynb               MC 轨迹 GA+Adam
│   └── METHODOLOGY.md                   方法论详解
│
├── 📁 surrogate_lgbm/                   代理模型管线
│   ├── train_lgbm_surrogate.ipynb       BO-LGBM 训练
│   │   └── lgbm_surrogate.txt + lgbm_evaluation.png
│   ├── nsga_surrogate_comparison.ipynb  纯 NSGA2 vs 代理辅助 ⭐
│   │   └── angle1-4.png (4 角度对比)
│   ├── age_moea_surrogate.ipynb         两阶段 warm-start (AGE 版)
│   ├── final_validation.ipynb           最终验证 (4D 切片 + HV/IGD)
│   │   └── validation_sweeps.png + pareto_metrics.png
│   ├── trust_region.ipynb               置信域实验 (负结果)
│   └── rbf_local_polish.ipynb           RBF 局部精炼 (负结果)
│
└── 📁 legacy/                           归档
    ├── export_data.m / human_meta_trajectory.csv
    └── stacking/                        Ridge+LGBM 实验 (负结果)
```

## 文档

| 文件 | 内容 |
|---|---|
| `REPORT.md` | 面向导师的详细汇报 (从 AGE-MOEA 讲起) |
| `STAGE_SUMMARY.md` | 全项目阶段总结 |
| `python_optimization/METHODOLOGY.md` | 方法论详解 |
| `Reference.md` | 五篇论文数学模型 |
