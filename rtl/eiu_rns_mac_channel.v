// eiu_rns_mac_channel.v -- 单 RNS MAC 通道 (通道解耦, 无进位链)
// Per Halo Paper App. F.1 -- acc' = (acc + a_i*b_i) mod m_i, 单周期 reg-to-reg
// 接口兼容 baseline eiu_mac_tile 的 clear/en 语义
module eiu_rns_mac_channel #(
    parameter B = 32,
    parameter C = 1
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        en,
    input  wire        clear,
    input  wire [B-1:0] a,
    input  wire [B-1:0] b,
    output reg  [B-1:0] acc
);
    wire [B-1:0] prod, sum;
    rns_mod_mul  #(B, C) u_mul (.a(a),   .b(b),    .p(prod));
    rns_mod_add  #(B, C) u_add (.a(acc), .b(prod), .s(sum));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)     acc <= {B{1'b0}};
        else if (clear) acc <= {B{1'b0}};
        else if (en)    acc <= sum;
    end
endmodule
