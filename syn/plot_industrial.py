#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plot_industrial.py -- 工业可行性图表 (GPU 能耗 / 数据中心面积 / 商用吞吐)
实测锚点: SKY130HD (Yosys+ABC amap, 18ch array 0.69mm²/26.4MHz/128.29mW)
5nm 投影口径 (全部标注 projected): 面积/100, 频率 x38 (26.4MHz->1GHz 保守),
功率 = CV²f 全缩放: 128.29mW x 38/660 = 7.4mW/array @1GHz 持续; 门控平均 <2mW.
GPU 公开规格: H100 SXM 700W / FP64 67 TFLOPS (33.5 TMAC/s 64b) / die 814mm²;
B200 1000W; GB200 NVL72 机架 120kW; reticle 858mm².
精确 limb 仿真成本: 527b->9-limb (x243 64b-MAC), 705b->11-limb (x300), 753b->x320.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["WenQuanYi Zen Hei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
import numpy as np

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(W, "download", "repo", "figures")
os.makedirs(FIG, exist_ok=True)

C_RNS, C_GPU, C_GPUX, C_TH = "#d62728", "#1f77b4", "#7f7f7f", "#2ca02c"

# ---------- 模型参数 (MAC/token = 2*params) ----------
models = ["7B\n(527b,19ch)", "600B\n(705b,26ch)", "2T\n(753b,27ch)"]
macs = {"7B": 14e9, "600B": 1.2e12, "2T": 4e12}
limb = {"7B": 243, "600B": 300, "2T": 320}

# EIU 集群配置 (5nm 投影, 1GHz 持续, 7.4mW/array, 0.0069-0.0104mm²/array)
cfg = {"7B":  (1000, 0.0069), "600B": (10000, 0.0100), "2T": (40000, 0.0104)}
eiu_toks, eiu_area, eiu_pwr, eiu_eng = [], [], [], []
for m in ["7B", "600B", "2T"]:
    n, a = cfg[m]
    macs_s = n * 1e9                      # @1GHz
    eiu_toks.append(macs[m] / macs_s)     # tok/s
    eiu_area.append(n * a)                # mm²
    eiu_pwr.append(n * 7.4e-3)            # W
    eiu_eng.append(n * 7.4e-3 / (macs[m] / macs_s))  # J/token

# GPU 精确 limb 仿真 @H100 (700W, 33.5 TMAC/s 64b)
gpu_toks, gpu_eng = [], []
for m in ["7B", "600B", "2T"]:
    t = macs[m] * limb[m] / 3.35e13       # s/token
    gpu_toks.append(1 / t)
    gpu_eng.append(700 * t)
bf16_eng = 0.35  # J/token 7B 单流参照 (700W/2000tok/s)

x = np.arange(3); w = 0.27

fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.4))

# ---- P1: 能耗/token ----
ax = axes[0]
ax.bar(x - w, eiu_eng, w, color=C_RNS, label="EIU exact (5nm proj, 1GHz)")
ax.bar(x, gpu_eng, w, color=C_GPU, label="H100 exact (FP64 limb 仿真)")
ax.bar(x[:1] + w, [bf16_eng], w, color=C_GPUX, label="H100 BF16 不精确参照")
for i, v in enumerate(eiu_eng):
    ax.annotate(f"{v:.2f}J", (i - w, v), xytext=(0, 4), ha="center",
                fontsize=8, color=C_RNS, textcoords="offset points")
for i, v in enumerate(gpu_eng):
    ax.annotate(f"{v:,.0f}J", (i, v), xytext=(0, 4), ha="center",
                fontsize=8, color=C_GPU, textcoords="offset points")
ax.axhline(bf16_eng, color=C_GPUX, ls=":", lw=1)
ax.set_yscale("log"); ax.set_xticks(x); ax.set_xticklabels(models)
ax.set_ylabel("每 token 能耗 (J, log)", fontsize=11)
ax.set_title("能耗对比: EIU 精确 vs GPU 精确仿真 (680-845× 优势)", fontsize=11)
ax.legend(fontsize=8); ax.grid(alpha=0.3, axis="y")

# ---- P2: 面积 ----
ax = axes[1]
ax.bar(x, eiu_area, 0.5, color=C_RNS, label="EIU 集群 (5nm proj)")
for i, v in enumerate(eiu_area):
    ax.annotate(f"{v:.1f}mm²", (i, v), xytext=(0, 4), ha="center",
                fontsize=9, color=C_RNS, textcoords="offset points")
ax.axhline(814, color=C_GPU, ls="--", lw=1.5)
ax.axhline(858, color="k", ls=":", lw=1.5)
ax.annotate("H100 die 814mm²", (2.35, 814), fontsize=8.5, color=C_GPU, va="bottom")
ax.annotate("reticle 858mm²", (2.35, 858), fontsize=8.5, va="top")
ax.set_yscale("log"); ax.set_xticks(x); ax.set_xticklabels(models)
ax.set_ylabel("芯片面积 (mm², log)", fontsize=11)
ax.set_ylim(1, 2000)
ax.set_title("面积: 7B 全集群 = 0.85% 单颗 H100 die", fontsize=11)
ax.legend(fontsize=8.5); ax.grid(alpha=0.3, axis="y")

# ---- P3: 吞吐 ----
ax = axes[2]
ax.bar(x - w/2, eiu_toks, w, color=C_RNS, label="EIU exact (tok/s)")
ax.bar(x + w/2, gpu_toks, w, color=C_GPU, label="H100 exact (tok/s)")
for i, v in enumerate(eiu_toks):
    ax.annotate(f"{v:.0f}", (i - w/2, v), xytext=(0, 4), ha="center",
                fontsize=9, color=C_RNS, textcoords="offset points")
for i, v in enumerate(gpu_toks):
    ax.annotate(f"{v:.2f}", (i + w/2, v), xytext=(0, 4), ha="center",
                fontsize=9, color=C_GPU, textcoords="offset points")
ax.axhline(20, color=C_TH, ls="--", lw=1.5)
ax.annotate("交互式门槛 20 tok/s", (0.02, 21), fontsize=8.5, color=C_TH)
ax.axhline(8, color=C_TH, ls=":", lw=1.2)
ax.annotate("可读流式 8 tok/s", (0.02, 8.5), fontsize=8.5, color=C_TH)
ax.set_yscale("log"); ax.set_xticks(x); ax.set_xticklabels(models)
ax.set_ylabel("精确推理吞吐 (token/s, log)", fontsize=11)
ax.set_title("商用吞吐: 7B 交互级 71 tok/s / 600B 流式 8.3 / 2T 10", fontsize=11)
ax.legend(fontsize=8.5); ax.grid(alpha=0.3, axis="y")

fig.suptitle("Halo EIU-RNS 工业可行性: 实测 SKY130HD 锚点 + 5nm 投影 (面积/100, f x38, CV²f 全缩放, 7.4mW/array@1GHz)",
             fontsize=12.5, y=1.04)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "industrial_feasibility.png"), dpi=200, bbox_inches="tight")
print("wrote industrial_feasibility.png")

# ---------- resource_rns_scaling_1: 实测面积 vs 通道数 ----------
fig, ax = plt.subplots(figsize=(6.5, 4.8))
pts_x = [1, 8, 18]
pts_a = [41891/1e4, 317810/1e4, 691601/1e4]   # mm² @130nm 实测
ax.plot(pts_x, pts_a, "o-", color=C_RNS, ms=9, lw=2, label="实测 (SKY130HD)")
xx = np.array([8, 18, 26, 35, 54, 91])
a_lin = 317810/1e4 * xx / 8
ax.plot(xx, a_lin, "s--", color=C_RNS, alpha=0.45, label="线性外推 (通道解耦)")
for xi, yi in zip(pts_x, pts_a):
    ax.annotate(f"{yi:.2f}mm²", (xi, yi), xytext=(6, 4), fontsize=8.5,
                textcoords="offset points")
for xi, lab in [(26, "600B"), (35, "1024b"), (54, "1000T"), (91, "4096b")]:
    i = list(xx).index(xi)
    ax.annotate(lab, (xi, a_lin[i]), fontsize=8, xytext=(4, -12),
                textcoords="offset points", color="#555")
ax.set_xlabel("RNS 通道数 (k)", fontsize=11)
ax.set_ylabel("面积 @130nm (mm²)", fontsize=11)
ax.set_title("面积线性扩展: 实测 1/8/18ch 锚点, 18ch=外推 96.7%", fontsize=11)
ax.legend(fontsize=9); ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "resource_rns_scaling_1.png"), dpi=200, bbox_inches="tight")
print("wrote resource_rns_scaling_1.png")

# ---------- resource_rns_scaling_1_1: 功耗 vs 通道数 ----------
fig, ax = plt.subplots(figsize=(6.5, 4.8))
pts_p = [9.845, 71.465, 128.29]   # mW @α=0.10 实测
ax.plot(pts_x, pts_p, "o-", color=C_RNS, ms=9, lw=2, label="实测功耗 (α=0.10, @实测Fmax)")
xx2 = np.array([8, 18, 26, 35, 54, 91])
p_lin = 71.465 * xx2 / 8
ax.plot(xx2, p_lin, "s--", color=C_RNS, alpha=0.45, label="线性外推")
for xi, yi in zip(pts_x, pts_p):
    ax.annotate(f"{yi:.1f}mW", (xi, yi), xytext=(6, 4), fontsize=8.5,
                textcoords="offset points")
ax.set_xlabel("RNS 通道数 (k)", fontsize=11)
ax.set_ylabel("功耗 @130nm (mW, α=0.10)", fontsize=11)
ax.set_title("功耗线性扩展: 细粒度门控下按需线性伸缩", fontsize=11)
ax.legend(fontsize=9); ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "resource_rns_scaling_1_1.png"), dpi=200, bbox_inches="tight")
print("wrote resource_rns_scaling_1_1.png")

# ---------- resource_rns_scaling_2: 吞吐 vs 模型规模 (对数) ----------
fig, ax = plt.subplots(figsize=(6.5, 4.8))
sizes = [7, 600, 2000, 1000000]
eiu_r = [71.4, 8.3, 10.0, 0.02]
gpu_r = [9.8, 0.093, 0.028, None]
ax.plot(sizes[:3], eiu_r[:3], "o-", color=C_RNS, ms=10, lw=2.2,
        label="EIU 集群 (5nm proj): 7B=1k, 600B=10k, 2T=40k 阵列")
ax.plot(sizes[:3], gpu_r[:3], "s--", color=C_GPU, ms=10, lw=2.2,
        label="H100 精确仿真 (FP64 limb)")
ax.plot([1000000], [0.02], "^", color=C_RNS, ms=11, alpha=0.6)
ax.annotate("1000T: wafer-scale 离线", (1000000, 0.02), fontsize=8.5,
            xytext=(-95, 14), textcoords="offset points", color="#555")
ax.axhline(20, color=C_TH, ls="--", lw=1.5); ax.annotate("交互式 20 tok/s", (1.2, 23), fontsize=8.5, color=C_TH)
ax.axhline(8, color=C_TH, ls=":", lw=1.2); ax.annotate("可读流式 8 tok/s", (1.2, 9), fontsize=8.5, color=C_TH)
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("模型规模 (params)", fontsize=11)
ax.set_ylabel("精确推理吞吐 (token/s)", fontsize=11)
ax.set_title("精确吞吐 vs 模型规模: GPU 精确模式全线不可商用", fontsize=11)
ax.legend(fontsize=8.5, loc="lower left"); ax.grid(alpha=0.3, which="both")
fig.tight_layout()
fig.savefig(os.path.join(FIG, "resource_rns_scaling_2.png"), dpi=200, bbox_inches="tight")
print("wrote resource_rns_scaling_2.png")
