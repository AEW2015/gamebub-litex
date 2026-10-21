`timescale 1ns/1ps
// Fixed-rate raster: AXIS cannot pause the physical LCD clock. A missing pixel
// blacks the rest of this frame and drains input until the next SOF. No silent
// pixel shift. Upstream must provide a pixel each active cycle (use a FIFO).
module gamebub_axis_raster #(
 parameter integer WIDTH=480, HEIGHT=800, HSTART=14, VSTART=24,
 parameter integer HTOTAL=541, VTOTAL=834, HSYNC=4, VSYNC=4,
 parameter integer RGB_PACKING=0
)(
 input wire clk,resetn,input wire [23:0] tdata,
 input wire tvalid,tuser,tlast,output wire tready,
 output reg hs=0,vs=0,de=0,output reg [23:0] rgb=0,
 output reg [9:0] x=0,y=0,output reg locked=0,
 output reg underflow=0,framing_error=0
);
 reg [9:0] sx=0,sy=0;
 wire active=sx>=HSTART && sx<HSTART+WIDTH && sy>=VSTART && sy<VSTART+HEIGHT;
 wire first_pixel=sx==HSTART && sy==VSTART;
 wire last_pixel=sx==HSTART+WIDTH-1 && sy==VSTART+HEIGHT-1;
 wire end_line=sx==HSTART+WIDTH-1;
 // An early SOF is held, never discarded. Unsynchronized non-SOF data drains.
 assign tready=resetn && (tuser ? first_pixel : (locked ? active : 1'b1));
 wire take=tvalid && tready;
 wire display_pixel=active && take && ((locked && !tuser) || (first_pixel && tuser));
 always @(posedge clk) begin
  if(!resetn) begin
   sx<=0;sy<=0;hs<=0;vs<=0;de<=0;rgb<=0;x<=0;y<=0;
   locked<=0;underflow<=0;framing_error<=0;
  end else begin
   if(sx==HTOTAL-1) begin sx<=0;sy<=sy==VTOTAL-1?0:sy+1'b1;end else sx<=sx+1'b1;
   hs<=sx<HSYNC;vs<=sy<VSYNC;de<=active;
   x<=active?sx-HSTART:0;y<=active?sy-VSTART:0;
   // AMD AXIS Video RGB8 packs {R,B,G}; optional conventional {R,G,B}.
   rgb<=display_pixel ? (RGB_PACKING ? tdata : {tdata[23:16],tdata[7:0],tdata[15:8]}) : 24'd0;
   if(first_pixel) begin
    if(take && tuser) locked<=1;
    else begin locked<=0;underflow<=1;end
   end else if(active && locked && !display_pixel) begin
    locked<=0;
    if(tvalid && tuser) framing_error<=1;else underflow<=1;
   end
   if(display_pixel && tlast!=end_line) begin locked<=0;framing_error<=1;end
   // Every new frame must start with SOF, including after a complete good frame.
   if(last_pixel) locked<=0;
  end
 end
endmodule
