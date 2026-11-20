# Board audit

Functional audit of the six boards against the VM (`src/kone/*`) and the
microcode (`logisim/python/kone_microcode.py`), 2026-10-10. Generated files
were not edited. Every fix is in a generator, and the boards were rebuilt
from them.

## Method

- **Netlist.** The pad nets of all six `.kicad_pcb` files, joined through
  the backplane pads into one netlist for the stack. Routing is not
  re-checked: DRC reports 0 unconnected and 0 violations on every board, so
  the pad nets are the copper.
- **Generator consistency.** Every placed part was compared, pad by pad and
  by position, against what `build_kicad.py` builds from the circuits now.
- **Simulation.** A gate-level simulator over that netlist. The pinouts were
  typed in from the datasheets, *not* taken from `logisim/components.py`, so
  a pinout error in the generator would show up. The ROMs are loaded from
  `kicad/roms/` by their silkscreen label. Each run is checked in lockstep
  against a transcription of `cpu_functions.c` and `alu_functions.c`: all 32
  registers after every instruction (R16-R19 through what a program reads
  back), and the RAM at the end. The display and keyboard bridge follows
  `kicad/README.md`, with a configurable delay per character. The harness is
  not in the repo.

## Findings

| # | Board | Finding | Status |
| --- | --- | --- | --- |
| 1 | sequencer (ROMs) | `BOOT` only set SP. PC, every other register, F and the RAM came up wherever the 74377s and the 62256 powered up. The comment's claim that "a 74377 powers up at 0" is true in Logisim only. | fixed |
| 2 | sequencer (ROMs) | `BOOT` set SP to `0xFC3F`, a 40x24 display's value; the VM uses `0xFFAF`. | fixed |
| 3 | io | `R18` reloaded from `BUS` on every clock while it was nonzero (`nCLK18 = nW18 AND R18Z`), so it cleared itself the first time `BUS` was 0, without waiting for `DISPCLR`. | fixed |
| 4 | memory | The 62256's data pins sat on `BUS`, and with `CE#` tied low and `OE#` = `RAMWE`, the RAM drove `BUS` on every cycle that was not a write, whatever the address. | fixed |
| 5 | memory | The 62256 `WE#` was `NOT(MEMW AND MA15)`, a level straight off the control EEPROMs. It was not qualified by the clock, so it was open to ROM output glitches at every microstep change and raced the bus at the end of the step. | fixed |
| 6 | io | `DISPCLR` and `KBAV` floated whenever the bridge was unplugged or in its own reset. | fixed |
| 7 | docs | IC counts: `io` 24 and `sequencer` 22, not 23 and 20. BACKPLANE.md said "ten" 28-pin memories (there are 11) and omitted `io` as the source of `NRES`. | fixed |
| 8 | io | `TTYD` was 7 bits. A char of 128-255 written to `R19` showed as its low 7 bits on the LCD, where the VM shows a blank cell. | fixed: `TTYD7` on the backplane, the bridge blanks it |
| 9 | stack | One can oscillator drove `CLK` into 43 74377s across six boards and 24 connector contacts, unbuffered. | fixed: one 74HC14 per clocked board |
| 10 | stack | The backplane had 2 `GND` and 2 `+5V` pins for 143 signals. | fixed: `+5V` on pin 1 and `GND` on pins 2 and 40 of every connector, spare pins `GND` |
| 11 | io | Before the first clock edge, `R18`/`R19` hold their power-up values, so a bridge that is already running can take one junk char. With the Arduino's 1-2 s boot this cannot happen at power-on; it can on a J8 reset only if `R18` happened to be set at that moment. | open |
| 12 | docs | The bridge pin map in `kicad/README.md` was one pin off on every display line (`TTYD0` on BP4.4, which is `TQ7`). Wiring the bridge from it would have put the ALU's input on the Mega. | fixed, the table is now regenerated from `BACKPLANE.md` |
| 13 | io | With J6 on 2-3 and nothing on J7, `CLK` floated. | fixed: R5 pulls `EXTCLK` low |

### 1, 2 -- BOOT

The old microcode in simulation, from a random power-up state (three seeds),
fails at the first instruction: PC is `0x09e2`, `0x3e9c`, `0x5cb4`, and a junk
char reaches the display before the program runs. From an all-zero state (the
Logisim model), SP is the only mismatch.

`BOOT` now does what `cpu_reset()` does. It writes 0 to every register,
`0xFFAF` to SP, and 0 to every RAM byte (a 3-step loop that counts PC from
`0x8000` until it wraps, which leaves PC at 0). Step 0 clears `R18`, so a held
reset keeps the display quiet. This takes 179 of the 256 microsteps and
98,720 clocks, 0.1 s at 1 MHz.

It costs time in Logisim: 99k cycles is about 50 s at the GUI's 4 kHz tick,
and `KoneTest.java` now allows `BOOT` = 100,000 cycles more per case. The RAM
clear can be dropped, by deleting `boot_page` and `boot_byte`, if a slower
Logisim start is not worth it. In that case klib's display column and row at
`0x8000`/`0x8022` start at random on the board.

### 3 -- R18

R18 now loads on a write or on `DISPCLR`, and only then
(`nCLK18 = nW18 AND NDISPCLR`). In Logisim `DISPCLR` is `DISPNZ` buffered, so
`NDISPCLR` equals `R18Z` there: the simulation could not see this bug, and the
change leaves it as it was. On the board netlist, `hello` with a bridge that
needs 500 clocks per character:

| | screen |
| --- | --- |
| before | `Hlo ol!` |
| after | `Hello, World!` |

### 4, 5 -- memory board

`memory()` now has a 74245 (`ramd`) from `BUS` to the RAM's own data net
`RAMD`, enabled only by `RAMWE`. The 62256 drives `RAMD` otherwise, and the
`mem` mux reads it there. `WE#` is
`NOT(RAMWE AND NOT CLK)`: low only in the second half of the clock, once the
EEPROMs have settled, and it rises with the clock before anything changes.
Logisim's RAM still takes `RAMWE` on the clock edge, so the circuit simulates
as before. This adds one IC on `memory` (8 to 9) and uses two spare gates.

As built, the simulator counted 37 bus conflicts on 8 nets within the first
20 clocks, and SP was corrupt after the first instruction. Fixed, there are 0
conflicts in every run below.

This was the open item that held the memory board back. A 74245 was tried
once before and broke the write path in Logisim; this version passes
`make logisim_test` and the board-level lockstep. Write timing at the
transition (data hold after `WE#` rises: about 3 gate delays for `WE#`
against 377 + EEPROM + 74153 + 74245 for the data) is reasoned about, not
measured, like everything else on the boards.

### 6 -- pull-downs

R3 and R4 (10k) pull `DISPCLR` and `KBAV` low on `io`. Otherwise a floating
`KBAV` sets `R16` with a garbage `R17`, and a floating `DISPCLR` clears `R18`
at random. `KBD0`-`KBD6` still float with the bridge unplugged; they only
matter while `KBAV` is high.

### 8-10, 12, 13 -- second round

- **Clock.** Every clocked block has a `clkbuf`: a 7404 in Logisim and a
  74HC14 on the board (the same pinout, chosen by label in `kicad.py`). Gate 1
  takes `CLK` off the backplane, and gates 2-6 drive at most eight latches
  each. The backplane `CLK` now has five loads: one gate on each of
  `regfile`, `datapath`, `sequencer`, `memory` and `io`. `alu` has no clock.
  Every 74377 is two Schmitt stages from `CLK`, so the skew between boards is
  the spread of two HC gates, a few ns, less than the minimum
  clock-to-output delay of the 74377 that launches the data.
- **Ground.** 4 `+5V` and 12 `GND` pins, three ground pins per connector.
  Signal positions moved, so every board was rerouted, and the README's pin
  map was regenerated.
- **`TTYD7`.** The bridge writes a space for anything outside 32-126. A test
  printing `A`, 200, `B` shows `A B`, as the VM does.
- **Reset reference.** The reset 7414 is now numbered after the chips. It was
  hard-coded as U24, which the new buffer on `io` would have taken. It is U25
  now.

### 11 -- still open

The one junk char from a bridge that is already running before the first
clock edge, explained in the table.

## Per board

Static checks over the pad netlist, for every board:

- each IC has its datasheet `GND`/`VCC` pin on the planes;
- one 100 nF per IC (including X1 and the reset 7414) plus a 100 uF bulk cap;
- no input on an undriven net, except `RESRC`, which is the RC;
- no net with two drivers, except the tri-state 74245 outputs;
- every 74377 pin 11 two 74HC14 stages from `CLK`;
- `NRES` from `io` U25 pin 4 reaches `sequencer` through the backplane.

| Board | Netlist = generator | Power, decoupling | Inputs, drivers | Function (lockstep) |
| --- | --- | --- | --- | --- |
| regfile | pass, 0 diffs | pass, 87/87 | pass | pass |
| alu | pass | pass, 27/27 | pass (74HC21 NC pins 3, 11 on +5V, harmless) | pass |
| datapath | pass | pass, 16/16 | pass | pass |
| sequencer | pass | pass, 23/23 | pass | pass after 1, 2 |
| memory | pass | pass, 10/10 | pass after 4 | pass after 4, 5 |
| io | pass after 3 | pass, 25 + X1 | pass after 6, 13 | pass after 3 |

The "netlist = generator" column is for the boards as they were before this
audit. `io` differed from the generator only in the one pad the R18 fix
changes.

**Backplane.** All 160 pads carry a net on every board. Connectors J1-J4 and
holes H1-H4 sit at identical coordinates, and all six outlines are
302.88 x 415.82 mm. Each board's local net names were checked against
`BACKPLANE.md`: all of them are port renames (`BI0` for `BUS0` on regfile,
`R16Q0` for `KBACK` on io, and so on). `RW` and `WE0` are one signal
on two pins, joined on `sequencer` (harmless, one pin wasted).

**ROM images.** `build_roms.py` was regenerated and diffed: before the
change, all ten matched the microcode byte for byte. The silkscreen label of
each 28C256 was matched to its data nets (`uLIT` drives `LIT0-7`, `uMISC`
drives `RSRC0`, ..., `DISPSEL`, and so on), and the simulation loads each
image by that label. The images are regenerated with the new microcode.

## Path traces

Pin references are `board Uref pin`, taken from the boards of the first
round; the second round added a chip per board, so a U number may have moved.
Backplane positions are in `boards/BACKPLANE.md`.

- **a) fetch.** `MAR <- PCL/PCH`: microcode `MLW`/`MHW` on `uWE` bits 4/5 go
  over the backplane to memory U1 (7404) pins 1/3 -> `nMLW`/`nMHW` -> U3/U4
  (74377) pin 1. `BUS` reaches their D pins and the buffered clock pin 11. Below
  `0x8000` the 28C256 `prog` is selected by `MA15`=0 on the `mem` 74157
  pin 1. Then `IR0 <- MEM`: datapath U8 `bus0` 74153 (`BSRC` on pins 14/2,
  input 1 = `MEMO`) drives `BUS`. `PC+1` is two ALU `ADD`s through `T`. The
  carry goes alu U1/U2 74283 `C4` -> `COUT` -> U9 74HC21 gate 2 (with `CWR`)
  -> `C` -> `ALUC` -> datapath U12 `cy` pin 3, loaded by `nCYW`.
  `CY` comes back into the `alur` 74153 on input 2 (U4 pin 4) for the high
  byte. Matches `cpu_fetch()`, including the wrap at `0xFFFF`.
- **b) ALU op.** `T <- A` loads U14 `t` (`nTW`). `RSRC` (`uMISC` bits 0-1)
  selects `REGO`/`LIT`/`CY`/`T2Q`. `AOP` is the opcode byte
  itself: bit 7 selects the result mux, bits 5-4
  ORR/AND/XOR/ADD, bits 2-0 the unary ops. Only `0xF0` raises `CWR` (U9
  gate 1 = `P7 P6 P5 P4`). `ADD` writes `A` and `CY` together, and three
  more steps fold `CY` into `F` bit 0 (`F AND 0xFE OR CY`), leaving F1-F7
  untouched. Matches `alu_add()` and `cpu_set_flag()`.
- **c) memory write.** `MAR` as in (a). `MEMW` (`uWE` bit 6) AND
  `MA15` -> memory U7 `RAMWE`. It opens U6 74245 (`nRAMBUS`) and holds the
  62256 `OE#` high. `WE#` = `NOT(RAMWE AND NCLK)`. Below `0x8000`,
  `RAMWE` = 0 and the write is dropped (the documented ROM-half deviation).
- **d) devices.** io U8 74138 decodes `nW16-nW19` from `ADDR0-1` when
  `DEVWR` = `RW` AND `DEVSEL` (U7: `ADDR4`, `NADDR3`, `NADDR2`), which is
  R16-R19. Reads return the `dev` mux through the `rego` 74157 on
  `DEVSEL`. Keyboard: `KBSET` = `KBAV AND NOT R16` loads `R17 <- KBD` and
  `R16 <- 1`, and `KBACK` = `R16Q0`. Display: `R19Q0-7` as `TTYD`. `DISPNZ` = `R18 != 0` (U6 7427 + U7 7411 + U9), and
  `DISPCLR` loads `R18 <- 0`. The pin map in `kicad/README.md`
  agrees with `BACKPLANE.md`. One deviation: the VM overwrites `R17` when a
  key arrives while `R16` is set, the board holds it until the program
  acknowledges.
- **e) branch.** sequencer U3 74151 `cond`: `A`/`B`/`C` = `CSEL0-2` (pins
  11/10/9) select D0 = GND, D1 `BUSZ`, D2 `NBUSZ`, D3 `BUS0`, D4 `NBUS0`, D5
  `CY`, D6 `NCY`, D7 `ISM`. That is exactly `CSEL` in the microcode (none,
  Z, NZ, C1, C0, CY, NCY, ISM). `COND` picks `ALT` over `NEXT` on the `seqb`
  74157, and the `JA0`/`JA1`/`JC0`/`JC1` entries read `A` or `F` onto `BUS`
  in the condition step. `ISM` = `BUS5 AND NOT BUS6 AND NOT BUS7` is
  `OC_FLAG_POS_M`.

## Simulation runs

All runs below are after the fixes, from a random power-up state, with no
bus conflicts. Every one was run twice: on the first round's netlist, and again
on the second round's (clock buffers, new backplane, `TTYD7`), with the
same results. The second round adds a test printing `A`, char 200, `B`,
which shows `A B` on both the board and the VM.

| Program | Mode | Result |
| --- | --- | --- |
| 18 klib tests (`disp`, `mem`, `str_eq`, `int32_*`, `float32_*`, all but read and write) | lockstep | `ALL PASS`, every register equal after each of 1,486-47,807 instructions, RAM equal at the end |
| `test_int32_write`, `test_float32_write` | lockstep | equal for 1.5 M clocks (68,000-74,000 instructions), summary not yet reached |
| `count` | lockstep | equal for 20,601 instructions, `40` `41` `42` on screen |
| `test_int32_read`, `test_float32_read` | `.in` typed through the bridge | `ALL PASS` |
| `keyboard` | `Hi!` typed | `Hi!` |
| `hello` | bridge 1000 clocks/char | `Hello, World!` |
| `display` | bridge 1000 clocks/char | the char sequence intact over four rows |

Before the fixes (zero power-up, RAM split by hand, VM given SP `0xFC3F`),
the same 18 tests and both write tests matched too. The fixes changed
nothing in the datapath; they fixed reset, the handshake and the memory
board.

## Timing (estimate, not measured)

Longest path, the dispatch step at the end of FETCH, with 74HC maxima at
4.5 V / 25 °C and 150 ns EEPROMs:

| Stage | ns |
| --- | --- |
| uaddr 74377 clk->Q | 36 |
| control EEPROM | 150 |
| `adr` 74157 | 45 |
| two 74138 | 88 |
| 7432 | 23 |
| 74245 enable | 45 |
| `rego` 74157, `bus` 74153 | 64 |
| `dispA` EEPROM | 150 |
| `seqd`, `seqn` 74157 | 64 |
| `ures` 7408, setup | 40 |
| **total** | **~705** |

That leaves about 30 % margin on the 1000 ns clock at 25 °C, and less hot
(the HC maxima at 85 °C are some 25 % higher). The ADD-with-carry path to the
condition mux comes to about 625 ns. Neither the 1 MHz can nor the write
pulse (500 ns in the low half) is a problem by this estimate. It still has
to be measured on a built stack.
