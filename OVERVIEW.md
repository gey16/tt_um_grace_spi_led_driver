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
tt_um_grace_spi_led.sv  (top-level, maps TT pins to named signals)
    ↓
synchronizer.sv        (2-flop CDC for spi_cs_n, spi_clk, spi_mosi)
    ↓
spi_peripheral.sv           (SPI FSM — decodes transactions, drives register file)
    ↓
register_file.sv       (16 × 8-bit registers)
    ↓
uo_out[7:0]            (8 LED outputs via TT output pins)
```

Reference implementation studied: **calonso88/tt07_alu_74181** — a working TT design with a very similar SPI stack. Key file: `src/calonso_ref/spi_reg.sv`.

Architecture diagrams (HTML, open in browser):
- `/Users/grace/Career/AI_ChipDesign/tiny_tapeout/architecture_diagram.html` — module hierarchy
- `/Users/grace/Career/AI_ChipDesign/tiny_tapeout/spi_peripheral_internals.html` — internal block diagram of spi_peripheral.sv grouped by role

---

## Week 1 — COMPLETE

Goals: get calonso's tests passing on macOS, understand the repo architecture end-to-end.

### Fixes applied to calonso's repo (branch: dev/grace, fork: gey16/tt07_alu_74181)

**1. Icarus Verilog 13 "declaration after use" — `src/spi_reg.sv`**
Icarus 13 enforces strict declaration-before-use. Fixed by adding forward declarations at the top of the module before the `assign` statements.

**2. cocotb 2.0 `LogicArray` TypeError — `test/test.py`**
cocotb 2.0 returns `LogicArray` from `.value`; bitwise ops need `int()`. Fixed in four helper functions:
```python
def get_bit(value, bit_index):   temp = int(value) & (1 << bit_index)
def set_bit(value, bit_index):   temp = int(value) | (1 << bit_index)
def clear_bit(value, bit_index): temp = int(value) & ~(1 << bit_index)
def xor_bit(value, bit_index):   temp = int(value) ^ (1 << bit_index)
```

### Concepts Grace now understands
- TT chip pin mapping: `uio_in[0]`=CS, `uio_in[3]`=SCLK, `uio_in[1]`=MOSI, `uio_out[2]`=MISO
- SPI protocol: CS active-low, CPOL=0/CPHA=0 (sample on rising SCLK), 16-bit transaction format
- 2-flop CDC synchronizer: why it exists, how it introduces a 2-cycle delay, metastability
- VCD waveform viewing with Surfer (GTKWave incompatible with macOS 14+; installed via `brew install surfer`)
- cocotb test structure: how `spi_write()` in test.py maps to pin wiggles maps to module behavior
- calonso's FSM state machine: IDLE → ADDR → RX/TX → IDLE
- Edge detectors: how `falling_edge_detector` and `rising_edge_detector` work
- `tb.v` vs `test.py` roles: tb.v is the Verilog shim cocotb attaches to; test.py is the Python test driver
- TT bidir pins: `uio_in`/`uio_out`/`uio_oe` work together — `uio_oe[n]` sets direction, then either `uio_in[n]` or `uio_out[n]` is active
- Makefile mechanics: `SIM_BUILD`, `VERILOG_SOURCES`, `addprefix`, `TOPLEVEL`, `MODULE`, inline comments cause trailing-whitespace bugs

---

## Week 2 — COMPLETE

Goals: write all RTL modules from scratch, write cocotb test infrastructure from scratch, get a passing write transaction test in simulation.

### Exit criterion met
A complete SPI master-write transaction (CS low → 16 bits clocked in → CS high) correctly updates the register file and drives `uo_out` LEDs. Test passes with assertions verifying LED on/off state.

### What was built this week

**RTL modules (all in `src/`):**
- `spi_peripheral.sv` — SPI FSM, write path fully working
- `register_file.sv` — 16 × 8-bit registers, LED output logic
- `tt_um_grace_spi_led.sv` — top-level TT wrapper, pin mapping, synchronizer + spi_peripheral + register_file instantiation
- `synchronizer.sv` — 2-flop CDC (instantiates `reclocking.sv`)
- `reclocking.sv` — single flip-flop stage
- `rising_edge_detector.sv`, `falling_edge_detector.sv` — Grace's own versions (use `rst_n` port name)

**Test infrastructure (all in `test/`):**
- `tb.v` — Verilog testbench shim for cocotb
- `test.py` — cocotb test: reset, SPI write to reg 8 (enable), SPI write to reg 0 (LED data), assert `uo_out`
- `Makefile` — updated for Grace's sources; calonso sources removed

**Repo reorganization:**
- Calonso's original src files moved to `src/calonso_ref/`
- Calonso's original test files moved to `test/calonso_ref/`

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

### Key bug discovered and fixed: reg_rw timing

In `spi_peripheral.sv` STATE_ADDR, the FSM originally checked the registered `reg_rw` signal to decide whether to transition to STATE_RX_DATA or STATE_TX_DATA. But `reg_rw` is updated by an `always_ff` block one cycle *after* `sample_addr` fires — so the FSM always saw the stale value (0 = read at reset), sending every transaction to STATE_TX_DATA.

**Fix:** in the `always_comb` next-state block, check `rx_buffer[REG_W-1]` directly instead of `reg_rw`. The rx_buffer already has the correct value at the moment the counter hits 8.

```systemverilog
// WRONG — stale by one cycle:
if (reg_rw == 1'b1) next_state = STATE_RX_DATA;

// CORRECT — read directly from rx_buffer:
if (rx_buffer[REG_W-1] == 1'b1) next_state = STATE_RX_DATA;
```

### Makefile gotcha: inline comments cause trailing-whitespace bugs

In GNU Make, tabs/spaces before a `#` comment on a variable assignment line are included in the variable value. This caused `$(addprefix $(SRC_DIR)/,...)` to produce paths split on whitespace (e.g. `/path/to/src` and `/file.sv` as two separate words instead of `/path/to/src/file.sv`).

**Fix:** never put inline comments on variable assignment lines. Put comments on their own line above. Also use `$(strip ...)` for safety on path variables:
```makefile
# path to RTL source files
SRC_DIR := $(strip $(CURDIR)/../src)
```

---

## Running the tests

```bash
cd /Users/grace/tt/tt_um_grace_spi_led/test
make
```

Tests pass on macOS with Icarus Verilog 13 + cocotb 2.0.1. VCD output: `test/tb.vcd`, view with:
```bash
surfer /Users/grace/tt/tt_um_grace_spi_led/test/tb.vcd
```

Git: branch `dev/grace`, repo at `git@github.com:geysenbach/tt_um_grace_spi_led.git` (confirm remote with `git remote -v`).

---

## Key files in the repo

| File | Description |
|------|-------------|
| `src/tt_um_grace_spi_led.sv` | Top-level TT wrapper |
| `src/spi_peripheral.sv` | SPI FSM — write path and TX (read) path both complete |
| `src/register_file.sv` | 16 × 8-bit registers, LED output logic |
| `src/synchronizer.sv` | 2-flop CDC synchronizer |
| `src/reclocking.sv` | Single FF stage (used by synchronizer) |
| `src/rising_edge_detector.sv` | Rising edge detector (uses `rst_n` port name) |
| `src/falling_edge_detector.sv` | Falling edge detector (uses `rst_n` port name) |
| `src/calonso_ref/` | calonso's original src files — reference only |
| `test/tb.v` | Verilog testbench shim |
| `test/test.py` | cocotb tests: 5 write-path tests passing; spi_read() helper written, read test in progress |
| `test/Makefile` | Build config for Grace's design |
| `test/calonso_ref/` | calonso's original test files — reference only |
| `REFERENCE.md` | Design notes, diagrams, concept explanations |

---

## register_file.sv LED output logic

Each LED (`uo_out[n]`) is gated by a global enable bit in register 8:
```
uo_out[n] = registers[8][0] && registers[n][7]
```
- Write `0x01` to register 8 to enable LED outputs globally
- Write `0x80` to register n to turn on LED n (bit 7 = LED on)
- Registers 0–7 → LEDs 0–7. Register 8 = CTRL (bit 0 = global enable).

---

## Week 3 — IN PROGRESS (May 4–10)

Goal: Finish SPI slave — read transactions, RO-write-dropped behavior, full 16-register decoder.
Exit criterion: Full register-file cocotb tests pass.

### Done so far

**RTL additions to `spi_peripheral.sv`:**
- TX path fully implemented: `tx_buffer`, `tx_buffer_counter`, `STATE_TX_DATA` in FSM
- `spi_miso` driven from `tx_buffer[7]` (MSB-first shift register)
- `tx_buffer_load` fires on entry to `STATE_TX_DATA` (counter == 0), loads `reg_data_i`
- `tx_buffer` left-shifts on each rising SPI clock edge; `tx_buffer_counter` only counts in `STATE_TX_DATA`

**Test infrastructure:**
- 5 write-path tests all passing: walking ones, walking zeros, enable gate, random don't-care bits, multi-LED patterns
- `spi_read()` cocotb helper function written in `test.py`
- Key timing fix: MISO must be sampled **before** raising CLK (CPHA=0 — slave drives MISO, master samples on rising edge, shift happens after)
- `make log` target added: saves full cocotb output to `test/test_run.log`

**Repo / CI fixes:**
- `src/spi_peripheral.sv` renamed from `spi_slave.sv`; all references updated
- `info.yaml` fixed: `pinout:` and `yaml_version: 6` at top level (not nested inside `project:`), source files updated
- `src/config.tcl` added (required by OpenLane/TT GDS action)
- Linter warnings identified (unused signals: `spi_clk_neg`, `reg_rw`, `tx_buffer_load`, `status`; undriven: `spi_miso` — now fixed)

### Remaining for Week 3 exit criterion

1. ~~Verify `spi_read` test passes~~ **DONE** — all 3 tests passing
2. ~~Write-then-readback tests for all 8 BRIGHT registers (0x0–0x7), not just reg 0~~ **DONE**
3. ~~RO register values in `register_file.sv`: `ID (0x9) = 0xA5`, `VERSION (0xA) = 0x01`~~ **DONE**
4. ~~RO write protection: writes to 0x9–0xF silently dropped in `register_file.sv`~~ **DONE**
5. ~~CTRL/ENABLE → STATUS mirroring~~ **RTL DONE** — `status[0]` mirrors `registers[8][0]`, `status[1]` = `LAST_OP_WAS_WRITE`; driven by `reg_data_o_dv`/`reg_data_i_dv`; wired through top-level. **TODO (Grace):** write cocotb test to verify STATUS register behavior
6. GitHub Actions lint clean (remaining unused-signal warnings)

---

## Immediate next steps (in order)

1. ~~**Verify spi_read test passes**~~ **DONE**
2. ~~**Write-then-readback for all 8 BRIGHT registers** — extend `spi_read_tests` to cover 0x0–0x7~~ **DONE** — randomized write/readback loop over 0x0–0x7, 3 iterations, passing
   - **TODO (Grace):** fully understand and clean up `spi_read_tests` in `test/test.py`
3. ~~**Add RO registers to register_file.sv** — hardwire `ID (0x9) = 0xA5`, `VERSION (0xA) = 0x01`; silently drop writes to 0x9–0xF~~ **DONE** — write guard (`reg_addr < 4'h9`) in `always_ff`, `always_comb` case block returns hardwired constants on read; randomized write-then-readback test passing
4. ~~**Implement STATUS register RTL**~~ **DONE** — **TODO (Grace):** write cocotb STATUS register test
5. **Clean up linter warnings** — suppress or fix unused signals to get GitHub Actions green
6. **Week 4: MVT user logic** — confirm `uo[i] = ENABLE && BRIGHT_i[7]` is already the behavior in `register_file.sv`; first LibreLane CI run
