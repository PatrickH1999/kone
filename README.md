# Kone
The goal of this project ('kone' means 'device' or 'gadget' in finnish) is to design and build a computer using simple logic chips (e.g., from the 74xx series) and other components. By any means, the use of ICs that resemble a full-blown CPU is strictly forbidden.

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

### No Operation
| #  | Mnemonic | Opcode (Cycle 1)         | Opcode (Cycle 2)       | Description |
|----|----------|------------------------|------------------------|-------------|
| 0  | NOP      | 0000 0000              |                        | Do nothing  |

### Input/Output Operations
| #  | Mnemonic | Opcode (Cycle 1)       | Opcode (Cycle 2)       | Description |
|----|----------|------------------------|------------------------|-------------|
| 1  | LDR      | 0xxx xRRR              | -                      | Load data from Register RRR into Accumulator |
| 2  | STR      | 0xxx xRRR              | -                      | Store data from Accumulator in Register RRR |
| 3  | LDM      | 1xxx xMMM              | MMMM MMMM              | Load data from Memory address MMM MMMM MMMM into Accumulator |
| 4  | STM      | 1xxx xMMM              | MMMM MMMM              | Store data from Accumulator in Memory address MMM MMMM MMMM |
| 5  | LDI      | 1xxx x000              | IIII IIII              | Load immediate IIII IIII into Accumulator |

### Bitwise Operations
| #  | Mnemonic | Opcode (Cycle 1)       | Opcode (Cycle 2)       | Description |
|----|----------|------------------------|------------------------|-------------|
| 6  | ORR      | 0xxx xRRR              | -                      | Perform bitwise-OR on Accumulator with Register RRR |
| 7  | AND      | 0xxx xRRR              | -                      | Perform bitwise-AND on Accumulator with Register RRR |
| 8  | XOR      | 0xxx xRRR              | -                      | Perform bitwise-XOR on Accumulator with Register RRR |
| 9  | NOT      | 0000 1000              | -                      | Perform bitwise-NOT on Accumulator |

### Shift/Rotation Operations
| #  | Mnemonic | Opcode (Cycle 1)       | Opcode (Cycle 2)       | Description |
|----|----------|------------------------|------------------------|-------------|
| 10 | BSL      | 0xxx x                 | -                      | Perform bit shift left on Accumulator |
| 11 | BSR      | 0xxx x                 | -                      | Perform bit shift right on Accumulator |
| 12 | BRL      | 0xxx x                 | -                      | Perform bit rotation left on Accumulator |
| 13 | BRR      | 0xxx x                 | -                      | Perform bit rotation right on Accumulator |

### Math Operations
| #  | Mnemonic | Opcode (Cycle 1)       | Opcode (Cycle 2)       | Description |
|----|----------|------------------------|------------------------|-------------|
| 14 | ADD      | 0xxx xRRR              | -                      | Perform ADD on Accumulator with Register RRR |

### (Conditional) Jump Operations
| #  | Mnemonic | Opcode (Cycle 1)       | Opcode (Cycle 2)       | Description |
|----|----------|------------------------|------------------------|-------------|
| 15 | JMP      | 1xxx xPPP              | PPPP PPPP              | Jump to address PPP PPPP PPPP in program memory |
| 16 | JC0      | 1xxx xPPP              | PPPP PPPP              | Jump to address PPP PPPP PPPP if Carry = 0 |
| 17 | JC1      | 1xxx xPPP              | PPPP PPPP              | Jump to address PPP PPPP PPPP if Carry = 1 |
| 18 | JA0      | 1xxx xPPP              | PPPP PPPP              | Jump to address PPP PPPP PPPP if Accumulator = 0 |
| 19 | JA1      | 1xxx xPPP              | PPPP PPPP              | Jump to address PPP PPPP PPPP if Accumulator ≠ 0 |
