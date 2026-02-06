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
    "GPC": 0b0110_0000,
    "OUT": 0b0110_1000,
    "INN": 0b0111_0000,
    "EXT": 0b0111_1000
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
    "GPC": [],
    "OUT": [0b111],
    "INN": [0b111],
    "EXT": []
}

takes_addr_alias = ["JMP", "JC0", "JC1", "JA1"]

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
with open(infile_name) as infile:
    lines = infile.readlines()

for parse_cycle in ["addr_alias", "main"]:
    machine_code = []
    if (parse_cycle == "addr_alias"): addr_alias = {}
    pc = 0   # Program counter for jump-address-evaluation
    
    for line in lines:
        words = line.split()
        
        for i, word in enumerate(words):
            if (word[0:2] == "//"):   # If comment
                words = words[:i]   # Limit parsed code up until where "//" is encountered
                break
        
        if (len(words) == 0):
            continue   # No words in line -> go to next line
        
        if (words[0][-1] == ":"):
            alias = words[0][:-1]
            addr_alias[alias] = pc
            continue   # Jump address -> go to next line
    
        opcode = words[0]
        assert opcode in opcodes, f"Unknown opcode: {opcode}!"
        assert (len(words) == (len(arglims[opcode]) + 1)), (
            f"Wrong number ({len(words) - 1}) arguments for opcode {opcode} "
            "(expects {len(arglims[opcode])})!"
        )
        cycle0 = opcodes[opcode]   # machine cycle 0
        two_cycles = False
        
        if (len(words) == 1):
            machine_code.append(cycle0)
        elif (len(words) == 2):
            arg_str = words[1]
            arg = -1
            if (parse_cycle != "addr_alias"):
                assert arg_str.isdigit() or (arg_str in addr_alias), (
                    f"Opcode argument {arg_str} is neither an unsigned "
                    "decimal integer nor in list of address aliases!"
                )
            
            if arg_str.isdigit():
                arg = int(arg_str)
                assert 0 <= arg <= arglims[opcode][0], (
                    f"Opcode argument value {arg} out of bounds for opcode {opcode}!"
                )
            elif (parse_cycle != "addr_alias") and (arg_str in addr_alias):
                assert opcode in takes_addr_alias, (
                    f"Opcode {opcode} does not take address alias ({arg_str})!"
                )
                arg = addr_alias[arg_str]
    
            two_cycles = ((opcodes[opcode] >> 7) == 1)
            
            if not two_cycles:
                cycle0 += arg
                machine_code.append(cycle0)
            elif two_cycles:
                cycle0 += (arg >> 8)
                cycle1 = (arg & 0b1111_1111)   # machine cycle 1
                machine_code.extend([cycle0, cycle1])
        
        if not two_cycles: pc += 1
        elif two_cycles: pc += 2

outfile_name = args.output
with open(outfile_name, "wb") as outfile:
    outfile.write(bytes(machine_code))
