#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plot_ppa_rns.py -- RNS-EIU vs Naive vs FP-FMA PPA 对比 (SKY130HD)
数据: results/ppa.json (实测 + 线性外推, 方法字段区分)
基线: FMA32/64 为先前会话同 liberty 同 abc 流程实测
输出: figures/rns_scaling_ppa.png (200 dpi)
"""
import json, os, csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(W, "download", "eiu_rns_ppa", "results")
FIG = os.path.join(W, "download", "eiu_rns_ppa", "figures")
os.makedirs(FIG, exist_ok=True)
PPA = json.load(open(os.path.join(RES, "ppa.json")))
M = lambda k: PPA[k]

fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))

# ---------------- F1: Fmax vs 累加位宽 ----------------
ax = axes[0]
x_rns = [512, 1024, 4096]
y_rns = [M("array8_512")["fmax_mhz"], M("array8_1024")["fmax_mhz"], M("array8_4096")["fmax_mhz"]]
ax.plot(x_rns, y_rns, "o-", color="#d62728", lw=2, ms=9,
        label="RNS-EIU MAC (8ch 实测锚点; 全阵列同频/线性)")
y_nv = [M("naive512")["fmax_mhz"], M("naive1024")["fmax_mhz"], M("naive4096")["fmax_mhz"]]
ax.plot(x_rns, y_nv, "s--", color="#1f77b4", lw=2, ms=9,
        label="Naive 补码 MAC (进位链, 实测)")
ax.plot([1024], [M("fma32")["fmax_mhz"]], "^", color="#2ca02c", ms=10,
        label="FP32 FMA (40b mantissa 级, 先前实测)")
ax.plot([1024], [M("fma64")["fmax_mhz"]], "v", color="#9467bd", ms=10,
        label="FP64 FMA (先前实测)")
ax.annotate(f"{y_rns[0]:.1f} MHz", (1024, y_rns[0]), textcoords="offset points",
            xytext=(10, 8), fontsize=9, color="#d62728")
ax.annotate(f"{y_rns[1]:.1f} MHz", (4096, y_rns[1]), textcoords="offset points",
            xytext=(-50, 8), fontsize=9, color="#d62728")
ax.annotate(f"{y_nv[0]:.1f} MHz", (1024, y_nv[0]), textcoords="offset points",
            xytext=(10, -14), fontsize=9, color="#1f77b4")
ax.annotate(f"{y_nv[1]:.2f} MHz", (4096, y_nv[1]), textcoords="offset points",
            xytext=(-60, 8), fontsize=9, color="#1f77b4")
ax.set_xlabel("累加动态范围 (bit)", fontsize=11)
ax.set_ylabel("Fmax (MHz)  [SKY130HD tt 0.25C 1.80V, Yosys+ABC amap]", fontsize=10)
ax.set_title("Fmax 与位宽解耦: RNS 22.5MHz vs naive 1.7MHz @4096b (13x)", fontsize=11)
ax.set_xscale("log", base=2); ax.set_yscale("log", base=10)
ax.set_xticks([512, 1024, 4096]); ax.set_xticklabels(["512", "1024", "4096"])
ax.legend(loc="lower left", fontsize=8.5)
ax.grid(alpha=0.3, which="both")

# ---------------- F2: 面积 vs 位宽 ----------------
ax = axes[1]
x_ar = [512, 1024, 4096]
a_rns = [M("array18_512")["area_um2"]/1e3, M("array35_1024")["area_um2"]/1e3, M("array91_4096")["area_um2"]/1e3]
ax.plot(x_ar, a_rns, "o-", color="#d62728", lw=2, ms=9,
        label="RNS-EIU 35/91ch 全阵列 (8ch 锚点线性外推)")
a_nv = [M("naive512")["area_um2"]/1e3, M("naive1024")["area_um2"]/1e3, M("naive4096")["area_um2"]/1e3]
ax.plot(x_ar, a_nv, "s--", color="#1f77b4", lw=2, ms=9,
        label="Naive MAC (实测)")
ax.plot([1024], [M("fma32")["area_um2"]/1e3], "^", color="#2ca02c", ms=10,
        label="FP32 FMA (先前实测)")
ax.plot([1024], [M("fma64")["area_um2"]/1e3], "v", color="#9467bd", ms=10,
        label="FP64 FMA (先前实测)")
for x, y, c, txt in [(1024, a_rns[0], "#d62728", f"{a_rns[0]:.0f}k µm²"),
                     (4096, a_rns[1], "#d62728", f"{a_rns[1]:.0f}k µm²"),
                     (1024, a_nv[0], "#1f77b4", f"{a_nv[0]:.0f}k"),
                     (4096, a_nv[1], "#1f77b4", f"{a_nv[1]:.0f}k")]:
    ax.annotate(txt, (x, y), textcoords="offset points", xytext=(8, 6),
                fontsize=9, color=c)
ax.set_xlabel("累加动态范围 (bit)", fontsize=11)
ax.set_ylabel("芯片面积 (10³ µm²)", fontsize=11)
ax.set_title("面积代价: 18/35/91 独立乘法通道 (4096b: 10.0mm² vs 0.26mm²)", fontsize=11)
ax.set_xscale("log", base=2)
ax.set_xticks([512, 1024, 4096]); ax.set_xticklabels(["512", "1024", "4096"])
ax.legend(loc="upper left", fontsize=8.5)
ax.grid(alpha=0.3, which="both")

fig.suptitle("RNS-EIU vs 基线: SKY130HD 逻辑综合 PPA "
             "(1024b/4096b 精确整数 MAC, Yosys 0.69 + ABC amap, 全部端到端仿真验证通过)",
             fontsize=12, y=1.03)
fig.tight_layout()
out = os.path.join(FIG, "rns_scaling_ppa.png")
fig.savefig(out, dpi=200, bbox_inches="tight")
print("wrote", out)
