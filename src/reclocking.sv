/*
 * reclocking.sv
 * Reclocking = capturing a signal into new clock domain. 1x FF
 * Grace Eysenbach
 */

// reclocking --> one Flip-Flop. On system clock rising edge, captures whatever is on the wire. 
// WIDTH default = 4. Actual width is set by when module is instantiated. 
module reclocking #(parameter int WIDTH = 4) (rst_n, clk, ena, data_in, data_out);

  input logic rst_n;
  input logic clk;
  input logic ena;
  input logic [WIDTH-1:0] data_in;

  output logic [WIDTH-1:0] data_out;

  logic [WIDTH-1:0] data_sync;

  // On the rising edge of system clock ... 
  always_ff @(negedge(rst_n) or posedge(clk)) begin
    // If reset asserted, "zero-out" data_sync
    if (!rst_n) begin
      data_sync <= '0;
    end 
    // Else, place async input data into WIDTH-bit data_sync register
    else begin
      if (ena == 1'b1) begin
        data_sync <= data_in;
      end
    end
  end

  // sync input data is placed into data_out (sync input signal)
  assign data_out = data_sync;

endmodule
