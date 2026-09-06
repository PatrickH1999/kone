#!/usr/bin/env python3
"""kone's ALU, as one circuit to instantiate elsewhere.

The nine ALU opcodes of the ISA and nothing else: NOT/BSL/BSR/BRL/BRR on L, and
ORR/AND/XOR/ADD on L and R. OP is the opcode byte itself -- the ALU picks the
operation out of the same bits the decoder reads, so no separate encoding
exists. Every other opcode leaves OUT undefined; the CPU does not latch A then.

L is the ALU's left input (register I, the copy of the accumulator), R the right
one (the selected register), exactly as README.md describes them.

Shifts and rotations are wiring, not chips: they are L, renumbered into the
mux inputs.
"""

from pathlib import Path

from logisim import *

OUT = Path(__file__).resolve().parents[1] / "alu.circ"

STRIP_Y = 100                   # the pin strip, above everything else
ROW = (700, 1500, 2300)         # operators, unary muxes, result muxes and flags
COL = 400                       # chip pitch within a row
X0 = 200

# Opcode bits the ALU uses, from README.md "Instruction set": bit 7 tells the
# two-operand ops (1CCC 0000) from the one-operand ops (0000 CCCC), bits 5-4
# pick among ORR/AND/XOR/ADD, bits 2-0 among the one-operand ops.
SEL_BINARY, SEL_OP, SEL_UNARY = "P7", ("P4", "P5"), ("P0", "P1", "P2")


def gate_bank(c, cls, x, y, label, a, b, out, bits):
    """Four two-input gates, one per bit: out<k> = a<k> op b<k>."""
    nets = {}
    for g, k in enumerate(bits):
        nets[f"A{g + 1}"] = f"{a}{k}"
        nets[f"B{g + 1}"] = f"{b}{k}"
        nets[f"Y{g + 1}"] = f"{out}{k}"
    return wire_dip(c, c.add(cls(x, y, label=label)), nets)


def operators(c, y):
    """Adder, OR, AND, XOR and NOT: four bits per chip, low nibble then high."""
    for half, bits in enumerate((range(4), range(4, 8))):
        x = X0 + COL * half
        nets = {"CIN": "CMID" if half else Ground, "C4": "COUT" if half else "CMID"}
        for g, k in enumerate(bits):
            nets[f"A{g + 1}"] = f"L{k}"
            nets[f"B{g + 1}"] = f"R{k}"
            nets[f"S{g + 1}"] = f"SUM{k}"
        wire_dip(c, c.add(Ttl74283(x, y, label=f"add{half}")), nets)

        for i, (cls, op) in enumerate(((Ttl7432, "ORR"), (Ttl7408, "AND"),
                                       (Ttl7486, "XOR"))):
            gate_bank(c, cls, X0 + COL * (2 + 2 * i + half), y,
                      f"{op.lower()}{half}", "L", "R", op, bits)

        # Two of the six inverters per chip are spare; TTL inputs cannot float.
        nets = {}
        for g in range(6):
            nets[f"A{g + 1}"] = f"L{bits[g]}" if g < 4 else Ground
            nets[f"Y{g + 1}"] = f"NOT{bits[g]}" if g < 4 else None
        wire_dip(c, c.add(Ttl7404(X0 + COL * (8 + half), y, label=f"not{half}")), nets)


def unary_mux(c, k, x, y):
    """Bit k of the one-operand result, selected by opcode bits 2-0."""
    lo, hi = f"L{(k - 1) % 8}", f"L{(k + 1) % 8}"
    wire_dip(c, c.add(Ttl74151(x, y, label=f"un{k}")), {
        "D0": f"L{k}",                          # 0x00 NOP: A is unchanged
        "D1": f"NOT{k}",                        # 0x01 NOT
        "D2": Ground, "D3": Ground,             # 0x02, 0x03: no such opcode
        "D4": lo if k else Ground,              # 0x04 BSL
        "D5": hi if k < 7 else Ground,          # 0x05 BSR
        "D6": lo,                               # 0x06 BRL
        "D7": hi,                               # 0x07 BRR
        "A": SEL_UNARY[0], "B": SEL_UNARY[1], "C": SEL_UNARY[2],
        "nG": Ground, "Y": f"UN{k}", "W": None,
    })


def binary_mux(c, pair, x, y):
    """Two bits of the two-operand result, selected by opcode bits 5-4."""
    lo, hi = 2 * pair, 2 * pair + 1
    nets = {"S0": SEL_OP[0], "S1": SEL_OP[1], "n1E": Ground, "n2E": Ground}
    for half, k in ((1, lo), (2, hi)):
        nets[f"{half}D0"] = f"ORR{k}"           # 0xC0 ORR
        nets[f"{half}D1"] = f"AND{k}"           # 0xD0 AND
        nets[f"{half}D2"] = f"XOR{k}"           # 0xE0 XOR
        nets[f"{half}D3"] = f"SUM{k}"           # 0xF0 ADD
        nets[f"{half}Y"] = f"BIN{k}"
    wire_dip(c, c.add(Ttl74153(x, y, label=f"bin{lo}-{hi}")), nets)


def result_mux(c, half, x, y):
    """Four bits of OUT: the two-operand result when opcode bit 7 is set."""
    nets = {"SELECT": SEL_BINARY, "nSTROBE": Ground}
    for g in range(4):
        k = 4 * half + g
        nets[f"{g + 1}A"] = f"UN{k}"
        nets[f"{g + 1}B"] = f"BIN{k}"
        nets[f"{g + 1}Y"] = f"OUT{k}"
    wire_dip(c, c.add(Ttl74157(x, y, label=f"out{4 * half}-{4 * half + 3}")), nets)


def flags(c, x, y):
    """Z = OUT is zero; C = the adder's carry, but only while ADD is selected."""
    wire_dip(c, c.add(Ttl7427(x, y, label="zero")), {
        "A1": "OUT0", "B1": "OUT1", "C1": "OUT2", "Y1": "NZ0",
        "A2": "OUT3", "B2": "OUT4", "C2": "OUT5", "Y2": "NZ1",
        "A3": "OUT6", "B3": "OUT7", "C3": Ground, "Y3": "NZ2",
    })
    wire_dip(c, c.add(Ttl7411(x + COL, y, label="zero")), {
        "A1": "NZ0", "B1": "NZ1", "C1": "NZ2", "Y1": "Z",
        "A2": Ground, "B2": Ground, "C2": Ground, "Y2": None,
        "A3": Ground, "B3": Ground, "C3": Ground, "Y3": None,
    })
    # CWR is what keeps the other eight operations from touching the flag:
    # only ADD (1111 0000) writes carry.
    wire_dip(c, c.add(Ttl7421(x + 2 * COL, y, label="carry")), {
        "A1": "P7", "B1": "P6", "C1": "P5", "D1": "P4", "Y1": "CWR",
        "A2": "COUT", "B2": "CWR", "C2": Power, "D2": Power, "Y2": "C",
    })


def io(c):
    """L, R and OP in, OUT and the flags out; all of it on tunnels."""
    for i, (name, prefix) in enumerate((("L", "L"), ("R", "R"), ("OP", "P"))):
        x = 100 + 600 * i
        pin = c.add(Pin(x, STRIP_Y, name, width=8))
        split = c.add(Splitter(x + 100, STRIP_Y, fanout=8, incoming=8,
                               appear="right", spacing=2))
        c.connect(pin, None, split, "in")
        for k in range(8):
            stub(c, split.port(str(k)), (x + 300, STRIP_Y + 10 + 20 * k),
                 f"{prefix}{k}", "west")

    split = c.add(Splitter(2100, STRIP_Y + 200, fanout=8, incoming=8,
                           facing="north", appear="left", spacing=2))
    for k in range(8):
        ex, ey = split.port(str(k))
        stub(c, (ex, ey), (ex, ey - 40), f"OUT{k}", "south")
    tx, ty = split.port("in")
    c.route((tx, ty), (tx, ty + 40))
    c.add(Pin(tx, ty + 40, "OUT", width=8, output=True, facing="north"))

    for i, name in enumerate(("C", "Z", "CWR")):
        pin = c.add(Pin(2700, STRIP_Y + 100 * i, name, output=True))
        stub(c, pin.port(), (2600, STRIP_Y + 100 * i), name, "east")


def alu():
    c = Circuit("alu")
    io(c)
    operators(c, ROW[0])
    for k in range(8):
        unary_mux(c, k, X0 + COL * k, ROW[1])
    for pair in range(4):
        binary_mux(c, pair, X0 + COL * pair, ROW[2])
    for half in range(2):
        result_mux(c, half, X0 + COL * (4 + half), ROW[2])
    flags(c, X0 + COL * 6, ROW[2])
    return c


if __name__ == "__main__":
    project = Project(main="alu")
    project.add(alu())
    print(project.save(OUT))
