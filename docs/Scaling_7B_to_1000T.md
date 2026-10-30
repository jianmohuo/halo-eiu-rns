# Scaling: 7B → 1000T / 模数集与精度余量

## Moduli sets (all pairwise coprime, b ≤ 36 for 512/1024b sets, b ≤ 66 for 4096b set)

| Target | Precision needed | Channels k | Product P | Margin |
|---|---|---|---|---|
| 7B | 527 bit | 18–19 | P > 2^527 | 7.7× (19ch set) |
| 512b EIU | 512+15 bit | 18 | P > 2^527 | measured set |
| 600B | 705 bit | 26 | P > 2^705 | pay-as-you-go |
| 1024b EIU | 1024+17 | 35 | P > 2^1041 | measured set |
| 2T | 753 bit | 27 | P > 2^753 | pay-as-you-go |
| 1000T | ~1500 bit | 54 | P > 2^1500 | est. |
| 4096b EIU | 4096+29 | 91 | P > 2^4125 | measured set (b ≤ 66) |

- Channels use Mersenne (2^k−1), pseudo-Mersenne (2^k−c), and truncation (2^k) moduli — single-cycle mod-add/mod-mul for each class (`rtl/rns_mod_mul.v`).
- Lazy MRC cost: 3k+k+3 cycles per conversion (512b: 75; 1024b: 143), amortized over SCAN+HORNER, off the MAC critical path.

## Measured channel-level anchors (SKY130HD)

| Channel | Area µm² | Fmax MHz |
|---|---:|---:|
| mod 2^32 (truncation) | 18,863 | 124.85 |
| mod 2^31−1 (Mersenne) | 39,495 | 36.39 |
| mod 2^36−1 (Mersenne) | 41,891 | 33.62 |
| mod 2^33−3 (pseudo) | 45,522 | 31.69 |
| mod 2^30−5 (pseudo) | 39,211 | 31.46 |

Width-decoupled: Fmax stays 22–36 MHz from 18ch to 91ch (64b channels), vs naive collapse 28.6→1.69 MHz.
