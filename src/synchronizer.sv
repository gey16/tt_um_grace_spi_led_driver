/*
 * synchronizer.sv
 * Synchronize input signals 
 * Grace Eysenbach
 */

// synchronizer --> 2x reclocking (FF) instances chained together. 
// GOAL: synchronize the signals coming out of Master with 2x Flip Flops to avoid metastablity
module synchronizer #(parameter int STAGES = 2, parameter int WIDTH = 4) (rst_n, clk, ena, data_in, data_out);

  input logic rst_n;                  // TT global reset signal
  input logic clk;                    // TT main system clock - 50 MHz
  input logic ena;                    // TT chip enable signal 
  input logic [WIDTH-1:0] data_in;    // (async) input signal from Master 
  output logic [WIDTH-1:0] data_out;  // synchronized input signal from Master

  logic [WIDTH-1:0] data_sync [STAGES+1];   // array of WIDTH-bit x "STAGES+1" registers

  assign data_sync[0] = data_in;            // place async data into first register

  generate
    // Generate 2 flip-flop stages gen_reclocking[0] and gen_reclocking[1]
    // Output of FF1 feeds into FF2 
    for (genvar i=0; i<STAGES; i++) begin : gen_reclocking
      reclocking #(.WIDTH(WIDTH)) reclocking_i0  // instantiate reclocking module labeled "reclocking_i0"
      // pass in input (async) data and output data once it's been clocked into the FF
      (.rst_n(rst_n), .clk(clk), .ena(ena), .data_in(data_sync[i]), .data_out(data_sync[i+1]));
    end
  endgenerate
  
  // Output of final FF stage -- now synchronized 
  assign data_out = data_sync[STAGES];

endmodule
