Idea:
6 bit opcode: xxxxxx

Opcode flags (1: flag, C: opcode, R: register, I: immediate, M: memory address):
No argument:                                                        0000 CCCC
First digit -> 'register' flag (argument is register):              1CCC RRRR
Second digit -> 'immediate' flag (argument is 8 bit immediate):     01CC CCCC | IIII IIII
Third digit -> 'memory' flag (argument is memory address):          001C CCCC | MMMM MMMM | MMMM MMMM
Fourth digit -> virtual 'register' flag:                            0001 CCCC | 0000 RRRR

### Operations with no argument:
| Mnemonic | Opcode (Cycle 1) | Opcode (Cycle 2) | Description                                          |
| -------- | ---------------- | ---------------- | ---------------------------------------------------- |
| NOP      | 0000 0000        | -                | Do nothing                                           |
| NOT      | 0000 0001        | -                | Perform bitwise-NOT on Accumulator                   |
| BSL      | 0000 0100        | -                | Perform bit shift left on Accumulator                |
| BSR      | 0000 0101        | -                | Perform bit shift right on Accumulator               |
| BRL      | 0000 0110        | -                | Perform bit rotation left on Accumulator             |
| BRR      | 0000 0111        | -                | Perform bit rotation right on Accumulator            |

### Operations with 'register' argument:
| Mnemonic | Opcode (Cycle 1) | Opcode (Cycle 2) | Description                                          |
| -------- | ---------------- | ---------------- | ---------------------------------------------------- |
| LDR      | 1000 RRRR        | -                | Load data from Register RRR into Accumulator         |
| STR      | 1001 RRRR        | -                | Store data from Accumulator in Register RRR          |
| ORR      | 1100 RRRR        | -                | Perform bitwise-OR on Accumulator with Register RRR  |
| AND      | 1101 RRRR        | -                | Perform bitwise-AND on Accumulator with Register RRR |
| XOR      | 1110 RRRR        | -                | Perform bitwise-XOR on Accumulator with Register RRR |
| ADD      | 1111 RRRR        | -                | Perform ADD on Accumulator with Register RRR         |

### Operations with 'immediate' argument:
| Mnemonic | Opcode (Cycle 1) | Opcode (Cycle 2) | Description                                          |
| -------- | ---------------- | ---------------- | ---------------------------------------------------- |
| LDI      | 0100 0000        | IIII IIII        | Load immediate into Accumulator                      |

### Operations with 'memory' argument:
| Mnemonic | Opcode (Cycle 1) | Opcode (Cycle 2) | Description                                          |
| -------- | ---------------- | ---------------- | ---------------------------------------------------- |
| LDM      | 0010 0000        | MMMM MMMM        | Load data from Memory into Accumulator               |
| STM      | 0010 0001        | MMMM MMMM        | Store data from Accumulator in Memory                |
| JMP      | 0010 1000        | PPPP PPPP        | Jump to address                                      |
| JC0      | 0010 1010        | PPPP PPPP        | Jump if Carry = 0                                    |
| JC1      | 0010 1011        | PPPP PPPP        | Jump if Carry = 1                                    |
| JA0      | 0010 1100        | PPPP PPPP        | Jump if Accumulator = 0                              |
| JA1      | 0010 1101        | PPPP PPPP        | Jump if Accumulator ≠ 0                              |

### Virtual operations with register argument:
| Mnemonic | Opcode (Cycle 1) | Opcode (Cycle 2) | Description                                          |
| -------- | ---------------- | ---------------- | ---------------------------------------------------- |
| vOUT     | 1000 RRRR        | -                | VIRTUAL: Send data from register RRR to printf()     |
| vINN     | 1001 RRRR        | -                | VIRTUAL: Send data from scanf() to Register RRR      |
| vEXT     | 1010 RRRR        | -                | VIRTUAL: Call exit(0)                                |
