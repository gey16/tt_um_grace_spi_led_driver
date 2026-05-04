# Reference: SPI Slave Design Notes

## Why edge detectors exist

The FSM runs on the system clock (`clk`), not `spi_clk`. But `spi_clk` comes from outside the chip and may stay high for several system clock cycles. Without edge detection, the FSM would sample MOSI multiple times per bit.

### Problem: sampling MOSI when spi_clk is high (no edge detector)

```
           ↑       ↑       ↑       ↑       ↑       ↑       ↑
         __|__   __|__   __|__   __|__   __|__   __|__   __|__
clk:  __|     |_|     |_|     |_|     |_|     |_|     |_|     |__
         1       2       3       4       5       6       7

                   |___________________|
spi_clk:  _________|                   |___________________________

spi_clk   0       0       1       1       1       0       0
on clk↑:

mosi:     X       X       1       1       1       X       X
sampled?  X       X       1       1       1       X       X   ← sampled 3 times!
```

### Solution: spi_clk_pos (rising edge detector output)

`spi_clk_pos` pulses HIGH for exactly one system clock cycle at the moment `spi_clk` transitions low→high. After that it returns to 0 even if `spi_clk` stays high.

```
           ↑       ↑       ↑       ↑       ↑       ↑       ↑
         __|__   __|__   __|__   __|__   __|__   __|__   __|__
clk:  __|     |_|     |_|     |_|     |_|     |_|     |_|     |__
         1       2       3       4       5       6       7

                   |___________________|
spi_clk:  _________|                   |___________________________

spi_clk   0       0       1       1       1       0       0
on clk↑:

spi_clk_pos:
          0       0       1       0       0       0       0   ← 1-cycle pulse only

mosi:     X       X       1       1       1       X       X
sampled?  X       X       1       X       X       X       X   ← sampled exactly once
```

The same logic applies to `sof` (CS falling edge → start of transaction) and `eof` (CS rising edge → end of transaction).

### Why not just clock the FSM on spi_clk directly?

1. `spi_clk` is asynchronous to the system clock — using it as a clock risks **metastability**.
2. Tiny Tapeout designs should be single-clock — multiple clock domains make synthesis and timing analysis much harder.

Edge detectors (combined with the 2-flop synchronizer before them) let the FSM stay entirely in the system clock domain while still reacting to SPI edges exactly once.
