# Tiny Tapeout Project — Planning Doc

## Schedule

### Key dates
- **Target shuttle:** TTGF26a (GF180MCU, 180nm, Global Foundries)
- **Submission deadline:** June 22, 2026
- **Today:** June 6, 2026
- **Time to deadline:** ~9 weeks
- **Expected chip delivery:** Nov 15, 2026
- **Expected dev board + chip in hand:** Late Nov / Dec 2026

### Time budget
- **Committed pace:** ~10 hrs/week, ~90 hrs total ceiling
- **Realistic working time:** 60–75 hrs after factoring in bad weeks
- **Implication:** full-scope project (~88 hrs estimated) has zero buffer at this pace. MVT discipline is required, not optional.

### Shuttle slip policy
Decision point at **end of week 4 (mid-May)**. Go/no-go criteria below. If no-go, slip to the next GF180 or Sky130 shuttle (chips would then arrive ~Q1 2027). No money committed before submission, so slipping costs calendar time only.

Estimated probability of hitting June 22 at 10 hrs/week: **~60–70%**. Slipping to the next shuttle is an acceptable outcome, not a failure.

### Week-by-week plan

| Week | Dates | Focus | Hours | Exit criterion |
|---|---|---|---|---|
| 1 | Apr 20 – Apr 26 | Toolchain setup. Clone calonso88/tt07_alu_74181. Get his cocotb tests passing against his RTL on macOS. **Write zero Verilog.** | 10 | `make test` passes in calonso's repo on your Mac |
| 2 | Apr 27 – May 3 | Write SPI slave FSM from scratch. MOSI/SCLK/CS input synchronizers. CPOL=0/CPHA=0 shift register. Write-transaction decode. Smoke test in iverilog. | 10 | Write transaction correctly updates an internal 16-byte memory in sim |
| 3 | May 4 – May 10 | Finish SPI slave: read transactions, RO-write-dropped behavior, full 16-register decoder. Adapt calonso's cocotb tests (protocol/BFM tests kept, register-value tests edited). | 10 | Full register-file cocotb tests pass |
| 4 | May 11 – May 17 | **MVT user logic (MSB-drive)** implementation. Integrate into TT top wrapper. First LibreLane CI run via GitHub Actions. Read every PD report line-by-line. **WEEK-4 GO/NO-GO CHECKPOINT.** | 10 | CI reaches GDS generation (not necessarily clean); sim passes |
| 5 | May 18 – May 24 | Fix CI/PD issues. Close timing if open. Clean up lint warnings. Draft `docs/info.md` datasheet. Verify `info.yaml` is correct. | 10 | **MVT is submittable** — if hit by a bus at EOW5, this state ships |
| 6 | May 25 – May 31 | *Decision point: stretch or consolidate.* If ahead of schedule, start PWM stretch (swap MSB-drive for counter-based PWM). If not, deepen tests, document more thoroughly, review reports. | 10 | Either stretch RTL complete in sim, or MVT docs/tests hardened |
| 7 | Jun 1 – Jun 7 | Continue stretch OR early submission prep. Full regression of tests. Re-run CI. | 10 | Stretch passes CI, or final MVT polish complete |
| 8 | Jun 8 – Jun 14 | **Submission lock.** Freeze RTL. Final `info.yaml` + datasheet. Prepurchase tile on app.tinytapeout.com/prepurchase. Submit design. | 10 | Submitted to TT |
| 9 | Jun 15 – Jun 22 | Buffer. Respond to any TT feedback requesting fixes. Final resubmission if needed. | 10 | Deadline passes |

### Checkpoints and fallbacks

- **EOW1 checkpoint:** calonso's tests run on your Mac. If not, debug toolchain before proceeding.
- **EOW3 checkpoint:** your SPI slave passes basic round-trip test. If not, likely schedule slip territory.
- **EOW4 go/no-go (hard):** MVT user logic done + first CI run reaches GDS. If not, slip to next shuttle — do not attempt to rush through weeks 5–8.
- **EOW5 checkpoint:** MVT state is submittable. Everything after this is stretch or buffer.
- **EOW8 hard deadline:** submission uploaded. Never wait until week 9 to submit.

## Open Silicon Tools

### Flow orchestration
- **LibreLane** — top-level flow driver. Ties together synthesis, P&R, and signoff into a single configurable flow. Successor to OpenLane. Runs via Docker on macOS.
- **Tiny Tapeout support tools (`tt-support-tools`)** — glue scripts that wrap LibreLane for TT submissions, generate datasheets and GDS renders, and enforce TT shuttle constraints (pin count, tile size, etc.).

### Simulation and verification
- **Icarus Verilog (`iverilog`)** — Verilog simulator. Runs natively on macOS via Homebrew.
- **Verilator** — linter and fast simulator. Used in LibreLane for lint checking during synthesis.
- **cocotb** — Python-based testbench framework. Primary verification environment.
- **GTKWave** — waveform viewer.

### Synthesis
- **Yosys** — RTL-to-gates synthesis.
- **ABC** — technology mapping and logic optimization, called by Yosys.

### Physical design
- **OpenROAD** — floorplanning, placement, clock tree synthesis, routing, chip finishing. Called by LibreLane.
- **OpenSTA** — static timing analysis engine used throughout the flow.
- **OpenRCX** — parasitic extraction for post-route timing.

### Signoff
- **KLayout** — GDS viewer and DRC runner.
- **Magic** — layout viewer, DRC, and LVS.
- **Netgen** — LVS (layout vs schematic) checking.

### PDK
- **GF180MCU** (Global Foundries 180nm MCU process) — open-source PDK released by Google in partnership with GlobalFoundries. Targeted for TTGF26a.

### Shuttle program
- **Tiny Tapeout** — open MPW shuttle service. Multiplexes many designs onto a shared die. Provides fixed pin interface (8 in / 8 out / 8 bidir) and a shared clock. Projects delivered as part of a dev board with an RP2350 MCU (RP2040 on older boards; TTGF26a dev boards will ship with RP2350).

### Local environment (macOS)
- **Docker Desktop** — required container runtime for LibreLane on macOS. Flow runs ~2 hr per hardening on Apple Silicon, vs ~15 min on native Linux.
- **GitHub Actions** — cloud CI using the TT template. Primary iteration path on macOS to avoid slow local runs. Local Docker used only for debug.

## Project

**SPI slave peripheral with an addressable register file, driving an 8-channel LED driver.**

The chip implements an SPI slave that exposes 16 8-bit registers over MOSI/MISO/SCLK/CS. An external SPI master (the MCU on the TT dev board — RP2350 on current boards, RP2040 on older) issues read/write transactions against addressed registers. Eight of the RW registers directly drive LEDs on `uo[0..7]`.

Two scope tiers are defined:
- **MVT (required):** LED drive is via MSB of each BRIGHT register (on/off only). Software patterns possible, no brightness control.
- **Stretch (if time allows):** LED drive is via counter-based PWM with per-channel brightness and software-configurable refresh rate.

See the User Logic section below for details. The SPI protocol, register map, and TT integration are identical in both tiers — only the internal user-logic module differs.

Rationale:
- Exercises the fundamental chip-design pattern that every real SoC uses: a serial control interface wrapping a register file wrapping user logic.
- Forces learning of clock-domain crossing fundamentals (SPI SCLK is async to the TT internal clock).
- Fits trivially in 1 tile, so area is not the constraint and the learning stays focused on the flow.
- Silicon-proven reference exists (see References), which de-risks the CDC and the post-silicon bring-up.
- LED demo runs via an off-the-shelf Pmod 8LD plugged into the output Pmod header on the TT dev board — no scope, buzzer, or custom hardware required for post-silicon bring-up. (The dev board itself has a 7-segment display but no discrete LEDs wired to `uo_out`.)

### Key design constraints
- **SCLK ≤ ASIC clock / 20** — required for safe 2-flop synchronization on the SPI inputs. With a nominal 50 MHz TT clock, target SCLK ≤ 2.5 MHz for bring-up. Silicon-verified on the reference project at a 1:5 ratio; we design for 1:20 for margin.
- **SPI mode:** CPOL=0, CPHA=0 only. Other modes add RTL complexity with no learning value for a first tapeout.
- **Pin convention:** follow the TT community standard (`uio[0]=CS`, `uio[1]=MOSI`, `uio[2]=MISO`, `uio[3]=SCK`) for compatibility with community tools.
- **Register layout:** 9 RW registers (0x0–0x8), 7 RO registers (0x9–0xF). RO write boundary is 0x9 — writes to 0x9 and above are silently dropped.

### Transaction format

16-bit transaction, MSB first, CPOL=0/CPHA=0. Single register access per CS assertion.

```
Bit:    [15]   [14:12]     [11:8]    [7:0]
MOSI:   R/W    reserved    addr      data (write) | don't-care (read)
MISO:   0      0           0         0 (write)    | data (read)
```

- `R/W`: 1 = write, 0 = read
- `reserved`: held at 0, ignored on decode (kept don't-care for future features)
- `addr`: 4-bit register address, 0x0 to 0xF
- `data`: on writes, the value to store; on reads, returned by slave on MISO in bits [7:0]

Writes to RO addresses (0x9–0xF) are silently dropped.

### Register map

| Addr | Name | Access | Reset | Description |
|---|---|---|---|---|
| 0x0 | `BRIGHT_0` | RW | 0x00 | PWM brightness for LED 0 (`uo[0]`). 0x00=off, 0xFF=always on |
| 0x1 | `BRIGHT_1` | RW | 0x00 | PWM brightness for LED 1 (`uo[1]`) |
| 0x2 | `BRIGHT_2` | RW | 0x00 | PWM brightness for LED 2 (`uo[2]`) |
| 0x3 | `BRIGHT_3` | RW | 0x00 | PWM brightness for LED 3 (`uo[3]`) |
| 0x4 | `BRIGHT_4` | RW | 0x00 | PWM brightness for LED 4 (`uo[4]`) |
| 0x5 | `BRIGHT_5` | RW | 0x00 | PWM brightness for LED 5 (`uo[5]`) |
| 0x6 | `BRIGHT_6` | RW | 0x00 | PWM brightness for LED 6 (`uo[6]`) |
| 0x7 | `BRIGHT_7` | RW | 0x00 | PWM brightness for LED 7 (`uo[7]`) |
| 0x8 | `CTRL` | RW | 0x80 | See CTRL breakdown below |
| 0x9 | `ID` | RO | 0xA5 | Fixed magic byte for SPI sanity check |
| 0xA | `VERSION` | RO | 0x01 | Design version. Proves address decode works beyond ID. |
| 0xB | `STATUS` | RO | — | Debug/status observables. See STATUS breakdown below. |
| 0xC | `COUNTER` | RO | — | Current value of the free-running PWM counter (debug) |
| 0xD | `RESERVED` | RO | 0x00 | Reserved for future use |
| 0xE | `RESERVED` | RO | 0x00 | Reserved for future use |
| 0xF | `SCRATCH_RO` | RO | — | Mirrors the last value written to any RW register (debug) |

**CTRL register (0x8) bit layout**

| Bits | Name | Description |
|---|---|---|
| [7:4] | `PRESCALER` | Tick-rate divider. Counter advances every 2^PRESCALER ASIC cycles. Reset value: 0x8 (≈760 Hz PWM refresh at 50 MHz) |
| [3:1] | reserved | Read as 0, writes ignored |
| [0] | `ENABLE` | 1 = LEDs driven by their BRIGHT_i values, 0 = all LEDs forced off. Reset value: 0 |

**STATUS register (0xA) bit layout**

| Bits | Name | Description |
|---|---|---|
| [7:4] | reserved | Read as 0 |
| [3] | `COUNTER_RUNNING` | Stretch only: 1 while PWM counter is ticking. MVT: always 0 (hardwired). |
| [2] | `PROTO_ERR` | Stretch only. Sticky; set if the last transaction had any bit in MOSI[14:12] nonzero (malformed packet from master). Cleared on next CS assertion. MVT: hardwired 0. |
| [1] | `LAST_OP_WAS_WRITE` | 1 after a completed write transaction, 0 after a completed read. Updates on CS deassertion. |
| [0] | `ENABLE` | Mirrors CTRL[0]. Diagnostic — proves CTRL writes are landing. |

Rationale for STATUS design: each bit is picked to give software a different-register readback path for something it can also control or infer, so mismatches between expected and observed state localize the bug. PROTO_ERR (stretch) catches master-side software bugs where junk reserved bits are being sent — useful during bring-up but non-critical; punted to stretch to keep MVT RTL lean.

### User logic

The register file wraps a user-logic module that drives `uo[0..7]` based on the 8 `BRIGHT_i` registers. Two scope tiers are defined; MVT is the required ship target, stretch is the aspirational one.

#### MVT: MSB-drive (must ship)

`uo[i] = ENABLE && BRIGHT_i[7]` for i in 0..7.

- Each BRIGHT register is a full 8-bit RW register (for forward compatibility with stretch), but only bit 7 gates the output.
- Writing 0x80–0xFF turns the LED on; writing 0x00–0x7F turns it off.
- CTRL register exists and is writable, but only `ENABLE` (bit[0]) affects output. `PRESCALER` bits are stored but unused.
- COUNTER register (0xC) returns 0x00 always in MVT.
- STATUS: ENABLE and LAST_OP_WAS_WRITE are live in MVT. PROTO_ERR and COUNTER_RUNNING are hardwired to 0.
- All other registers and the full SPI protocol work identically to stretch.

Demo story for MVT: software running on the RP2040 writes patterns (scanner, chase, strobe) to the BRIGHT registers; LEDs follow the pattern. No brightness control, but pattern playback works.

#### Stretch: full 8-channel PWM — COMPLETE (Week 7)

`uo[i] = ENABLE && (BRIGHT_i == 0xFF || pwm_counter < BRIGHT_i)` for i in 0..7.

- One shared 8-bit free-running counter (`pwm_counter`), gated by a configurable prescaler (divide by `2^PRESCALER`).
- Tick rate formula: `pwm_refresh_hz = asic_clk_hz / (2^PRESCALER * 256)`. With PRESCALER=8 (default) and 50 MHz clock, refresh ≈ 760 Hz (flicker-free).
- Boundary cases: BRIGHT=0xFF → always on (bypasses counter compare); BRIGHT=0x00 → always off (unsigned compare, counter never < 0).
- COUNTER register (0xC) returns live `pwm_counter` value for observability.
- STATUS: COUNTER_RUNNING and PROTO_ERR remain hardwired to 0 (not implemented — out of scope).
- Implemented directly in `register_file.sv` alongside the existing register file logic (not a separate module swap).

Patterns (scanner, breathing, fade) are implemented on the RP2040 in software — the chip is a dumb dimming engine (or dumb on/off engine in MVT). This is the correct split: hardware primitive, software flexibility.

### Interop with calonso88 reference

We reuse calonso88's cocotb BFM infrastructure (clock/reset scaffolding, SPI transaction helpers) but write our own tests from scratch. The register map diverges from calonso's (9 RW / 7 RO vs his 8 RW / 8 RO, different addresses), so test-level reuse is minimal. The BFM layer is the only thing that transfers cleanly.

Tests to write from scratch:
- Write transaction: write value to BRIGHT_i, read back same value
- RO protection: write to 0x9 (ID), confirm read returns 0xA5 unchanged
- CTRL/ENABLE: write 0x01 to CTRL (0x8), confirm STATUS mirrors ENABLE bit
- LED end-to-end: write 0x80 to BRIGHT_0 with ENABLE=1, confirm uo[0] goes high

### What this project does NOT do
- No async FIFO or full async CDC. The clock-ratio constraint (SCLK ≤ clk/20) avoids it.
- No SPI master. TT dev board's RP2040 is the master.
- No DMA, no interrupts, no multi-register bursts. Single-register per transaction only.
- No hardware pattern generation. All LED patterns are software-driven over SPI.

## Post-silicon bring-up

Plan for when chips arrive (~Nov 2026). No RTL work here, but defining the plan now shapes what observables we build into the design.

### Equipment

- **TT dev board** (ships with GF180 die, RP2350 MCU, 7-segment display, DIP switches, PMOD headers, power LEDs). ~€100.
- **Pmod 8LD** (Digilent part 410-076 or compatible clone). 8 discrete high-brightness LEDs on a 12-pin PMOD module. Plugs into the output PMOD header on the dev board. ~€8–20 depending on source.
- **USB cable** (Type-C). Laptop for host-side scripting.
- **Not needed:** oscilloscope, logic analyzer, external SPI master, USB-UART. The MCU on the dev board is the SPI master; the Pmod 8LD provides the visual demo.

**Pmod 8LD pin mapping when plugged in:**
- TT `uo_out[0..7]` → LD0..LD7 (all 8 active, brightness-controlled)

Both devices operate at 3.3V. Pmod 8LD draws ~1 mA per LED from the signal pins (well within TT's drive capability). No external components needed.

### Software tiers

Three graduation steps. Reaching tier 0 constitutes a successful bring-up.

- **Tier 0 — MicroPython REPL via TT Commander.** Type SPI transactions manually as Python commands. Uses `machine.SoftSPI` at ~10 kHz. Pattern used by calonso88 on his equivalent project. Good enough for initial sanity checks.
- **Tier 1 — Scripted MicroPython on the dev board MCU.** Same SoftSPI but runs a full test sequence automatically and prints pass/fail per check.
- **Tier 2 — Hardware SPI at speed.** Use the MCU's hardware SPI peripheral (SPI1 on RP2040, equivalent on RP2350) at the full `asic_clk/20` ≈ 2.5 MHz. Enables real-time pattern demos.

### Bring-up sequence

**Setup before starting:** Plug the Pmod 8LD into the output PMOD header on the dev board. Plug the dev board into USB.

Each step must pass before the next is meaningful. If step N fails, stop and diagnose before continuing.

1. **Board alive.** TT Commander loads over USB-serial. Select our design from the mux. All Pmod LEDs off (expected — ENABLE=0 at reset).
2. **SPI protocol alive.** Read 0x9 (ID). Expect 0xA5. If this fails, nothing else matters.
3. **Address decode works.** Read 0xA (VERSION), expect 0x01.
4. **RW loopback works.** Write 0xA5 to 0x0, read back 0xA5. Try 0x5A, then try multiple addresses in 0x0–0x7.
5. **RO writes dropped.** Write 0xFF to 0x9 (ID). Read 0x9, expect 0xA5 (not 0xFF). Proves write-mask logic.
6. **STATUS tracking.** Write to any RW register. Read STATUS (0xB), expect LAST_OP_WAS_WRITE=1. Read any register. Read STATUS, expect LAST_OP_WAS_WRITE=0.
7. **Control takes effect.** Write 0x01 to CTRL (0x8). Read STATUS, expect bit[0]=1. Proves CTRL→STATUS wire works.
8. **User logic end-to-end (MVT).** With ENABLE=1, write 0x80 to BRIGHT_0. Pmod LD0 lights up. Write 0x00, LD0 off. Cycle through LD0–LD7 individually.
9. **Pattern demos.** Scripted patterns: scanner, chase, strobe. Proves sustained traffic works.

### Failure modes and diagnostics

| Symptom | Likely cause | First check |
|---|---|---|
| Reading 0x9 returns all zeros | Wrong design selected, or reset not released | TT Commander design number + reset state |
| Reading 0x9 returns 0xFF | MISO not being driven (tristate issue) | Probe `uio[2]` |
| Reading 0x9 returns garbage | SCLK too fast, synchronizer violated | Drop SCLK below 1 MHz |
| Read works, write doesn't | R/W bit decoded wrong | Check bit[15] polarity in master code |
| Only some registers respond | Address decode bug | Exercise all 16 addresses, map which fail |
| LEDs don't light despite correct logic path | Pmod 8LD not plugged in, wrong Pmod header, or `uo` pin mapping in `info.yaml` wrong | Check Pmod is seated in OUTPUT header; cross-check `info.yaml` vs register map |
| PROTO_ERR always 1 (stretch only) | Master sending nonzero reserved bits | Fix master software |

### Success criterion

Tier 0 sequence steps 1–9 pass. Tier 1 automation and tier 2 performance are polish, not requirements.

## References

### Silicon-proven prior art

- **calonso88 / `tt07_alu_74181`** — TT07 (SKY130), tapeout May 2024. SPI slave + 8 RW + 8 RO registers + ALU user logic. Same architecture as this project.
  - Project page: https://tinytapeout.com/chips/tt07/tt_um_calonso88_74181
  - Repo (Apache-2.0): https://github.com/calonso88/tt07_alu_74181
  - Post-silicon status: confirmed working by author and Matt Venn. SPI functional at SCLK ≤ ASIC_clk / 5.

- **calonso88 / `tt07_spi_wrapper`** — standalone repo factoring out the SPI+regfile as reusable IP. Best place to study his SPI code cleanly, separated from the ALU.
  - Repo: https://github.com/calonso88/tt07_spi_wrapper

- **calonso88 / `tt09_rsa`** — TTIHP 0.2, same SPI wrapper reused with an RSA core as user logic. Confirms pattern portability across PDKs.
  - Project page: https://tinytapeout.com/chips/ttihp0p2/tt_um_calonso88_rsa

- **pa1mantri / `tt_um_pa1mantri_cdc_fifo`** — TT07. Explicit CDC FIFO on TT, useful as a reference if we ever outgrow the clock-ratio approach.
  - Project page: https://tinytapeout.com/chips/tt07/036

### Related TT docs

- TT Pmod SPI pinout convention: https://tinytapeout.com/specs/pinouts/
- TT memory options (includes `spi-ram-emu`, the inverse pattern): https://tinytapeout.com/specs/memory/
- TT local hardening guide (macOS Docker flow): https://tinytapeout.com/guides/local-hardening/

## Project Extension: RL for EDA Optimization

After chip delivery (~Nov 2026), a potential research/learning extension: apply reinforcement learning to optimize steps in the OpenLane/LibreLane flow.

### Most promising targets

**1. Synthesis recipe optimization (Yosys pass sequencing)**
Yosys exposes a sequence of optimization passes (e.g. `opt`, `techmap`, `abc`, `share`, `flatten`). The order and selection of passes affects area, timing, and power. An RL agent could learn to select pass sequences that minimize a QoR objective (e.g. cell count, critical path) for a class of designs similar to this one.
- Action space: discrete (select next Yosys pass from a menu)
- Reward: area / timing from synthesis output (fast to compute — seconds per run)
- Tractability: high — fast feedback loop, well-defined action space, measurable reward

**2. OpenLane hyperparameter tuning**
OpenLane exposes dozens of config knobs (placement density, buffer insertion strategy, routing layer weights, etc.). RL could search this space to find configurations that consistently produce better QoR for SPI-like designs.
- Action space: continuous or discretized config parameters
- Reward: routed area, WNS, TNS from OpenLane reports
- Tractability: medium — slower feedback loop (~minutes per run), higher-dimensional action space than synthesis

### Why not macro placement (AlphaChip-style)?
This design has no hard macros — only standard cells. The macro placement problem doesn't apply here. Standard cell placement is handled by OpenROAD's analytical placer and is harder to improve at this scale without significant infrastructure.

### Suggested starting point
Start with **synthesis recipe optimization (#1)** — fastest iteration cycle, most approachable action space, and directly applicable to this design. Use the GF180 cell library and this project's RTL as the training environment.

## Open Questions

- [ ] Budget total — concrete parts: €70 (tile) + €100 (dev board) + €8–20 (Pmod 8LD) ≈ **€180–190**. Open: shipping, spare chips, any optional FPGA for pre-silicon emulation.
- [ ] GF180-specific config tweaks to calonso's LibreLane Tcl (to be discovered empirically in week 1–2)
- [ ] Whether to graduate to tier 2 hardware-SPI bring-up (decide after chips arrive based on demo needs)