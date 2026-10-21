// SPDX-License-Identifier: 0BSD
`timescale 1ns/1ps
module tb_endpoint_timing;
 reg clk200=0;always #2.5 clk200=~clk200;
 reg rst_n=0,qspi_sck=0,qspi_cs_n=1;reg [3:0] qspi_dq_i=0;
 wire [3:0] dq_o,dq_oe,ref_o,ref_oe,control,ref_control;
 wire [11:0] forced,ref_forced;wire display,ref_display,irq,ref_irq;
 wire ov_wr,ref_ov_wr,mailbox_wr,ref_mailbox_wr;
 wire [17:0] ov_addr,ref_ov_addr;wire [15:0] ov_data,ref_ov_data;
 wire [13:0] mailbox_addr,ref_mailbox_addr;wire [31:0] mailbox_wdata,ref_mailbox_wdata;
 wire [31:0] diag_data,ref_diag_data;reg [4:0] diag_select=4;
 esp32_v102_endpoint dut(.clk200(clk200),.rst_n(rst_n),.qspi_sck(qspi_sck),.qspi_cs_n(qspi_cs_n),
  .qspi_dq_i(qspi_dq_i),.dq_o(dq_o),.dq_oe(dq_oe),.buttons_native(12'd0),.vblank(1'b0),.irq_request(irq),
  .control(control),.force_buttons_native(forced),.display_external(display),.color_correct_enable(),
  .overlay_xctrl(),.overlay_yctrl(),.ov_wr(ov_wr),.ov_addr(ov_addr),.ov_data(ov_data),
  .mailbox_wr(mailbox_wr),.mailbox_addr(mailbox_addr),.mailbox_wdata(mailbox_wdata),
  .mailbox_rdata(32'hdeadbeef),.diag_select(diag_select),.inject_toggle(1'b0),.diag_data(diag_data));
 esp32_v102_reference reference_dut(.clk200(clk200),.rst_n(rst_n),.qspi_sck(qspi_sck),.qspi_cs_n(qspi_cs_n),
  .qspi_dq_i(qspi_dq_i),.dq_o(ref_o),.dq_oe(ref_oe),.buttons_native(12'd0),.vblank(1'b0),.irq_request(ref_irq),
  .control(ref_control),.force_buttons_native(ref_forced),.display_external(ref_display),.color_correct_enable(),
  .overlay_xctrl(),.overlay_yctrl(),.ov_wr(ref_ov_wr),.ov_addr(ref_ov_addr),.ov_data(ref_ov_data),
  .mailbox_wr(ref_mailbox_wr),.mailbox_addr(ref_mailbox_addr),.mailbox_wdata(ref_mailbox_wdata),
  .mailbox_rdata(32'hdeadbeef),.diag_select(diag_select),.inject_toggle(1'b0),.diag_data(ref_diag_data));
 integer compare_cycles=0,cases=0,read_words=0,abort_cases=0;
 always @(negedge clk200)if(rst_n)begin
  compare_cycles=compare_cycles+1;
  if(dq_oe!==ref_oe || ((dq_o&dq_oe)!==(ref_o&ref_oe)))$fatal(1,"Pin output differs from frozen reference");
  if(forced!==ref_forced || control!==ref_control || display!==ref_display || irq!==ref_irq || diag_data!==ref_diag_data)
   $fatal(1,"Control or write counters differ from frozen reference");
  if(ov_wr!==ref_ov_wr || (ov_wr && {ov_addr,ov_data}!=={ref_ov_addr,ref_ov_data}))$fatal(1,"Overlay write differs");
  if(mailbox_wr!==ref_mailbox_wr || (mailbox_wr && {mailbox_addr,mailbox_wdata}!=={ref_mailbox_addr,ref_mailbox_wdata}))$fatal(1,"Mailbox write differs");
 end
 real hp=12.5;
 task automatic pulse;begin #(hp)qspi_sck=1;#(hp)qspi_sck=0;end endtask
 task automatic send(input integer bits,input integer lanes,input [31:0] data);
  integer b;begin for(b=bits-lanes;b>=0;b=b-lanes)begin qspi_dq_i=4'(data>>b);pulse();end qspi_dq_i=0;end
 endtask
 task automatic begin_tx;begin qspi_sck=0;qspi_dq_i=0;#(hp)qspi_cs_n=0;end endtask
 task automatic end_tx;begin qspi_sck=0;#(hp)qspi_cs_n=1;#0.5;
  if(dq_oe!==0 || ref_oe!==0)$fatal(1,"Raw CS did not release OE immediately");
  #100;end endtask
 function automatic [7:0] cmd(input bit rd,input integer lanes,input integer bits,input bit swap,burst);
  begin cmd=8'((rd?1:0)|((bits==32?2:bits==16?1:0)<<1)|(swap<<3)|(burst<<4)|((lanes==4?2:lanes==2?1:0)<<5));end
 endfunction
 function automatic [31:0] encode(input [31:0] d,input integer bits,input bit swap);
  begin
   if(bits==8)encode={24'd0,d[7:0]};
   else if(bits==16)encode=swap?{16'd0,d[7:0],d[15:8]}:{16'd0,d[15:0]};
   else encode=swap?{d[7:0],d[15:8],d[23:16],d[31:24]}:d;
  end
 endfunction
 function automatic [11:0] reverse12(input [11:0] d);
  integer b;begin for(b=0;b<12;b=b+1)reverse12[b]=d[11-b];end
 endfunction
 task automatic write_tx(input integer lanes,bits,input bit swap,burst,input [31:0] address,input [31:0] first);
  integer w;begin hp=12.5;begin_tx();send(8,1,cmd(0,lanes,bits,swap,burst));send(32,lanes,address);
   for(w=0;w<(burst?3:1);w=w+1)send(bits,lanes,encode(first+w,bits,swap));end_tx();end
 endtask
 task automatic read_tx(input integer lanes,bits,input bit swap,burst,input [31:0] expected_first,input bit abort_read);
  integer i,w;reg [31:0] value;reg [3:0] mask;begin
   hp=31.25;begin_tx();send(8,1,cmd(1,lanes,bits,swap,burst));send(32,lanes,32'hf1001008);
   for(i=0;i<64/lanes;i=i+1)pulse();
   mask=lanes==4?15:lanes==2?3:2;
   for(w=0;w<(burst?3:1);w=w+1)begin
    value=0;
    for(i=0;i<bits/lanes;i=i+1)begin
     #(hp)qspi_sck=1;
     if(dq_oe!==mask || ref_oe!==mask)$fatal(1,"Missing read ownership lanes%0d",lanes);
     value=(value<<lanes)|(lanes==1?((dq_o>>1)&1):(dq_o&mask));
     #(hp)qspi_sck=0;
     if(abort_read && i==0)begin end_tx();abort_cases=abort_cases+1;return;end
    end
    if(w==0 && value!==encode(expected_first,bits,swap))$fatal(1,"Read value mismatch lanes%0d bits%0d swap%0d got%08x expected%08x",lanes,bits,swap,value,encode(expected_first,bits,swap));
    read_words=read_words+1;
   end
   end_tx();
  end
 endtask
 integer l,b,swap,burst,j;reg [31:0] desired,expected,before_abort;
 initial begin
  repeat(10)@(negedge clk200);rst_n=1;#200;
  for(l=1;l<=4;l=l*2)for(b=8;b<=32;b=b*2)for(swap=0;swap<2;swap=swap+1)for(burst=0;burst<2;burst=burst+1)begin
   desired=32'h13570151+cases;
   write_tx(l,b,1'(swap),1'(burst),32'hf1001008,desired);
   expected=(b==8?{24'd0,desired[7:0]}:desired)&32'hfff;
   if(forced!==reverse12(expected[11:0]))$fatal(1,"40MHz service write failed");
   read_tx(l,b,1'(swap),1'(burst),expected,0);
   write_tx(l,b,1'(swap),1'(burst),32'hf2000100,desired);
   write_tx(l,b,1'(swap),1'(burst),32'h00110000,desired);
   cases=cases+1;
  end
  // Abort at command, address and data boundaries; no incomplete data commit.
  for(l=1;l<=4;l=l*2)begin
   before_abort=diag_data;hp=12.5;
   begin_tx();send(4,1,4'h5);end_tx();
   begin_tx();send(8,1,cmd(0,l,32,0,0));send(12,l,32'hf100);end_tx();
   begin_tx();send(8,1,cmd(0,l,32,0,0));send(32,l,32'hf1001008);send(4,l,32'hf);end_tx();
   if(diag_data!==before_abort)$fatal(1,"Aborted write committed");abort_cases=abort_cases+3;
   read_tx(l,32,0,1,{20'd0,reverse12(forced)},1);
  end
  $display("MATRIX_PASS cases=%0d writeSCK40MHz readSCK16MHz words=%0d aborts=%0d compared_service_cycles=%0d",cases,read_words,abort_cases,compare_cycles);$finish;
 end
 initial begin #5000000;$fatal(1,"timeout");end
endmodule
