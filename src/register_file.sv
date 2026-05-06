/*
 * register_file.sv
 * Chip Register File
 * Grace Eysenbach
 */

module register_file #(
    // Parameters
    parameter int ADDR_W = 4,   // 4b address, supports 16 registers (0x0-0xF)
    parameter int REG_W = 8     // register width = 8b 
) (
// TT Signals 
input logic clk,            // main TT 50 MHz system clock
input logic rst_n,          // reset signal (default = 1, run normally)
input logic ena,            // TT enable signal, used to "select" your design (1 = chip selected)
output logic [7:0] uo_out,   // TT output signals 7:0 are mapped to LEDs

// Register R/W Signals 
input logic [ADDR_W-1:0] reg_addr,      // decoded register addr for r/w
output logic [REG_W-1:0] reg_data_i,    // data coming out from register file into spi_peripheral.sv (Master Read)
input logic [REG_W-1:0] reg_data_o,     // data going into register file from spi_peripheral.sv (Master Write)
input logic reg_data_o_dv               // pulses HIGH to indicate reg file should store reg_data_o at reg_addr
                                        // reg_data_o, data going to reg_file is "data valid" (dv)

// TODO: Status Register 
// output logic [7:0] status    // 8b status register including "last_op_was_write" and "enable" bits
);

// Internal Signals 
// Define 16x 8-bit registers 
logic [REG_W-1:0] registers [0:15];     // 16 registers, each of width 7:0 (8-bits)

// Register Logic
// At the falling edge of reset (reset asserted) or rising edge of the clock ...
always_ff @(negedge(rst_n) or posedge(clk)) begin
    // If reset asserted, set all registers to 0
    if (!rst_n) begin
        for (int i = 0; i < 16; i++) begin
            registers[i] <= '0;
        end
    end 
    // Else if our chip is selected (ena = 1)...
    else begin 
        if (ena == 1'b1) begin  
            // If data in reg_data_o is valid, clock into register at decoded addr
            if (reg_data_o_dv == 1'b1) begin 
                registers[reg_addr] <= reg_data_o;
            end  
        end
    end
end

// Master Read: return contents of register from requested reg_addr 
assign reg_data_i = registers[reg_addr];

// Update LED Settings 
// each led 7:0 mapped to bit 7 of its corresponding register
// Enable signal = bit 0 of CTRL register (#8)
assign uo_out[0] = registers[8][0] && registers[0][7];
assign uo_out[1] = registers[8][0] && registers[1][7];
assign uo_out[2] = registers[8][0] && registers[2][7];
assign uo_out[3] = registers[8][0] && registers[3][7];
assign uo_out[4] = registers[8][0] && registers[4][7];
assign uo_out[5] = registers[8][0] && registers[5][7];
assign uo_out[6] = registers[8][0] && registers[6][7];
assign uo_out[7] = registers[8][0] && registers[7][7];

endmodule
