// eiu_mac_naive.v -- Naive 大位宽补码 MAC baseline (carry-chain explosion)
// Per Halo Paper App. F.3: baseline eiu_mac_tile (40b, 实测 15269um2/183MHz)
// 的位宽外推结构: acc' = acc + a*b (W-bit 补码加法, 单周期组合进位链)
module eiu_mac_naive #(
    parameter W  = 1024,
    parameter AW = 32
) (
    input  wire           clk,
    input  wire           rst_n,
    input  wire           en,
    input  wire           clear,
    input  wire [AW-1:0]  a,
    input  wire [AW-1:0]  b,
    output reg  [W-1:0]   acc
);
    wire [2*AW-1:0] prod = a * b;
    wire [W-1:0]   sum  = acc + {{(W-2*AW){1'b0}}, prod};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)     acc <= {W{1'b0}};
        else if (clear) acc <= {W{1'b0}};
        else if (en)    acc <= sum;
    end
endmodule
