#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""estimate_power.py -- SKY130HD 功耗估算 (liberty 解析 + blif cell 直方图)
方法 (无 SAIF, 工程估算口径, 全部假设显式标注):
  P_leak = Σ n_i * leak_i                     [W, liberty cell_leakage_power, 精确]
  P_switch = α * f * V² * Σ n_i * C_pin_i     [线/pin 电容翻转, liberty pin capacitance]
  P_int    = α * f * Σ n_i * E_int_i          [单元内部能量, liberty internal_power 表全体均值]
假设: V=1.80V (tt_025C_1v80), 翻转率 α 两档 0.10 / 0.25 (无 SAIF 工程惯例),
     时钟频率取各设计实测 Fmax; 输入假设 0 翻转 (仅内部翻转贡献).
输出: results/power_table.csv + ppa.json 附加 power 字段
"""
import re, os, csv, json, glob
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.environ.get("SKY130_LIB", os.path.join(ROOT, "syn", "sky.lib"))
NET = os.path.join(ROOT, "syn", "netlists")
SYN = os.path.join(ROOT, "tmp", "syn")
OUT = os.path.join(ROOT, "results")
PPA_JSON = os.path.join(OUT, "ppa.json")

V = 1.80
ALPHAS = (0.10, 0.25)

# ---------------- design metadata: fmax + blif file ----------------
DESIGNS = {
    "ch32c0":     "ch32c1.blif",   # fallback overwritten below
    "ch31c1":     "ch31c1.blif",
    "ch36c1":     "ch36c1_map.blif",
    "ch33c3":     "ch33c3.blif",
    "ch30c5":     "ch30c5.blif",
    "naive512":   "naive512.blif",
    "naive1024":  "naive1024.blif",
    "naive4096":  "naive4096.blif",
    "array8_1024":   "array8_1024.blif",
    "array8_512":    "array8_512.blif",
    "array18_512":   "array18_512.blif",
    "array8_4096":   "array8_4096.blif",
    "mrc_1024":      "mrc_1024.blif",
    "mrc_512":       "mrc_512.blif",
}

# ---------------- 1) liberty parsing ----------------
def parse_liberty(path):
    """粗粒度 regex 解析: 每个特征化 cell 的
       - cell_leakage_power (W)
       - 每输入/输出 pin 的 capacitance (pF)
       - internal_power values 均值 (rise/fall 能量表全体平均, 单位表内未定标 -> 由
         liberty 规范: energy = power * time, SKY130 表为功率×向量时间 => 转换: 表值
         即 energy per switching event, 内部一致性足够 (估算口径)"""
    lib = {}
    t = open(path, errors="ignore").read()
    # 按 cell 块切分
    cell_iter = re.finditer(r'\bcell\s*\(\s*"?([A-Za-z0-9_]+)"?\s*\)\s*\{', t)
    starts = [(m.start(), m.group(1)) for m in cell_iter]
    n = len(starts)
    for i, (pos, name) in enumerate(starts):
        end = starts[i+1][0] if i+1 < n else len(t)
        blk = t[pos:end]
        # 跳过物理/接口 cell
        if "__fill" in name or "__decap" in name or "__tap" in name or \
           "__diode" in name or "__lpflow" in name:
            continue
        m = re.search(r'cell_leakage_power\s*:\s*([\d.eE+-]+)\s*;', blk)
        # liberty 头: leakage_power_unit = "1nW" -> 转 W
        leak = (float(m.group(1)) * 1e-9) if m else 0.0
        # pin 电容 (pF), capacitive_load_unit(1, "pf"); 含全部 capacitance 字段
        # (输入/输出/rise/fall) -> 保守上界口径
        caps = [float(x) for x in
                re.findall(r'capacitance\s*:\s*([\d.]+)\s*;', blk)]
        C_pin = sum(caps)  # 单元全部 pin 电容之和 (pF)
        # internal_power 表值全体均值; 单位 = V*mA*ns = pJ (energy per switch)
        vals = []
        for vm in re.finditer(r'values\s*\(\s*"(.*?)"\s*\)\s*;', blk):
            for num in re.findall(r'-?[\d.]+(?:[eE]-?\d+)?', vm.group(1)):
                vals.append(float(num))
        e_int = (sum(vals)/len(vals)) if vals else 0.0
        lib[name] = {"leak": leak, "C_pin_pF": C_pin, "e_int_raw": e_int,
                     "n_tables": len(vals)}
    return lib

# SKY130HD: voltage_unit=1V, current_unit=1mA, time_unit=1ns
# => internal_power 表 values 单位 = V*mA*ns = pJ (能量/次翻转)
E_SCALE = 1e-12  # pJ -> J

def main():
    print("parsing liberty (12MB) ...")
    lib = parse_liberty(LIB)
    print(f"  {len(lib)} characterized cells")
    # sanity: nand2_1
    n2 = lib.get("sky130_fd_sc_hd__nand2_1", {})
    print(f"  nand2_1: leak={n2.get('leak')}, C_pin={n2.get('C_pin_pF')}pF, "
          f"tables={n2.get('n_tables')}")

    ppa = json.load(open(PPA_JSON))
    rows = []
    for name, blif in sorted(DESIGNS.items()):
        p = os.path.join(NET, blif)
        if not os.path.exists(p):
            # 尝试同名
            p2 = os.path.join(NET, name + ".blif")
            if os.path.exists(p2):
                p = p2
            else:
                continue
        hist = Counter()
        for m in re.finditer(r'^(?:\.gate|\.subckt)\s+([A-Za-z0-9_]+)', open(p, errors="ignore").read(), re.M):
            hist[m.group(1)] += 1
        # .subckt 同样计入
        total_cells = sum(hist.values())
        if total_cells == 0:
            continue
        leak = 0.0; Ctot = 0.0; Etot = 0.0
        for cellname, n in hist.items():
            c = lib.get(cellname)
            if c is None:
                continue
            leak += n * c["leak"]
            Ctot += n * c["C_pin_pF"]
            Etot += n * c["e_int_raw"] * E_SCALE
        fmax = ppa.get(name, {}).get("fmax_mhz")
        if not fmax:
            # 从日志兜底
            d = re.findall(r"Delay\s*=\s*([\d.]+) ps",
                           open(os.path.join(SYN, name + ".log"), errors="ignore").read()) \
                if os.path.exists(os.path.join(SYN, name + ".log")) else []
            if not d:
                continue
            fmax = 1e6/float(d[-1])
        f = fmax * 1e6
        res = {"design": name, "cells": total_cells,
               "fmax_mhz": round(fmax, 2),
               "p_leak_w": leak}
        for a in ALPHAS:
            p_sw = a * f * V*V * Ctot * 1e-12
            p_in = a * f * Etot
            res[f"p_dyn_a{int(a*100)}_w"] = p_sw + p_in
            res[f"p_sw_a{int(a*100)}_w"] = p_sw
            res[f"p_int_a{int(a*100)}_w"] = p_in
        res["p_tot_a10_w"] = leak + res["p_dyn_a10_w"]
        res["p_tot_a25_w"] = leak + res["p_dyn_a25_w"]
        rows.append(res)
        print(f"  {name:14s} cells={total_cells:>7} leak={leak*1e6:8.2f}uW "
              f"Ptot(a.10)={res['p_tot_a10_w']*1e3:9.3f}mW "
              f"Ptot(a.25)={res['p_tot_a25_w']*1e3:9.3f}mW @{fmax:.1f}MHz")

    # CSV
    cols = ["design", "cells", "fmax_mhz", "p_leak_w",
            "p_sw_a10_w", "p_int_a10_w", "p_dyn_a10_w", "p_tot_a10_w",
            "p_sw_a25_w", "p_int_a25_w", "p_dyn_a25_w", "p_tot_a25_w"]
    with open(os.path.join(OUT, "power_table.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=cols); wr.writeheader()
        for r in rows: wr.writerow(r)
    # ppa.json 附加 power
    for r in rows:
        k = r["design"]
        if k in ppa:
            ppa[k]["power"] = {
                "cells": r["cells"], "p_leak_w": r["p_leak_w"],
                "p_tot_mW_a10": round(r["p_tot_a10_w"]*1e3, 3),
                "p_tot_mW_a25": round(r["p_tot_a25_w"]*1e3, 3),
                "method": "liberty-parsed, alpha=0.10/0.25, V=1.80V, @measured fmax"}
    json.dump(ppa, open(PPA_JSON, "w"), indent=1)
    print(f"\nwrote {OUT}/power_table.csv ({len(rows)} designs) + ppa.json power fields")

if __name__ == "__main__":
    main()
