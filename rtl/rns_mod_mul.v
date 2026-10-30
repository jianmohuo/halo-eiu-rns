// rns_mod_mul.v -- 参数化模乘法器 (单周期组合, 结构化约减)
// Per Halo Paper App. F.1 / LITERATURE_MAPPING.md sec.2
// M = 2^B - C (C<=39). 2^B ≡ C (mod M):
//   x = a*b = hi*2^B + lo ≡ lo + C*hi
//   一轮折叠 k1 = t1>>B (<=C), t2 < 2^B + C^2; 两级条件减 -> [0,M)
// C=0 (mod 2^B): 纯截断 (三模数集 {2^n-1, 2^n, 2^n+1} 的 2^n 通道)
module rns_mod_mul #(
    parameter B = 32,
    parameter C = 1
) (
    input  [B-1:0] a,
    input  [B-1:0] b,
    output [B-1:0] p
);
    localparam [B:0] M = (1 << B) - C;
    generate
    if (C == 0) begin : g_pow2
        wire [2*B-1:0] x = a * b;
        assign p = x[B-1:0];
    end else begin : g_mers
        wire [2*B-1:0] x  = a * b;
        wire [B-1:0]   lo = x[B-1:0];
        wire [B-1:0]   hi = x[2*B-1:B];
        wire [B+6:0]  t1 = {7'b0, lo} + {1'b0, C} * {7'b0, hi};
        wire [6:0]    k1 = t1[B+6:B];
        wire [B+6:0]  t2 = {7'b0, t1[B-1:0]} + {1'b0, C} * {1'b0, k1};
        wire [B+6:0]  t3 = (t2 >= {6'b0, M}) ? (t2 - {6'b0, M}) : t2;
        wire [B+6:0]  t4 = (t3 >= {6'b0, M}) ? (t3 - {6'b0, M}) : t3;
        assign p = t4[B-1:0];
    end
    endgenerate
endmodule
