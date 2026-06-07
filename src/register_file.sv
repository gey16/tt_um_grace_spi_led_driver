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
input logic reg_data_o_dv,              // pulses HIGH to indicate reg file should store reg_data_o at reg_addr
                                        // reg_data_o, data going to reg_file is "data valid" (dv)
input logic reg_data_i_dv               // pulses HIGH to indicate read ongoing (data going from registers to MISO)
);

// Internal Signals 
// Define 16x 8-bit registers 
logic [REG_W-1:0] registers [0:15];     // 16 registers, each of width 7:0 (8-bits)
logic [7:0] status;     // 8b status register including "last_op_was_write" and "enable" bits
// LED Brightness signals 
logic global_en;
logic [7:0] pwm_counter;    
logic [15:0] prescalar_cnt;
logic [3:0] prescalar_val;

// Register Logic
// At the falling edge of reset (reset asserted) or rising edge of the clock ...
always_ff @(negedge(rst_n) or posedge(clk)) begin

    // If reset asserted, set all registers to 0
    if (!rst_n) begin
        for (int i = 0; i < 16; i++) begin
            registers[i] <= '0;
        end
        status[7:0] <= '0;
        registers[8] <= 8'h80;      // Default CTRL register value is 0x80
    end 
    
    // Else if our chip is selected (ena = 1)...
    else begin 
        if (ena == 1'b1) begin  
            // Status 0-bit mirrors Global Enable 
            // Remaining bits assigned to 0
            status[0] <= registers[8][0];
            status[7:2] <= '0; 

            // If data in reg_data_o is valid, clock into register at decoded addr
            if (reg_data_o_dv == 1'b1) begin 
                status[1] <= 1'b1;
                // Only write to registers 0x0-0x8 [write protection]
                if (reg_addr < 4'h9) begin
                    registers[reg_addr] <= reg_data_o;
                end
            end  
            else if (reg_data_i_dv == 1'b1) begin
                status[1] <= 1'b0;
            end
        end
    end
end

// Control LED Brightness 
always_ff @(negedge(rst_n) or posedge(clk)) begin
    
    // If reset asserted, set all led control values to 0
    if (!rst_n) begin
        pwm_counter <= '0;
        prescalar_cnt <= '0;
    end 
    
    // Else if our chip is selected (ena = 1)...
    else begin 
        if (ena == 1'b1) begin
            // Increment Clock Counts (0 --> 2^prescalar -1)
            if (prescalar_cnt < ((16'h1 << prescalar_val) - 1)) begin
                prescalar_cnt <= prescalar_cnt + 1;  
            end
            // Reset prescalar_cnt and tick pwm_counter every 2^prescalar_val clock cycles
            else begin
                prescalar_cnt <= '0;
                pwm_counter <= pwm_counter + 1;
            end
        end
    end
end

// Master Read: return contents of register from requested reg_addr
always_comb begin
    case (reg_addr)
        4'h9: reg_data_i = 8'hA5;   // ID hard-coded to 0xA5
        4'hA: reg_data_i = 8'h1;    // Version hard-coded to 0x01
        4'hB: reg_data_i = status[7:0];         // STATUS Registewer. bit0 = Global Enable. bit1 = LAST_OP_WAS_WRITE
        4'hC: reg_data_i = pwm_counter;         // COUNTER Register. Contains current value of pwm counter.
        default: reg_data_i = registers[reg_addr];  // default = read from actual registers
    endcase
end



// Update LED Settings 
// each led 7:0 mapped to its corresponding register
// each led on when ENABLE=1 and pwm_counter < BRIGHT_i (PWM duty cycle)
// EXCEPT: 0xFF = always on, 0x00 = always off
// Enable signal = bit 0 of CTRL register (#8)
assign prescalar_val = registers[8][7:4];
assign global_en = registers[8][0];
always_comb begin
    for (int i = 0; i < 8; i++) begin
        // If LED fully on (0xFF), set output equal to Global Enable 
        if (registers[i] == 8'hFF) begin
            uo_out[i] = global_en;
        end
        else begin
            uo_out[i] = global_en && (pwm_counter < registers[i]);
        end
    end
end

endmodule
