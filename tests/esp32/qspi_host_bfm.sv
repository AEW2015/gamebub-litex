// SPDX-License-Identifier: 0BSD
// Pin-level QSPI host model for the supported v1.0.2 endpoint subset.
// Mode 0, single-lane MSB-first command, quad address/data, 8 dummy bytes.
`timescale 1ns/1ps

module esp32_qspi_host_bfm #(
    parameter real SCK_HALF_PERIOD_NS = 31.25
) (
    output reg        qspi_sck,
    output reg        qspi_cs_n,
    output reg [3:0]  qspi_dq_i,
    input      [3:0]  qspi_dq_o,
    input      [3:0]  qspi_dq_oe
);
    initial begin
        qspi_sck = 1'b0;
        qspi_cs_n = 1'b1;
        qspi_dq_i = 4'b0000;
    end

    task automatic clock_nibble;
        begin
            #(SCK_HALF_PERIOD_NS) qspi_sck = 1'b1;
            #(SCK_HALF_PERIOD_NS) qspi_sck = 1'b0;
        end
    endtask

    task automatic begin_transaction;
        begin
            qspi_sck = 1'b0;
            qspi_dq_i = 4'b0000;
            #(SCK_HALF_PERIOD_NS) qspi_cs_n = 1'b0;
        end
    endtask

    task automatic end_transaction;
        begin
            qspi_sck = 1'b0;
            qspi_dq_i = 4'b0000;
            #(SCK_HALF_PERIOD_NS) qspi_cs_n = 1'b1;
            #1;
            if (qspi_dq_oe !== 4'b0000)
                $fatal(1, "FPGA did not release DQ immediately on raw CS deassertion");
            #(SCK_HALF_PERIOD_NS);
        end
    endtask

    task automatic send_command(input [7:0] command);
        integer i;
        begin
            for (i = 7; i >= 0; i = i - 1) begin
                qspi_dq_i = {3'b000, command[i]};
                clock_nibble();
            end
            qspi_dq_i = 4'b0000;
        end
    endtask

    task automatic send_quad32(input [31:0] data);
        integer i;
        begin
            for (i = 7; i >= 0; i = i - 1) begin
                qspi_dq_i = data[i*4 +: 4];
                clock_nibble();
            end
            qspi_dq_i = 4'b0000;
        end
    endtask

    task automatic send_address(input [31:0] address);
        begin send_quad32(address); end
    endtask

    // Match the official driver's little-endian byte stream with its default
    // byte_swap=true command field.
    function automatic [31:0] reverse_bytes(input [31:0] value);
        reverse_bytes = {value[7:0], value[15:8], value[23:16], value[31:24]};
    endfunction

    task automatic write32(input [31:0] address, input [31:0] value);
        begin
            begin_transaction();
            send_command(8'h5c); // Quad, 32-bit, byte-swap, auto-increment.
            send_address(address);
            send_quad32(reverse_bytes(value));
            end_transaction();
        end
    endtask

    task automatic write16(input [31:0] address, input [15:0] value);
        begin
            begin_transaction();
            send_command(8'h5a); // Quad, 16-bit, byte-swap, auto-increment.
            send_address(address);
            qspi_dq_i = value[7:4];   clock_nibble();
            qspi_dq_i = value[3:0];   clock_nibble();
            qspi_dq_i = value[15:12]; clock_nibble();
            qspi_dq_i = value[11:8];  clock_nibble();
            end_transaction();
        end
    endtask

    task automatic read32(input [31:0] address, output [31:0] value);
        integer i;
        begin
            begin_transaction();
            send_command(8'h5d); // Read + quad + 32-bit + swap + increment.
            send_address(address);
            qspi_dq_i = 4'b0000;
            for (i = 0; i < 16; i = i + 1) clock_nibble(); // Eight bytes.
            value = 32'b0;
            for (i = 7; i >= 0; i = i - 1) begin
                #(SCK_HALF_PERIOD_NS) qspi_sck = 1'b1;
                if (qspi_dq_oe !== 4'hf)
                    $fatal(1, "read32 nibble %0d missing quad DQ ownership: %b", i, qspi_dq_oe);
                value[i*4 +: 4] = qspi_dq_o;
                #(SCK_HALF_PERIOD_NS) qspi_sck = 1'b0;
            end
            end_transaction();
        end
    endtask

    task automatic read16(input [31:0] address, output [15:0] value);
        integer i;
        begin
            begin_transaction();
            send_command(8'h5b); // Read + quad + 16-bit + swap + increment.
            send_address(address);
            qspi_dq_i = 4'b0000;
            for (i = 0; i < 16; i = i + 1) clock_nibble();
            value = 16'b0;
            for (i = 3; i >= 0; i = i - 1) begin
                #(SCK_HALF_PERIOD_NS) qspi_sck = 1'b1;
                if (qspi_dq_oe !== 4'hf)
                    $fatal(1, "read16 nibble %0d missing quad DQ ownership: %b", i, qspi_dq_oe);
                value[i*4 +: 4] = qspi_dq_o;
                #(SCK_HALF_PERIOD_NS) qspi_sck = 1'b0;
            end
            end_transaction();
        end
    endtask
endmodule
