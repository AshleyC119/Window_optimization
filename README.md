# EM Window Optimization

> 电磁窗口在建筑幕墙上的最优配置 — 多目标 Pareto 前沿 + 双阶段代理优化。

## 核心结果

**固定房间 (10×10m)**：Pure NSGA-II 1.682 m² @ 9.93% (134s)；Dual AGE-MOEA 1.658 m² (84s)。

**动态房间 (2–20m)**：21 特征 LGBM (Feasible MAE 0.25%) + Wildcard Pipeline (gap < 2%)。

## 报告

| 文件 | 内容 |
|---|---|
| `REPORT_PART1_FIXED_ROOM.md` | 固定 10×10m 完整汇报 |
| `REPORT_PART2_DYNAMIC_ROOM.md` | 动态 2–20m 完整汇报 |
| `REPORT.md` | 报告索引 |

## 目录

```
Window_optimization/
├── 📄 README.md / REPORT*.md
│
├── 📁 python_optimization/              固定房间物理优化
│   ├── pareto_front.ipynb               NSGA-II Pareto 前沿 ⭐
│   ├── algorithm_comparison.ipynb       三算法互证 (NSGA2/AGE/MOEA)
│   ├── pareto_jump_diagnostic.ipynb     Knee Jump + Jump B 归因
│   ├── pareto_comparison.ipynb          自阻塞消融对比
│   ├── ergodicity_validation.ipynb      KDE vs Markov 收敛验证
│   └── METHODOLOGY.md
│
├── 📁 surrogate_lgbm/                   固定房间代理模型
│   ├── train_lgbm_surrogate.ipynb       BO-LGBM 训练 (4D)
│   ├── full_comparison.ipynb            四臂 + 四角度对比 ⭐
│   └── final_validation.ipynb           交叉切片 + HV/IGD 验证
│
├── 📁 dynamic_optimization/             动态房间物理优化
│   ├── pareto_front.ipynb               NSGA-II (参数化房间)
│   ├── multi_room_batch.ipynb           7 房间批量 (pop=300) ⭐
│   └── engine_compare.ipynb             4D vs 动态引擎对比（诊断用）
│
├── 📁 dynamic_room/                     动态房间代理模型
│   ├── generate_training_data.ipynb     30k 样本生成 (多进程 KDE)
│   ├── train_lgbm.ipynb                 21 特征 LGBM 训练
│   ├── pipeline_v1p5.ipynb              最终 Wildcard Pipeline ⭐
│   ├── pipeline.ipynb                   原版 Pipeline
│   ├── pipeline_tune.ipynb              网格搜索调优 (P1×P2)
│   ├── pipeline_compare.ipynb           原版 vs v1.5 全房间对比
│   ├── pipeline_vs_pure.ipynb           三线 Pareto 叠加图
│   └── validate_model.ipynb             三路 HV/IGD 验证
│
└── 📁 legacy/                           归档
    ├── stacking/                        Ridge+LGBM (负结果)
    ├── dynamic_room_v2/                 v2 实验 (逆对数采样)
    └── search_channel.m                 MATLAB 原版
```
