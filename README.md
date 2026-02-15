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
- Registers: 8 (one is a shift register for the 8-segment displays)
- Memory: 2048 x 8 bit

**Arithmetic Logic Unit (ALU)**:
- Input buffers:
    - I (input left)
- Output buffers:
    - A (accumulator)
    - C (carry)
- Note that the input buffer (i.e., I) is there to prevent simultaneous read/write operations on the output accumulator (i.e., A). E.g., before performing the add operation (i.e., ADD), A would first be written to I, which is connected to the left ALU input, while the selected operand register would be directly connected to the right ALU input. 

## Instruction Set

### No operation
| #  | Mnemonic | Opcode (Cycle 1)       | Opcode (Cycle 2)       | Description |
|----|----------|------------------------|------------------------|-------------|
| 0  | NOP      | 0000 0000              | -                      | Do nothing  |

### Input/output operations
| #  | Mnemonic | Opcode (Cycle 1)       | Opcode (Cycle 2)       | Description |
|----|----------|------------------------|------------------------|-------------|
| 1  | LDR      | 0001 0RRR              | -                      | Load data from Register RRR into Accumulator |
| 2  | STR      | 0001 1RRR              | -                      | Store data from Accumulator in Register RRR |
| 3  | LDM      | 1001 0MMM              | MMMM MMMM              | Load data from Memory address MMM MMMM MMMM into Accumulator |
| 4  | STM      | 1001 1MMM              | MMMM MMMM              | Store data from Accumulator in Memory address MMM MMMM MMMM |
| 5  | LDI      | 1000 1000              | IIII IIII              | Load immediate IIII IIII into Accumulator |

### bitwise operations
| #  | Mnemonic | Opcode (Cycle 1)       | Opcode (Cycle 2)       | Description |
|----|----------|------------------------|------------------------|-------------|
| 6  | ORR      | 0010 0RRR              | -                      | Perform bitwise-OR on Accumulator with Register RRR |
| 7  | AND      | 0010 1RRR              | -                      | Perform bitwise-AND on Accumulator with Register RRR |
| 8  | XOR      | 0011 0RRR              | -                      | Perform bitwise-XOR on Accumulator with Register RRR |
| 9  | NOT      | 0000 1000              | -                      | Perform bitwise-NOT on Accumulator |

### Shift/rotation operations
| #  | Mnemonic | Opcode (Cycle 1)       | Opcode (Cycle 2)       | Description |
|----|----------|------------------------|------------------------|-------------|
| 10 | BSL      | 0100 0000              | -                      | Perform bit shift left on Accumulator |
| 11 | BSR      | 0100 1000              | -                      | Perform bit shift right on Accumulator |
| 12 | BRL      | 0101 0000              | -                      | Perform bit rotation left on Accumulator |
| 13 | BRR      | 0101 1000              | -                      | Perform bit rotation right on Accumulator |

### Math operations
| #  | Mnemonic | Opcode (Cycle 1)       | Opcode (Cycle 2)       | Description |
|----|----------|------------------------|------------------------|-------------|
| 14 | ADD      | 0011 1RRR              | -                      | Perform ADD on Accumulator with Register RRR |

### (Conditional) jump operations
| #  | Mnemonic | Opcode (Cycle 1)       | Opcode (Cycle 2)       | Description |
|----|----------|------------------------|------------------------|-------------|
| 15 | JMP      | 1010 0PPP              | PPPP PPPP              | Jump to address PPP PPPP PPPP in program memory |
| 16 | JC0      | 1010 1PPP              | PPPP PPPP              | Jump to address PPP PPPP PPPP if Carry = 0 |
| 17 | JC1      | 1011 0PPP              | PPPP PPPP              | Jump to address PPP PPPP PPPP if Carry = 1 |
| 18 | JA0      | 1110 1PPP              | PPPP PPPP              | Jump to address PPP PPPP PPPP if Accumulator = 0 |
| 19 | JA1      | 1111 0PPP              | PPPP PPPP              | Jump to address PPP PPPP PPPP if Accumulator ≠ 0 |

### Get Program Counter
| #  | Mnemonic | Opcode (Cycle 1)       | Opcode (Cycle 2)       | Description |
|----|----------|------------------------|------------------------|-------------|
| 20 | GPC      | 0110 0000              | -                      | Write PC to R (R6: First 8 bits, R7: Last 3 bits) |

### Virtual operations (only available on virtual machine)
| #  | Mnemonic | Opcode (Cycle 1)       | Opcode (Cycle 2)       | Description |
|----|----------|------------------------|------------------------|-------------|
| 21 | OUT      | 0110 1RRR              | -                      | Send data from Register RRR to printf() |
| 22 | INN      | 0111 0RRR              | -                      | Send data from scanf() to Register RRR |
| 23 | EXT      | 0111 1RRR              | -                      | Call exit(0) |
