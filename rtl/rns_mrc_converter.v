// rns_mrc_converter.v -- 流水线化 MRC 逆转换器 (S-RNS 递推 + Horner 尾段)
// Per Halo Paper App. F.2 / LITERATURE_MAPPING.md sec.4
// 算法 (与 syn/rtl_check_rns.py mrc_hw_model 逐拍一致, 三方自检 PASS):
//   SNAP: start 沿锁存 k 通道残差 (fire-and-forget)
//   SCAN (3 拍/行 x k):
//     3r   : d_r = ((r_r - S_r) mod m_r) * ch_inv(r) mod m_r
//     3r+1 : i>r: S_i  <- S_i + (d mod m_i) * gp_i   [d 跨通道先归约]
//     3r+2 : i>r: gp_i <- gp_i * gam(r,i)            (gam = m_r mod m_i)
//   HORNER (k 拍): r=k-1..0: T <- T*m_r + d_r   (T*m = (T<<B) - C*T)
// 每通道 1 个静态参数模乘器 + 1 模加器 + d 归约器 (lo + hi*Cg)
module rns_mrc_converter #(
    parameter TOTAL_BITS = 1024,
    parameter TB = 1044,   // = TOTAL_BITS+20 (覆盖 P 上界)
    parameter WB = 1260
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            start,
    input  wire [WB-1:0]   rns_in,
    output reg             done,
    output reg  [TB-1:0]   X
);
    `ifdef RNS_W4096
      `include "eiu_rns_moduli_4096.vh"
    `elsif RNS_W512
      `include "eiu_rns_moduli_512.vh"
    `else
      `include "eiu_rns_moduli_1024.vh"
    `endif
    localparam integer LP = NK;
    localparam integer BW = BMAX;
    localparam integer TW = TB + BMAX + 4;

    reg [2:0]  state;
    localparam [2:0] S_IDLE = 3'd0, S_SNAP = 3'd1, S_SCAN = 3'd2,
                     S_HOR = 3'd3,  S_DONE = 3'd4;
    reg [8:0]   row, hcnt;
    reg [1:0]   phase;
    reg [TB-1:0] T;
    reg [WB-1:0] snap, dv;

    // ---------------- 顶层公共信号 ----------------
    wire [WB-1:0] mul_p, Sr_bus;                    // 通道总线
    wire [BW-1:0] snap_r  = snap[row*BW +: BW];
    wire [BW-1:0] s_r     = Sr_bus[row*BW +: BW];
    wire [BW:0]   m_row   = ch_m(row);
    wire [BW:0]   usub    = {1'b0, snap_r} - {1'b0, s_r};
    wire [BW-1:0] u_bcast = usub[BW] ? (usub[BW-1:0] + m_row[BW-1:0])
                                     : usub[BW-1:0];
    wire [BW-1:0] d_bcast = dv[row*BW +: BW];

    // HORNER 尾段 (TW 覆盖 T*2^B)
    wire [6:0]    hB = ch_b(hcnt);
    wire [7:0]    hC = ch_c(hcnt);
    wire [BW-1:0] hd = dv[hcnt*BW +: BW];
    wire [TW-1:0] tshift = {{(TW-TB){1'b0}}, T} << hB;
    wire [TW-1:0] cmul   = {{(TW-TB){1'b0}}, T} * {{(TW-8){1'b0}}, hC};
    wire [TW-1:0] hTm    = tshift - cmul;

    // ---------------- 通道处理单元 ----------------
    genvar g;
    generate
    for (g = 0; g < NK; g = g + 1) begin : mrcch
        localparam integer Bg = ch_b(g);
        localparam integer Cg = ch_c(g);
        reg [Bg-1:0] Sr, gp;
        wire [Bg-1:0] gam_sel = ch_gam(row*LP + g);
        wire [BW:0] inv_full = ch_inv(row);
        wire [Bg-1:0] ma0 = u_bcast[Bg-1:0];
        wire [Bg-1:0] mb0 = inv_full[Bg-1:0];
        // d 归约 (mod m_g): d = hi*2^Bg + lo ≡ lo + hi*Cg
        wire [Bg-1:0] d_lo = d_bcast[Bg-1:0];
        wire [BW-1:0] d_sh = d_bcast >> Bg;
        wire [13:0]   d_hi = d_sh[13:0];
        wire [19:0]   d_hiC = d_hi * Cg;
        wire [Bg-1:0] d_mod;
        rns_mod_add #(Bg, Cg) udmod (.a(d_lo), .b({{(Bg-20){1'b0}}, d_hiC}),
                                     .s(d_mod));
        wire [Bg-1:0] ma1 = d_mod;
        wire [Bg-1:0] mb1 = gp;
        wire [Bg-1:0] ma2 = gp;
        wire [Bg-1:0] mb2 = gam_sel;
        wire [Bg-1:0] ma = (phase == 2'd0) ? ma0 : ((phase == 2'd1) ? ma1 : ma2);
        wire [Bg-1:0] mb = (phase == 2'd0) ? mb0 : ((phase == 2'd1) ? mb1 : mb2);
        wire [Bg-1:0] p;
        rns_mod_mul #(Bg, Cg) um (.a(ma), .b(mb), .p(p));
        // S 更新用加法器 (拍 3r+1)
        wire [Bg-1:0] msum;
        rns_mod_add #(Bg, Cg) uadd (.a(Sr), .b(p), .s(msum));

        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                Sr <= 0; gp <= 1;
            end else if (state == S_SNAP) begin
                Sr <= 0; gp <= 1;
            end else begin
                if (state == S_SCAN && phase == 2'd1 && (g > row))
                    Sr <= msum;
                if (state == S_SCAN && phase == 2'd2 && (g > row))
                    gp <= p;
            end
        end
        assign mul_p[g*BW +: BW] = {{(BW-Bg){1'b0}}, p};
        assign Sr_bus[g*BW +: BW] = {{(BW-Bg){1'b0}}, Sr};
    end
    endgenerate

    wire [BW-1:0] dnext = mul_p[row*BW +: BW];

    // ---------------- 控制状态机 ----------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE; done <= 0; row <= 0; hcnt <= 0;
            phase <= 0; T <= 0; X <= 0; snap <= 0; dv <= 0;
        end else begin
            done <= 1'b0;
            case (state)
            S_IDLE: if (start) state <= S_SNAP;
            S_SNAP: begin
                snap <= rns_in;
                T <= 0; row <= 0; phase <= 0;
                state <= S_SCAN;
            end
            S_SCAN: begin
                case (phase)
                2'd0: begin
                    dv[row*BW +: BW] <= dnext;
                    phase <= 2'd1;
                end
                2'd1: phase <= 2'd2;
                2'd2: begin
                    if (row == LP-1) begin
                        state <= S_HOR; hcnt <= LP-1;
                    end else begin
                        row <= row + 1; phase <= 2'd0;
                    end
                end
                endcase
            end
            S_HOR: begin
                T <= hTm[TB-1:0] + {{(TB-BW){1'b0}}, hd};
                if (hcnt == 0) state <= S_DONE;
                else           hcnt <= hcnt - 1;
            end
            S_DONE: begin
                X <= T; done <= 1'b1; state <= S_IDLE;
            end
            endcase
        end
    end
endmodule
