/*
 * spi_peripheral.sv
 * SPI peripheral FSM — CPOL=0, CPHA=0 only
 * Grace Eysenbach
 *
 * SPI packet format (16 bits total, MSB first):
 *
 *   Byte 1 — address phase (8 bits, STATE_ADDR):
 *   ┌───────┬───────────────────┬───────────────────┐
 *   │ bit 7 │   bits 6-4        │   bits 3-0        │
 *   │  R/W  │  don't care (×3)  │   reg addr [3:0]  │
 *   │  1=wr │   (ignored)       │   (0x0 – 0xF)     │
 *   └───────┴───────────────────┴───────────────────┘
 *
 *   Byte 2 — data phase (8 bits, STATE_RX_DATA or STATE_TX_DATA):
 *   ┌─────────────────────────────────────────────────┐
 *   │                  bits 7-0                       │
 *   │                 data [7:0]                      │
 *   │   (written to reg on write; read from reg file) │
 *   └─────────────────────────────────────────────────┘
 *
 *   CS (spi_cs_n) stays LOW for the entire 16-bit transaction.
 *   Data is sampled on the rising edge of spi_clk (CPHA=0).
 */

module spi_peripheral #(
    // Parameters
    parameter int ADDR_W = 4,   // 4b address, supports 16 registers (0x0-0xF)
    parameter int REG_W = 8     // register width = 8b 
)(
    // Input/Output Ports 
    input logic clk,            // main TT 50 MHz system clock
    input logic rst_n,          // reset signal (default = 1, run normally)
    input logic ena,            // TT enable signal, used to "select" your design (1 = chip selected)
    input logic spi_mosi,       // Master-Out, Slave-In (Master Write)
    output logic spi_miso,      // Master-In, Slave-Out (Master Read)
    input logic spi_clk,        // SPI clock from master (RP2040)
    input logic spi_cs_n,       // SPI "chip select" signal for initiating SPI R/W
    output logic [ADDR_W-1:0] reg_addr,     // decoded register addr for r/w
    input logic [REG_W-1:0] reg_data_i,     // data coming in from register file (Master Read)
    output logic [REG_W-1:0] reg_data_o,    // data going out to the register file (Master Write)
    output logic reg_data_o_dv,     // pulses HIGH to indicate reg file should store reg_data_o at reg_addr
                                    // reg_data_o, data going to reg_file is "data valid" (dv)
    input logic [7:0] status    // 8b status register including "last_op_was_write" and "enable" bits
);
    // Edge Detectors (sof/eof)

    // Start of Frame (sof) = Falling edge (negedge) of chip select (spi_cs_n)
    logic sof;
    // Pulse to indicate start of frame (sof logic signal)
    // When "chip select" goes low, it indicates master is initiating a transaction to the slave
    falling_edge_detector falling_edge_detector_sof (
        .rst_n(rst_n), .clk(clk), .ena(ena), 
        .data(spi_cs_n), .neg_edge(sof));

    // Pulse to indicate end of frame (eof logic signal)
    // When "chip select" goes high, it indicates master is done transacting with slave
    logic eof;
    rising_edge_detector rising_edge_detector_eof (
        .rst_n(rst_n), .clk(clk), .ena(ena), 
        .data(spi_cs_n), .pos_edge(eof));
    
    // Pulse for 1 clk cycle on the rising edge of SPI clock 
    // Indicates FSM to sample MOSI exactly once
    logic spi_clk_pos;  // spi clock HIGH pulse = rising edge of spi_clk
    rising_edge_detector rising_edge_detector_spi_clk (
        .rst_n(rst_n), .clk(clk), .ena(ena), 
        .data(spi_clk), .pos_edge(spi_clk_pos)
    );

    // Pulse for 1 clk cycle on the falling edge of SPI clock 
    logic spi_clk_neg;  // spi clock LOW pulse = falling edge of spi_clk
    falling_edge_detector falling_edge_detector_spi_clk (
        .rst_n(rst_n), .clk(clk), .ena(ena), 
        .data(spi_clk), .neg_edge(spi_clk_neg)
    );

    // FSM state definitions
    typedef enum logic [1:0] {
        STATE_IDLE, STATE_ADDR, STATE_RX_DATA, STATE_TX_DATA
    } fsm_state;

    fsm_state state, next_state;

    // State Register Transition
    // At the falling edge of reset (reset asserted) or rising edge of the clock ...
    always_ff @(negedge(rst_n) or posedge(clk)) begin
        // If reset asserted ... return to IDLE 
        if (!rst_n) begin
            state <= STATE_IDLE;
        end 
        // Else if our chip is selected (ena = 1) move to "next state"
        else begin 
            if (ena == 1'b1) begin  
                state <= next_state;
            end
        end
    end

    // Internal signals
    logic [REG_W-1:0] rx_buffer;        // 8b buffer for storing recieved bits from Master 
    logic [3:0] rx_buffer_counter;      // track how many bits recieved on MOSI
    logic reg_rw;                       // detemine if master write vs. read

    // Sample addr and data 
    // Control signals 
    logic tx_buffer_load;   // pulse high = load register file's read data into tx register so we can send over MISO (Master Read)
    logic sample_addr;      // pulse high = address bits in rx_buffer are ready to be latched into reg_addr
    logic sample_data;      // pulse high = data bits in rx_buffer are ready to be latched into reg_data_o

    // Next State Logic
    // always_comb = updates instantly whenever inputs change (no clk)
    // given current state + current input signals... what should next state be
    always_comb begin 
        // Default settings -- initialize all control signals to 0
        next_state = state;
        tx_buffer_load = 1'b0;
        sample_addr = 1'b0;
        sample_data = 1'b0;

        case (state)

            // Idle, default state
            STATE_IDLE : begin
                // If "start of frame" is HIGH (1) then next state is ADDR
                // sof = 1-cycle pulse when CS goes low; indicates start of transaction
                if (sof == 1'b1) begin
                    next_state = STATE_ADDR;
                end
            end 

            // Determine reg address, and whether cmd is master read/write
            STATE_ADDR : begin
                // If the rx buffer counter is at 8... (means 8 bits have been clocked in)
                // 4'd8 = 4bit number with value 8 (1000) 
                if (rx_buffer_counter == 4'd8) begin
                    // Sample rx_buffer: bottom 4 bits -> reg_addr, top_bit -> reg_rw
                    sample_addr = 1'b1;
                    // if r/w bit is 0 (master read) ... slave has to TX/send return data 
                    if (rx_buffer[REG_W-1] == 1'b0) begin
                        next_state = STATE_TX_DATA;
                    end
                    // else if r/w bit is 1 (master write) ... slave has to RX/place data into registers
                    else if (rx_buffer[REG_W-1]  == 1'b1) begin
                        next_state = STATE_RX_DATA;
                    end
                end
                // return to IDLE if CS unexpectedly goes HIGH mid-transaction
                else if (eof == 1'b1) begin
                    next_state = STATE_IDLE;
                end
            end 
            
            // Complete master read (slave TX data)
            STATE_TX_DATA : begin
                // TODO: Uncomment once TX pathway implemented
                /* 
                // If TX buffer counter is at 0, start loading register data into tx_buffer
                if (tx_buffer_counter == 4'd0) begin
                    tx_buffer_load = 1'b1;
                end
                // Else if tx bufffer counter is at 8, then return to idle (slave done with master read)
                else if (tx_buffer_counter == 4'd8) begin
                    next_state = STATE_IDLE;
                end
                // return to IDLE if CS unexpectedly goes HIGH mid-transaction
                else if (eof == 1'b1) begin
                    next_state = STATE_IDLE;
                end
                */
            end

            // Complete master write (slave RX data)
            STATE_RX_DATA : begin 
                // If RX buffer counter is at 8, begin latching data into register 
                if (rx_buffer_counter == 4'd8) begin
                    sample_data = 1'b1;
                    next_state = STATE_IDLE;
                end
                // return to IDLE if CS unexpectedly goes HIGH mid-transaction
                else if (eof == 1'b1) begin
                    next_state = STATE_IDLE;
                end
            end

            // Default state = IDLE 
            default : begin
                next_state = STATE_IDLE;
            end
        endcase
    end

    // RX Buffer Behavior
    // At the rising edge of clk (or if reset is asserted) ...
    always_ff @(negedge(rst_n) or posedge(clk)) begin
        // if reset is asserted, write rx_buffer to all 0s
        if (!rst_n) begin
            rx_buffer <= '0;
        end
        // else if this chip selected...
        else begin
            if (ena == 1'b1) begin
                // ... If data_sample control signal asserted ...
                if (spi_clk_pos == 1'b1) begin
                    // ... add MOSI as LSB to existing bits 0-6 of buffer
                    // oldest bit, b7 falls off the top 
                    // after 8 clock edges, rx_buffer holds complete byte
                    rx_buffer <= {rx_buffer[REG_W-2:0], spi_mosi};
                end
            end
        end
    end


    // RX Buffer Counter Behavior
    always_ff @(negedge(rst_n) or posedge(clk)) begin
        // if reset is asserted, write rx_buffer_counter to 0
        if (!rst_n) begin
            rx_buffer_counter <= '0;
        end
        // else if this chip selected...
        else begin
            if (ena == 1'b1) begin
                // if counter reaches 8 (full byte recieved), reset counter to 0
                if (rx_buffer_counter == 4'd8) begin
                    rx_buffer_counter <= 4'd0;
                end
                // on each SPI clock pulse (one bit arriving on MOSI), increment counter
                else if (spi_clk_pos == 1'b1) begin
                    rx_buffer_counter <= rx_buffer_counter + 1;
                end
            end
        end 
    end


    // Address + reg_rw Registers
    always_ff @(negedge(rst_n) or posedge(clk)) begin
        // if reset is asserted, write address + r/w bit to 0
        if (!rst_n) begin
            reg_addr <= '0;
            reg_rw <= '0;
        end
        // else if this chip selected...
        else begin
            if (ena == 1'b1) begin 
                // only check address + r/w bit once it has been properly sampled 
                if (sample_addr == 1'b1) begin
                    // address is bits 3:0 of byte#1 where ADDR_W = 4
                    // r/w bit is bit 7 of byte#1 where REG_W = 8
                    reg_addr <= rx_buffer[ADDR_W-1:0];
                    reg_rw <= rx_buffer[REG_W-1];
                end
            end
        end
    end 


    // Data output Register + Write Strobe signal    
    always_ff @(negedge(rst_n) or posedge(clk)) begin
        // if reset is asserted, reset data output values to 0
        if (!rst_n) begin
            reg_data_o <= '0;
            reg_data_o_dv <= '0;
        end
        // else if this chip selected...
        else begin
            if (ena == 1'b1) begin 
                // when data sample pulses, latch all 8b rx_buffer data into reg_data_o
                // set "data valid" bit to indicate output reg has valid data 
                if (sample_data == 1'b1) begin
                    reg_data_o <= rx_buffer;
                    reg_data_o_dv <= 1'b1;
                end 
                // If data not being loaded into reg_data_o, "data valid" set to 0
                else begin
                    reg_data_o_dv <= 1'b0;
                end
            end
        end
    end


endmodule
