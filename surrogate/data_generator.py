#!/usr/bin/env python3
# =====================================================================
# data_generator.py — 离线数据集采集脚本
# 目标：生成高质量 (X, Y) 样本，供后续代理模型（Surrogate Model）训练
#
# X ∈ R^{N×4} : [xc, zc, Lx, Lz]  窗口中心坐标与尺寸
# Y ∈ R^{N×2} : [area, grid_outage]  几何面积  与  加权网格中断率
#
# 抽样策略：拉丁超立方 (LHS)，确保 4 维空间填充性
# 评估引擎：确定性 GPU 网格积分（复用 parent_front 的验证闭环）
# 输出格式：.csv（人类可读） + .pt（PyTorch 直接加载）
# =====================================================================

import torch
import numpy as np
import math
import os

# ============================================================
# 0. 全局配置
# ============================================================
N_SAMPLES   = 10000       # 总样本数
BATCH_SIZE  = 100         # GPU 每批评估量（T4 14.5GiB 下安全）
DEVICE      = 'cuda' if torch.cuda.is_available() else 'cpu'

# 输出文件路径
OUT_CSV = 'em_window_dataset.csv'
OUT_PT  = 'em_window_dataset.pt'

print(f'Device: {DEVICE}')
print(f'Total samples: {N_SAMPLES}, batch size: {BATCH_SIZE}')

# ============================================================
# 1. 系统物理常量（与 search_channel.m 严格对齐，不动）
# ============================================================
room_x, room_y, room_z_max = 10.0, 10.0, 3.0
x_BS, y_BS, z_BS = 10.0, -100.0, -10.0
E = 8; d_B = 0.075; lambda_val = 0.075; L1 = 2
d_ref = abs(y_BS) * 1.5
P_BS_dBm = 40.0; R_th = 0.2
N0_dBm_Hz = -174.0; B = 20e6
p_m = 1.0 / 5.0; n_users = 5

P_BS = 10 ** (P_BS_dBm / 10.0) * 1e-3
N0   = 10 ** (N0_dBm_Hz / 10.0) * 1e-3 * B

# ============================================================
# 2. 决策变量边界（对齐 MATLAB ga() 的 lb / ub）
# ============================================================
x_min, x_max = 0.2, 9.8     # xc
z_min, z_max = 0.2, 2.8     # zc
L_min, L_max = 0.1, 9.8     # Lx
W_min, W_max = 0.1, 2.8     # Lz (此处用 W 避免歧义)

lb = np.array([x_min, z_min, L_min, W_min])
ub = np.array([x_max, z_max, L_max, W_max])

# ============================================================
# 3. 构建确定性空间网格与权重（一次性，驻留 GPU）
# ============================================================
GRID_RES = 200
Z_FIXED  = 1.5

x_vals = torch.linspace(0, room_x, GRID_RES, device=DEVICE)
y_vals = torch.linspace(0, room_y, GRID_RES, device=DEVICE)
Xg, Yg = torch.meshgrid(x_vals, y_vals, indexing='ij')
grid_locs = torch.stack([
    Xg.flatten(),
    Yg.flatten(),
    torch.full_like(Xg.flatten(), Z_FIXED)
], dim=1)                        # shape: [40000, 3]
N_GRID = grid_locs.shape[0]

# 高斯热点权重：f_hr(r) = 0.7·Gaussian(μ=(5,5), σ=2.5) + 0.3·Uniform
hotspot_center = torch.tensor([room_x / 2, room_y / 2], device=DEVICE)
sigma_h = 2.5
dist_sq = ((grid_locs[:, 0] - hotspot_center[0]) ** 2 +
           (grid_locs[:, 1] - hotspot_center[1]) ** 2)

f_stationary = (1.0 / (2.0 * math.pi * sigma_h ** 2)) * \
               torch.exp(-dist_sq / (2.0 * sigma_h ** 2))
f_uniform = torch.full_like(f_stationary, 1.0 / (room_x * room_y))
grid_weights = 0.7 * f_stationary + 0.3 * f_uniform
grid_weights = grid_weights / grid_weights.sum()    # 归一化

# NLoS 路径参数（固定种子，确定性）
np.random.seed(42)
_nlos_psi = torch.tensor(2 * np.pi * np.random.rand(N_GRID),
                         dtype=torch.float32, device=DEVICE)
_nlos_tt  = torch.tensor(-np.pi + 2 * np.pi * np.random.rand(N_GRID),
                         dtype=torch.float32, device=DEVICE)
_nlos_eta = torch.tensor(10 ** ((-15 + 5 * np.random.rand(N_GRID)) / 10),
                         dtype=torch.float32, device=DEVICE)

print(f'Grid built: {N_GRID} points, weights range '
      f'[{grid_weights.min().item():.2e}, {grid_weights.max().item():.2e}]')

# ============================================================
# 4. 等效远场衍射信道模型（完整移植 MATLAB equivalent_farfield_channel_2）
# ============================================================
def equivalent_farfield_channel_pytorch(window_params, locs):
    """
    输入：
        window_params: Tensor[4] 或 Tensor[N_batch, 4]
        locs:          Tensor[N_grid, 3]  空间采样点
    输出：
        H_eq: Tensor[N_batch, N_grid, E]  复数信道系数
    """
    # ---- 形状处理：支持单窗口 或 批量窗口 ----
    single_input = (window_params.dim() == 1)
    if single_input:
        window_params = window_params.unsqueeze(0)   # [1, 4]

    xc = window_params[:, 0]; zc = window_params[:, 1]
    Lx = window_params[:, 2]; Lz = window_params[:, 3]
    Bn = window_params.shape[0]    # 批次大小
    xu = locs[:, 0]; yu = locs[:, 1]; zu = locs[:, 2]   # [N_grid]

    # ---- 基站 → 窗口中心 ----
    dx_BS = xc - x_BS
    dy_BS = torch.full_like(xc, 0.0 - y_BS)          # 显式张量化, 防 float→Tensor 类型错误
    dz_BS = zc - z_BS
    R_BW = torch.sqrt(dx_BS**2 + dy_BS**2 + dz_BS**2)           # [Bn]
    theta_BW = torch.atan2(dy_BS, dx_BS)
    phi_BW   = torch.acos(dz_BS / R_BW)
    k_tx = torch.sin(phi_BW) * torch.cos(theta_BW)              # [Bn]
    k_tz = torch.cos(phi_BW)                                    # [Bn]

    # ---- 窗口四角 ----
    x1 = xc - Lx/2; z1 = zc - Lz/2
    x2 = xc - Lx/2; z2 = zc + Lz/2
    x3 = xc + Lx/2; z3 = zc - Lz/2
    x4 = xc + Lx/2; z4 = zc + Lz/2

    def ray_dir(xs, zs):
        """基站 → 窗户角点的单位方向向量"""
        dx = xs.unsqueeze(1) - x_BS             # [Bn, N_grid]
        dy = torch.full_like(dx, 0.0 - y_BS)
        dz = zs.unsqueeze(1) - z_BS
        L  = torch.sqrt(dx**2 + dy**2 + dz**2)
        return dx/L, dy/L, dz/L

    ux1, _, uz1 = ray_dir(x1, z1); ux2, _, uz2 = ray_dir(x2, z2)
    ux3, _, uz3 = ray_dir(x3, z3); ux4, _, uz4 = ray_dir(x4, z4)

    # ---- 用户方向 ----
    dx_WU = xu - x_BS; dy_WU = yu - y_BS; dz_WU = zu - z_BS
    L_USER = torch.sqrt(dx_WU**2 + dy_WU**2 + dz_WU**2)        # [N_grid]
    ux_user = dx_WU / L_USER                                    # [N_grid]
    uz_user = dz_WU / L_USER

    # ---- 光照判断 (sigmoid 软化) ----
    ux_all = torch.stack([ux1, ux2, ux3, ux4], dim=0)           # [4, Bn, N_grid]
    uz_all = torch.stack([uz1, uz2, uz3, uz4], dim=0)
    ux_min = ux_all.min(dim=0).values                           # [Bn, N_grid]
    ux_max = ux_all.max(dim=0).values
    uz_min = uz_all.min(dim=0).values
    uz_max = uz_all.max(dim=0).values

    beta = 1000.0
    inx = (torch.sigmoid(beta * (ux_user - ux_min)) *
           torch.sigmoid(beta * (ux_max - ux_user)))
    inz = (torch.sigmoid(beta * (uz_user - uz_min)) *
           torch.sigmoid(beta * (uz_max - uz_user)))
    in_illumination = inx * inz                                  # [Bn, N_grid]

    # ---- 衍射角 ----
    dx_WU2 = xu - xc.unsqueeze(1); dy_WU2 = yu
    dz_WU2 = zu - zc.unsqueeze(1)
    R_WU = torch.sqrt(dx_WU2**2 + dy_WU2**2 + dz_WU2**2)       # [Bn, N_grid]
    t1 = dx_WU2 / R_WU; t2 = dz_WU2 / R_WU
    ax = (1.0 - in_illumination) * (k_tx.unsqueeze(1) - t1)
    az = (1.0 - in_illumination) * (k_tz.unsqueeze(1) - t2)
    sincx = torch.sinc((math.pi / lambda_val) * Lx.unsqueeze(1) * ax)
    sincz = torch.sinc((math.pi / lambda_val) * Lz.unsqueeze(1) * az)

    # ---- 天线阵列响应 ----
    n_ant = torch.arange(E, dtype=torch.float32, device=DEVICE)

    # 路径 1 (LoS)：散射角 = theta_BW
    ph1 = (2.0 * math.pi / lambda_val) * d_B * n_ant * torch.sin(theta_BW).unsqueeze(1)  # [Bn, E]
    a1  = (1.0 / math.sqrt(E)) * torch.complex(torch.cos(ph1), torch.sin(ph1))
    v1m = (lambda_val / (4.0 * math.pi)) / R_BW                                    # [Bn]
    v1p = -(2.0 * math.pi / lambda_val) * R_BW
    v1  = torch.complex(v1m * torch.cos(v1p), v1m * torch.sin(v1p))               # [Bn]
    H1  = v1.unsqueeze(1) * a1.conj()                                               # [Bn, E]

    # 路径 2 (NLoS)：每网格点独立随机散射
    ph2 = ((2.0 * math.pi / lambda_val) * d_B *
           n_ant.unsqueeze(0) * torch.sin(_nlos_tt).unsqueeze(1))                   # [N_grid, E]
    a2  = (1.0 / math.sqrt(E)) * torch.complex(torch.cos(ph2), torch.sin(ph2))
    v2m = _nlos_eta * (lambda_val / (4.0 * math.pi * d_ref))                       # [N_grid]
    v2  = torch.complex(v2m * torch.cos(_nlos_psi), v2m * torch.sin(_nlos_psi))
    H2  = v2.unsqueeze(1) * a2.conj()                                               # [N_grid, E]
    H2  = H2.unsqueeze(0)                                                            # [1, N_grid, E]

    H_total = math.sqrt(E / L1) * (H1.unsqueeze(1) + H2)                            # [Bn, N_grid, E]

    # ---- 窗口衍射因子 ----
    fm = (Lx.unsqueeze(1) * Lz.unsqueeze(1) * sincx * sincz) / (lambda_val * R_WU)  # [Bn, N_grid]
    fp = (-(2.0 * math.pi / lambda_val) * (k_tx * xc + k_tz * zc) - (math.pi / 2.0))  # [Bn]
    factor = torch.complex(fm * torch.cos(fp.unsqueeze(1)),
                           fm * torch.sin(fp.unsqueeze(1)))                          # [Bn, N_grid]

    H_eq = H_total * factor.unsqueeze(2)                                              # [Bn, N_grid, E]
    if single_input:
        H_eq = H_eq.squeeze(0)                                                       # [N_grid, E]
    return H_eq

# ============================================================
# 5. 批量评估函数：X_batch → [area, outage]
# ============================================================
@torch.no_grad()
def evaluate_batch(X_batch):
    """
    X_batch: np.ndarray, shape [B, 4]  — (xc, zc, Lx, Lz)
    返回:    np.ndarray, shape [B, 2]  — (area, outage)
    """
    theta = torch.tensor(X_batch, dtype=torch.float32, device=DEVICE)   # [B, 4]

    H_eq = equivalent_farfield_channel_pytorch(theta, grid_locs)         # [B, N_grid, E]
    H_w  = torch.sum(H_eq, dim=2) / math.sqrt(E)                        # [B, N_grid]

    dp   = (torch.abs(H_w) ** 2) * p_m * P_BS
    intf = (n_users - 1) * dp
    sinr = dp / (intf + N0)
    rate = torch.log2(1.0 + sinr)                                       # [B, N_grid]

    outage_bits = (rate < R_th).float()                                 # [B, N_grid]
    outage = torch.sum(outage_bits * grid_weights, dim=1)              # [B]

    area = theta[:, 2] * theta[:, 3]                                    # Lx * Lz, [B]

    return torch.stack([area, outage], dim=1).cpu().numpy()             # [B, 2]

# ============================================================
# 6. 拉丁超立方抽样 (LHS)
# ============================================================
from scipy.stats.qmc import LatinHypercube

print(f'\nGenerating {N_SAMPLES} LHS samples...')
sampler = LatinHypercube(d=4, seed=42)
X_unit = sampler.random(n=N_SAMPLES)                           # [N, 4] ∈ [0, 1]^4
X = lb + X_unit * (ub - lb)                                    # [N, 4]  逆归一化

# ============================================================
# 7. 分批评估并收集结果
# ============================================================
Y_list = []
n_batches = int(np.ceil(N_SAMPLES / BATCH_SIZE))

for i in range(n_batches):
    start = i * BATCH_SIZE
    end   = min((i + 1) * BATCH_SIZE, N_SAMPLES)
    X_batch = X[start:end]

    Y_batch = evaluate_batch(X_batch)
    Y_list.append(Y_batch)
    torch.cuda.empty_cache()  # 每批后释放 GPU 中间张量

    if (i + 1) % 10 == 0 or i == n_batches - 1:
        # 简单进度提示：当前批次的面积和 outage 范围
        a_min, a_max = Y_batch[:, 0].min(), Y_batch[:, 0].max()
        o_min, o_max = Y_batch[:, 1].min(), Y_batch[:, 1].max()
        print(f'  batch {i+1:4d}/{n_batches} | '
              f'area [{a_min:.3f}, {a_max:.3f}] | '
              f'outage [{o_min*100:.1f}%, {o_max*100:.1f}%]')

Y = np.concatenate(Y_list, axis=0)                              # [N, 2]

# ============================================================
# 8. 数据质量统计
# ============================================================
print(f'\n{"="*60}')
print(f'Data collection complete.')
print(f'  X shape: {X.shape}  (N_samples=4 features)')
print(f'  Y shape: {Y.shape}  (area, grid_outage)')
print(f'  Area     range: [{Y[:, 0].min():.4f}, {Y[:, 0].max():.4f}] m²')
print(f'  Outage   range: [{Y[:, 1].min()*100:.2f}%, {Y[:, 1].max()*100:.2f}%]')
print(f'  Feasible (<10% outage): {(Y[:, 1] <= 0.10).sum()} / {N_SAMPLES} samples')

# ============================================================
# 9. 结构化落盘
# ============================================================

# --- 9a. CSV (人类可读) ---
import pandas as pd
df = pd.DataFrame(
    np.concatenate([X, Y], axis=1),
    columns=['xc', 'zc', 'Lx', 'Lz', 'area', 'grid_outage']
)
df.to_csv(OUT_CSV, index=False)
print(f'\nCSV saved: {OUT_CSV}  ({len(df)} rows × {len(df.columns)} cols)')

# --- 9b. PyTorch .pt (直接加载) ---
X_tensor = torch.tensor(X, dtype=torch.float32)
Y_tensor = torch.tensor(Y, dtype=torch.float32)
torch.save({'X': X_tensor, 'Y': Y_tensor,
            'bounds': {'lb': lb, 'ub': ub},
            'description': 'EM window LHS dataset: X=[xc,zc,Lx,Lz], Y=[area,grid_outage]'},
           OUT_PT)
print(f'PT  saved: {OUT_PT}   (keys: X, Y, bounds, description)')

# ============================================================
# 10. 快速自检：加载 .pt 并打印前 5 条样例
# ============================================================
loaded = torch.load(OUT_PT, weights_only=False)  # PyTorch 2.6+ 需显式关闭
print(f'\nSelf-check — first 5 samples from .pt file:')
for i in range(min(5, N_SAMPLES)):
    xc, zc, Lx, Lz = loaded['X'][i].tolist()
    area, outage   = loaded['Y'][i].tolist()
    print(f'  [{xc:.2f}, {zc:.2f}, {Lx:.2f}, {Lz:.2f}]  →  '
          f'area={area:.4f} m²,  outage={outage*100:.2f}%')

print(f'\nDone. Ready for surrogate model training.')
