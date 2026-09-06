#!/usr/bin/env python3
"""The microprogram kone.circ runs, one microstep per clock.

Every architectural register lives in the register file, at the index
cpu_init() gives it, so a microstep is a move between register file, memory,
ALU and the latches around them. The C VM is the reference: FETCH is
cpu_fetch(), DISPATCH is cpu_decode_exec()'s switch, and each block below is
one alu_*().

A step reads at most one register and writes at most one -- the register file
has a single address port -- so a register-to-register move takes two steps:
the ALU passes L through on opcode 0x00, so `T <- src`, then `dst <- alu(T)`.
"""

SPL, SPH, I, A, F, IR0, IR1, IR2, PCL, PCH = 22, 23, 24, 25, 26, 27, 28, 29, 30, 31

BSRC = {"REG": 0, "MEM": 1, "ALU": 2, "LIT": 3}
RSRC = {"REG": 0, "LIT": 1, "CY": 2, "T2": 3}
WRITES = ("RW", "TW", "T2W", "ALW", "MLW", "MHW", "MEMW", "CYW")

# Branch conditions, read off the main bus: Z/NZ test the whole byte (JA0/JA1),
# C1/C0 its bit 0 (carry, F0), ISM is the opcode class with a second operand.
CSEL = {None: 0, "Z": 1, "NZ": 2, "C1": 3, "C0": 4, "CY": 5, "NCY": 6, "ISM": 7}

# Opcodes, from src/kasm/isa.c.
NOP, NOT, BSL, BSR, BRL, BRR = 0x00, 0x01, 0x04, 0x05, 0x06, 0x07
PSH, POP, RET = 0x08, 0x09, 0x0A
LDR, STR, ORR, AND, XOR, ADD = 0x80, 0x90, 0xC0, 0xD0, 0xE0, 0xF0
LDI, LDM, STM = 0x40, 0x20, 0x21
JMP, JC0, JC1, JA0, JA1, CLL = 0x28, 0x29, 0x2A, 0x2C, 0x2D, 0x30

ONE_OPERAND = (LDR, STR, ORR, AND, XOR, ADD, LDI)
TWO_OPERANDS = (LDM, STM, JMP, JC0, JC1, JA0, JA1, CLL)
NO_OPERAND = (NOP, NOT, BSL, BSR, BRL, BRR, PSH, POP, RET)


def u(src="REG", ra=0, asel=0, lit=0, aop=NOP, r="REG",
      w=(), cond=None, alt=None, nxt=None, disp=None):
    """One microinstruction; it falls through to the next unless nxt is set."""
    return dict(label=None, src=src, ra=ra, asel=asel, lit=lit, aop=aop, r=r,
                w=w, cond=cond, alt=alt, nxt=nxt, disp=disp)


def block(label, steps):
    steps[0]["label"] = label
    return steps


def move(src_reg, dst_reg, nxt=None):
    return [u(ra=src_reg, w=("TW",)),
            u(src="ALU", ra=dst_reg, w=("RW",), nxt=nxt)]


def mar(lo, hi):
    return [u(ra=lo, w=("MLW",)), u(ra=hi, w=("MHW",))]


def inc16(lo, hi):
    return [u(ra=lo, w=("TW",)),
            u(src="ALU", aop=ADD, r="LIT", lit=1, ra=lo, w=("RW", "CYW")),
            u(ra=hi, w=("TW",)),
            u(src="ALU", aop=ADD, r="CY", ra=hi, w=("RW",))]


def dec16(lo, hi, tag):
    """Add 0xFF to the low byte; the high byte only changes on a borrow."""
    return [u(ra=lo, w=("TW",)),
            u(src="ALU", aop=ADD, r="LIT", lit=0xFF, ra=lo, w=("RW", "CYW")),
            u(ra=hi, w=("TW",)),
            u(cond="CY", alt=f"{tag}_end"),
            u(src="ALU", aop=ADD, r="LIT", lit=0xFF, ra=hi, w=("RW",)),
            *block(f"{tag}_end", [u()])]


def fetch(into, last):
    return mar(PCL, PCH) + [u(src="MEM", ra=into, w=("RW",))] + inc16(PCL, PCH) + [last]


def program():
    code = []

    # cpu_reset(): SP starts below the display-sized block, everything else at
    # 0, which is where a 74377 powers up.
    code += block("BOOT", [u(src="LIT", lit=0x3F, ra=SPL, w=("RW",)),
                           u(src="LIT", lit=0xFC, ra=SPH, w=("RW",), nxt="FETCH")])
    code += block("BAD", [u(nxt="BAD")])        # an opcode the ISA does not define

    code += block("FETCH", fetch(IR0, u(ra=IR0, disp="A")))
    code += block("FETCH1", fetch(IR1, u(ra=IR0, cond="ISM", alt="FETCH2")))
    code += block("DISPATCH", [u(ra=IR0, disp="B")])
    code += block("FETCH2", fetch(IR2, u(nxt="DISPATCH")))

    for tag, op in (("NOT", NOT), ("BSL", BSL), ("BSR", BSR),
                    ("BRL", BRL), ("BRR", BRR)):
        code += block(tag, [u(ra=A, w=("TW",)),
                            u(src="ALU", ra=I, w=("RW",)),
                            u(src="ALU", aop=op, ra=A, w=("RW",), nxt="FETCH")])

    code += block("LDR", [u(ra=IR1, w=("ALW",)),
                          u(asel=1, w=("TW",)),
                          u(src="ALU", ra=A, w=("RW",), nxt="FETCH")])
    code += block("STR", [u(ra=IR1, w=("ALW",)),
                          u(ra=A, w=("TW",)),
                          u(src="ALU", asel=1, w=("RW",), nxt="FETCH")])

    for tag, op in (("ORR", ORR), ("AND", AND), ("XOR", XOR)):
        code += block(tag, [u(ra=IR1, w=("ALW",)),
                            u(ra=A, w=("TW",)),
                            u(src="ALU", ra=I, w=("RW",)),
                            u(asel=1, w=("T2W",)),
                            u(src="ALU", aop=op, r="T2", ra=A, w=("RW",),
                              nxt="FETCH")])

    # ADD is the only op that writes carry, and it leaves F's other bits alone.
    code += block("ADD", [u(ra=IR1, w=("ALW",)),
                          u(ra=A, w=("TW",)),
                          u(src="ALU", ra=I, w=("RW",)),
                          u(asel=1, w=("T2W",)),
                          u(src="ALU", aop=ADD, r="T2", ra=A, w=("RW", "CYW")),
                          u(ra=F, w=("TW",)),
                          u(src="ALU", aop=AND, r="LIT", lit=0xFE, w=("TW",)),
                          u(src="ALU", aop=ORR, r="CY", ra=F, w=("RW",),
                            nxt="FETCH")])

    code += block("LDI", move(IR1, A, nxt="FETCH"))

    code += block("LDM", mar(IR1, IR2) + [u(src="MEM", ra=A, w=("RW",),
                                            nxt="FETCH")])
    code += block("STM", mar(IR1, IR2) + [u(ra=A, w=("TW",)),
                                          u(src="ALU", w=("MEMW",), nxt="FETCH")])

    code += block("JMP", move(IR1, PCL) + move(IR2, PCH, nxt="FETCH"))
    code += block("JC0", [u(ra=F, cond="C0", alt="JMP", nxt="FETCH")])
    code += block("JC1", [u(ra=F, cond="C1", alt="JMP", nxt="FETCH")])
    code += block("JA0", [u(ra=A, cond="Z", alt="JMP", nxt="FETCH")])
    code += block("JA1", [u(ra=A, cond="NZ", alt="JMP", nxt="FETCH")])

    code += block("PSH", dec16(SPL, SPH, "psh") + mar(SPL, SPH)
                  + [u(ra=A, w=("TW",)),
                     u(src="ALU", w=("MEMW",), nxt="FETCH")])

    # alu_pop() and alu_ret() zero the cell they read.
    code += block("POP", mar(SPL, SPH)
                  + [u(src="MEM", ra=A, w=("RW",)),
                     u(src="LIT", lit=0, w=("MEMW",))]
                  + inc16(SPL, SPH))
    code[-1]["nxt"] = "FETCH"

    # The high byte of PC sits at the lower address.
    code += block("RET", mar(SPL, SPH)
                  + [u(src="MEM", ra=PCH, w=("RW",)),
                     u(src="LIT", lit=0, w=("MEMW",))]
                  + inc16(SPL, SPH) + mar(SPL, SPH)
                  + [u(src="MEM", ra=PCL, w=("RW",)),
                     u(src="LIT", lit=0, w=("MEMW",))]
                  + inc16(SPL, SPH))
    code[-1]["nxt"] = "FETCH"

    code += block("CLL", dec16(SPL, SPH, "cll0") + mar(SPL, SPH)
                  + [u(ra=PCL, w=("TW",)), u(src="ALU", w=("MEMW",))]
                  + dec16(SPL, SPH, "cll1") + mar(SPL, SPH)
                  + [u(ra=PCH, w=("TW",)),
                     u(src="ALU", w=("MEMW",), nxt="JMP")])
    return code


ENTRY = {NOP: "FETCH", NOT: "NOT", BSL: "BSL", BSR: "BSR", BRL: "BRL",
         BRR: "BRR", PSH: "PSH", POP: "POP", RET: "RET", LDR: "LDR",
         STR: "STR", ORR: "ORR", AND: "AND", XOR: "XOR", ADD: "ADD",
         LDI: "LDI", LDM: "LDM", STM: "STM", JMP: "JMP", JC0: "JC0",
         JC1: "JC1", JA0: "JA0", JA1: "JA1", CLL: "CLL"}


def assemble():
    """-> (seven 256-byte control ROMs, dispatch A, dispatch B, labels)."""
    code = program()
    labels = {}
    for addr, step in enumerate(code):
        if step["label"]:
            if step["label"] in labels:
                raise ValueError(f"duplicate microcode label {step['label']}")
            labels[step["label"]] = addr
    if len(code) > 256:
        raise ValueError(f"microcode is {len(code)} steps, the ROM holds 256")

    def target(name, default):
        return labels[name] if name else default

    rom = [[0] * 256 for _ in range(7)]
    for addr, s in enumerate(code):
        writes = 0
        for bit, name in enumerate(WRITES):
            if name in s["w"]:
                writes |= 1 << bit
        disp = {None: 0, "A": 1, "B": 3}[s["disp"]]     # bit 0 on, bit 1 picks B
        rom[0][addr] = s["lit"]
        rom[1][addr] = s["aop"]
        rom[2][addr] = target(s["nxt"], (addr + 1) & 0xFF)
        rom[3][addr] = target(s["alt"], 0)
        rom[4][addr] = writes
        rom[5][addr] = s["ra"] | (s["asel"] << 5) | (BSRC[s["src"]] << 6)
        rom[6][addr] = RSRC[s["r"]] | (CSEL[s["cond"]] << 2) | (disp << 5)

    bad = labels["BAD"]
    dispatch_a = [bad] * 256
    dispatch_b = [bad] * 256
    for opcode, entry in ENTRY.items():
        # A register operand is encoded in the opcode's low nibble, so every
        # 1xxx0000 opcode covers its whole nibble -- cpu_decode_exec() masks it.
        codes = ([opcode | n for n in range(16)] if opcode & 0x80 else [opcode])
        for oc in codes:
            dispatch_b[oc] = labels[entry]
            if oc in ONE_OPERAND or (oc & 0xF0) in ONE_OPERAND:
                dispatch_a[oc] = labels["FETCH1"]
            elif oc in TWO_OPERANDS:
                dispatch_a[oc] = labels["FETCH1"]
            else:
                dispatch_a[oc] = labels[entry]
    return rom, dispatch_a, dispatch_b, labels, len(code)


if __name__ == "__main__":
    _, _, _, labels, size = assemble()
    print(f"{size} microsteps")
    for name, addr in sorted(labels.items(), key=lambda kv: kv[1]):
        print(f"  {addr:3d}  {name}")
