// eiu_rns_cluster.v -- RNS EIU 阵列顶层 (TOTAL_BITS = 1024 / 4096)
// Per Halo Paper App. F/G.1: k 通道 MAC 阵列 (无进位链) + MRC 引擎 (惰性)
// WB = NK*BMAX: 1024b: 35*36=1260; 4096b: 91*66=6006
// 4096b: -DRNS_W4096
module eiu_rns_cluster #(
    parameter TOTAL_BITS = 1024,
    parameter WB = 1260
) (
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire                   en,
    input  wire                   clear,
    input  wire [WB-1:0]          a_rns,
    input  wire [WB-1:0]          b_rns,
    output wire [WB-1:0]          acc_rns,
    input  wire                   mrc_start,
    output wire                   mrc_done,
    output wire [TOTAL_BITS+19:0] mrc_x
);
    `ifdef RNS_W4096
      `include "eiu_rns_moduli_4096.vh"
    `elsif RNS_W512
      `include "eiu_rns_moduli_512.vh"
    `else
      `include "eiu_rns_moduli_1024.vh"
    `endif

    genvar gi;
    generate
    for (gi = 0; gi < NK; gi = gi + 1) begin : macch
        localparam integer Bi = ch_b(gi);
        localparam integer Ci = ch_c(gi);
        wire [Bi-1:0] ai = a_rns[gi*BMAX +: Bi];
        wire [Bi-1:0] bi = b_rns[gi*BMAX +: Bi];
        wire [Bi-1:0] acci;
        eiu_rns_mac_channel #(Bi, Ci) uch (
            .clk(clk), .rst_n(rst_n), .en(en), .clear(clear),
            .a(ai), .b(bi), .acc(acci)
        );
        assign acc_rns[gi*BMAX +: BMAX] = {{(BMAX-Bi){1'b0}}, acci};
    end
    endgenerate

    rns_mrc_converter #(
        .TOTAL_BITS(TOTAL_BITS),
        .TB(TOTAL_BITS + 20),
        .WB(WB)
    ) umrc (
        .clk(clk), .rst_n(rst_n),
        .start(mrc_start),
        .rns_in(acc_rns),
        .done(mrc_done),
        .X(mrc_x)
    );
endmodule
