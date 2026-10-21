package sram_test_pkg;
 function automatic [31:0] sat_inc(input [31:0] n);sat_inc=&n?n:n+1'b1;endfunction
 function automatic [15:0] prbs_next(input [15:0] x);prbs_next={x[14:0],x[15]^x[13]^x[12]^x[10]};endfunction
 function automatic [15:0] pattern_data(input [3:0] p,input [17:0] a,input [15:0] lfsr);
  case(p)
   0:pattern_data=0;1:pattern_data=16'hffff;2:pattern_data=16'haaaa;3:pattern_data=16'h5555;
   4:pattern_data=16'h1<<a[3:0];5:pattern_data=~(16'h1<<a[3:0]);
   6:pattern_data=a[15:0];7:pattern_data=~a[15:0];default:pattern_data=lfsr;
  endcase
 endfunction
endpackage
