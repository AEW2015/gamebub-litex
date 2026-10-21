`timescale 1ns/1ps
// Always-on, native-app subset of the production HandheldTop host interface.
// Pin protocol: mode 0, DQ0 command, 1/2/4-lane address/data, eight dummy
// BYTES on reads, MSB first, optional per-word byte reversal. clk200 must
// remain 200 MHz regardless of app/SDRAM settings. Validated digital rates:
// writes <=40 MHz, reads <=16 MHz; external pin margins require signoff.
// No external-memory or game-core emulation. Unknown reads return zero;
// unknown writes have no effect. Overlay memory is a separate consumer.
module esp32_v102_endpoint (
 input wire clk200, rst_n,
 input wire qspi_sck, qspi_cs_n,
 input wire [3:0] qspi_dq_i,
 output wire [3:0] dq_o, dq_oe,
 input wire [11:0] buttons_native,
 input wire vblank,
 output wire irq_request,
 output reg [3:0] control,
 output wire [11:0] force_buttons_native,
 output reg display_external, color_correct_enable,
 output reg [23:0] overlay_xctrl, overlay_yctrl,
 output reg ov_wr,
 output reg [17:0] ov_addr,
 output reg [15:0] ov_data,
 output reg mailbox_wr,
 output reg [13:0] mailbox_addr,
 output reg [31:0] mailbox_wdata,
 input wire [31:0] mailbox_rdata,
 input wire [4:0] diag_select,
 input wire inject_toggle,
 output reg [31:0] diag_data
);
 localparam IDLE=0, COMMAND=1, ADDRESS=2, WRITE=3, DUMMY=4, READ=5, INVALID=6;
 (* ASYNC_REG="TRUE" *) reg [1:0] sck_sync,cs_sync;
 (* ASYNC_REG="TRUE" *) reg [3:0] dq_meta,dq_sync;
 (* ASYNC_REG="TRUE" *) reg [11:0] buttons_meta,buttons_sync;
 (* ASYNC_REG="TRUE" *) reg [1:0] vblank_sync;
 reg prev_sck,prev_cs,prev_vblank;
 reg [11:0] prev_buttons;
 reg [2:0] warmup,state;
 reg seen_idle,tx_active;
 reg [7:0] command;
 reg [31:0] shift_in,address,shift_out,read_prefetch;
 reg [4:0] read_select;
 reg service_wr_pending;
 reg mailbox_addr_inc_pending;
 reg [13:0] mailbox_addr_plus_word;
 reg [15:0] service_wr_addr;
 reg [31:0] service_wr_data;
 reg [6:0] bits_left,tx_left;
 reg [11:0] forced;
 reg [3:0] irq_enable,irq_flags;
 reg inject_previous;
 reg [31:0] transactions,reads,writes,acks,button_reads,pending_reads,overlay_words;
 reg [31:0] last_address,last_write,last_read,heartbeat,button_events,injected_events;
 always @* begin
  case(diag_select)
   0:diag_data=32'h56313032; // V102 smoke identity, not official framework version
   1:diag_data=heartbeat;
   2:diag_data=transactions;
   3:diag_data=reads;
   4:diag_data=writes;
   5:diag_data=acks;
   6:diag_data=button_reads;
   7:diag_data=pending_reads;
   8:diag_data=overlay_words;
   9:diag_data=last_address;
   10:diag_data=last_write;
   11:diag_data=last_read;
   12:diag_data={19'b0,irq_request,irq_flags,irq_enable,physical_host[3:0]};
   13:diag_data={20'b0,physical_host};
   14:diag_data=button_events;
   15:diag_data=injected_events;
   default:diag_data=0;
  endcase
 end
 wire rise=sck_sync[1]&&!prev_sck;
 wire fall=!sck_sync[1]&&prev_sck;
 wire [2:0] lanes=(state==COMMAND) ? 3'd1:
                         command[6:5]==2'd2 ? 3'd4:command[6:5]==2'd1 ? 3'd2:3'd1;
 wire [5:0] word_bits=command[2:1]==2'd2 ? 6'd32:command[2:1]==2'd1 ? 6'd16:6'd8;
 wire [2:0] word_bytes=command[2:1]==2'd2 ? 3'd4:command[2:1]==2'd1 ? 3'd2:3'd1;
 wire [31:0] incoming=(shift_in<<lanes) |
                (lanes==4 ? {28'b0,dq_sync}:lanes==2 ? {30'b0,dq_sync[1:0]}:{31'b0,dq_sync[0]});
 // The native tester mapping is A,B,X,Y,Up,Down,Left,Right,L,R,Start,Select.
 wire [11:0] physical_host={buttons_sync[0],buttons_sync[1],buttons_sync[2],buttons_sync[3],
                           buttons_sync[4],buttons_sync[5],buttons_sync[6],buttons_sync[7],
                           buttons_sync[8],buttons_sync[9],buttons_sync[10],buttons_sync[11]};
 genvar k;
 generate for(k=0;k<12;k=k+1) begin: force_map
   assign force_buttons_native[k]=forced[11-k];
 end endgenerate
 assign irq_request=|(irq_enable&irq_flags);
 // Deassert ownership immediately on raw CS, including while synchronizers
 // still contain an old selected transaction. DQ1 is MISO in single mode.
 assign dq_oe=(!rst_n || qspi_cs_n || !tx_active) ? 4'b0:
               command[6:5]==2'd2 ? 4'b1111:command[6:5]==2'd1 ? 4'b0011:4'b0010;
 wire [31:0] aligned_out=command[2:1]==2'd2 ? shift_out:
                        command[2:1]==2'd1 ? {shift_out[15:0],16'b0}:{shift_out[7:0],24'b0};
 assign dq_o=command[6:5]==2'd2 ? aligned_out[31:28]:
             command[6:5]==2'd1 ? {2'b0,aligned_out[31:30]}:{2'b0,aligned_out[31],1'b0};
 function automatic [31:0] swap_word(input [31:0] d,input [1:0] size,input swap);
 begin
   case(size)
    0: swap_word={24'b0,d[7:0]};
    1: swap_word=swap ? {16'b0,d[7:0],d[15:8]}:{16'b0,d[15:0]};
    default:swap_word=swap ? {d[7:0],d[15:8],d[23:16],d[31:24]}:d;
   endcase
 end endfunction
 reg [4:0] next_read_select;
 reg [31:0] read_data;
 // Capture the completed QSPI address directly.  Keeping the BRAM address
 // registered avoids a long combinational path from the protocol state.  A
 // burst-write increment is delayed one clk200 cycle so the mailbox observes
 // the completed word's address while mailbox_wr is asserted.
 // Split address decoding from the data mux.  Read transactions provide 64
 // dummy bits, and burst addresses remain stable for an entire word, so this
 // registered predecode is complete well before shift_out consumes the data.
 always @* begin
   next_read_select=0;
   if(address[31:16]==16'hF100) case(address[15:0])
    16'h0000:next_read_select=5'd2;
    16'h0004:next_read_select=5'd3;
    16'h1000:next_read_select=5'd5;
    16'h1004:next_read_select=5'd6;
    16'h1008:next_read_select=5'd4;
    16'h100c:next_read_select=5'd7;
    16'h2000:next_read_select=5'd8;
    16'h0100:next_read_select=5'd11;
    16'h0104:next_read_select=5'd12;
    default:next_read_select=0;
   endcase
 end
 always @* begin
   case(read_select)
    1:read_data=mailbox_rdata;
    2:read_data=0; // Diagnostic endpoint does not claim complete framework ABI.
    3:read_data=32'd200000000;
    4:read_data={20'b0,forced};
    5:read_data={28'b0,irq_enable};
    6:read_data={28'b0,irq_flags};
    7:read_data={31'b0,display_external};
    8:read_data={20'b0,physical_host};
    9:read_data={8'b0,overlay_xctrl};
    10:read_data={8'b0,overlay_yctrl};
    11:read_data={16'd240,16'd360}; // Firmware overlay geometry; no LCD in smoke image.
    12:read_data=16;
    default:read_data=0;
   endcase
 end
 wire [31:0] write_data=swap_word(incoming,command[2:1],command[3]);
 always @(posedge clk200) begin
  if(!rst_n) begin
   inject_previous<=0;transactions<=0;reads<=0;writes<=0;acks<=0;
   button_reads<=0;pending_reads<=0;overlay_words<=0;last_address<=0;
   last_write<=0;last_read<=0;heartbeat<=0;button_events<=0;injected_events<=0;
   sck_sync<=0;cs_sync<=3;dq_meta<=0;dq_sync<=0;
   buttons_meta<=0;buttons_sync<=0;vblank_sync<=0;
   prev_sck<=0;prev_cs<=1;prev_vblank<=0;prev_buttons<=0;
   warmup<=0;seen_idle<=0;tx_active<=0;state<=IDLE;command<=0;
   shift_in<=0;shift_out<=0;read_prefetch<=0;read_select<=0;address<=0;bits_left<=0;tx_left<=0;
   service_wr_pending<=0;service_wr_addr<=0;service_wr_data<=0;
   mailbox_addr<=0;mailbox_addr_inc_pending<=0;mailbox_addr_plus_word<=0;
   // JTAG image must start without an ESP32 core-load/enable transaction.
   control<=4'b0011;forced<=0;irq_enable<=4'b0010;irq_flags<=0;
   display_external<=0;color_correct_enable<=0;
   overlay_xctrl<=0;overlay_yctrl<=0;ov_wr<=0;ov_addr<=0;ov_data<=0;mailbox_wr<=0;mailbox_wdata<=0;
  end else begin
   heartbeat<=heartbeat+1;
   inject_previous<=inject_toggle;
   sck_sync<={sck_sync[0],qspi_sck};cs_sync<={cs_sync[0],qspi_cs_n};
   dq_meta<=qspi_dq_i;dq_sync<=dq_meta;
   buttons_meta<=buttons_native;buttons_sync<=buttons_meta;
   vblank_sync<={vblank_sync[0],vblank};
   prev_sck<=sck_sync[1];prev_cs<=cs_sync[1];
   prev_buttons<=buttons_sync;prev_vblank<=vblank_sync[1];
   ov_wr<=0;mailbox_wr<=0;service_wr_pending<=0;
   // Keep the burst-address adder off the state/decode control cone.  The
   // QSPI word interval gives this continuously registered sum ample time to
   // settle before the deferred commit below.
   mailbox_addr_plus_word<=mailbox_addr+word_bytes;
   if(mailbox_addr_inc_pending) begin
    mailbox_addr<=mailbox_addr_plus_word;
    mailbox_addr_inc_pending<=0;
   end
   // Read addresses are stable for the eight dummy bytes and for the entire
   // preceding burst word.  Prefetching removes address decode, mailbox mux,
   // and byte swapping from the shift-register load cycle.
   read_select<=next_read_select;
   read_prefetch<=read_data;
   if(service_wr_pending) begin
    case(service_wr_addr)
     16'h1008:forced<=service_wr_data[11:0];
     16'h100c:display_external<=service_wr_data[0];
     16'h1000:irq_enable<=service_wr_data[3:0];
     16'h1004:begin irq_flags<=irq_flags&~service_wr_data[3:0];acks<=acks+1;end
     default:begin end
    endcase
   end
   if(warmup!=7) warmup<=warmup+1'b1;
   if(warmup==7 && cs_sync[1]) seen_idle<=1;
   if(cs_sync[1]) begin state<=IDLE;shift_out<=0;tx_active<=0;end
   else if(seen_idle && prev_cs) begin
    state<=COMMAND;bits_left<=8;shift_in<=0;shift_out<=0;command<=0;tx_active<=0;
   end else if(seen_idle) begin
    if(rise) begin
     case(state)
      COMMAND:begin
       shift_in<=incoming;bits_left<=bits_left-1'b1;
       if(bits_left==1) begin
        command<=incoming[7:0];shift_in<=0;bits_left<=32;
        state<=(incoming[7]||incoming[6:5]==3||incoming[2:1]==3) ? INVALID:ADDRESS;
       end
      end
      ADDRESS:begin
       shift_in<=incoming;bits_left<=bits_left-lanes;
       if(bits_left==lanes) begin
         transactions<=transactions+1;last_address<=incoming;
         address<=incoming;mailbox_addr<=incoming[13:0];
         mailbox_addr_inc_pending<=0;shift_in<=0;tx_left<=0;
        state<=command[0] ? DUMMY:WRITE;
        bits_left<=command[0] ? 7'd64:{1'b0,word_bits};
       end
      end
      DUMMY:begin
       bits_left<=bits_left-lanes;
       if(bits_left==lanes) begin state<=READ;tx_left<=0;end
      end
      WRITE:begin
       shift_in<=incoming;bits_left<=bits_left-lanes;
       if(bits_left==lanes) begin
        writes<=writes+1;last_write<=write_data;
        shift_in<=0;bits_left<={1'b0,word_bits};
         if(command[4]) address<=address+word_bytes;
         if(address[31:14]==18'h00440) begin
          mailbox_wr<=1;mailbox_wdata<=write_data;
          if(command[4]) mailbox_addr_inc_pending<=1;
         end
        else if(address[31:16]==16'hF100) begin
         service_wr_pending<=1;service_wr_addr<=address[15:0];service_wr_data<=write_data;
        end
        if(address[31:24]==8'hF2 && address[23:18]==0) begin
         overlay_words<=overlay_words+1;
         ov_wr<=1;ov_addr<=address[17:0];ov_data<=write_data[15:0];
        end
       end
      end
      default:begin end
     endcase
    end
    if(fall && (state==DUMMY || state==READ)) tx_active<=1;
    if(fall && state==READ) begin
     if(tx_left==0) begin
      reads<=reads+1;last_read<=read_prefetch;
      if(address==32'hF1002000)button_reads<=button_reads+1;
      if(address==32'hF1001004)pending_reads<=pending_reads+1;
      shift_out<=swap_word(read_prefetch,command[2:1],command[3]);
      tx_left<={1'b0,word_bits}-lanes;
       if(command[4]) begin
        address<=address+word_bytes;
        // Defer the mailbox increment one clk200 cycle.  This keeps the
        // tx_left boundary detector off the address-adder critical path;
        // the next QSPI word is still many clk200 cycles away.
        mailbox_addr_inc_pending<=1;
       end
     end else begin shift_out<=shift_out<<lanes;tx_left<=tx_left-lanes;end
    end
   end
   // New events win over a simultaneous W1C acknowledgment, as upstream.
   if(buttons_sync!=prev_buttons)begin irq_flags[1]<=1;button_events<=button_events+1;end
   if(inject_toggle!=inject_previous)begin irq_flags[1]<=1;injected_events<=injected_events+1;end
   if(vblank_sync[1]&&!prev_vblank) irq_flags[0]<=1;
  end
 end
endmodule
