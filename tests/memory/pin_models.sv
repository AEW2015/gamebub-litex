`timescale 1ns/1ps
// Independent pin models, deliberately no Wishbone/controller internal access.
// Sparse contents cover arbitrary full-aperture addresses (4096 written halfwords).
module gamebub_async_sram_model(
 input wire [17:0] a,inout wire [15:0] dq,
 input wire ce_n,we_n,oe_n,lb_n,ub_n,input wire fault_read,
 output integer writes,reads
);
 reg [17:0] tags[0:4095]; reg [15:0] words[0:4095]; integer used=0;
 integer k,slot; realtime write_start;
 initial begin writes=0;reads=0;write_start=0;end
 function automatic [15:0] lookup(input [17:0] key);
  integer j;begin lookup=16'hxxxx;for(j=0;j<used;j=j+1)if(tags[j]==key)lookup=words[j];end
 endfunction
 wire reading=!ce_n && !oe_n && we_n;
 assign dq=reading ? (lookup(a) ^ {15'd0,fault_read}) : 16'hzzzz;
 always @(negedge we_n) if(!ce_n) begin
  if(!oe_n)$fatal(1,"SRAM OE active during write");write_start=$realtime;
 end
 always @(posedge we_n) if(!ce_n) begin
  if($realtime-write_start<60)$fatal(1,"SRAM write pulse shorter than conservative60ns");
  slot=-1;for(k=0;k<used;k=k+1)if(tags[k]==a)slot=k;
  if(slot<0)begin if(used==4096)$fatal(1,"SRAM sparse capacity");slot=used;used=used+1;tags[slot]=a;words[slot]=0;end
  if(!lb_n)words[slot][7:0]=dq[7:0];if(!ub_n)words[slot][15:8]=dq[15:8];writes=writes+1;
 end
 always @(posedge reading)reads=reads+1;
endmodule

module gamebub_sdr_sdram_model(
 input wire clk,input wire [12:0] a,input wire [1:0] ba,
 input wire [1:0] cs_n,cke,input wire ras_n,cas_n,we_n,
 input wire [1:0] dm,inout wire [15:0] dq,input wire fault_read,
 output reg initialized=0,output integer refreshes,writes,reads
);
 reg [23:0] tags[0:4095];reg [15:0] words[0:4095];integer used=0;
 reg [12:0] rows[0:3]; reg [3:0] opened=0;
 integer activated[0:3],precharged[0:3],last_write[0:3],close_due[0:3];
 integer cycle=0,last_refresh=0,init_refreshes=0,mode_cycle=0,cas_latency=2;
 integer due[0:7];reg [23:0] read_key[0:7];reg driving=0;reg [15:0] data_out;
 integer k,slot,b,q;reg [23:0] key;
 assign dq=driving?(data_out ^ {15'd0,fault_read}):16'hzzzz;
 initial begin refreshes=0;writes=0;reads=0;for(q=0;q<8;q=q+1)due[q]=-1;
  for(b=0;b<4;b=b+1)begin activated[b]=-100;precharged[b]=-100;last_write[b]=-100;close_due[b]=-1;end
 end
 function automatic [15:0] lookup(input [23:0] address);
  integer j;begin lookup=16'hxxxx;for(j=0;j<used;j=j+1)if(tags[j]==address)lookup=words[j];end
 endfunction
 always @(posedge clk)begin
  cycle=cycle+1;driving<=#6 0;
  if(cs_n[1]!==1'b1)$fatal(1,"Unexpected second SDRAM chip select");
  // Micron CL2: READ atT0, outputs start afterT1 and validbyT2.
  // A conservative6ns clock-to-data fits the 10ns half-cycle sampling margin.
  for(q=0;q<8;q=q+1)if(due[q]==cycle)begin data_out<=#6 lookup(read_key[q]);driving<=#6 1;due[q]=-1;end
  for(b=0;b<4;b=b+1)if(close_due[b]==cycle)begin opened[b]=0;precharged[b]=cycle;close_due[b]=-1;end
  if(initialized && cycle-last_refresh>500)$fatal(1,"SDRAM refresh overdue");
  if(cke[0] && !cs_n[0])case({ras_n,cas_n,we_n})
   3'b011:begin // ACTIVATE
    if(!initialized)$fatal(1,"ACT before init");
    if(opened[ba])$fatal(1,"ACT on open bank");
    if(cycle-precharged[ba]<1)$fatal(1,"tRP violation");
    opened[ba]=1;rows[ba]=a;activated[ba]=cycle;
   end
   3'b101:begin // READ BL1, CL2
    if(!initialized || !opened[ba])$fatal(1,"READ without initialized open row");
    if(cycle-activated[ba]<1)$fatal(1,"tRCD violation");
    if(due[reads%8]>=0)$fatal(1,"Read model queue overflow");
    read_key[reads%8]={rows[ba],ba,a[8:0]};due[reads%8]=cycle+cas_latency-1;reads=reads+1;
    if(a[10])close_due[ba]=cycle+cas_latency;
   end
   3'b100:begin // WRITE BL1
    if(!initialized || !opened[ba])$fatal(1,"WRITE without initialized open row");
    if(cycle-activated[ba]<1)$fatal(1,"tRCD violation");
    key={rows[ba],ba,a[8:0]};slot=-1;
    for(k=0;k<used;k=k+1)if(tags[k]==key)slot=k;
    if(slot<0)begin if(used==4096)$fatal(1,"SDRAM sparse capacity");slot=used;used=used+1;tags[slot]=key;words[slot]=0;end
    if(!dm[0])words[slot][7:0]=dq[7:0];if(!dm[1])words[slot][15:8]=dq[15:8];
    writes=writes+1;last_write[ba]=cycle;if(a[10])close_due[ba]=cycle+2;
   end
   3'b010:begin // PRECHARGE
    if(cycle<10000)$fatal(1,"SDRAM200us power-up wait omitted");
    for(b=0;b<4;b=b+1)if(a[10] || b==ba)begin
     if(opened[b] && cycle-last_write[b]<1)$fatal(1,"tWR violation");
     opened[b]=0;precharged[b]=cycle;close_due[b]=-1;
    end
   end
   3'b001:begin // AUTO REFRESH
    if(opened!=0)$fatal(1,"REFRESH with open bank");
    if(refreshes && cycle-last_refresh<4)$fatal(1,"tRFC violation");
    last_refresh=cycle;refreshes=refreshes+1;if(!initialized)init_refreshes=init_refreshes+1;
   end
   3'b000:begin // MODE REGISTER SET
    if(init_refreshes<8)$fatal(1,"Fewer than8 init refreshes");
    if(a[2:0]!=0 || a[6:4]!=2)$fatal(1,"Model expects BL1 CL2");
    mode_cycle=cycle;initialized=1;
   end
   default:;
  endcase
 end
endmodule
