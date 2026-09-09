"""KiCad backend: the same Circuit the .circ writer uses, as a board project.

The netlist is derived from the circuit, not from the generated file, so a
change to a build script reaches Logisim and KiCad alike. Logisim's own parts
have no place on a board: a Tunnel is a net name, a Splitter joins a bus to its
bits, a Pin becomes a header pin, Ground/Power/Constant become the two rails.

The circuits themselves come from logisim/python, which the entry scripts put
on the path -- this backend reads that model, nothing there knows about it.
"""

import math
import os

from logisim.components import _TtlChip


class NetlistError(ValueError):
    pass


# A 28-pin JEDEC memory, the pinout 28C256 and 62256 share.
JEDEC28 = {
    1: "A14",
    2: "A12",
    3: "A7",
    4: "A6",
    5: "A5",
    6: "A4",
    7: "A3",
    8: "A2",
    9: "A1",
    10: "A0",
    11: "D0",
    12: "D1",
    13: "D2",
    14: "GND",
    15: "D3",
    16: "D4",
    17: "D5",
    18: "D6",
    19: "D7",
    20: "nCE",
    21: "A10",
    22: "nOE",
    23: "A11",
    24: "A9",
    25: "A8",
    26: "A13",
    27: "nWE",
    28: "VCC",
}

PARTS = {
    "ROM": ("28C256", "DIP-28_W15.24mm"),
    "RAM": ("62256", "DIP-28_W15.24mm"),
}

# footprint -> (lead pitch, drill, pad diameter) for the two-lead parts the
# boards need beyond the logic: bulk capacitor, power entry, indicator.
TWO_PAD = {
    "CP_Radial_D6.3mm_P2.50mm": (2.5, 0.9, 1.8),
    "TerminalBlock_2x5.08mm": (5.08, 1.3, 2.6),
    "R_Axial_P10.16mm": (10.16, 0.9, 1.8),
    "LED_D3.0mm_P2.54mm": (2.54, 0.9, 1.8),
}


class Netlist:
    """Chips, connectors and the nets between them, all named."""

    def __init__(self, circuit):
        self.circuit = circuit
        self.chips = [c for c in circuit.components if isinstance(c, _TtlChip)]
        # Logisim's memories are not parts; PARTS says which package they are.
        self.memories = [c for c in circuit.components if c.NAME in PARTS]
        self._build()

    # -- net extraction ---------------------------------------------------

    def _build(self):
        nets = self.circuit.nets()
        index = self.circuit.ports_at()
        at = {}  # location -> net id
        for i, net in enumerate(nets):
            for point in net:
                at[point] = i

        def label(i):
            names = sorted(
                {
                    c.get("label")
                    for p in nets[i]
                    for c in index.get(p, ())
                    if c.NAME == "Tunnel" and c.get("label")
                }
            )
            return names[0] if names else None

        width = [1] * len(nets)
        for comp in self.circuit.components:
            if comp.NAME in ("Tunnel", "Pin", "Splitter", "Constant"):
                w = int(
                    comp.get("width", 1)
                    if comp.NAME != "Splitter"
                    else comp.get("incoming", 2)
                )
                if comp.NAME == "Splitter":
                    width[at[comp.port("in")]] = w
                else:
                    for _, x, y in comp.ports():
                        width[at[(x, y)]] = max(width[at[(x, y)]], w)

        parent = {}

        def find(k):
            parent.setdefault(k, k)
            while parent[k] != k:
                parent[k] = parent[parent[k]]
                k = parent[k]
            return k

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        # Tunnels of the same label are one net, which is how a block's port
        # reaches the splitter that fans it out into bits.
        by_label = {}
        for comp in self.circuit.components:
            if comp.NAME == "Tunnel" and comp.get("label"):
                by_label.setdefault(comp.get("label"), []).append(
                    at[comp.port("out")]
                )
        for ids in by_label.values():
            for other in ids[1:]:
                for bit in range(width[ids[0]]):
                    union((ids[0], bit), (other, bit))

        for comp in self.circuit.components:
            if comp.NAME != "Splitter":
                continue
            trunk = at[comp.port("in")]
            fanout = int(comp.get("fanout", 2))
            incoming = int(comp.get("incoming", 2))
            groups = [comp.get(f"bit{i}", i) for i in range(incoming)]
            for end in range(fanout):
                carried = [
                    i for i, g in enumerate(groups) if str(g) == str(end)
                ]
                if not carried:
                    continue
                target = at[comp.port(str(end))]
                for j, bit in enumerate(carried):
                    union((trunk, bit), (target, j))

        # A rail is whatever a Ground, a Power or a Constant drives.
        self.rails = {}
        for comp in self.circuit.components:
            if comp.NAME in ("Ground", "Power"):
                self.rails[find((at[comp.port("out")], 0))] = (
                    "GND" if comp.NAME == "Ground" else "+5V"
                )
            elif comp.NAME == "Constant":
                value = int(str(comp.get("value", 1)), 0)
                for bit in range(int(comp.get("width", 1))):
                    rail = "+5V" if (value >> bit) & 1 else "GND"
                    self.rails[find((at[comp.port("out")], bit))] = rail

        self.names = {}
        for narrow in (True, False):
            for i in range(len(nets)):
                if (width[i] == 1) != narrow:
                    continue
                base = label(i)
                for bit in range(width[i]):
                    root = find((i, bit))
                    if root in self.rails:
                        self.names[root] = self.rails[root]
                    elif base:
                        name = f"{base}{bit}" if width[i] > 1 else base
                        self.names.setdefault(root, name)
        for i in range(len(nets)):
            for bit in range(width[i]):
                self.names.setdefault(find((i, bit)), f"N{len(self.names):03d}")

        self._at, self._find, self._width = at, find, width

    def bits_at(self, comp, port):
        """The nets on a component's port, one per bit."""
        i = self._at[comp.port(port)]
        return [
            self.names[self._find((i, bit))] for bit in range(self._width[i])
        ]

    def net_of(self, comp, pin):
        """Net name at a component's pin."""
        return self.names[self._find((self._at[comp.port(pin)], 0))]

    def pin_nets(self, pin_component):
        """The nets on a Pin, one per bit, in bit order."""
        i = self._at[pin_component.port()]
        return [
            self.names[self._find((i, bit))] for bit in range(self._width[i])
        ]

    def connectors(self):
        """Circuit pins, as (label, [net per bit]) in the order they were added."""
        return [(p.get("label"), self.pin_nets(p)) for p in self.circuit.pins()]

    def nets(self):
        """Net name -> [(chip, pin name)], the chip pins on it."""
        out = {}
        for chip in self.chips:
            for pin, x, y in chip.ports():
                out.setdefault(self.net_of(chip, pin), []).append((chip, pin))
        return out


# --------------------------------------------------------------------------
# Parts
#
# Logisim's TTL model leaves GND and VCC off a DIP, since it does not simulate
# them; a board needs them, so they are added back here from the package size.
# --------------------------------------------------------------------------

PITCH = 2.54  # DIP pin pitch, and the schematic grid
# A track has to pass between two pins, so the pad is as small as a
# 0.8 mm drill allows: 2.54 - 1.4 leaves 1.14 mm, and a 0.25 track with
# its clearance on both sides needs 0.95 of it.
DIP_PAD = 1.4
ROW = 7.62  # DIP row spacing, 0.3 inch packages throughout

# One entry per pin: number -> (name, electrical type).
BUS_PINS = {"74245": ("A", "B")}


def dip(chip):
    """(number, name, type) for every pin of a chip, power pins included."""
    half = len(chip.PINS) // 2
    out = []
    for i, name in enumerate(chip.PINS):
        number = i + 1
        if name is None:
            out.append((number, "GND" if number == half else "VCC", "power_in"))
            continue
        if any(name.startswith(p) for p in BUS_PINS.get(chip.NAME, ())):
            kind = "passive"
        elif name in chip.INPUTS:
            kind = "input"
        else:
            kind = "output"
        out.append((number, name, kind))
    return out


def package(chip):
    return f"DIP-{len(chip.PINS)}_W7.62mm"


def dip_rows(footprint):
    return float(footprint.split("_W")[1].rstrip("mm"))


def memory_pins(netlist, comp):
    """A 28-pin memory, wired from the Logisim part's ports.

    A ROM is permanently selected and output-enabled; the SRAM takes its output
    enable from the write strobe and its own strobe from the inverse, which the
    circuit has to provide as n<STROBE>. Logisim's separate data in and out are
    one bidirectional bus on the chip, so the two nets become one.
    """
    addr = netlist.bits_at(comp, "addr")
    if comp.NAME == "ROM":
        data, ties = netlist.bits_at(comp, "data"), {}
        control = {"nCE": "GND", "nOE": "GND", "nWE": "+5V"}
    else:
        data = netlist.bits_at(comp, "din")
        ties = dict(zip(netlist.bits_at(comp, "dout"), data))
        strobe = netlist.bits_at(comp, "we")[0]
        if f"n{strobe}" not in netlist.names.values():
            raise NetlistError(
                f"{comp.NAME} {comp.get('label')}: no net n{strobe} for the "
                f"active-low write strobe"
            )
        control = {"nCE": "GND", "nOE": strobe, "nWE": f"n{strobe}"}
    pins = {}
    for number, signal in JEDEC28.items():
        if signal[0] == "A":
            bit = int(signal[1:])
            pins[number] = addr[bit] if bit < len(addr) else "GND"
        elif signal[0] == "D":
            pins[number] = data[int(signal[1:])]
        elif signal == "VCC":
            pins[number] = "+5V"
        else:
            pins[number] = control.get(signal, signal)
    return pins, ties


class Part:
    """A placed part: reference, value, footprint and net per pin number."""

    def __init__(self, ref, value, footprint, symbol, pins, at, silk=None):
        self.ref, self.value = ref, value
        self.footprint, self.symbol = footprint, symbol
        self.pins = pins  # {number: net name}
        self.x, self.y = at
        self.silk = silk or value

    def span(self):
        """Width and height the footprint occupies, pads and silk included."""
        if self.footprint.startswith("DIP"):
            pins = int(self.footprint.split("-")[1].split("_")[0])
            return (pins // 2 - 1) * PITCH + 4, dip_rows(self.footprint) + 6
        if self.footprint.startswith("PinHeader"):
            cols, rows = self.footprint.split("_")[1].split("x")
            return (
                (int(cols) - 1) * PITCH + 4,
                (int(rows.split("_")[0]) - 1) * PITCH + 6,
            )
        return 9.0, 6.0


# --------------------------------------------------------------------------
# KiCad files
#
# KiCad's own symbol and footprint libraries are not installed here, so the
# project carries its own: a DIP is a rectangle with numbered pins, which is
# what a 74xx symbol is anyway.
# --------------------------------------------------------------------------

import json
import uuid as _uuid

NAMESPACE = _uuid.UUID("6b1f2f9a-0000-4000-8000-6b6f6e650000")
SCH_VERSION = 20250114
PCB_VERSION = 20241229
LIB_VERSION = 20241209

# The connector every board shares. The signal list is not written down here:
# system_nets() reads it off the top level of kone.circ, so a board's header
# pin means the same thing on every board.
HEADER_PINS = 40  # one 2x20 connector
RAILS = ("+5V", "GND", "+5V", "GND")


def system_nets(top):
    """(block, port) -> (net name at the top level, width).

    A block's port is stubbed to the tunnel that names the net; a port the top
    level ties to a rail reports that rail instead.
    """
    nets, index = top.nets(), top.ports_at()
    at = {p: i for i, net in enumerate(nets) for p in net}
    out = {}
    for comp in top.components:
        block = getattr(comp, "circuit", None)
        if block is None:
            continue
        width = {p.get("label"): int(p.get("width", 1)) for p in block.pins()}
        for name, x, y in comp.ports():
            on_net = nets[at[(x, y)]]
            names = {
                c.get("label")
                for p in on_net
                for c in index.get(p, ())
                if c.NAME == "Tunnel"
            }
            rails = {
                c.NAME
                for p in on_net
                for c in index.get(p, ())
                if c.NAME in ("Power", "Ground")
            }
            if names:
                out[(block.name, name)] = (sorted(names)[0], width[name])
            elif rails:
                out[(block.name, name)] = (
                    "+5V" if "Power" in rails else "GND",
                    width[name],
                )
    return out


def backplane(system):
    """Every inter-board signal, one entry per bit, at a fixed position."""
    signals = sorted({v for v in system.values() if v[0] not in ("+5V", "GND")})
    out = list(RAILS)
    for net, width in signals:
        out += [f"{net}{i}" for i in range(width)] if width > 1 else [net]
    while len(out) % HEADER_PINS:
        out.append(f"SP{len(out)}")
    return out


def uid(*key):
    return str(_uuid.uuid5(NAMESPACE, "/".join(str(k) for k in key)))


def font(size=1.27):
    return f"(effects (font (size {size} {size})))"


class Symbol:
    """A generated schematic symbol: inputs left, outputs right, power top-down."""

    def __init__(self, name, pins, footprint):
        self.name, self.footprint = name, footprint
        left, right = [], []
        for number, pin, kind in pins:
            side = left if (kind == "input" or pin.startswith("A")) else right
            if pin in ("VCC", "GND"):
                side = left if pin == "GND" else right
            side.append((number, pin, kind))
        rows = max(len(left), len(right))
        self.height = (rows + 1) * PITCH
        self.width = 20.32
        self.at = {}
        for side, xs in ((left, -self.width / 2), (right, self.width / 2)):
            top = (len(side) - 1) * PITCH / 2
            for i, (number, pin, kind) in enumerate(side):
                self.at[number] = (
                    xs,
                    top - i * PITCH,
                    pin,
                    kind,
                    -1 if xs < 0 else 1,
                )

    def sexpr(self, prefix=""):
        """The library form; inside a schematic the name is the full lib_id."""
        name = prefix + self.name
        out = [
            f'\t(symbol "{name}"',
            "\t\t(pin_names (offset 0.508))",
            "\t\t(exclude_from_sim no) (in_bom yes) (on_board yes)",
            f'\t\t(property "Reference" "U" (at 0 {self.height / 2 + 2.54:.2f} 0) {font()})',
            f'\t\t(property "Value" "{self.name}" (at 0 {-self.height / 2 - 2.54:.2f} 0) {font()})',
            f'\t\t(property "Footprint" "kone:{self.footprint}" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
            f'\t\t(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
            f'\t\t(symbol "{self.name}_0_1"',
            f"\t\t\t(rectangle (start {-self.width / 2:.2f} {self.height / 2:.2f}) "
            f"(end {self.width / 2:.2f} {-self.height / 2:.2f}) "
            "(stroke (width 0.254) (type default)) (fill (type background)))",
            "\t\t)",
            f'\t\t(symbol "{self.name}_1_1"',
        ]
        for number, (x, y, pin, kind, side) in sorted(self.at.items()):
            angle = 0 if side < 0 else 180
            out.append(
                f"\t\t\t(pin {kind} line (at {x + side * PITCH:.2f} {y:.2f} {angle}) "
                f'(length {PITCH}) (name "{pin}" {font(1.0)}) '
                f'(number "{number}" {font(1.0)}))'
            )
        out += ["\t\t)", "\t)"]
        return "\n".join(out)


def symbol_library(symbols):
    out = [
        f'(kicad_symbol_lib (version {LIB_VERSION}) (generator "kone") '
        '(generator_version "10.0")'
    ]
    out += [s.sexpr() for s in symbols]
    out.append(")")
    return "\n".join(out) + "\n"


def _outline(key, box, layers=(("F.SilkS", 0.12), ("F.CrtYd", 0.05))):
    out = []
    for i, (x1, y1) in enumerate(box):
        x2, y2 = box[(i + 1) % 4]
        for layer, width in layers:
            out.append(
                f"\t(fp_line (start {x1:.2f} {y1:.2f}) (end {x2:.2f} {y2:.2f}) "
                f'(stroke (width {width}) (type solid)) (layer "{layer}") '
                f'(uuid "{uid(key, layer, i)}"))'
            )
    return out


def _pad(key, number, shape, x, y, size, drill, nets, solid=False):
    net = nets.get(str(number))
    tail = f' (net {net[0]} "{net[1]}")' if net else ""
    # A pin in a header grid has no room for two thermal spokes; the plane
    # takes it solid instead, which is what DRC's spoke count asks for.
    tail += " (zone_connect 2)" if solid else ""
    return (
        f'\t(pad "{number}" thru_hole {shape} (at {x:.2f} {y:.2f}) '
        f'(size {size} {size}) (drill {drill}) (layers "*.Cu" "*.Mask")'
        f'{tail} (uuid "{uid(key, "pad", number)}"))'
    )


def _head(name, key, at, ref, value, ref_at, value_at):
    place = f" (at {at[0]:.2f} {at[1]:.2f})" if at else ""
    return [
        f'(footprint "{name}" (version {PCB_VERSION}) (generator "kone") '
        '(generator_version "10.0")',
        f'\t(layer "F.Cu")',
        f'\t(uuid "{uid(key)}"){place}',
        "\t(attr through_hole)",
        f'\t(property "Reference" "{ref}" (at {ref_at[0]:.2f} {ref_at[1]:.2f} 0) '
        f'(layer "F.SilkS") (uuid "{uid(key, "ref")}") '
        "(effects (font (size 1 1) (thickness 0.15))))",
        f'\t(property "Value" "{value}" (at {value_at[0]:.2f} {value_at[1]:.2f} 0) '
        f'(layer "F.Fab") (uuid "{uid(key, "val")}") '
        "(effects (font (size 1 1) (thickness 0.15))))",
    ]


def pads(footprint):
    """(number, x, y, pad size, drill) of a footprint, its one geometry."""
    if footprint.startswith("DIP"):
        pins = int(footprint.split("-")[1].split("_")[0])
        half, row = pins // 2, dip_rows(footprint)
        return [
            (
                i + 1,
                (i if i < half else pins - 1 - i) * PITCH,
                0.0 if i < half else row,
                DIP_PAD,
                0.8,
            )
            for i in range(pins)
        ]
    if footprint.startswith("PinHeader"):
        cols, rows = footprint.split("_")[1].split("x")
        cols, rows = int(cols), int(rows.split("_")[0])
        return [
            (col * rows + row + 1, col * PITCH, row * PITCH, 1.7, 1.0)
            for col in range(cols)
            for row in range(rows)
        ]
    if footprint in TWO_PAD:
        pitch, drill, pad = TWO_PAD[footprint]
        return [(1, 0.0, 0.0, pad, drill), (2, pitch, 0.0, pad, drill)]
    return [(1, 0.0, 0.0, 1.6, 0.8), (2, 5.08, 0.0, 1.6, 0.8)]


def dip_footprint(
    pins, key=None, at=None, ref="U**", value=None, nets=None, width=7.62
):
    """A DIP, pin 1 top left, numbering counterclockwise."""
    name = f"DIP-{pins}_W{width:.2f}mm"
    key, nets = key or f"lib/{name}", nets or {}
    half, body, ROW = pins // 2, (pins // 2 - 1) * PITCH, width
    out = _head(
        name if at is None else f"kone:{name}",
        key,
        at,
        ref,
        value or name,
        (body / 2, -2.5),
        (body / 2, ROW + 2.5),
    )
    for number, x, y, size, drill in pads(name):
        out.append(
            _pad(
                key,
                number,
                "rect" if number == 1 else "oval",
                x,
                y,
                size,
                drill,
                nets,
            )
        )
    out += _outline(
        key,
        [
            (-1.5, -1.5),
            (body + 1.5, -1.5),
            (body + 1.5, ROW + 1.5),
            (-1.5, ROW + 1.5),
        ],
    )
    out.append(
        f"\t(fp_circle (center -2.6 0) (end -2.2 0) "
        '(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS") '
        f'(uuid "{uid(key, "dot")}"))'
    )
    out.append(")")
    return "\n".join(out) + "\n"


def header_footprint(
    rows, cols, key=None, at=None, ref="J**", value=None, nets=None
):
    name = f"PinHeader_{cols}x{rows:02d}_P2.54mm"
    key, nets = key or f"lib/{name}", nets or {}
    out = _head(
        name if at is None else f"kone:{name}",
        key,
        at,
        ref,
        value or name,
        (0, -2.5),
        (0, rows * PITCH + 1),
    )
    for number, x, y, size, drill in pads(name):
        out.append(
            _pad(
                key,
                number,
                "rect" if number == 1 else "oval",
                x,
                y,
                size,
                drill,
                nets,
                solid=True,
            )
        )
    out += _outline(
        key,
        [
            (-1.5, -1.5),
            ((cols - 1) * PITCH + 1.5, -1.5),
            ((cols - 1) * PITCH + 1.5, (rows - 1) * PITCH + 1.5),
            (-1.5, (rows - 1) * PITCH + 1.5),
        ],
    )
    # Pin 1, the one mark that says which way round the connector goes: a
    # square around the pad and a dot beside it, the same on every board.
    out += _outline(
        key + "/pin1",
        [(-1.5, -1.5), (1.5, -1.5), (1.5, 1.5), (-1.5, 1.5)],
        layers=(("F.SilkS", 0.2),),
    )
    out.append(
        f"\t(fp_circle (center -2.6 0) (end -2.2 0) "
        '(stroke (width 0.12) (type solid)) (fill solid) (layer "F.SilkS") '
        f'(uuid "{uid(key, "pin1")}"))'
    )
    out.append(")")
    return "\n".join(out) + "\n"


def footprint_body(footprint, **kw):
    """The .kicad_mod text for a footprint, as library entry or placed."""
    if footprint.startswith("DIP"):
        pins = int(footprint.split("-")[1].split("_")[0])
        return dip_footprint(pins, width=dip_rows(footprint), **kw)
    if footprint.startswith("C_Disc"):
        return cap_footprint(**kw)
    if footprint.startswith("MountingHole"):
        return hole_footprint(**kw)
    if footprint in TWO_PAD:
        pitch, drill, pad = TWO_PAD[footprint]
        return two_pad_footprint(footprint, pitch, drill, pad, **kw)
    cols, rows = footprint.split("_")[1].split("x")
    return header_footprint(int(rows.split("_")[0]), int(cols), **kw)


def hole_footprint(key=None, at=None, ref="H**", value="M3", nets=None):
    """A plated-free M3 hole; the pad carries no net, so nothing routes to it."""
    name = "MountingHole_3.2mm_M3"
    key = key or f"lib/{name}"
    out = _head(
        name if at is None else f"kone:{name}",
        key,
        at,
        ref,
        value,
        (0, -3.5),
        (0, 3.5),
    )
    out.append(
        f'\t(pad "" np_thru_hole circle (at 0 0) (size 3.2 3.2) '
        f'(drill 3.2) (layers "F&B.Cu" "*.Mask") '
        f'(uuid "{uid(key, "hole")}"))'
    )
    out += _outline(
        key,
        [(-3.5, -3.5), (3.5, -3.5), (3.5, 3.5), (-3.5, 3.5)],
        layers=(("F.CrtYd", 0.05),),
    )
    out.append(
        f"\t(fp_circle (center 0 0) (end 2.5 0) "
        '(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS") '
        f'(uuid "{uid(key, "ring")}"))'
    )
    out.append(")")
    return "\n".join(out) + "\n"


def two_pad_footprint(
    name, pitch, drill, pad, key=None, at=None, ref="X**", value=None, nets=None
):
    """Anything with two leads in a row: resistor, LED, electrolytic, terminal."""
    key, nets = key or f"lib/{name}", nets or {}
    out = _head(
        name if at is None else f"kone:{name}",
        key,
        at,
        ref,
        value or name,
        (pitch / 2, -2.6),
        (pitch / 2, 3.2),
    )
    for number, x, y, size, hole in pads(name):
        out.append(
            _pad(
                key,
                number,
                "rect" if number == 1 else "oval",
                x,
                y,
                size,
                hole,
                nets,
            )
        )
    out += _outline(
        key,
        [(-1.6, -2.0), (pitch + 1.6, -2.0), (pitch + 1.6, 2.0), (-1.6, 2.0)],
    )
    out.append(")")
    return "\n".join(out) + "\n"


def cap_footprint(key=None, at=None, ref="C**", value="100n", nets=None):
    name = "C_Disc_D5.0mm_P5.08mm"
    key, nets = key or f"lib/{name}", nets or {}
    out = _head(
        name if at is None else f"kone:{name}",
        key,
        at,
        ref,
        value,
        (2.54, -3.6),
        (2.54, 3),
    )
    for number, x in ((1, 0.0), (2, 5.08)):
        out.append(
            _pad(
                key,
                number,
                "rect" if number == 1 else "oval",
                x,
                0,
                1.6,
                0.8,
                nets,
            )
        )
    out += _outline(key, [(-1.5, -2.0), (6.6, -2.0), (6.6, 2.0), (-1.5, 2.0)])
    out.append(")")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# One board
# --------------------------------------------------------------------------

ORIGIN = 63.5  # the sheet grid; every stub lands on 1.27 mm
CONN_STRIP = 60.0  # room at the bottom for the connectors
CONN_X = 20.0  # the connector row, identical on every board
CONN_PITCH = 45.0
HOLE_INSET = 6.0  # M3 holes, one per corner
HOLE_KEEPOUT = 7.0  # nothing routes inside this, washer room
CAP_ROOM = 16.0  # under an IC: its cap, and the row's routing channel             # board grid per IC, room for its decoupling cap
SCH_CELL = (63.5, 50.8)  # schematic grid, room for pin labels
# KiCad 10 numbering: copper is even, F.Cu 0, B.Cu 2, inner layers from 4.
# The two inner ones are solid planes, which is what makes 391 nets routable
# on a board this dense: the router only sees signals.
LAYERS = (
    (0, "F.Cu", "signal", None),
    (4, "In1.Cu", "power", None),
    (6, "In2.Cu", "power", None),
    (2, "B.Cu", "signal", None),
    (9, "F.Adhes", "user", "F.Adhesive"),
    (13, "F.Paste", "user", None),
    (5, "F.SilkS", "user", "F.Silkscreen"),
    (1, "F.Mask", "user", None),
    (3, "B.Mask", "user", None),
    (7, "B.SilkS", "user", "B.Silkscreen"),
    (31, "F.CrtYd", "user", "F.Courtyard"),
    (35, "F.Fab", "user", None),
    (25, "Edge.Cuts", "user", None),
    (27, "Margin", "user", None),
)

# net -> the plane it lives on; these never reach the router.
PLANES = (("GND", "In1.Cu"), ("+5V", "In2.Cu"))


def _order(comp):
    """Placement order: chips that share a label end up side by side, so a
    register sits next to the driver it feeds and a bus stays local."""
    label = comp.get("label") or ""
    digits = "".join(c if c.isdigit() else " " for c in label).split()
    return (
        "".join(c for c in label if not c.isdigit()),
        int(digits[0]) if digits else 0,
        comp.NAME,
        comp.y,
        comp.x,
    )


class Board:
    """The chips of one Circuit as a KiCad project: schematic, board, libraries.

    Placement follows the order the build script created the chips in, so the
    board keeps the structure of the logic: a row of registers stays a row.
    """

    def __init__(
        self,
        name,
        circuit,
        columns=8,
        title=None,
        ports=None,
        positions=None,
        size=None,
        entry=False,
    ):
        self.name, self.title = name, title or name
        self.netlist = Netlist(circuit)
        self.columns = columns
        self.size = size  # the outline every board shares
        self.entry = entry  # this board carries the supply connector
        self.ports = ports or {}  # port label -> (system net, width)
        self.positions = positions or {}  # system signal -> backplane index
        self.parts = []
        self.symbols = {}
        # A port the CPU ties to a rail is tied here too, rather than brought
        # out to the backplane.
        self.tie = {}
        for pin in circuit.pins():
            rail, _ = self.ports.get(pin.get("label"), (None, 0))
            if rail in ("+5V", "GND"):
                for net in self.netlist.pin_nets(pin):
                    self.tie[net] = rail
        for mem in self.netlist.memories:  # one data bus, not two
            self.tie.update(memory_pins(self.netlist, mem)[1])
        self._place()

    def net(self, name):
        return self.tie.get(name, name)

    # -- parts -------------------------------------------------------------

    def _symbol(self, key, pins, footprint):
        if key not in self.symbols:
            self.symbols[key] = Symbol(key, pins, footprint)
        return self.symbols[key]

    def _packages(self):
        """Every real IC: the TTL chips, then the memories, in layout order."""
        out = []
        for chip in sorted(self.netlist.chips, key=_order):
            pins = dip(chip)
            nets = {
                n: (
                    {"VCC": "+5V", "GND": "GND"}[pin]
                    if kind == "power_in"
                    else self.net(self.netlist.net_of(chip, pin))
                )
                for n, pin, kind in pins
            }
            out.append(
                (chip.NAME, package(chip), pins, nets, chip.get("label"))
            )
        for mem in sorted(self.netlist.memories, key=_order):
            value, footprint = PARTS[mem.NAME]
            nets = {
                n: self.net(v)
                for n, v in memory_pins(self.netlist, mem)[0].items()
            }
            pins = [
                (
                    n,
                    JEDEC28[n],
                    "power_in"
                    if JEDEC28[n] in ("VCC", "GND")
                    else "passive"
                    if JEDEC28[n][0] == "D"
                    else "input",
                )
                for n in sorted(JEDEC28)
            ]
            out.append((value, footprint, pins, nets, mem.get("label")))
        return out

    def _place(self):
        packages = self._packages()
        # The grid follows the largest package, so a 0.6 inch memory fits next
        # to a 14-pin gate without either overlapping its decoupling cap.
        spans = [Part("U", v, f, v, {}, (0, 0)).span() for v, f, *_ in packages]
        body = max(h for _, h in spans)
        self.cell = (max(w for w, _ in spans) + 6, body + CAP_ROOM)
        rows = (len(packages) + self.columns - 1) // self.columns
        if self.size:
            # Every board carries the largest one's outline, so a small board
            # spreads its chips over the whole of it rather than crowding a
            # corner: the router needs the channels more than the board needs
            # to be compact.
            self.cell = (
                max(self.cell[0], (self.size[0] - 40) / self.columns),
                max(self.cell[1], (self.size[1] - CONN_STRIP - 30) / rows),
            )
        for i, (value, footprint, pins, nets, label) in enumerate(packages):
            col, row = i % self.columns, i // self.columns
            x, y = 20 + col * self.cell[0], 20 + row * self.cell[1]
            self._symbol(value, pins, footprint)
            self.parts.append(
                Part(
                    f"U{i + 1}",
                    value,
                    footprint,
                    value,
                    nets,
                    (x, y),
                    silk=f"{value} {label}" if label else value,
                )
            )
            self._symbol(
                "C",
                [(1, "1", "passive"), (2, "2", "passive")],
                "C_Disc_D5.0mm_P5.08mm",
            )
            self.parts.append(
                Part(
                    f"C{i + 1}",
                    "100n",
                    "C_Disc_D5.0mm_P5.08mm",
                    "C",
                    {1: "+5V", 2: "GND"},
                    (x + 2, y + body + 1),
                    silk="100n",
                )
            )
        self.ic_rows = rows

        # The backplane: fixed positions system-wide. Every board carries every
        # connector, so a stack goes together in any order; a pin whose signal
        # a board has not got is a pass-through, carrying the backplane net
        # and nothing else on that board.
        used = dict(enumerate(RAILS))
        for signal, index in self.positions.items():
            used.setdefault(index, signal)
        driven = set()
        for pin in self.netlist.circuit.pins():
            label = pin.get("label")
            system, _ = self.ports.get(label, (label, 1))
            if system in ("+5V", "GND"):
                continue
            nets = self.netlist.pin_nets(pin)
            for bit, net in enumerate(nets):
                key = f"{system}{bit}" if len(nets) > 1 else system
                if key in self.positions:
                    used[self.positions[key]] = self.net(net)
                    driven.add(self.positions[key])
        self.used = used
        self.driven = driven
        rows = HEADER_PINS // 2
        self._symbol(
            "Conn_2x20",
            [(n + 1, str(n + 1), "passive") for n in range(HEADER_PINS)],
            f"PinHeader_2x{rows:02d}_P2.54mm",
        )
        # Every board carries the same outline, the same four M3 holes and
        # the same connector positions, so a stack lines up.
        grid = (
            20 + self.columns * self.cell[0],
            20 + self.ic_rows * self.cell[1],
        )
        self.width, self.height = self.size or (
            grid[0] + 20,
            grid[1] + CONN_STRIP + 10,
        )
        conn_y = self.height - CONN_STRIP + 6

        headers = sorted({p // HEADER_PINS for p in used})
        for header in headers:
            pins = {
                p % HEADER_PINS + 1: net
                for p, net in used.items()
                if p // HEADER_PINS == header
            }
            self.parts.append(
                Part(
                    f"J{header + 1}",
                    f"Backplane {header + 1}",
                    f"PinHeader_2x{rows:02d}_P2.54mm",
                    "Conn_2x20",
                    pins,
                    (CONN_X + header * CONN_PITCH, conn_y),
                    silk=f"BP{header + 1} ({header * HEADER_PINS + 1}"
                    f"-{(header + 1) * HEADER_PINS})",
                )
            )
        self._symbol(
            "Conn_1x02",
            [(1, "1", "passive"), (2, "2", "passive")],
            "PinHeader_1x02_P2.54mm",
        )
        self.parts.append(
            Part(
                "J0",
                "Power",
                "PinHeader_1x02_P2.54mm",
                "Conn_1x02",
                {1: "+5V", 2: "GND"},
                (CONN_X + 4 * CONN_PITCH, conn_y),
                silk="+5V / GND",
            )
        )

        # Bulk capacitance sits with the connectors on every board.
        self._symbol(
            "CP",
            [(1, "1", "passive"), (2, "2", "passive")],
            "CP_Radial_D6.3mm_P2.50mm",
        )
        self.parts.append(
            Part(
                "C0",
                "100u",
                "CP_Radial_D6.3mm_P2.50mm",
                "CP",
                {1: "+5V", 2: "GND"},
                (CONN_X + 4 * CONN_PITCH, conn_y + 20),
                silk="100u",
            )
        )

        # The whole stack is fed here, and this is the board that says so.
        if self.entry:
            for ref, value, footprint, symbol, pins, dy, silk in (
                (
                    "J5",
                    "5V IN",
                    "TerminalBlock_2x5.08mm",
                    "Conn_1x02",
                    {1: "+5V", 2: "GND"},
                    40,
                    "5V IN  +5V/GND",
                ),
                (
                    "R1",
                    "220R",
                    "R_Axial_P10.16mm",
                    "R",
                    {1: "+5V", 2: "PWRLED"},
                    60,
                    "220R",
                ),
                (
                    "D1",
                    "PWR",
                    "LED_D3.0mm_P2.54mm",
                    "LED",
                    {1: "PWRLED", 2: "GND"},
                    75,
                    "PWR",
                ),
            ):
                self._symbol(
                    symbol,
                    [(1, "1", "passive"), (2, "2", "passive")],
                    footprint,
                )
                self.parts.append(
                    Part(
                        ref,
                        value,
                        footprint,
                        symbol,
                        pins,
                        (CONN_X + 5 * CONN_PITCH, conn_y + dy - 40),
                        silk=silk,
                    )
                )

            # The clock the whole stack runs on. A can oscillator in a socket
            # drives CLK through a jumper; move the jumper and an external
            # source on J7 drives it instead, down to single steps by hand.
            # Pin 1 is an enable on the cans that have one and open on the
            # rest, so it is tied high either way.
            self._symbol(
                "OSC",
                [
                    (1, "EN", "input"),
                    (7, "GND", "power_in"),
                    (8, "OUT", "output"),
                    (14, "VCC", "power_in"),
                ],
                "DIP-14_W7.62mm",
            )
            self._symbol(
                "Conn_1x03",
                [(n, str(n), "passive") for n in (1, 2, 3)],
                "PinHeader_1x03_P2.54mm",
            )
            # Power-on reset. The RC holds NRES low while the rails come up,
            # the Schmitt inverter gives the sequencer a clean edge, and
            # shorting J8 resets by hand. NRES is a backplane signal, so the
            # sequencer sees it wherever it sits in the stack.
            self._symbol(
                "SCHMITT",
                [
                    (1, "A", "input"),
                    (2, "Y", "output"),
                    (3, "A", "input"),
                    (4, "Y", "output"),
                    (5, "A", "input"),
                    (9, "A", "input"),
                    (11, "A", "input"),
                    (13, "A", "input"),
                    (7, "GND", "power_in"),
                    (14, "VCC", "power_in"),
                ],
                "DIP-14_W7.62mm",
            )
            reset = (CONN_X + 4 * CONN_PITCH, conn_y - 60)
            for ref, value, footprint, symbol, pins, at, silk in (
                (
                    "U24",
                    "7414",
                    "DIP-14_W7.62mm",
                    "SCHMITT",
                    # the four gates nothing uses keep their inputs tied
                    {
                        1: "RESRC",
                        2: "RES",
                        3: "RES",
                        4: "NRES",
                        5: "GND",
                        9: "GND",
                        11: "GND",
                        13: "GND",
                        7: "GND",
                        14: "+5V",
                    },
                    (0, 0),
                    "7414 reset",
                ),
                (
                    "C88",
                    "100n",
                    "C_Disc_D5.0mm_P5.08mm",
                    "C",
                    {1: "+5V", 2: "GND"},
                    (2, 16),
                    "100n",
                ),
                (
                    "R2",
                    "10k",
                    "R_Axial_P10.16mm",
                    "R",
                    {1: "+5V", 2: "RESRC"},
                    (0, 26),
                    "10k",
                ),
                (
                    "C89",
                    "10u",
                    "CP_Radial_D6.3mm_P2.50mm",
                    "CP",
                    {1: "RESRC", 2: "GND"},
                    (0, 34),
                    "10u",
                ),
                (
                    "J8",
                    "RESET",
                    "PinHeader_1x02_P2.54mm",
                    "Conn_1x02",
                    {1: "RESRC", 2: "GND"},
                    (14, 30),
                    "RESET",
                ),
            ):
                self.parts.append(
                    Part(
                        ref,
                        value,
                        footprint,
                        symbol,
                        pins,
                        (reset[0] + at[0], reset[1] + at[1]),
                        silk=silk,
                    )
                )

            clock = (CONN_X + 5 * CONN_PITCH, conn_y - 60)
            for ref, value, footprint, symbol, pins, at, silk in (
                (
                    "X1",
                    "1MHz",
                    "DIP-14_W7.62mm",
                    "OSC",
                    {1: "+5V", 7: "GND", 8: "OSC", 14: "+5V"},
                    (0, 0),
                    "1MHz",
                ),
                (
                    "C87",
                    "100n",
                    "C_Disc_D5.0mm_P5.08mm",
                    "C",
                    {1: "+5V", 2: "GND"},
                    (2, 16),
                    "100n",
                ),
                (
                    "J6",
                    "CLK SRC",
                    "PinHeader_1x03_P2.54mm",
                    "Conn_1x03",
                    {1: "OSC", 2: self.net("CLK"), 3: "EXTCLK"},
                    (0, 28),
                    "CLK SRC  osc/ext",
                ),
                (
                    "J7",
                    "EXT CLK",
                    "PinHeader_1x02_P2.54mm",
                    "Conn_1x02",
                    {1: "EXTCLK", 2: "GND"},
                    (20, 28),
                    "EXT CLK",
                ),
            ):
                self.parts.append(
                    Part(
                        ref,
                        value,
                        footprint,
                        symbol,
                        pins,
                        (clock[0] + at[0], clock[1] + at[1]),
                        silk=silk,
                    )
                )

        self._symbol("HOLE", [], "MountingHole_3.2mm_M3")
        for i, (hx, hy) in enumerate(
            (
                (HOLE_INSET, HOLE_INSET),
                (self.width - HOLE_INSET, HOLE_INSET),
                (HOLE_INSET, self.height - HOLE_INSET),
                (self.width - HOLE_INSET, self.height - HOLE_INSET),
            )
        ):
            self.parts.append(
                Part(
                    f"H{i + 1}",
                    "M3",
                    "MountingHole_3.2mm_M3",
                    "HOLE",
                    {},
                    (hx, hy),
                    silk="M3",
                )
            )
        self.holes = [
            (p.x, p.y) for p in self.parts if p.footprint.startswith("Mounting")
        ]

        self._symbol("PWR", [(1, "1", "power_out")], "")
        self.parts.append(Part("PWR1", "+5V", "", "PWR", {1: "+5V"}, (0, 0)))
        self.parts.append(Part("PWR2", "GND", "", "PWR", {1: "GND"}, (0, 0)))

    def nets(self):
        """Net name -> index, GND and +5V first."""
        names = sorted({n for p in self.parts for n in p.pins.values()})
        names.sort(key=lambda n: (n not in ("GND", "+5V"), n))
        return {n: i + 1 for i, n in enumerate(names)}

    def extent(self):
        if self.size:
            return 0.0, 0.0, self.width, self.height
        xs, ys = [], []
        for part in self.parts:
            if part.symbol == "PWR":
                continue
            w, h = part.span()
            xs += [part.x - 5, part.x + w + 5]
            ys += [part.y - 5, part.y + h + 5]
        return min(xs), min(ys), max(xs), max(ys)


def _sch_positions(board):
    """Where each part goes on the sheet: ICs on a grid, caps and headers below."""
    at, ic, cap = {}, 0, 0
    for part in board.parts:
        if part.symbol in ("C", "PWR") or part.symbol.startswith("Conn"):
            continue
        at[part.ref] = (
            ORIGIN + (ic % board.columns) * SCH_CELL[0],
            ORIGIN + (ic // board.columns) * SCH_CELL[1],
        )
        ic += 1
    bottom = ORIGIN + ((ic + board.columns - 1) // board.columns) * SCH_CELL[1]
    for part in board.parts:
        if part.symbol == "C":
            at[part.ref] = (
                ORIGIN + (cap % 16) * 25.4,
                bottom + (cap // 16) * 25.4,
            )
            cap += 1
    bottom += ((cap + 15) // 16) * 25.4 + 38.1
    for i, part in enumerate(
        p
        for p in board.parts
        if p.symbol.startswith("Conn") or p.symbol == "PWR"
    ):
        at[part.ref] = (ORIGIN + i * 76.2, bottom)
    return at


def schematic(board):
    """The sheet: a symbol per part, every pin stubbed to a net label."""
    at = _sch_positions(board)
    used = {}
    for part in board.parts:
        for net in part.pins.values():
            used[net] = used.get(net, 0) + 1
    width = max(x for x, _ in at.values()) + 120
    height = max(y for _, y in at.values()) + 120

    out = [
        f'(kicad_sch (version {SCH_VERSION}) (generator "kone") '
        '(generator_version "10.0")',
        f'\t(uuid "{uid(board.name, "sheet")}")',
        f'\t(paper "User" {width:.1f} {height:.1f})',
        f'\t(title_block (title "kone {board.title}") (company "generated by '
        'kicad/python"))',
        "\t(lib_symbols",
    ]
    out += [s.sexpr("kone:") for s in board.symbols.values()]
    out.append("\t)")

    for part in board.parts:
        sym = board.symbols[part.symbol]
        x, y = at[part.ref]
        key = (board.name, part.ref)
        out += [
            f'\t(symbol (lib_id "kone:{part.symbol}") (at {x:.2f} {y:.2f} 0) '
            "(unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)",
            f'\t\t(uuid "{uid(*key)}")',
            f'\t\t(property "Reference" "{part.ref}" '
            f"(at {x:.2f} {y - sym.height / 2 - 2.54:.2f} 0) {font()})",
            f'\t\t(property "Value" "{part.value}" '
            f"(at {x:.2f} {y + sym.height / 2 + 2.54:.2f} 0) {font()})",
            f'\t\t(property "Footprint" '
            f'"{"kone:" + part.footprint if part.footprint else ""}" '
            f"(at {x:.2f} {y:.2f} 0) "
            "(effects (font (size 1.27 1.27)) (hide yes)))",
        ]
        for number in sorted(sym.at):
            out.append(f'\t\t(pin "{number}" (uuid "{uid(*key, number)}"))')
        out += [
            f'\t\t(instances (project "{board.name}" (path "/{uid(board.name, "sheet")}" '
            f'(reference "{part.ref}") (unit 1))))',
            "\t)",
        ]
        for number, (px, py, pin, kind, side) in sym.at.items():
            cx, cy = x + px + side * PITCH, y - py
            net = part.pins.get(number)
            if net is None or used.get(net, 0) < 2:
                out.append(
                    f"\t(no_connect (at {cx:.2f} {cy:.2f}) "
                    f'(uuid "{uid(*key, "nc", number)}"))'
                )
                continue
            ex = cx + side * PITCH
            out += [
                f"\t(wire (pts (xy {cx:.2f} {cy:.2f}) (xy {ex:.2f} {cy:.2f})) "
                "(stroke (width 0) (type default)) "
                f'(uuid "{uid(*key, "w", number)}"))',
                f'\t(label "{net}" (at {ex:.2f} {cy:.2f} {0 if side > 0 else 180}) '
                f"(effects (font (size 1.27 1.27)) (justify left bottom)) "
                f'(uuid "{uid(*key, "l", number)}"))',
            ]
    out += [
        f'\t(sheet_instances (path "/" (page "1")))',
        "\t(embedded_fonts no)",
        ")",
    ]
    return "\n".join(out) + "\n"


def pcb(board, tracks=(), vias=()):
    """The board: footprints on the logic's own grid, and what Freerouting found."""
    nets = board.nets()
    x0, y0, x1, y1 = board.extent()
    out = [
        f'(kicad_pcb (version {PCB_VERSION}) (generator "kone") '
        '(generator_version "10.0")',
        "\t(general (thickness 1.6) (legacy_teardrops no))",
        '\t(paper "A4")',
        "\t(layers",
    ]
    for number, name, kind, alias in LAYERS:
        out.append(
            f'\t\t({number} "{name}" {kind}'
            + (f' "{alias}")' if alias else ")")
        )
    out += ["\t)", "\t(setup (pad_to_mask_clearance 0))", '\t(net 0 "")']
    out += [
        f'\t(net {i} "{n}")'
        for n, i in sorted(nets.items(), key=lambda kv: kv[1])
    ]

    for part in board.parts:
        if part.symbol == "PWR":
            continue
        pads = {str(n): (nets[net], net) for n, net in part.pins.items()}
        body = footprint_body(
            part.footprint,
            key=part.ref,
            at=(part.x, part.y),
            ref=part.ref,
            value=part.value,
            nets=pads,
        )
        out.append("\t" + body.replace("\n", "\n\t").rstrip("\t"))
        if part.footprint.startswith("C_"):
            continue  # its reference on the silk is enough
        w, _ = part.span()
        at = (
            (part.x + PITCH / 2, part.y - 3.4)
            if part.footprint.startswith("PinHeader_2x")
            else (part.x + w / 2 - 2, part.y + ROW + 2.4)
        )
        out.append(
            f'\t(gr_text "{part.silk}" (at {at[0]:.2f} '
            f'{at[1]:.2f}) (layer "F.SilkS") '
            f'(uuid "{uid(part.ref, "silk")}") '
            "(effects (font (size 1 1) (thickness 0.15))))"
        )

    nets_by_name = {n: i for n, i in nets.items()}
    for i, (net, layer, width, points) in enumerate(tracks):
        for j, ((ax, ay), (bx, by)) in enumerate(zip(points, points[1:])):
            out.append(
                f"\t(segment (start {ax:.4f} {ay:.4f}) "
                f"(end {bx:.4f} {by:.4f}) (width {width:.3f}) "
                f'(layer "{layer}") (net {nets_by_name.get(net, 0)}) '
                f'(uuid "{uid(board.name, "seg", i, j)}"))'
            )
    for i, (net, vx, vy) in enumerate(vias):
        out.append(
            f"\t(via (at {vx:.4f} {vy:.4f}) (size {VIA_SIZE}) "
            f"(drill {VIA_DRILL}) "
            f'(layers "F.Cu" "B.Cu") (net {nets_by_name.get(net, 0)}) '
            f'(uuid "{uid(board.name, "via", i)}"))'
        )

    # GND and +5V are planes, not routed nets: 380 pads reach them straight
    # through the board, and the two signal layers stay free.
    pour = [
        (x0 + EDGE, y0 + EDGE),
        (x1 - EDGE, y0 + EDGE),
        (x1 - EDGE, y1 - EDGE),
        (x0 + EDGE, y1 - EDGE),
    ]
    for net, layer in PLANES:
        out += [
            f'\t(zone (net {nets[net]}) (net_name "{net}") (layer "{layer}") '
            f'(uuid "{uid(board.name, "zone", net)}") (hatch edge 0.5)',
            "\t\t(connect_pads (clearance 0.5))",
            "\t\t(min_thickness 0.25) (filled_areas_thickness no)",
            "\t\t(fill yes (thermal_gap 0.5) (thermal_bridge_width 0.5))",
            "\t\t(polygon (pts "
            + " ".join(f"(xy {x:.2f} {y:.2f})" for x, y in pour)
            + "))",
            "\t)",
        ]

    box = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for i, (ax, ay) in enumerate(box):
        bx, by = box[(i + 1) % 4]
        out.append(
            f"\t(gr_line (start {ax:.2f} {ay:.2f}) (end {bx:.2f} {by:.2f}) "
            '(stroke (width 0.1) (type solid)) (layer "Edge.Cuts") '
            f'(uuid "{uid(board.name, "edge", i)}"))'
        )
    out.append(
        f'\t(gr_text "kone {board.title}" (at {x0 + 20:.2f} {y0 + 4:.2f}) '
        f'(layer "F.SilkS") (uuid "{uid(board.name, "title")}") '
        "(effects (font (size 2 2) (thickness 0.3))))"
    )
    out.append(")")
    return "\n".join(out) + "\n"


PROJECT = {
    "board": {
        "design_settings": {
            "rule_severities": {
                "unconnected_items": "error",
                "silk_over_copper": "warning",
                "silk_overlap": "warning",
                "lib_footprint_mismatch": "ignore",
            }
        }
    },
    "erc": {"rule_severities": {}},
    "meta": {"filename": "", "version": 3},
    "sheets": [],
    "text_variables": {},
}


def write(board, outdir, tracks=(), vias=(), fixed=False):
    """The whole project: libraries, tables, schematic, board, and its .dsn."""
    from pathlib import Path

    out = Path(outdir)
    (out / "kone.pretty").mkdir(parents=True, exist_ok=True)
    (out / "kone.kicad_sym").write_text(symbol_library(board.symbols.values()))
    seen = set()
    for part in board.parts:
        if not part.footprint or part.footprint in seen:
            continue
        seen.add(part.footprint)
        body = footprint_body(part.footprint)
        (out / "kone.pretty" / f"{part.footprint}.kicad_mod").write_text(body)
    (out / "sym-lib-table").write_text(
        '(sym_lib_table (version 7)\n  (lib (name "kone")(type "KiCad")'
        '(uri "${KIPRJMOD}/kone.kicad_sym")(options "")(descr ""))\n)\n'
    )
    (out / "fp-lib-table").write_text(
        '(fp_lib_table (version 7)\n  (lib (name "kone")(type "KiCad")'
        '(uri "${KIPRJMOD}/kone.pretty")(options "")(descr ""))\n)\n'
    )
    project = dict(PROJECT)
    project["meta"] = {"filename": f"{board.name}.kicad_pro", "version": 3}
    (out / f"{board.name}.kicad_pro").write_text(json.dumps(project, indent=2))
    (out / f"{board.name}.kicad_sch").write_text(schematic(board))
    (out / f"{board.name}.kicad_pcb").write_text(pcb(board, tracks, vias))
    # The design keeps what is routed only when asked: a fresh route starts
    # from an empty board, a second pass keeps the tracks and closes the rest.
    (out / f"{board.name}.dsn").write_text(
        dsn(board, tracks, vias) if fixed else dsn(board)
    )
    return out


# --------------------------------------------------------------------------
# Routing, through Freerouting
#
# KiCad 10's CLI dropped Specctra, so the .dsn goes out from here and the .ses
# comes back the same way: the board is regenerated with the tracks in it.
# --------------------------------------------------------------------------

DSN_SCALE = 10000  # (resolution um 10): one unit is 0.1 um
VIA = "Via[0-1]_800:400_um"
VIA_SIZE, VIA_DRILL = 0.8, 0.4  # mm
TRACK_WIDTH = 0.2  # mm; JLCPCB stops at 0.09, the room matters more
EDGE = 1.0  # mm the routing keeps clear of the outline
# What the router is told to keep, wider than KiCad's 0.2 rule so its rounding
# stays inside it. Which value comes out clean is a property of the board, not
# of the run, so `route` retries with another one (KONE_CLEARANCE) rather than
# running the same board twice.
CLEARANCE = float(os.environ.get("KONE_CLEARANCE", "0.3"))


def _padstack(size, square):
    return (
        f"Rect[A]Pad_{round(size * 1000)}x{round(size * 1000)}_um"
        if square
        else f"Round[A]Pad_{round(size * 1000)}_um"
    )


def _dsn(x, y):
    """DSN keeps y pointing up, KiCad down."""
    return f"{round(x * DSN_SCALE)} {round(-y * DSN_SCALE)}"


def dsn(board, tracks=(), vias=()):
    """The board as a Specctra design, the autorouter's input.

    Tracks handed in go into the wiring section as protected, which is how the
    router is asked to keep what it already found and only close the rest.
    """
    # Inset the boundary: the router lays tracks right up to it, and copper on
    # the board outline is a DRC error.
    x0, y0, x1, y1 = board.extent()
    x0, y0, x1, y1 = x0 + EDGE, y0 + EDGE, x1 - EDGE, y1 - EDGE
    routable = {}
    for part in board.parts:
        if part.symbol == "PWR":
            continue
        for number, net in part.pins.items():
            routable.setdefault(net, []).append(f"{part.ref}-{number}")
    routable = {
        n: p
        for n, p in sorted(routable.items())
        if len(p) > 1 and n not in {net for net, _ in PLANES}
    }

    out = [
        f'(pcb "{board.name}.dsn"',
        "  (parser",
        '    (string_quote ")',
        "    (space_in_quoted_tokens on)",
        '    (host_cad "kone")',
        '    (host_version "1.0")',
        "  )",
        "  (resolution um 10)",
        "  (unit um)",
        "  (structure",
        "    (layer F.Cu (type signal) (property (index 0)))",
        "    (layer B.Cu (type signal) (property (index 1)))",
        "    (boundary (path pcb 0 "
        + " ".join(
            _dsn(x, y)
            for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0))
        )
        + "))",
        f'    (via "{VIA}")',
        *(
            f'    (keepout "" (circle F.Cu {round(HOLE_KEEPOUT * DSN_SCALE)} '
            f"{_dsn(hx, hy)}))\n"
            f'    (keepout "" (circle B.Cu {round(HOLE_KEEPOUT * DSN_SCALE)} '
            f"{_dsn(hx, hy)}))"
            for hx, hy in board.holes
        ),
        f"    (rule (width {round(TRACK_WIDTH * DSN_SCALE)}) "
        f"(clearance {round(CLEARANCE * DSN_SCALE)}) "
        f"(clearance {round(CLEARANCE * DSN_SCALE)} (type default_smd)))",
        "  )",
        "  (placement",
    ]
    by_footprint = {}
    for part in board.parts:
        if part.symbol == "PWR" or not part.pins:
            continue
        by_footprint.setdefault(part.footprint, []).append(part)
    for footprint, group in sorted(by_footprint.items()):
        out.append(f'    (component "{footprint}"')
        for part in group:
            out.append(
                f'      (place "{part.ref}" {_dsn(part.x, part.y)} '
                f'front 0 (PN "{part.value}"))'
            )
        out.append("    )")
    out += ["  )", "  (library"]
    # Pin 1 is a square pad, and its corners are what a circle would hide.
    stacks = set()
    for footprint in sorted(by_footprint):
        out.append(f'    (image "{footprint}"')
        for number, px, py, size, _ in pads(footprint):
            stacks.add((size, number == 1))
            out.append(
                f'      (pin "{_padstack(size, number == 1)}" '
                f"{number} {_dsn(px, py)})"
            )
        out.append("    )")
    for size, square in sorted(stacks):
        half = round(size * DSN_SCALE / 2)
        shape = (
            f"rect {{}} {-half} {-half} {half} {half}"
            if square
            else f"circle {{}} {round(size * DSN_SCALE)}"
        )
        out += [
            f'    (padstack "{_padstack(size, square)}"',
            f"      (shape ({shape.format('F.Cu')}))",
            f"      (shape ({shape.format('B.Cu')}))",
            "      (attach off)",
            "    )",
        ]
    out += [
        f'    (padstack "{VIA}"',
        f"      (shape (circle F.Cu {round(VIA_SIZE * DSN_SCALE)}))",
        f"      (shape (circle B.Cu {round(VIA_SIZE * DSN_SCALE)}))",
        "      (attach off)",
        "    )",
        "  )",
        "  (network",
    ]
    for net, pins_on_net in routable.items():
        out.append(f'    (net "{net}" (pins ' + " ".join(pins_on_net) + "))")
    out += [
        '    (class kicad_default "" ' + " ".join(f'"{n}"' for n in routable),
        f'      (circuit (use_via "{VIA}"))',
        f"      (rule (width {round(TRACK_WIDTH * DSN_SCALE)}) "
        f"(clearance {round(CLEARANCE * DSN_SCALE)}))",
        "    )",
        "  )",
        "  (wiring",
    ]
    for net, layer, width, path in tracks:
        if net in routable:
            out.append(
                f"    (wire (path {layer} {round(width * DSN_SCALE)} "
                + " ".join(_dsn(x, y) for x, y in path)
                + f') (net "{net}") (type protect))'
            )
    for net, x, y in vias:
        if net in routable:
            out.append(
                f'    (via "{VIA}" {_dsn(x, y)} (net "{net}") (type protect))'
            )
    out += ["  )", ")"]
    return "\n".join(out) + "\n"


def _tokens(text):
    return text.replace("(", " ( ").replace(")", " ) ").split()


def _tree(tokens):
    out, stack = [], [[]]
    for token in tokens:
        if token == "(":
            stack.append([])
        elif token == ")":
            done = stack.pop()
            stack[-1].append(done)
        else:
            stack[-1].append(token.strip('"'))
    return stack[0]


def _walk(node, name):
    for item in node:
        if isinstance(item, list) and item and item[0] == name:
            yield item


def _ses_scale(tree, board):
    """Units per mm, read off the placements: the declared resolution lies."""
    at = {p.ref: p for p in board.parts}
    for session in _walk(tree, "session"):
        for placement in _walk(session, "placement"):
            for component in _walk(placement, "component"):
                for place in _walk(component, "place"):
                    part = at.get(place[1])
                    if part and part.x:
                        return float(place[2]) / part.x
    raise NetlistError("no placement in the session file to calibrate on")


def ses_fits(text, board):
    """Whether a session still describes this board.

    A part added or moved since the router ran invalidates every track in it,
    and applying it anyway lays copper through the new pads.
    """
    tree = _tree(_tokens(text))
    placed = {
        place[1]: (component[1], float(place[2]), float(place[3]))
        for session in _walk(tree, "session")
        for placement in _walk(session, "placement")
        for component in _walk(placement, "component")
        for place in _walk(component, "place")
    }
    at = {
        part.ref: part
        for part in board.parts
        if part.symbol != "PWR" and part.pins
    }
    if set(placed) != set(at):
        return False
    scale = _ses_scale(tree, board)
    # References are positional, so a part that changed under one keeps its
    # place: the footprint has to match too, not only the coordinates.
    if not all(
        footprint == at[ref].footprint
        and abs(x / scale - at[ref].x) < 0.01
        and abs(-y / scale - at[ref].y) < 0.01
        for ref, (footprint, x, y) in placed.items()
    ):
        return False
    # And the nets have to be the ones it routed: a signal added to the
    # backplane moves every connector pin onto another net without moving a
    # part, and the old tracks then join the wrong pins.
    pads = {}
    for net, (x, y), _ in _pads_of(board):
        pads[(round(x, 2), round(y, 2))] = net
    for session in _walk(tree, "session"):
        for routes in _walk(session, "routes"):
            for network in _walk(routes, "network_out"):
                for net in _walk(network, "net"):
                    for wire in _walk(net, "wire"):
                        for path in _walk(wire, "path"):
                            xy = [float(v) / scale for v in path[3:]]
                            for i in (0, len(xy) - 2):
                                at_pad = pads.get(
                                    (round(xy[i], 2), round(-xy[i + 1], 2))
                                )
                                if at_pad is not None and at_pad != net[1]:
                                    return False
    return True


def _pads_of(board):
    """Every pad on the board as (net, (x, y), radius)."""
    for part in board.parts:
        for number, dx, dy, size, _ in pads(part.footprint):
            yield part.pins.get(number), (part.x + dx, part.y + dy), size / 2


def parse_ses(text, board):
    """Freerouting's session file -> the tracks and vias it found."""
    tree = _tree(_tokens(text))
    scale = _ses_scale(tree, board)
    tracks, vias = [], []
    for session in _walk(tree, "session"):
        for routes in _walk(session, "routes"):
            for network in _walk(routes, "network_out"):
                for net in _walk(network, "net"):
                    name = net[1]
                    for wire in _walk(net, "wire"):
                        for path in _walk(wire, "path"):
                            layer, width = path[1], float(path[2]) / scale
                            xy = [float(v) / scale for v in path[3:]]
                            points = [
                                (xy[i], -xy[i + 1])
                                for i in range(0, len(xy), 2)
                            ]
                            # The router emits zero-length fragments that DRC
                            # then reports as clearance violations.
                            kept = [points[0]]
                            for point in points[1:]:
                                if (
                                    abs(point[0] - kept[-1][0]) > 0.01
                                    or abs(point[1] - kept[-1][1]) > 0.01
                                ):
                                    kept.append(point)
                            if len(kept) > 1:
                                tracks.append((name, layer, width, kept))
                    for via in _walk(net, "via"):
                        vias.append(
                            (
                                name,
                                float(via[2]) / scale,
                                -float(via[3]) / scale,
                            )
                        )
    return tracks, vias
