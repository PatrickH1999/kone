#!/usr/bin/env python3
"""The whole kone CPU: six blocks wired together, one per job.

    python3 logisim/python/build_kone.py [bin/display.bin]

The top level is a block diagram -- regfile, alu, sequencer, datapath, memory
and io, joined by named buses. Everything the C VM keeps in CPU.R lives in the
register file, so the datapath is small: one main bus, a few 74377 latches and
two source muxes. The sequencer is seven 256-byte ROMs addressed by a
microprogram counter (see kone_microcode.py); two more turn an opcode into a
microcode address, which is cpu_decode_exec()'s switch.

Memory is split at 0x8000: the program sits in ROM below, RAM covers the half
above, which is where klib scratch, program data and the stack live. Writes
below 0x8000 are dropped -- the one place this machine is not the VM.

R16-R19 are device registers, as README.md describes them: they are not in the
register file but in io, which reads and clears them the way
keyboard_push_cpu() and display_fetch() do.
"""

import sys
from pathlib import Path

from logisim import *
from kone_microcode import assemble

OUT = Path(__file__).resolve().parents[1] / "kone.circ"
DEFAULT_PROGRAM = Path(__file__).resolve().parents[2] / "bin" / "display.bin"

ROM_ADDR_BITS = 15              # 0x0000-0x7FFF program, 0x8000-0xFFFF RAM
PITCH = 400                     # chip pitch inside a row

# The microcode's write-enable byte, bit 0 first; each block splits out its own.
WE_BITS = ("RW", "TW", "T2W", "ALW", "MLW", "MHW", "MEMW", "CYW")
SEL_BITS = ("RA0", "RA1", "RA2", "RA3", "RA4", "ASEL", "BSRC0", "BSRC1")


def bits(name, n=8):
    return [f"{name}{k}" for k in range(n)]


def keep(names, *wanted):
    """The named lines of a microcode byte, the rest left unsplit."""
    return [n if n in wanted else None for n in names]


def image(data, addr_bits):
    """Logisim's memory image format, the one a ROM's contents attribute holds."""
    words = list(data) + [0] * ((1 << addr_bits) - len(data))
    out, i = [], 0
    while i < len(words):
        run = 1
        while i + run < len(words) and words[i + run] == words[i]:
            run += 1
        out.append(f"{run}*{words[i]:x}" if run > 3 else " ".join(
            [f"{words[i]:x}"] * run))
        i += run
    return f"addr/data: {addr_bits} 8\n" + "\n".join(out) + "\n"


def wires(c, x, y, bus, names):
    """Splitter tying the wide tunnel `bus` to the one-bit tunnels `names`."""
    n = len(names)
    split = c.add(Splitter(x, y, fanout=n, incoming=n, facing="north",
                           appear="left", spacing=2))
    for k, name in enumerate(names):
        if name is None:
            continue
        ex, ey = split.port(str(k))
        stub(c, (ex, ey), (ex, ey - 40), name, "south")
    stub(c, split.port("in"), (x, y + 40), bus, "north", width=n)
    return split


def ports(c, ins, outs):
    """Pins of a block, each one wired to the tunnel of the same name."""
    for i, (name, width) in enumerate(ins):
        pin = c.add(Pin(100, 100 + 100 * i, name, width=width))
        stub(c, pin.port(), (300, 100 + 100 * i), name, "west", width=width)
    for i, (name, width) in enumerate(outs):
        pin = c.add(Pin(900, 100 + 100 * i, name, width=width, output=True))
        stub(c, pin.port(), (700, 100 + 100 * i), name, "east", width=width)
    return 100 * max(len(ins), len(outs)) + 500


def mux4(c, x, y, tag, sel, srcs, out):
    """Four 74153, two bits each: out[k] = srcs[sel][k]."""
    for j in range(4):
        nets = {"n1E": Ground, "n2E": Ground, "S0": sel[0], "S1": sel[1]}
        for half, k in ((1, 2 * j), (2, 2 * j + 1)):
            for i in range(4):
                nets[f"{half}D{i}"] = srcs[i][k]
            nets[f"{half}Y"] = out[k]
        wire_dip(c, c.add(Ttl74153(x + PITCH * j, y, label=f"{tag}{2 * j}")), nets)


def mux2(c, x, y, tag, sel, a, b, out):
    """74157, four bits each: out[k] = sel ? b[k] : a[k]."""
    for j in range((len(out) + 3) // 4):
        nets = {"SELECT": sel, "nSTROBE": Ground}
        for ch in range(4):
            k = 4 * j + ch
            inside = k < len(out)
            nets[f"{ch + 1}A"] = a[k] if inside else Ground
            nets[f"{ch + 1}B"] = b[k] if inside else Ground
            nets[f"{ch + 1}Y"] = out[k] if inside else None
        wire_dip(c, c.add(Ttl74157(x + PITCH * j, y, label=f"{tag}{4 * j}")), nets)


def latch(c, x, y, tag, d, q, nclken):
    """One 74377, loaded on the CPU clock while nclken is low."""
    nets = {"CLK": "CLK", "nCLKen": nclken}
    for k in range(8):
        nets[f"D{k + 1}"] = d[k]
        nets[f"Q{k + 1}"] = q[k]
    wire_dip(c, c.add(Ttl74377(x, y, label=tag)), nets)


def sequencer(rom, dispatch_a, dispatch_b):
    """Microprogram counter, the control ROMs and the next-address path."""
    c = Circuit("sequencer")
    y = ports(c, [("CLK", 1), ("BUS", 8), ("CY", 1)],
              [("UADDR", 8), ("LIT", 8), ("AOP", 8), ("WE", 8), ("SEL", 8),
               ("RSRC", 2), ("RW", 1)])

    banks = (("LIT", "LIT", None), ("AOP", "AOP", None),
             ("NEXT", "MNEXT", bits("NEXT")), ("ALT", "MALT", bits("ALT")),
             ("WE", "WE", None), ("SEL", "SEL", None),
             ("MISC", "MMISC", ["RSRC0", "RSRC1", "CSEL0", "CSEL1", "CSEL2",
                                "DISPEN", "DISPSEL", None]))
    for i, (tag, bus, names) in enumerate(banks):
        x = 200 + 600 * i
        chip = c.add(Rom(x, y, addr_width=8, data_width=8, label=f"u{tag}",
                         contents=image(rom[i], 8)))
        stub(c, chip.port("addr"), (x - 60, y + 10), "UADDR", "east", width=8)
        stub(c, chip.port("data"), (x + 300, y + 60), bus, "west", width=8)
        if names:
            wires(c, x + 60, y + 300, bus, names)

    for i, (tag, table) in enumerate((("A", dispatch_a), ("B", dispatch_b))):
        x = 4400 + 600 * i
        chip = c.add(Rom(x, y, addr_width=8, data_width=8, label=f"disp{tag}",
                         contents=image(table, 8)))
        stub(c, chip.port("addr"), (x - 60, y + 10), "BUS", "east", width=8)
        stub(c, chip.port("data"), (x + 300, y + 60), f"D{tag}", "west", width=8)
        wires(c, x + 60, y + 300, f"D{tag}", bits(f"D{tag}"))

    y += 1000
    mux2(c, 200, y, "seqb", "COND", bits("NEXT"), bits("ALT"), bits("SEQ"))
    mux2(c, 1000, y, "seqd", "DISPSEL", bits("DA"), bits("DB"), bits("DSP"))
    mux2(c, 1800, y, "seqn", "DISPEN", bits("SEQ"), bits("DSP"), bits("UNEXT"))
    latch(c, 2600, y, "uaddr", bits("UNEXT"), bits("UADDR"), Ground)
    wires(c, 3000, y + 400, "UADDR", bits("UADDR"))
    wires(c, 3400, y + 400, "BUS", bits("BUS"))
    wires(c, 3800, y + 400, "WE", keep(WE_BITS, "RW"))
    wires(c, 4200, y + 400, "RSRC", ["RSRC0", "RSRC1"])

    # Conditions, all read off the main bus: see CSEL in kone_microcode.py.
    wire_dip(c, c.add(Ttl74151(4600, y, label="cond")), {
        "D0": Ground, "D1": "BUSZ", "D2": "NBUSZ", "D3": "BUS0", "D4": "NBUS0",
        "D5": "CY", "D6": "NCY", "D7": "ISM",
        "A": "CSEL0", "B": "CSEL1", "C": "CSEL2",
        "nG": Ground, "Y": "COND", "W": None})
    wire_dip(c, c.add(Ttl7427(5000, y, label="busz")), {
        "A1": "BUS0", "B1": "BUS1", "C1": "BUS2", "Y1": "Z0",
        "A2": "BUS3", "B2": "BUS4", "C2": "BUS5", "Y2": "Z1",
        "A3": "BUS6", "B3": "BUS7", "C3": Ground, "Y3": "Z2"})
    wire_dip(c, c.add(Ttl7411(5400, y, label="busz")), {
        "A1": "Z0", "B1": "Z1", "C1": "Z2", "Y1": "BUSZ",
        "A2": "BUS5", "B2": "NBUS6", "C2": "NBUS7", "Y2": "ISM",
        "A3": Ground, "B3": Ground, "C3": Ground, "Y3": None})
    wire_dip(c, c.add(Ttl7404(5800, y, label="inv")), {
        "A1": "BUSZ", "Y1": "NBUSZ", "A2": "BUS0", "Y2": "NBUS0",
        "A3": "BUS6", "Y3": "NBUS6", "A4": "BUS7", "Y4": "NBUS7",
        "A5": "CY", "Y5": "NCY", "A6": Ground, "Y6": None})
    return c


def datapath():
    """The main bus, the ALU's operand latches and the address mux."""
    c = Circuit("datapath")
    y = ports(c, [("CLK", 1), ("REGO", 8), ("MEMO", 8), ("ALUO", 8), ("ALUC", 1),
                  ("LIT", 8), ("WE", 8), ("SEL", 8), ("RSRC", 2)],
              [("BUS", 8), ("ADDR", 5), ("TQ", 8), ("ALUR", 8), ("CY", 1)])

    for i, (bus, names) in enumerate((
            ("WE", keep(WE_BITS, "TW", "T2W", "ALW", "CYW")),
            ("SEL", list(SEL_BITS)), ("RSRC", ["RSRC0", "RSRC1"]),
            ("LIT", bits("LIT")), ("REGO", bits("REGO")), ("MEMO", bits("MEMO")),
            ("ALUO", bits("ALUO")), ("BUS", bits("BUS")), ("TQ", bits("TQ")),
            ("ALUR", bits("ALUR")), ("ADDR", bits("ADDR", 5)))):
        wires(c, 200 + PITCH * i, y, bus, names)

    y += 600
    # ADDR is the microcode's RA, or the register named by IR1 (the AL latch).
    mux2(c, 200, y, "adr", "ASEL",
         ["RA0", "RA1", "RA2", "RA3", "RA4"], bits("ALQ", 5), bits("ADDR", 5))
    mux4(c, 1000, y, "bus", ("BSRC0", "BSRC1"),
         [bits("REGO"), bits("MEMO"), bits("ALUO"), bits("LIT")], bits("BUS"))
    mux4(c, 2600, y, "alur", ("RSRC0", "RSRC1"),
         [bits("REGO"), bits("LIT"), ["CY"] + [Ground] * 7, bits("T2Q")],
         bits("ALUR"))

    y += 800
    for i, (tag, q, en) in enumerate((("t", "TQ", "nTW"), ("t2", "T2Q", "nT2W"),
                                      ("al", "ALQ", "nALW"))):
        latch(c, 200 + PITCH * i, y, tag, bits("BUS"), bits(q), en)
    latch(c, 1400, y, "cy", ["ALUC"] + [Ground] * 7, ["CY"] + [None] * 7, "nCYW")
    wire_dip(c, c.add(Ttl7404(1800, y, label="inv")), {
        "A1": "TW", "Y1": "nTW", "A2": "T2W", "Y2": "nT2W",
        "A3": "ALW", "Y3": "nALW", "A4": "CYW", "Y4": "nCYW",
        "A5": Ground, "Y5": None, "A6": Ground, "Y6": None})
    return c


def memory(program):
    """MAR, the program ROM below 0x8000 and the RAM above it."""
    c = Circuit("memory")
    y = ports(c, [("CLK", 1), ("BUS", 8), ("WE", 8)],
              [("MEMO", 8), ("MAR", 16)])

    wires(c, 200, y, "WE", keep(WE_BITS, "MLW", "MHW", "MEMW"))
    wires(c, 600, y, "BUS", bits("BUS"))
    wires(c, 1000, y, "MEMO", bits("MEMO"))
    wires(c, 1400, y, "MAR", bits("MARL") + bits("MARH"))

    y += 600
    latch(c, 200, y, "marl", bits("BUS"), bits("MARL"), "nMLW")
    latch(c, 600, y, "marh", bits("BUS"), bits("MARH"), "nMHW")
    wire_dip(c, c.add(Ttl7404(1000, y, label="inv")), {
        "A1": "MLW", "Y1": "nMLW", "A2": "MHW", "Y2": "nMHW",
        "A3": Ground, "Y3": None, "A4": Ground, "Y4": None,
        "A5": Ground, "Y5": None, "A6": Ground, "Y6": None})
    # A write below 0x8000 lands in the ROM half and is dropped.
    wire_dip(c, c.add(Ttl7408(1400, y, label="ramwe")), {
        "A1": "MEMW", "B1": "MA15", "Y1": "RAMWE",
        "A2": Ground, "B2": Ground, "Y2": None,
        "A3": Ground, "B3": Ground, "Y3": None,
        "A4": Ground, "B4": Ground, "Y4": None})

    y += 600
    split = c.add(Splitter(200, y, fanout=2, incoming=16, spacing=2,
                           facing="north", appear="left", bits=[0] * 15 + [1]))
    stub(c, split.port("in"), (200, y + 40), "MAR", "north", width=16)
    stub(c, split.port("0"), (split.port("0")[0], y - 60), "MADDR", "south",
         width=15)
    stub(c, split.port("1"), (split.port("1")[0], y - 100), "MA15", "south")

    rom = c.add(Rom(800, y, addr_width=ROM_ADDR_BITS, data_width=8,
                    label="prog", contents=image(program, ROM_ADDR_BITS)))
    stub(c, rom.port("addr"), (740, y + 10), "MADDR", "east", width=15)
    stub(c, rom.port("data"), (1100, y + 60), "ROMO", "west", width=8)

    ram = c.add(Ram(1600, y, addr_width=ROM_ADDR_BITS, data_width=8,
                    asyncread=True, label="dram"))
    for port, net, width in (("addr", "MADDR", 15), ("din", "BUS", 8),
                             ("we", "RAMWE", 1), ("clk", "CLK", 1)):
        px, py = ram.port(port)
        stub(c, (px, py), (px - 60, py), net, "east", width=width)
    ox, oy = ram.port("oe")
    c.route((ox, oy), (ox - 60, oy))
    c.add(Power(ox - 60, oy, facing="west"))
    stub(c, ram.port("dout"), (1900, y + 90), "RAMO", "west", width=8)

    wires(c, 2300, y + 300, "ROMO", bits("ROMO"))
    wires(c, 2700, y + 300, "RAMO", bits("RAMO"))
    mux2(c, 3100, y + 700, "mem", "MA15", bits("ROMO"), bits("RAMO"),
         bits("MEMO"))
    return c


def io():
    """R16-R19 and the handshakes around them; the TTY and keyboard sit above."""
    c = Circuit("io")
    y = ports(c, [("CLK", 1), ("BUS", 8), ("RFO", 8), ("ADDR", 5), ("RW", 1),
                  ("KBAV", 1), ("KBD", 7)],
              [("REGO", 8), ("TTYD", 7), ("DISPNZ", 1), ("KBSET", 1)])

    for i, (bus, names) in enumerate((("BUS", bits("BUS")), ("RFO", bits("RFO")),
                                      ("REGO", bits("REGO")),
                                      ("ADDR", bits("ADDR", 5)))):
        wires(c, 200 + PITCH * i, y, bus, names)

    y += 600
    wire_dip(c, c.add(Ttl74138(200, y, label="devwr")), {
        "A": "ADDR0", "B": "ADDR1", "C": Ground, "G1": "DEVWR",
        "nG2A": Ground, "nG2B": Ground,
        "nY0": "nW16", "nY1": "nW17", "nY2": "nW18", "nY3": "nW19",
        "nY4": None, "nY5": None, "nY6": None, "nY7": None})
    wire_dip(c, c.add(Ttl7411(600, y, label="devsel")), {
        "A1": "ADDR4", "B1": "NADDR3", "C1": "NADDR2", "Y1": "DEVSEL",
        "A2": "R18Z0", "B2": "R18Z1", "C2": "R18Z2", "Y2": "R18Z",
        "A3": Ground, "B3": Ground, "C3": Ground, "Y3": None})
    wire_dip(c, c.add(Ttl7427(1000, y, label="r18z")), {
        "A1": "R18Q0", "B1": "R18Q1", "C1": "R18Q2", "Y1": "R18Z0",
        "A2": "R18Q3", "B2": "R18Q4", "C2": "R18Q5", "Y2": "R18Z1",
        "A3": "R18Q6", "B3": "R18Q7", "C3": Ground, "Y3": "R18Z2"})
    wire_dip(c, c.add(Ttl7404(1400, y, label="inv")), {
        "A1": "ADDR2", "Y1": "NADDR2", "A2": "ADDR3", "Y2": "NADDR3",
        "A3": "R16Q0", "Y3": "NR16", "A4": "R18Z", "Y4": "DISPNZ",
        "A5": "nW16", "Y5": "W16", "A6": "nW17", "Y6": "W17"})
    wire_dip(c, c.add(Ttl7408(1800, y, label="and1")), {
        "A1": "RW", "B1": "DEVSEL", "Y1": "DEVWR",
        "A2": "KBAV", "B2": "NR16", "Y2": "KBSET",
        "A3": "nW16", "B3": "NKBSET", "Y3": "nCLK16",
        "A4": "nW17", "B4": "NKBSET", "Y4": "nCLK17"})
    wire_dip(c, c.add(Ttl7408(2200, y, label="and2")), {
        "A1": "nW18", "B1": "R18Z", "Y1": "nCLK18",
        "A2": Ground, "B2": Ground, "Y2": None,
        "A3": Ground, "B3": Ground, "Y3": None,
        "A4": Ground, "B4": Ground, "Y4": None})
    wire_dip(c, c.add(Ttl7404(2600, y, label="inv2")), {
        "A1": "KBSET", "Y1": "NKBSET", "A2": Ground, "Y2": None,
        "A3": Ground, "Y3": None, "A4": Ground, "Y4": None,
        "A5": Ground, "Y5": None, "A6": Ground, "Y6": None})
    # display_fetch(): the char goes out and the set register is cleared again.
    for j in range(2):
        wire_dip(c, c.add(Ttl7408(3000 + PITCH * j, y, label=f"r18d{j}")),
                 {f"{p}{i + 1}": v for i in range(4)
                  for p, v in (("A", f"BUS{4 * j + i}"), ("B", "R18Z"),
                               ("Y", f"R18D{4 * j + i}"))})

    # keyboard_push_cpu(): a waiting char lands in R17 and sets R16.
    y += 800
    mux2(c, 200, y, "r16d", "W16", ["KBONE"] + [Ground] * 7, bits("BUS"),
         bits("R16D"))
    mux2(c, 1000, y, "r17d", "W17", bits("KBD", 7) + [Ground], bits("BUS"),
         bits("R17D"))
    for i, (tag, d, q, en) in enumerate((
            ("r16", bits("R16D"), bits("R16Q"), "nCLK16"),
            ("r17", bits("R17D"), bits("R17Q"), "nCLK17"),
            ("r18", bits("R18D"), bits("R18Q"), "nCLK18"),
            ("r19", bits("BUS"), bits("R19Q"), "nW19"))):
        latch(c, 1800 + PITCH * i, y, tag, d, q, en)
    one = c.add(Power(3400, y, facing="north"))
    stub(c, one.port(), (3400, y + 40), "KBONE", "north")

    y += 800
    mux4(c, 200, y, "dev", ("ADDR0", "ADDR1"),
         [bits("R16Q"), bits("R17Q"), bits("R18Q"), bits("R19Q")], bits("DEVO"))
    mux2(c, 1800, y, "rego", "DEVSEL", bits("RFO"), bits("DEVO"), bits("REGO"))

    # R19 drives the TTY's seven data bits; R16's set bit gates the keyboard.
    y += 600
    split = c.add(Splitter(200, y, fanout=1, incoming=8, spacing=2,
                           facing="north", appear="left", bits=[0] * 7 + [None]))
    stub(c, split.port("in"), (200, y + 40), "R19Q", "north", width=8)
    stub(c, split.port("0"), (split.port("0")[0], y - 60), "TTYD", "south",
         width=7)
    wires(c, 600, y, "R19Q", bits("R19Q"))
    wires(c, 1000, y, "KBD", bits("KBD", 7))
    return c


def place(c, block, x, y, rename=None):
    """A block, with every port stubbed to the tunnel of the same name."""
    inst = c.add(block.instance(x, y))
    width = {p.get("label"): int(p.get("width", 1)) for p in block.pins()}
    outputs = {p.get("label") for p in block.output_pins()}
    for i, (name, _, _) in enumerate(inst.port_spec()):
        net = (rename or {}).get(name, name)
        if net is None:
            continue
        px, py = inst.port(name)
        out = name in outputs
        to = (px + (80 + 30 * i) * (1 if out else -1), py)
        stub(c, (px, py), to, net, "west" if out else "east", width=width[name])
    return inst


def kone(blocks):
    """The block diagram: six blocks, the two devices, a clock and three probes."""
    # Logisim opens a file at 1 Hz; at that rate a program prints nothing you
    # would notice, since a kone instruction is some 20 microsteps.
    c = Circuit("kone", simulation_frequency=4096)
    clk = c.add(Clock(200, 100, label="clk"))
    stub(c, clk.port(), (300, 100), "CLK", "west")
    for i, (name, width) in enumerate((("UADDR", 8), ("BUS", 8), ("MAR", 16))):
        pin = c.add(Pin(1200 + 500 * i, 100, name, width=width, output=True))
        stub(c, pin.port(), (1100 + 500 * i, 100), name, "east", width=width)

    # The 40x24 display and the keyboard are here rather than inside io, so
    # what a program prints is on screen without opening a subcircuit.
    tty = c.add(Tty(2800, 500, rows=24, cols=40))
    for port, net, width in (("data", "TTYD", 7), ("clk", "CLK", 1),
                             ("we", "DISPNZ", 1)):
        px, py = tty.port(port)
        stub(c, (px, py), (px - 100, py), net, "east", width=width)
    cx, cy = tty.port("clr")
    c.route((cx, cy), (cx, cy + 60))
    c.add(Ground(cx, cy + 60))

    kbd = c.add(Keyboard(2800, 700))
    for port, net in (("clk", "CLK"), ("re", "KBSET")):
        px, py = kbd.port(port)
        stub(c, (px, py), (px - 100, py), net, "east")
    cx, cy = kbd.port("clr")
    c.route((cx, cy), (cx, cy + 60))
    c.add(Ground(cx, cy + 60))
    stub(c, kbd.port("avail"), (kbd.port("avail")[0], 800), "KBAV", "north")
    stub(c, kbd.port("data"), (3400, 710), "KBD", "west", width=7)

    regfile, alu, seq, data, mem, dev = blocks
    rf = place(c, regfile, 400, 1100,
               rename={"BUS_IN": "BUS", "WR": "RW", "BUS_OUT": "RFO", "RD": None})
    px, py = rf.port("RD")
    c.route((px, py), (px - 80, py))
    c.add(Power(px - 80, py, facing="west"))
    place(c, alu, 400, 1900,
          rename={"L": "TQ", "R": "ALUR", "OP": "AOP", "OUT": "ALUO",
                  "C": "ALUC", "Z": None, "CWR": None})
    place(c, seq, 1800, 1100)
    place(c, data, 1800, 2100)
    place(c, mem, 3800, 1100)
    place(c, dev, 3800, 1900)
    return c


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PROGRAM
    if not path.exists():
        sys.exit(f"no program image at {path} -- run `make examples` first")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_regfile import regfile
    from build_alu import alu

    rom, dispatch_a, dispatch_b, _, _ = assemble()
    blocks = (regfile(), alu(), sequencer(rom, dispatch_a, dispatch_b),
              datapath(), memory(path.read_bytes()), io())
    project = Project(main="kone")
    project.add(kone(blocks))
    for block in blocks:
        project.add(block)
    print(project.save(OUT), f"({path.name}, {path.stat().st_size} bytes)")
