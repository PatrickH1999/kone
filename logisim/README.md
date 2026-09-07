# kone as hardware

`logisim/` holds the second half of the project: the same machine as circuits
and as printed boards. `python/` generates [Logisim
Evolution](https://github.com/logisim-evolution/) files built from 74xx-series
chips, so the ISA can be checked against something buildable from real logic,
and a second backend turns the same circuits into KiCad 10 projects. Nothing
here is drawn by hand and nothing parses a generated file: a change to a build
script reaches both outputs.

## Board format

All six boards share one outline, **302.88 x 415.82 mm**, four layers on 1.6 mm
FR-4, with four M3 holes 6 mm in from the corners and every backplane connector
at the same place on every board. Nothing on a board is rotated, so the stack
goes together in any order. `stacking()` in `python/build_kicad.py` fails the
build if a board disagrees, and the size above is the largest board's, measured
there -- it warns when the two have drifted apart. The gerbers are what a fab
goes by; `kicad/BACKPLANE.md` carries the generated pinout.

## Build everything

```
make -C logisim circ cpu route gerbers test
```

- `circ` -- `regfile.circ`, `alu.circ` and `kone.circ`
- `cpu` -- `kone.circ` alone, on another program; `LOGISIM_PROG` defaults to
  `bin/display.bin`, which is what `circ` bakes in too
- `route` -- the KiCad projects under `kicad/`, routed and DRC clean; some
  20 minutes, and it wants `FREEROUTING_JAR`
- `gerbers` -- DRC again, then a fab ZIP per board in `kicad/out/`
- `test` -- the four programs booted headlessly on `kone.circ`; about a minute,
  and it wants a JDK and `LOGISIM_JAR`

Each target has a section of its own below. `route` and `gerbers` both build
`kicad`, which a single run makes once.

Everything has its own makefile. From the repo root the targets carry a
`logisim_` prefix, inside this directory they do not:

| From the root | Here | What it does |
| --- | --- | --- |
| `make logisim_circ` | `make circ` | every `python/build_*.py` -> `logisim/*.circ` |
| `make logisim_cpu` | `make cpu` | only `kone.circ`; `LOGISIM_PROG=bin/<name>.bin` picks its program |
| `make logisim_regfile`, `make logisim_alu` | `make regfile`, `make alu` | one circuit each |
| `make logisim_test` | `make test` | boot four programs on `kone.circ` in Logisim, headless |
| `make logisim_kicad` | `make kicad` | the KiCad projects, then ERC and DRC |
| `make logisim_route` | `make route` | autoroute with Freerouting, then DRC |
| `make logisim_gerbers` | `make gerbers` | DRC, then gerbers and drills zipped per board |
| `make logisim_clean` | `make clean` | the generated files, `kicad/` included |

## The circuits

| File | Contents |
| --- | --- |
| `logisim/regfile.circ` | the 32 x 8 bit register file, 74377 + 74245 per register, addressed by a 74138 tree |
| `logisim/alu.circ` | the nine ALU operations, 74283 adder and 74151/74153/74157 result muxes |
| `logisim/kone.circ` | the whole CPU: both of the above under a microcoded control unit, with memory, display and keyboard |

`kone.circ` opens as a block diagram of six subcircuits (`regfile`, `alu`, `sequencer`, `datapath`, `memory` and `io`) joined by named buses, with a clock and three probe pins. It is a microcoded machine: every register the ISA names lives in the register file at the index the VM gives it, seven 256-byte ROMs in `sequencer` hold the microprogram, and two more turn an opcode into its entry point. `R16`-`R19` are device registers in `io`; the Logisim TTY and keyboard they drive sit in the top-level circuit, so a running program's output is on screen without opening a subcircuit. The program sits in a ROM below `0x8000` with RAM above it, which is the one deviation from the VM, whose memory is writable throughout.

To watch it run, open `logisim/kone.circ`, reset with *Simulate -> Reset* and start the clock with *Simulate -> Auto-Tick*. The file opens at Logisim's fastest tick rate, 4 kHz, which is about 2000 CPU cycles a second because a cycle is two ticks, and a kone instruction is some 20 cycles. `display` and `hello` print at once; `count` needs roughly 30 000 cycles per number, so expect a number every few seconds rather than a stream.

## Testing headlessly

`make logisim_test` boots `display`, `hello`, `keyboard` and
`tests/klib/test_mem.kasm` on `kone.circ` in Logisim's own simulator
(`java/KoneTest.java`), stopping each case as soon as the TTY says what the vm
prints. The klib case runs `mem_poke`/`mem_peek`, which patch an `LDM`/`STM`
into scratch and call it, so it is also the test that the machine executes from
RAM.

A case is one row of the `CASES` table in `KoneTest.java` -- program, cycle
budget, keystrokes, expected display text. The harness writes the program into
the `prog` ROM itself, so a new case needs no new `.circ`, and it loads a copy
of the circuit from `logisim/bin/`: Logisim's loader stops with a dialog on the
`.circ.autosave` it leaves beside a file that is open in its GUI.

## Layout

| Path | Contents |
| --- | --- |
| `python/logisim/core.py` | `Component`, `Wire`, `Circuit`, `Project`, grid checks |
| `python/logisim/components.py` | the concrete components and their port geometry |
| `python/logisim/kicad.py` | the KiCad backend: the same circuits as boards |
| `python/build_<circuit>.py` | one build script per circuit; `build_kicad.py` writes boards instead |
| `python/kone_microcode.py` | the microprogram `kone.circ` runs |
| `java/` | headless checks that run a generated file in Logisim |
| `*.circ` | the generated files |
| `kicad/<board>/` | the generated KiCad projects, `kicad/out/` their gerber zips |
| `PARTS.md` | every chip and part the six boards need, generated |
| `kicad/BACKPLANE.md` | the connector pinout, generated |
| `Makefile` | the targets above |

A build script imports the library from its own directory, so
`python3 python/build_regfile.py` works from anywhere.

## Writing a build script

```python
from pathlib import Path
from logisim import *

c = Circuit("main")
a = c.add(Pin(100, 100, "A"))
b = c.add(Pin(100, 200, "B"))
g = c.add(AndGate(400, 150))
c.connect(g, "A", a)                    # port name -> pin, wires routed for you
c.connect(g, "B", b)
c.connect(g, "out", c.add(Pin(600, 150, "Y", output=True)))

p = Project(main="main")
p.add(c)
p.save(Path(__file__).resolve().parents[1] / "example.circ")
```

`connect(src, port, dst, dst_port=None, style="hv")` looks both ports up by name
and lays an L-shaped wire between them; `style="vh"` turns the corner the other
way. `dst_port` may be omitted when the target has exactly one port. An endpoint
may also be a bare `(x, y)`.

For anything longer than an elbow use `route(p1, p2, ...)`, which wires a
polyline. Fan-out is the one thing to lay out by hand: two `connect()` calls from
the same port produce two independent routes that may overlap. Give each net its
own trunk column or run it through a `Tunnel`, which is what the two build
scripts do throughout.

`stub(circuit, port, to, label, facing)` drops a tunnel at `to` and wires it back
to `port`; `wire_dip(circuit, chip, nets)` does that for every pin of a DIP at
once, taking a tunnel label, `Ground`/`Power` or `None` per pin. Both build
scripts wire chips exclusively that way, so a net is a name rather than a route.

Ports are named, not numbered: `adder.port("cout")`, `gate.port("B")`,
`reg.port("clk")`. Gate inputs answer to `A`, `B`, `C`… as well as `in0`, `in1`…
and to their index. `component.ports()` lists them all.

Coordinates must be multiples of 10. Off-grid positions raise `GridError`; set
`logisim.core.STRICT_GRID = False` to downgrade that to a warning. `Project.save`
also refuses duplicate circuit names, two identical components in one spot,
repeated pin labels, any net carrying two different tunnel labels — which is
what an accidentally shared trunk column looks like — and a floating TTL input;
each chip class lists the pins that have to be driven in `INPUTS`. `circuit.nets()` returns the
same connectivity Logisim computes: wires join at a shared endpoint or where an
endpoint or port lands inside another wire, so wires that merely cross are two
nets.

## Subcircuits

A `Circuit` goes inside another one through `circuit.instance(x, y)`:

```python
adder = full_adder()                    # a Circuit with labelled pins
stage = c.add(adder.instance(400, 400))
c.connect(stage, "Cin", carry_source, "Cout")
project.add(adder)                      # the definition still has to be added
```

`loc` is the **top-left corner** of the box. Ports carry their pin's label:
inputs down the left edge, outputs down the right, 20px apart, in the order the
pins were added to the circuit.

The library writes its own `<appear>` block for this, which is why the port
positions are exactly the ones `port()` reports. Logisim's built-in appearances
size the box from the rendered circuit name, which cannot be reproduced without
the font metrics, so `port()` refuses to guess for a circuit built with
`appearance="classic"`, `"evolution"` or `"logisim_evolution"`.

## Components

Wiring: `Pin` `Probe` `Tunnel` `Constant` `Power` `Ground` `Clock` `Splitter`
`BitExtender` — Gates: `NotGate` `Buffer` `AndGate` `OrGate` `NandGate`
`NorGate` `XorGate` `XnorGate` `OddParity` `EvenParity` `ControlledBuffer`
`ControlledInverter` — Plexers: `Multiplexer` `Demultiplexer` `Decoder`
`BitSelector` — Arithmetic: `Adder` `Subtractor` `Multiplier` `Divider`
`Negator` `Comparator` `Shifter` — Memory: `Register` `DFlipFlop` `TFlipFlop`
`JKFlipFlop` `SRFlipFlop` `Ram` `Rom` — I/O: `Led` `Button` `SevenSegment`
`HexDigit` `DipSwitch` `Keyboard` `Tty` — TTL: `Ttl7404` `Ttl7432` `Ttl74138`
`Ttl74245` `Ttl74377`.

TTL parts are addressed by their DIP pin name — `chip.port("nCLKen")`,
`chip.port("nY0")`, `chip.port("B3")` — and rotate with `facing`. GND and VCC
have no port; setting `VccGndPorts` raises `PortError`.

Constructor keywords map to Logisim attributes and only the ones you pass are
written to the file. Anything without a keyword can be passed through as
`**attrs`, e.g. `Register(x, y, width=8, trigger="falling", labelloc="south")`.

Two components are deliberately restricted, because their port positions move
with attributes the library does not model:

- Memory parts keep Logisim's `logisim_evolution` appearance; `Register`, the
  flip-flops, `Ram` and `Rom` raise `PortError` for `classic`/`evolution`.
- `Ram` supports `databus="bibus"` only — separate data-in and data-out pins.

`Counter` is not wrapped at all: its symbol width follows the digit count of its
maximum value. Build one from a `Register` and an `Adder`.

## regfile.circ

`build_regfile.py` generates a 32 x 8-bit register file out of 74xx parts: a
74377 per register, a 74245 putting it on the bus, and a two-level 74138 tree
decoding `ADDR` into 32 active-low selects that 7432 gates combine with `RD` and
`WR`. `make logisim_regfile` builds it; `make logisim_circ` does too.

The 32 slices come first on the canvas, in an 8 x 4 grid whose rows are the
decoder groups, so the chips are in view when the file opens; the pins, the
74138 tree and the 7432 gates sit below them.

Logisim Evolution has no bidirectional `Pin`, so the bus leaves the circuit as
`BUS_IN` and `BUS_OUT`. Wire both to the same bus net in the parent: `BUS_OUT` is
high-Z unless `RD` selects a register.

## alu.circ

`build_alu.py` generates the ALU: the nine ALU opcodes of the ISA and nothing
else. `L` and `R` are the two operands (`I` and the selected register), `OP` is
the opcode byte itself, `OUT`, `C`, `Z` and `CWR` the results.

| stage | parts |
| --- | --- |
| `L + R` | 2 x 74283 |
| `L or/and/xor R` | 2 x 7432, 2 x 7408, 2 x 7486 |
| `not L` | 2 x 7404 |
| `L` shifted or rotated | wiring into the mux inputs |
| one-operand result, opcode bits 2-0 | 8 x 74151 |
| two-operand result, opcode bits 5-4 | 4 x 74153 |
| `OUT`, opcode bit 7 | 2 x 74157 |
| `Z`, `C`, `CWR` | 7427, 7411, 7421 |

`CWR` is high only for `ADD`; it is what a flag register has to gate on, because
in the ISA only `ADD` writes carry. For an opcode that is not one of the nine,
`OUT` is undefined -- the CPU does not latch `A` from the ALU then.

`make logisim_alu` builds it; `make logisim_circ` does too.

## kone.circ

`build_kone.py` puts `regfile.circ` and `alu.circ` under a microcoded control
unit and adds memory, a display and a keyboard: the whole CPU. The top level is
a block diagram of six subcircuits and nothing else:

| Block | Ports | Contents |
| --- | --- | --- |
| `regfile` | `BUS_IN ADDR RD WR CLK` -> `BUS_OUT` | unchanged |
| `alu` | `L R OP` -> `OUT C Z CWR` | unchanged |
| `sequencer` | `CLK BUS CY` -> `UADDR LIT AOP WE SEL RSRC RW` | microprogram counter, nine ROMs, next-address and condition muxes |
| `datapath` | `CLK REGO MEMO ALUO ALUC LIT WE SEL RSRC` -> `BUS ADDR TQ ALUR CY` | bus and operand muxes, `T`/`T2`/`AL`/`CY` latches, address mux |
| `memory` | `CLK BUS WE` -> `MEMO MAR` | `MAR`, program ROM, RAM, the `MA15` split |
| `io` | `CLK BUS RFO ADDR RW KBAV KBD` -> `REGO TTYD DISPNZ KBSET` | `R16`-`R19` and their decode |

The TTY and the keyboard are in `kone` itself rather than in `io`: a display
inside a subcircuit only shows what a program prints once you descend into it.

Tunnels are private to a block, so a net that crosses a boundary is a pin. The
microcode's control bytes cross whole -- `WE` (the write enables) and `SEL`
(register address, `ASEL`, bus source) -- and each block splits out the lines it
uses, which is why adding a control line means touching only its consumer.

`make logisim_cpu` builds the file and `LOGISIM_PROG=bin/<name>.bin` picks the
program in its ROM. `make logisim_test` boots `display`, `hello`, `keyboard` and
`tests/klib/test_mem.kasm` on it headlessly (`logisim/java/KoneTest.java`),
stopping each case as soon as the TTY says what the vm prints. The klib case
runs `mem_poke`/`mem_peek`, which patch an `LDM`/`STM` into scratch and call it,
so it is also the test that the machine executes from RAM.

A case is one row of the `CASES` table in `KoneTest.java` -- program, cycle
budget, keystrokes, expected display text. The harness writes the program into
the `prog` ROM itself, so a new case needs no new `.circ`, and it loads a copy
of the circuit from `bin/`: Logisim's loader stops with a dialog on
the `.circ.autosave` it leaves beside a file that is open in its GUI.

The microprogram is `kone_microcode.py`, one dict per step, assembled into seven
256-byte ROMs plus two that map an opcode to its entry point:

| ROM | Field |
| --- | --- |
| `uLIT` | 8-bit literal, a bus source and the ALU's right input |
| `uAOP` | ALU opcode, straight from the ISA |
| `uNEXT`, `uALT` | next microaddress, and the one taken while the condition holds |
| `uWE` | the eight write enables: `RW TW T2W ALW MLW MHW MEMW CYW` |
| `uRA` | register address, `ASEL` (use the `AL` latch instead), bus source |
| `uMISC` | ALU right-hand source, branch condition, dispatch |
| `dispA`, `dispB` | opcode -> operand fetch, opcode -> execute |

Conditions are read off the main bus, so a step that branches puts the register
it tests on the bus in the same step. `python3 python/kone_microcode.py`
prints the assembled listing with its addresses, which is the first thing to
look at when the CPU goes somewhere unexpected -- the `UADDR` output pin says
which microstep it is in, and `BUS` and `MAR` say what it is doing.

## Where the port offsets come from

They are not guessed. Logisim Evolution's own jar was loaded headlessly and
asked, for every component and attribute combination, where it puts its pins
(`InstanceFactory.getPorts()`), and the generated file was then read back with
`LogisimFile.load` to compare the offsets the library computes against the ones
the simulator reports. All 1419 combinations agree for v4.1.0. If a future
Logisim moves a pin, that comparison is the thing to re-run — the probe is four
short Java files against
`/usr/share/java/logisim-evolution/logisim-evolution.jar`.

## Display and keyboard

Both devices hang off the backplane as plain 5 V logic; `kicad/BACKPLANE.md`
lists the pins, this is what the lines mean.

**Display, CPU to device.** `TTYD0`-`TTYD6` carry the character as 7-bit ASCII
(bits 0-6 of `R19`), `DISPNZ` goes high when the program writes `R18` and stays
high until the device answers on `DISPCLR`, which clears `R18`. The program's
poll loop on `R18` therefore ends when the device says so, not after a fixed
number of clocks -- the display sets the pace, exactly as the display process
does in the vm. Characters are 32-126 plus 8 for backspace.

**Keyboard, device to CPU.** `KBAV` says a character is waiting on
`KBD0`-`KBD6`; the CPU takes it and sets `R16`, which raises `KBACK` and holds
it until the program acknowledges by writing 0 to `R16`. `KBSET` is the same
event as a single-clock pulse, for a device that wants an edge instead of a
level. Enter arrives as 10, backspace as 8 or 127, anything else as a space.

In `kone.circ` the two are a Logisim TTY and keyboard at the top level, and
`DISPCLR` is the strobe fed back through a buffer -- a device that is always
ready. On a board those four wires go to the connector instead.

### The bridge

An **HD44780 character display takes ASCII directly**: its character ROM covers
0x20-0x7D almost one for one (0x5C is a yen sign, 0x7E and 0x7F are arrows). It
is not a terminal, though. It has no line wrap, no scrolling, no backspace and
no notion of a grid, it needs an initialisation sequence, and it wants RS, R/W
and an E pulse rather than one strobe. Between the backplane and the display
belongs a small controller, and the same one serves the keyboard:

| Side | Wires | To |
| --- | --- | --- |
| display | `TTYD0`-`6`, `DISPNZ` in, `DISPCLR` out | 9 pins on the bridge, plus 2 for the LCD's I2C backpack |
| keyboard | `KBD0`-`6`, `KBAV` out, `KBACK` in | 9 pins, plus 4 SPI lines and an interrupt for the USB host |

The display the machine is built for is a **20x4 HD44780 module** (a Freenove
I2C LCD2004, the controller behind a PCF8574 backpack), and the vm's grid is
20x4 because of it: what the bridge receives it writes one for one, with no
window into a larger grid to keep. The keyboard is a **USB keyboard behind a
USB Host Shield** (MAX3421E), on SPI with its `SS` on 53 or the shield's 10 and
`INT` on 9. Both hang off one **Arduino Mega 2560**: 5 V like the io board, so
nothing needs level shifting, and enough pins to serve both sides at once,
which a Nano has not -- its 18 usable GPIO are already gone on the shield and
the LCD, before any of the io board's 18 lines. The LCD's I2C goes to 20 (SDA)
and 21 (SCL).

A USB Host Shield is an Uno shield and takes SPI from pins 11, 12 and 13, which
on a Mega are ordinary GPIO. Use a revision that takes SPI from the **ICSP
header** -- the USB Host Shield 2.0 boards do, and the header carries the Mega's
hardware SPI -- or lift the shield's 11/12/13 and jumper them to 51 (MOSI), 50
(MISO) and 52 (SCK).

Do not feed the stack from the Mega's 5 V pin: the backplane's supply and the
Mega's USB supply are separate, and only their grounds are tied together.

#### Pin map

The signals are the ones `kicad/BACKPLANE.md` lists for the `io` board;
direction is the machine's, the mode is the Mega's.

| kone signal | Backplane | Direction | Mega pin | Mega mode |
| --- | --- | --- | --- | --- |
| `TTYD0` | BP4.4 | out | 22 | input |
| `TTYD1` | BP4.5 | out | 23 | input |
| `TTYD2` | BP4.6 | out | 24 | input |
| `TTYD3` | BP4.7 | out | 25 | input |
| `TTYD4` | BP4.8 | out | 26 | input |
| `TTYD5` | BP4.9 | out | 27 | input |
| `TTYD6` | BP4.10 | out | 28 | input |
| `DISPNZ` | BP2.6 | out | 29 | input |
| `DISPCLR` | BP2.5 | in | 30 | output |
| `KBD0` | BP2.9 | in | 31 | output |
| `KBD1` | BP2.10 | in | 32 | output |
| `KBD2` | BP2.11 | in | 33 | output |
| `KBD3` | BP2.12 | in | 34 | output |
| `KBD4` | BP2.13 | in | 35 | output |
| `KBD5` | BP2.14 | in | 36 | output |
| `KBD6` | BP2.15 | in | 37 | output |
| `KBAV` | BP2.8 | in | 38 | output |
| `KBACK` | BP2.7 | out | 39 | input |
| `GND` | BP1.2 | - | GND | - |

`KBSET` (BP2.16) stays unconnected: the bridge watches the `KBAV` level rather
than an edge. The data lines are seven bits wide, so ASCII 0-127 passes and
nothing above it -- the vm's keyboard takes 32-255, but a real keyboard has no
way to send the upper half anyway.

#### What the bridge does

Per character out: wait for `DISPNZ`, read the seven `TTYD` lines, write that
character to the LCD, then raise `DISPCLR` and hold it until `DISPNZ` falls
before dropping it again.

Per key in: translate the USB HID key to ASCII, normalized as above, put the
code on `KBD0`-`KBD6`, raise `KBAV`, wait for `KBACK`, drop `KBAV`, and wait
for `KBACK` to fall again before offering the next character. Dropping `KBAV`
only after `KBACK` is what keeps `KBSET` (`KBAV AND NOT R16`) from offering one
character twice. A key struck while the
program is not polling `R16` is lost rather than buffered, as it is on the vm;
a ring buffer in the bridge is a deliberate deviation, not a fix.

The grid the bridge owes the program is the vm's, in the root `README.md`,
down to a full row wrapping onto the next cleared one and a full last row
clearing the display. klib's `disp_putc` counts on it: it keeps its own column
and row pointer and never reads the display back. An HD44780's DDRAM rows are
not contiguous (0x00, 0x40, 0x14, 0x54 for 20x4), so a row start needs its own
`setCursor` rather than being written on.

The sketch is not in the repo. There is no `arduino-cli` on this machine to
compile it against, and an unverified sketch is worse than none; the two
protocols above are complete enough to write it (`USB Host Shield 2.0` for the
keyboard, `LiquidCrystal_I2C` for the display).

## KiCad boards

The same generator also emits KiCad 10 projects, so a board is built from the circuit rather than drawn: `python/logisim/kicad.py` turns a `Circuit` into a schematic, a netlist and a placed board, adding what Logisim does not model — the VCC and GND pins of every package, a 100nF decoupling capacitor per IC, a power header and the backplane connectors. `make logisim_kicad` writes them under `kicad/` and checks them with `kicad-cli`.

Each of the six blocks of `kone.circ` is a board of its own, generated from the same circuit, ERC clean and DRC clean:

| Board | ICs | Contents |
| --- | --- | --- |
| `regfile` | 86 | 32 registers, their bus drivers and the address decoder tree |
| `alu` | 27 | adder, logic banks and the result muxes |
| `io` | 23 | `R16`-`R19` and the two device handshakes |
| `sequencer` | 20 | microprogram counter and the nine 28C256 holding the microcode |
| `datapath` | 15 | bus and operand muxes, the latches around the ALU |
| `memory` | 8 | a 28C256 for the program, a 62256 for the RAM, the address split |

One screw terminal on the `io` board feeds the whole stack through the backplane -- there is no regulator on any board, so the supply must be regulated 5 V; `logisim/kicad/BACKPLANE.md` states the current to plan for. Logisim parts that are not real chips become real ones: a Logisim ROM is a 28C256, its RAM a 62256 on the same 28-pin pinout. The boards plug into a common backplane whose pinout `logisim/kicad/BACKPLANE.md` lists; it is derived from the top level of `kone.circ`, so a header pin carries the same signal on every board.

```python
from logisim.kicad import Board, write
write(Board("regfile", regfile(), columns=8), "logisim/kicad/regfile")
```

`Netlist` resolves what Logisim uses for wiring into real nets -- a tunnel is a
net name, a splitter ties a bus to its bits, `Ground`/`Power`/`Constant` are the
two rails -- and `Board` adds what a board needs and Logisim does not model: the
VCC and GND pins of each package, a 100nF per IC, the power header and the four
2x20 backplane connectors (`BACKPLANE` in `kicad.py`, written out as
`logisim/kicad/BACKPLANE.md`).

`write()` emits a project with its own symbol and footprint library, a schematic
in which every pin is stubbed to a net label, and a board whose footprints are
placed on the grid the chips were created in -- a row of registers stays a row.
Each IC carries its designation and reference on the silkscreen (`74377 R7`,
`U12`), so a board can be populated without the schematic. `make logisim_kicad`
runs `kicad-cli` ERC and DRC over the result and fails on an error; the board
has no tracks yet at that point, so open connections are the one class it lets
through.

`dsn()` writes the board as a Specctra design and `parse_ses()` reads back what
Freerouting made of it, so `make logisim_route` is a round trip that ends in the
same `.kicad_pcb`. Both ends are here because KiCad 10's CLI dropped Specctra.
Two things to know: every dimension in a `.dsn` is in the same units as its
coordinates, pad and via shapes included, and the session comes back at a
different scale than it went out, which is why `parse_ses()` calibrates on the
placements rather than on the resolution the file declares.

`build_kicad.py` lists the boards in `BOARDS`, one per block of `kone.circ`, and
derives the backplane from the top level of that circuit: `system_nets()` reads
which net a block's port is stubbed to, so `BUS_IN` on the register file and
`BUS` on the datapath end up on the same header pin. A port the CPU ties to a
rail is tied on the board instead of brought out.

`PARTS` maps the Logisim parts that are not chips onto real ones: a ROM becomes
a 28C256 and a RAM a 62256, both on the 28-pin JEDEC pinout. The ROM sits
permanently selected and output-enabled; the SRAM takes `OE#` from the write
strobe and `WE#` from the net named `n<STROBE>`, which the circuit provides.
Logisim's separate `din` and `dout` are one bus on the chip, so those two nets
are merged on the board.

## Fabrication

The four layers are signals on the outside, a solid `GND` plane on `In1.Cu` and
a solid `+5V` plane on `In2.Cu`. They cost more per board than two layers would,
and they are what makes the register file routable: the two rails are
a third of its connections, and taking them off the signal layers is the
difference between sixty connections left open and none.

A DIP pad is 1.4 mm around a 0.8 mm drill rather than the usual 1.6 mm, because
2.54 - 1.4 leaves 1.14 mm between two pins -- room for a 0.25 mm track with the
widest clearance the router is given (0.35 mm) to pass straight through a chip.
At 1.6 mm that gap is 0.94 mm,
the router runs out of vertical channels, and a bus bit stays open however long
it tries. Pins of a header take the plane solid instead of through a thermal
relief: in a 2.54 mm grid their neighbours leave no room for the two spokes DRC
asks for.

Tracks come from [Freerouting](https://github.com/freerouting/freerouting):
`make logisim_route` writes a Specctra `.dsn`, runs the router over it and reads
the `.ses` back into the board, since KiCad 10's command line can do neither.
Each board is routed, imported and checked with DRC. Now and then the router
leaves a connection open or lays two tracks into each other, and re-running it
unchanged does not help -- with a shuffled item order or another strategy it
reproduces the same short down to the coordinate. What does help is a different
clearance, so a board whose DRC fails is routed again with the next value in
`FREEROUTING_CLEARANCES` (0.3, 0.35, 0.25 mm). The register file wants the
narrow one, `datapath` the wide one. `FREEROUTING_PASSES` is an upper
bound rather than a cost: the router stops once a pass no longer improves, which
the small boards reach after five or six and the register file after twenty. The
six boards come out with no unrouted connection and no DRC violation, so there
is no manual pass in pcbnew. The jar
is not packaged anywhere -- put it where `FREEROUTING_JAR` points, or pass
`FREEROUTING_JAR=/path/to/freerouting.jar`.

`make logisim_kicad` checks a board that has no tracks yet, so open connections
are the one DRC class it lets through; `make logisim_route` and
`make logisim_gerbers` count them as errors. Gerbers carry both inner layers.
The projects bring their own symbol and
footprint library, so they do not depend on which version of KiCad's libraries
is installed.
