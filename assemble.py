#!/home/patrick/miniforge3/bin/python

import sys

opcodes = {
    "NOP": 0b00000000,
    "NOT": 0b00001000,
    "LDR": 0b00010000,
    "STR": 0b00011000,
    "LDM": 0b10010000,
    "STM": 0b10011000,
    "LDI": 0b10001000,        
    "ORR": 0b00100000,
    "AND": 0b00101000,
    "XOR": 0b00110000,
    "ADD": 0b00111000,
    "BSL": 0b01000000,
    "BSR": 0b01001000,
    "BRL": 0b01010000,
    "BRR": 0b01011000,
    "JMP": 0b10100000,
    "JC0": 0b10101000,
    "JC1": 0b10110000,
    "JA0": 0b11101000,
    "JA1": 0b11110000,
    "PRN": 0b01100000
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
    "PRN": [0b111]
}

file_name = sys.argv[1]
with open(file_name) as file:
    lines = file.readlines()
for line in lines:
    words = line.split()
    opcode = words[0]
    assert opcode in opcodes, f"Unknown opcode: {opcode}"
    line0 = opcodes[opcode]
    assert (len(words) == (len(arglims[opcode]) + 1)), f"Wrong number ({len(words) - 1}) arguments for opcode {opcode} (expects {len(arglims[opcode])})"
    if (len(words) == 2):
        arg = int(words[1], 0) 
        assert 0 <= arg <= arglims[opcode][0], f"Opcode argument {arg} out of bounds for opcode {opcode}" 
        two_cycles = ((opcodes[opcode] >> 7) == 1);

