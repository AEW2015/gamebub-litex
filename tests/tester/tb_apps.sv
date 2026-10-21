// SPDX-License-Identifier: 0BSD
`timescale 1ns/1ps
`include "simulation_bindings.vh"
module tb_apps;
 reg clk50=0;always #10 clk50=~clk50;
 reg [11:0] buttons_n=12'hfff;
 wire [17:0]sram_a;tri[15:0]sram_dq;
 wire sram_ce_n,sram_we_n,sram_oe_n,sram_lb_n,sram_ub_n;
 wire [12:0]sdram_a;wire[1:0]sdram_ba,sdram_dm,sdram_cs_n,sdram_cke;
 tri[15:0]sdram_dq;wire sdram_ras_n,sdram_cas_n,sdram_we_n,sdram_clk;
 wire lcd_dotclk,lcd_de,lcd_hsync,lcd_vsync;wire[7:0]lcd_r,lcd_g,lcd_b;
 wire qspi_sck,qspi_cs_n;tri[3:0]qspi_dq;
 wire[3:0]qspi_dq_i,qspi_dq_o=qspi_dq,qspi_dq_oe=`QSPI_OE;
 wire esp_irq_gate;
 wire cart_oe_n,cart_bank0_dir,cart_bank1_dir,cart_bank2_dir,cart_bank3_dir,cart_pin30_dir,cart_pin31_dir;
 wire dac_bclk,dac_din,dac_mclk,dac_wclk,link_sc_dir,link_sd_dir,link_si_dir,link_so_dir,vibrate_in1,vibrate_in2;
 gamebub_soc dut(.*);
 bit corrupt_sram=0,corrupt_sdram=0;
 integer sr_writes,sr_reads,dr_writes,dr_reads,refreshes;wire model_ready;
 gamebub_async_sram_model sm(.a(sram_a),.dq(sram_dq),.ce_n(sram_ce_n),.we_n(sram_we_n),.oe_n(sram_oe_n),.lb_n(sram_lb_n),.ub_n(sram_ub_n),.fault_read(corrupt_sram),.writes(sr_writes),.reads(sr_reads));
 gamebub_sdr_sdram_model dm(.clk(sdram_clk),.a(sdram_a),.ba(sdram_ba),.dq(sdram_dq),.dm(sdram_dm),.cs_n(sdram_cs_n),.cke(sdram_cke),.ras_n(sdram_ras_n),.cas_n(sdram_cas_n),.we_n(sdram_we_n),.fault_read(corrupt_sdram),.initialized(model_ready),.refreshes(refreshes),.writes(dr_writes),.reads(dr_reads));
 esp32_qspi_host_bfm host(.*);
 assign qspi_dq=!qspi_cs_n ? qspi_dq_i : 4'hz; // This test emits writes only.
 always @(posedge clk50) if(!qspi_cs_n && |qspi_dq_oe)$fatal(1,"QSPI ownership conflict");
 integer cycles=0,px=0,py=0,capture,checked=0,frame=0;
 bit old_de=0,old_vs=0,checking=0,snapshot=0,overlay_set=0;
 reg[23:0]expect_rgb;
 function automatic[23:0]bar(input integer x);
   case(x/60)0:bar=24'hffffff;1:bar=24'hffff00;2:bar=24'h00ffff;3:bar=24'h00ff00;
     4:bar=24'hff00ff;5:bar=24'hff0000;6:bar=24'h0000ff;default:bar=0;endcase
 endfunction
 always @(posedge lcd_dotclk)begin
   #1;
   if(lcd_vsync&&!old_vs)begin py=0;frame++; if(`RESULT==32'h600d500f&&`PAGE==0)checking=1;end
   if(lcd_de)begin
     if(!old_de)px=0;
     if(checking && `PAGE==0)begin
       expect_rgb=bar(px);
       if(px<112||px>=368||py<188||py>=556)begin
         if({lcd_r,lcd_g,lcd_b}!==expect_rgb)$fatal(1,"background %0d,%0d",px,py);
         checked++;
       end
       if(px==112&&py==188 && {lcd_r,lcd_g,lcd_b}!==24'hffffff)$fatal(1,"UI border missing got=%06x",{lcd_r,lcd_g,lcd_b});
       if(px==120&&py==212 && {lcd_r,lcd_g,lcd_b}!==(overlay_set?24'hffffff:0))$fatal(1,"UI black / ESP32 priority incorrect");
       if(px==128&&py==332 && {lcd_r,lcd_g,lcd_b}!==24'hffffff)$fatal(1,"CPU-drawn G glyph missing");
       if(snapshot)$fwrite(capture,"%c%c%c",lcd_r,lcd_g,lcd_b);
     end
     px++;
   end
   if(!lcd_de&&old_de)py++;
   old_de=lcd_de;old_vs=lcd_vsync;
 end
 always @(posedge clk50)begin
   cycles++;
   if(cycles%2500000==0)$display("APPS_PROGRESS cycles=%0d page=%0d state=%0d progress=%0d",cycles,`PAGE,`STATE,`PROGRESS);
   if(cycles>100000000)$fatal(1,"apps timeout page=%d state=%d result=%x",`PAGE,`STATE,`RESULT);
   if(vibrate_in2!==0||cart_oe_n!==1)$fatal(1,"unsafe motor reverse or cartridge state");
 end
 task automatic press(input integer bit_index);
   begin buttons_n[bit_index]=0;#45000000;buttons_n[bit_index]=1;#45000000;end
 endtask
 task automatic page_next(input integer wanted);
   begin press(9);if(`PAGE!==wanted)$fatal(1,"shoulder navigation wanted=%0d got=%0d",wanted,`PAGE);end
 endtask
 integer motor_edges=0,nonzero_samples=0,bits_seen=0,audio_frames=0;
 reg[31:0]audio_word=0;
 always @(posedge vibrate_in1)motor_edges++;
 always @(negedge dac_bclk)begin
   #1;
   if(dac_wclk)begin bits_seen=0;audio_word=0;end
   if(bits_seen<32)begin
     audio_word={audio_word[30:0],dac_din};bits_seen++;
     if(bits_seen==32)begin
       audio_frames++;
       if(audio_word!=0)begin
         if(audio_word!==32'h08000800 && audio_word!==32'hf800f800)$fatal(1,"DSP stereo PCM mismatch %x",audio_word);
         nonzero_samples++;
       end
     end
   end else if(dac_din!==0)$fatal(1,"nonzero DSP padding");
 end
 initial begin
   corrupt_sram=$test$plusargs("corrupt_sram");corrupt_sdram=$test$plusargs("corrupt_sdram");
   wait(`RESULT==32'h600d500f);#2000000;
   capture=$fopen("apps.ppm","wb");$fwrite(capture,"P6\n480 800\n255\n");
   @(posedge lcd_vsync);snapshot=1;@(posedge lcd_vsync);snapshot=0;$fclose(capture);
   host.write16(32'hf2000000+2*(60*360+100),16'hffff);overlay_set=1;
   @(posedge lcd_vsync);@(posedge lcd_vsync);
   host.write16(32'hf2000000+2*(60*360+100),16'h0000);overlay_set=0;
   @(posedge lcd_vsync);@(posedge lcd_vsync);
   if(checked<100000)$fatal(1,"insufficient LCD comparisons");
   page_next(1);
   if(corrupt_sdram)page_next(2);
   press(0);
   if(corrupt_sram||corrupt_sdram)begin
     wait(`STATE==3);
     if(`PROGRESS>=156)$fatal(1,"fault incorrectly passed");
     $display("APPS_NEGATIVE_PASS SRAM=%b SDRAM=%b page=%d state=FAIL",corrupt_sram,corrupt_sdram,`PAGE);
     $finish;
   end
   wait(`STATE==2);if(sr_reads<8192)$fatal(1,"incomplete SRAM scratch test");
   page_next(2);press(0);wait(`STATE==2);
   if(dr_reads<8192||`PASSES!==3)$fatal(1,"incomplete SDRAM scratch test");
   page_next(3);press(0);
   if(nonzero_samples<10)$fatal(1,"audio did not start");
   press(1);#100000;if(dac_din!==0)$fatal(1,"audio B stop failed");
   page_next(4);
   buttons_n[0]=0;#45000000;buttons_n[0]=1;
   #30000000;if(motor_edges<100)$fatal(1,"motor PWM missing");
   #220000000;if(vibrate_in1!==0)$fatal(1,"motor timeout failed");
   page_next(0);press(8);if(`PAGE!==4)$fatal(1,"left shoulder failed");
   if(vibrate_in1!==0)$fatal(1,"motor not off on app exit");
   $display("APPS_PASS pixels=%0d SRAMreads=%0d SDRAMreads=%0d PCM=%0d motorEdges=%0d",checked,sr_reads,dr_reads,nonzero_samples,motor_edges);
   $finish;
 end
endmodule
