# kone as boards

`kicad/` holds the machine as six stackable printed boards, KiCad 10 projects
with their gerbers, an EEPROM image per memory and a parts list to order from.
Nothing here is drawn either: `python/kicad.py` is a second backend on the same
`Circuit` objects [`logisim/`](../logisim/README.md) writes its `.circ` files
from, so a change to a build script there reaches a board as well. Nothing
parses a generated file.

## Board format

All six boards share one outline, **302.88 x 415.82 mm**, four layers on 1.6 mm
FR-4, with four M3 holes 6 mm in from the corners and every backplane connector
at the same place on every board. Nothing on a board is rotated, so the stack
goes together in any order. `stacking()` in `python/build_kicad.py` fails the
build if a board disagrees, and the size above is the largest board's, measured
there -- it warns when the two have drifted apart. The gerbers are what a fab
goes by; `boards/BACKPLANE.md` carries the generated pinout.

## Build everything

```
make -C kicad route gerbers
```

- `boards` -- the KiCad projects under `boards/`, ERC and DRC clean
- `route` -- the same boards routed; some 20 minutes, and it wants
  `FREEROUTING_JAR`
- `gerbers` -- DRC again, then a fab ZIP per board in `boards/out/`
- `roms` -- one EEPROM image per chip into `roms/`

`route` and `gerbers` both build `boards`, which a single run makes once. Each
target has a section of its own below.

From the repo root the targets carry a `kicad_` prefix, inside this directory
they do not:

| From the root | Here | What it does |
| --- | --- | --- |
| `make kicad_boards` | `make boards` | the KiCad projects, then ERC and DRC |
| `make kicad_route` | `make route` | autoroute with Freerouting, then DRC |
| `make kicad_gerbers` | `make gerbers` | DRC, then gerbers and drills zipped per board |
| `make kicad_roms` | `make roms` | one EEPROM image per chip into `roms/` |
| `make kicad_clean` | `make clean` | the generated files, `boards/` included -- the root `make clean` leaves them alone |

## Layout

| Path | Contents |
| --- | --- |
| `python/kicad.py` | the backend: a `Circuit` as schematic, netlist and placed board |
| `python/build_kicad.py` | the six boards, the backplane and the parts list |
| `python/build_roms.py` | the EEPROM images |
| `boards/<board>/` | the generated KiCad projects, `boards/out/` their gerber zips |
| `boards/BACKPLANE.md` | the connector pinout, generated |
| `roms/` | the EEPROM images, one per chip, generated |
| `PARTS.md` | every chip and part the six boards need, generated |
| `Makefile` | the targets above |

The circuits themselves live in `logisim/python`, which the two build scripts
put on the path; that half does not know this one exists.

## The generator

A board is built from the circuit rather than drawn: `python/kicad.py` turns a `Circuit` into a schematic, a netlist and a placed board, adding what Logisim does not model — the VCC and GND pins of every package, a 100nF decoupling capacitor per IC, a power header and the backplane connectors. `make kicad_boards` writes them under `boards/` and checks them with `kicad-cli`.

Each of the six blocks of `kone.circ` is a board of its own, generated from the same circuit, ERC clean and DRC clean:

| Board | ICs | Contents |
| --- | --- | --- |
| `regfile` | 86 | 32 registers, their bus drivers and the address decoder tree |
| `alu` | 27 | adder, logic banks and the result muxes |
| `io` | 23 | `R16`-`R19` and the two device handshakes |
| `sequencer` | 20 | microprogram counter and the nine 28C256 holding the microcode |
| `datapath` | 15 | bus and operand muxes, the latches around the ALU |
| `memory` | 8 | a 28C256 for the program, a 62256 for the RAM, the address split |

One screw terminal on the `io` board feeds the whole stack through the backplane -- there is no regulator on any board, so the supply must be regulated 5 V; `boards/BACKPLANE.md` states the current to plan for. Logisim parts that are not real chips become real ones: a Logisim ROM is a 28C256, its RAM a 62256 on the same 28-pin pinout. The boards plug into a common backplane whose pinout `boards/BACKPLANE.md` lists; it is derived from the top level of `kone.circ`, so a header pin carries the same signal on every board.

```python
from kicad import Board, write
write(Board("regfile", regfile(), columns=8), "kicad/boards/regfile")
```

`Netlist` resolves what Logisim uses for wiring into real nets -- a tunnel is a
net name, a splitter ties a bus to its bits, `Ground`/`Power`/`Constant` are the
two rails -- and `Board` adds what a board needs and Logisim does not model: the
VCC and GND pins of each package, a 100nF per IC, the power header and the four
2x20 backplane connectors (`BACKPLANE` in `python/kicad.py`, written out as
`boards/BACKPLANE.md`).

`write()` emits a project with its own symbol and footprint library, a schematic
in which every pin is stubbed to a net label, and a board whose footprints are
placed on the grid the chips were created in -- a row of registers stays a row.
Each IC carries its designation and reference on the silkscreen (`74377 R7`,
`U12`), so a board can be populated without the schematic. `make kicad_boards`
runs `kicad-cli` ERC and DRC over the result and fails on an error; the board
has no tracks yet at that point, so open connections are the one class it lets
through.

`dsn()` writes the board as a Specctra design and `parse_ses()` reads back what
Freerouting made of it, so `make kicad_route` is a round trip that ends in the
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
`make kicad_route` writes a Specctra `.dsn`, runs the router over it and reads
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

`make kicad_boards` checks a board that has no tracks yet, so open connections
are the one DRC class it lets through; `make kicad_route` and
`make kicad_gerbers` count them as errors. Gerbers carry both inner layers.
The projects bring their own symbol and
footprint library, so they do not depend on which version of KiCad's libraries
is installed.

## Assembly

The six boards come out of `make kicad_gerbers` as ZIPs in `boards/out/`, one
per board, four layers each and all the same outline. What to do with them:

**Hold the `memory` board back.** On it the 62256's data pins are its data in
and data out merged, and data in is `BUS`, which the datapath's mux drives at
all times: the two fight on every cycle that is not a memory write. Logisim has
no conflict there, because data in and data out are separate nets and a mux
picks the ROM or the RAM. The board wants a 74245 between the bus and the chip,
enabled from the write strobe, and putting one in breaks the write path in
simulation, so it is not settled. The other five boards are unaffected.

**Stacking order does not matter.** Every board carries all four backplane
connectors, and a pin whose signal a board has no use for is a pass-through:
the pad is there, carrying the backplane net, with nothing else on that board
on it. Only the orientation matters, and pin 1 wears a square pad and a dot on
the silkscreen on every board. The four M3 holes sit 6 mm in from the corners
on all six, so one set of standoffs goes through the lot.

**Sockets.** `PARTS.md` counts one per DIP package. The eleven 28-pin memories
and the can oscillator want them for certain, since those are the parts you
pull to reprogram or to change the clock.

**The EEPROMs.** `make kicad_roms` writes one image per chip into
`roms/`, named after the label on the socket's silkscreen: `uLIT.bin`
into the chip marked `28C256 uLIT`, `prog.bin` into `28C256 prog` on the memory
board. `boards/BACKPLANE.md` has the table with the board and reference of each.
The nine microcode images are 256 bytes -- the address lines above A7 are
grounded, so a programmer filling the rest of the chip with anything is fine.
`LOGISIM_PROG` picks which kasm program becomes `prog.bin`.

**Power and clock.** One 5 V regulated supply into the screw terminal (J5) on
`io` feeds the whole stack; there is no regulator anywhere on it. X1, the can
oscillator, drives `CLK` with the jumper on J6 across 1-2. Across 2-3 the clock
comes from J7 instead, which is where an external generator or the Arduino
bridge single-steps the machine.

**Reset.** The microprogram counter is a 74377 and comes up wherever it likes,
so the sequencer gates its next address to zero while `NRES` is low. `io`
generates that: an RC (R2, C89) holds it down while the rails come up, U24
squares the edge, and shorting J8 resets by hand. Microaddress 0 is `BOOT`,
which sets the stack pointer and falls into FETCH -- the same thing
`cpu_reset()` does in the vm.

## Display and keyboard

Both devices hang off the backplane as plain 5 V logic; `boards/BACKPLANE.md`
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

The signals are the ones `boards/BACKPLANE.md` lists for the `io` board;
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

Two more wires are worth having: **J7 on the io board is the clock input** and
**J8 is reset**, and a free Mega pin on each turns the bridge into the single
step debugger. The stack
normally runs off X1, the 1 MHz can oscillator, with the jumper on J6 across
pins 1-2; move that jumper to 2-3 and `CLK` comes from J7 instead. Pulse it
from the sketch and the machine advances one clock at a time, which is the only
way to watch a microstep go by; pull J8 low first and the machine starts from
BOOT rather than wherever it happened to be. Both headers have `GND` on their
second pin, so the Mega's ground is already shared.

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

