# logisim.py

Generates `.circ` files (logic circuits) for *logisim-evolution* so the `kone`
CPU can be built in code instead of with the mouse. The target circuit covers

1. __CPU__
2. __Keyboard__
3. __Display__

Project-internal tooling: plain scripts, no packaging, `python3` only, no
dependencies. Requires Python 3.9+.

## Layout

| Path | Contents |
| --- | --- |
| `logisim/python/logisim/core.py` | `Component`, `Wire`, `Circuit`, `Project`, grid checks |
| `logisim/python/logisim/components.py` | the concrete components and their port geometry |
| `logisim/python/build_*.py` | one build script per generated circuit |
| `logisim/*.circ` | the generated files |

`make circ` runs every `build_*.py`. A build script imports the library from its
own directory, so `python3 logisim/python/build_regfile.py` works from anywhere.

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
`WR`. `make regfile` builds it; `make circ` does too.

The 32 slices come first on the canvas, in an 8 x 4 grid whose rows are the
decoder groups, so the chips are in view when the file opens; the pins, the
74138 tree and the 7432 gates sit below them.

Logisim Evolution has no bidirectional `Pin`, so the bus leaves the circuit as
`BUS_IN` and `BUS_OUT`. Wire both to the same bus net in the parent: `BUS_OUT` is
high-Z unless `RD` selects a register.

## Where the port offsets come from

They are not guessed. Logisim Evolution's own jar was loaded headlessly and
asked, for every component and attribute combination, where it puts its pins
(`InstanceFactory.getPorts()`), and the generated file was then read back with
`LogisimFile.load` to compare the offsets the library computes against the ones
the simulator reports. All 1419 combinations agree for v4.1.0. If a future
Logisim moves a pin, that comparison is the thing to re-run — the probe is four
short Java files against
`/usr/share/java/logisim-evolution/logisim-evolution.jar`.

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

`make alu` builds it; `make circ` does too.
