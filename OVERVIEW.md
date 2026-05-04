# Grace's Tiny Tapeout Project — Handoff Overview

## Who is Grace

Grace is learning chip design from scratch as part of a Tiny Tapeout submission targeting the **TTGF26a shuttle (deadline: June 22, 2026)**. She has some software background but this is her first hardware/RTL project. She is learning SystemVerilog, SPI protocol, FSM design, and cocotb simulation from the ground up.

**Collaboration style:** Act as a tutor. Ask guiding questions rather than giving answers directly. Grace makes her own edits — do not edit her files without her asking you to. When she asks you to check something, point out what's wrong and explain why; let her fix it. She has found this approach very effective.

---

## Project Goal

Grace is building her own custom Tiny Tapeout design called **tt_um_grace_spi_led** — an SPI-controlled LED driver chip. The planned architecture:

```
RP2040 (SPI master)
    ↓ CS, SCLK, MOSI / ↑ MISO
tt_um_grace_spi_led.v  (top-level, maps TT pins to named signals)
    ↓
synchronizer.sv        (2-flop CDC for spi_cs_n, spi_clk, spi_mosi)
    ↓
spi_slave.sv           (SPI FSM — decodes transactions, drives register file)  ← CURRENTLY BUILDING
    ↓
register_file.sv       (16 × 8-bit registers)                                  ← NOT YET STARTED
    ↓
uo_out[6:0]            (7 LED outputs via TT output pins)
```

Reference implementation studied: **calonso88/tt07_alu_74181** — a working TT design with a very similar SPI stack. Key file: `src/spi_reg.sv`.

Architecture diagrams (HTML, open in browser):
- `/Users/grace/Career/AI_ChipDesign/tiny_tapeout/architecture_diagram.html` — module hierarchy
- `/Users/grace/Career/AI_ChipDesign/tiny_tapeout/spi_slave_internals.html` — internal block diagram of spi_slave.sv grouped by role

---

## Week 1 — COMPLETE

Goals: get calonso's tests passing on macOS, understand the repo architecture end-to-end.

### Fixes applied to calonso's repo (branch: dev/grace, fork: gey16/tt07_alu_74181)

**1. Icarus Verilog 13 "declaration after use" — `src/spi_reg.sv`**
Icarus 13 enforces strict declaration-before-use. Fixed by adding forward declarations at the top of the module before the `assign` statements:
```systemverilog
logic [ADDR_W-1:0] addr;
logic reg_rw;
logic [REG_W-1:0] data;
logic dv;
logic [REG_W-1:0] tx_buffer;
logic [3:0] rx_buffer_counter;
logic [3:0] tx_buffer_counter;
```

**2. cocotb 2.0 `LogicArray` TypeError — `test/test.py`**
cocotb 2.0 returns `LogicArray` from `.value`; bitwise ops need `int()`. Fixed in four helper functions:
```python
def get_bit(value, bit_index):   temp = int(value) & (1 << bit_index)
def set_bit(value, bit_index):   temp = int(value) | (1 << bit_index)
def clear_bit(value, bit_index): temp = int(value) & ~(1 << bit_index)
def xor_bit(value, bit_index):   temp = int(value) ^ (1 << bit_index)
```

Both changes documented in `test/TEST_CHANGES.md`.

### Concepts Grace now understands
- TT chip pin mapping: `uio_in[0]`=CS, `uio_in[3]`=SCLK, `uio_in[1]`=MOSI, `uio_out[2]`=MISO
- SPI protocol: CS active-low, CPOL=0/CPHA=0 (sample on rising SCLK), 16-bit transaction format
- 2-flop CDC synchronizer: why it exists, how it introduces a 2-cycle delay, metastability
- VCD waveform viewing with Surfer (GTKWave incompatible with macOS 14+; installed via `brew install surfer`)
- cocotb test structure: how `spi_write()` in test.py maps to pin wiggles maps to module behavior
- calonso's FSM state machine: IDLE → ADDR → RX/TX → IDLE
- Edge detectors: how `falling_edge_detector` and `rising_edge_detector` work (see below)

---

## Week 2 — IN PROGRESS

Goal: write `spi_slave.sv` from scratch. Exit criterion: a write transaction correctly updates an internal 16-byte memory in simulation.

### SPI packet format (16 bits, MSB first)

```
Byte 1 — address phase (STATE_ADDR):
  bit 7   | bits 6-4        | bits 3-0
  R/W     | don't care (×3) | reg addr [3:0]
  1=write | (ignored)       | (0x0–0xF)

Byte 2 — data phase (STATE_RX_DATA or STATE_TX_DATA):
  bits 7-0
  data [7:0]

CS stays LOW for the entire 16-bit transaction.
Data sampled on rising edge of spi_clk (CPHA=0).
```

---

## Current state of `src/spi_slave.sv`

File path: `/Users/grace/tt/tt07_alu_74181/src/spi_slave.sv`

### What is DONE and correct

- Module port declaration (parameters, all I/O ports)
- Header comment with SPI packet format diagram
- Edge detector submodule instantiations (sof, eof, spi_clk_pos)
- FSM typedef enum: `STATE_IDLE, STATE_ADDR, STATE_RX_DATA, STATE_TX_DATA`
- FSM state register `always_ff` block
- FSM next-state `always_comb` block (all 4 states, correct transitions, correct control signal pulses, eof abort cases)
- Internal signal declarations (`rx_buffer`, `rx_buffer_counter`, `reg_rw`, `spi_clk_pos`, `tx_buffer_load`, `sample_addr`, `sample_data`)
- RX buffer `always_ff` — shifts MOSI in on each `spi_clk_pos`
- RX buffer counter `always_ff` — resets at 8, increments on `spi_clk_pos`
- addr + reg_rw register `always_ff` — latches on `sample_addr`, correct slices
- Data output register `always_ff` — structure correct, **one bug remaining (see below)**

### Known bugs / issues to fix

**1. Line 51 — syntax error: space in module name**
```systemverilog
// WRONG:
falling edge_detector falling_edge_detector_sof (
// CORRECT:
falling_edge_detector falling_edge_detector_sof (
```
The module is called `falling_edge_detector` (one word). This will cause a compile error.

**2. Lines 257-260 — data output register: wrong assignment**
```systemverilog
// WRONG — this is a shift operation (one bit at a time), not a latch:
reg_data_o <= {reg_data_o, rx_buffer[REG_W-1]};

// CORRECT — sample_data fires once when full byte is in rx_buffer; just latch it:
reg_data_o <= rx_buffer;
```
Comments on those lines are also wrong — they describe the RX buffer shift behavior, not this block. Update to: "latch completed rx_buffer into output register".

**3. Edge detector port name mismatch: `rst_n` vs `rstb`**
The existing `falling_edge_detector.sv` and `rising_edge_detector.sv` in `src/` use port name `rstb`, but Grace's instantiations connect `.rst_n(rst_n)`. This will cause a port connection error at compile time. Options:
  - Write her own edge detector modules with port name `rst_n` (preferred — good learning exercise)
  - Or rename the connections to `.rstb(rst_n)` to match the existing modules

**4. `tx_buffer_counter` used but not declared or implemented**
STATE_TX_DATA references `tx_buffer_counter` but it is never declared as a signal and there is no `always_ff` block for it. The TX path (slave sending data back on MISO) is entirely unimplemented.

### What is NOT YET STARTED

- **TX path**: `tx_buffer`, `tx_buffer_counter`, `spi_miso` output logic — needed for master read transactions. The FSM has STATE_TX_DATA but the data path for it is empty.
- **`falling_edge_detector.sv` and `rising_edge_detector.sv` (Grace's own versions)** — she needs to write these with `rst_n` port name, or reuse calonso's with `.rstb(rst_n)` connections.
- **`register_file.sv`** — 16 × 8-bit register array, not started.
- **`tt_um_grace_spi_led.v`** — top-level TT wrapper, not started.
- **Simulation / testbench** — no cocotb test written for Grace's design yet. Week 2 exit criterion is a passing write transaction test.

---

## Key files in the repo

| File | Description |
|------|-------------|
| `src/spi_slave.sv` | Grace's SPI FSM (in progress) |
| `src/spi_reg.sv` | calonso's reference SPI FSM — use for comparison |
| `src/falling_edge_detector.sv` | calonso's edge detector (uses `rstb` port name) |
| `src/rising_edge_detector.sv` | calonso's edge detector (uses `rstb` port name) |
| `src/synchronizer.sv` | 2-flop CDC synchronizer |
| `src/tt_um_calonso88_74181.v` | calonso's top-level (shows TT pin mapping pattern) |
| `test/test.py` | cocotb testbench (fixed for cocotb 2.0 + IVerilog 13) |
| `test/TEST_CHANGES.md` | Documents the two test fixes from week 1 |

---

## How the edge detectors work (Grace had a TODO to understand these)

Both submodules use a 1-cycle delayed copy of the input (`data_dly`) to detect transitions:

```systemverilog
// rising_edge_detector:
assign pos_edge = data & (!data_dly);   // data is HIGH now, was LOW last cycle

// falling_edge_detector:
assign neg_edge = (!data) & data_dly;   // data is LOW now, was HIGH last cycle
```

So they produce a **1-cycle pulse** on the system clock (`clk`) whenever the SPI signal transitions. This is how raw SPI pin signals (which change at SPI clock rate, asynchronously to system clock) get turned into clean 1-cycle pulses the FSM can act on.

- `sof` = 1-cycle pulse when CS goes LOW (start of transaction)
- `eof` = 1-cycle pulse when CS goes HIGH (end/abort of transaction)
- `spi_clk_pos` = 1-cycle pulse on each rising edge of SPI clock (one bit arriving)

The TODO comment on line 47 of spi_slave.sv can be removed — Grace understands this now.

---

## Running the tests

```bash
cd /Users/grace/tt/tt07_alu_74181/test
make
```

Tests pass on macOS with Icarus Verilog 13 + cocotb 2.0.1 after the fixes above. VCD output: `test/tb.vcd`, view with `surfer test/tb.vcd`.

Git: branch `dev/grace`, fork at `gey16/tt07_alu_74181` on GitHub. Remote set to SSH: `git@github.com:gey16/tt07_alu_74181.git`.

---

## Immediate next steps (in order)

1. Fix the two bugs in `spi_slave.sv` listed above (line 51 syntax error, line 260 wrong assignment)
2. Decide: write own edge detector modules with `rst_n`, or fix port connections to use `.rstb(rst_n)`
3. Implement TX path: declare `tx_buffer` and `tx_buffer_counter`, add their `always_ff` blocks, wire `spi_miso`
4. Write `register_file.sv` (16 × 8-bit registers, write-enable strobe)
5. Write `tt_um_grace_spi_led.v` top-level (map TT pins, instantiate synchronizer + spi_slave + register_file)
6. Write cocotb test for a complete write transaction and verify it updates the register
