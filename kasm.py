#!/usr/bin/env python3

import argparse
import os


# Replace .include "<file.kasm>" with code from <file.kasm>:
def replace_include_statements(lines: list[str], main_dir: str) -> list[str]:
    for i, line in enumerate(lines):
        words = line.split()
        if len(words) == 0:
            continue
        if words[0] == ".include":
            assert len(words) == 2, (
                f"Wrong number ({len(words) - 1}) arguments for '.include' statement "
                "(expects {2})!"
            )
            include_file = words[1].strip('"')
            include_path = os.path.join(main_dir, include_file)
            with open(include_path) as include:
                lines_ = include.readlines()
            lines.pop(i)
            lines[i:i] = lines_
            lines = replace_include_statements(lines, main_dir)
    return lines


def is_uint(s: str) -> bool:
    try:
        int(s, 0)
        return True
    except ValueError:
        return False


def search_comment(words: list[str]) -> list[str]:
    for i, word in enumerate(words):
        if word[0:2] == "//":  # If comment
            words = words[:i]  # Limit parsed code up until where "//" is encountered
            break
    return words


def check_addr_alias(
    words: list[str], pc: int, addr_alias: dict[str, int], parse_cycle: str
) -> tuple[dict[str, int], bool]:
    if words[0][-1] == ":":
        alias = words[0][:-1]
        if parse_cycle == "addr_alias":
            addr_alias[alias] = pc
        return addr_alias, True
    return addr_alias, False


def get_opcode(
    words: list[str], opcodes: dict[str, int], arglims: dict[str, list[int]]
) -> str:
    opcode = words[0]
    assert opcode in opcodes, f"Unknown opcode: {opcode}!"
    assert len(words) == (len(arglims[opcode]) + 1), (
        f"Wrong number ({len(words) - 1}) arguments for opcode {opcode} "
        "(expects {len(arglims[opcode])})!"
    )
    return opcode


def get_arg(
    arg_str: str,
    parse_cycle: str,
    addr_alias: dict[str, int],
    arglims: dict[str, list[int]],
    takes_addr_alias: list[str],
    opcode: str,
) -> (
    int
):  # Performs checks and converts opcode argument (uint8_str or address alias) to uint8
    arg = -1
    if parse_cycle == "main":
        assert is_uint(arg_str) or (arg_str in addr_alias), (
            f"Opcode argument {arg_str} is neither an unsigned "
            "decimal integer nor in list of address aliases!"
        )
        if is_uint(arg_str):
            arg = int(arg_str, 0)
            assert 0 <= arg <= arglims[opcode][0], (
                f"Opcode argument value {arg} out of bounds for opcode {opcode}!"
            )
        elif arg_str in addr_alias:
            assert opcode in takes_addr_alias, (
                f"Opcode {opcode} does not take address alias ({arg_str})!"
            )
            arg = addr_alias[arg_str]
    return arg


opcodes = {
    "NOP": 0b0000_0000,
    "NOT": 0b0000_0001,
    "BSL": 0b0000_0100,
    "BSR": 0b0000_0101,
    "BRL": 0b0000_0110,
    "BRR": 0b0000_0111,
    "PSH": 0b0000_1000,
    "POP": 0b0000_1001,
    "RET": 0b0000_1010,
    "LDR": 0b1000_0000,
    "STR": 0b1001_0000,
    "ORR": 0b1100_0000,
    "AND": 0b1101_0000,
    "XOR": 0b1110_0000,
    "ADD": 0b1111_0000,
    "LDI": 0b0100_0000,
    "LDM": 0b0010_0000,
    "STM": 0b0010_0001,
    "JMP": 0b0010_1000,
    "JC0": 0b0010_1001,
    "JC1": 0b0010_1010,
    "JA0": 0b0010_1100,
    "JA1": 0b0010_1101,
    "CLL": 0b0011_0000,
}

arglims = {
    "NOP": [],
    "NOT": [],
    "BSL": [],
    "BSR": [],
    "BRL": [],
    "BRR": [],
    "PSH": [],
    "POP": [],
    "RET": [],
    "LDR": [0b1111],
    "STR": [0b1111],
    "ORR": [0b1111],
    "AND": [0b1111],
    "XOR": [0b1111],
    "ADD": [0b1111],
    "LDI": [0b1111_1111],
    "LDM": [0b1111_1111_1111_1111],
    "STM": [0b1111_1111_1111_1111],
    "JMP": [0b1111_1111_1111_1111],
    "JC0": [0b1111_1111_1111_1111],
    "JC1": [0b1111_1111_1111_1111],
    "JA0": [0b1111_1111_1111_1111],
    "JA1": [0b1111_1111_1111_1111],
    "CLL": [0b1111_1111_1111_1111],
}

takes_addr_alias = [
    "JMP",
    "JC0",
    "JC1",
    "JA0",
    "JA1",
    "CLL",
]  # Opcodes that accept address alias as argument

parser = argparse.ArgumentParser(
    description="Assemble kone assembly to kone machine code."
)
parser.add_argument("input", help="input assembly file (.asm)")
parser.add_argument("-o", "--output", required=True, help="output binary file (.bin)")
args = parser.parse_args()

main_path = args.input
main_dir = os.path.dirname(main_path)
with open(main_path) as main:
    lines = main.readlines()


lines = replace_include_statements(lines, main_dir)

addr_alias = {}
machine_code = []

for parse_cycle in ["addr_alias", "main"]:
    if parse_cycle == "addr_alias":
        addr_alias = {}
    pc = 0  # Program counter for jump-address-evaluation

    for line in lines:
        words = line.split()
        words = search_comment(words)
        if len(words) == 0:
            continue  # No words in line -> go to next line
        addr_alias, found = check_addr_alias(words, pc, addr_alias, parse_cycle)
        if found:
            continue  # Address alias found -> go to next line
        opcode = get_opcode(words, opcodes, arglims)
        cycle0 = opcodes[opcode]  # machine cycle 0
        n_cycles = -1
        if len(words) == 1:
            n_cycles = 1
            if parse_cycle == "main":
                machine_code.append(cycle0)
        elif len(words) == 2:
            arg_str = words[1]
            arg = get_arg(
                arg_str, parse_cycle, addr_alias, arglims, takes_addr_alias, opcode
            )

            if (cycle0 >> 5) == 1:
                n_cycles = 3
            elif (cycle0 >> 6) == 1:
                n_cycles = 2
            else:
                n_cycles = 1

            if parse_cycle == "main":
                cycles = []
                if n_cycles == 1:
                    cycle0 += arg
                    cycles = [cycle0]
                elif n_cycles == 2:
                    cycle1 = arg
                    cycles = [cycle0, cycle1]
                elif n_cycles == 3:
                    cycle1 = arg & 0b1111_1111
                    cycle2 = (arg >> 8) & 0b1111_1111
                    cycles = [cycle0, cycle1, cycle2]
                machine_code.extend(cycles)

        if n_cycles == 1:
            pc += 1
        elif n_cycles == 2:
            pc += 2
        elif n_cycles == 3:
            pc += 3

outfile_name = args.output
with open(outfile_name, "wb") as outfile:
    outfile.write(bytes(machine_code))
