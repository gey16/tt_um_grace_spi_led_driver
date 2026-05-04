/*
 * falling_edge_detector.sv
 * Falling Edge Detector
 * Grace Eysenbach
 */

module falling_edge_detector (rst_n, clk, ena, data, neg_edge);

  input logic rst_n;        // universal chip reset
  input logic clk;          // main system clock - 50MHz
  input logic ena;          // enable = 1, selected this TT chip
  input logic data;         // generic input signal we sample (the falling edge we care about)

  output logic neg_edge;    // output signal (pulse high on each falling edge)

  logic data_delayed;       // state of input signal, 1 clock cycle delayed

  // If reset is asserted or system clock rising edge... 
  always_ff @(negedge(rst_n) or posedge(clk)) begin
    // if reset asserted, 0-out delayed data
    if (!rst_n) begin
      data_delayed <= '0;
    end 
    // else if this chip selected ...
    else begin
      if (ena == 1'b1) begin
        // on every system clock rising edge data_delayed set equal to state of input signal (data)
        data_delayed <= data;
      end
    end
  end

  // output signal will always be 0, unless theres a falling edge change of input signal value between 2 clock cycles 
  // falling edge: data_delayed = 1, data = 0 --> neg_edge = 1&1 = 1
  assign neg_edge = (!data) & data_delayed;

endmodule
