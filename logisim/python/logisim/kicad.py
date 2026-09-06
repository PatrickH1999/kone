"""KiCad backend: the same Circuit the .circ writer uses, as a board project.

The netlist is derived from the circuit, not from the generated file, so a
change to a build script reaches Logisim and KiCad alike. Logisim's own parts
have no place on a board: a Tunnel is a net name, a Splitter joins a bus to its
bits, a Pin becomes a header pin, Ground/Power/Constant become the two rails.
"""

from .components import _TtlChip


class NetlistError(ValueError):
    pass


class Netlist:
    """Chips, connectors and the nets between them, all named."""

    def __init__(self, circuit):
        self.circuit = circuit
        self.chips = [c for c in circuit.components if isinstance(c, _TtlChip)]
        self._build()

    # -- net extraction ---------------------------------------------------

    def _build(self):
        nets = self.circuit.nets()
        index = self.circuit.ports_at()
        at = {}                         # location -> net id
        for i, net in enumerate(nets):
            for point in net:
                at[point] = i

        def label(i):
            names = sorted({c.get("label") for p in nets[i] for c in index.get(p, ())
                            if c.NAME == "Tunnel" and c.get("label")})
            return names[0] if names else None

        width = [1] * len(nets)
        for comp in self.circuit.components:
            if comp.NAME in ("Tunnel", "Pin", "Splitter", "Constant"):
                w = int(comp.get("width", 1) if comp.NAME != "Splitter"
                        else comp.get("incoming", 2))
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

        for comp in self.circuit.components:
            if comp.NAME != "Splitter":
                continue
            trunk = at[comp.port("in")]
            fanout = int(comp.get("fanout", 2))
            incoming = int(comp.get("incoming", 2))
            groups = [comp.get(f"bit{i}", i) for i in range(incoming)]
            for end in range(fanout):
                carried = [i for i, g in enumerate(groups) if str(g) == str(end)]
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
                    "GND" if comp.NAME == "Ground" else "+5V")
            elif comp.NAME == "Constant":
                value = int(str(comp.get("value", 1)), 0)
                for bit in range(int(comp.get("width", 1))):
                    rail = "+5V" if (value >> bit) & 1 else "GND"
                    self.rails[find((at[comp.port("out")], bit))] = rail

        self.names = {}
        for i in range(len(nets)):
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

    def net_of(self, comp, pin):
        """Net name at a component's pin."""
        return self.names[self._find((self._at[comp.port(pin)], 0))]

    def pin_nets(self, pin_component):
        """The nets on a Pin, one per bit, in bit order."""
        i = self._at[pin_component.port()]
        return [self.names[self._find((i, bit))]
                for bit in range(self._width[i])]

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

PITCH = 2.54                    # DIP pin pitch, and the schematic grid
ROW = 7.62                      # DIP row spacing, 0.3 inch packages throughout

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


class Part:
    """A placed part: reference, value, footprint and net per pin number."""

    def __init__(self, ref, value, footprint, symbol, pins, at, silk=None):
        self.ref, self.value = ref, value
        self.footprint, self.symbol = footprint, symbol
        self.pins = pins                # {number: net name}
        self.x, self.y = at
        self.silk = silk or value

    def span(self):
        """Width and height the footprint occupies, pads and silk included."""
        if self.footprint.startswith("DIP"):
            pins = int(self.footprint.split("-")[1].split("_")[0])
            return (pins // 2 - 1) * PITCH + 4, ROW + 6
        if self.footprint.startswith("PinHeader"):
            cols, rows = self.footprint.split("_")[1].split("x")
            return ((int(cols) - 1) * PITCH + 4,
                    (int(rows.split("_")[0]) - 1) * PITCH + 6)
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

# The connector every board shares, a 2x20 header. A board wires up the lines
# it uses and leaves the rest of the pads unconnected.
BACKPLANE = (
    "+5V", "GND", "+5V", "GND",
    "BI0", "BI1", "BI2", "BI3", "BI4", "BI5", "BI6", "BI7",
    "BO0", "BO1", "BO2", "BO3", "BO4", "BO5", "BO6", "BO7",
    "A0", "A1", "A2", "A3", "A4",
    "RD", "WR", "CLK",
    "SP0", "SP1", "SP2", "SP3", "SP4", "SP5", "SP6", "SP7",
    "GND", "+5V", "GND", "+5V",
)


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
                self.at[number] = (xs, top - i * PITCH, pin, kind,
                                   -1 if xs < 0 else 1)

    def sexpr(self, prefix=""):
        """The library form; inside a schematic the name is the full lib_id."""
        name = prefix + self.name
        out = [f'\t(symbol "{name}"',
               '\t\t(pin_names (offset 0.508))',
               '\t\t(exclude_from_sim no) (in_bom yes) (on_board yes)',
               f'\t\t(property "Reference" "U" (at 0 {self.height / 2 + 2.54:.2f} 0) {font()})',
               f'\t\t(property "Value" "{self.name}" (at 0 {-self.height / 2 - 2.54:.2f} 0) {font()})',
               f'\t\t(property "Footprint" "kone:{self.footprint}" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
               f'\t\t(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
               f'\t\t(symbol "{self.name}_0_1"',
               f'\t\t\t(rectangle (start {-self.width / 2:.2f} {self.height / 2:.2f}) '
               f'(end {self.width / 2:.2f} {-self.height / 2:.2f}) '
               '(stroke (width 0.254) (type default)) (fill (type background)))',
               '\t\t)',
               f'\t\t(symbol "{self.name}_1_1"']
        for number, (x, y, pin, kind, side) in sorted(self.at.items()):
            angle = 0 if side < 0 else 180
            out.append(f'\t\t\t(pin {kind} line (at {x + side * PITCH:.2f} {y:.2f} {angle}) '
                       f'(length {PITCH}) (name "{pin}" {font(1.0)}) '
                       f'(number "{number}" {font(1.0)}))')
        out += ['\t\t)', '\t)']
        return "\n".join(out)


def symbol_library(symbols):
    out = [f'(kicad_symbol_lib (version {LIB_VERSION}) (generator "kone") '
           '(generator_version "10.0")']
    out += [s.sexpr() for s in symbols]
    out.append(")")
    return "\n".join(out) + "\n"


def _outline(key, box, layers=(("F.SilkS", 0.12), ("F.CrtYd", 0.05))):
    out = []
    for i, (x1, y1) in enumerate(box):
        x2, y2 = box[(i + 1) % 4]
        for layer, width in layers:
            out.append(f'\t(fp_line (start {x1:.2f} {y1:.2f}) (end {x2:.2f} {y2:.2f}) '
                       f'(stroke (width {width}) (type solid)) (layer "{layer}") '
                       f'(uuid "{uid(key, layer, i)}"))')
    return out


def _pad(key, number, shape, x, y, size, drill, nets):
    net = nets.get(str(number))
    tail = f' (net {net[0]} "{net[1]}")' if net else ""
    return (f'\t(pad "{number}" thru_hole {shape} (at {x:.2f} {y:.2f}) '
            f'(size {size} {size}) (drill {drill}) (layers "*.Cu" "*.Mask")'
            f'{tail} (uuid "{uid(key, "pad", number)}"))')


def _head(name, key, at, ref, value, ref_at, value_at):
    place = f" (at {at[0]:.2f} {at[1]:.2f})" if at else ""
    return [f'(footprint "{name}" (version {PCB_VERSION}) (generator "kone") '
            '(generator_version "10.0")',
            f'\t(layer "F.Cu")', f'\t(uuid "{uid(key)}"){place}', '\t(attr through_hole)',
            f'\t(property "Reference" "{ref}" (at {ref_at[0]:.2f} {ref_at[1]:.2f} 0) '
            f'(layer "F.SilkS") (uuid "{uid(key, "ref")}") '
            '(effects (font (size 1 1) (thickness 0.15))))',
            f'\t(property "Value" "{value}" (at {value_at[0]:.2f} {value_at[1]:.2f} 0) '
            f'(layer "F.Fab") (uuid "{uid(key, "val")}") '
            '(effects (font (size 1 1) (thickness 0.15))))']


def pads(footprint):
    """(number, x, y, pad size, drill) of a footprint, its one geometry."""
    if footprint.startswith("DIP"):
        pins = int(footprint.split("-")[1].split("_")[0])
        half = pins // 2
        return [(i + 1, (i if i < half else pins - 1 - i) * PITCH,
                 0.0 if i < half else ROW, 1.6, 0.8) for i in range(pins)]
    if footprint.startswith("PinHeader"):
        cols, rows = footprint.split("_")[1].split("x")
        cols, rows = int(cols), int(rows.split("_")[0])
        return [(col * rows + row + 1, col * PITCH, row * PITCH, 1.7, 1.0)
                for col in range(cols) for row in range(rows)]
    return [(1, 0.0, 0.0, 1.6, 0.8), (2, 5.08, 0.0, 1.6, 0.8)]


def dip_footprint(pins, key=None, at=None, ref="U**", value=None, nets=None):
    """A 0.3 inch DIP, pin 1 top left, numbering counterclockwise."""
    name = f"DIP-{pins}_W7.62mm"
    key, nets = key or f"lib/{name}", nets or {}
    half, body = pins // 2, (pins // 2 - 1) * PITCH
    out = _head(name if at is None else f"kone:{name}", key, at, ref, value or name,
                (body / 2, -2.5), (body / 2, ROW + 2.5))
    for number, x, y, size, drill in pads(name):
        out.append(_pad(key, number, "rect" if number == 1 else "oval",
                        x, y, size, drill, nets))
    out += _outline(key, [(-1.5, -1.5), (body + 1.5, -1.5),
                          (body + 1.5, ROW + 1.5), (-1.5, ROW + 1.5)])
    out.append(f'\t(fp_circle (center -2.6 0) (end -2.2 0) '
               '(stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS") '
               f'(uuid "{uid(key, "dot")}"))')
    out.append(")")
    return "\n".join(out) + "\n"


def header_footprint(rows, cols, key=None, at=None, ref="J**", value=None,
                     nets=None):
    name = f"PinHeader_{cols}x{rows:02d}_P2.54mm"
    key, nets = key or f"lib/{name}", nets or {}
    out = _head(name if at is None else f"kone:{name}", key, at, ref, value or name,
                (0, -2.5), (0, rows * PITCH + 1))
    for number, x, y, size, drill in pads(name):
        out.append(_pad(key, number, "rect" if number == 1 else "oval",
                        x, y, size, drill, nets))
    out += _outline(key, [(-1.5, -1.5), ((cols - 1) * PITCH + 1.5, -1.5),
                          ((cols - 1) * PITCH + 1.5, (rows - 1) * PITCH + 1.5),
                          (-1.5, (rows - 1) * PITCH + 1.5)])
    out.append(")")
    return "\n".join(out) + "\n"


def cap_footprint(key=None, at=None, ref="C**", value="100n", nets=None):
    name = "C_Disc_D5.0mm_P5.08mm"
    key, nets = key or f"lib/{name}", nets or {}
    out = _head(name if at is None else f"kone:{name}", key, at, ref, value,
                (2.54, -3.6), (2.54, 3))
    for number, x in ((1, 0.0), (2, 5.08)):
        out.append(_pad(key, number, "rect" if number == 1 else "oval", x, 0,
                        1.6, 0.8, nets))
    out += _outline(key, [(-1.5, -2.0), (6.6, -2.0), (6.6, 2.0), (-1.5, 2.0)])
    out.append(")")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# One board
# --------------------------------------------------------------------------

ORIGIN = 63.5                   # the sheet grid; every stub lands on 1.27 mm
CELL = (30.0, 25.0)             # board grid per IC, room for its decoupling cap
SCH_CELL = (63.5, 50.8)         # schematic grid, room for pin labels
LAYERS = ((0, "F.Cu", "signal", None), (2, "B.Cu", "signal", None),
          (9, "F.Adhes", "user", "F.Adhesive"), (11, "F.Paste", "user", None),
          (13, "F.SilkS", "user", "F.Silkscreen"), (15, "F.Mask", "user", None),
          (17, "B.Mask", "user", None), (31, "B.SilkS", "user", "B.Silkscreen"),
          (33, "F.CrtYd", "user", "F.Courtyard"), (35, "F.Fab", "user", None),
          (44, "Edge.Cuts", "user", None), (45, "Margin", "user", None))


class Board:
    """The chips of one Circuit as a KiCad project: schematic, board, libraries.

    Placement follows the order the build script created the chips in, so the
    board keeps the structure of the logic: a row of registers stays a row.
    """

    def __init__(self, name, circuit, columns=8, title=None):
        self.name, self.title = name, title or name
        self.netlist = Netlist(circuit)
        self.columns = columns
        self.parts = []
        self.symbols = {}
        self._place()

    # -- parts -------------------------------------------------------------

    def _symbol(self, key, pins, footprint):
        if key not in self.symbols:
            self.symbols[key] = Symbol(key, pins, footprint)
        return self.symbols[key]

    def _place(self):
        chips = sorted(self.netlist.chips, key=lambda c: (c.y, c.x))
        for i, chip in enumerate(chips):
            col, row = i % self.columns, i // self.columns
            pins = dip(chip)
            self._symbol(chip.NAME, pins, package(chip))
            nets = {}
            for number, pin, kind in pins:
                nets[number] = ({"VCC": "+5V", "GND": "GND"}[pin]
                                if kind == "power_in"
                                else self.netlist.net_of(chip, pin))
            label = chip.get("label")
            self.parts.append(Part(
                f"U{i + 1}", chip.NAME, package(chip), chip.NAME, nets,
                (20 + col * CELL[0], 20 + row * CELL[1]),
                silk=f"{chip.NAME} {label}" if label else chip.NAME))
            self._symbol("C", [(1, "1", "passive"), (2, "2", "passive")],
                         "C_Disc_D5.0mm_P5.08mm")
            self.parts.append(Part(
                f"C{i + 1}", "100n", "C_Disc_D5.0mm_P5.08mm", "C",
                {1: "+5V", 2: "GND"},
                (22 + col * CELL[0], 35 + row * CELL[1]), silk="100n"))
        self.ic_rows = (len(chips) + self.columns - 1) // self.columns

        # The backplane header: every board carries the same pinout, wired up
        # only where the board has that signal.
        have = {net for _, nets in self.netlist.connectors() for net in nets}
        have |= {"+5V", "GND"}
        self.backplane = [(i + 1, n if n in have else None)
                          for i, n in enumerate(BACKPLANE)]
        rows = len(BACKPLANE) // 2
        self._symbol("Conn_2x20", [(n, str(n), "passive")
                                   for n, _ in self.backplane],
                     f"PinHeader_2x{rows:02d}_P2.54mm")
        self.parts.append(Part(
            "J1", "Backplane", f"PinHeader_2x{rows:02d}_P2.54mm", "Conn_2x20",
            {n: net for n, net in self.backplane if net},
            (20, 30 + self.ic_rows * CELL[1]), silk="BACKPLANE"))
        self._symbol("Conn_1x02", [(1, "1", "passive"), (2, "2", "passive")],
                     "PinHeader_1x02_P2.54mm")
        self.parts.append(Part(
            "J2", "Power", "PinHeader_1x02_P2.54mm", "Conn_1x02",
            {1: "+5V", 2: "GND"},
            (20 + 8 * PITCH, 30 + self.ic_rows * CELL[1]), silk="+5V / GND"))
        self._symbol("PWR", [(1, "1", "power_out")], "")
        self.parts.append(Part("PWR1", "+5V", "", "PWR", {1: "+5V"}, (0, 0)))
        self.parts.append(Part("PWR2", "GND", "", "PWR", {1: "GND"}, (0, 0)))

    def nets(self):
        """Net name -> index, GND and +5V first."""
        names = sorted({n for p in self.parts for n in p.pins.values()})
        names.sort(key=lambda n: (n not in ("GND", "+5V"), n))
        return {n: i + 1 for i, n in enumerate(names)}

    def extent(self):
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
        at[part.ref] = (ORIGIN + (ic % board.columns) * SCH_CELL[0],
                        ORIGIN + (ic // board.columns) * SCH_CELL[1])
        ic += 1
    bottom = ORIGIN + ((ic + board.columns - 1) // board.columns) * SCH_CELL[1]
    for part in board.parts:
        if part.symbol == "C":
            at[part.ref] = (ORIGIN + (cap % 16) * 25.4, bottom + (cap // 16) * 25.4)
            cap += 1
    bottom += ((cap + 15) // 16) * 25.4 + 38.1
    for i, part in enumerate(p for p in board.parts
                             if p.symbol.startswith("Conn") or p.symbol == "PWR"):
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

    out = [f'(kicad_sch (version {SCH_VERSION}) (generator "kone") '
           '(generator_version "10.0")',
           f'\t(uuid "{uid(board.name, "sheet")}")',
           f'\t(paper "User" {width:.1f} {height:.1f})',
           f'\t(title_block (title "kone {board.title}") (company "generated by '
           'logisim/python"))',
           '\t(lib_symbols']
    out += [s.sexpr("kone:") for s in board.symbols.values()]
    out.append('\t)')

    for part in board.parts:
        sym = board.symbols[part.symbol]
        x, y = at[part.ref]
        key = (board.name, part.ref)
        out += [f'\t(symbol (lib_id "kone:{part.symbol}") (at {x:.2f} {y:.2f} 0) '
                '(unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)',
                f'\t\t(uuid "{uid(*key)}")',
                f'\t\t(property "Reference" "{part.ref}" '
                f'(at {x:.2f} {y - sym.height / 2 - 2.54:.2f} 0) {font()})',
                f'\t\t(property "Value" "{part.value}" '
                f'(at {x:.2f} {y + sym.height / 2 + 2.54:.2f} 0) {font()})',
                f'\t\t(property "Footprint" '
                f'"{"kone:" + part.footprint if part.footprint else ""}" '
                f'(at {x:.2f} {y:.2f} 0) '
                '(effects (font (size 1.27 1.27)) (hide yes)))']
        for number in sorted(sym.at):
            out.append(f'\t\t(pin "{number}" (uuid "{uid(*key, number)}"))')
        out += [f'\t\t(instances (project "{board.name}" (path "/{uid(board.name, "sheet")}" '
                f'(reference "{part.ref}") (unit 1))))',
                '\t)']
        for number, (px, py, pin, kind, side) in sym.at.items():
            cx, cy = x + px + side * PITCH, y - py
            net = part.pins.get(number)
            if net is None or used.get(net, 0) < 2:
                out.append(f'\t(no_connect (at {cx:.2f} {cy:.2f}) '
                           f'(uuid "{uid(*key, "nc", number)}"))')
                continue
            ex = cx + side * PITCH
            out += [f'\t(wire (pts (xy {cx:.2f} {cy:.2f}) (xy {ex:.2f} {cy:.2f})) '
                    '(stroke (width 0) (type default)) '
                    f'(uuid "{uid(*key, "w", number)}"))',
                    f'\t(label "{net}" (at {ex:.2f} {cy:.2f} {0 if side > 0 else 180}) '
                    f'(effects (font (size 1.27 1.27)) (justify left bottom)) '
                    f'(uuid "{uid(*key, "l", number)}"))']
    out += [f'\t(sheet_instances (path "/" (page "1")))', '\t(embedded_fonts no)', ')']
    return "\n".join(out) + "\n"


def pcb(board, tracks=(), vias=()):
    """The board: footprints on the logic's own grid, and what Freerouting found."""
    nets = board.nets()
    x0, y0, x1, y1 = board.extent()
    out = [f'(kicad_pcb (version {PCB_VERSION}) (generator "kone") '
           '(generator_version "10.0")',
           '\t(general (thickness 1.6) (legacy_teardrops no))', '\t(paper "A4")',
           '\t(layers']
    for number, name, kind, alias in LAYERS:
        out.append(f'\t\t({number} "{name}" {kind}'
                   + (f' "{alias}")' if alias else ")"))
    out += ['\t)', '\t(setup (pad_to_mask_clearance 0))', '\t(net 0 "")']
    out += [f'\t(net {i} "{n}")' for n, i in sorted(nets.items(), key=lambda kv: kv[1])]

    for part in board.parts:
        if part.symbol == "PWR":
            continue
        pads = {str(n): (nets[net], net) for n, net in part.pins.items()}
        if part.footprint.startswith("DIP"):
            body = dip_footprint(int(part.footprint.split("-")[1].split("_")[0]),
                                 key=part.ref, at=(part.x, part.y), ref=part.ref,
                                 value=part.value, nets=pads)
        elif part.footprint.startswith("C_"):
            body = cap_footprint(key=part.ref, at=(part.x, part.y), ref=part.ref,
                                 value=part.value, nets=pads)
        else:
            cols, rows = part.footprint.split("_")[1].split("x")
            body = header_footprint(int(rows.split("_")[0]), int(cols),
                                    key=part.ref, at=(part.x, part.y),
                                    ref=part.ref, value=part.value, nets=pads)
        out.append("\t" + body.replace("\n", "\n\t").rstrip("\t"))
        if part.footprint.startswith("C_"):
            continue                    # its reference on the silk is enough
        w, _ = part.span()
        out.append(f'\t(gr_text "{part.silk}" (at {part.x + w / 2 - 2:.2f} '
                   f'{part.y + ROW + 2.4:.2f}) (layer "F.SilkS") '
                   f'(uuid "{uid(part.ref, "silk")}") '
                   '(effects (font (size 1 1) (thickness 0.15))))')

    nets_by_name = {n: i for n, i in nets.items()}
    for i, (net, layer, width, points) in enumerate(tracks):
        for j, ((ax, ay), (bx, by)) in enumerate(zip(points, points[1:])):
            out.append(f'\t(segment (start {ax:.4f} {ay:.4f}) '
                       f'(end {bx:.4f} {by:.4f}) (width {width:.3f}) '
                       f'(layer "{layer}") (net {nets_by_name.get(net, 0)}) '
                       f'(uuid "{uid(board.name, "seg", i, j)}"))')
    for i, (net, vx, vy) in enumerate(vias):
        out.append(f'\t(via (at {vx:.4f} {vy:.4f}) (size {VIA_SIZE}) '
                   f'(drill {VIA_DRILL}) '
                   f'(layers "F.Cu" "B.Cu") (net {nets_by_name.get(net, 0)}) '
                   f'(uuid "{uid(board.name, "via", i)}"))')

    box = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for i, (ax, ay) in enumerate(box):
        bx, by = box[(i + 1) % 4]
        out.append(f'\t(gr_line (start {ax:.2f} {ay:.2f}) (end {bx:.2f} {by:.2f}) '
                   '(stroke (width 0.1) (type solid)) (layer "Edge.Cuts") '
                   f'(uuid "{uid(board.name, "edge", i)}"))')
    out.append(f'\t(gr_text "kone {board.title}" (at {x0 + 20:.2f} {y0 + 4:.2f}) '
               f'(layer "F.SilkS") (uuid "{uid(board.name, "title")}") '
               '(effects (font (size 2 2) (thickness 0.3))))')
    out.append(")")
    return "\n".join(out) + "\n"


PROJECT = {
    "board": {"design_settings": {"rule_severities": {
        "unconnected_items": "warning", "silk_over_copper": "warning",
        "silk_overlap": "warning", "lib_footprint_mismatch": "ignore"}}},
    "erc": {"rule_severities": {}},
    "meta": {"filename": "", "version": 3},
    "sheets": [], "text_variables": {},
}


def write(board, outdir, tracks=(), vias=()):
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
        if part.footprint.startswith("DIP"):
            body = dip_footprint(int(part.footprint.split("-")[1].split("_")[0]))
        elif part.footprint.startswith("C_"):
            body = cap_footprint()
        else:
            cols, rows = part.footprint.split("_")[1].split("x")
            body = header_footprint(int(rows.split("_")[0]), int(cols))
        (out / "kone.pretty" / f"{part.footprint}.kicad_mod").write_text(body)
    (out / "sym-lib-table").write_text(
        '(sym_lib_table (version 7)\n  (lib (name "kone")(type "KiCad")'
        '(uri "${KIPRJMOD}/kone.kicad_sym")(options "")(descr ""))\n)\n')
    (out / "fp-lib-table").write_text(
        '(fp_lib_table (version 7)\n  (lib (name "kone")(type "KiCad")'
        '(uri "${KIPRJMOD}/kone.pretty")(options "")(descr ""))\n)\n')
    project = dict(PROJECT)
    project["meta"] = {"filename": f"{board.name}.kicad_pro", "version": 3}
    (out / f"{board.name}.kicad_pro").write_text(json.dumps(project, indent=2))
    (out / f"{board.name}.kicad_sch").write_text(schematic(board))
    (out / f"{board.name}.kicad_pcb").write_text(pcb(board, tracks, vias))
    (out / f"{board.name}.dsn").write_text(dsn(board))
    return out


# --------------------------------------------------------------------------
# Routing, through Freerouting
#
# KiCad 10's CLI dropped Specctra, so the .dsn goes out from here and the .ses
# comes back the same way: the board is regenerated with the tracks in it.
# --------------------------------------------------------------------------

DSN_SCALE = 10000               # (resolution um 10): one unit is 0.1 um
VIA = "Via[0-1]_800:400_um"
VIA_SIZE, VIA_DRILL = 0.8, 0.4  # mm
TRACK_WIDTH = 0.25              # mm
CLEARANCE = 0.2                 # mm


def _padstack(size, square):
    return (f"Rect[A]Pad_{round(size * 1000)}x{round(size * 1000)}_um" if square
            else f"Round[A]Pad_{round(size * 1000)}_um")


def _dsn(x, y):
    """DSN keeps y pointing up, KiCad down."""
    return f"{round(x * DSN_SCALE)} {round(-y * DSN_SCALE)}"


def dsn(board):
    """The board as a Specctra design, the autorouter's input."""
    x0, y0, x1, y1 = board.extent()
    routable = {}
    for part in board.parts:
        if part.symbol == "PWR":
            continue
        for number, net in part.pins.items():
            routable.setdefault(net, []).append(f"{part.ref}-{number}")
    routable = {n: p for n, p in sorted(routable.items()) if len(p) > 1}

    out = [f'(pcb "{board.name}.dsn"', '  (parser',
           '    (string_quote ")', '    (space_in_quoted_tokens on)',
           '    (host_cad "kone")', '    (host_version "1.0")', '  )',
           '  (resolution um 10)', '  (unit um)', '  (structure',
           '    (layer F.Cu (type signal) (property (index 0)))',
           '    (layer B.Cu (type signal) (property (index 1)))',
           '    (boundary (path pcb 0 ' + " ".join(
               _dsn(x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1),
                                       (x0, y0))) + '))',
           f'    (via "{VIA}")',
           f'    (rule (width {round(TRACK_WIDTH * DSN_SCALE)}) '
           f'(clearance {round(CLEARANCE * DSN_SCALE)}) '
           f'(clearance {round(CLEARANCE * DSN_SCALE)} (type default_smd)))',
           '  )', '  (placement']
    by_footprint = {}
    for part in board.parts:
        if part.symbol == "PWR":
            continue
        by_footprint.setdefault(part.footprint, []).append(part)
    for footprint, group in sorted(by_footprint.items()):
        out.append(f'    (component "{footprint}"')
        for part in group:
            out.append(f'      (place "{part.ref}" {_dsn(part.x, part.y)} '
                       f'front 0 (PN "{part.value}"))')
        out.append('    )')
    out += ['  )', '  (library']
    # Pin 1 is a square pad, and its corners are what a circle would hide.
    stacks = set()
    for footprint in sorted(by_footprint):
        out.append(f'    (image "{footprint}"')
        for number, px, py, size, _ in pads(footprint):
            stacks.add((size, number == 1))
            out.append(f'      (pin "{_padstack(size, number == 1)}" '
                       f'{number} {_dsn(px, py)})')
        out.append('    )')
    for size, square in sorted(stacks):
        half = round(size * DSN_SCALE / 2)
        shape = (f"rect {{}} {-half} {-half} {half} {half}" if square
                 else f"circle {{}} {round(size * DSN_SCALE)}")
        out += [f'    (padstack "{_padstack(size, square)}"',
                f'      (shape ({shape.format("F.Cu")}))',
                f'      (shape ({shape.format("B.Cu")}))',
                '      (attach off)', '    )']
    out += [f'    (padstack "{VIA}"',
            f'      (shape (circle F.Cu {round(VIA_SIZE * DSN_SCALE)}))',
            f'      (shape (circle B.Cu {round(VIA_SIZE * DSN_SCALE)}))',
            '      (attach off)', '    )',
            '  )', '  (network']
    for net, pins_on_net in routable.items():
        out.append(f'    (net "{net}" (pins ' + " ".join(pins_on_net) + '))')
    out += ['    (class kicad_default "" ' + " ".join(
                f'"{n}"' for n in routable),
            f'      (circuit (use_via "{VIA}"))',
            f'      (rule (width {round(TRACK_WIDTH * DSN_SCALE)}) '
            f'(clearance {round(CLEARANCE * DSN_SCALE)}))',
            '    )', '  )', '  (wiring', '  )', ')']
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
                            points = [(xy[i], -xy[i + 1])
                                      for i in range(0, len(xy), 2)]
                            tracks.append((name, layer, width, points))
                    for via in _walk(net, "via"):
                        vias.append((name, float(via[2]) / scale,
                                     -float(via[3]) / scale))
    return tracks, vias
