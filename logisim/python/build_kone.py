#!/usr/bin/env python3
"""The whole kone CPU: regfile.circ and alu.circ under a microcoded control unit.

    python3 logisim/python/build_kone.py [bin/display.bin]

Everything the C VM keeps in CPU.R lives in the register file, so the datapath
is small: one main bus, a few 74377 latches around the ALU and the memory, and
a control unit that is seven 256-byte ROMs addressed by a microprogram counter
(see kone_microcode.py). Two more ROMs turn an opcode into a microcode address,
which is cpu_decode_exec()'s switch.

Memory is split at 0x8000: the program sits in ROM below, RAM covers the half
above, which is where klib scratch, program data and the stack live. Writes
below 0x8000 are dropped -- the one place this machine is not the VM.

R16-R19 are device registers, as README.md describes them: they are not in the
register file but in the keyboard and display blocks, which read and clear them
the way keyboard_push_cpu() and display_fetch() do.
"""

import sys
from pathlib import Path

from logisim import *
from kone_microcode import assemble

OUT = Path(__file__).resolve().parents[1] / "kone.circ"
DEFAULT_PROGRAM = Path(__file__).resolve().parents[2] / "bin" / "display.bin"

ROM_ADDR_BITS = 15              # 0x0000-0x7FFF program, 0x8000-0xFFFF RAM
PITCH = 400                     # chip pitch inside a row
BIT = tuple(range(8))


def image(data, addr_bits):
    """Logisim's memory image format, the one a ROM's contents attribute holds."""
    words = list(data) + [0] * ((1 << addr_bits) - len(data))
    out, run, i = [], 0, 0
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
    for k in BIT:
        nets[f"D{k + 1}"] = d[k]
        nets[f"Q{k + 1}"] = q[k]
    wire_dip(c, c.add(Ttl74377(x, y, label=tag)), nets)


def bits(name, n=8):
    return [f"{name}{k}" for k in range(n)]


def control(c, y, rom, dispatch_a, dispatch_b):
    """Microprogram counter, the control ROMs and the next-address path."""
    banks = (("LIT", "MLIT", bits("LIT")), ("AOP", "AOP", None),
             ("NEXT", "MNEXT", bits("NEXT")), ("ALT", "MALT", bits("ALT")),
             ("WE", "MWE", ["RW", "TW", "T2W", "ALW", "MLW", "MHW", "MEMW", "CYW"]),
             ("RA", "MRA", ["RA0", "RA1", "RA2", "RA3", "RA4", "ASEL",
                            "BSRC0", "BSRC1"]),
             ("MISC", "MMISC", ["RSRC0", "RSRC1", "CSEL0", "CSEL1", "CSEL2",
                                "DISPEN", "DISPSEL", None]))
    for i, (tag, bus, names) in enumerate(banks):
        x = 200 + 600 * i
        chip = c.add(Rom(x, y, addr_width=8, data_width=8, label=f"u{tag}",
                         contents=image(rom[i], 8)))
        stub(c, chip.port("addr"), (x - 60, y + 10), "UA", "east", width=8)
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


def sequencer(c, y):
    """next = dispatch, or the branch target while the condition holds."""
    mux2(c, 200, y, "seqb", "COND", bits("NEXT"), bits("ALT"), bits("SEQ"))
    mux2(c, 1000, y, "seqd", "DISPSEL", bits("DA"), bits("DB"), bits("DSP"))
    mux2(c, 1800, y, "seqn", "DISPEN", bits("SEQ"), bits("DSP"), bits("UNEXT"))
    latch(c, 2600, y, "uaddr", bits("UNEXT"), bits("UA"), Ground)
    wires(c, 3000, y + 400, "UA", bits("UA"))

    # Conditions, all read off the main bus: see CSEL in kone_microcode.py.
    wire_dip(c, c.add(Ttl74151(3400, y, label="cond")), {
        "D0": Ground, "D1": "BUSZ", "D2": "NBUSZ", "D3": "BUS0", "D4": "NBUS0",
        "D5": "CY", "D6": "NCY", "D7": "ISM",
        "A": "CSEL0", "B": "CSEL1", "C": "CSEL2",
        "nG": Ground, "Y": "COND", "W": None})
    wire_dip(c, c.add(Ttl7427(3800, y, label="busz")), {
        "A1": "BUS0", "B1": "BUS1", "C1": "BUS2", "Y1": "Z0",
        "A2": "BUS3", "B2": "BUS4", "C2": "BUS5", "Y2": "Z1",
        "A3": "BUS6", "B3": "BUS7", "C3": Ground, "Y3": "Z2"})
    wire_dip(c, c.add(Ttl7411(4200, y, label="busz")), {
        "A1": "Z0", "B1": "Z1", "C1": "Z2", "Y1": "BUSZ",
        "A2": "BUS5", "B2": "NBUS6", "C2": "NBUS7", "Y2": "ISM",
        "A3": Ground, "B3": Ground, "C3": Ground, "Y3": None})
    wire_dip(c, c.add(Ttl7404(4600, y, label="inv1")), {
        "A1": "BUSZ", "Y1": "NBUSZ", "A2": "BUS0", "Y2": "NBUS0",
        "A3": "BUS6", "Y3": "NBUS6", "A4": "BUS7", "Y4": "NBUS7",
        "A5": "CY", "Y5": "NCY", "A6": "KBSET", "Y6": "NKBSET"})
    wire_dip(c, c.add(Ttl7404(5000, y, label="inv2")), {
        "A1": "TW", "Y1": "nTW", "A2": "T2W", "Y2": "nT2W",
        "A3": "ALW", "Y3": "nALW", "A4": "MLW", "Y4": "nMLW",
        "A5": "MHW", "Y5": "nMHW", "A6": "CYW", "Y6": "nCYW"})


def datapath(c, y, regfile, alu):
    """Register file, ALU, the latches around them and the two source muxes."""
    rf = c.add(regfile.instance(200, y))
    for port, net, width in (("BUS_IN", "BUS", 8), ("ADDR", "ADDR", 5),
                             ("RD", None, 1), ("WR", "RW", 1), ("CLK", "CLK", 1)):
        px, py = rf.port(port)
        if net is None:
            c.route((px, py), (px - 60, py))
            c.add(Power(px - 60, py, facing="west"))
        else:
            stub(c, (px, py), (px - 60, py), net, "east", width=width)
    stub(c, rf.port("BUS_OUT"), (rf.port("BUS_OUT")[0] + 60, rf.port("BUS_OUT")[1]),
         "RFO", "west", width=8)
    wires(c, 600, y + 200, "RFO", bits("RFO"))
    wires(c, 1000, y + 200, "ADDR", ["ADDR0", "ADDR1", "ADDR2", "ADDR3", "ADDR4"])

    au = c.add(alu.instance(200, y + 500))
    for port, net in (("L", "TQ"), ("R", "ALUR"), ("OP", "AOP")):
        px, py = au.port(port)
        stub(c, (px, py), (px - 60, py), net, "east", width=8)
    for port, net, width in (("OUT", "ALUO", 8), ("C", "ALUC", 1)):
        px, py = au.port(port)
        stub(c, (px, py), (px + 60, py), net, "west", width=width)
    wires(c, 600, y + 700, "ALUO", bits("ALUO"))
    wires(c, 1000, y + 700, "TQ", bits("TQ"))
    wires(c, 1400, y + 700, "ALUR", bits("ALUR"))

    # ADDR is the microcode's RA, or the register named by IR1 (the AL latch).
    mux2(c, 1800, y, "adr", "ASEL",
         ["RA0", "RA1", "RA2", "RA3", "RA4"], bits("ALQ", 5), bits("ADDR", 5))
    mux4(c, 2600, y, "bus", ("BSRC0", "BSRC1"),
         [bits("REGO"), bits("MEMO"), bits("ALUO"), bits("LIT")], bits("BUS"))
    mux4(c, 4200, y, "alur", ("RSRC0", "RSRC1"),
         [bits("REGO"), bits("LIT"), ["CY"] + [Ground] * 7, bits("T2Q")],
         bits("ALUR"))
    wires(c, 5800, y + 200, "BUS", bits("BUS"))

    for i, (tag, q, en) in enumerate((("t", "TQ", "nTW"), ("t2", "T2Q", "nT2W"),
                                      ("marl", "MARL", "nMLW"),
                                      ("marh", "MARH", "nMHW"),
                                      ("al", "ALQ", "nALW"))):
        latch(c, 200 + PITCH * i, y + 1100, tag, bits("BUS"), bits(q), en)
    latch(c, 2200, y + 1100, "cy", ["ALUC"] + [Ground] * 7,
          ["CY"] + [None] * 7, "nCYW")


def memory(c, y, program):
    """Program ROM below 0x8000, RAM above it, one address latch pair."""
    wires(c, 700, y, "MAR", bits("MARL") + bits("MARH"))
    split = c.add(Splitter(1100, y, fanout=2, incoming=16, spacing=2,
                           facing="north", appear="left", bits=[0] * 15 + [1]))
    stub(c, split.port("in"), (1100, y + 40), "MAR", "north", width=16)
    stub(c, split.port("0"), (split.port("0")[0], y - 60), "MADDR", "south", width=15)
    stub(c, split.port("1"), (split.port("1")[0], y - 100), "MA15", "south")

    rom = c.add(Rom(1400, y, addr_width=ROM_ADDR_BITS, data_width=8,
                    label="prog", contents=image(program, ROM_ADDR_BITS)))
    stub(c, rom.port("addr"), (1340, y + 10), "MADDR", "east", width=15)
    stub(c, rom.port("data"), (1700, y + 60), "ROMO", "west", width=8)

    ram = c.add(Ram(2200, y, addr_width=ROM_ADDR_BITS, data_width=8,
                    asyncread=True, label="dram"))
    for port, net, width in (("addr", "MADDR", 15), ("din", "BUS", 8),
                             ("we", "RAMWE", 1), ("clk", "CLK", 1)):
        px, py = ram.port(port)
        stub(c, (px, py), (px - 60, py), net, "east", width=width)
    ox, oy = ram.port("oe")
    c.route((ox, oy), (ox - 60, oy))
    c.add(Power(ox - 60, oy, facing="west"))
    stub(c, ram.port("dout"), (2500, y + 90), "RAMO", "west", width=8)

    wires(c, 2900, y + 300, "ROMO", bits("ROMO"))
    wires(c, 3300, y + 300, "RAMO", bits("RAMO"))
    mux2(c, 3700, y + 700, "mem", "MA15", bits("ROMO"), bits("RAMO"), bits("MEMO"))


def devices(c, y):
    """R16-R19 and the two device blocks that own them."""
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
    wire_dip(c, c.add(Ttl7404(1400, y, label="inv3")), {
        "A1": "ADDR2", "Y1": "NADDR2", "A2": "ADDR3", "Y2": "NADDR3",
        "A3": "R16Q0", "Y3": "NR16", "A4": "R18Z", "Y4": "DISPNZ",
        "A5": "nW16", "Y5": "W16", "A6": "nW17", "Y6": "W17"})
    wire_dip(c, c.add(Ttl7408(1800, y, label="and1")), {
        "A1": "MEMW", "B1": "MA15", "Y1": "RAMWE",
        "A2": "RW", "B2": "DEVSEL", "Y2": "DEVWR",
        "A3": "KBAV", "B3": "NR16", "Y3": "KBSET",
        "A4": "nW16", "B4": "NKBSET", "Y4": "nCLK16"})
    wire_dip(c, c.add(Ttl7408(2200, y, label="and2")), {
        "A1": "nW17", "B1": "NKBSET", "Y1": "nCLK17",
        "A2": "nW18", "B2": "R18Z", "Y2": "nCLK18",
        "A3": Ground, "B3": Ground, "Y3": None,
        "A4": Ground, "B4": Ground, "Y4": None})
    # display_fetch(): the char goes out and the set register is cleared again.
    for j in range(2):
        wire_dip(c, c.add(Ttl7408(2600 + PITCH * j, y, label=f"r18d{j}")),
                 {f"{p}{i + 1}": v for i in range(4)
                  for p, v in (("A", f"BUS{4 * j + i}"), ("B", "R18Z"),
                               ("Y", f"R18D{4 * j + i}"))})

    # keyboard_push_cpu(): a waiting char lands in R17 and sets R16.
    mux2(c, 200, y + 800, "r16d", "W16",
         ["KBONE"] + [Ground] * 7, bits("BUS"), bits("R16D"))
    mux2(c, 1000, y + 800, "r17d", "W17",
         bits("KBD", 7) + [Ground], bits("BUS"), bits("R17D"))
    for i, (tag, d, q, en) in enumerate((
            ("r16", bits("R16D"), bits("R16Q"), "nCLK16"),
            ("r17", bits("R17D"), bits("R17Q"), "nCLK17"),
            ("r18", bits("R18D"), bits("R18Q"), "nCLK18"),
            ("r19", bits("BUS"), bits("R19Q"), "nW19"))):
        latch(c, 1800 + PITCH * i, y + 800, tag, d, q, en)
    mux4(c, 200, y + 1600, "dev", ("ADDR0", "ADDR1"),
         [bits("R16Q"), bits("R17Q"), bits("R18Q"), bits("R19Q")], bits("DEVO"))
    mux2(c, 1800, y + 1600, "rego", "DEVSEL", bits("RFO"), bits("DEVO"),
         bits("REGO"))

    one = c.add(Power(3400, y + 800, facing="north"))
    stub(c, one.port(), (3400, y + 840), "KBONE", "north")

    tty = c.add(Tty(3800, y + 1000, rows=24, cols=40))
    for port, net, width in (("data", "TTYD", 7), ("clk", "CLK", 1),
                             ("we", "DISPNZ", 1)):
        px, py = tty.port(port)
        stub(c, (px, py), (px - 100, py), net, "east", width=width)
    cx, cy = tty.port("clr")
    c.route((cx, cy), (cx, cy + 60))
    c.add(Ground(cx, cy + 60))
    split = c.add(Splitter(4600, y + 1000, fanout=1, incoming=8, spacing=2,
                           facing="north", appear="left", bits=[0] * 7 + [None]))
    stub(c, split.port("in"), (4600, y + 1040), "R19Q", "north", width=8)
    stub(c, split.port("0"), (split.port("0")[0], y + 940), "TTYD", "south", width=7)
    wires(c, 5000, y + 1400, "R19Q", bits("R19Q"))

    kbd = c.add(Keyboard(3800, y + 1800))
    for port, net in (("clk", "CLK"), ("re", "KBSET")):
        px, py = kbd.port(port)
        stub(c, (px, py), (px - 100, py), net, "east")
    cx, cy = kbd.port("clr")
    c.route((cx, cy), (cx, cy + 60))
    c.add(Ground(cx, cy + 60))
    stub(c, kbd.port("avail"), (kbd.port("avail")[0], y + 1900), "KBAV", "north")
    stub(c, kbd.port("data"), (4400, y + 1810), "KBDQ", "west", width=7)
    wires(c, 4800, y + 2100, "KBDQ", bits("KBD", 7))


def probes(c):
    """A clock, and the three nets worth watching from outside."""
    clk = c.add(Clock(200, 100, label="clk"))
    stub(c, clk.port(), (300, 100), "CLK", "west")
    for i, (name, net, width) in enumerate((("UADDR", "UA", 8), ("BUS", "BUS", 8),
                                            ("MAR", "MAR", 16))):
        pin = c.add(Pin(1000 + 400 * i, 100, name, width=width, output=True))
        stub(c, pin.port(), (900 + 400 * i, 100), net, "east", width=width)


def kone(regfile, alu, program):
    rom, dispatch_a, dispatch_b, _, _ = assemble()
    c = Circuit("kone")
    probes(c)
    control(c, 600, rom, dispatch_a, dispatch_b)
    sequencer(c, 1600)
    datapath(c, 2600, regfile, alu)
    memory(c, 4600, program)
    devices(c, 5800)
    return c


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PROGRAM
    if not path.exists():
        sys.exit(f"no program image at {path} -- run `make examples` first")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_regfile import regfile
    from build_alu import alu

    rf, al = regfile(), alu()
    project = Project(main="kone")
    project.add(kone(rf, al, path.read_bytes()))
    project.add(rf)
    project.add(al)
    print(project.save(OUT), f"({path.name}, {path.stat().st_size} bytes)")
