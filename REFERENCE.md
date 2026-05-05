# Reference: SPI Slave Design Notes

## TT pin signals: ui_in, uo_out, uio_in, uio_out, uio_oe

```
                    YOUR CHIP
         ┌─────────────────────────────┐
         │                             │
ui_in ──▶│  always input (8 pins)      │
         │                             │
uo_out ◀─│  always output (8 pins)     │
         │                             │
         │  bidir pins (8 pins each):  │
         │                             │
         │  uio_in[n]  ◀───────────┐   │
         │                         │   │
physical │                      [pin n]│──── physical pad
   pad ──│                         │   │
         │  uio_out[n] ────────────┘   │
         │              (only drives   │
         │               when oe=1)    │
         │                             │
         │  uio_oe[n]:                 │
         │    0 = pin is INPUT         │
         │        → chip reads uio_in  │
         │    1 = pin is OUTPUT        │
         │        → chip drives uio_out│
         └─────────────────────────────┘
```

For this design specifically:

```
bit  uio_oe  direction   signal
──────────────────────────────────
 0     0      INPUT    ← spi_cs_n   (CS from RP2040)
 1     0      INPUT    ← spi_mosi   (MOSI from RP2040)
 2     1      OUTPUT   → spi_miso   (MISO back to RP2040)
 3     0      INPUT    ← spi_clk    (SCLK from RP2040)
4-7    0      unused
```

`uio_in` is always readable regardless of direction. Only makes sense to read it when `uio_oe=0` (pin is input). When `uio_oe=1`, the chip itself is driving the pad, so `uio_in` just echoes back the chip's own output.

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
