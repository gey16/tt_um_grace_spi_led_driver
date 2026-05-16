/*
 * tb.v — Verilog testbench wrapper to enable cocotb
 *
 * Role of tb.v vs test.py:
 *
 *   Icarus Verilog compiles:  tb.v + your .sv files  →  simulation binary
 *                                        ↑
 *   cocotb attaches to the simulation and runs:  test.py
 *                                        ↓
 *   test.py drives dut.clk, dut.uio_in, etc. → tb.v wires → your RTL
 *
 * tb.v  = thin Verilog shim: instantiates your top-level module, exposes wires,
 *         sets up VCD dump. cocotb cannot instantiate SV modules directly.
 * test.py = Python test driver: bit-bangs SPI, awaits clock cycles, asserts.
 */

// *** Compiler Directives *** //
`default_nettype none       // undeclared wire names trigger compiler error
`timescale 1ns / 1ps        // 1ns = time unit (#10 in verilog = 10nS)
                            // 1ps = precision (smallest time step simulator tracks)

module tb ();

// *** Setup Code  *** //
// VCD = Value Change Dumps --> what you open in Surfer to see waveforms 
// Create a file called "tb.vcd" and write all signal changes to it
initial begin
    $dumpfile("tb.vcd");
    $dumpvars(0, tb);       // depth = 0 --> record everything 
                            // tb = start from tb module (my testbench)
    #1;                     // wait 1 time unit (1nS) before starting test 
end

// *** Inputs/Outputs  *** //
// Verilog (.v) Convention
// reg = input to chip
// wire = outputs from chip 
// NOTE: in SystemVerilog, logic can be used for both reg/wire
reg clk;    
reg rst_n;
reg ena;
reg [7:0] ui_in;
reg [7:0] uio_in;
wire [7:0] uo_out;
wire [7:0] uio_out;
wire [7:0] uio_oe;

// Power Port Signals 
// if compiler flag "GL_TEST" defined ...
// connect power port VPWR to voltage HIGH
 // connect ground port to GND
`ifdef GL_TEST
  wire VPWR = 1'b1;
  wire VGND = 1'b0;
`endif

// *** Instantiate Module  *** //
tt_um_grace_spi_led_driver user_project (

// Include power ports for the Gate Level test:
`ifdef GL_TEST
      .VPWR(VPWR),
      .VGND(VGND),
`endif

    // Digital Input/Output Signals 
    .clk     (clk),         // system clk - 50 MHz
    .rst_n   (rst_n),       // system RESET
    .ena     (ena),         // chip enable
    .ui_in   (ui_in),       // dedicated input signals
    .uo_out  (uo_out),      // dedicated output signals
    .uio_in  (uio_in),      // bi-directional IOs: Input Path
    .uio_out (uio_out),     // bi-directional IOs: Output Path (chip drives out)
    .uio_oe  (uio_oe)       // bi-directional IOs: Enable path (enable = 1)

);

endmodule
