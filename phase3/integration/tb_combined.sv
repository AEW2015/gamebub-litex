// SPDX-License-Identifier: 0BSD
`timescale 1ns/1ps
module tb_combined;
 reg clk50=0,clk200=0,clk_video=0,sim_reset=1;
 always #10 clk50=~clk50;
 always #2.5 clk200=~clk200;
 always #17.028824834 clk_video=~clk_video;
 reg [11:0] buttons_n=12'hfff;
 wire [31:0] test_status;
 wire serial_tx; wire serial_rx=1;
 wire [17:0] sram_a;tri [15:0] sram_dq;
 wire sram_ce_n,sram_we_n,sram_oe_n,sram_lb_n,sram_ub_n;
 wire [12:0] sdram_a;wire [1:0] sdram_ba,sdram_dm,sdram_cs_n,sdram_cke;
 tri [15:0] sdram_dq;wire sdram_ras_n,sdram_cas_n,sdram_we_n,sdram_clk;
 wire lcd_dotclk,lcd_de,lcd_hsync,lcd_vsync;wire [7:0] lcd_r,lcd_g,lcd_b;
 wire qspi_sck,qspi_cs_n;wire [3:0] qspi_dq_i,qspi_dq_o,qspi_dq_oe;
 wire esp_irq_gate;
 gamebub_phase3 dut(.*);
 bit corrupt_sram=0,corrupt_sdram=0;
 integer sr_writes,sr_reads,dr_writes,dr_reads,refreshes;
 wire model_ready;
 gamebub_async_sram_model sm(.a(sram_a),.dq(sram_dq),.ce_n(sram_ce_n),
  .we_n(sram_we_n),.oe_n(sram_oe_n),.lb_n(sram_lb_n),.ub_n(sram_ub_n),
  .fault_read(corrupt_sram),.writes(sr_writes),.reads(sr_reads));
 gamebub_sdr_sdram_model dm(.clk(sdram_clk),.a(sdram_a),.ba(sdram_ba),
  .dq(sdram_dq),.dm(sdram_dm),.cs_n(sdram_cs_n),.cke(sdram_cke),
  .ras_n(sdram_ras_n),.cas_n(sdram_cas_n),.we_n(sdram_we_n),
  .fault_read(corrupt_sdram),.initialized(model_ready),.refreshes(refreshes),
  .writes(dr_writes),.reads(dr_reads));
 esp32_qspi_host_bfm host(.*);

 integer cycles=0,complete_frames=0,frame_pixels=0,line_pixels=0,active_lines=0;
 integer px=0,py=0,total_pixels=0,overlay_pixels=0,capture;
 reg previous_de=0,previous_vs=0,frame_started=0;
 reg [23:0] expected_rgb;
 bit host_done=0;
 function automatic [23:0] bar(input integer x);
  case(x/60)
   0:bar=24'hffffff;1:bar=24'hffff00;2:bar=24'h00ffff;3:bar=24'h00ff00;
   4:bar=24'hff00ff;5:bar=24'hff0000;6:bar=24'h0000ff;default:bar=0;
  endcase
 endfunction
 // A pin-only LCD consumer reconstructs coordinates from DE and VSYNC.
 // The independent component test additionally checks every clock/HSYNC edge.
 always @(posedge clk_video)begin
  #1;
  if(lcd_vsync && !previous_vs)begin
   if(frame_started)begin
    if(frame_pixels!=384000 || active_lines!=800)
     $fatal(1,"LCD incomplete frame pixels=%0d lines=%0d",frame_pixels,active_lines);
    complete_frames=complete_frames+1;
   end
   frame_started=1;frame_pixels=0;active_lines=0;py=0;
  end
  if(lcd_de)begin
   if(!previous_de)begin px=0;line_pixels=0;end
   expected_rgb=bar(px);
   // 10x10 source pixels written by real QSPI become20x20 rotated panel pixels.
   if(px<20 && py>=12 && py<32)begin expected_rgb=0;overlay_pixels=overlay_pixels+1;end
   if(px>=60 && px<70 && py>=12 && py<22)begin expected_rgb=24'hffffff;overlay_pixels=overlay_pixels+1;end
   if(px>=10 && px<12 && py>=22 && py<24)expected_rgb=bar(px);
   if({lcd_r,lcd_g,lcd_b}!==expected_rgb)
    $fatal(1,"LCD mismatch native(%0d,%0d) got=%06x expected=%06x",px,py,{lcd_r,lcd_g,lcd_b},expected_rgb);
   if(complete_frames==1)$fwrite(capture,"%c%c%c",lcd_r,lcd_g,lcd_b);
   px=px+1;line_pixels=line_pixels+1;frame_pixels=frame_pixels+1;total_pixels=total_pixels+1;
  end
  if(!lcd_de && previous_de)begin
   if(line_pixels!=480)$fatal(1,"LCD line width%0d",line_pixels);
   active_lines=active_lines+1;py=py+1;
  end
  previous_de=lcd_de;previous_vs=lcd_vsync;
 end
 always @(posedge clk50)begin
  cycles=cycles+1;
  if(cycles>5000000)$fatal(1,"Combined timeout status=%08x frames=%0d",test_status,complete_frames);
 end
 task automatic read_expect(input [31:0] address,input [31:0] expected);
  reg [31:0] raw;
  begin host.read32(address,raw);
   if(host.reverse_bytes(raw)!==expected)
    $fatal(1,"QSPI read %08x got=%08x expected=%08x",address,host.reverse_bytes(raw),expected);
  end
 endtask
 task automatic require_irq(input bit expected);
  begin repeat(40)@(posedge clk200);
   if(esp_irq_gate!==expected)$fatal(1,"ESP IRQ gate got%b expected%b",esp_irq_gate,expected);
  end
 endtask
 integer row,col;
 reg [31:0] pending;
 initial begin
  corrupt_sram=$test$plusargs("corrupt_sram");
  corrupt_sdram=$test$plusargs("corrupt_sdram");
  capture=$fopen("combined.ppm","wb");
  $fwrite(capture,"P6\n480 800\n255\n");
  repeat(20)@(negedge clk50);sim_reset=0;
  #5000;
  require_irq(0);
  read_expect(32'hf1000004,200000000);
  read_expect(32'hf1000100,32'h00f00168);
  read_expect(32'hf1000104,16);
  host.write32(32'hf1001004,15);host.write32(32'hf1001000,2);
  buttons_n[9]=0;require_irq(1); // Right shoulder, host bit2.
  read_expect(32'hf1002000,4);
  host.read32(32'hf1001004,pending);
  if(!(host.reverse_bytes(pending)&2))$fatal(1,"Missing button pending flag");
  host.write32(32'hf1001004,2);require_irq(0);
  buttons_n[9]=1;require_irq(1);
  host.write32(32'hf1001004,2);require_irq(0);
  read_expect(32'hf1002000,0);
  read_expect(32'hffff0000,0);
  for(row=0;row<10;row=row+1)for(col=0;col<10;col=col+1)
   host.write16(32'hf2000000+2*(row*360+col),16'h8000);
  for(row=30;row<35;row=row+1)for(col=0;col<5;col=col+1)
   host.write16(32'hf2000000+2*(row*360+col),16'hffff);
  // Restore transparency inside black; green maps to monochrome white.
  host.write16(32'hf2000000+2*(5*360+5),16'h0000);
  host.write16(32'hf2000000+2*(30*360+1),16'h83e0);
  // Now verify the real LCD frame event, not an injected IRQ pulse. Clear
  // stale startup flags before enabling vblank, then wait for the next frame.
  host.write32(32'hf1001004,15);host.write32(32'hf1001000,1);require_irq(0);
  @(posedge lcd_vsync);require_irq(1);
  host.read32(32'hf1001004,pending);
  if(!(host.reverse_bytes(pending)&1))$fatal(1,"Missing vblank pending flag");
  host.write32(32'hf1001004,1);require_irq(0);
  host.write32(32'hf1001000,2);
  host_done=1;
  $display("QSPI_IRQ_OVERLAY_HOST_PASS");
 end

 integer byte_number=0,bit_number;
 reg [7:0] received;
 string expected="GB3_BOOT\nSRAM_OK\nSDRAM_OK\nESP32_OK\nVIDEO_OK\nGB3_PASS\n";
 initial begin
  #1;
  if(corrupt_sram)expected="GB3_BOOT\nGB3_FAIL\n";
  if(corrupt_sdram)expected="GB3_BOOT\nSRAM_OK\nGB3_FAIL\n";
  forever begin
   @(negedge serial_tx);
   repeat(217)@(posedge clk50);
   if(serial_tx!==0)$fatal(1,"UART start");
   for(bit_number=0;bit_number<8;bit_number=bit_number+1)begin
    repeat(434)@(posedge clk50);received[bit_number]=serial_tx;
   end
   repeat(434)@(posedge clk50);
   if(serial_tx!==1)$fatal(1,"UART stop");
   if(received!==expected[byte_number])
    $fatal(1,"UART byte%0d got%02x expected%02x status%08x",byte_number,received,expected[byte_number],test_status);
   $display("UART byte=%0d value=%02x cycle=%0d status=%08x",byte_number,received,cycles,test_status);
   byte_number=byte_number+1;
   if(byte_number==expected.len())begin
    if(corrupt_sram || corrupt_sdram)begin
     if(test_status!==(corrupt_sram?32'hbad30001:32'hbad30002))$fatal(1,"Wrong failure signature");
     $display("COMBINED_NEGATIVE_PASS SRAM=%0d SDRAM=%0d status=%08x",corrupt_sram,corrupt_sdram,test_status);
    end else begin
     if(test_status!==32'h600d300f || !host_done || complete_frames<2 ||
        sr_reads<64 || dr_reads<64 || dr_writes<64 || refreshes<20 || overlay_pixels<800)
      $fatal(1,"Incomplete combined coverage status=%08x frames=%0d sr=%0d dr=%0d refresh=%0d overlay=%0d",
       test_status,complete_frames,sr_reads,dr_reads,refreshes,overlay_pixels);
     $display("COMBINED_PASS cycles=%0d frames=%0d pixels=%0d overlay=%0d SRAMreads=%0d SDRAMreads=%0d refreshes=%0d",
       cycles,complete_frames,total_pixels,overlay_pixels,sr_reads,dr_reads,refreshes);
    end
    $fclose(capture);$finish;
   end
  end
 end
endmodule
