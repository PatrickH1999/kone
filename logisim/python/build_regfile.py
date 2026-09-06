#!/usr/bin/env python3
"""kone's 32 x 8-bit register file, as one circuit to instantiate elsewhere.

One 74377 holds each register and one 74245 puts it on the bus. A two-level
74138 tree turns ADDR into 32 active-low selects nS0..nS31; a 7404 inverts RD
and WR, and 7432 gates OR each select with the inverted strobe into the
active-low enables nOE<i> (74245) and nWE<i> (74377 nCLKen).

Logisim Evolution has no bidirectional Pin, so the bus leaves the circuit as
BUS_IN and BUS_OUT; wire both to the same bus net in the parent.
"""

from pathlib import Path

from logisim import *

OUT = Path(__file__).resolve().parents[1] / "regfile.circ"

REGISTERS = 32
COLUMNS = 8                     # a row of 8 is one stage-2 decoder's group
COL_PITCH, ROW_PITCH = 420, 700
GRID = (200, 400)               # the register slices, first so they open in view
CTRL = (100, 3300)              # pins and the two bus splitters
DECODE_Y = 3700                 # the 74138 tree and the strobe inverter
GLUE = (200, 4700)              # the 7432 enable gates

D_PIN = tuple(f"D{k + 1}" for k in range(8))
Q_PIN = tuple(f"Q{k + 1}" for k in range(8))
A_PIN = tuple(f"A{k + 1}" for k in range(8))
B_PIN = tuple(f"B{k + 1}" for k in range(8))


def stub(c, port, to, label, facing, width=1):
    """Tunnel at `to`, wired back to `port`."""
    c.route(port, to)
    return c.add(Tunnel(to[0], to[1], label, width=width, facing=facing))


def register_slice(c, i, x, y):
    """74377 above, 74245 mirrored below it, the bus on named tunnels."""
    reg = c.add(Ttl74377(x, y, label=f"R{i}"))
    drv = c.add(Ttl74245(x + 190, y + 320, facing="west", label=f"R{i}"))

    for k in range(8):
        px, py = reg.port(D_PIN[k])
        below = k < 4
        stub(c, (px, py), (px, py + (20 if below else -20)), f"BI{k}",
             "north" if below else "south")

    # Q -> A. Bits 4-7 leave on the 74377's top row, so they come back down
    # the left of both chips; every net gets a channel and a column of its own.
    for k in range(8):
        src, dst = reg.port(Q_PIN[k]), drv.port(A_PIN[k])
        if k < 4:
            band = y + 110 + 20 * k
            c.route(src, (src[0], band), (dst[0], band), dst)
        else:
            j = k - 4
            over, side = y - 90 - 20 * j, x - 30 - 20 * j
            band = y + 190 + 20 * j
            c.route(src, (src[0], over), (side, over), (side, band),
                    (dst[0], band), dst)

    split = c.add(Splitter(x + 150, y + 390, fanout=8, incoming=8,
                           facing="north", appear="left", spacing=2))
    for k in range(8):
        c.route(drv.port(B_PIN[k]), split.port(str(k)))
    stub(c, split.port("in"), (x + 150, y + 410), "BO", "north", width=8)

    stub(c, reg.port("nCLKen"), (x + 10, y + 90), f"nWE{i}", "north")
    stub(c, reg.port("CLK"), (x + 190, y - 70), "CLK", "south")
    stub(c, drv.port("nOE"), (x + 160, y + 430), f"nOE{i}", "north")

    # DIR high: the register side drives the bus side.
    dir_x, dir_y = drv.port("DIR")
    c.route((dir_x, dir_y), (dir_x, dir_y - 20))
    c.add(Constant(dir_x, dir_y - 20, value=1, facing="south"))


# 74138 pins in left-to-right order along each row; nY7 sits among the inputs.
DEC_BOTTOM = ("A", "B", "C", "nG2A", "nG2B", "G1", "nY7")
DEC_TOP = ("nY0", "nY1", "nY2", "nY3", "nY4", "nY5", "nY6")


def decoder(c, x, y, label, nets):
    """One 74138. nets maps a pin to a tunnel label; nG2B and G1 are strapped."""
    chip = c.add(Ttl74138(x, y, label=label))
    for row, order in ((1, DEC_BOTTOM), (-1, DEC_TOP)):
        for i, pin in enumerate(order):
            px, py = chip.port(pin)
            to = (px, y + row * (70 + 40 * i))
            if pin in ("nG2B", "G1"):
                c.route((px, py), to)
                c.add((Ground if pin == "nG2B" else Power)(*to, facing="south"))
            elif nets.get(pin):
                stub(c, (px, py), to, nets[pin],
                     "north" if row > 0 else "south")
            elif pin in ("C", "nG2A"):
                c.route((px, py), to)
                c.add(Ground(*to, facing="south"))
    return chip


OR_BOTTOM = ("A1", "B1", "Y1", "A2", "B2", "Y2")
OR_TOP = ("A4", "B4", "Y4", "A3", "B3", "Y3")


def or_bank(c, x, y, label, nets):
    chip = c.add(Ttl7432(x, y, label=label))
    for row, order in ((1, OR_BOTTOM), (-1, OR_TOP)):
        for i, pin in enumerate(order):
            px, py = chip.port(pin)
            stub(c, (px, py), (px, y + row * (70 + 40 * i)), nets[pin],
                 "north" if row > 0 else "south")
    return chip


def control(c):
    """Pins, the address decoders and the enable gates."""
    cx, cy = CTRL
    bus_in = c.add(Pin(cx, cy, "BUS_IN", width=8))
    addr = c.add(Pin(cx, cy + 300, "ADDR", width=5))
    for i, name in enumerate(("RD", "WR", "CLK")):
        pin = c.add(Pin(cx, cy + 500 + 100 * i, name))
        stub(c, pin.port(), (cx + 200, cy + 500 + 100 * i), name, "west")

    for pin, count, y, prefix in ((bus_in, 8, cy, "BI"), (addr, 5, cy + 300, "A")):
        split = c.add(Splitter(cx + 100, y, fanout=count, incoming=count,
                               appear="right", spacing=2))
        c.connect(pin, None, split, "in")
        for k in range(count):
            stub(c, split.port(str(k)), (cx + 300, y + 10 + 20 * k),
                 f"{prefix}{k}", "west")

    out = c.add(Pin(cx + 300, cy + 800, "BUS_OUT", width=8, output=True))
    stub(c, out.port(), (cx + 200, cy + 800), "BO", "east", width=8)

    inv = c.add(Ttl7404(2900, DECODE_Y, label="strobes"))
    for i, (pin, net) in enumerate((("A1", "RD"), ("Y1", "nRD"),
                                   ("A2", "WR"), ("Y2", "nWR"))):
        px, py = inv.port(pin)
        stub(c, (px, py), (px, DECODE_Y + 70 + 40 * i), net, "north")
    for pin, dy in (("A3", 70), ("A4", -70), ("A5", -110), ("A6", -150)):
        px, py = inv.port(pin)
        c.route((px, py), (px, DECODE_Y + dy))
        c.add(Ground(px, DECODE_Y + dy, facing="south" if dy > 0 else "north"))

    # ADDR[3:4] picks a group of eight, ADDR[0:2] the register in it.
    decoder(c, 700, DECODE_Y, "group",
            {"A": "A3", "B": "A4",
             **{f"nY{g}": f"nG{g}" for g in range(4)}})
    for g in range(4):
        decoder(c, 1200 + 400 * g, DECODE_Y, f"sel{g}",
                {"A": "A0", "B": "A1", "C": "A2", "nG2A": f"nG{g}",
                 **{f"nY{j}": f"nS{8 * g + j}" for j in range(8)}})

    # nEN<i> = nSTROBE + nS<i>: low only while the strobe is high and the
    # register is selected.
    for bank in range(8):
        for kind, strobe, prefix in (("W", "nWR", "nWE"), ("R", "nRD", "nOE")):
            n = bank + (0 if kind == "W" else 8)
            x, y = GLUE[0] + 400 * (n % 8), GLUE[1] + 700 * (n // 8)
            base = 4 * bank
            or_bank(c, x, y, f"{prefix}{base}-{base + 3}",
                    {f"A{g + 1}": strobe for g in range(4)}
                    | {f"B{g + 1}": f"nS{base + g}" for g in range(4)}
                    | {f"Y{g + 1}": f"{prefix}{base + g}" for g in range(4)})


def regfile():
    c = Circuit("regfile")
    control(c)
    for i in range(REGISTERS):
        col, row = i % COLUMNS, i // COLUMNS
        register_slice(c, i, GRID[0] + COL_PITCH * col, GRID[1] + ROW_PITCH * row)
    return c


if __name__ == "__main__":
    project = Project(main="regfile")
    project.add(regfile())
    print(project.save(OUT))
