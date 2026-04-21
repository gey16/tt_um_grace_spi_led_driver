# Test Changes

## Fixes required to run tests with Icarus Verilog 13 and cocotb 2.0.1

### `../src/spi_reg.sv` — Declaration after use (Icarus Verilog 13)

Icarus Verilog 13 is stricter than other simulators about signals being declared before their first use. Several signals in `spi_reg.sv` were declared after their point of first use:

- `addr`, `reg_rw` — used in `assign` and `always_comb` at the top of the file, declared near the bottom
- `data`, `dv` — used in `assign` statements, declared later
- `tx_buffer` — used in `assign spi_miso = tx_buffer[REG_W-1]`, declared later
- `rx_buffer_counter` — used in `always_comb` state machine, declared after it
- `tx_buffer_counter` — used in `always_comb` state machine, declared after it

**Fix:** Added forward declarations for all seven signals at the top of the module (before the `assign` statements), and removed the duplicate declarations from their original locations.

### `test.py` — `LogicArray` incompatibility with bitwise `int` operators (cocotb 2.0)

In cocotb 2.0, reading `.value` from a DUT port returns a `LogicArray` object instead of a plain `int`. The bit-manipulation helper functions (`get_bit`, `set_bit`, `clear_bit`, `xor_bit`) used `&`, `|`, `^`, `~` directly on the `LogicArray`, which raises `TypeError`.

**Fix:** Added `int(value)` conversion at the start of each of the four helper functions so bitwise operations work regardless of whether the caller passes a `LogicArray` or a plain `int`.
