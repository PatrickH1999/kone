"""Component, Wire, Circuit and Project: the .circ document model."""

import warnings
from xml.sax.saxutils import escape, quoteattr

GRID = 10

# Library ids as Logisim Evolution 4.1 writes them; the header declares all of
# them so a hand-edit in the GUI does not renumber ours.
LIBRARIES = [
    "Wiring", "Gates", "Plexers", "Arithmetic", "FPArithmetic", "Memory",
    "I/O", "TTL", "TCL", "Base", "BFH-Praktika", "Input/Output-Extra", "Soc",
]
LIB_ID = {name: i for i, name in enumerate(LIBRARIES)}

STRICT_GRID = True


class GridError(ValueError):
    pass


class PortError(KeyError):
    pass


def on_grid(x, y, what="point"):
    if x % GRID == 0 and y % GRID == 0:
        return
    msg = f"{what} at ({x},{y}) is off the {GRID}px grid"
    if STRICT_GRID:
        raise GridError(msg)
    warnings.warn(msg, stacklevel=3)


def attr_value(value):
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def _attr_xml(attrs, indent):
    return "".join(
        f'{indent}<a name={quoteattr(str(k))} val={quoteattr(attr_value(v))}/>\n'
        for k, v in attrs.items()
    )


def rotate(dx, dy, facing):
    """Rotate an offset given for facing "east" onto another facing."""
    if facing == "east":
        return dx, dy
    if facing == "north":
        return dy, -dx
    if facing == "west":
        return -dx, -dy
    if facing == "south":
        return -dy, dx
    raise ValueError(f"bad facing {facing!r}")


class Component:
    LIB = "Wiring"
    NAME = ""
    PORTS = ()          # ((name, dx, dy), ...) in Logisim's own end order
    ALIASES = {}        # extra name -> canonical name

    def __init__(self, x, y, **attrs):
        self.x, self.y = int(x), int(y)
        self.attrs = {k: v for k, v in attrs.items() if v is not None}
        on_grid(self.x, self.y, type(self).__name__)

    def get(self, name, default=None):
        return self.attrs.get(name, default)

    def port_spec(self):
        return self.PORTS

    def ports(self):
        return [(n, self.x + dx, self.y + dy) for n, dx, dy in self.port_spec()]

    def port_names(self):
        return [n for n, _, _ in self.port_spec()]

    def port(self, name=None):
        """Absolute (x, y) of a port, by name, alias or index."""
        spec = self.port_spec()
        if name is None:
            if len(spec) != 1:
                raise PortError(
                    f"{self.NAME} has {len(spec)} ports, name one of "
                    f"{self.port_names()}")
            name = spec[0][0]
        if isinstance(name, int):
            n, dx, dy = spec[name]
            return self.x + dx, self.y + dy
        key = self.ALIASES.get(name, name)
        for n, dx, dy in spec:
            if n == key:
                return self.x + dx, self.y + dy
        raise PortError(f"{self.NAME} has no port {name!r}; have {self.port_names()}")

    def to_xml(self, indent="    "):
        lib = f'lib="{LIB_ID[self.LIB]}" ' if self.LIB else ""
        head = f'{indent}<comp {lib}loc="({self.x},{self.y})" name={quoteattr(self.NAME)}'
        if not self.attrs:
            return head + "/>\n"
        return (head + ">\n" + _attr_xml(self.attrs, indent + "  ")
                + f"{indent}</comp>\n")

    def __repr__(self):
        return f"<{type(self).__name__} {self.NAME} ({self.x},{self.y})>"


class Wire:
    def __init__(self, a, b):
        (x1, y1), (x2, y2) = a, b
        if x1 != x2 and y1 != y2:
            raise ValueError(
                f"wire ({x1},{y1})-({x2},{y2}) is neither horizontal nor vertical")
        on_grid(x1, y1, "wire end")
        on_grid(x2, y2, "wire end")
        self.a, self.b = (x1, y1), (x2, y2)

    def to_xml(self, indent="    "):
        return (f'{indent}<wire from="({self.a[0]},{self.a[1]})" '
                f'to="({self.b[0]},{self.b[1]})"/>\n')


class Circuit:
    """A named circuit; instantiate it with instance() to nest it in another.

    appearance "custom" makes the library emit an explicit <appear> block, so a
    subcircuit's port offsets are exactly the ones port() reports. Logisim's own
    layouts size the box from the rendered text, which cannot be reproduced here,
    so port() refuses to guess for them.
    """

    PITCH = 20          # vertical spacing of ports on a custom appearance

    def __init__(self, name, appearance="custom", simulation_frequency=None):
        self.name = name
        self.appearance = appearance
        self.components = []
        self.wires = []
        self.attrs = {"appearance": appearance, "circuit": name}
        if simulation_frequency is not None:
            self.attrs["simulationFrequency"] = simulation_frequency

    # -- building ---------------------------------------------------------

    def add(self, component):
        self.components.append(component)
        return component

    def extend(self, components):
        for c in components:
            self.add(c)
        return components

    def wire(self, a, b):
        w = Wire(a, b)
        if w.a != w.b:
            self.wires.append(w)
        return w

    def route(self, *points, style="hv"):
        """Wire a path. Two points that share no axis get an L with one corner."""
        pts = [tuple(p) for p in points]
        made = []
        for a, b in zip(pts, pts[1:]):
            if a[0] != b[0] and a[1] != b[1]:
                corner = (b[0], a[1]) if style == "hv" else (a[0], b[1])
                made.append(self.wire(a, corner))
                made.append(self.wire(corner, b))
            else:
                made.append(self.wire(a, b))
        return [w for w in made if w is not None]

    def connect(self, src, src_port, dst, dst_port=None, style="hv"):
        """Wire two component ports by name: connect(adder, "A", pin_a)."""
        return self.route(_endpoint(src, src_port), _endpoint(dst, dst_port),
                          style=style)

    # -- pins and subcircuit appearance ------------------------------------

    def pins(self):
        return [c for c in self.components if getattr(c, "IS_PIN", False)]

    def input_pins(self):
        return [p for p in self.pins() if p.get("type") != "output"]

    def output_pins(self):
        return [p for p in self.pins() if p.get("type") == "output"]

    def instance(self, x, y, **attrs):
        return Subcircuit(self, x, y, **attrs)

    def port_layout(self):
        """(width, height, [(label, dx, dy)]) of the generated <appear> box."""
        ins, outs = self.input_pins(), self.output_pins()
        for p in ins + outs:
            if not p.get("label"):
                raise ValueError(
                    f"circuit {self.name!r}: every pin needs a label to be usable "
                    f"as a subcircuit port ({p!r})")
        longest = lambda ps: max((len(p.get("label")) for p in ps), default=0)
        width = max(80, _ceil_grid(8 * (longest(ins) + longest(outs) + 3)),
                    _ceil_grid(8 * (len(self.name) + 2)))
        height = max(2 * self.PITCH,
                     self.PITCH * (max(len(ins), len(outs)) + 1))
        ports = [(p.get("label"), 0, self.PITCH * (i + 1))
                 for i, p in enumerate(ins)]
        ports += [(p.get("label"), width, self.PITCH * (i + 1))
                  for i, p in enumerate(outs)]
        return width, height, ports

    def _appear_xml(self, indent="    "):
        # Appearance coordinates are relative to <circ-anchor>, so any origin
        # works; 100,100 keeps the box in view of Logisim's appearance editor.
        ox = oy = 100
        width, height, ports = self.port_layout()
        pins = self.input_pins() + self.output_pins()
        out = [f"{indent}<appear>\n"]
        out.append(f'{indent}  <rect fill="none" height="{height}" '
                   f'stroke="#000000" stroke-width="2" width="{width}" '
                   f'x="{ox}" y="{oy}"/>\n')
        out.append(f'{indent}  <text font-family="SansSerif" font-size="12" '
                   f'text-anchor="middle" x="{ox + width // 2}" y="{oy + 14}">'
                   f"{escape(self.name)}</text>\n")
        out.append(f'{indent}  <circ-anchor facing="east" height="6" width="6" '
                   f'x="{ox - 3}" y="{oy - 3}"/>\n')
        n_in = len(self.input_pins())
        for i, (pin, (_, dx, dy)) in enumerate(zip(pins, ports)):
            # Logisim reads the direction off the radius: 4 in, 5 out.
            radius, direction = (4, "in") if i < n_in else (5, "out")
            out.append(f'{indent}  <circ-port dir="{direction}" '
                       f'height="{2 * radius}" pin="{pin.x},{pin.y}" '
                       f'width="{2 * radius}" x="{ox + dx - radius}" '
                       f'y="{oy + dy - radius}"/>\n')
        out.append(f"{indent}</appear>\n")
        return "".join(out)

    # -- output -----------------------------------------------------------

    def nets(self):
        """Connected groups of port and wire-end locations.

        Logisim joins wires at a shared endpoint and wherever an endpoint or a
        port lands inside another wire, so wires that merely cross are two nets.
        """
        parent = {}

        def find(p):
            parent.setdefault(p, p)
            while parent[p] != p:
                parent[p] = parent[parent[p]]
                p = parent[p]
            return p

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        rows, cols = {}, {}
        for w in self.wires:
            union(w.a, w.b)
            if w.a[1] == w.b[1]:
                rows.setdefault(w.a[1], []).append(w)
            else:
                cols.setdefault(w.a[0], []).append(w)

        points = {p for w in self.wires for p in (w.a, w.b)}
        points.update(p for c in self.components for p in
                      ((x, y) for _, x, y in c.ports()))
        for x, y in points:
            for w in rows.get(y, ()):
                if min(w.a[0], w.b[0]) < x < max(w.a[0], w.b[0]):
                    union((x, y), w.a)
            for w in cols.get(x, ()):
                if min(w.a[1], w.b[1]) < y < max(w.a[1], w.b[1]):
                    union((x, y), w.a)

        nets = {}
        for p in points:
            nets.setdefault(find(p), []).append(p)
        return list(nets.values())

    def ports_at(self):
        """Location -> the components with a port there."""
        index = {}
        for comp in self.components:
            for _, x, y in comp.ports():
                index.setdefault((x, y), []).append(comp)
        return index

    def check(self):
        problems = []
        seen = {}
        for c in self.components:
            key = (c.NAME, c.x, c.y)
            if key in seen:
                problems.append(f"{self.name}: two {c.NAME} at ({c.x},{c.y})")
            seen[key] = c
        labels = [p.get("label") for p in self.pins() if p.get("label")]
        for label in set(labels):
            if labels.count(label) > 1:
                problems.append(f"{self.name}: {labels.count(label)} pins labelled {label!r}")
        index = self.ports_at()
        nets = self.nets()
        for net in nets:
            tunnels = {c.get("label") for p in net for c in index.get(p, ())
                       if c.NAME == "Tunnel"}
            if len(tunnels) > 1:
                problems.append(
                    f"{self.name}: tunnels {sorted(tunnels)} share the net at "
                    f"{min(net)}")
        net_of = {p: net for net in nets for p in net}
        for comp in self.components:
            for name in getattr(comp, "INPUTS", ()):
                loc = comp.port(name)
                if not any(other is not comp
                           for p in net_of.get(loc, [loc])
                           for other in index.get(p, ())):
                    problems.append(
                        f"{self.name}: {comp.NAME} {comp.get('label', '')!r} "
                        f"input {name} at {loc} is floating")
        return problems

    def to_xml(self, indent="  "):
        body = [f"{indent}<circuit name={quoteattr(self.name)}>\n"]
        body.append(_attr_xml(self.attrs, indent + "  "))
        if self.appearance == "custom" and self.pins():
            body.append(self._appear_xml(indent + "  "))
        for c in self.components:
            body.append(c.to_xml(indent + "  "))
        for w in sorted(self.wires, key=lambda w: (w.a, w.b)):
            body.append(w.to_xml(indent + "  "))
        body.append(f"{indent}</circuit>\n")
        return "".join(body)


class Subcircuit(Component):
    """A Circuit placed inside another Circuit. loc is the box's top-left corner."""

    LIB = None

    def __init__(self, circuit, x, y, **attrs):
        self.circuit = circuit
        self.NAME = circuit.name
        super().__init__(x, y, **attrs)

    def port_spec(self):
        if self.circuit.appearance != "custom":
            raise PortError(
                f"circuit {self.circuit.name!r} uses Logisim's {self.circuit.appearance!r} "
                f"appearance, whose port positions depend on rendered text; use "
                f"appearance='custom' to address its ports by name")
        return self.circuit.port_layout()[2]


class Project:
    HEADER = (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
        '<project source="{source}" version="{version}">\n'
        "  This file is intended to be loaded by Logisim-evolution "
        "v{source}(https://github.com/logisim-evolution/).\n\n"
    )
    OPTIONS = (
        "  <options>\n"
        '    <a name="gateUndefined" val="ignore"/>\n'
        '    <a name="simlimit" val="1000"/>\n'
        '    <a name="simrand" val="0"/>\n'
        "  </options>\n"
        "  <mappings>\n"
        '    <tool lib="9" map="Button2" name="Poke Tool"/>\n'
        '    <tool lib="9" map="Button3" name="Menu Tool"/>\n'
        '    <tool lib="9" map="Ctrl Button1" name="Menu Tool"/>\n'
        "  </mappings>\n"
        "  <toolbar>\n"
        '    <tool lib="9" name="Poke Tool"/>\n'
        '    <tool lib="9" name="Edit Tool"/>\n'
        '    <tool lib="9" name="Wiring Tool"/>\n'
        '    <tool lib="9" name="Text Tool"/>\n'
        "    <sep/>\n"
        '    <tool lib="0" name="Pin"/>\n'
        '    <tool lib="0" name="Pin">\n'
        '      <a name="facing" val="west"/>\n'
        '      <a name="type" val="output"/>\n'
        "    </tool>\n"
        "    <sep/>\n"
        '    <tool lib="1" name="NOT Gate"/>\n'
        '    <tool lib="1" name="AND Gate"/>\n'
        '    <tool lib="1" name="OR Gate"/>\n'
        '    <tool lib="1" name="XOR Gate"/>\n'
        '    <tool lib="1" name="NAND Gate"/>\n'
        '    <tool lib="1" name="NOR Gate"/>\n'
        "    <sep/>\n"
        '    <tool lib="5" name="D Flip-Flop"/>\n'
        '    <tool lib="5" name="Register"/>\n'
        "  </toolbar>\n"
    )

    def __init__(self, main="main", source="4.1.0", version="1.0"):
        self.circuits = []
        self.main = main
        self.source = source
        self.version = version

    def add(self, circuit):
        self.circuits.append(circuit)
        return circuit

    def circuit(self, name, **kwargs):
        return self.add(Circuit(name, **kwargs))

    def check(self):
        problems = []
        names = [c.name for c in self.circuits]
        for name in set(names):
            if names.count(name) > 1:
                problems.append(f"{names.count(name)} circuits named {name!r}")
        if self.main not in names:
            problems.append(f"main circuit {self.main!r} is not in the project")
        for c in self.circuits:
            problems.extend(c.check())
        return problems

    def to_xml(self):
        out = [self.HEADER.format(source=self.source, version=self.version)]
        for i, lib in enumerate(LIBRARIES):
            out.append(f'  <lib desc="#{lib}" name="{i}"/>\n')
        out.append(f'  <main name={quoteattr(self.main)}/>\n')
        out.append(self.OPTIONS)
        for c in self.circuits:
            out.append(c.to_xml())
        out.append("</project>\n")
        return "".join(out)

    def save(self, path, check=True):
        if check:
            problems = self.check()
            if problems:
                raise ValueError("; ".join(problems))
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_xml())
        return path


def _endpoint(obj, port=None):
    if isinstance(obj, (tuple, list)):
        x, y = obj
        on_grid(x, y, "endpoint")
        return int(x), int(y)
    return obj.port(port)


def _ceil_grid(n):
    return -(-int(n) // GRID) * GRID
