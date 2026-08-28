# Kone
The goal of this project ('kone' means 'device' or 'gadget' in Finnish) is to design and build a computer using simple logic chips (e.g., from the 74xx series) and other components. Under no circumstances is the use of ICs that resemble a full-blown CPU allowed.

## Usage
This project provides a virtual machine (called `kone`), which is written in the C programming language and follows the __kone__ cpu architecture. To build the virtual machine, run:
```bash
cd kone
make clean
make
```
This also builds the __kasm__ assembler. Other useful targets are `make test` (run the test suite), `make debug` (build with debugging symbols and no optimization), `make kasm` (build only the assembler), and `make install` (install `kone` and `kasm` to `$(HOME)/.local/bin`, override with `PREFIX=...`).

The Applications for __kone__ are written in __kasm__ (for 'kone assembly'). The assembler, `kasm`, only generates machine code for the __kone__ cpu architecture. For an example, run:
```bash
./kasm -i examples/display.kasm -o bin/display.bin
```
This generates a __kone__ machine code binary (`display.bin`), which can be executed via the __kone__ virtual machine:
```bash
./kone -b bin/display.bin -t 1
```
This fills the terminal with a continuously cycling sequence of printable ASCII characters (space through `~`), scrolling row by row across the 40x24 __kone__ display. Press `Ctrl+C` to exit.

## Architecture
**General Features**:
- Data bus: 8 bit
- Registers: 32:
    - `R0`-`R15`: Custom registers
    - `R16`-`R19`: Keyboard/Display device registers (see "Devices" below)
    - `R22`-`R23`: `SP[2]`, stack pointer (data structure: FILO)
    - `R24`: `I`, ALU input (left)
    - `R25`: `A`, accumulator
        - `F0`: carry flag
    - `R26`: `F`, flags (`F7`, `F6`, `F5`, `F4`, `F3`, `F2`, `F1`, `F0`)
    - `R27`-`R29`: `IR[3]`, instruction register
    - `R30`-`R31`: `PC[2]`, program counter
- RAM: 64 KiB (16 bit addresses)

**Arithmetic Logic Unit (ALU)**:
- Input buffers:
    - `I` (input left -> `R24`)
- Output buffers:
    - `A` (accumulator -> `R25`)
    - `C` (carry -> `F0`)
- Note that the input buffer (i.e., `I`) is there to prevent simultaneous read/write operations on the output accumulator (i.e., `A`). E.g., before performing the add operation (i.e., `ADD`), A is first written to I, which is connected to the left ALU input, while the selected operand register is directly connected to the right ALU input.

**Devices**:
- Keyboard: pressed keys are polled in the background and, once received, exposed via `R16` (set flag) and `R17` (char, ASCII 32-255, plus backspace: 8 or 127, depending on the terminal); every other char is reported as a space. kasm programs should clear the set flag after reading to acknowledge the char (see `examples/keyboard.kasm`).
- Display: writing an ASCII char (32-126) to `R19` and setting `R18` pushes it to the next cell of a 40x24 character grid, wrapping to a new row once the current row is full (see `examples/display.kasm`). Writing a backspace (8) instead steps back onto the previous cell and clears it, which is how a program erases what it printed; at the start of a row it does nothing.

## Instruction Set:
The __kone__ decoder first evaluates opcode flags, which tell the decoder what kind of arguments are to be expected and how long they are:
- No argument:                                                        `0000 CCCC`
- First digit -> 'register' flag (argument is register):              `1CCC 0000` | `000R RRRR`
- Second digit -> 'immediate' flag (argument is 8 bit immediate):     `01CC CCCC` | `IIII IIII`
- Third digit -> 'memory' flag (argument is memory address):          `001C CCCC` | `MMMM MMMM` | `MMMM MMMM`
- Fourth digit -> virtual opcode (argument is register):              `0001 CCCC` | `0000 RRRR`

### Operations with no argument:
| Mnemonic | Opcode (Cycle 0) | Opcode (Cycle 1) | Opcode (Cycle 2) | Description                                          |
| -------- | ---------------- | ---------------- | ---------------- | ---------------------------------------------------- |
| `NOP`    | `0000 0000`      | -                | -                | Do nothing                                           |
| `NOT`    | `0000 0001`      | -                | -                | Perform bitwise-NOT on accumulator                   |
| `BSL`    | `0000 0100`      | -                | -                | Perform bit shift left on accumulator                |
| `BSR`    | `0000 0101`      | -                | -                | Perform bit shift right on accumulator               |
| `BRL`    | `0000 0110`      | -                | -                | Perform bit rotation left on accumulator             |
| `BRR`    | `0000 0111`      | -                | -                | Perform bit rotation right on accumulator            |
| `PSH`    | `0000 1000`      | -                | -                | Push accumulator to stack                            |
| `POP`    | `0000 1001`      | -                | -                | Pop stack top value to accumulator                   |
| `RET`    | `0000 1010`      | -                | -                | Return to address at SP                              |

### Operations with 'register' argument:
| Mnemonic | Opcode (Cycle 0) | Opcode (Cycle 1) | Opcode (Cycle 2) | Description                                          |
| -------- | ---------------- | ---------------- | ---------------- | ---------------------------------------------------- |
| `LDR`    | `1000 0000`      | `000R RRRR`      | -                | Load data from Register RRR into accumulator         |
| `STR`    | `1001 0000`      | `000R RRRR`      | -                | Store data from accumulator in Register RRR          |
| `ORR`    | `1100 0000`      | `000R RRRR`      | -                | Perform bitwise-OR on accumulator with Register RRR  |
| `AND`    | `1101 0000`      | `000R RRRR`      | -                | Perform bitwise-AND on accumulator with Register RRR |
| `XOR`    | `1110 0000`      | `000R RRRR`      | -                | Perform bitwise-XOR on accumulator with Register RRR |
| `ADD`    | `1111 0000`      | `000R RRRR`      | -                | Perform ADD on accumulator with Register RRR         |

### Operations with 'immediate' argument:
| Mnemonic | Opcode (Cycle 0) | Opcode (Cycle 1) | Opcode (Cycle 2) | Description                                          |
| -------- | ---------------- | ---------------- | ---------------- | ---------------------------------------------------- |
| `LDI`    | `0100 0000`      | `IIII IIII`      | -                | Load immediate into accumulator                      |

### Operations with 'memory' argument:
| Mnemonic | Opcode (Cycle 0) | Opcode (Cycle 1) | Opcode (Cycle 2) | Description                                          |
| -------- | ---------------- | ---------------- | ---------------- | ---------------------------------------------------- |
| `LDM`    | `0010 0000`      | `MMMM MMMM`      | `MMMM MMMM`      | Load data from Memory into accumulator               |
| `STM`    | `0010 0001`      | `MMMM MMMM`      | `MMMM MMMM`      | Store data from accumulator in Memory                |
| `JMP`    | `0010 1000`      | `PPPP PPPP`      | `PPPP PPPP`      | Jump to address                                      |
| `JC0`    | `0010 1001`      | `PPPP PPPP`      | `PPPP PPPP`      | Jump if carry = 0                                    |
| `JC1`    | `0010 1010`      | `PPPP PPPP`      | `PPPP PPPP`      | Jump if carry = 1                                    |
| `JA0`    | `0010 1100`      | `PPPP PPPP`      | `PPPP PPPP`      | Jump if accumulator = 0                              |
| `JA1`    | `0010 1101`      | `PPPP PPPP`      | `PPPP PPPP`      | Jump if accumulator ≠ 0                              |
| `CLL`    | `0011 0000`      | `PPPP PPPP`      | `PPPP PPPP`      | Call/jump to memory address, push PC to SP           |
