# test.py
# cocotb Simulation Tests 
# Grace Eysenbach

import random

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
    temp = port.value    
    result = pull_cs_high(temp)
    port.value = result
    await ClockCycles(clk, 10)
    temp = port.value
    result = pull_cs_low(temp)
    port.value = result
    await ClockCycles(clk, 10)

    # -- Send Bit Sequence -- #
    # 1. Set MOSI to bit value
    # 2. Toggle CLK high
    # 3. Toggle CLK low 

    # Send R/W Bit over MOSI
    # byte 1, bit 7
    temp = port.value      # read current 8-bit value into temp
    result = spi_clk_invert(temp)  # invert clk bit 
    result2 = spi_mosi_high(result) # set MOSI bit high
    port.value = result2    # write back 8-bit value w/ a) inverted clk bit, and b) MOSI high
    await ClockCycles(clk, 10)
    temp = port.value
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
    temp = port.value
    result = pull_cs_high(temp)
    port.value = result
    await ClockCycles(clk, 10)
  


async def spi_read (clk, port_in, port_out, address):
# ports defined from DUT's perspective
# port_in = incoming signals (spi_clk, mosi)
# port_out = outgoing signals (miso) 

    # Assert Chip Select (1-->0)
    temp = port_in.value;         # port_in = DUT's perspective; incoming signals (SPI_CLK)
    result = pull_cs_high(temp)
    port_in.value = result
    await ClockCycles(clk, 10)
    temp = port_in.value;
    result = pull_cs_low(temp)
    port_in.value = result
    await ClockCycles(clk, 10)

    # -- Send Bit Sequence -- #
    # 1. Set MOSI to bit value
    # 2. Toggle CLK high
    # 3. Toggle CLK low 

    # Send R Bit over MOSI
    # byte 1, bit 7 = 0
    temp = port_in.value;      # read current 8-bit value into temp
    result = spi_clk_invert(temp)  # invert clk bit 
    result2 = spi_mosi_low(result) # set MOSI bit LOW (read)
    port_in.value = result2    # write back 8-bit value w/ a) inverted clk bit, and b) MOSI low
    await ClockCycles(clk, 10)
    temp = port_in.value; 
    result = spi_clk_invert(temp)
    port_in.value = result
    await ClockCycles(clk, 10)

    # Send 3x Dont-Care Bits over MOSI 
    # byte 1, bits 6:4
    i = 0
    while i < 3:
        temp = port_in.value; 
        result = spi_clk_invert(temp)
        result2 = spi_mosi_high(result)
        port_in.value = result2
        await ClockCycles(clk, 10)
        temp = port_in.value; 
        result = spi_clk_invert(temp)
        port_in.value = result
        await ClockCycles(clk, 10)
        i +=1

    # Send 4x Address Bits over MOSI 
    # byte 1, bits 3:0
    # send MSB first 
    i = 3
    while i >= 0:
        temp = port_in.value; 
        result = spi_clk_invert(temp)
        address_bit = get_bit(address, i)
        if (address_bit == 0):
            result2 = spi_mosi_low(result)
        else:
            result2 = spi_mosi_high(result)
        port_in.value = result2
        await ClockCycles(clk, 10)
        temp = port_in.value; 
        result = spi_clk_invert(temp)
        port_in.value = result
        await ClockCycles(clk, 10)
        i -=1  
    
    # Recieve 8x Data Bits over MISO
    # Peripheral returns register content
    i = 7
    reg_data = 0;     # initialize register data collected from peripheral    
    while i >= 0:
        #TODO: print(f"CLK pre-Rising Edge: i={i}  MISO={spi_miso_read(port_out)}")
        reg_data = (reg_data << 1) | spi_miso_read(port_out)    
        temp = port_in.value; 
        result = spi_clk_invert(temp)
        port_in.value = result
        await ClockCycles(clk, 10)
        #print(f"CLK post-Rising Edge: i={i}  MISO={spi_miso_read(port_out)}")
        temp = port_in.value; 
        result = spi_clk_invert(temp)
        port_in.value = result
        await ClockCycles(clk, 10)
        i -=1  

    # SPI Write Complete --> de-assert CS
    temp = port_in.value
    result = pull_cs_high(temp)
    port_in.value = result
    await ClockCycles(clk, 10)
    
    return reg_data
 
@cocotb.test()
async def spi_read_tests(dut):
    dut._log.info("Starting SPI Read Tests")

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

    dut._log.info("Test SPI Register Read Behavior")

    # Wait for some time
    await ClockCycles(dut.clk, 10)
    await ClockCycles(dut.clk, 10)

    # CPOL = 0, SPI_CLK low in idle
    temp = dut.uio_in.value
    result = spi_clk_low(temp)
    dut.uio_in.value = result

    # Wait for some time
    await ClockCycles(dut.clk, 10)
    await ClockCycles(dut.clk, 10)

    # ITERATIONS 
    iterations = 0

    # -- Enable LED Outputs -- #
    # Default PRESCALAR = 8 (0b1000)
    # enable  = 1000 0001
    # disable = 1000 0000
    enable_out = 0x81
    disable_out = 0x80

    # byte2 = 1111 1111 (100% PWM)
    led_on  = 0xFF
    # byte2 = 0 0000000
    led_off = 0x0

    #TODO: increase iterations
    while iterations < 3:
      # -- Basic write + read to LED registers -- #
      
      # Write/Read Loopback with randomized LED Register values (0-FF)
      for i in range(8): 
        expected_val = random.randint(0x00, 0xFF)
        await spi_write (dut.clk, dut.uio_in, i, expected_val)
        await ClockCycles(dut.clk, 10)
        await ClockCycles(dut.clk, 10)
        read_data = await spi_read(dut.clk, dut.uio_in, dut.uio_out, i)
        await ClockCycles(dut.clk, 10)
        await ClockCycles(dut.clk, 10)

        assert int(read_data) == int(expected_val), f"Unexpected Value. Expected: {expected_val:#010b}, Actual: {int(read_data):#010b}"
        dut._log.info(f"Wrote {expected_val:#010b} → read_data={int(read_data):#010b} expected={expected_val:#010b}")
      iterations = iterations + 1
# TODO: reinstate write tests 

@cocotb.test()
async def spi_write_tests(dut):
    dut._log.info("Starting SPI Write Test")

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

    dut._log.info("Test SPI Register Write Behavior")

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

    #TODO: increase iterations
    while iterations < 3:

        # -- Enable LED Outputs -- #
        # Default PRESCALAR = 8 (0b1000)
        # enable  = 1000 0001
        # disable = 1000 0000
        enable_out = 0x81
        disable_out = 0x80

        # byte2 = 1111 1111 (100% PWM)
        led_on  = 0xFF
        # byte2 = 0 0000000
        led_off = 0x0

        # Disable LED Outputs
        await spi_write (dut.clk, dut.uio_in, 8, disable_out)
        await ClockCycles(dut.clk, 10)
        await ClockCycles(dut.clk, 10)

        # Turn off ALL Leds 
        for j in range(8): 
          await spi_write (dut.clk, dut.uio_in, j, led_off)

        # Enable LED Outputs
        await spi_write (dut.clk, dut.uio_in, 8, enable_out)
        await ClockCycles(dut.clk, 10)
        await ClockCycles(dut.clk, 10)

        # -- Walking Ones -- # 
        for i in range(8):
            
            # Turn off ALL Leds 
            for j in range(8): 
                await spi_write (dut.clk, dut.uio_in, j, led_off)

            # Turn on 1 LED at a time
            await spi_write (dut.clk, dut.uio_in, i, led_on)

            await ClockCycles(dut.clk, 10)
            await ClockCycles(dut.clk, 10)

            # Check for any incorrect LEDs ON
            expected_on = 1 << i
            assert int(dut.uo_out.value) == expected_on, f"Unexpected LED still ON. Expected: {expected_on:#010b}, Actual: {int(dut.uo_out.value):#010b}"
            dut._log.info(f"i={i} wrote {led_on:#010b} → uo_out={int(dut.uo_out.value):#010b} expected={expected_on:#010b}")

            await ClockCycles(dut.clk, 10)
            await ClockCycles(dut.clk, 10)

        # Turn off ALL Leds 
        for j in range(8): 
          await spi_write (dut.clk, dut.uio_in, j, led_off)

        # -- Enable Gate Test -- #
        # Turn on ALL Leds 
        for j in range(8): 
          await spi_write (dut.clk, dut.uio_in, j, led_on)
        
        # Disable LED Outputs
        await spi_write (dut.clk, dut.uio_in, 8, disable_out)
        await ClockCycles(dut.clk, 10)
        await ClockCycles(dut.clk, 10)

        # Check that all LEDs are OFF when Global disable Set 
        expected_off =  0x0
        assert int(dut.uo_out.value) == expected_off, f"Unexpected LED ON. Expected: {expected_off:#010b}, Actual: {int(dut.uo_out.value):#010b}"
        dut._log.info(f"after disable → uo_out={int(dut.uo_out.value):#010b}")

        # Enable LED Outputs
        await spi_write (dut.clk, dut.uio_in, 8, enable_out)
        await ClockCycles(dut.clk, 10)
        await ClockCycles(dut.clk, 10)

        # Check that all LEDs are ON
        expected_on =  0xFF
        assert int(dut.uo_out.value) == expected_on, f"Unexpected LED OFF. Expected: {expected_on:#010b}, Actual: {int(dut.uo_out.value):#010b}"
        dut._log.info(f"after re-enable → uo_out={int(dut.uo_out.value):#010b}")

        # -- Incremental LEDs -- #
        # GOAL: add leds 1 at a time until all are on
        # ensure no LEDs incorrectly turn off 
        for i in range(8):

          # Turn off ALL Leds 
          for j in range(8): 
            await spi_write (dut.clk, dut.uio_in, j, led_off)

          await ClockCycles(dut.clk, 10)
          await ClockCycles(dut.clk, 10)

        # Turn on 1 LED at a time
          await spi_write (dut.clk, dut.uio_in, i, led_on)

          await ClockCycles(dut.clk, 10)
          await ClockCycles(dut.clk, 10)

          # Check for any incorrect LEDs ON
          expected_on = 1 << i
          assert int(dut.uo_out.value) == expected_on, f"Unexpected LED still ON. Expected: {expected_on:#010b}, Actual: {int(dut.uo_out.value):#010b}"
          dut._log.info(f"walk_ones i={i} wrote {led_on:#010b} → uo_out={int(dut.uo_out.value):#010b} expected={expected_on:#010b}")

          await ClockCycles(dut.clk, 10)
          await ClockCycles(dut.clk, 10)

          # ~~~ Only Needed for MVT ~~~ # 
          # # Randomize Don't Care bits in Output register 
          # data_i = random.randint(0x00, 0xFF) | led_on
          # await spi_write (dut.clk, dut.uio_in, i, data_i)
          # assert int(dut.uo_out.value[i]) == 0x1, f"LED is not ON. Expected: 0x1, Actual: {int(dut.uo_out.value[i]):#010b}"
          # dut._log.info(f"rand_dc i={i} wrote {data_i:#010b} → uo_out[{i}]={int(dut.uo_out.value[i])}")

        # -- Walking Zeros Test -- #
        # GOAL: turn off LEDs 1-by-1 and ensure others stay on
        for i in range(8):
          # Turn ON ALL Leds 
          for j in range(8): 
            await spi_write (dut.clk, dut.uio_in, j, led_on)

          await ClockCycles(dut.clk, 10)
          await ClockCycles(dut.clk, 10)

        # Turn OFF 1 LED at a time
          await spi_write (dut.clk, dut.uio_in, i, led_off)

          await ClockCycles(dut.clk, 10)
          await ClockCycles(dut.clk, 10)

          # Check for any incorrect LEDs OFF
          # Ex: 00000010 --> 11111101
          #                & 11111111 --> 11111101 --> only LED[1] should be off 
          expected_on = ~(1 << i) & 0xFF
          assert int(dut.uo_out.value) == expected_on, f"Unexpected LED Off. Expected: {expected_on:#010b}, Actual: {int(dut.uo_out.value):#010b}"
          dut._log.info(f"walk_zeros i={i} wrote led_off → uo_out={int(dut.uo_out.value):#010b} expected={expected_on:#010b}")

          await ClockCycles(dut.clk, 10)
          await ClockCycles(dut.clk, 10)

        # -- Multi-LED Pattern Test -- #
        # 3 loops of randomized values 
        for loop in range(3):
          expected_on = 0x0
          for i in range(8):
            # Pick a random state (on/off) for led register 
            data_i = random.choice([0x00, 0xFF])
            await spi_write (dut.clk, dut.uio_in, i, data_i)

            await ClockCycles(dut.clk, 10)
            await ClockCycles(dut.clk, 10)
          
            # LED fully on (0xFF) or fully off (0x00)
            # If LED randomized to be ON, update the expected_on register
            if data_i == 0xFF:
              expected_on = expected_on | (1 << i)
          
          assert int(dut.uo_out.value) == expected_on, f"Unexpected LED Off. Expected: {expected_on:#010b}, Actual: {int(dut.uo_out.value):#010b}"
          dut._log.info(f"loop={loop} final uo_out={int(dut.uo_out.value):#010b} expected={expected_on:#010b}")
        
        iterations = iterations + 1
    
    # Wait for some time
    await ClockCycles(dut.clk, 10)
    await ClockCycles(dut.clk, 10)

@cocotb.test()
async def spi_pwm_tests(dut):
  dut._log.info("Starting SPI PWM Brightness Tests")

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

  # Wait for some time
  await ClockCycles(dut.clk, 10)
  await ClockCycles(dut.clk, 10)

  # CPOL = 0, SPI_CLK low in idle
  temp = dut.uio_in.value
  result = spi_clk_low(temp)
  dut.uio_in.value = result

  # Wait for some time
  await ClockCycles(dut.clk, 10)
  await ClockCycles(dut.clk, 10)

  # ITERATIONS 
  iterations = 0

  # -- Enable LED Outputs -- #
  # Default PRESCALAR = 8 (0b1000)
  # enable  = 1000 0001
  # disable = 1000 0000
  enable_out = 0x81
  disable_out = 0x80

  led_on  = 0x1
  led_off = 0x0

  # PWM Test Variables 
  read_brightness = 0x0
  pwm_counter = 0x0
  buffer = 0x5
  expected_state = 0x0

  # Disable LED Outputs
  await spi_write (dut.clk, dut.uio_in, 8, disable_out)
  await ClockCycles(dut.clk, 10)
  await ClockCycles(dut.clk, 10)

  # Turn off ALL Leds 
  for j in range(8): 
    await spi_write (dut.clk, dut.uio_in, j, led_off)

  # Enable LED Outputs
  await spi_write (dut.clk, dut.uio_in, 8, enable_out)
  await ClockCycles(dut.clk, 10)
  await ClockCycles(dut.clk, 10)

  # -- Individual LED Brightness Test -- # 
  for i in range(8):
    # Turn off ALL Leds 
    for j in range(8): 
      await spi_write (dut.clk, dut.uio_in, j, led_off)

    # Pick randomized brightness value
    pwm_brightness = random.randint(0x00, 0xFF)
    await spi_write (dut.clk, dut.uio_in, i, pwm_brightness)
    read_brightness = await spi_read(dut.clk, dut.uio_in, dut.uio_out, i)
    pwm_counter = await spi_read(dut.clk, dut.uio_in, dut.uio_out, 0xC)
    if (pwm_counter < (read_brightness - buffer)): 
       expected_state = 1 << i
    else:
       expected_state = led_off
    dut._log.info(f"PWM Brightness = {pwm_brightness:#04x}")
    dut._log.info(f"Read Brightness = {read_brightness:#04x}")
    dut._log.info(f"PWM Counter = {pwm_counter:#04x}")
    assert int(dut.uo_out.value) == expected_state, f"Unexpected LED State. Expected: {expected_state:#010b}, Actual: {int(dut.uo_out.value):#010b}"

  # -- Multi-Channel LED Brightness Test -- #
  # Turn off ALL LEDs first
  for j in range(8):
    await spi_write(dut.clk, dut.uio_in, j, led_off)

  brightness_vals = []
  for i in range(8):
    pwm_brightness = random.randint(0x01, 0xFE)
    await spi_write(dut.clk, dut.uio_in, i, pwm_brightness)
    brightness_vals.append(pwm_brightness)

  # Read counter once after all 8 channels written
  pwm_counter = await spi_read(dut.clk, dut.uio_in, dut.uio_out, 0xC)

  expected_state = 0x0
  valid_mask = 0x0
  for i in range(8):
    if pwm_counter < (brightness_vals[i] - buffer):
      expected_state |= (1 << i)
      valid_mask |= (1 << i)
    elif pwm_counter >= (brightness_vals[i] + buffer):
      valid_mask |= (1 << i)
    # else: danger zone — skip channel

  dut._log.info(f"Multi-channel PWM Counter = {pwm_counter:#04x}")
  dut._log.info(f"Expected State = {expected_state:#010b}, Valid Mask = {valid_mask:#010b}")
  assert (int(dut.uo_out.value) & valid_mask) == expected_state, f"Unexpected LED State. Expected: {expected_state:#010b}, Actual: {int(dut.uo_out.value):#010b}"


# 1. write a random brightness level 
# 2. read back current brightness level 
# 3. if curr_brightness < pwm_counter - buffer --> expected_state = ON 
#   else --> expected_state = OFF 
# 4. compare expected_state + uo_out[i] to make sure they match 

@cocotb.test()
async def spi_RO_register_tests(dut):
  dut._log.info("Starting SPI RO Register Tests")

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

  # Wait for some time
  await ClockCycles(dut.clk, 10)
  await ClockCycles(dut.clk, 10)

  # CPOL = 0, SPI_CLK low in idle
  temp = dut.uio_in.value
  result = spi_clk_low(temp)
  dut.uio_in.value = result

  # Wait for some time
  await ClockCycles(dut.clk, 10)
  await ClockCycles(dut.clk, 10)

  # ITERATIONS 
  iterations = 0

  # Expected Constants 
  id_reg = 0x9
  ver_reg = 0xA
  status_reg = 0xB
  counter_reg = 0xC

  id_val = 0xA5
  ver_val = 0x01
  count_before = 0
  count_after = 0

  #TODO: increase iterations
  while iterations < 3:
    # Set Global Enable
    await spi_write (dut.clk, dut.uio_in, 8, 0x1)

    # Expected Status Value = 00000011
    # bit[0] = 1 --> Global Enable set
    # bit[1] = 1 --> last op was write 
    status_val = 0x3

    # Attempt write to RO registers (should ignore)
    # 0x9 = ID Register --> 0xA5
    # 0xA = Version Register --> 0x01
    # 0xB = Status Register --> b0 = global enable set, b1 = last op was write
    # 0xC = Counter Register --> stores current value of pwm_counter for controlling brightness
    # 0xB-0xE = Unmapped Registers --> 0x0
    test_val = random.randint(0x00, 0xFF)
    for i in range(0x9, 0x10):

      await spi_write (dut.clk, dut.uio_in, i, test_val)
      await ClockCycles(dut.clk, 10)
      await ClockCycles(dut.clk, 10)

      read_data = await spi_read(dut.clk, dut.uio_in, dut.uio_out, i)
      await ClockCycles(dut.clk, 10)
      await ClockCycles(dut.clk, 10)

      if (i == id_reg):
        assert int(read_data) == int(id_val), f"Unexpected Value. Expected: {id_val:#010b}, Actual: {int(read_data):#010b}"
        dut._log.info(f"Wrote {int(test_val):#010b} → read_data={int(read_data):#010b} expected={id_val:#010b}")
        dut._log.info(f"[0x{i:02X}] ID Value = 0x{read_data:02X}")
      elif (i == ver_reg):
        assert int(read_data) == int(ver_val), f"Unexpected Value. Expected: {ver_val:#010b}, Actual: {int(read_data):#010b}"
        dut._log.info(f"Wrote {int(test_val):#010b} → read_data={int(read_data):#010b} expected={ver_val:#010b}")
        dut._log.info(f"[0x{i:02X}] Version Value = 0x{read_data:02X}")
      elif (i == status_reg):
        assert int(read_data) == int(status_val), f"Unexpected Value. Expected: {status_val:#010b}, Actual: {int(read_data):#010b}"
        dut._log.info(f"Wrote {int(test_val):#010b} → read_data={int(read_data):#010b} expected={status_val:#010b}")
        dut._log.info(f"[0x{i:02X}] Status Value (Enable + Write) = 0x{read_data:02X}")

        read_data = await spi_read(dut.clk, dut.uio_in, dut.uio_out, i)
        await ClockCycles(dut.clk, 10)
        await ClockCycles(dut.clk, 10)

        # Last Op is now Read 
        status_val = 0x01
        assert int(read_data) == int(status_val), f"Unexpected Value. Expected: {status_val:#010b}, Actual: {int(read_data):#010b}"
        dut._log.info(f"Wrote {int(test_val):#010b} → read_data={int(read_data):#010b} expected={status_val:#010b}")
        dut._log.info(f"[0x{i:02X}] Status Value (Enable + Read)= 0x{read_data:02X}")

        # Disable Global Enable
        # Last Op is Write (spi_read to STATUS won't contain the updated bit[1] yet)
        await spi_write (dut.clk, dut.uio_in, 8, 0x0)
        await ClockCycles(dut.clk, 10)
        await ClockCycles(dut.clk, 10)
        read_data = await spi_read(dut.clk, dut.uio_in, dut.uio_out, i)
        await ClockCycles(dut.clk, 10)
        await ClockCycles(dut.clk, 10)
      
        status_val = 0x2
        assert int(read_data) == int(status_val), f"Unexpected Value. Expected: {status_val:#010b}, Actual: {int(read_data):#010b}"
        dut._log.info(f"Wrote {int(test_val):#010b} → read_data={int(read_data):#010b} expected={status_val:#010b}")
        dut._log.info(f"[0x{i:02X}] Status Value (Disable + Write)= 0x{read_data:02X}")

        # Last Op is Now Read 
        read_data = await spi_read(dut.clk, dut.uio_in, dut.uio_out, i)
        await ClockCycles(dut.clk, 10)
        await ClockCycles(dut.clk, 10)

        status_val = 0x00
        assert int(read_data) == int(status_val), f"Unexpected Value. Expected: {status_val:#010b}, Actual: {int(read_data):#010b}"
        dut._log.info(f"Wrote {int(test_val):#010b} → read_data={int(read_data):#010b} expected={status_val:#010b}")
        dut._log.info(f"[0x{i:02X}] Status Value (Disable + Read)= 0x{read_data:02X}")

      # Check that value of pwm_counter increments before/after 1000 clock cycles
      elif (i == counter_reg):
          count_before = await spi_read(dut.clk, dut.uio_in, dut.uio_out, counter_reg)
          await ClockCycles(dut.clk, 1000)
          count_after = await spi_read(dut.clk, dut.uio_in, dut.uio_out, counter_reg)
          assert int(count_before) != int(count_after), f"PWM Counter did not increment as expected. Count_Before: {count_before:#010b}, Count_After: {count_after:#010b}"

      else:
        assert int(read_data) == 0x0, f"Unexpected Value. Expected: {0x0}, Actual: {int(read_data):#010b}"
        dut._log.info(f"Wrote {int(test_val):#010b} → read_data={int(read_data):#010b} expected={0x0}")
        dut._log.info(f"[0x{i:02X}] Unused Register Value = 0x{read_data:02X}")

    iterations = iterations + 1

@cocotb.test()
async def spi_prescaler_tests(dut):
  dut._log.info("Starting SPI Prescaler Rate Tests")

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

  await ClockCycles(dut.clk, 10)
  await ClockCycles(dut.clk, 10)

  # CPOL = 0, SPI_CLK low in idle
  temp = dut.uio_in.value
  result = spi_clk_low(temp)
  dut.uio_in.value = result

  await ClockCycles(dut.clk, 10)
  await ClockCycles(dut.clk, 10)

  counter_reg = 0xC
  window = 4000   # system clocks between the two counter reads

  # Helper: measure how far the counter advances over a fixed window
  # for a given PRESCALER value. Returns the delta (mod 256 for wrap safety).
  async def measure_delta(prescaler):
    ctrl_val = (prescaler << 4) | 0x1     # PRESCALER + ENABLE=1
    await spi_write(dut.clk, dut.uio_in, 8, ctrl_val)
    await ClockCycles(dut.clk, 10)
    before = int(await spi_read(dut.clk, dut.uio_in, dut.uio_out, counter_reg))
    await ClockCycles(dut.clk, window)
    after = int(await spi_read(dut.clk, dut.uio_in, dut.uio_out, counter_reg))
    return (after - before) % 256

  # Lower prescaler => counter ticks faster => larger delta.
  # Use 6 (tick every 64 clk) vs 8 (tick every 256 clk).
  delta_fast = await measure_delta(6)
  delta_slow = await measure_delta(8)
  dut._log.info(f"PRESCALER=6 delta={delta_fast}, PRESCALER=8 delta={delta_slow}")

  # #2: counter must actually advance (stronger than "!= before")
  assert delta_fast > 0, f"Counter did not advance at PRESCALER=6 (delta={delta_fast})"
  assert delta_slow > 0, f"Counter did not advance at PRESCALER=8 (delta={delta_slow})"

  # #1: a smaller prescaler must advance the counter strictly faster
  assert delta_fast > delta_slow, f"Prescaler had no effect on rate. PRESCALER=6 delta={delta_fast}, PRESCALER=8 delta={delta_slow}"

@cocotb.test()
async def spi_reset_default_tests(dut):
  dut._log.info("Starting SPI Reset Default Tests")

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

  await ClockCycles(dut.clk, 10)
  await ClockCycles(dut.clk, 10)

  # CPOL = 0, SPI_CLK low in idle
  temp = dut.uio_in.value
  result = spi_clk_low(temp)
  dut.uio_in.value = result

  await ClockCycles(dut.clk, 10)
  await ClockCycles(dut.clk, 10)

  # CTRL (0x8) must reset to 0x80 (PRESCALER=8, ENABLE=0)
  ctrl = await spi_read(dut.clk, dut.uio_in, dut.uio_out, 0x8)
  assert int(ctrl) == 0x80, f"CTRL reset wrong. Expected: 0x80, Actual: {int(ctrl):#04x}"
  dut._log.info(f"CTRL reset value = {int(ctrl):#04x}")

  # All 8 BRIGHT registers must reset to 0x00
  for i in range(8):
    bright = await spi_read(dut.clk, dut.uio_in, dut.uio_out, i)
    assert int(bright) == 0x00, f"BRIGHT_{i} reset wrong. Expected: 0x00, Actual: {int(bright):#04x}"
  dut._log.info("All BRIGHT registers reset to 0x00")
