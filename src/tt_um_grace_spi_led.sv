/*
 * tt_um_grace_spi_led.sv
 * Top-Level chip defintion
 * Grace Eysenbach
 */

 module tt_um_grace_spi_led (
    input  wire [7:0] ui_in,        // TT 8x input-only pins
    output wire [7:0] uo_out,       // TT 8x output-only pins --> drive LEDs
    input  wire [7:0] uio_in,       // TT 8x input pins
    output wire [7:0] uio_out,      // TT 8x output pins (only active when uio_oe = 1)
    output wire [7:0] uio_oe,       // TT output enable pin 
    input  wire       ena,          // TT chip enable pin
    input  wire       clk,          // TT main clock - 50 MHz
    input  wire       rst_n         // TT system reset signal 
 );

    // Bi direction IOs 0,1,3 as inputs 
    // CS, MOSI, SPI_CLK
    assign uio_oe[1:0] = 2'b00;
    assign uio_oe[3] = 1'b0;

    // Bi direction IOs [2] as output
    // MISO
    assign uio_oe[2]   = 1'b1;

    // Unused signals needs to be assigned to 0.
    assign uio_out[1:0] = 2'b00;
    assign uio_out[7:3] = 5'b00000;
    assign uio_oe[7:4]  = 4'b0000;

    // SPI Signals
    wire spi_cs_n;
    wire spi_clk;
    wire spi_miso;
    wire spi_mosi;

    // SPI port assignments
    assign spi_cs_n    = uio_in[0];
    assign spi_mosi    = uio_in[1];
    assign spi_clk     = uio_in[3];
    assign uio_out[2]  = spi_miso;

    // Synchronized signals (2x FF)
    // 3x signals coming in from master 
    wire spi_cs_n_sync;
    wire spi_clk_sync;
    wire spi_mosi_sync;

    // Number of stages in each synchronizer
    localparam int SYNC_STAGES = 2;     // 2x flip flops
    localparam int SYNC_WIDTH = 1;      // SPI = 1-wire, only need 1bit

    // Synchronizers
    // CS, MOSI, SPI_CLK
    synchronizer #(.STAGES(SYNC_STAGES), .WIDTH(SYNC_WIDTH)) synchronizer_spi_cs_n_inst (.rst_n(rst_n), .clk(clk), .ena(ena), .data_in(spi_cs_n), .data_out(spi_cs_n_sync));
    synchronizer #(.STAGES(SYNC_STAGES), .WIDTH(SYNC_WIDTH)) synchronizer_spi_clk_inst  (.rst_n(rst_n), .clk(clk), .ena(ena), .data_in(spi_clk),  .data_out(spi_clk_sync));
    synchronizer #(.STAGES(SYNC_STAGES), .WIDTH(SYNC_WIDTH)) synchronizer_spi_mosi_inst (.rst_n(rst_n), .clk(clk), .ena(ena), .data_in(spi_mosi), .data_out(spi_mosi_sync));

    // ********************* //
    // Module Instantiations //
    // ********************* // 

    // Register Wires
    logic [3:0] reg_addr;
    logic [7:0] reg_data_i;
    logic [7:0] reg_data_o;
    logic reg_data_o_dv;
    // logic [7:0] status; // TODO: implement status register

    // SPI Wrapper
    spi_peripheral spi_peripheral_1 (
        .rst_n(rst_n), .clk(clk), .ena(ena), 
        .spi_cs_n(spi_cs_n_sync), .spi_clk(spi_clk_sync), .spi_mosi(spi_mosi_sync), .spi_miso(spi_miso),
        .reg_addr(reg_addr), .reg_data_i(reg_data_i), .reg_data_o(reg_data_o), .reg_data_o_dv(reg_data_o_dv),
        .status(8'b0)  // TODO: implement status register
    );

    register_file register_file_1(
        .rst_n(rst_n), .clk(clk), .ena(ena), 
        .reg_addr(reg_addr), .reg_data_i(reg_data_i), .reg_data_o(reg_data_o), .reg_data_o_dv(reg_data_o_dv),
        .uo_out(uo_out)
    );

 endmodule