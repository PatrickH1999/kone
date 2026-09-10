# kone as circuits

`logisim/` holds the machine as [Logisim
Evolution](https://github.com/logisim-evolution/) files built from 74xx-series
chips, so the ISA can be checked against something buildable from real logic.
`python/` generates them: nothing here is drawn by hand and nothing parses a
generated file. The same circuits become printed boards in
[`kicad/`](../kicad/README.md), which reads this directory rather than the
files it writes, so a change to a build script reaches both.

## Build everything

```
make -C logisim circ cpu test
```

- `circ` -- `regfile.circ`, `alu.circ` and `kone.circ`
- `cpu` -- `kone.circ` alone, on another program; `LOGISIM_PROG` defaults to
  `bin/display.bin`, which is what `circ` bakes in too
- `test` -- the four programs booted headlessly on `kone.circ`; about a minute,
  and it wants a JDK and `LOGISIM_JAR`

Each target has a section of its own below.

From the repo root the targets carry a `logisim_` prefix, inside this directory
they do not:

| From the root | Here | What it does |
| --- | --- | --- |
| `make logisim_circ` | `make circ` | every `python/build_*.py` -> `logisim/*.circ` |
| `make logisim_cpu` | `make cpu` | only `kone.circ`; `LOGISIM_PROG=bin/<name>.bin` picks its program |
| `make logisim_regfile`, `make logisim_alu` | `make regfile`, `make alu` | one circuit each |
| `make logisim_test` | `make test` | boot four programs on `kone.circ` in Logisim, headless |
| `make logisim_clean` | `make clean` | the generated files |

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
| `python/build_<circuit>.py` | one build script per circuit |
| `python/kone_microcode.py` | the microprogram `kone.circ` runs |
| `java/` | headless checks that run a generated file in Logisim |
| `*.circ` | the generated files |
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

