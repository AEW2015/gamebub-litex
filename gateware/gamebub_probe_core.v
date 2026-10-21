// SPDX-License-Identifier: 0BSD
// 50-MHz bring-up core: autonomous heartbeat and destructive INTERNAL BRAM test.
// This never accesses external SRAM/SDRAM or any actuator. See root README.md.
module gamebub_probe_core #(
    parameter ADDR_WIDTH = 8
) (
    input  wire        clk,
    input  wire        reset,
    output reg  [31:0] heartbeat = 0,
    output reg  [31:0] tested_words = 0,
    output reg         test_done = 0,
    output reg         test_failed = 0,
    output wire [31:0] status
);
    localparam [1:0] WRITE = 0, READ_ISSUE = 1, READ_CHECK = 2, DONE = 3;
    reg [1:0] state = WRITE;
    reg [ADDR_WIDTH-1:0] address = 0;
    (* ram_style = "block" *) reg [31:0] memory [0:(1 << ADDR_WIDTH)-1];
    reg [31:0] read_data;

    function [31:0] pattern;
        input [ADDR_WIDTH-1:0] index;
        begin
            pattern = 32'h47504231 ^ (32'h01010101 * index);
        end
    endfunction

    // Synchronous read/write; no reset on memory storage or read-data register.
    // The mapper must retain an actual RAMB primitive (checked after synthesis).
    always @(posedge clk) begin
        if (!reset && state == WRITE)
            memory[address] <= pattern(address);
        read_data <= memory[address];
    end

    always @(posedge clk) begin
        heartbeat <= heartbeat + 1;
        if (reset) begin
            heartbeat <= 0;
            tested_words <= 0;
            test_done <= 0;
            test_failed <= 0;
            address <= 0;
            state <= WRITE;
        end else begin
            case (state)
                WRITE: begin
                    if (&address) begin
                        address <= 0;
                        state <= READ_ISSUE;
                    end else
                        address <= address + 1;
                end
                READ_ISSUE: state <= READ_CHECK;
                READ_CHECK: begin
                    tested_words <= tested_words + 1;
                    if (read_data != pattern(address))
                        test_failed <= 1;
                    if (&address) begin
                        test_done <= 1;
                        state <= DONE;
                    end else begin
                        address <= address + 1;
                        state <= READ_ISSUE;
                    end
                end
                DONE: state <= DONE;
                default: begin
                    test_failed <= 1;
                    test_done <= 1;
                    state <= DONE;
                end
            endcase
        end
    end
    assign status = {16'h4742, 14'b0, test_failed, test_done};
endmodule
