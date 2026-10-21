`timescale 1ns/1ps
// Verification-only primitive models. Never include this file in synthesis.
module BUFG(input I,output O);assign O=I;endmodule
module FDCE #(parameter INIT=0)(input C,CE,CLR,D,output reg Q=INIT);
 always @(posedge C or posedge CLR)if(CLR)Q<=0;else if(CE)Q<=D;
endmodule
module FDPE #(parameter INIT=0)(input C,CE,PRE,D,output reg Q=INIT);
 always @(posedge C or posedge PRE)if(PRE)Q<=1;else if(CE)Q<=D;
endmodule
module FDRE #(parameter INIT=0,IS_C_INVERTED=0,IS_D_INVERTED=0,IS_R_INVERTED=0)
 (input C,CE,R,D,output reg Q=INIT);
 wire ci=C^IS_C_INVERTED;
 always @(posedge ci)if(R^IS_R_INVERTED)Q<=0;else if(CE)Q<=D^IS_D_INVERTED;
endmodule
module FDSE #(parameter INIT=0,IS_C_INVERTED=0,IS_D_INVERTED=0,IS_S_INVERTED=0)
 (input C,CE,S,D,output reg Q=INIT);
 wire ci=C^IS_C_INVERTED;
 always @(posedge ci)if(S^IS_S_INVERTED)Q<=1;else if(CE)Q<=D^IS_D_INVERTED;
endmodule
module IBUF #(parameter IBUF_LOW_PWR="TRUE",IOSTANDARD="DEFAULT")(input I,output O);
 assign O=I;
endmodule
module OBUF #(parameter DRIVE=12,IOSTANDARD="DEFAULT",SLEW="SLOW")(input I,output O);
 assign O=I;
endmodule
module IOBUF #(parameter DRIVE=12,IOSTANDARD="DEFAULT",SLEW="SLOW",IBUF_LOW_PWR="TRUE")
 (input I,T,output O,inout IO);
 assign IO=T?1'bz:I;assign O=IO;
endmodule
module ODDR #(parameter DDR_CLK_EDGE="OPPOSITE_EDGE",INIT=0,SRTYPE="SYNC")
 (input C,CE,D1,D2,R,S,output reg Q=INIT);
 reg d2_hold=INIT;
 generate if(SRTYPE=="ASYNC")begin
   always @(posedge C or negedge C or posedge R or posedge S)begin
     if(R)Q<=0;else if(S)Q<=1;
     else if(CE)begin
       if(C)begin Q<=D1;d2_hold<=D2;end
       else Q<=DDR_CLK_EDGE=="SAME_EDGE"?d2_hold:D2;
     end
   end
 end else begin
   always @(posedge C or negedge C)begin
     if(R)Q<=0;else if(S)Q<=1;
     else if(CE)begin
       if(C)begin Q<=D1;d2_hold<=D2;end
       else Q<=DDR_CLK_EDGE=="SAME_EDGE"?d2_hold:D2;
     end
   end
 end endgenerate
endmodule
module BSCANE2 #(parameter JTAG_CHAIN=1,DISABLE_JTAG="FALSE")
 (input TDO,output CAPTURE,DRCK,RESET,RUNTEST,SEL,SHIFT,TCK,TDI,TMS,UPDATE);
 // Quiescent disconnected host: no JTAG transactions, no UART FIFO drain.
 assign {CAPTURE,DRCK,RESET,RUNTEST,SEL,SHIFT,TCK,TDI,TMS,UPDATE}=10'd0;
endmodule
module IDDR #(parameter DDR_CLK_EDGE="OPPOSITE_EDGE",INIT_Q1=0,INIT_Q2=0,SRTYPE="SYNC")
 (input C,CE,D,R,S,output reg Q1=INIT_Q1,Q2=INIT_Q2);
 reg falling_sample=INIT_Q2,rising_sample=INIT_Q1;
 always @(negedge C)begin
   if(R)begin falling_sample<=0;if(DDR_CLK_EDGE=="OPPOSITE_EDGE")Q2<=0;end
   else if(S)begin falling_sample<=1;if(DDR_CLK_EDGE=="OPPOSITE_EDGE")Q2<=1;end
   else if(CE)begin falling_sample<=D;if(DDR_CLK_EDGE=="OPPOSITE_EDGE")Q2<=D;end
 end
 always @(posedge C)begin
   if(R)begin Q1<=0;rising_sample<=0;if(DDR_CLK_EDGE!="OPPOSITE_EDGE")Q2<=0;end
   else if(S)begin Q1<=1;rising_sample<=1;if(DDR_CLK_EDGE!="OPPOSITE_EDGE")Q2<=1;end
   else if(CE)begin
     rising_sample<=D;Q1<=DDR_CLK_EDGE=="SAME_EDGE_PIPELINED"?rising_sample:D;
     if(DDR_CLK_EDGE!="OPPOSITE_EDGE")Q2<=falling_sample;
   end
 end
 initial if(SRTYPE!="SYNC")$fatal(1,"IDDR model supports synchronous reset only");
endmodule
module MMCME2_ADV #(
 parameter BANDWIDTH="OPTIMIZED",parameter real CLKFBOUT_MULT_F=5.0,
 parameter real CLKIN1_PERIOD=0.0,CLKOUT0_DIVIDE_F=1.0,
 parameter integer CLKOUT1_DIVIDE=1,CLKOUT2_DIVIDE=1,DIVCLK_DIVIDE=1,
 parameter real CLKOUT0_PHASE=0.0,CLKOUT1_PHASE=0.0,CLKOUT2_PHASE=0.0,REF_JITTER1=0.01
)(input CLKFBIN,CLKIN1,PWRDWN,RST,output CLKFBOUT,CLKOUT0,CLKOUT1,CLKOUT2,output reg LOCKED=0);
 localparam real VCO_PERIOD=CLKIN1_PERIOD*DIVCLK_DIVIDE/CLKFBOUT_MULT_F;
 reg c0=0,c1=0,c2=0;
 always #(VCO_PERIOD*CLKOUT0_DIVIDE_F/2) c0=~c0;
 always #(VCO_PERIOD*CLKOUT1_DIVIDE/2) c1=~c1;
 always #(VCO_PERIOD*CLKOUT2_DIVIDE/2) c2=~c2;
 assign CLKOUT0=LOCKED?c0:0;assign CLKOUT1=LOCKED?c1:0;assign CLKOUT2=LOCKED?c2:0;
 assign CLKFBOUT=CLKIN1;
 integer edges=0;
 always @(posedge CLKIN1 or posedge RST or posedge PWRDWN)begin
   if(RST||PWRDWN)begin LOCKED<=0;edges<=0;end
   else if(edges==19)LOCKED<=1;else edges<=edges+1;
 end
 initial begin
   if(CLKFBOUT_MULT_F!=16 || DIVCLK_DIVIDE!=1 || CLKOUT0_DIVIDE_F!=27.25 || CLKOUT1_DIVIDE!=16 || CLKOUT2_DIVIDE!=4)
     $fatal(1,"unexpected synthesized MMCM parameters");
 end
endmodule
