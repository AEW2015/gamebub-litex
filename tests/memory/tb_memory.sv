`timescale 1ns/1ps
module tb_memory;
 import sram_test_pkg::*;
 reg sys_clk=0;always #10 sys_clk=~sys_clk;
 reg sys_rst=1;
 reg [29:0] wb_adr=0;reg [31:0] wb_dat_w=0;reg [3:0] wb_sel=15;
 reg wb_cyc=0,wb_stb=0,wb_we=0;reg [2:0] wb_cti=0;reg [1:0] wb_bte=0;
 wire [31:0] wb_dat_r,reference_data;wire wb_ack,wb_err,memory_ready;
 wire [17:0] sram_a;wire [15:0] sram_dq;wire sram_ce_n,sram_we_n,sram_oe_n,sram_lb_n,sram_ub_n;
 wire [12:0] sdram_a;wire [1:0] sdram_ba,sdram_dm,sdram_cs_n,sdram_cke;
 wire [15:0] sdram_dq;wire sdram_ras_n,sdram_cas_n,sdram_we_n,sdram_clk;
 memory_test_top dut(.*);
 integer sram_writes,sram_reads,dram_writes,dram_reads,refreshes;wire model_ready;
 reg fault_sram=0,fault_sdram=0;
 initial begin fault_sram=$test$plusargs("corrupt_sram");fault_sdram=$test$plusargs("corrupt_sdram");end
 gamebub_async_sram_model sm(.a(sram_a),.dq(sram_dq),.ce_n(sram_ce_n),.we_n(sram_we_n),
  .oe_n(sram_oe_n),.lb_n(sram_lb_n),.ub_n(sram_ub_n),.fault_read(fault_sram),.writes(sram_writes),.reads(sram_reads));
 gamebub_sdr_sdram_model dm(.clk(sdram_clk),.a(sdram_a),.ba(sdram_ba),.dq(sdram_dq),.dm(sdram_dm),
  .cs_n(sdram_cs_n),.cke(sdram_cke),.ras_n(sdram_ras_n),.cas_n(sdram_cas_n),.we_n(sdram_we_n),
  .fault_read(fault_sdram),.initialized(model_ready),.refreshes(refreshes),.writes(dram_writes),.reads(dram_reads));
 integer transactions=0,total_stalls=0;
 task automatic access(input bit wr,input [31:0] address,input [31:0] value,input [3:0] sel,input [31:0] expected,input bit keep_cycle);
  integer waited;
  begin
   @(negedge sys_clk);wb_adr=address>>2;wb_dat_w=value;wb_sel=sel;wb_we=wr;wb_stb=1;wb_cyc=1;waited=0;
   @(posedge sys_clk);
   while(!wb_ack)begin waited=waited+1;if(waited>20000)$fatal(1,"Wishbone timeout addr%08x",address);@(posedge sys_clk);end
   if(wb_err)$fatal(1,"Wishbone error");
   if(!wr && wb_dat_r!==expected)$fatal(1,"Read mismatch addr%08x got%08x expected%08x",address,wb_dat_r,expected);
   if(!wr && wb_dat_r!==reference_data)$fatal(1,"External pin memory disagrees with upstream LiteX SRAM reference");
   transactions=transactions+1;total_stalls=total_stalls+waited;
   // Return at the ACK edge for continuous-CYC back-to-back transfers. The
   // next task changes address at the immediately following falling edge.
   if(!keep_cycle)begin @(negedge sys_clk);wb_stb=0;wb_cyc=0;end
  end
 endtask
 task automatic known_good_patterns(input [31:0] base);
  reg [31:0] vectors[0:7];reg [15:0] prbs;integer pattern,i;
  begin
   prbs=16'hace1;
   for(pattern=0;pattern<9;pattern=pattern+1)begin
    for(i=0;i<8;i=i+1)begin
     vectors[i][15:0]=pattern_data(pattern[3:0],18'(2*i),prbs);prbs=prbs_next(prbs);
     vectors[i][31:16]=pattern_data(pattern[3:0],18'(2*i+1),prbs);prbs=prbs_next(prbs);
     access(1,base+4*i,vectors[i],15,0,1);
    end
    for(i=0;i<8;i=i+1)access(0,base+4*i,0,15,vectors[i],1);
   end
   @(negedge sys_clk);wb_stb=0;wb_cyc=0;
  end
 endtask
 task automatic exercise(input [31:0] base,input [31:0] last);
  reg [31:0] addrs[0:7];integer i;
  begin
   addrs[0]=base;addrs[1]=base+4;addrs[2]=base+1020;addrs[3]=base+1024;
   addrs[4]=base+4092;addrs[5]=base+4096;addrs[6]=base+last-4;addrs[7]=base+last;
   for(i=0;i<8;i=i+1)access(1,addrs[i],32'ha5012345^(i*32'h10204081),15,0,1);
   for(i=0;i<8;i=i+1)access(0,addrs[i],0,15,32'ha5012345^(i*32'h10204081),1);
   access(1,base,32'hffffffff,15,0,1);
   access(1,base,32'h00000000,1,0,1);access(0,base,0,15,32'hffffff00,1);
   access(1,base,32'h12345678,2,0,1);access(0,base,0,15,32'hffff5600,1);
   access(1,base,32'habcd0000,12,0,1);access(0,base,0,15,32'habcd5600,1);
   access(1,base,0,0,0,1);access(0,base,0,15,32'habcd5600,0);
  end
 endtask
 initial begin
  repeat(8)@(negedge sys_clk);sys_rst=0;
  exercise(0,32'h0007fffc);
  // First SDRAM request deliberately starts before autonomous init finishes.
  access(1,32'h40000000,32'h12345678,15,0,0);
  if(!memory_ready || !model_ready || refreshes<8)$fatal(1,"Init not completed");
  exercise(32'h40000000,32'h01fffffc);
  access(0,0,0,15,32'habcd5600,0);
  repeat(1200)@(posedge sys_clk);
  access(0,32'h40000000,0,15,32'habcd5600,0);
  known_good_patterns(32'h1000);
  known_good_patterns(32'h40001000);
  if(refreshes<10 || sram_writes<16 || dram_writes<16 || total_stalls<10000)$fatal(1,"Insufficient coverage");
  $display("MEMORY_PIN_PASS transactions=%0d stalls=%0d SRAMwrites=%0d SDRAMwrites=%0d refreshes=%0d",transactions,total_stalls,sram_writes,dram_writes,refreshes);
  $finish;
 end
 initial begin #2000000;$fatal(1,"global timeout");end
endmodule
