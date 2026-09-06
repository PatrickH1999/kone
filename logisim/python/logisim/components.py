"""Concrete Logisim components.

Port offsets are Logisim Evolution 4.1's own, read out of the running
simulator; tools/README.md says how they were obtained. Every port_spec()
returns ports in Logisim's end order, which is what the .circ format keys on.
"""

from .core import Component, PortError, rotate

FACINGS = ("east", "west", "north", "south")


def _facing_attrs(facing, default):
    return {} if facing in (None, default) else {"facing": facing}


def _letters(prefix, n):
    """{"A": "in0", "0": "in0", ...} so gates take either name."""
    out = {}
    for i in range(n):
        out[chr(ord("A") + i)] = f"{prefix}{i}"
        out[str(i)] = f"{prefix}{i}"
    return out


# --------------------------------------------------------------------------
# Wiring
# --------------------------------------------------------------------------

class Pin(Component):
    LIB = "Wiring"
    NAME = "Pin"
    IS_PIN = True
    PORTS = (("pin", 0, 0),)
    ALIASES = {"in": "pin", "out": "pin", "q": "pin", "d": "pin", "value": "pin"}

    def __init__(self, x, y, label=None, width=1, output=False, facing=None,
                 **attrs):
        a = {}
        if facing is not None:
            a["facing"] = facing
        elif output:
            a["facing"] = "west"
        if output:
            a["type"] = "output"
        if width != 1:
            a["width"] = width
        if label is not None:
            a["label"] = label
        a.update(attrs)
        super().__init__(x, y, **a)


class Probe(Component):
    LIB = "Wiring"
    NAME = "Probe"
    PORTS = (("in", 0, 0),)

    def __init__(self, x, y, label=None, radix=None, facing=None, **attrs):
        super().__init__(x, y, label=label, radix=radix,
                         **_facing_attrs(facing, "east"), **attrs)


class Tunnel(Component):
    """Named net; two tunnels with the same label are the same wire."""

    LIB = "Wiring"
    NAME = "Tunnel"
    PORTS = (("io", 0, 0),)
    ALIASES = {"in": "io", "out": "io"}

    def __init__(self, x, y, label, width=1, facing=None, **attrs):
        a = {"label": label}
        if width != 1:
            a["width"] = width
        a.update(_facing_attrs(facing, "west"))
        a.update(attrs)
        super().__init__(x, y, **a)


class Constant(Component):
    LIB = "Wiring"
    NAME = "Constant"
    PORTS = (("out", 0, 0),)

    def __init__(self, x, y, value=1, width=1, facing=None, **attrs):
        a = {"value": value if isinstance(value, str) else hex(value)}
        if width != 1:
            a["width"] = width
        a.update(_facing_attrs(facing, "east"))
        a.update(attrs)
        super().__init__(x, y, **a)


class Power(Component):
    LIB = "Wiring"
    NAME = "Power"
    PORTS = (("out", 0, 0),)

    def __init__(self, x, y, width=1, facing=None, **attrs):
        a = {} if width == 1 else {"width": width}
        a.update(_facing_attrs(facing, "north"))
        super().__init__(x, y, **a, **attrs)


class Ground(Component):
    LIB = "Wiring"
    NAME = "Ground"
    PORTS = (("out", 0, 0),)

    def __init__(self, x, y, width=1, facing=None, **attrs):
        a = {} if width == 1 else {"width": width}
        a.update(_facing_attrs(facing, "south"))
        super().__init__(x, y, **a, **attrs)


class Clock(Component):
    LIB = "Wiring"
    NAME = "Clock"
    PORTS = (("out", 0, 0),)

    def __init__(self, x, y, label=None, high=None, low=None, facing=None,
                 **attrs):
        super().__init__(x, y, label=label, highDuration=high, lowDuration=low,
                         **_facing_attrs(facing, "east"), **attrs)


class BitExtender(Component):
    LIB = "Wiring"
    NAME = "Bit Extender"
    PORTS = (("out", 0, 0), ("in", -40, 0))

    def __init__(self, x, y, in_width=8, out_width=16, type="sign", **attrs):
        super().__init__(x, y, in_width=in_width, out_width=out_width,
                         type=type, **attrs)


class Splitter(Component):
    """fanout ends are numbered 0..fanout-1 from the end nearest the trunk."""

    LIB = "Wiring"
    NAME = "Splitter"

    def __init__(self, x, y, fanout=2, incoming=2, appear="left", facing=None,
                 spacing=1, bits=None, **attrs):
        a = {"fanout": fanout, "incoming": incoming, "appear": appear}
        if spacing != 1:
            a["spacing"] = spacing
        a.update(_facing_attrs(facing, "east"))
        if bits is not None:
            for i, group in enumerate(bits):
                a[f"bit{i}"] = "none" if group is None else group
        a.update(attrs)
        super().__init__(x, y, **a)

    def port_spec(self):
        fanout = int(self.get("fanout", 2))
        pitch = int(self.get("spacing", 1)) * 10
        facing = self.get("facing", "east")
        appear = self.get("appear", "left")
        # "left"/"right" are relative to the facing, so they swap with it; the
        # centred layouts are the same list mirrored on the vertical facings.
        if appear in ("center", "legacy"):
            offs = [pitch * (k - 1) - pitch * (fanout // 2)
                    for k in range(1, fanout + 1)]
            if facing in ("north", "south"):
                offs = [-o - (pitch if fanout % 2 == 0 else 0) for o in offs]
        else:
            near = [10 + pitch * (k - 1) for k in range(1, fanout + 1)]
            far = [-(10 + pitch * (fanout - k)) for k in range(1, fanout + 1)]
            flip = (facing in ("east", "south")) == (appear == "left")
            offs = far if flip else near
            if facing in ("north", "south"):
                offs = [-o for o in offs]
        depth = {"east": (20, 0), "west": (-20, 0),
                 "north": (0, -20), "south": (0, 20)}[facing]
        spec = [("in", 0, 0)]
        for i, o in enumerate(offs):
            if facing in ("east", "west"):
                spec.append((str(i), depth[0], o))
            else:
                spec.append((str(i), o, depth[1]))
        return spec

    @property
    def ALIASES(self):
        return {f"out{i}": str(i) for i in range(int(self.get("fanout", 2)))}


# --------------------------------------------------------------------------
# Gates
# --------------------------------------------------------------------------

# Everything follows one formula bar these five, which Logisim spreads wider.
_GATE_SPECIAL = {
    (50, 2): (-20, 20),
    (50, 3): (-20, 0, 20),
    (70, 2): (-20, 20),
    (70, 3): (-30, 0, 30),
    (70, 4): (-30, -10, 10, 30),
}


def gate_input_offsets(size, inputs):
    special = _GATE_SPECIAL.get((size, inputs))
    if special is not None:
        return list(special)
    if inputs % 2:
        return [-5 * (inputs - 1) + 10 * i for i in range(inputs)]
    return [-5 * inputs + 10 * i + (10 if i >= inputs // 2 else 0)
            for i in range(inputs)]


class _Gate(Component):
    LIB = "Gates"
    DEFAULT_SIZE = 50
    BONUS = 0            # extra body length before the input pins
    NEGATED = False      # bubble on the output adds another 10

    def __init__(self, x, y, inputs=2, size=None, facing=None, width=None,
                 label=None, negate=(), **attrs):
        a = {}
        if inputs != 2:
            a["inputs"] = inputs
        if size is not None and size != self.DEFAULT_SIZE:
            a["size"] = size
        if width not in (None, 1):
            a["width"] = width
        if label is not None:
            a["label"] = label
        a.update(_facing_attrs(facing, "east"))
        for i in negate:
            a[f"negate{i}"] = True
        a.update(attrs)
        super().__init__(x, y, **a)

    def port_spec(self):
        size = int(self.get("size", self.DEFAULT_SIZE))
        inputs = int(self.get("inputs", 2))
        facing = self.get("facing", "east")
        body = size + self.BONUS + (10 if self.NEGATED else 0)
        spec = [("out", 0, 0)]
        for i, (dx, dy) in enumerate(_data_positions(
                facing, -body, gate_input_offsets(size, inputs))):
            spec.append((f"in{i}", dx, dy))
        return spec

    @property
    def ALIASES(self):
        a = _letters("in", int(self.get("inputs", 2)))
        a.update({"y": "out", "q": "out"})
        return a


class AndGate(_Gate):
    NAME = "AND Gate"


class OrGate(_Gate):
    NAME = "OR Gate"


class NandGate(_Gate):
    NAME = "NAND Gate"
    NEGATED = True


class NorGate(_Gate):
    NAME = "NOR Gate"
    NEGATED = True


class XorGate(_Gate):
    NAME = "XOR Gate"
    BONUS = 10


class XnorGate(_Gate):
    NAME = "XNOR Gate"
    BONUS = 10
    NEGATED = True


class OddParity(_Gate):
    NAME = "Odd Parity"


class EvenParity(_Gate):
    NAME = "Even Parity"


class NotGate(Component):
    LIB = "Gates"
    NAME = "NOT Gate"
    ALIASES = {"a": "in", "0": "in", "y": "out", "q": "out"}

    def __init__(self, x, y, size=None, facing=None, width=None, label=None,
                 **attrs):
        a = {}
        if size is not None and size != 30:
            a["size"] = size
        if width not in (None, 1):
            a["width"] = width
        if label is not None:
            a["label"] = label
        a.update(_facing_attrs(facing, "east"))
        a.update(attrs)
        super().__init__(x, y, **a)

    def port_spec(self):
        size = int(self.get("size", 30))
        facing = self.get("facing", "east")
        return [("out", 0, 0), ("in",) + rotate(-size, 0, facing)]


class Buffer(Component):
    LIB = "Gates"
    NAME = "Buffer"
    ALIASES = {"a": "in", "0": "in", "y": "out"}

    def __init__(self, x, y, facing=None, width=None, label=None, **attrs):
        a = {} if width in (None, 1) else {"width": width}
        if label is not None:
            a["label"] = label
        a.update(_facing_attrs(facing, "east"))
        super().__init__(x, y, **a, **attrs)

    def port_spec(self):
        facing = self.get("facing", "east")
        return [("out", 0, 0), ("in",) + rotate(-20, 0, facing)]


class ControlledBuffer(Component):
    LIB = "Gates"
    NAME = "Controlled Buffer"
    BODY = 20
    ALIASES = {"a": "in", "y": "out", "control": "en", "oe": "en"}

    def __init__(self, x, y, facing=None, width=None, control="right", **attrs):
        a = {} if width in (None, 1) else {"width": width}
        if control != "right":
            a["control"] = control
        a.update(_facing_attrs(facing, "east"))
        super().__init__(x, y, **a, **attrs)

    def port_spec(self):
        facing = self.get("facing", "east")
        side = 10 if self.get("control", "right") == "right" else -10
        return [("out", 0, 0),
                ("in",) + rotate(-self.BODY, 0, facing),
                ("en",) + rotate(-self.BODY + 10, side, facing)]


class ControlledInverter(ControlledBuffer):
    NAME = "Controlled Inverter"
    BODY = 30


# --------------------------------------------------------------------------
# Plexers
#
# Data ports run top-to-bottom on a horizontal facing and left-to-right on a
# vertical one, so they mirror rather than rotate. "behind"/"ahead" below are
# relative to the facing.
# --------------------------------------------------------------------------

def _along(facing, distance):
    return {"east": (distance, 0), "west": (-distance, 0),
            "north": (0, -distance), "south": (0, distance)}[facing]


def _across(facing, offset):
    return (0, offset) if facing in ("east", "west") else (-offset, 0)


def _data_positions(facing, depth, offsets):
    ahead = _along(facing, depth)
    if facing in ("east", "west"):
        return [(ahead[0], o) for o in offsets]
    return [(o, ahead[1]) for o in offsets]


def _select_offsets(select):
    n = 1 << select
    if select == 1:
        return [-10, 10]
    return [10 * i - 10 * (n // 2) for i in range(n)]


class _Plexer(Component):
    LIB = "Plexers"

    def __init__(self, x, y, select=1, width=None, facing=None, enable=False,
                 selloc=None, **attrs):
        a = {}
        if select != 1:
            a["select"] = select
        if width not in (None, 1):
            a["width"] = width
        if enable != self.ENABLE_DEFAULT:
            a["enable"] = bool(enable)
        if selloc not in (None, "bl"):
            a["selloc"] = selloc
        a.update(_facing_attrs(facing, "east"))
        a.update(attrs)
        super().__init__(x, y, **a)

    def _common(self):
        select = int(self.get("select", 1))
        facing = self.get("facing", "east")
        selloc = self.get("selloc", "bl")
        enable = bool(self.get("enable", self.ENABLE_DEFAULT))
        n = 1 << select
        side = 10 * max(2, n // 2)
        if selloc == "tr":
            side = -side
        return select, facing, n, side, enable


class Multiplexer(_Plexer):
    NAME = "Multiplexer"
    ENABLE_DEFAULT = False

    def port_spec(self):
        select, facing, n, side, enable = self._common()
        depth = -(30 if select == 1 else 40)
        spec = [(f"in{i}", dx, dy) for i, (dx, dy) in
                enumerate(_data_positions(facing, depth, _select_offsets(select)))]
        sx, sy = _along(facing, -20)
        ax, ay = _across(facing, side)
        spec.append(("sel", sx + ax, sy + ay))
        if enable:
            ex, ey = _along(facing, -10)
            spec.append(("en", ex + ax, ey + ay))
        spec.append(("out", 0, 0))
        return spec

    @property
    def ALIASES(self):
        a = _letters("in", 1 << int(self.get("select", 1)))
        a.update({"s": "sel", "select": "sel"})
        return a


class Demultiplexer(_Plexer):
    NAME = "Demultiplexer"
    ENABLE_DEFAULT = False

    def port_spec(self):
        select, facing, n, side, enable = self._common()
        depth = 30 if select == 1 else 40
        spec = [(f"out{i}", dx, dy) for i, (dx, dy) in
                enumerate(_data_positions(facing, depth, _select_offsets(select)))]
        sx, sy = _along(facing, 20)
        ax, ay = _across(facing, side)
        spec.append(("sel", sx + ax, sy + ay))
        if enable:
            ex, ey = _along(facing, 10)
            spec.append(("en", ex + ax, ey + ay))
        spec.append(("in", 0, 0))
        return spec

    @property
    def ALIASES(self):
        a = _letters("out", 1 << int(self.get("select", 1)))
        a.update({"s": "sel", "select": "sel"})
        return a


class Decoder(_Plexer):
    NAME = "Decoder"
    ENABLE_DEFAULT = True

    def port_spec(self):
        select, facing, n, _side, enable = self._common()
        selloc = self.get("selloc", "bl")
        depth = 10 if select == 1 else 20
        # The output strip sits on the negative side for bl on a horizontal
        # facing, and swaps for both tr and the vertical facings.
        negative = (selloc == "bl") == (facing in ("east", "west"))
        if select == 1:
            offsets = [-30 + 20 * i for i in range(2)] if negative \
                else [10 + 20 * i for i in range(2)]
        else:
            base = -10 * n if negative else 0
            offsets = [base + 10 * i for i in range(n)]
        spec = [(f"out{i}", dx, dy) for i, (dx, dy) in
                enumerate(_data_positions(facing, depth, offsets))]
        spec.append(("sel", 0, 0))
        if enable:
            spec.append(("en",) + _along(facing, -10))
        return spec

    @property
    def ALIASES(self):
        a = _letters("out", 1 << int(self.get("select", 1)))
        a.update({"s": "sel", "select": "sel"})
        return a


class BitSelector(Component):
    LIB = "Plexers"
    NAME = "BitSelector"
    ALIASES = {"s": "sel", "select": "sel"}

    def __init__(self, x, y, width=8, group=1, facing=None, selloc=None,
                 **attrs):
        a = {"width": width}
        if group != 1:
            a["group"] = group
        if selloc not in (None, "bl"):
            a["selloc"] = selloc
        a.update(_facing_attrs(facing, "east"))
        super().__init__(x, y, **a, **attrs)

    SEL = {"east": (-10, 10), "west": (10, -10),
           "north": (-10, 10), "south": (-10, -10)}

    def port_spec(self):
        facing = self.get("facing", "east")
        sx, sy = self.SEL[facing]
        if self.get("selloc", "bl") != "bl":
            sx, sy = (sx, -sy) if facing in ("east", "west") else (-sx, sy)
        return [("out", 0, 0), ("in",) + _along(facing, -30), ("sel", sx, sy)]


# --------------------------------------------------------------------------
# Arithmetic (no facing attribute)
# --------------------------------------------------------------------------

class _Arith(Component):
    LIB = "Arithmetic"

    def __init__(self, x, y, width=8, **attrs):
        super().__init__(x, y, width=width, **attrs)


class Adder(_Arith):
    NAME = "Adder"
    PORTS = (("a", -40, -10), ("b", -40, 10), ("out", 0, 0),
             ("cin", -20, -20), ("cout", -20, 20))
    ALIASES = {"A": "a", "B": "b", "sum": "out", "s": "out",
               "carryin": "cin", "carryout": "cout"}


class Subtractor(_Arith):
    NAME = "Subtractor"
    PORTS = (("a", -40, -10), ("b", -40, 10), ("out", 0, 0),
             ("bin", -20, -20), ("bout", -20, 20))
    ALIASES = {"A": "a", "B": "b", "minuend": "a", "subtrahend": "b",
               "diff": "out", "borrowin": "bin", "borrowout": "bout"}


class Multiplier(_Arith):
    NAME = "Multiplier"
    PORTS = (("a", -40, -10), ("b", -40, 10), ("out", 0, 0),
             ("cin", -20, -20), ("cout", -20, 20))
    ALIASES = {"A": "a", "B": "b", "product": "out"}


class Divider(_Arith):
    NAME = "Divider"
    PORTS = (("lower", -40, -10), ("divisor", -40, 10), ("out", 0, 0),
             ("upper", -20, -20), ("rem", -20, 20))
    ALIASES = {"a": "lower", "b": "divisor", "quotient": "out",
               "remainder": "rem"}


class Negator(_Arith):
    NAME = "Negator"
    PORTS = (("in", -40, 0), ("out", 0, 0))
    ALIASES = {"a": "in"}


class Comparator(_Arith):
    NAME = "Comparator"
    PORTS = (("a", -40, -10), ("b", -40, 10),
             ("gt", 0, -10), ("eq", 0, 0), ("lt", 0, 10))
    ALIASES = {"A": "a", "B": "b", "greater": "gt", "equal": "eq", "less": "lt"}

    def __init__(self, x, y, width=8, mode=None, **attrs):
        super().__init__(x, y, width=width, mode=mode, **attrs)


class Shifter(_Arith):
    NAME = "Shifter"
    PORTS = (("in", -40, -10), ("dist", -40, 10), ("out", 0, 0))
    ALIASES = {"a": "in", "shift": "dist", "amount": "dist"}

    def __init__(self, x, y, width=8, shift="ll", **attrs):
        super().__init__(x, y, width=width, shift=shift, **attrs)


# --------------------------------------------------------------------------
# Memory (logisim_evolution appearance; the others size themselves from text)
# --------------------------------------------------------------------------

class _EvolutionShape(Component):
    LIB = "Memory"
    APPEARANCE = "logisim_evolution"

    def _check_appearance(self):
        appearance = self.get("appearance", self.APPEARANCE)
        if appearance != self.APPEARANCE:
            raise PortError(
                f"{self.NAME}: port offsets are only modelled for "
                f"appearance={self.APPEARANCE!r}, not {appearance!r}")


class Register(_EvolutionShape):
    NAME = "Register"
    PORTS = (("out", 60, 30), ("in", 0, 30), ("clk", 0, 70),
             ("clr", 30, 90), ("en", 0, 50))
    ALIASES = {"q": "out", "d": "in", "ck": "clk", "clock": "clk",
               "reset": "clr", "enable": "en"}

    def __init__(self, x, y, width=8, trigger=None, label=None, **attrs):
        super().__init__(x, y, width=width, trigger=trigger, label=label,
                         **attrs)

    def port_spec(self):
        self._check_appearance()
        return self.PORTS


class _FlipFlop(_EvolutionShape):
    DATA = ()

    def __init__(self, x, y, trigger=None, label=None, **attrs):
        super().__init__(x, y, trigger=trigger, label=label, **attrs)

    def port_spec(self):
        self._check_appearance()
        spec = [(name, -10, 10 + 20 * i) for i, name in enumerate(self.DATA)]
        spec.append(("clk", -10, 50))
        spec += [("q", 50, 10), ("qnot", 50, 50),
                 ("reset", 20, 60), ("preset", 20, 0)]
        return spec

    @property
    def ALIASES(self):
        return {"ck": "clk", "clock": "clk", "clr": "reset", "set": "preset",
                "notq": "qnot", "q_": "qnot"}


class DFlipFlop(_FlipFlop):
    NAME = "D Flip-Flop"
    DATA = ("d",)


class TFlipFlop(_FlipFlop):
    NAME = "T Flip-Flop"
    DATA = ("t",)


class JKFlipFlop(_FlipFlop):
    NAME = "J-K Flip-Flop"
    DATA = ("j", "k")


class SRFlipFlop(_FlipFlop):
    NAME = "S-R Flip-Flop"
    DATA = ("s", "r")


class Rom(_EvolutionShape):
    NAME = "ROM"
    PORTS = (("addr", 0, 10), ("data", 240, 60))
    ALIASES = {"a": "addr", "d": "data", "out": "data"}

    def __init__(self, x, y, addr_width=8, data_width=8, contents=None,
                 label=None, **attrs):
        super().__init__(x, y, addrWidth=addr_width, dataWidth=data_width,
                         contents=contents, label=label, **attrs)

    def port_spec(self):
        self._check_appearance()
        return self.PORTS


class Ram(_EvolutionShape):
    """Separate data-in / data-out bus (databus="bibus", Logisim's default)."""

    NAME = "RAM"
    ALIASES = {"a": "addr", "d": "din", "in": "din", "out": "dout",
               "ck": "clk", "clock": "clk"}

    def __init__(self, x, y, addr_width=8, data_width=8, enables=None,
                 clear_pin=None, trigger=None, label=None, **attrs):
        super().__init__(x, y, addrWidth=addr_width, dataWidth=data_width,
                         enables=enables, clearpin=clear_pin, trigger=trigger,
                         label=label, **attrs)

    def port_spec(self):
        self._check_appearance()
        databus = self.get("databus", "bibus")
        if databus != "bibus":
            raise PortError(
                f"RAM: only databus='bibus' (separate in and out) is modelled, "
                f"not {databus!r}")
        spec = [("addr", 0, 10), ("dout", 240, 90), ("din", 0, 90)]
        if self.get("enables", "byte") == "byte":
            spec.append(("oe", 0, 60))
        spec += [("we", 0, 50), ("clk", 0, 70)]
        if self.get("clearpin", False) in (True, "true"):
            spec.append(("clr", 40, 0))
        return spec


# --------------------------------------------------------------------------
# I/O
# --------------------------------------------------------------------------

class Led(Component):
    LIB = "I/O"
    NAME = "LED"
    PORTS = (("in", 0, 0),)

    def __init__(self, x, y, label=None, facing=None, color=None, **attrs):
        a = {"label": label, "color": color}
        a.update(_facing_attrs(facing, "west"))
        super().__init__(x, y, **a, **attrs)


class Button(Component):
    LIB = "I/O"
    NAME = "Button"
    PORTS = (("out", 0, 0),)

    def __init__(self, x, y, label=None, facing=None, **attrs):
        super().__init__(x, y, label=label, **_facing_attrs(facing, "east"),
                         **attrs)


class SevenSegment(Component):
    LIB = "I/O"
    NAME = "7-Segment Display"
    PORTS = (("a", 20, 0), ("b", 30, 0), ("c", 20, 60), ("d", 10, 60),
             ("e", 0, 60), ("f", 10, 0), ("g", 0, 0), ("dp", 30, 60))

    def __init__(self, x, y, label=None, **attrs):
        super().__init__(x, y, label=label, **attrs)


class HexDigit(Component):
    LIB = "I/O"
    NAME = "Hex Digit Display"
    PORTS = (("in", 0, 0), ("dp", 20, 0))

    def __init__(self, x, y, label=None, **attrs):
        super().__init__(x, y, label=label, **attrs)


class DipSwitch(Component):
    LIB = "I/O"
    NAME = "DipSwitch"

    def __init__(self, x, y, number=8, label=None, facing=None, **attrs):
        a = {"number": number, "label": label}
        a.update(_facing_attrs(facing, "north"))
        super().__init__(x, y, **a, **attrs)

    def port_spec(self):
        return [(str(i), 10 * (i + 1), 0)
                for i in range(int(self.get("number", 8)))]


class Keyboard(Component):
    LIB = "I/O"
    NAME = "Keyboard"
    PORTS = (("clr", 20, 10), ("clk", 0, 0), ("re", 10, 10),
             ("avail", 130, 10), ("data", 140, 10))
    ALIASES = {"ck": "clk", "read": "re", "out": "data"}

    def __init__(self, x, y, buflen=None, trigger=None, **attrs):
        super().__init__(x, y, buflen=buflen, trigger=trigger, **attrs)


class Tty(Component):
    LIB = "I/O"
    NAME = "TTY"
    PORTS = (("clr", 20, 10), ("clk", 0, 0), ("we", 10, 10), ("data", 0, -10))
    ALIASES = {"ck": "clk", "in": "data", "write": "we"}

    def __init__(self, x, y, rows=None, cols=None, trigger=None, **attrs):
        super().__init__(x, y, rows=rows, cols=cols, trigger=trigger, **attrs)


# --------------------------------------------------------------------------
# TTL
#
# A DIP package: pins 1..n/2 run left to right along the bottom edge, then
# n/2+1..n right to left along the top. GND (pin n/2) and VCC (pin n) get no
# port unless VccGndPorts is set, which is not modelled.
# --------------------------------------------------------------------------

class _TtlChip(Component):
    LIB = "TTL"
    PINS = ()           # DIP pin names, index 0 = pin 1; None on GND and VCC
    INPUTS = ()         # pins that have to be driven; check() reports the rest
    BOTTOM = 30         # loc to the bottom pin row; the top row is always -30

    def __init__(self, x, y, facing=None, label=None, **attrs):
        a = dict(_facing_attrs(facing, "east"))
        if label is not None:
            a["label"] = label
        a.update(attrs)
        super().__init__(x, y, **a)

    def port_spec(self):
        if self.get("VccGndPorts"):
            raise PortError(
                f"{self.NAME}: port offsets are only modelled without the "
                f"VccGndPorts pins")
        facing = self.get("facing", "east")
        half = len(self.PINS) // 2
        spec = []
        for i, name in enumerate(self.PINS):
            if name is None:
                continue
            if i < half:
                dx, dy = 10 + 20 * i, self.BOTTOM
            else:
                dx, dy = 10 + 20 * (len(self.PINS) - 1 - i), -30
            spec.append((name, *rotate(dx, dy, facing)))
        return spec


class Ttl7404(_TtlChip):
    NAME = "7404"
    INPUTS = tuple(f"A{i}" for i in range(1, 7))
    PINS = ("A1", "Y1", "A2", "Y2", "A3", "Y3", None,
            "Y4", "A4", "Y5", "A5", "Y6", "A6", None)


class Ttl7408(_TtlChip):
    NAME = "7408"
    INPUTS = tuple(f"{p}{i}" for i in range(1, 5) for p in "AB")
    PINS = ("A1", "B1", "Y1", "A2", "B2", "Y2", None,
            "Y3", "A3", "B3", "Y4", "A4", "B4", None)


class Ttl7411(_TtlChip):
    NAME = "7411"
    INPUTS = tuple(f"{p}{i}" for i in range(1, 4) for p in "ABC")
    PINS = ("A1", "B1", "A2", "B2", "C2", "Y2", None,
            "Y3", "A3", "B3", "C3", "Y1", "C1", None)


class Ttl7421(_TtlChip):
    NAME = "7421"
    INPUTS = tuple(f"{p}{i}" for i in range(1, 3) for p in "ABCD")
    PINS = ("A1", "B1", None, "C1", "D1", "Y1", None,
            "Y2", "D2", "C2", None, "B2", "A2", None)


class Ttl7427(_TtlChip):
    NAME = "7427"
    INPUTS = Ttl7411.INPUTS
    PINS = Ttl7411.PINS


class Ttl7432(_TtlChip):
    NAME = "7432"
    INPUTS = Ttl7408.INPUTS
    PINS = ("A1", "B1", "Y1", "A2", "B2", "Y2", None,
            "Y3", "B3", "A3", "Y4", "B4", "A4", None)


class Ttl7486(_TtlChip):
    NAME = "7486"
    INPUTS = Ttl7408.INPUTS
    PINS = Ttl7408.PINS


class Ttl74138(_TtlChip):
    NAME = "74138"
    INPUTS = ("A", "B", "C", "nG2A", "nG2B", "G1")
    PINS = ("A", "B", "C", "nG2A", "nG2B", "G1", "nY7", None,
            "nY6", "nY5", "nY4", "nY3", "nY2", "nY1", "nY0", None)


class Ttl74151(_TtlChip):
    NAME = "74151"
    INPUTS = tuple(f"D{i}" for i in range(8)) + ("A", "B", "C", "nG")
    PINS = ("D3", "D2", "D1", "D0", "Y", "W", "nG", None,
            "C", "B", "A", "D7", "D6", "D5", "D4", None)


class Ttl74153(_TtlChip):
    NAME = "74153"
    BOTTOM = 50
    INPUTS = ("S0", "S1", "n1E", "n2E") + tuple(
        f"{half}D{i}" for half in (1, 2) for i in range(4))
    PINS = ("n1E", "S1", "1D3", "1D2", "1D1", "1D0", "1Y", None,
            "2Y", "2D0", "2D1", "2D2", "2D3", "S0", "n2E", None)


class Ttl74157(_TtlChip):
    NAME = "74157"
    INPUTS = ("SELECT", "nSTROBE") + tuple(
        f"{i}{p}" for i in range(1, 5) for p in "AB")
    PINS = ("SELECT", "1A", "1B", "1Y", "2A", "2B", "2Y", None,
            "3Y", "3B", "3A", "4Y", "4B", "4A", "nSTROBE", None)


class Ttl74245(_TtlChip):
    NAME = "74245"
    # A and B follow DIR, so which side is an input is not fixed.
    INPUTS = ("DIR", "nOE")
    PINS = ("DIR", "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", None,
            "B8", "B7", "B6", "B5", "B4", "B3", "B2", "B1", "nOE", None)


class Ttl74283(_TtlChip):
    NAME = "74283"
    INPUTS = ("CIN",) + tuple(f"{p}{i}" for i in range(1, 5) for p in "AB")
    PINS = ("S2", "B2", "A2", "S1", "A1", "B1", "CIN", None,
            "C4", "S4", "B4", "A4", "S3", "A3", "B3", None)


class Ttl74377(_TtlChip):
    NAME = "74377"
    BOTTOM = 50
    INPUTS = ("nCLKen", "CLK") + tuple(f"D{i}" for i in range(1, 9))
    PINS = ("nCLKen", "Q1", "D1", "D2", "Q2", "Q3", "D3", "D4", "Q4", None,
            "CLK", "Q5", "D5", "D6", "Q6", "Q7", "D7", "D8", "Q8", None)
