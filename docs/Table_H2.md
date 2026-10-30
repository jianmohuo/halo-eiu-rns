# Table H2 — Hardware Advantage (for paper) / 论文硬件优势表

## Measured (SKY130HD, tt 0.25C 1.80V, Yosys 0.69 + ABC amap)

| Metric | Naive carry-chain | RNS-EIU | Advantage |
|---|---:|---:|---:|
| Fmax @512b | 28.61 MHz | 26.4 MHz (18ch, full) | ×0.92 (crossover ~1–2k bit) |
| Fmax @1024b | 12.37 MHz | 32.14 MHz (8ch anchor, 35ch linear) | **×2.6** |
| Fmax @4096b | 1.69 MHz | 22.48 MHz (8ch anchor, 91ch linear) | **×13.3** |
| Area @4096b | 255,743 µm² | 10,012,465 µm² (91ch) | ×39 cost |
| Energy/MAC @512b | 0.396 nJ | 4.86 nJ | ×12 cost |
| Energy/MAC @4096b | 1.509 nJ | 69.13 nJ | ×46 cost |
| P_leak (18ch) | — | 0.27 µW | negligible |
| Linearity | — | 8ch→18ch = 96.7% | predictable |

## Projected (5nm, explicit rules: area/100, f×38, CV²f)

| Metric | H100 exact (FP64 limb, 700 W) | EIU cluster (5nm proj) | Advantage |
|---|---:|---:|---:|
| 7B exact tok/s | 9.8 | **71.4** (1k arrays, 7.4 W) | throughput ×7.3, power ×95 less |
| 600B exact tok/s | 0.093 | **8.3** (10k, 74 W) | ×89 |
| Energy/token 7B | 71 J | **0.10 J** | **680×** |
| Energy/token 600B | 7,500 J | **8.9 J** | **840×** |
| Area 7B cluster | 814 mm² (die) | 6.9 mm² | 0.85% of die |
| Rack share | 120 kW (GB200) | 74 W (10k arrays) | 0.06% |

## Functional proof

- 512b: 114/114 bit-exact; 1024b: 216/216; 4096b: 552/552 (incl. lazy-MRC recovery)
- Three-way independent golden model (Python big-int ↔ iverilog RTL ↔ self-check)

Citation: @article{ren2025halo, title={Halo Architecture: From Fuzzy to Exact}, author={Ren, Hansheng}, journal={arXiv:2510.08260}, year={2025}}
