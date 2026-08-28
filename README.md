# Kone
The goal of this project ('kone' means 'device' or 'gadget' in Finnish) is to design and build a computer using simple logic chips (e.g., from the 74xx series) and other components. Under no circumstances is the use of ICs that resemble a full-blown CPU allowed.

## Start
This project provides a virtual machine (called `kone`), which is written in the C programming language and follows the __kone__ cpu architecture. To build the virtual machine, run:
```bash
make
```
Run an example:
```bash
bin/kone -b bin/calculator.bin
```
Try the `kasm` assembler:
```
bin/kasm -i examples/calculator.kasm -o bin/calculator.bin
```

## Table of contents:

- [Start](#start)
- [Make targets](#make-targets)
- [`kone` usage](#kone-usage)
- [`kasm` usage](#kasm-usage)
- [Examples](#examples)
- [`klib` standard library](#klib-standard-library)
    - [`math`](#math)
- [Architecture](#architecture)
    - [General Features](#general-features)
    - [Arithmetic Logic Unit (ALU)](#arithmetic-logic-unit-alu)
    - [Devices](#devices)
- [Instruction set](#instruction-set)
    - [Operations with no argument:](#operations-with-no-argument)
    - [Operations with 'register' argument:](#operations-with-register-argument)
    - [Operations with 'immediate' argument:](#operations-with-immediate-argument)
    - [Operations with 'memory' argument:](#operations-with-memory-argument)

## Make targets
`make` also builds the __kasm__ assembler. Other useful targets are:
 - `make test`: run the test suite
 - `make debug`: build with debugging symbols and no optimization
 - `make kasm`: build only the assembler
 - `make install`: install `kone` and `kasm` to `$(HOME)/.local/bin` (Note that `$(HOME)/.local/bin` needs to be in your `$PATH` variable to enable the `kone` and `kasm` commands. Override default target path with `PREFIX=...`)

## `kone` usage
The virtual machine loads a boot file into memory and runs it until it is interrupted (`Ctrl-C`): A kone program never halts on its own. It takes the following arguments:
 - `-b BOOTFILE`, `--bootfile BOOTFILE`: path to the binary boot file that is loaded into memory before execution starts. This argument is required and has no default.
 - `-t MSEC`, `--clockspeed MSEC`: number of milliseconds to sleep between clock cycles (default: `0`, run as fast as possible). A value like `-t 100` is useful for watching an example step through its instructions.
 - `-v [0-3]`, `--verbose [0-3]`: verbosity level of the output (default: `0`). The levels are cumulative:
    - `0`: only the 40x24 display
    - `1`: additionally the cycle counter and the program counter, printed as `[ cycle : PC ]`
    - `2`: additionally the instruction that was just decoded and executed
    - `3`: additionally the full CPU state (`R0`-`R21`, stack pointer, input buffer, accumulator, flags, instruction register and program counter)

   The level can be stacked (`-vvv`), used bare to raise it by one (`-v`, `--verbose`), or set explicitly (`-v2`, `-v 2`, `--verbose=2`, `--verbose 2`).
 - `-l`, `--log`: enables continuous logging mode (default: disabled), where the state is written out at every clock cycle instead of being redrawn in the interactive display. At `-v3` that amounts to a few hundred MB per second, so redirect it to a file with room to spare.
 - `-h`, `--help`: prints the help page and exits (default: disabled).

## `kasm` usage
The assembler translates a kasm assembly source file into the flat binary that `kone` boots:
 - `-i FILE`, `--input FILE`: input assembly source file (`.kasm`). This argument is required.
 - `-o FILE`, `--output FILE`: output binary file (`.bin`). This argument is required.
 - `-h`, `--help`: prints the help page and exits.

The assembler is deliberately minimal, which is worth keeping in mind when writing kasm programs. `.include "file"` (resolved relative to the including file) is the only directive. There is no `.equ`, so every operand has to be spelled out as a literal (decimal, `0x`, `0b` or `0o`) or as a label. There is no way to emit or reserve data, so constants have to be built with `LDI` and scratch memory has to be addressed by hand with `LDM`/`STM`. Labels are only accepted as the operand of a control-flow instruction (`JMP`, `JC0`, `JC1`, `JA0`, `JA1`, `CLL`), so passing one to `LDM` or `STM` is an error. `.include` has no include guards: Only circular includes are caught, so a file that is pulled in twice is assembled twice and its labels silently resolve to the second copy. 

## Examples

- `calculator`: An interactive 32 bit signed decimal calculator built from klib's `math`, `int32_read`, and `int32_write`, covering the range -2147483648 to 2147483647. A line that starts with a digit replaces the accumulator and starts a new calculation, a line that starts with `+`, `-`, `*` or `/` applies that operator and the number behind it to the accumulator. Run it with `bin/kone -b bin/calculator.bin` and type, e.g., `1000`, then `/8`.

- `count`: Counts up in `R0` in an endless loop, wrapping around at 255, and prints every value to the display as a decimal number, one per row. Run it with `bin/kone -b bin/count.bin`, or add `-vvv` to watch the counter in the register dump as well.

- `display`: Cycles endlessly through the printable ASCII chars (32 to 126) and pushes each one to the display via `R19`/`R18`, which fills the character grid row by row. Run it with `bin/kone -b bin/display.bin`, or with `-t 20` to follow the wrapping.

- `keyboard`: Polls the keyboard set-bit (`R16`), copies every received char to the display and clears the set-bit again to acknowledge it, i.e., it echoes what you type. `R1` counts the chars on the display, so backspace erases the last one and is ignored once there is nothing left to erase. Run it with `bin/kone -b bin/keyboard.bin` and press some keys.

- `pi`: Approximates π by summing the 255 equal edge lengths of a regular polygon into a 16 bit fixed-point perimeter, halving it and printing the digits of the result through repeated subtraction. Run it with `bin/kone -b bin/pi.bin`; it prints `3.1415` and then loops in place.

## `klib` standard library

- `int32_read`: Reads a decimal number from the keyboard (`R16`/`R17`) and echoes every typed char to the display. The value ends up in `R0`-`R3` and the char that terminated it in `R14`; `R4`-`R11` are preserved, `R12`-`R15` are clobbered. The magnitude is built up digit by digit as `A = A * 10 + digit`, so a `-` before the first digit makes the number negative, `.` and `,` are dropped as thousands separators, and a backspace drops the last digit again. Reading stops at the first char that is none of the above, which is echoed as well and left in `R14` for the caller to inspect (kone maps ENTER to a space).

- `int32_write`: Prints the 32 bit signed integer in `R0`-`R3` to the display as a decimal number, prefixed with `=` and followed by a newline; a negative value is printed as `-` plus its magnitude. `R0`-`R3` survive the call, `R4`-`R15` are clobbered. The digits are produced least significant first and pushed onto the stack, which hands them back most significant first for printing. This file also holds the display helpers `disp_putc`, `disp_bs` and `disp_nl`, so it has to be assembled even by a program that only wants to print a char.

### `math`

- `int32_add`: Adds the two 32 bit values in `R0`-`R3` and `R4`-`R7` and returns the sum in `R8`-`R11`, clobbering only `R12`. The carry between the four bytes is propagated by reading the flags register (`R26`) after every `ADD`. The carry out of the MSB is discarded, so the result wraps around; as the operands are two's complement, the same routine covers signed and unsigned addition.

- `int32_sub`: Subtracts `R4`-`R7` from `R0`-`R3` and returns the difference in `R8`-`R11`, clobbering `R12` and `R13`. It is implemented as `A + ~B + 1`, i.e., the second operand is inverted with `NOT` and the carry chain is seeded with a 1. The borrow out of the MSB is discarded, so an underflow wraps around. Negating a value is simply `0 - value`, which is how `int32_read` and `examples/calculator.kasm` apply a leading `-`.

- `int32_mul`: Multiplies the two 32 bit values in `R0`-`R3` and `R4`-`R7` and returns the low 32 bit of the product in `R8`-`R11`; the high half is discarded. It is a shift-and-add loop that adds `A` to the result whenever the lowest bit of `B` is set and then shifts `A` left and `B` right, so it runs until `B` is used up. Because the low half is the same for signed and unsigned operands, it serves both. Note that it consumes its inputs: `R0`-`R7` and `R12` are all clobbered, so copy anything that is still needed before calling it.

- `int32_div`: Divides `R0`-`R3` by `R4`-`R7` and returns the quotient in `R8`-`R11`. Both operands are treated as unsigned, and dividing by zero yields `0xFFFFFFFF` rather than failing, so a caller that wants signed division has to handle the signs itself (see `examples/calculator.kasm`). The routine subtracts the divisor over and over and counts the subtractions, so its run time grows with the quotient. It returns no remainder and destroys `R0`-`R3` (plus `R12` and `R13`) on the way, which is why `int32_write` recovers each digit as `A - (A / 10) * 10`.

## Architecture

### General Features
- Data bus: 8 bit
- Registers: 32:
    - `R0`-`R15`: Custom registers
    - `R16`-`R19`: Keyboard/Display device registers (see "Devices" below)
    - `R20`-`R21`: Unused
    - `R22`-`R23`: `SP[2]`, stack pointer (data structure: FILO)
    - `R24`: `I`, ALU input (left)
    - `R25`: `A`, accumulator
        - `F0`: carry flag
    - `R26`: `F`, flags (`F7`, `F6`, `F5`, `F4`, `F3`, `F2`, `F1`, `F0`)
    - `R27`-`R29`: `IR[3]`, instruction register
    - `R30`-`R31`: `PC[2]`, program counter
- RAM: 64 KiB (16 bit addresses)

### Arithmetic Logic Unit (ALU)
- Input buffers:
    - `I` (input left -> `R24`)
- Output buffers:
    - `A` (accumulator -> `R25`)
    - `C` (carry -> `F0`)
- Note that the input buffer (i.e., `I`) is there to prevent simultaneous read/write operations on the output accumulator (i.e., `A`). E.g., before performing the add operation (i.e., `ADD`), A is first written to I, which is connected to the left ALU input, while the selected operand register is directly connected to the right ALU input.

### Devices
- __Keyboard:__ pressed keys are polled in the background and, once received, exposed via `R16` (set flag) and `R17` (char, ASCII 32-255, plus backspace: 8 or 127, depending on the terminal); every other char is reported as a space. kasm programs should clear the set flag after reading to acknowledge the char (see `examples/keyboard.kasm`).
- __Display:__ writing an ASCII char (32-126) to `R19` and setting `R18` pushes it to the next cell of a 40x24 character grid, wrapping to a new (cleared) row once the current row is full and starting over on a cleared display once the last row is full (see `examples/display.kasm`). Writing a backspace (8) instead steps back onto the previous cell and clears it, which is how a program erases what it printed; at the start of a row it does nothing.

## Instruction set
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
