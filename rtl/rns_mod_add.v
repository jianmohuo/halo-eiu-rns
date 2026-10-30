// rns_mod_add.v -- 参数化模加法器 (RNS 通道单元)
// Per Halo Paper App. F.1 / LITERATURE_MAPPING.md sec.2
// M = 2^B - C; 输入任意 B-bit; 2 级条件减覆盖 a+b < 2^(B+1)
module rns_mod_add #(
    parameter B = 32,
    parameter C = 1
) (
    input  [B-1:0] a,
    input  [B-1:0] b,
    output [B-1:0] s
);
    localparam [B:0] M = (1 << B) - C;
    wire [B:0] t  = {1'b0, a} + {1'b0, b};
    wire [B:0] t1 = (t  >= M) ? (t  - M) : t;
    wire [B:0] t2 = (t1 >= M) ? (t1 - M) : t1;
    assign s = t2[B-1:0];
endmodule
