![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg)

# tt_um_grace_spi_led_driver — SPI LED Driver

An SPI-controlled 8-channel LED driver chip built for the [Tiny Tapeout](https://tinytapeout.com) TTGF26a shuttle (GF180MCU, 180nm).

An SPI master (e.g. the RP2040/RP2350 on the TT dev board) writes to a 16-register file over a standard 4-wire SPI interface. Eight BRIGHT registers directly drive 8 LED outputs. A global ENABLE bit in the CTRL register gates all outputs. Seven read-only registers provide device ID, version, and status observables for bring-up.

- [Full datasheet and pin descriptions](docs/info.md)

## What is Tiny Tapeout?

Tiny Tapeout is an educational project that makes it easier and cheaper than ever to get your digital designs manufactured on a real chip. To learn more, visit [tinytapeout.com](https://tinytapeout.com).

## Running simulations locally

The cocotb testbench requires a Python virtual environment with cocotb and its dependencies installed.

**Activate the virtual environment before running `make`:**

```bash
source ~/Career/AI_ChipDesign/tiny_tapeout/tt/venv/bin/activate
cd tt_um_grace_spi_led_driver/test
make
```

Waveform output is written to `test/tb.vcd`. View it with:

```bash
surfer test/tb.vcd
```

To run a specific test:

```bash
make TESTCASE=spi_write_tests
make TESTCASE=spi_read_tests
make TESTCASE=spi_RO_register_tests
```

## Resources

- [FAQ](https://tinytapeout.com/faq/)
- [Digital design lessons](https://tinytapeout.com/digital_design/)
- [Join the community](https://tinytapeout.com/discord)
