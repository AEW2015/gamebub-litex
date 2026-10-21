// SPDX-License-Identifier: 0BSD
// Behavioral models for source-level simulation only. These are not vendor
// simulation libraries and do not model FPGA clock routing or JTAG hardware.
module BUFG(input wire I, output wire O);
    assign O = I;
endmodule

module BSCANE2 #(
    parameter integer JTAG_CHAIN = 1
) (
    output wire DRCK,
    output wire CAPTURE,
    output wire SHIFT,
    output wire SEL,
    output wire TDI,
    input wire TDO,
    output wire RESET,
    output wire RUNTEST,
    output wire TCK,
    output wire TMS,
    output wire UPDATE
);
    reg sim_drck = 1'b0;
    reg sim_capture = 1'b0;
    reg sim_shift = 1'b0;
    reg sim_sel = 1'b0;

    assign DRCK = sim_drck;
    assign CAPTURE = sim_capture;
    assign SHIFT = sim_shift;
    assign SEL = sim_sel;
    assign TDI = 1'b0;
    assign RESET = 1'b0;
    assign RUNTEST = 1'b0;
    assign TCK = sim_drck;
    assign TMS = 1'b0;
    assign UPDATE = 1'b0;

    // Retain the chain parameter in simulation for a simple elaboration check.
    initial if (JTAG_CHAIN != 4) $fatal(1, "expected USER4 BSCANE2 model");
endmodule
