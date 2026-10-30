// tb_eiu_rns.v -- EIU RNS 阵列 + MRC 自动化测试平台
// 向量: syn/rtl_check_rns.py gen; 对拍: 同脚本 check (大整数位精确)
// 输出: "ACC <vec> <ch> <hex>" / "X <vec> <hex>"
// 4096b: iverilog 加 -DRNS_W4096
module tb_eiu_rns;
    localparam integer NVEC  = 6;
    localparam integer NSTEP = 8;
`ifdef RNS_W4096
    localparam integer TOTAL = 4096;
    localparam integer WB    = 6006;   // 91*66
    localparam integer BMAXW = 66;
`elsif RNS_W512
    localparam integer TOTAL = 512;
    localparam integer WB    = 648;    // 18*36
    localparam integer BMAXW = 36;
`else
    localparam integer TOTAL = 1024;
    localparam integer WB    = 1260;   // 35*36
    localparam integer BMAXW = 36;
`endif
    localparam integer NKCH = WB/BMAXW;

    reg clk, rst_n, en, clear, mrc_start;
    reg  [WB-1:0] a_rns, b_rns;
    wire [WB-1:0] acc_rns;
    wire          mrc_done;
    wire [TOTAL+19:0] mrc_x;

    eiu_rns_cluster #(.TOTAL_BITS(TOTAL), .WB(WB)) dut (
        .clk(clk), .rst_n(rst_n), .en(en), .clear(clear),
        .a_rns(a_rns), .b_rns(b_rns), .acc_rns(acc_rns),
        .mrc_start(mrc_start), .mrc_done(mrc_done), .mrc_x(mrc_x)
    );

    always #5 clk = ~clk;
    initial clk = 0;

    reg [65:0] vm [0 : NVEC*NSTEP*2*NKCH - 1];
    integer vi, si, ci, w;
    reg [31:0] xw32;

    task do_clear;
        begin
            @(negedge clk); clear = 1;
            @(negedge clk); clear = 0;
        end
    endtask

    // 激励全部 negedge 驱动 (posedge 采样, 无竞争)
    initial begin
        `ifdef RNS_W4096
          $readmemh("rns_vec_4096.txt", vm);
        `elsif RNS_W512
          $readmemh("rns_vec_512.txt", vm);
        `else
          $readmemh("rns_vec_1024.txt", vm);
        `endif
        rst_n = 0; en = 0; clear = 0; mrc_start = 0;
        a_rns = 0; b_rns = 0;
        repeat (3) @(negedge clk);
        rst_n = 1; @(negedge clk);
        for (vi = 0; vi < NVEC; vi = vi + 1) begin
            do_clear;
            for (si = 0; si < NSTEP; si = si + 1) begin
                @(negedge clk);
                for (ci = 0; ci < NKCH; ci = ci + 1)
                    a_rns[ci*BMAXW +: BMAXW] = vm[(vi*NSTEP + si)*2*NKCH + ci][BMAXW-1:0];
                for (ci = 0; ci < NKCH; ci = ci + 1)
                    b_rns[ci*BMAXW +: BMAXW] = vm[(vi*NSTEP + si)*2*NKCH + NKCH + ci][BMAXW-1:0];
                en = 1;
            end
            @(negedge clk); en = 0;
            @(posedge clk); @(negedge clk);   // acc 稳定
            for (ci = 0; ci < NKCH; ci = ci + 1)
                $display("ACC %0d %0d %h", vi, ci, acc_rns[ci*BMAXW +: BMAXW]);
            // ---- MRC 逆转换 ----
            @(negedge clk); mrc_start = 1;
            @(negedge clk); mrc_start = 0;
            wait (mrc_done === 1'b1);
            @(negedge clk);
            $write("X   %0d ", vi);
            for (w = ((TOTAL+39+31)/32) - 1; w >= 0; w = w - 1) begin
                xw32 = mrc_x >> (32*w);
                $write("%08h", xw32);
            end
            $write("\n");
        end
        $finish;
    end
endmodule
