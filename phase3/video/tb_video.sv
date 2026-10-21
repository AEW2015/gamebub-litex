`timescale 1ns/1ps
module tb_video;
`ifndef PROFILE
`define PROFILE 1
`endif
 localparam integer HT=`PROFILE ? 605:541, VT=`PROFILE ? 809:834;
 localparam integer HS=`PROFILE ? 123:14, VS=`PROFILE ? 6:24;
 reg clk=0; always #17.028825 clk=~clk;
 reg rst=1;
 wire dot,de,hs,vs; wire [7:0] r,g,b;
 wire [9:0] x,y,ox,oy;wire ode,frame_start;
 reg overlay_valid=0;reg [23:0] overlay_rgb=0;
 integer cycle=0,checked=0,pixels=0,lines=0,linepixels=0,fd,fo;
 reg overlay_enable=0;
 gamebub_video dut(.video_clk(clk),.video_rst(rst),.dotclk(dot),.de(de),.hsync(hs),.vsync(vs),
   .r(r),.g(g),.b(b),.x(x),.y(y),.overlay_x(ox),.overlay_y(oy),.overlay_de(ode),
   .frame_start(frame_start),.overlay_valid(overlay_valid),.overlay_rgb(overlay_rgb));
 // A synchronous pixel lookup models the ESP32 overlay RAM reader contract.
 always @(posedge clk) begin
   overlay_valid <= !rst && overlay_enable && ode && ox>=10 && ox<30 && oy>=20 && oy<40;
   overlay_rgb <= 24'h1265ab;
 end
 function automatic [23:0] bars(input integer col);
   case(col/60)
    0:bars=24'hffffff;1:bars=24'hffff00;2:bars=24'h00ffff;3:bars=24'h00ff00;
    4:bars=24'hff00ff;5:bars=24'hff0000;6:bars=24'h0000ff;default:bars=0;
   endcase
 endfunction
 integer source_x=0,source_y=0;
 wire ready;wire [23:0] rgb0;
 wire hs0,vs0,de0,locked,underflow,framing;wire [9:0] rx,ry;
 always @(posedge clk) begin
   if(rst) begin source_x<=0;source_y<=0;end
   else if(ready) begin
     if(source_x==479) begin source_x<=0;source_y<=source_y==799?0:source_y+1;end
     else source_x<=source_x+1;
   end
 end
 // Unmodified independently maintained public packaged raster, profile explicit.
 gamebub_axis_raster #(.HSTART(HS),.VSTART(VS),.HTOTAL(HT),.VTOTAL(VT),.RGB_PACKING(1)) reference(
   .clk(clk),.resetn(!rst),.tdata(bars(source_x)),.tvalid(!rst),
   .tuser(source_x==0 && source_y==0),.tlast(source_x==479),.tready(ready),
   .hs(hs0),.vs(vs0),.de(de0),.rgb(rgb0),.x(rx),.y(ry),
   .locked(locked),.underflow(underflow),.framing_error(framing));
 reg rh=0,rv=0,rd=0;reg[23:0] rr=0;reg[9:0] rxd=0,ryd=0;
 always @(posedge clk) begin
   if(rst) begin rh<=0;rv<=0;rd<=0;rr<=0;rxd<=0;ryd<=0;end
   else begin
     rh<=hs0;rv<=vs0;rd<=de0;rr<=de0&&overlay_valid?overlay_rgb:rgb0;rxd<=rx;ryd<=ry;
   end
 end
 reg old_de=0;
 integer u,v,expected_de,expected_hs,expected_vs;
 reg [23:0] expected_rgb;
 initial begin
   fd=$fopen("colorbars.ppm","wb");fo=$fopen("overlay.ppm","wb");
   $fwrite(fd,"P6\n480 800\n255\n");$fwrite(fo,"P6\n480 800\n255\n");
   repeat(5)@(negedge clk);rst=0;
   // At each falling edge observe settled registered pin outputs.
   while(cycle<2*HT*VT+2) begin
     @(negedge clk);
     if(dot!==0) $fatal(1,"dotclock mismatch");
     if({hs,vs,de,r,g,b,x,y} !== {rh,rv,rd,rr,rxd,ryd})
       $fatal(1,"reference mismatch cycle=%0d got=%h ref=%h",cycle,{hs,vs,de,r,g,b,x,y},{rh,rv,rd,rr,rxd,ryd});
     if(cycle>=1 && cycle<=2*HT*VT) begin
       checked++;
       u=(cycle-1)%HT;v=((cycle-1)/HT)%VT;
       expected_hs=u<4;expected_vs=v<4;
       expected_de=u>=HS&&u<HS+480&&v>=VS&&v<VS+800;
       if({hs,vs,de} !== {1'(expected_hs),1'(expected_vs),1'(expected_de)})
         $fatal(1,"independent timing mismatch cycle=%0d u=%0d v=%0d",cycle,u,v);
       if(de) begin
         if(x!==10'(u-HS)||y!==10'(v-VS))$fatal(1,"coordinate mismatch");
         expected_rgb=bars(u-HS);
         if(cycle>HT*VT && x>=10 && x<30 && y>=20 && y<40)expected_rgb=24'h1265ab;
         if({r,g,b}!==expected_rgb)$fatal(1,"pixel mismatch x=%0d y=%0d",x,y);
         if(cycle<=HT*VT)$fwrite(fd,"%c%c%c",r,g,b);else $fwrite(fo,"%c%c%c",r,g,b);
         pixels++;linepixels++;
       end else if({r,g,b}!==0)$fatal(1,"nonblack blanking");
       if(!de&&old_de) begin
         if(linepixels!=480)$fatal(1,"line width %0d",linepixels);
         lines++;linepixels=0;
       end
       old_de=de;
     end
     cycle++;
     if(cycle==HT*VT)overlay_enable=1;
   end
   if(underflow||framing)$fatal(1,"reference stream faults");
   if(pixels!=768000 || lines!=1600)$fatal(1,"bad geometry pixels=%0d lines=%0d",pixels,lines);
   $fclose(fd);$fclose(fo);
   $display("VIDEO_PASS profile=%0d frames=2 pixels=%0d lines=%0d checked_clocks=%0d overlay_pixels=400",`PROFILE,pixels,lines,checked);
   $finish;
 end
 initial begin #100000000; $fatal(1,"video timeout");end
endmodule
