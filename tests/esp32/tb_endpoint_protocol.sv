// SPDX-License-Identifier: 0BSD
`timescale 1ns/1ps

module tb_endpoint_protocol;
    reg clk200 = 1'b0;
    reg rst_n = 1'b0;
    always #2.5 clk200 = ~clk200;

    wire qspi_sck, qspi_cs_n;
    wire [3:0] qspi_dq_i, dq_o, dq_oe;
    reg [11:0] buttons_native = 12'b0;
    reg vblank = 1'b0;
    wire irq_request;
    wire [3:0] control;
    wire [11:0] force_buttons_native;
    wire display_external, color_correct_enable;
    wire [23:0] overlay_xctrl, overlay_yctrl;
    wire ov_wr;
    wire [17:0] ov_addr;
    wire [15:0] ov_data;
    wire mailbox_wr;
    wire [13:0] mailbox_addr;
    wire [31:0] mailbox_wdata;
    wire [31:0] diag_data;
    reg [4:0] diag_select = 0;
    reg inject_toggle = 0;
    reg saw_overlay_start = 0;
    reg saw_overlay_end = 0;
    reg [15:0] overlay_start_data = 0;
    reg [15:0] overlay_end_data = 0;
    reg [31:0] read_value = 0;

    esp32_qspi_host_bfm #(.SCK_HALF_PERIOD_NS(31.25)) host (
        .qspi_sck(qspi_sck), .qspi_cs_n(qspi_cs_n), .qspi_dq_i(qspi_dq_i),
        .qspi_dq_o(dq_o), .qspi_dq_oe(dq_oe)
    );

    esp32_v102_endpoint dut (
        .clk200(clk200), .rst_n(rst_n),
        .qspi_sck(qspi_sck), .qspi_cs_n(qspi_cs_n), .qspi_dq_i(qspi_dq_i),
        .dq_o(dq_o), .dq_oe(dq_oe), .buttons_native(buttons_native),
        .vblank(vblank), .irq_request(irq_request), .control(control),
        .force_buttons_native(force_buttons_native),
        .display_external(display_external), .color_correct_enable(color_correct_enable),
        .overlay_xctrl(overlay_xctrl), .overlay_yctrl(overlay_yctrl),
        .ov_wr(ov_wr), .ov_addr(ov_addr), .ov_data(ov_data),
        .mailbox_wr(mailbox_wr), .mailbox_addr(mailbox_addr),
        .mailbox_wdata(mailbox_wdata), .mailbox_rdata(32'b0),
        .diag_select(diag_select), .inject_toggle(inject_toggle), .diag_data(diag_data)
    );

    always @(posedge clk200) begin
        if (ov_wr && ov_addr == 18'h00000) begin
            saw_overlay_start <= 1;
            overlay_start_data <= ov_data;
        end
        if (ov_wr && ov_addr == 18'h2a2fe) begin
            saw_overlay_end <= 1;
            overlay_end_data <= ov_data;
        end
    end

    initial begin
        repeat (8) @(posedge clk200);
        rst_n = 1'b1;
        repeat (24) @(posedge clk200);

        // Official v1.0.2 framed register transactions (8 dummy read bytes).
        host.read32(32'hf100_0004, read_value);
        if (read_value !== 32'h00c2_eb0b)
            $fatal(1, "sysclk read raw byte-swapped value: %08x", read_value);

        // Enable button-change IRQ, then exercise change -> pending read -> W1C.
        host.write32(32'hf100_1000, 32'h0000_0002);
        buttons_native[0] = 1'b1;
        repeat (20) @(posedge clk200);
        if (!irq_request) $fatal(1, "button event did not assert IRQ request");
        host.read32(32'hf100_1004, read_value);
        if (read_value !== 32'h0200_0000)
            $fatal(1, "pending read raw byte-swapped value: %08x", read_value);
        host.write32(32'hf100_1004, 32'h0000_0002);
        repeat (12) @(posedge clk200);
        if (irq_request) $fatal(1, "W1C did not deassert IRQ request");

        // Start and final valid framebuffer word addresses (360*240 pixels).
        host.write16(32'hf200_0000, 16'hffff);
        host.write16(32'hf202_a2fe, 16'h8000);
        repeat (12) @(posedge clk200);
        if (!saw_overlay_start || overlay_start_data !== 16'hffff)
            $fatal(1, "overlay start write missing or wrong");
        if (!saw_overlay_end || overlay_end_data !== 16'h8000)
            $fatal(1, "overlay last-pixel write missing or wrong");

        // DQ ownership must be released immediately after CS rises.
        if (dq_oe !== 4'b0000) $fatal(1, "QSPI DQ ownership not released");
        $display("PASS: official QSPI reads/writes, buttons, IRQ W1C and overlay bounds");
        $finish;
    end

    initial begin
        #20000000;
        $fatal(1, "protocol simulation timeout");
    end
endmodule
