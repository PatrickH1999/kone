# Kone
The goal of this project ('kone' means 'device' or 'gadget' in finnish) is to design and build a computer using simple logic chips (e.g., from the 74xx series) and other components. By any means, the use of ICs that resemble a full-blown CPU is strictly forbidden.

## Usage
This project provides a virtual machine (called `kone`), which is written in the C programming language and follows the __kone__ cpu architecture. To build the virtual machine, run:
```bash
cd kone
make clean
make
```
The Applications for __kone__ are written in __kasm__ (for 'kone assembly'). The assembler, `kasm.py`, does only generate machine code for the __kone__ cpu architecture. For an example, run:
```bash
./kasm.py examples/count.kasm -o examples/count.bin
```
This generates a __kone__ machine code binary (`count.bin`), which can be executed via the __kone__ virtual machine:
```bash
./kone examples/count.bin
```
The output should be:
```bash
./kone examples/count.bin
Output: 1
Output: 2
Output: 3
Output: 4
Output: 5
Output: 6
Output: 7
Output: 8
Output: 9
...
```

## Architecture
**General Features**:
- Data bus: 8 bit
- Registers: 16 (R0 to R15):
    - `R14`-`R15`: Program counter
    - `R11`-`R13`: Instruction register
    - `R10`: flag (`F7`, `F6`, `F5`, `F4`, `F3`, `F2`, `F1`, `F0`)
    - `R9`: accumulator
    - `R8`: ALU input left
    - `R6`-`R7`: Stack pointer 
- RAM: 64 kiB (16 bit addresses)

**Arithmetic Logic Unit (ALU)**:
- Input buffers:
    - `I` (input left -> `R13`)
- Output buffers:
    - `A` (accumulator -> `R14`)
    - `C` (carry -> `F0`)
- Note that the input buffer (i.e., `I`) is there to prevent simultaneous read/write operations on the output accumulator (i.e., `A`). E.g., before performing the add operation (i.e., `ADD`), A would first be written to I, which is connected to the left ALU input, while the selected operand register would be directly connected to the right ALU input.

## Instruction Set:
The __kone__ decoder first evaluates opcode flags, which tell the decoder what kind of arguments are to be expected and how long they are:
- No argument:                                                        `0000 CCCC` 
- First digit -> 'register' flag (argument is register):              `1CCC RRRR` 
- Second digit -> 'immediate' flag (argument is 8 bit immediate):     `01CC CCCC` | `IIII IIII` 
- Third digit -> 'memory' flag (argument is memory address):          `001C CCCC` | `MMMM MMMM` | `MMMM MMMM`
- Fourth digit -> virtual opcode (argument is register):              `0001 CCCC` | `0000 RRRR` 

### Operations with no argument:
| Mnemonic | Opcode (Cycle 0) | Opcode (Cycle 1) | Opcode (Cycle 2) | Description                                          |
| -------- | ---------------- | ---------------- | ---------------- | ---------------------------------------------------- |
| `NOP`    | `0000 0000`      | -                | -                | Do nothing                                           |
| `NOT`    | `0000 0001`      | -                | -                | Perform bitwise-NOT on Accumulator                   |
| `BSL`    | `0000 0100`      | -                | -                | Perform bit shift left on Accumulator                |
| `BSR`    | `0000 0101`      | -                | -                | Perform bit shift right on Accumulator               |
| `BRL`    | `0000 0110`      | -                | -                | Perform bit rotation left on Accumulator             |
| `BRR`    | `0000 0111`      | -                | -                | Perform bit rotation right on Accumulator            |
| `RET`    | `0000 1000`      | -                | -                | Return to address at SP                              |

### Operations with 'register' argument:
| Mnemonic | Opcode (Cycle 0) | Opcode (Cycle 1) | Opcode (Cycle 2) | Description                                          |
| -------- | ---------------- | ---------------- | ---------------- | ---------------------------------------------------- |
| `LDR`    | `1000 RRRR`      | -                | -                | Load data from Register RRR into Accumulator         |
| `STR`    | `1001 RRRR`      | -                | -                | Store data from Accumulator in Register RRR          |
| `PSH`    | `1010 RRRR`      | -                | -                | Push Register RRR to stack                           |
| `POP`    | `1011 RRRR`      | -                | -                | Pop stack top value to Register RRR                  |
| `ORR`    | `1100 RRRR`      | -                | -                | Perform bitwise-OR on Accumulator with Register RRR  |
| `AND`    | `1101 RRRR`      | -                | -                | Perform bitwise-AND on Accumulator with Register RRR |
| `XOR`    | `1110 RRRR`      | -                | -                | Perform bitwise-XOR on Accumulator with Register RRR |
| `ADD`    | `1111 RRRR`      | -                | -                | Perform ADD on Accumulator with Register RRR         |

### Operations with 'immediate' argument:
| Mnemonic | Opcode (Cycle 0) | Opcode (Cycle 1) | Opcode (Cycle 2) | Description                                          |
| -------- | ---------------- | ---------------- | ---------------- | ---------------------------------------------------- |
| `LDI`    | `0100 0000`      | `IIII IIII`      | -                | Load immediate into Accumulator                      |

### Operations with 'memory' argument:
| Mnemonic | Opcode (Cycle 0) | Opcode (Cycle 1) | Opcode (Cycle 2) | Description                                          |
| -------- | ---------------- | ---------------- | ---------------- | ---------------------------------------------------- |
| `LDM`    | `0010 0000`      | `MMMM MMMM`      | `MMMM MMMM`      | Load data from Memory into Accumulator               |
| `STM`    | `0010 0001`      | `MMMM MMMM`      | `MMMM MMMM`      | Store data from Accumulator in Memory                |
| `JMP`    | `0010 1000`      | `PPPP PPPP`      | `PPPP PPPP`      | Jump to address                                      |
| `JC0`    | `0010 1010`      | `PPPP PPPP`      | `PPPP PPPP`      | Jump if Carry = 0                                    |
| `JC1`    | `0010 1011`      | `PPPP PPPP`      | `PPPP PPPP`      | Jump if Carry = 1                                    |
| `JA0`    | `0010 1100`      | `PPPP PPPP`      | `PPPP PPPP`      | Jump if Accumulator = 0                              |
| `JA1`    | `0010 1101`      | `PPPP PPPP`      | `PPPP PPPP`      | Jump if Accumulator ≠ 0                              |
| `CLL`    | `0011 0000`      | `PPPP PPPP`      | `PPPP PPPP`      | Call/jump to memory address, push PC to SP           |

### Virtual operations with register argument:
| Mnemonic | Opcode (Cycle 0) | Opcode (Cycle 1) | Opcode (Cycle 2) | Description                                          |
| -------- | ---------------- | ---------------- | ---------------- | ---------------------------------------------------- |
| `vOUT`   | `1000 RRRR`      | -                | -                | VIRTUAL: Send data from register RRR to printf()     |
| `vINN`   | `1001 RRRR`      | -                | -                | VIRTUAL: Send data from scanf() to Register RRR      |
| `vEXT`   | `1010 RRRR`      | -                | -                | VIRTUAL: Call exit(0)                                |
