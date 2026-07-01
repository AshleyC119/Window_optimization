# 电磁窗口优化 — Matlab GA 与 Python 对比验证汇报

> 学长好，我按照你给的 Matlab 代码逻辑，用 Python 复现了一套带统计验证的优化框架，也把你原来的 Matlab GA 跑了几遍做对比。下面汇报情况。

---

## 一、做了哪些事

1. 把 `search_channel.m` 里的 GA 参数、信道模型（`equivalent_farfield_channel_2`）、轨迹生成逻辑（`getHumanPosi_custom`）逐行对齐搬到了 Python
2. 跑了 4 遍你的 Matlab 原版代码，记录每次输出
3. 用 Python 写了一个独立交叉验证脚本，对你的 Matlab 解做大样本评估
4. 在 Python 里跑了自己的 Monte Carlo GA + Adam 精调

---

## 二、Matlab 原版重复运行结果

同一份 `search_channel.m`，每次运行不改任何参数，仅靠 `rand()` 产生不同随机种子：

| # | 窗口 (xc, zc, Lx, Lz) | 面积 | 报告 outage | GA 代数 |
|---|---|---|---|---|
| 1 | (5.09, 1.49, 0.10, 0.12) | 0.012 m² | 9.33% | 2 |
| 2 | (4.82, 1.41, 0.10, 0.11) | 0.011 m² | 16.67% | 2 |
| 3 | (6.03, 1.37, 1.50, 0.10) | 0.150 m² | 18.00% | 2 |
| 4 | (5.11, 1.47, 0.10, 0.11) | 0.011 m² | 10.67% | 2 |

窗口参数和 outage 每次都不同，面积从 0.011 跳到 0.150，outage 从 9.33% 跳到 18.00%。

---

## 三、Matlab 代码的局限分析

学长的代码在算法设计上思路很清晰——惩罚函数、非线性约束、全局 GA 选型都没问题。但在实际运行时，GA 面对的是一个高度随机的目标函数，这导致了几个连锁反应。

### 3.1 每次目标函数调用都重新 `rand()`，GA 面对的是随机噪声而非确定的适应度

`obj_fun`（`search_channel.m` 第 65 行附近）内部调用：

```matlab
outage = compute_average_outage(x, params, room_x, room_z_max, ...);
```

而 `compute_average_outage`（第 147 行）每次都调用：

```matlab
[users_trajectory, users_height] = generate_human_trajectory(room_x, room_x, ...);
```

这个函数内部又有两层 `rand()`：`getHumanPosi_custom` 用随机数生成用户初始位置、目标点、暂停状态；同时 `equivalent_farfield_channel_2`（第 237 行）在 NLoS 路径（`l1==2` 分支）中再次调用：

```matlab
psi=2*pi*rand(); tt=-pi+2*pi*rand(); pt=pi*rand();
eta=10^((-15+5*rand())/10);
```

这导致：**同一个候选窗口 `[xc, zc, Lx, Lz]` 先后被评估两次，拿到的是完全不同的 cost。** 对极小窗口（如 0.01 m²），cost 可从 0.012（纯面积）跳到 87（面积 + 500×0.15 的惩罚），波动近万倍。GA 的选择算子很多时候不是在比较"哪个几何更好"，而是在比较"谁这次运气更好"。

### 3.2 GA 因此 2 代即早停，四轮皆如此

每次运行日志都显示：

```
Generation  Func-count        f(x)     Constraint  Stall Generations
    1           2650       40.1855            0      0
    2           5250       13.4832            0      0
优化结束: 适应度值的平均变化小于 options.FunctionTolerance
```

`TolFun=1e-3`，但 Best f(x) 的变化量（40→13，差 27）远大于 1e-4。GA 报告"平均变化 < TolFun"而非"最佳值变化 < TolFun"，说明**种群内所有个体的适应度已经被随机噪声拉到同一水平**，失去了区分度。对于 4 变量强非凸的衍射信道问题，2 代不可能真正收敛——是被噪声"冲平"了。

### 3.3 最终报告的 outage 是单样本，不具备统计意义

GA 跑完后，第 97 行的：

```matlab
final_outage = compute_average_outage(X_opt, params, room_x, room_z_max, ...);
```

又是一次独立的 `rand()` 抽样——和 GA 内部 5250 次评估一样，只是另一次随机。四次运行结果 9.33%→16.67%→18.00%→10.67%，最大差距 8.67 个百分点。可复现性需要再讨论。

### 3.4 综上

三个问题环环相扣：随机目标函数 → 噪声淹没适应度信号 → GA 假收敛 → 单样本报告碰运气。解决方案不是改 GA 算法，而是**给目标函数加 Monte Carlo 平均**——每次评估生成 N 组独立轨迹取 outage 均值，让噪声在评估内部就被消掉。

---

## 四、Python 交叉验证

把 Matlab 第 1 次跑出的窗口 `[5.09, 1.49, 0.10, 0.12]` 固定住，用 Python 引擎跑 200 组独立轨迹和 NLoS 信道：

```
MC200 统计:
  均值 outage:  12.76%
  标准差:        3.39%
  95% CI:       [12.3%, 13.2%]
  <10% 比例:    17.5%  (35/200)
```

Matlab 报告的 9.33% 落在分布的低尾——大约 1/6 的概率。这个窗口在大多数随机环境下并不满足 <10%。

---

## 五、Python 复现的效果（已采用 GPU 加速）  

用对齐后的 Python GA（10 轮 × 150 代，每轮候选解用 3 组随机轨迹评估，MC50 后验筛选）：

```
10 轮 GA 面积分布:
  [0.025, 0.028, 0.161, 0.172, 0.182, 0.198, 0.247, 0.356, 0.469, 0.794] m²
```

最优一轮经 PyTorch Adam 精调：

| 指标 | GA 阶段 | Adam 精调后 |
|---|---|---|
| 窗口 (xc, zc, Lx, Lz) | (4.74, 1.32, 0.16, 0.16) | (4.73, 1.30, 0.16, 0.18) |
| 面积 | 0.025 m² | 0.028 m² |
| MC100 均值 outage | 10.71% | 10.05% |

10 轮中没有任何一轮能同时做到面积 < 0.02 且 MC50 < 10%。这表明在当前的物理模型下，0.02–0.03 m² 可能是 outage < 10% 的真实下限。

---

## 六、关于 `human_meta_trajectory.csv`

这是我早期为了严格控制变量从 Matlab 导出的静态轨迹快照（`export_data.m`，`sim_time=2000`）。第一版 Python 用它做确定性优化，后来发现固定数据集相当于只有一份测试试题，GA 容易过拟合。现在 `searcher_v2.ipynb` 已改为直接移植你的 `getHumanPosi_custom` 在 Python 里动态生成轨迹（`sim_time=300, dt=10`），不再依赖 CSV。

---

## 七、后续想法

Python 版的 GA 阶段已基本完善，但 **Adam 精调** 阶段还有优化空间，我比较不满意。当前 Adam 用 sigmoid 可微逼近计算梯度，sigmoid 的斜率在参数空间平坦处较浅。后续打算试一下**直接对硬 outage 做数值梯度近似**（有限差分或 SPSA），绕过 sigmoid 的逼近误差。如果做通了，在保持统计严谨的前提下有可能把面积从 0.025 进一步压到 0.02 附近。

---

## 八、建议

如果不想大改 Matlab 代码，最小改动是在 `compute_average_outage` 里加一个循环，多生成几组独立轨迹取平均：

```matlab
function avg_outage = compute_average_outage(x, ..., N_MC)
    out = zeros(1, N_MC);
    for i = 1:N_MC
        [users_trajectory, users_height] = generate_human_trajectory(...);
        % ... 原有 outage 计算逻辑 ...
        out(i) = total / n_users;
    end
    avg_outage = mean(out);
end
```

`N_MC=10` 就能把单样本的标准差从 ~3.4% 压到 ~1.1%。

---

## 文件清单

| 文件 | 用途 |
|---|---|
| `search_channel.m` | 你的 Matlab GA（原版不动） |
| `export_data.m` | 轨迹导出脚本（旧，供参考） |
| `human_meta_trajectory.csv` | 旧版固定轨迹数据（已弃用） |
| `searcher_v2.ipynb` | Python MC GA + Adam（GPU 可跑） |
| `cross_validate_matlab.ipynb` | 独立交叉验证脚本 |
| `grid_search.ipynb` | **NEW** 网格积分版（确定性目标，GPU 加速） |
| `output.txt` | `searcher_v2.ipynb` 的 Kaggle 运行输出 |
| `PROGRESS_REPORT.md` | 本报告 |
| `Reference.md` | 五篇论文的数学模型梳理 |
