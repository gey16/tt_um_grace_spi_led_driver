# test.py
# cocotb Simulation Tests 
# Grace Eysenbach

import cocotb 
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles 


## -- Helper Functions -- ## 
# value = full byte
# bit_index = bit you want to interact with 

# "get_bit" = find value of bit at bit_index 
# 1 << bit_index = bit mask with only bit_index set to 1 
# if bit = 0 --> temp = 0&1 = 0
# if bit = 1 --> temp = 1&1 = 1
def get_bit(value, bit_index):
    temp = int(value) & (1 << bit_index)
    return temp 

# "set_bit" = set bit_index equal to 1
# 1 << bit_index = bit mask with only bit_index set to 1 
# if bit = 0 --> temp = 0 | 1 = 1
# if bit = 1 --> temp = 1 | 1 = 1
def set_bit(value, bit_index):
  temp = int(value) | (1 << bit_index)
  return temp

# "clear_bit" = set bit_index equal to 0
# 1 << bit_index = bit mask with only bit_index set to 1 
# if bit = 0 --> temp = 0 & ~1 = 0
# if bit = 1 --> temp = 1 & ~1 = 0
def clear_bit(value, bit_index):
  temp = int(value) & ~(1 << bit_index)
  return temp

# "xor_bit" = flips bit_index value
# 1 << bit_index = bit mask with only bit_index set to 1 
# if bit = 0 --> temp = 0 ^ 1 = 1
# if bit = 1 --> temp = 1 ^ 1 = 0
def xor_bit(value, bit_index):
  temp = int(value) ^ (1 << bit_index)
  return temp

# CS High --> set uio_in[0] = 1;
def pull_cs_high(value):
  temp = set_bit(value, 0)
  return temp

# CS Low --> set uio_in[0] = 0;
def pull_cs_low(value):
  temp = clear_bit(value, 0)
  return temp

# spi_clk High --> set uio_in[3] = 1;
def spi_clk_high(value):
  temp = set_bit(value, 3)
  return temp

# spi_clk Low --> set uio_in[3] = 0;
def spi_clk_low(value):
  temp = clear_bit(value, 3)
  return temp

# spi_clk invert --> set uio_in[3] != uio_in[3];
def spi_clk_invert(value):
  temp = xor_bit(value, 3)
  return temp

# MOSI High --> set uio_in[1] = 1;
def spi_mosi_high(value):
  temp = set_bit(value, 1)
  return temp

# MOSI Low --> set uio_in[1] = 0;
def spi_mosi_low(value):
  temp = clear_bit(value, 1)
  return temp

# MISO Low --> read value of uio_out[2] (MISO pin);
def spi_miso_read(port):
  return (get_bit (port.value, 2) >> 2)

async def spi_write (clk, port, address, data):
    
    # Assert Chip Select (1-->0)
    temp = port.value;      #TODO: understand this more
    result = pull_cs_high(temp)
    port.value = result
    await ClockCycles(clk, 10)
    temp = port.value;
    result = pull_cs_low(temp)
    port.value = result
    await ClockCycles(clk, 10)

    # -- Send Bit Sequence -- #
    # 1. Set MOSI to bit value
    # 2. Toggle CLK high
    # 3. Toggle CLK low 

    # Send R/W Bit over MOSI
    # byte 1, bit 7
    temp = port.value;      # read current 8-bit value into temp
    result = spi_clk_invert(temp)  # invert clk bit 
    result2 = spi_mosi_high(result) # set MOSI bit high
    port.value = result2    # write back 8-bit value w/ a) inverted clk bit, and b) MOSI high
    await ClockCycles(clk, 10)
    temp = port.value; 
    result = spi_clk_invert(temp)
    port.value = result
    await ClockCycles(clk, 10)

    # Send 3x Dont-Care Bits over MOSI 
    # byte 1, bits 6:4
    i = 0
    while i < 3:
        temp = port.value; 
        result = spi_clk_invert(temp)
        result2 = spi_mosi_high(result)
        port.value = result2
        await ClockCycles(clk, 10)
        temp = port.value; 
        result = spi_clk_invert(temp)
        port.value = result
        await ClockCycles(clk, 10)
        i +=1

    # Send 4x Address Bits over MOSI 
    # byte 1, bits 3:0
    # send MSB first 
    i = 3
    while i >= 0:
        temp = port.value; 
        result = spi_clk_invert(temp)
        address_bit = get_bit(address, i)
        if (address_bit == 0):
            result2 = spi_mosi_low(result)
        else:
            result2 = spi_mosi_high(result)
        port.value = result2
        await ClockCycles(clk, 10)
        temp = port.value; 
        result = spi_clk_invert(temp)
        port.value = result
        await ClockCycles(clk, 10)
        i -=1        

    # Send 8x Data Bits over MOSI
    # byte 2, bits 7:0
    i = 7
    while i >= 0:
        temp = port.value; 
        result = spi_clk_invert(temp)
        data_bit = get_bit(data, i)
        if (data_bit == 0):
            result2 = spi_mosi_low(result)
        else:
            result2 = spi_mosi_high(result)
        port.value = result2
        await ClockCycles(clk, 10)
        temp = port.value; 
        result = spi_clk_invert(temp)
        port.value = result
        await ClockCycles(clk, 10)
        i -=1  

    # SPI Write Complete --> de-assert CS
    temp = port.value;
    result = pull_cs_high(temp)
    port.value = result
    await ClockCycles(clk, 10)
  

# TODO: implement when spi_read path implemented 
#async def spi_read (clk, port_in, port_out, address, data):

@cocotb.test()
async def test_project(dut):
    dut._log.info("Starting Test")

    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1

    dut._log.info("Test SPI LED Chip Behavior")

    # Wait for some time
    await ClockCycles(dut.clk, 10)
    await ClockCycles(dut.clk, 10)

    # CPOL = 0, SPI_CLK low in idle
    temp = dut.uio_in.value;
    result = spi_clk_low(temp)
    dut.uio_in.value = result

    # Wait for some time
    await ClockCycles(dut.clk, 10)
    await ClockCycles(dut.clk, 10)

    # ITERATIONS 
    iterations = 0

    while iterations < 10:

        # -- Enable LED Outputs -- #
        # byte1 = 1 000 1000
        # byte2 = 0000000 1
        enable_out = 0x1
        await spi_write (dut.clk, dut.uio_in, 8, enable_out)
        
        # byte1 = 1 000 0000
        # byte2 = 1 0000000
        led0_on  = 0x80
        # byte1 = 1 000 0000
        # byte2 = 0 0000000
        led0_off = 0x0
        
        # Turn LED0 Off + On 
        await spi_write (dut.clk, dut.uio_in, 0, led0_off)

        await ClockCycles(dut.clk, 10)
        await ClockCycles(dut.clk, 10)

        # Check that uo_out[0] = 0
        assert int(dut.uo_out.value) == 0x00, "LED0 should be OFF"

        await spi_write (dut.clk, dut.uio_in, 0, led0_on)

        await ClockCycles(dut.clk, 10)
        await ClockCycles(dut.clk, 10)

        # Check that uo_out[0] = 1
        assert int(dut.uo_out.value) == 0x01, "LED0 should be ON"

        # TODO: expand to other LEDs 
        # # Write reg[1] = 0xDE
        # await spi_write (dut.clk, dut.uio_in, 1, data1)
        # # Write reg[2] = 0xAD
        # await spi_write (dut.clk, dut.uio_in, 2, data2)
        # # Write reg[3] = 0xBE
        # await spi_write (dut.clk, dut.uio_in, 3, data3)
        # # Write reg[4] = 0xEF
        # await spi_write (dut.clk, dut.uio_in, 4, data4)
        # # Write reg[5] = 0x55
        # await spi_write (dut.clk, dut.uio_in, 5, data5)
        # # Write reg[6] = 0xAA
        # await spi_write (dut.clk, dut.uio_in, 6, data6)
        # # Write reg[7] = 0x0F
        # await spi_write (dut.clk, dut.uio_in, 7, data7)

        # Wait for some time
        await ClockCycles(dut.clk, 10)
        await ClockCycles(dut.clk, 10)

        iterations = iterations + 1
    
    # Wait for some time
    await ClockCycles(dut.clk, 10)
    await ClockCycles(dut.clk, 10)