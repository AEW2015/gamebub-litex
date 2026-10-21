// SPDX-License-Identifier: 0BSD
// Minimal Rev4.x source-to-bitstream probe, NOT ESP32-compatible application FW.
// All exposed functional peripherals are inactive. USER4 reads status only.
module gamebub_probe (
    input  wire clk_50mhz,
    output wire vibrate_in1, vibrate_in2,
    output wire dac_mclk, dac_wclk, dac_bclk, dac_din,
    output wire mcu_irq_n,
    output wire cart_oe_n,
    output wire cart_bank0_dir, cart_bank1_dir, cart_bank2_dir, cart_bank3_dir,
    output wire cart_pin30_dir, cart_pin31_dir,
    output wire link_so_dir, link_si_dir, link_sd_dir, link_sc_dir,
    output wire sram_ce_n, sram_we_n, sram_oe_n, sram_ub_n, sram_lb_n,
    output wire [1:0] sdram_cke, sdram_cs_n,
    output wire sdram_clk, sdram_we_n, sdram_ras_n, sdram_cas_n,
    output wire sdram_ldqm, sdram_udqm,
    output wire lcd_dotclk, lcd_hsync, lcd_vsync, lcd_data_en,
    output wire [7:0] lcd_data_r, lcd_data_g, lcd_data_b
);
    wire clk;
    BUFG system_clock (.I(clk_50mhz), .O(clk));

    // Configuration INIT releases reset without any ESP32 transaction.
    reg [5:0] startup = 0;
    always @(posedge clk)
        if (!(&startup)) startup <= startup + 1;
    wire reset = !(&startup);
    wire [31:0] heartbeat, tested_words, status;
    wire test_done, test_failed;
    gamebub_probe_core core (
        .clk(clk), .reset(reset), .heartbeat(heartbeat),
        .tested_words(tested_words), .status(status),
        .test_done(test_done), .test_failed(test_failed)
    );

    // Rev4 drives an nFET IRQ gate: despite this historic port name, LOW is idle.
    assign mcu_irq_n = 0;
    assign {vibrate_in1, vibrate_in2} = 2'b00;
    assign {dac_mclk, dac_wclk, dac_bclk, dac_din} = 4'b0000;
    assign cart_oe_n = 1;
    assign {cart_bank0_dir, cart_bank1_dir, cart_bank2_dir, cart_bank3_dir,
            cart_pin30_dir, cart_pin31_dir} = 0;
    assign {link_so_dir, link_si_dir, link_sd_dir, link_sc_dir} = 0;
    assign {sram_ce_n, sram_we_n, sram_oe_n, sram_ub_n, sram_lb_n} = 5'b11111;
    assign sdram_cke = 2'b00;
    assign sdram_cs_n = 2'b11;
    assign sdram_clk = 0;
    assign {sdram_we_n, sdram_ras_n, sdram_cas_n, sdram_ldqm, sdram_udqm} = 5'b11111;
    assign {lcd_dotclk, lcd_data_en} = 2'b00;
    assign {lcd_hsync, lcd_vsync} = 2'b11;
    assign {lcd_data_r, lcd_data_g, lcd_data_b} = 24'b0;

    // JTAG USER4 read-only diagnostic, low 32 bits shifted first. A capture
    // requests a system-domain snapshot; a LATER capture returns it when ready.
    // Zero indicates pending/uninitialized. No RAM/actuator writes are exposed.
    wire drck, capture, shift, select, tdi;
    wire tdo;
    BSCANE2 #(.JTAG_CHAIN(4)) user_status (
        .DRCK(drck), .CAPTURE(capture), .SHIFT(shift), .SEL(select), .TDI(tdi),
        .TDO(tdo), .RESET(), .RUNTEST(), .TCK(), .TMS(), .UPDATE()
    );
    reg request = 0;
    (* ASYNC_REG = "TRUE" *) reg [1:0] request_sync = 0;
    reg acknowledged = 0;
    reg [127:0] snapshot = 0;
    always @(posedge clk) begin
        request_sync <= {request_sync[0], request};
        if (request_sync[1] != acknowledged) begin
            snapshot <= {32'h47425031, heartbeat, tested_words, status};
            acknowledged <= request_sync[1];
        end
    end
    (* ASYNC_REG = "TRUE" *) reg [1:0] ack_sync = 0;
    reg [127:0] shift_data = 0;
    always @(posedge drck) begin
        ack_sync <= {ack_sync[0], acknowledged};
        if (select && capture) begin
            if (ack_sync[1] == request) begin
                shift_data <= snapshot;
                request <= ~request;
            end else
                shift_data <= 0;
        end else if (select && shift)
            shift_data <= {1'b0, shift_data[127:1]};
    end
    assign tdo = shift_data[0];
endmodule
