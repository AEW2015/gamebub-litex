// SPDX-License-Identifier: 0BSD
`timescale 1ns/1ps

module tb_gamebub_probe;
    reg clk = 1'b0;
    reg reset = 1'b1;
    wire [31:0] heartbeat;
    wire [31:0] tested_words;
    wire [31:0] status;
    wire test_done;
    wire test_failed;

    gamebub_probe_core #(.ADDR_WIDTH(8)) dut (
        .clk(clk),
        .reset(reset),
        .heartbeat(heartbeat),
        .tested_words(tested_words),
        .status(status),
        .test_done(test_done),
        .test_failed(test_failed)
    );

    always #5 clk = ~clk;

    task automatic wait_done;
        integer cycles;
        begin
            cycles = 0;
            while (!test_done && cycles < 2000) begin
                @(posedge clk);
                cycles = cycles + 1;
            end
            if (!test_done)
                $fatal(1, "timeout waiting for BRAM test completion");
        end
    endtask

    task automatic pulse_reset;
        begin
            @(negedge clk);
            reset = 1'b1;
            repeat (2) @(negedge clk);
            reset = 1'b0;
        end
    endtask

    integer reset_wait;
    reg [31:0] heartbeat_before;
    initial begin
        repeat (3) @(negedge clk);
        reset = 1'b0;

        // The heartbeat must advance while the deterministic memory test runs.
        heartbeat_before = heartbeat;
        repeat (8) @(posedge clk);
        if (heartbeat == heartbeat_before)
            $fatal(1, "heartbeat did not advance");

        wait_done();
        if (test_failed)
            $fatal(1, "uncorrupted BRAM test reported failure");
        if (tested_words != 32'd256)
            $fatal(1, "expected 256 checked words, got %0d", tested_words);
        if (status !== {16'h4742, 14'b0, 1'b0, 1'b1})
            $fatal(1, "unexpected passing status 0x%08x", status);
        repeat (4) @(posedge clk);
        if (!test_done || test_failed || tested_words != 32'd256)
            $fatal(1, "passing completion was not sticky");

        // Reset must restart counters/state without requiring memory clearing.
        pulse_reset();
        if (test_done || test_failed || tested_words != 0)
            $fatal(1, "reset did not restart the test state");
        wait_done();
        if (test_failed || tested_words != 32'd256)
            $fatal(1, "post-reset BRAM test did not pass");

        // Corrupt one stored word only after the write pass has completed.
        pulse_reset();
        reset_wait = 0;
        while (dut.state !== 2'd1 && reset_wait < 300) begin
            @(negedge clk);
            reset_wait = reset_wait + 1;
        end
        if (dut.state !== 2'd1)
            $fatal(1, "did not reach READ_ISSUE after write pass");
        dut.memory[17] = dut.memory[17] ^ 32'h0000_0001;
        wait_done();
        if (!test_failed)
            $fatal(1, "injected BRAM corruption was not detected");
        if (tested_words != 32'd256)
            $fatal(1, "corrupt test checked %0d words instead of 256", tested_words);
        if (status !== {16'h4742, 14'b0, 1'b1, 1'b1})
            $fatal(1, "unexpected failing status 0x%08x", status);
        repeat (4) @(posedge clk);
        if (!test_done || !test_failed || tested_words != 32'd256)
            $fatal(1, "failing completion was not sticky");

        $display("PASS gamebub_probe: heartbeat, 256-word pass, reset restart, corruption detection");
        $finish;
    end
endmodule
