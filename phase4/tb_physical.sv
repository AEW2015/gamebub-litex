// SPDX-License-Identifier: 0BSD
`timescale 1ns/1ps
`include "simulation_bindings.vh"
module tb_physical;
 reg clk50=0;always #10 clk50=~clk50;
 reg [11:0] buttons_n=12'hfff;
 wire [17:0]sram_a;tri[15:0]sram_dq;
 wire sram_ce_n,sram_we_n,sram_oe_n,sram_lb_n,sram_ub_n;
 wire [12:0]sdram_a;wire[1:0]sdram_ba,sdram_dm,sdram_cs_n,sdram_cke;
 tri[15:0]sdram_dq;wire sdram_ras_n,sdram_cas_n,sdram_we_n,sdram_clk;
 wire lcd_dotclk,lcd_de,lcd_hsync,lcd_vsync;wire[7:0]lcd_r,lcd_g,lcd_b;
 wire qspi_sck,qspi_cs_n;tri[3:0]qspi_dq;
 wire[3:0]qspi_dq_i,qspi_dq_o=qspi_dq,qspi_dq_oe=dut.basesoc2;
 wire esp_irq_gate;
 wire cart_oe_n,cart_bank0_dir,cart_bank1_dir,cart_bank2_dir,cart_bank3_dir,cart_pin30_dir,cart_pin31_dir;
 wire dac_bclk,dac_din,dac_mclk,dac_wclk,link_sc_dir,link_sd_dir,link_si_dir,link_so_dir,vibrate_in1,vibrate_in2;
 gamebub_soc dut(.*);
 bit corrupt_sram=0,corrupt_sdram=0;
 integer sr_writes,sr_reads,dr_writes,dr_reads,refreshes;wire model_ready;
 gamebub_async_sram_model sm(.a(sram_a),.dq(sram_dq),.ce_n(sram_ce_n),.we_n(sram_we_n),.oe_n(sram_oe_n),.lb_n(sram_lb_n),.ub_n(sram_ub_n),.fault_read(corrupt_sram),.writes(sr_writes),.reads(sr_reads));
 gamebub_sdr_sdram_model dm(.clk(sdram_clk),.a(sdram_a),.ba(sdram_ba),.dq(sdram_dq),.dm(sdram_dm),.cs_n(sdram_cs_n),.cke(sdram_cke),.ras_n(sdram_ras_n),.cas_n(sdram_cas_n),.we_n(sdram_we_n),.fault_read(corrupt_sdram),.initialized(model_ready),.refreshes(refreshes),.writes(dr_writes),.reads(dr_reads));
 esp32_qspi_host_bfm host(.*);
 // Host ownership comes solely from its transmitted packet phase. In read
 // transactions it releases at the final address falling edge, before dummy.
 integer host_edges=0;reg[7:0]host_command=0;reg host_released=0;
 wire host_driving=!qspi_cs_n&&!host_released;
 assign qspi_dq=host_driving?qspi_dq_i:4'hz;
 always @(negedge qspi_cs_n)begin host_edges=0;host_command=0;host_released=0;end
 always @(posedge qspi_sck)if(!qspi_cs_n)begin
   host_edges=host_edges+1;if(host_edges<=8)host_command={host_command[6:0],qspi_dq_i[0]};
 end
 always @(negedge qspi_sck)if(!qspi_cs_n && host_edges==16 && host_command[0])host_released=1;
 always @(posedge qspi_cs_n)host_released=0;
 always @(posedge clk50)if(host_driving && |qspi_dq_oe)$fatal(1,"physical QSPI contention");

 integer cycles=0,frames=0,pixels=0,frame_pixels=0,lines=0,line_pixels=0,px=0,py=0,capture;
 bit started=0,old_de=0,old_vs=0,host_done=0;
 reg[23:0]expected;
 function automatic[23:0]bar(input integer x);
   case(x/60)0:bar=24'hffffff;1:bar=24'hffff00;2:bar=24'h00ffff;3:bar=24'h00ff00;
     4:bar=24'hff00ff;5:bar=24'hff0000;6:bar=24'h0000ff;default:bar=0;endcase
 endfunction
 always @(posedge lcd_dotclk)begin
   #1;
   if(lcd_vsync&&!old_vs && `PASSES==3 && !corrupt_sram&&!corrupt_sdram)begin
     if(started)begin
       if(frame_pixels!=384000||lines!=800)$fatal(1,"physical frame geometry pixels=%0d lines=%0d",frame_pixels,lines);
       frames++;$display("PHYSICAL_FRAME_COMPLETE frame=%0d pixels=%0d",frames,frame_pixels);
     end
     started=1;frame_pixels=0;lines=0;py=0;
   end
   if(started && frames<2)begin
     if(lcd_de)begin
       if(!old_de)begin px=0;line_pixels=0;end
       expected=bar(px);
       if((px>=440&&px<450 || px>=460&&px<470)&&py>=780&&py<790)expected=24'h00ff00;
       // Real QSPI writes create a 4x4 opaque black corner of the rotated OSD.
       if(px<4&&py>=12&&py<16)expected=0;
       if({lcd_r,lcd_g,lcd_b}!==expected)$fatal(1,"physical LCD pixel %0d,%0d got=%06x expected=%06x passes=%x",px,py,{lcd_r,lcd_g,lcd_b},expected,`PASSES);
       if(frames==0)$fwrite(capture,"%c%c%c",lcd_r,lcd_g,lcd_b);
       px++;line_pixels++;frame_pixels++;pixels++;
     end
     if(!lcd_de&&old_de)begin
       if(line_pixels!=480)$fatal(1,"physical line width %0d",line_pixels);
       lines++;py++;
     end
   end
   old_de=lcd_de;old_vs=lcd_vsync;
 end
 always @(posedge clk50)begin
   cycles++;
   if(cycles%500000==0)$display("PHYSICAL_PROGRESS cycles=%0d result=%08x passes=%x frames=%0d",cycles,`RESULT,`PASSES,frames);
   if(cycles>6500000)$fatal(1,"physical timeout result=%08x passes=%x frames=%0d",`RESULT,`PASSES,frames);
   if(cycles>2000 && {vibrate_in1,vibrate_in2,dac_bclk,dac_din,dac_mclk,dac_wclk,link_sc_dir,link_sd_dir,link_si_dir,link_so_dir,cart_bank0_dir,cart_bank1_dir,cart_bank2_dir,cart_bank3_dir,cart_pin30_dir,cart_pin31_dir}!==16'b0)$fatal(1,"unsafe physical peripheral output");
   if(cycles>2000 && cart_oe_n!==1)$fatal(1,"cartridge enabled");
 end
 task automatic read_expect(input[31:0]address,input[31:0]expected_value);
   reg[31:0]raw;begin host.read32(address,raw);if(host.reverse_bytes(raw)!==expected_value)$fatal(1,"physical QSPI address=%x got=%x expected=%x",address,host.reverse_bytes(raw),expected_value);end
 endtask
 task automatic require_irq(input bit value);
   begin repeat(40)@(posedge clk50);if(esp_irq_gate!==value)$fatal(1,"physical IRQ got=%b expected=%b",esp_irq_gate,value);end
 endtask
 initial begin
   wait(dut.service_rst==0);#5000;
   read_expect(32'hf1000004,200000000);read_expect(32'hf1000100,32'h00f00168);
   host.write32(32'hf1001004,15);host.write32(32'hf1001000,2);require_irq(0);
   buttons_n[9]=0;require_irq(1);read_expect(32'hf1002000,4);
   host.write32(32'hf1001004,2);require_irq(0);buttons_n[9]=1;require_irq(1);
   host.write32(32'hf1001004,2);require_irq(0);
   host.write16(32'hf2000000,16'h8000);host.write16(32'hf2000002,16'h8000);
   host.write16(32'hf2000000+720,16'h8000);host.write16(32'hf2000002+720,16'h8000);
   host_done=1;$display("PHYSICAL_QSPI_IRQ_OVERLAY_PASS");
 end
 initial begin
   corrupt_sram=$test$plusargs("corrupt_sram");corrupt_sdram=$test$plusargs("corrupt_sdram");
   capture=$fopen("physical.ppm","wb");$fwrite(capture,"P6\n480 800\n255\n");
   if(corrupt_sram||corrupt_sdram)begin
     wait(`RESULT[31:16]==16'hbad4);
     if(`RESULT!==(corrupt_sram?32'hbad40001:32'hbad40002))$fatal(1,"wrong physical negative result %x",`RESULT);
     $display("PHYSICAL_NEGATIVE_PASS sram=%b sdram=%b result=%08x cycles=%0d",corrupt_sram,corrupt_sdram,`RESULT,cycles);
   end else begin
     wait(`RESULT==32'h600d400f && `PASSES==3 && frames>=2 && host_done);
     if(sr_reads<64 || dr_reads<64 || dr_writes<64 || refreshes<20 || pixels!=768000)$fatal(1,"insufficient physical coverage");
     $display("PHYSICAL_PASS cycles=%0d result=%08x passes=%x frames=%0d pixels=%0d SRAMreads=%0d SDRAMreads=%0d refreshes=%0d",cycles,`RESULT,`PASSES,frames,pixels,sr_reads,dr_reads,refreshes);
   end
   $fclose(capture);$finish;
 end
endmodule
