# Halo EIU RNS — Arithmetic-Precision-Decoupled Model Architecture（算术精度解耦模型架构，同构硬件支持无限连续精度）

### Isomorphic Hardware Substrate Supporting Infinite Continuous Precision
### 同构硬件底座支持无限连续精度

[![Paper: arXiv 2601.18702v5](https://img.shields.io/badge/arXiv-2601.18702v5-B31B1B.svg)](https://arxiv.org/abs/2601.18702v5)
[![Process: SKY130HD](https://img.shields.io/badge/Process-SKY130HD-1f2328.svg)](#3-measured-ppa--honest-trade-offs--实测-ppa-与架构权衡)
[![Hardware: Verilog 2001](https://img.shields.io/badge/Hardware-Verilog__2001-orange.svg)](#6-repository-structure--仓库结构)
[![Paper Link](https://img.shields.io/badge/Paper-arXiv%3A2601.18702v5-0969da.svg)](https://arxiv.org/abs/2601.18702v5)

> **One canonical model representation, multiple runtime numerical realizations.**  
> **单一规范模型表示，多种运行时数值实现。**
>
> Model truth is fundamentally separated from arithmetic precision. In traditional architectures (e.g., GPUs/TPUs), precision is a static attribute locked at model deployment time. In the Halo Exact Inference Unit (EIU), precision is a **dynamic runtime attribute** governed by rational approximation strategies and Residue Number System (RNS) channel allocation, executed seamlessly on a completely isomorphic hardware substrate.  
> Full details: [https://arxiv.org/abs/2601.18702v5](https://arxiv.org/abs/2601.18702v5)


> [!NOTE]
> ⚠️ **项目状态 / Project Scope**
> 
> 本项目是用于研究和比较 RNS 架构的 RTL 与 PPA 估算示范，不是已完成流片或硅后验证的芯片设计。“无限连续精度”是指 Halo 通过动态增加互素模数通道实现精度无上限扩展的**架构范式**。在物理落地中，具体硬件实例（如本仓库实现的 91 通道、4096-bit 拓扑）虽受限于固定通道数，但其提供的动态范围（约 $10^{1233}$）对于极深推理场景而言已极其庞大且在实际应用中几乎不受限；同时，硅片面积与反向重构（Garner MRC）开销会随着激活通道数相应扩展。文中结果基于 SKY130HD 标准单元综合与时序估算；标注为 extrapolated 的数据由实测锚点外推，功耗数据基于 Liberty 单元模型和假设活动率估算；此外，部分非 PPA 相关控制逻辑未完全实现或计入当前评估计算。实际芯片结果会受到布局布线、时钟树、负载、工艺角及真实工作负载活动率影响，可能与本文数据不同。
> 
> *This repository is an RTL and PPA-estimation demonstrator for studying and comparing an RNS architecture; it is not a taped-out or silicon-validated chip. "Infinite continuous precision" represents an extensible architectural paradigm achievable by expanding co-prime moduli channels. While physical implementations operate on a bounded channel array (e.g., the 91-channel, 4096-bit topology in this repo, which already provides a practically unbounded dynamic range of $\approx 10^{1233}$ for deep reasoning), silicon area and inverse reconstruction (Garner MRC) costs scale alongside activated channels. Results are based on SKY130HD standard-cell synthesis and timing estimates. Entries marked extrapolated are derived from measured anchors, power figures are Liberty-based estimates using assumed activity factors, and non-PPA-critical control logic is not fully implemented or included in the calculations. Physical implementation and workload-dependent results may differ.*

---

## 📑 Contents / 目录

1. [Core Concept: Breaking the GPU Fixed-Function Tax / 核心架构理念](#section-1)
2. [Architecture & Microarchitecture / 微架构设计](#section-2)
3. [Measured PPA & Honest Trade-offs / 实测 PPA 与架构权衡](#section-3)
4. [Reference Scaling Law: 7B to 1000T / 精度扩展法则](#section-4)
5. [Reconstruction & Error Detection / 惰性重构与容错机制](#section-5)
6. [Repository Structure / 仓库结构](#section-6)
7. [Reproduction Steps / 完整复现流程](#section-7)
8. [Citation/ 引用](#section-8)

---



<a id="section-1"></a>
## 💡 1. Core Concept: Breaking the GPU Fixed-Function Tax / 核心架构理念

Halo EIU RNS challenges the fixed-function precision tax of traditional GPUs. Instead of baking disjoint physical silicon execution paths for $$FP64$$, $$FP32$$, $$FP16$$, and $$FP8$$, Halo deploys a uniformly replicated substrate of channel-parallel RNS `mod_mul` and `mod_add` tiles:

* **Isomorphic Substrate:** Uniformly replicated modular arithmetic tiles across 91 parallel channels, each working on pairwise coprime moduli ($$m_i \approx 2^{28}$$ in the 512b/1024b sets, $$b \le 66$$ for 4096b).
* **Zero Cross-Channel Carry:** Multiply-accumulate operations across residue channels operate with $$O(1)$$ zero-inter-channel carry dependency. The critical path is strictly bounded by a single 32-bit channel tile.
* **Gear-Switching Precision:** Precision is simply the number of active moduli channels:
  <!-- $$\text{Dynamic Precision (bits)} = \text{popcount}(\text{active\_mask}[90:0]) \times \sim 28.5\text{b}$$  -->
  $$\text{Precision (bits)} = \sum_{i \in \text{active}} \lfloor \log_2 m_i \rfloor \approx \left\lfloor \log_2 \prod_{i \in \text{active}} m_i \right\rfloor$$

* **Pay-as-you-go Power (1-Clock Switch):** Reconfigure precision dynamically in **1 clock cycle** via `clk_en[i] = active_mask[i]`. Inactive channels are clock-gated with negligible leakage. Dynamic power and area scale linearly with active channel count.

---

<a id="section-2"></a>
## 🏛️ 2. Architecture & Microarchitecture / 微架构设计

```text
+-----------------------------------------------------------------------------------+
|                               Halo EIU RNS Substrate                              |
|                                                                                   |
|   +-------------------+   +-------------------+           +-------------------+   |
|   | RNS Channel 0     |   | RNS Channel 1     |   ...     | RNS Channel 90    |   |
|   | Modulo m_0        |   | Modulo m_1        |           | Modulo m_90       |   |
|   | (2^k / Mersenne)  |   | (Mersenne/Pseudo) |           | (Mersenne/Pseudo) |   |
|   +---------+---------+   +---------+---------+           +---------+---------+   |
|             |                       |                               |             |
|   +---------v-----------------------v-------------------------------v---------+   |
|   |                       Dynamic Active Channel Mask                         |   |
|   |                      active_mask[90:0] (1-cycle switch)                   |   |
|   +---------------------------------+-----------------------------------------+   |
|                                     |                                             |
|                                     v                                             |
|   +---------------------------------------------------------------------------+   |
|   |          O(1) Parallel Vector MAC Array (Zero Cross-Channel Carry)        |   |
|   +---------------------------------+-----------------------------------------+   |
|                                     | (Off-Path Garner MRC Lazy Readout)          |
|                                     v                                             |
|   +---------------------------------------------------------------------------+   |
|   |     Garner MRC Exact Reconstruction Converter (75 cycles / 512-bit)       |   |
|   +---------------------------------------------------------------------------+   |
+-----------------------------------------------------------------------------------+
```

* **Single Channel Tile:** `rtl/rns_mod_mul.v`, `rtl/rns_mod_add.v`, and `rtl/eiu_rns_mac_channel.v` implement single-cycle modular arithmetic ($$F_{\max} \sim 32\text{-bit}$$ logic ceiling at $$124.85\text{ MHz}$$ for $$2^{32}$$).
* **MAC Array:** `rtl/eiu_rns_mac_array.v` provides runtime gear reconfiguration over `active_mask[90:0]`.
* **Lazy Inverse Converter:** `rtl/rns_mrc_converter.v` (Garner MRC) is placed completely off the critical MAC pipeline, converting RNS remainders back to standard two's-complement binary only when needed.
* **Pre-calculated Moduli Headers:** Pre-packaged coprime sets for 512-bit (18 channels, $$P > 2^{527}$$), 1024-bit (35 channels, $$P > 2^{1041}$$), and 4096-bit (91 channels, $$P > 2^{4125}$$) dynamic range.



<a id="section-3"></a>
## 📊 3. Measured PPA & Honest Trade-offs / 实测 PPA 与架构权衡

All presented data are measured via industrial open-source EDA toolchains (**Yosys 0.69 + OpenSTA**) targeting the standard cell library **SKY130HD** (`1.80 V`, nominal worst-corner timing `Fmax = 1e6 / delay_ps`), or transparently scaled via explicit linear extrapolation bases documented in `results/ppa.json`.

* **Power Methodology:** Liberty-parsed gate switching, internal, and leakage power. Activity factor $$\alpha = 0.10$$ (standard PPA) and $$\alpha = 0.25$$, evaluated at measured $$F_{\max}$$.
* **Energy Metric:** $$\text{Energy/MAC (nJ)} = P_{\text{tot, }\alpha=0.10}\text{ (mW)} / F_{\max}\text{ (MHz)}$$.

### 3.1 The 4096-bit Hard Crossover: 45.8× Energy for 13.3× Frequency
At extreme widths like 4096-bit, traditional naive complement carry chains collapse ($$F_{\max}$$ drops to $$1.69\text{ MHz}$$). RNS completely eliminates this carry chain across 91 parallel channels:

| Metric @ 4096-bit Scale | Naive Complement Baseline (`naive4096`) | Halo RNS (`array91_4096`) | Architectural Verdict / Trade-off |
|:---|---:|---:|:---|
| **Method** | Measured | Extrapolated (from measured `array8_4096`) | — |
| **$$F_{\max}$$ (MHz)** | **1.69 MHz** | **22.48 MHz** | ⚡ **13.3× Frequency Speedup** |
| **Total Power (@ $$\alpha=0.10$$)** | 2.552 mW | 1554.030 mW | Cost of active parallel execution |
| **Energy / MAC Operation** | **1.509 nJ** | **69.130 nJ** | ⚖️ **45.8× Energy Scaling Cost** |
| **Cell Count / Silicon Area** | 32,461 cells ($$0.256\text{ mm}^2$$) | 1,808,272 cells ($$10.012\text{ mm}^2$$) | **39.1× Silicon Footprint** |
| **Wide Accumulation Status** | ❌ **Infeasible (Carry Collapse)** | ✅ **Feasible & Stable Timing** | **Breaks carry-chain physical limit** |

> **Conclusion & Honest Trade-off:** We explicitly trade **45.8× energy** and **39.1× area** to achieve **13.3× $$F_{\max}$$**. Without RNS non-positional decoupling, single-cycle exact accumulation at 4096-bit scale cannot close timing at viable clock frequencies.

---

### 3.2 Complete Measured PPA Summary (SKY130HD @ 1.8V)

#### A. Single-Channel Anchors (`eiu_rns_mac_channel`, Measured)
| Channel | Modulus Class | Cells | Area ($$\mu\text{m}^2$$) | Delay (ps) | $$F_{\max}$$ (MHz) | $$P_{\text{leak}}$$ (W) | Total Power $$\alpha=0.10$$ (mW) | Energy/MAC (nJ) |
|:---|:---|---:|---:|---:|---:|---:|---:|---:|
| **`ch32c0`** | $$\bmod\ 2^{32}$$ (Truncation) | 3,366 | 18,863.09 | 8,009.50 | **124.85** | $$9.51\times 10^{-9}$$ | 16.131 | **0.129** |
| **`ch31c1`** | $$\bmod\ (2^{31}-1)$$ (Mersenne) | 7,185 | 39,495.38 | 27,480.73 | **36.39** | $$1.72\times 10^{-8}$$ | 10.063 | **0.277** |
| **`ch36c1`** | $$\bmod\ (2^{36}-1)$$ (Mersenne) | 7,619 | 41,891.43 | 29,745.96 | **33.62** | $$1.80\times 10^{-8}$$ | 9.845 | **0.293** |
| **`ch33c3`** | $$\bmod\ (2^{33}-3)$$ (Pseudo) | 8,241 | 45,522.41 | 31,550.78 | **31.69** | $$1.97\times 10^{-8}$$ | 10.083 | **0.318** |
| **`ch30c5`** | $$\bmod\ (2^{30}-5)$$ (Pseudo) | 7,136 | 39,211.36 | 31,782.26 | **31.46** | $$1.72\times 10^{-8}$$ | 8.701 | **0.277** |

#### B. Multi-Channel RNS Arrays vs. Naive Baselines & MRC Converters
| Design | Method | Channels | Precision | Cells | Area ($$\text{mm}^2$$) | $$F_{\max}$$ (MHz) | Total Power $$\alpha=0.10$$ (mW) | Energy/MAC (nJ) |
|:---|:---|---:|---:|---:|---:|---:|---:|---:|
| **`naive512`** | Measured | — | 512b | 9,555 | 0.062 | **28.61** | 11.355 | **0.396** |
| **`naive1024`** | Measured | — | 1024b | 12,827 | 0.090 | **12.37** | 6.876 | **0.556** |
| **`naive4096`** | Measured | — | 4096b | 32,461 | 0.256 | **1.69** | 2.552 | **1.509** |
| **`array8_512`** | Measured | 8 ch | 512b sub | 57,494 | 0.318 | **32.14** | 71.465 | **2.224** |
| **`array18_512`** | Measured | 18 ch | **527b** | 125,384 | 0.692 | **26.40** | 128.290 | **4.859** |
| **`array8_1024`** | Measured | 8 ch | 1024b sub | 57,494 | 0.318 | **32.14** | 71.465 | **2.224** |
| **`array35_1024`**| Extrapolated | 35 ch | **1041b** | 251,536 | 1.390 | **32.14** | 312.661 | **9.728** |
| **`array8_4096`** | Measured | 8 ch | 4096b sub | 158,969 | 0.880 | **22.48** | 136.620 | **6.077** |
| **`array91_4096`**| Extrapolated | 91 ch | **4125b** | 1,808,272 | 10.012 | **22.48** | 1554.030 | **69.130** |
| **`mrc_512`** | Measured | 18 ch | 512b MRC | 205,418 | 1.257 | **6.01** | 49.047 | 75 cycles |
| **`mrc_1024`** | Measured | 35 ch | 1024b MRC | 408,111 | 2.420 | **3.33** | 51.851 | 143 cycles |
| **`mrc_4096`** | Extrapolated | 91 ch | 4096b MRC | 1,061,089 | 6.293 | **1.28** | 51.853 | 367 cycles |

> **Extrapolation Validity:** Because channels in `eiu_rns_mac_array` are strictly decoupled without inter-channel carry logic, `array35_1024` scales linearly ($$\times 35/8$$) from measured `array8_1024` at identical $$F_{\max} = 32.14\text{ MHz}$$; `array91_4096` scales linearly ($$\times 91/8$$) from measured `array8_4096` at identical $$F_{\max} = 22.48\text{ MHz}$$.

### 3.3 Advanced Node First-Order Scaling (5nm Projection)
Applying standard Dennard and technology scaling rules ($$V_{\text{dd}}: 1.80\text{V} \to 0.75\text{V}$$, dynamic power scaling $$\sim 100\times$$):
* **512-bit RNS Exact MAC (`array18_512`):** $$128.29\text{ mW @ 130nm} \longrightarrow \mathbf{\sim 1.28\text{ mW / array @ 5nm}}$$.
* **Effective Energy Efficiency:** **$$\sim 0.49\text{ pJ / MAC}$$** for 512-bit exact arithmetic.
* **Industry Baseline:** Reference NVIDIA H100 FP8 Tensor Core consumes **$$\sim 0.60\text{ pJ / MAC}$$**. Halo RNS delivers **512-bit exact arithmetic at GPU-grade low-precision energy scale**.

---

<a id="section-4"></a>
## 📈 4. Reference Scaling Law: 7B to 1000T / 精度扩展法则

Precision required to prevent logical accumulated drift in deep reasoning architectures scales logarithmically with parameter count ($$N$$):

$$\text{Precision Bits}(N) = 512 + 100 \times \log_{10}\left(\frac{N}{7\text{B}}\right)$$

Because precision is an online dynamic attribute in Halo EIU, the table below provides **analytical floor reference profiles** (the scheduler reconfigures `active_mask` on-the-fly):

| Model Scale ($$N$$) | Log Scale $$\log_{10}(N/7\text{B})$$ | Analytical Precision Floor | Active RNS Channels ($$k$$) | Dynamic Range ($$P = \prod m_i$$) | Runtime Profile |
|:---|---:|---:|---:|:---|:---|
| **7B Parameters** | 0.000 | **527 bits** | **18–19 ch** | $$P > 2^{527}$$ | Base Gear ($$7.7\times$$ margin @ 19ch) |
| **600B Parameters** | 1.933 | **705 bits** | **26 ch** | $$P > 2^{705}$$ | Mid Gear (`active_mask[25:0]`) |
| **2T Parameters** | 2.456 | **753 bits** | **27 ch** | $$P > 2^{753}$ | Mid Gear (`active_mask[26:0]`) |
| **1000T Parameters** | 5.155 | **~1500 bits** | **54 ch** | $$P > 2^{1500}$$ | High Gear (`active_mask[53:0]`) |
| **Hardware Maximum** | 35.80 | **4125 bits** | **91 ch** | $$P > 2^{4125} \approx 10^{1233}$$ | Full Array (Supports up to $$10^{1142}$$ worst-case params) |

*Full derivation: [`docs/Scaling_7B_to_1000T.md`](docs/Scaling_7B_to_1000T.md).*

---

<a id="section-5"></a>
## ⚙️ 5. Reconstruction & Error Detection / 惰性重构与容错机制

### Garner MRC Off-Path Reconstruction
Converting RNS residues back to standard two's-complement binary uses Garner’s Mixed-Radix Conversion (MRC) algorithm:

$$X = v_1 + v_2 m_1 + v_3 m_1 m_2 + \dots + v_M \prod_{i=1}^{M-1} m_i$$

* **Latency:** Bounded to $$3k + k + 3$$ cycles (**75 cycles for 512-bit / 18ch**; **143 cycles for 1024-bit / 35ch**) in `rtl/rns_mrc_converter.v`.
* **Asynchronous Decoupling:** Reconstruction only occurs at non-linear layer boundaries, fully overlapped with memory DMA transfers and off the MAC critical execution path.

### Cluster Fault Detection
`rtl/eiu_rns_cluster.v` integrates the multi-channel MAC array with dual redundant check moduli ($$m_{\text{check1}} = 2^{31}-1$$, $$m_{\text{check2}} = 2^{61}-1$$), providing silent data corruption (SDC) mitigation over multi-trillion reasoning iterations with zero timing penalty on the main datapath.

---

<a id="section-6"></a>
## 📁 6. Repository Structure / 仓库结构

```text
halo-eiu-rns/
├── README.md                         # Main technical specifications & PPA benchmarks
├── README_numbers.md                 # Complete raw numerical appendix & verification details
├── LICENSE                           # Apache License 2.0
├── rtl/                              # Synthesizable Hardware Modules (Verilog-2001)
│   ├── eiu_rns_mac_channel.v         # Base single-channel MAC (124.85 MHz ceiling)
│   ├── eiu_rns_mac_array.v           # Multi-channel array with active_mask dynamic gating
│   ├── eiu_rns_cluster.v             # Cluster module with lazy MRC & redundant check
│   ├── eiu_mac_naive.v               # Naive 512/1024/4096-bit binary MAC baselines
│   ├── rns_mod_mul.v                 # Fast modular multiplier (2^k, 2^k-1, 2^k-c)
│   ├── rns_mod_add.v                 # Modular adder subunit
│   ├── rns_mrc_converter.v           # Garner MRC lazy inverse converter (75 cyc @ 512b)
│   ├── tb_eiu_rns.v                  # Self-checking Icarus Verilog testbench
│   └── eiu_rns_moduli_*.{vh,json}    # Pre-calculated coprime moduli sets (512b/1024b/4096b)
├── results/                          # Synthesis & Static Timing Analysis Results
│   ├── ppa.json                      # Raw extracted metrics (Fmax, area, cells, leakage)
│   ├── ppa_table.csv                 # Tabulated summary with measured/extrapolated tags
│   ├── power_table.csv               # Liberty-parsed power table @ 1.8V worst corner
│   ├── rns_expect_*.json             # Golden verification vectors
│   └── sim*_out.txt                  # Verilog simulation execution logs
├── figures/                          # Architecture Curves & Plots
│   ├── rns_scaling_ppa.png           # Frequency crossover curve (512b crossover, 4096b 13.3x)
│   ├── industrial_feasibility.png    # Node-normalized industrial feasibility comparison
│   └── resource_rns_scaling_*.png    # Resource & area scaling curves
├── docs/                             # Derivations & Microarchitecture Specifications
│   ├── Scaling_7B_to_1000T.md        # Bitwidth derivations & gear mapping formulas
│   └── Table_H2.md                   # Hardware advantage & paper Table H.2 correspondence
└── syn/                              # Open-Source EDA Toolchain Scripts
    ├── synth.ys                      # Yosys synthesis flow script
    ├── batch.sh / batch2.sh / batch512.sh # Batch synthesis & STA execution drivers
    ├── extract_ppa.py                # Parses reports into results/ppa.json & ppa_table.csv
    ├── estimate_power.py             # Liberty-parsed power calculation script
    ├── rtl_check_rns.py              # Golden arithmetic test suite generator
    └── plot_ppa_rns.py               # Generates figures/rns_scaling_ppa.png
```

---

<a id="section-7"></a>
## 🚀 7. Reproduction Steps / 完整复现流程

All hardware numbers ($$F_{\max}$$, Cell Count, Area, Dynamic Power, Leakage) can be independently reproduced using open-source EDA tools (Yosys + OpenSTA + SKY130HD PDK).

### Step 1: Clone Repository
```bash
git clone https://github.com/renhansheng/halo-eiu-rns.git
cd halo-eiu-rns
```

### Step 2: RTL Functional Verification (Icarus Verilog)
Verify exact modular arithmetic and lazy Garner MRC reconstruction against the Python golden model:
```bash
python3 syn/rtl_check_rns.py
iverilog -g2012 -DWIDTH=512  -o sim512  rtl/*.v && vvp sim512
iverilog -g2012 -DWIDTH=1024 -o sim1024 rtl/*.v && vvp sim1024
iverilog -g2012 -DWIDTH=4096 -o sim4096 rtl/*.v && vvp sim4096
```

### Step 3: Gate Synthesis & STA Timing (Yosys + OpenSTA)
Run logic synthesis and worst-corner timing analysis (`sky130_fd_sc_hd__tt_025C_1v80.lib`):
```bash
bash syn/batch.sh        # Single channels, naive 1024/4096, 8-ch arrays, and FMA
bash syn/batch2.sh       # Garner MRC converters (512b and 1024b)
bash syn/batch512.sh     # naive512 and array18_512 (full 18-channel 512b array)
```

The scripts resolve project files relative to their own location, so they can be run from any working directory. Install Yosys and make `yosys` available on `PATH`; place the SKY130HD Liberty file at `syn/sky.lib`, or set `SKY130_LIB` to its location before running the synthesis or power-estimation scripts. Generated synthesis logs go to `tmp/syn/`, mapped BLIF netlists to `syn/netlists/`, and extracted tables to `results/`.

### Step 4: Extract PPA Metrics & Estimate Power
```bash
python3 syn/extract_ppa.py       # Generates results/ppa.json & results/ppa_table.csv
python3 syn/estimate_power.py    # Generates results/power_table.csv
python3 syn/plot_ppa_rns.py      # Regenerates figures/rns_scaling_ppa.png
```

> **Expected Verification Checkpoints (`results/ppa_table.csv`):**
> * `ch32c0`: **124.85 MHz** / **18,863.09 µm²** / **3,366 cells**
> * `array18_512`: **26.40 MHz** / **691,600.80 µm²** / **125,384 cells** / **128.29 mW** ($$\alpha=0.10$$)
> * `naive4096`: **1.69 MHz** / **590,057.06 ps delay** (carry-chain timing collapse confirmed)

---

<a id="section-8"></a>
## 📝 8. Citation / 引用

If you use this hardware architecture, RTL implementation, or PPA benchmarks in your research, please cite:

```bibtex
@article{ren2026halo,
  title   = {From Fuzzy to Exact: The Halo Architecture for Infinite-Depth Reasoning via Rational Arithmetic},
  author  = {Ren, Hansheng},
  journal = {arXiv preprint arXiv:2601.18702v5},
  url     = {https://arxiv.org/abs/2601.18702v5},
  year    = {2026}
}
```

*中文用户引用要求：如在学术论文、开源项目或商业产品中使用本仓库代码、架构设计或评测数据，请在发表物/文档中显式引用 Halo 架构论文 `arXiv:2601.18702v5`*
