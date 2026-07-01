# =====================================================================
# train_surrogate.py — 代理模型训练脚本
# 输入:  em_window_dataset.csv  (LHS 10k samples)
# 输出:  surrogate_model.pt    (可直接替换 compute_grid_outage)
#
# 设计决策:
#   - 仅预测 outage（area = Lx*Lz 是精确公式，不用学）
#   - 残差 MLP + 可行域加权损失
#   - 80/20 train/val 划分
# =====================================================================

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from torch.utils.data import DataLoader, TensorDataset
import os

# ============================================================
# 0. 配置
# ============================================================
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
BATCH   = 256
EPOCHS  = 300
LR      = 1e-3
DATA_DIR = '/kaggle/input/datasets/gxc4real/em-window-dataset'

print(f'Device: {DEVICE}')
print(f'Epochs: {EPOCHS}, Batch: {BATCH}, LR: {LR}')

# ============================================================
# 1. 加载数据 & 预处理
# ============================================================
df = pd.read_csv(os.path.join(DATA_DIR, 'em_window_dataset.csv'))
X_raw = df[['xc','zc','Lx','Lz']].values.astype(np.float32)   # [N, 4]
Y_raw = df[['grid_outage']].values.astype(np.float32)           # [N, 1]

# 变量边界（与采样时一致，用于归一化）
lb = np.array([0.2, 0.2, 0.1, 0.1], dtype=np.float32)
ub = np.array([9.8, 2.8, 9.8, 2.8], dtype=np.float32)

# Min-Max 归一化到 [0, 1]
X_norm = (X_raw - lb) / (ub - lb)
Y_norm = Y_raw   # outage 本身在 [0, 1]，不需要额外归一化

# Train / Val 划分 (80/20, 时序无关 → 随机)
N = len(X_norm)
idx = np.random.permutation(N)
split = int(N * 0.8)
train_idx, val_idx = idx[:split], idx[split:]

X_train, Y_train = X_norm[train_idx], Y_norm[train_idx]
X_val,   Y_val   = X_norm[val_idx],   Y_norm[val_idx]

print(f'Train: {len(X_train)}, Val: {len(X_val)}')

# DataLoader
train_loader = DataLoader(TensorDataset(
    torch.tensor(X_train), torch.tensor(Y_train)), batch_size=BATCH, shuffle=True)
val_loader = DataLoader(TensorDataset(
    torch.tensor(X_val), torch.tensor(Y_val)), batch_size=BATCH)

# ============================================================
# 2. 模型定义 — 残差 MLP
# ============================================================
class ResidualMLP(nn.Module):
    def __init__(self, in_dim=4, hidden=256, n_layers=4, dropout=0.05):
        super().__init__()
        self.input_layer = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.ReLU(),
            nn.BatchNorm1d(hidden)
        )
        self.blocks = nn.ModuleList()
        for _ in range(n_layers):
            self.blocks.append(nn.Sequential(
                nn.Linear(hidden, hidden),
                nn.ReLU(),
                nn.BatchNorm1d(hidden),
                nn.Dropout(dropout)
            ))
        self.output_layer = nn.Linear(hidden, 1)

    def forward(self, x):
        h = self.input_layer(x)
        for block in self.blocks:
            h = h + block(h)   # Skip connection: residual
        return torch.sigmoid(self.output_layer(h))  # 输出钳制在 [0,1]

model = ResidualMLP().to(DEVICE)
print(f'Model: {sum(p.numel() for p in model.parameters()):,} parameters')

# ============================================================
# 3. 损失函数 — 可行域加权 MSE
# ============================================================
def weighted_mse(pred, target, weight_feasible=3.0):
    """
    对 outage <= 10% 的样本给予更高权重，
    逼迫模型在可行域边界上学得更准
    """
    base_loss = (pred - target) ** 2
    is_feasible = (target < 0.10).float()
    weights = 1.0 + (weight_feasible - 1.0) * is_feasible
    return (base_loss * weights).mean()

# ============================================================
# 4. 训练循环
# ============================================================
optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-5)
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

train_losses, val_losses = [], []
best_val_loss = float('inf')

print('\nTraining...')
for epoch in range(EPOCHS):
    # --- Train ---
    model.train()
    train_loss = 0.0
    for xb, yb in train_loader:
        xb, yb = xb.to(DEVICE), yb.to(DEVICE)
        optimizer.zero_grad()
        pred = model(xb)
        loss = weighted_mse(pred, yb)
        loss.backward()
        optimizer.step()
        train_loss += loss.item() * len(xb)
    train_loss /= len(train_loader.dataset)
    train_losses.append(train_loss)
    scheduler.step()

    # --- Val ---
    model.eval()
    val_loss = 0.0
    with torch.no_grad():
        for xb, yb in val_loader:
            xb, yb = xb.to(DEVICE), yb.to(DEVICE)
            pred = model(xb)
            loss = weighted_mse(pred, yb)
            val_loss += loss.item() * len(xb)
    val_loss /= len(val_loader.dataset)
    val_losses.append(val_loss)

    if val_loss < best_val_loss:
        best_val_loss = val_loss
        torch.save(model.state_dict(), 'best_model.pt')

    if (epoch+1) % 30 == 0:
        print(f'  epoch {epoch+1:3d}/{EPOCHS} | '
              f'train_loss={train_loss:.6f} | val_loss={val_loss:.6f} | lr={scheduler.get_last_lr()[0]:.2e}')

# Load best checkpoint
model.load_state_dict(torch.load('best_model.pt'))

# ============================================================
# 5. 评估指标
# ============================================================
model.eval()
X_val_t = torch.tensor(X_val).to(DEVICE)
Y_val_t = torch.tensor(Y_val).to(DEVICE)
with torch.no_grad():
    Y_pred = model(X_val_t).cpu().numpy().flatten()
Y_true = Y_val.flatten()

# R²
ss_res = ((Y_true - Y_pred) ** 2).sum()
ss_tot = ((Y_true - Y_true.mean()) ** 2).sum()
r2 = 1 - ss_res / ss_tot

# MAE
mae = np.abs(Y_true - Y_pred).mean()

# 可行域分类准确率
true_feas = Y_true < 0.10
pred_feas = Y_pred < 0.10
feas_acc = (true_feas == pred_feas).mean()

# 可行域召回率与精确率
recall = (true_feas & pred_feas).sum() / max(true_feas.sum(), 1)
precision = (true_feas & pred_feas).sum() / max(pred_feas.sum(), 1)

print(f'\n{"="*60}')
print(f'Validation Metrics')
print(f'{"="*60}')
print(f'  R² Score:           {r2:.4f}')
print(f'  MAE:                {mae*100:.2f}% outage')
print(f'  Feasible Accuracy:  {feas_acc*100:.1f}%')
print(f'  Feasible Recall:    {recall*100:.1f}%')
print(f'  Feasible Precision: {precision*100:.1f}%')
print(f'  Best Val Loss:      {best_val_loss:.6f}')

# ============================================================
# 6. 保存完整模型（含归一化参数）
# ============================================================
torch.save({
    'model_state': model.state_dict(),
    'lb': torch.tensor(lb),
    'ub': torch.tensor(ub),
    'r2': r2,
    'mae': mae,
    'model_class': 'ResidualMLP',
    'usage': 'outage = model(x_norm); x_norm = (x_raw - lb)/(ub - lb)'
}, 'surrogate_model.pt')
print(f'\nModel saved: surrogate_model.pt')

# ============================================================
# 7. 可视化
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))

# Loss curve
ax = axes[0]
ax.plot(train_losses, 'b-', alpha=0.6, label='Train')
ax.plot(val_losses, 'r-', label='Val')
ax.set_xlabel('Epoch'); ax.set_ylabel('Weighted MSE')
ax.set_title('Loss Curve'); ax.legend(); ax.grid(True, alpha=0.3)

# Predicted vs True
ax = axes[1]
ax.scatter(Y_true*100, Y_pred*100, c='steelblue', s=3, alpha=0.4)
ax.plot([0,100], [0,100], 'r--', linewidth=1)
ax.axhline(y=10, color='gray', linestyle=':', alpha=0.5)
ax.axvline(x=10, color='gray', linestyle=':', alpha=0.5)
ax.set_xlabel('True Outage [%]'); ax.set_ylabel('Predicted Outage [%]')
ax.set_title(f'Pred vs True  (R²={r2:.3f}, MAE={mae*100:.2f}%)')
ax.grid(True, alpha=0.3)

# Error distribution
ax = axes[2]
errors = (Y_pred - Y_true) * 100
ax.hist(errors, bins=80, color='steelblue', alpha=0.7, edgecolor='white')
ax.axvline(x=0, color='red', linestyle='--', linewidth=1)
ax.set_xlabel('Prediction Error [% outage]')
ax.set_ylabel('Count')
ax.set_title(f'Error Distribution  (σ={errors.std():.2f}%)')
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('training_diagnostics.png', dpi=120)
plt.show()
print('Plot saved: training_diagnostics.png')
