#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""extract_ppa.py -- 解析 yosys+abc 综合日志 -> SKY130 PPA (JSON/CSV)
实测设计: tmp/syn/*.log (原生 Yosys 0.69 + SKY130HD tt_025C_1v80 + abc amap)
基线 (先前会话同流程实测): FMA32/FMA64/EIU-MAC-tile-40b/Stein-GCD
外推项: 通道解耦线性架构 (array8 锚点 x k/8), 明确标注 measured/extrapolated
"""
import re, json, os, glob, csv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYN = os.path.join(ROOT, "tmp", "syn")
OUT = os.path.join(ROOT, "results")
os.makedirs(OUT, exist_ok=True)

META = {
    "naive512":   ("Naive 补码 MAC 512b (32x32 乘 + 512b 进位链)", "measured"),
    "array8_512":  ("RNS MAC 阵列 8 通道 (512b 锚点, 18ch 体系)", "measured"),
    "array18_512": ("RNS MAC 阵列 18 通道 (512b 全阵列)", "measured"),
    "mrc_512":     ("MRC 逆转换引擎 512b (18ch, 惰性: 75拍/次)", "measured"),
    "ch32c0":     ("RNS 单通道 mod 2^32 (截断)", "measured"),
    "ch31c1":     ("RNS 单通道 mod 2^31-1 (梅森)", "measured"),
    "ch36c1":     ("RNS 单通道 mod 2^36-1 (梅森)", "measured"),
    "ch33c3":     ("RNS 单通道 mod 2^33-3 (伪梅森)", "measured"),
    "ch30c5":     ("RNS 单通道 mod 2^30-5 (伪梅森)", "measured"),
    "array8_1024":  ("RNS MAC 阵列 8 通道 (1024b 锚点)", "measured"),
    "array35_1024": ("RNS MAC 阵列 35 通道 (1024b 全阵列)", "extrapolated"),
    "array8_4096":  ("RNS MAC 阵列 8x64b 通道 (4096b 锚点)", "measured"),
    "array91_4096": ("RNS MAC 阵列 91 通道 (4096b 全阵列)", "extrapolated"),
    "naive1024":  ("Naive 1024b 补码 MAC (进位链)", "measured"),
    "naive4096":  ("Naive 4096b 补码 MAC (进位链)", "measured"),
    "mrc_1024":   ("RNS MRC 逆转换引擎 (1024b, 惰性)", "measured"),
    "mrc_4096":   ("RNS MRC 逆转换引擎 (4096b, 惰性)", "extrapolated"),
    "fma32":      ("FP32 FMA 基线 (先前会话同流程实测)", "measured"),
    "fma64":      ("FP64 FMA 基线 (先前会话同流程实测)", "measured"),
}

def parse_log(path):
    t = open(path, errors="ignore").read()
    d = {}
    m = re.findall(r"Chip area for module .*?: ([\d.]+)", t)
    if m: d["area_um2"] = float(m[-1])
    m = re.findall(r"Delay\s*=\s*([\d.]+) ps", t)
    if m:
        d["delay_ps"] = float(m[-1])
        d["fmax_mhz"] = round(1e6 / float(m[-1]), 2)
    return d

# 旧会话基线日志 (同 liberty 同流程)
PRIOR = {
    "fma32": {"area_um2": 46348.20, "delay_ps": 21252.88, "fmax_mhz": 47.05},
    "fma64": {"area_um2": 177716.69, "delay_ps": 57531.09, "fmax_mhz": 17.38},
}

def main():
    res = {}
    for name in ["ch32c0","ch31c1","ch36c1","ch33c3","ch30c5","naive1024","naive4096",
                 "array8_1024","array8_4096","mrc_1024"]:
        p = os.path.join(SYN, name + ".log")
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            d = parse_log(p)
            if d.get("area_um2"):
                res[name] = d
    res.update(PRIOR)
    # ---- 线性外推 (通道解耦; 锚点 measured x k/8) ----
    if "array8_1024" in res:
        a = res["array8_1024"]
        res["array35_1024"] = {
            "area_um2": round(a["area_um2"] / 8 * 35, 1),
            "fmax_mhz": a["fmax_mhz"], "delay_ps": a["delay_ps"],
            "basis": "array8_1024 / 8 * 35 (通道解耦线性)"}
    if "array8_4096" in res:
        a = res["array8_4096"]
        res["array91_4096"] = {
            "area_um2": round(a["area_um2"] / 8 * 91, 1),
            "fmax_mhz": a["fmax_mhz"], "delay_ps": a["delay_ps"],
            "basis": "array8_4096 / 8 * 91 (通道解耦线性)"}
    # MRC 4096 外推: 91/35 通道比例 (SCAN 引擎通道数线性; Horner 段位宽 4096 级)

    if "mrc_1024" in res and res.get("mrc_1024", {}).get("area_um2"):
        m = res["mrc_1024"]
        res["mrc_4096"] = {"area_um2": round(m["area_um2"] / 35 * 91, 1),
                           "note": "SCAN 通道 35->91 外推, Horner 段 4096b 加宽",
                           "basis": "mrc_1024 / 35 * 91"}
    # ---- 512b 批次 (全部实测) ----
    for f in ["naive512", "array8_512", "array18_512", "mrc_512"]:
        _p = os.path.join(SYN, f + ".log")
        if not os.path.exists(_p): continue
        _t = open(_p, errors="ignore").read()
        _a = re.findall(r"Chip area for module .*?: ([\d.]+)", _t)
        _d = re.findall(r"Delay\s*=\s*([\d.]+) ps", _t)
        if not _a: continue
        nm = f
        if f == "naive512":
            res[nm] = {"area_um2": float(_a[-1]), "delay_ps": float(_d[-1]) if _d else None,
                       "fmax_mhz": round(1e6/float(_d[-1]), 2) if _d else None,
                       "desc": "Naive 补码 MAC 512b (32x32 乘 + 512b 进位链)",
                       "method": "measured"}
        elif f == "array8_512":
            res[nm] = {"area_um2": float(_a[-1]), "delay_ps": float(_d[-1]) if _d else None,
                       "fmax_mhz": round(1e6/float(_d[-1]), 2) if _d else None,
                       "desc": "RNS MAC 阵列 8 通道 (512b 锚点, 18ch 体系)",
                       "method": "measured"}
        elif f == "array18_512":
            res[nm] = {"area_um2": float(_a[-1]), "delay_ps": float(_d[-1]) if _d else None,
                       "fmax_mhz": round(1e6/float(_d[-1]), 2) if _d else None,
                       "desc": "RNS MAC 阵列 18 通道 (512b 全阵列实测)",
                       "method": "measured"}
        elif f == "mrc_512":
            res[nm] = {"area_um2": float(_a[-1]), "delay_ps": float(_d[-1]) if _d else None,
                       "fmax_mhz": round(1e6/float(_d[-1]), 2) if _d else None,
                       "desc": "MRC 逆转换引擎 512b (18ch, 惰性: 75拍/次)",
                       "method": "measured"}
    # MRC 1024 实测
    import re as _re
    _t = open(os.path.join(SYN, "mrc_1024.log"), errors="ignore").read() if os.path.exists(
        os.path.join(SYN, "mrc_1024.log")) else ""
    _a = _re.findall(r"Chip area for module .*?: ([\d.]+)", _t)
    _d = _re.findall(r"Delay\s*=\s*([\d.]+) ps", _t)
    if _a:
        res["mrc_1024"] = {"area_um2": float(_a[-1]), "cells": 401392,
                           "delay_ps": float(_d[-1]) if _d else None,
                           "fmax_mhz": round(1e6/float(_d[-1]), 2) if _d else None,
                           "desc": "MRC 逆转换引擎 1024b (35ch, 惰性: 143拍/次, 摊销)",
                           "method": "measured", "basis": "full synth"}
        _d4096 = float(_d[-1]) * 91 / 35 if _d else None  # SCAN 3x91+HORNER 91
        res["mrc_4096"] = {"area_um2": float(_a[-1]) / 35 * 91,
                           "delay_ps": _d4096, "fmax_mhz": round(1e6/_d4096, 2) if _d4096 else None,
                           "desc": "MRC 逆转换引擎 4096b (91ch, 惰性: 367拍/次)",
                           "method": "extrapolated", "basis": "mrc_1024 / 35 * 91"}
    # 元数据
    for k, v in res.items():
        v["desc"] = META.get(k, (k, "?"))[0]
        v["method"] = META.get(k, (k, "?"))[1]
    out = os.path.join(OUT, "ppa.json")
    json.dump(res, open(out, "w"), indent=1)
    # CSV
    with open(os.path.join(OUT, "ppa_table.csv"), "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["design", "desc", "method", "area_um2", "delay_ps", "fmax_mhz"])
        for k, v in res.items():
            wr.writerow([k, v.get("desc",""), v.get("method",""), v.get("area_um2",""),
                         v.get("delay_ps",""), v.get("fmax_mhz","")])
    for k in sorted(res):
        v = res[k]
        print(f"{k:14s} {v.get('method','')[:7]:8s} area={v.get('area_um2',0):>12,.0f} "
              f"fmax={v.get('fmax_mhz',0):>8} MHz")
    print("\nwrote", out, f"({len(res)} entries)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
