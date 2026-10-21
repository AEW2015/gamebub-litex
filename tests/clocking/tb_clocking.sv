`timescale 1ns/1ps
module tb_clocking;
 reg clk50=0;always #10 clk50=~clk50;
 wire sys_clk,service_clk,video_clk,sys_rst,service_rst,video_rst,locked,reset_request,por_done_monitor;
 clocking_dut dut(.*);
 realtime last_sys=0,last_service=0,last_video=0,period_sys,period_service,period_video;
 integer sys_edges=0,service_edges=0,video_edges=0,lock_epochs=0;
 always @(posedge reset_request)begin sys_edges=0;service_edges=0;video_edges=0;end
 always @(posedge locked)lock_epochs++;
 always @(posedge sys_clk)begin
   period_sys=$realtime-last_sys;last_sys=$realtime;
   if(!reset_request)sys_edges++;
 end
 always @(posedge service_clk)begin
   period_service=$realtime-last_service;last_service=$realtime;
   if(!reset_request)service_edges++;
 end
 always @(posedge video_clk)begin
   period_video=$realtime-last_video;last_video=$realtime;
   if(!reset_request)video_edges++;
 end
 always @(negedge sys_rst)if($realtime-last_sys>0.001 || sys_edges<2)$fatal(1,"sys reset released asynchronously/early");
 always @(negedge service_rst)if($realtime-last_service>0.001 || service_edges<2)$fatal(1,"service reset released asynchronously/early");
 always @(negedge video_rst)if($realtime-last_video>0.001 || video_edges<2)$fatal(1,"video reset released asynchronously/early");
 task check_running;
   begin
     wait(!sys_rst && !service_rst && !video_rst);
     repeat(20)@(posedge clk50);
     if(period_sys<19.999||period_sys>20.001)$fatal(1,"bad sys period %f",period_sys);
     if(period_service<4.999||period_service>5.001)$fatal(1,"bad service period %f",period_service);
     if(period_video<34.061||period_video>34.064)$fatal(1,"bad video period %f",period_video);
   end
 endtask
 initial begin
   #1;if({sys_rst,service_rst,video_rst}!==3'b111)$fatal(1,"reset not asserted initially");
   repeat(10)@(negedge clk50);
   if(por_done_monitor||locked)$fatal(1,"POR prematurely released");
   check_running();
   // Simulate lock loss/stopped output clocks and require asynchronous resets.
   #1;force dut.MMCME2_ADV.PWRDWN=1;
   #0.01;if({sys_rst,service_rst,video_rst}!==3'b111)$fatal(1,"lock-loss reset missing");
   #100;release dut.MMCME2_ADV.PWRDWN;
   check_running();
   if(lock_epochs!=2)$fatal(1,"recovery did not relock");
   $display("CLOCKING_PASS sys_period_ns=%f service_period_ns=%f video_period_ns=%f lock_epochs=%0d async_assert_sync_release=1",period_sys,period_service,period_video,lock_epochs);
   $finish;
 end
 initial begin #100000;$fatal(1,"clocking timeout");end
endmodule
