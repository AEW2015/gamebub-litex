`timescale 1ns/1ps
// The binding file names exact generated RTL signals; no replacement hardware.
`include "soc_bindings.vh"
module tb_gamebub_soc;
    localparam integer BIT_CYCLES = 434;
    localparam integer MAX_CYCLES = 2000000;
    localparam integer GAP_CYCLES = 300000;
    reg clk50 = 0;
    always #10 clk50 = ~clk50;
    wire serial_tx;
    `SOC_TOP dut (.clk50(clk50), .serial_rx(1'b1), .serial_tx(serial_tx));
    integer cycles = 0, last_progress = 0, count = 0, boots = 0;
    integer i;
    reg [7:0] value;
    reg receiving = 0;
    string expected = "GB_BOOT\nRAM_OK\nID_OK\nTIMER_OK\nGB_PASS\n";

    // Bindings must test safe outputs and expose reset/status from actual RTL.
    always @(posedge clk50) begin
        cycles = cycles + 1;
        if ($test$plusargs("trace_cpu") &&
            ((cycles < 400 && dut.VexRiscv.lastStageIsFiring) || cycles % 10000 == 0))
            $display("CPU cycle=%0d reset=%b pc=%08x insn=%08x firing=%b reg_valid=%b reg_data=%08x ibus=%b/%b@%08x dbus=%b/%b@%08x", cycles,
                `SOC_RESET, dut.VexRiscv.lastStagePc, dut.VexRiscv.lastStageInstruction,
                dut.VexRiscv.lastStageIsFiring, dut.VexRiscv.writeBack_REGFILE_WRITE_VALID,
                dut.VexRiscv.writeBack_REGFILE_WRITE_DATA, dut.ibus_cyc, dut.ibus_ack, dut.ibus_adr,
                dut.dbus_cyc, dut.dbus_ack, dut.dbus_adr);
        if ($test$plusargs("trace_cpu") && cycles == 10000)
            $display("BUS grant=%b ibusstb=%b shared=%b/%b adr=%08x decode=%b rom=%b/%b ack=%b clock=%b startup=%d", dut.grant, dut.ibus_stb, dut.shared_cyc, dut.shared_stb, dut.shared_adr, dut.master, dut.basesoc_ram_bus_cyc, dut.basesoc_ram_bus_stb, dut.basesoc_ram_bus_ack, dut.sys_clk, dut.crg_startup);
        if (cycles > MAX_CYCLES)
            $fatal(1, "FAIL timeout cycle=%0d boot=%0d byte=%0d status=%08x", cycles, boots, count, `SOC_STATUS);
        if (cycles - last_progress > GAP_CYCLES)
            $fatal(1, "FAIL stalled cycle=%0d boot=%0d byte=%0d status=%08x", cycles, boots, count, `SOC_STATUS);
        if (cycles > 32) begin
            if (serial_tx !== 0 && serial_tx !== 1) $fatal(1, "FAIL unknown UART TX");
            `SOC_CHECK_SAFE
        end
    end

    initial begin
        if ($test$plusargs("fault_id")) begin
            force dut.identifier_status = 32'd0;
            expected = "GB_BOOT\nRAM_OK\nGB_FAIL\n";
        end
        // Exercise actual startup reset first, then force the generated core
        // reset for a second independent boot. No firmware/memory is patched.
        last_progress = 0;
        repeat (32) @(posedge clk50);
        forever begin
            @(negedge serial_tx);
            receiving = 1;
            repeat (BIT_CYCLES / 2) @(posedge clk50);
            if (serial_tx !== 0) $fatal(1, "FAIL UART start bit");
            for (i = 0; i < 8; i = i + 1) begin
                repeat (BIT_CYCLES) @(posedge clk50);
                if (serial_tx !== 0 && serial_tx !== 1) $fatal(1, "FAIL unknown UART data");
                value[i] = serial_tx;
            end
            repeat (BIT_CYCLES) @(posedge clk50);
            if (serial_tx !== 1) $fatal(1, "FAIL UART stop bit");
            receiving = 0;
            if (value !== expected[count])
                $fatal(1, "FAIL UART mismatch boot=%0d byte=%0d got=%02x expected=%02x", boots, count, value, expected[count]);
            $display("UART boot=%0d byte=%0d value=%02x cycle=%0d", boots, count, value, cycles);
            count = count + 1;
            last_progress = cycles;
            if (count == expected.len()) begin
                if ($test$plusargs("fault_id")) begin
                    if (`SOC_STATUS !== 32'hbad00002)
                        $fatal(1, "FAIL negative control signature %08x", `SOC_STATUS);
                    $display("PASS gamebub_soc negative control: bad identifier rejected cycles=%0d signature=%08x", cycles, `SOC_STATUS);
                    $finish;
                end
                if (`SOC_STATUS !== 32'h600d000f)
                    $fatal(1, "FAIL signature %08x", `SOC_STATUS);
                boots = boots + 1;
                if (boots == 2) begin
                    $display("PASS gamebub_soc: actual VexRiscv boots=2 UART_bytes=%0d cycles=%0d signature=%08x", 2*expected.len(), cycles, `SOC_STATUS);
                    $finish;
                end
                // Let the final stop bit complete before resetting the UART.
                repeat (BIT_CYCLES) @(posedge clk50);
                force `SOC_RESET = 1'b1;
                repeat (32) @(posedge clk50);
                release `SOC_RESET;
                count = 0;
                last_progress = cycles;
            end
        end
    end
endmodule
