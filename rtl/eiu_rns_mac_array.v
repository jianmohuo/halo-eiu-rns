// eiu_rns_mac_array.v -- 纯 RNS MAC 阵列 (无 MRC), NCH 参数化
// 综合用: 通道解耦线性架构的锚点验证 (Per LITERATURE_MAPPING sec.5)
module eiu_rns_mac_array #(
    parameter NCH = 8,
    parameter WB  = 1260
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            en,
    input  wire            clear,
    input  wire [WB-1:0]   a_rns,
    input  wire [WB-1:0]   b_rns,
    output wire [WB-1:0]   acc_rns
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
    for (gi = 0; gi < NCH; gi = gi + 1) begin : macch
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
    genvar gz;
    generate
    for (gz = NCH; gz < WB/BMAX; gz = gz + 1) begin : padch
        assign acc_rns[gz*BMAX +: BMAX] = {BMAX{1'b0}};
    end
    endgenerate
endmodule
