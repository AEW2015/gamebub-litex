// SPDX-License-Identifier: 0BSD
`timescale 1ns/1ps

module tb_gamebub_probe_top;
    reg clk_50mhz = 1'b0;
    reg sys_enable = 1'b1;
    wire vibrate_in1, vibrate_in2;
    wire dac_mclk, dac_wclk, dac_bclk, dac_din;
    wire mcu_irq_n, cart_oe_n;
    wire cart_bank0_dir, cart_bank1_dir, cart_bank2_dir, cart_bank3_dir;
    wire cart_pin30_dir, cart_pin31_dir;
    wire link_so_dir, link_si_dir, link_sd_dir, link_sc_dir;
    wire sram_ce_n, sram_we_n, sram_oe_n, sram_ub_n, sram_lb_n;
    wire [1:0] sdram_cke, sdram_cs_n;
    wire sdram_clk, sdram_we_n, sdram_ras_n, sdram_cas_n;
    wire sdram_ldqm, sdram_udqm;
    wire lcd_dotclk, lcd_hsync, lcd_vsync, lcd_data_en;
    wire [7:0] lcd_data_r, lcd_data_g, lcd_data_b;

    gamebub_probe dut (.*);

    always #10 begin
        if (sys_enable)
            clk_50mhz = ~clk_50mhz;
        else
            clk_50mhz = 1'b0;
    end

    // BSCANE2 DRCK runs asynchronously at 10 MHz, against the 50 MHz system clock.
    always #50 dut.user_status.sim_drck = ~dut.user_status.sim_drck;

    always @(posedge clk_50mhz) begin
        if ({vibrate_in1, vibrate_in2, dac_mclk, dac_wclk, dac_bclk, dac_din} !== 6'b0)
            $fatal(1, "motor/audio outputs were not held low");
        if (mcu_irq_n !== 1'b0)
            $fatal(1, "ESP32 IRQ gate was not held inactive");
        if (cart_oe_n !== 1'b1 ||
            {cart_bank0_dir, cart_bank1_dir, cart_bank2_dir, cart_bank3_dir,
             cart_pin30_dir, cart_pin31_dir} !== 6'b0)
            $fatal(1, "cartridge outputs were not disabled");
        if ({link_so_dir, link_si_dir, link_sd_dir, link_sc_dir} !== 4'b0)
            $fatal(1, "link-port outputs were not disabled");
        if ({sram_ce_n, sram_we_n, sram_oe_n, sram_ub_n, sram_lb_n} !== 5'b11111)
            $fatal(1, "SRAM was not held inactive");
        if (sdram_cke !== 2'b00 || sdram_cs_n !== 2'b11 || sdram_clk !== 1'b0 ||
            {sdram_we_n, sdram_ras_n, sdram_cas_n, sdram_ldqm, sdram_udqm} !== 5'b11111)
            $fatal(1, "SDRAM was not held inactive");
        if (lcd_dotclk !== 1'b0 || lcd_data_en !== 1'b0 ||
            lcd_hsync !== 1'b1 || lcd_vsync !== 1'b1 ||
            {lcd_data_r, lcd_data_g, lcd_data_b} !== 24'b0)
            $fatal(1, "LCD outputs did not remain at safe static levels");
    end

    task automatic capture_scan(output reg [127:0] scan);
        integer bit_index;
        begin
            @(negedge dut.user_status.sim_drck);
            dut.user_status.sim_sel = 1'b1;
            dut.user_status.sim_capture = 1'b1;
            @(posedge dut.user_status.sim_drck);
            #1;
            dut.user_status.sim_capture = 1'b0;
            dut.user_status.sim_shift = 1'b1;
            for (bit_index = 0; bit_index < 128; bit_index = bit_index + 1) begin
                @(posedge dut.user_status.sim_drck);
                scan[bit_index] = dut.tdo;
            end
            @(negedge dut.user_status.sim_drck);
            dut.user_status.sim_shift = 1'b0;
            dut.user_status.sim_sel = 1'b0;
        end
    endtask

    task automatic wait_for_done;
        integer cycles;
        begin
            cycles = 0;
            while (!dut.test_done && cycles < 2000) begin
                @(posedge clk_50mhz);
                cycles = cycles + 1;
            end
            if (!dut.test_done)
                $fatal(1, "autonomous startup did not finish BRAM test");
        end
    endtask

    task automatic check_scan(input [127:0] scan);
        begin
            if (scan[127:96] !== 32'h47425031)
                $fatal(1, "bad USER4 snapshot magic 0x%08x", scan[127:96]);
            if (scan[63:32] !== 32'd256)
                $fatal(1, "USER4 tested_words was %0d", scan[63:32]);
            if (scan[31:0] !== 32'h47420001)
                $fatal(1, "USER4 status was 0x%08x", scan[31:0]);
        end
    endtask

    reg [127:0] first_scan, second_scan, pending_scan;
    reg [31:0] heartbeat_before_pause;
    integer i;
    initial begin
        if (dut.user_status.JTAG_CHAIN != 4)
            $fatal(1, "BSCANE2 was not configured for USER4");

        // No host/ESP32 reset input exists: startup counter must release reset by itself.
        wait_for_done();
        if (dut.reset !== 1'b0)
            $fatal(1, "startup reset did not release autonomously");
        if (dut.test_failed !== 1'b0 || dut.tested_words !== 32'd256)
            $fatal(1, "top-level core did not pass all 256 words");

        // Initial scan may report the uninitialized snapshot; a later one must be fresh.
        capture_scan(first_scan);
        capture_scan(second_scan);
        check_scan(second_scan);
        if (second_scan[95:64] == first_scan[95:64])
            $fatal(1, "heartbeat did not advance between USER4 captures");

        // Stop only the simulated system clock to hold a snapshot request pending.
        // Consecutive captures during that pending window must not disturb the core.
        heartbeat_before_pause = dut.heartbeat;
        sys_enable = 1'b0;
        @(negedge dut.user_status.sim_drck);
        dut.user_status.sim_sel = 1'b1;
        dut.user_status.sim_capture = 1'b1;
        @(posedge dut.user_status.sim_drck);
        #1 dut.user_status.sim_capture = 1'b0;
        @(negedge dut.user_status.sim_drck);
        dut.user_status.sim_capture = 1'b1;
        @(posedge dut.user_status.sim_drck);
        #1;
        if (dut.tdo !== 1'b0)
            $fatal(1, "capture during pending request did not return pending zero");
        dut.user_status.sim_capture = 1'b0;
        dut.user_status.sim_sel = 1'b0;
        if (dut.heartbeat !== heartbeat_before_pause || dut.tested_words !== 32'd256 ||
            dut.test_done !== 1'b1 || dut.test_failed !== 1'b0)
            $fatal(1, "pending USER4 requests mutated core state");

        sys_enable = 1'b1;
        for (i = 0; i < 12; i = i + 1)
            @(posedge clk_50mhz);
        wait_for_done();
        capture_scan(pending_scan);
        check_scan(pending_scan);
        if (pending_scan[95:64] == heartbeat_before_pause)
            $fatal(1, "heartbeat failed to resume after pending request");

        $display("PASS gamebub_probe_top: autonomous reset, safe I/O, USER4 snapshot/scan, pending request");
        $finish;
    end
endmodule
