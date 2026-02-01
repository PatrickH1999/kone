#!/usr/bin/env python3

import argparse
import sys

opcodes = {
    "NOP": 0b0000_0000,
    "NOT": 0b0000_1000,
    "LDR": 0b0001_0000,
    "STR": 0b0001_1000,
    "LDM": 0b1001_0000,
    "STM": 0b1001_1000,
    "LDI": 0b1000_1000,        
    "ORR": 0b0010_0000,
    "AND": 0b0010_1000,
    "XOR": 0b0011_0000,
    "ADD": 0b0011_1000,
    "BSL": 0b0100_0000,
    "BSR": 0b0100_1000,
    "BRL": 0b0101_0000,
    "BRR": 0b0101_1000,
    "JMP": 0b1010_0000,
    "JC0": 0b1010_1000,
    "JC1": 0b1011_0000,
    "JA0": 0b1110_1000,
    "JA1": 0b1111_0000,
    "OUT": 0b0110_0000
}

arglims = {
    "NOP": [],
    "NOT": [],
    "LDR": [0b111],
    "STR": [0b111],
    "LDM": [0b111_1111_1111],
    "STM": [0b111_1111_1111],
    "LDI": [0b1111_1111],
    "ORR": [0b111],
    "AND": [0b111],
    "XOR": [0b111],
    "ADD": [0b111],
    "BSL": [],
    "BSR": [],
    "BRL": [],
    "BRR": [],
    "JMP": [0b111_1111_1111],
    "JC0": [0b111_1111_1111],
    "JC1": [0b111_1111_1111],
    "JA0": [0b111_1111_1111],
    "JA1": [0b111_1111_1111],
    "OUT": [0b111]
}

parser = argparse.ArgumentParser(
    description="Assemble kone assembly to kone machine code."
)
parser.add_argument(
    "input",
    help="input assembly file (.asm)"
)
parser.add_argument(
    "-o", "--output",
    required=True,
    help="output binary file (.bin)"
)
args = parser.parse_args()

infile_name = args.input
machine_code = []
with open(infile_name) as infile:
    lines = infile.readlines()
for line in lines:
    words = line.split()
    opcode = words[0]
    assert opcode in opcodes, f"Unknown opcode: {opcode}"
    assert (len(words) == (len(arglims[opcode]) + 1)), f"Wrong number ({len(words) - 1}) arguments for opcode {opcode} (expects {len(arglims[opcode])})"
    cycle0 = opcodes[opcode]   # machine cycle 0
    if (len(words) == 1):
        machine_code.append(cycle0)
    elif (len(words) == 2):
        arg = int(words[1], 0) 
        assert 0 <= arg <= arglims[opcode][0], f"Opcode argument {arg} out of bounds for opcode {opcode}" 
        two_cycles = ((opcodes[opcode] >> 7) == 1)
        if not two_cycles:
            cycle0 += arg
            machine_code.append(cycle0)
        elif two_cycles:
            cycle0 += (arg >> 8)
            cycle1 = (arg & 0b1111_1111)   # machine cycle 1
            machine_code.extend([cycle0, cycle1])
outfile_name = args.output
with open(outfile_name, "wb") as outfile:
    outfile.write(bytes(machine_code))
