# Kone
The goal of this project ('kone' means 'device' or 'gadget' in Finnish) is to design and build a computer using simple logic chips (e.g., from the 74xx series) and other components. Under no circumstances is the use of ICs that resemble a full-blown CPU allowed.

## Start
This project provides a virtual machine (called `kone`), which is written in the C programming language and follows the __kone__ cpu architecture. To build the virtual machine, run:
```bash
make
```
Run an example:
```bash
bin/kone -b bin/calculator_int32.bin
```
Try the `kasm` assembler:
```
bin/kasm -i examples/calculator_int32.kasm -o bin/calculator_int32.bin
```

## Table of contents:

- [Start](#start)
- [Make targets](#make-targets)
- [`kone` usage](#kone-usage)
- [`kasm` usage](#kasm-usage)
- [Examples](#examples)
- [Architecture](#architecture)
    - [General Features](#general-features)
    - [Arithmetic Logic Unit (ALU)](#arithmetic-logic-unit-alu)
    - [Devices](#devices)
- [Instruction set](#instruction-set)
    - [Operations with no argument:](#operations-with-no-argument)
    - [Operations with 'register' argument:](#operations-with-register-argument)
    - [Operations with 'immediate' argument:](#operations-with-immediate-argument)
    - [Operations with 'memory' argument:](#operations-with-memory-argument)
- [`klib` standard library](#klib-standard-library)
    - [`math`](#math)

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

- `calculator_float32`: An interactive 32 bit floating point calculator, the same program as `calculator_int32` below but on IEEE 754 single precision values, built from klib's `disp`, `math/int32`, `math/float32`, `float32_read`, and `float32_write`. Magnitudes run from about 1.2e-38 to 3.4e38 and six significant digits are printed, so `1` followed by `/3` comes out as `0.333333`. A number may carry a decimal point and an exponent (`1.5e-7`) as well as a leading `-`, and a line that starts with a digit or a `.` replaces the accumulator. Dividing by zero would give an infinity, which klib does not carry through its arithmetic, so it prints `ERR` and keeps the accumulator just like the integer version does. Backspace walks back through the number being typed and then through the operator, so a line can always be taken back to the bare prompt. Run it with `bin/kone -b bin/calculator_float32.bin` and type, e.g., `1.5`, then `*2.0`, then `+0.25`.

- `calculator_int32`: An interactive 32 bit signed integer decimal calculator built from klib's `disp`, `math/int32`, `int32_read`, and `int32_write`, covering the range -2147483648 to 2147483647. A line that starts with a digit replaces the accumulator and starts a new calculation, a line that starts with `+`, `-`, `*` or `/` applies that operator and the number behind it to the accumulator. Backspace walks back through the number being typed and then through the operator, so a line can always be taken back to the bare prompt. Run it with `bin/kone -b bin/calculator_int32.bin` and type, e.g., `1000`, then `/8`.

- `count`: Counts up in `R0` in an endless loop, wrapping around at 255, and prints every value to the display as a decimal number, one per row. Run it with `bin/kone -b bin/count.bin`, or add `-vvv` to watch the counter in the register dump as well.

- `display`: Cycles endlessly through the printable ASCII chars (32 to 126) and pushes each one to the display via `R19`/`R18`, which fills the character grid row by row. Run it with `bin/kone -b bin/display.bin`, or with `-t 20` to follow the wrapping.

- `keyboard`: Polls the keyboard set-bit (`R16`), copies every received char to the display and clears the set-bit again to acknowledge it, i.e., it echoes what you type. `R1` counts the chars on the display, so backspace erases the last one and is ignored once there is nothing left to erase. Run it with `bin/kone -b bin/keyboard.bin` and press some keys.

- `pi`: Approximates π by summing the 255 equal edge lengths of a regular polygon into a 16 bit fixed-point perimeter, halving it and printing the digits of the result through repeated subtraction. Run it with `bin/kone -b bin/pi.bin`; it prints `3.1415` and then loops in place.

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

## `klib` standard library

- `disp`: The display helpers `disp_putc`, `disp_bs` and `disp_nl`, which `int32_read` and `int32_write` echo and print through and which a program can just as well use on its own. The kone display has no cursor that a program could read back, so `disp_putc` keeps the column of the next cell at `0x8000`. `disp_bs` steps back onto the previous cell and clears it, and `disp_nl` pads the rest of the row with spaces, since the display has no newline char and wraps on its own once a row is full. Only `R13` is clobbered. This file also lists the whole klib scratch memory map, so that a new routine can tell which addresses are already taken.

- `int32_read`: Reads a decimal number from the keyboard (`R16`/`R17`) and echoes every typed char to the display. The value ends up in `R0`-`R3` and the char that terminated it in `R14`; `R4`-`R11` are preserved, `R12`-`R15` are clobbered. The magnitude is built up digit by digit as `A = A * 10 + digit`, so a `-` before the first digit makes the number negative, `.` and `,` are dropped as thousands separators, and a backspace drops the last digit again. Reading stops at the first char that is none of the above, which is echoed as well and left in `R14` for the caller to inspect (kone maps ENTER to a space). A backspace with nothing left to erase ends the number too, and is the one terminator that is not echoed: it reaches `R14` like any other, so a caller that printed something ahead of the call can take that back itself.

- `int32_write`: Prints the 32 bit signed integer in `R0`-`R3` to the display as a decimal number, prefixed with `=` and followed by a newline; a negative value is printed as `-` plus its magnitude. `R0`-`R3` survive the call, `R4`-`R15` are clobbered. The digits are produced least significant first and pushed onto the stack, which hands them back most significant first for printing.

- `float32_read`: Reads a decimal number from the keyboard (`R16`/`R17`) as an IEEE 754 single precision value and echoes every typed char to the display. The value ends up in `R0`-`R3` and the char that terminated it in `R14`; `R0`-`R15` are clobbered. The accepted shape is `[-] digits [ . digits ] [ (e|E) [+|-] digits ]`, and a `,` is dropped as a thousands separator. The mantissa is built up as an integer, at most nine digits of it, and everything beyond that only counts towards the decimal exponent, which `float32_pow10` then applies in chunks of at most 22, so a typed exponent beyond the range of the format ends up as an infinity or a zero. Reading stops at the first char that does not fit the shape above, which is echoed as well and left in `R14` for the caller to inspect (kone maps ENTER to a space). A backspace undoes the last char whatever it was, the decimal point and the `e` and the leading `-` included: the kind of every accepted char goes onto the stack, so erasing is a matter of popping the last one and reversing what it did. Once there is nothing left to erase a backspace ends the number instead, unechoed, so the caller can undo its own output in turn. Besides `disp` the routine needs both `math/int32` and `math/float32`.

- `float32_write`: Prints the IEEE 754 single precision value in `R0`-`R3` to the display, prefixed with `=` and followed by a newline, clobbering `R0`-`R15`. Six significant digits are printed, trailing zeros are dropped, and the layout follows printf's `%g`: positional while the decimal exponent is between -4 and 5, `d.dddddemdd` outside that range. A zero prints as `0` and an exponent of 255 as `inf` or `nan`. The digits come from `float32_digits`, which also lives in this file and is what the test covers: it scales the magnitude by a power of ten until it lands between 1e5 and 1e6, estimating the decimal exponent from the binary one, and turns that into a six digit integer. Every one of those steps truncates, so the last digit is off by one for about two percent of all values, and six digits are in any case too few to read the value back unchanged, which would take nine.

### `math`

`klib/math/` holds one routine per file, plus the two files below that pull a whole group in. Include a group rather than the single files as soon as a program needs more than one routine from it; the two groups do not depend on each other, so a program pays only for the one it actually uses.

- `math/int32`: The four 32 bit integer routines `int32_add`, `int32_sub`, `int32_mul` and `int32_div` in one include. `klib/int32_write.kasm`, `klib/int32_read.kasm` and `klib/float32_read.kasm` all sit on top of them, so a program that uses any of those three includes this group alongside `klib/disp.kasm` and the reader or writer itself. `float32_write` is the one decimal routine that does not need it.

- `math/float32`: The four IEEE 754 single precision routines `float32_add`, `float32_sub`, `float32_mul` and `float32_div` in one include, together with the three conversions `float32_from_int32`, `float32_to_int32` and `float32_pow10` that are built on them. None of the seven touches `math/int32`: the two places where the integer routines would have been the obvious building block are exactly the two where they turned out to be unusable (see `float32_mul` and `float32_div` below), so the groups really are independent, and `klib/float32_write.kasm` needs nothing but this group and `klib/disp.kasm`.

- `int32_add`: Adds the two 32 bit values in `R0`-`R3` and `R4`-`R7` and returns the sum in `R8`-`R11`, clobbering only `R12`. The carry between the four bytes is propagated by reading the flags register (`R26`) after every `ADD`. The carry out of the MSB is discarded, so the result wraps around; as the operands are two's complement, the same routine covers signed and unsigned addition.

- `int32_sub`: Subtracts `R4`-`R7` from `R0`-`R3` and returns the difference in `R8`-`R11`, clobbering `R12` and `R13`. It is implemented as `A + ~B + 1`, i.e., the second operand is inverted with `NOT` and the carry chain is seeded with a 1. The borrow out of the MSB is discarded, so an underflow wraps around. Negating a value is simply `0 - value`, which is how `int32_read` and `examples/calculator_int32.kasm` apply a leading `-`.

- `int32_mul`: Multiplies the two 32 bit values in `R0`-`R3` and `R4`-`R7` and returns the low 32 bit of the product in `R8`-`R11`; the high half is discarded. It is a shift-and-add loop that adds `A` to the result whenever the lowest bit of `B` is set and then shifts `A` left and `B` right, so it runs until `B` is used up. Because the low half is the same for signed and unsigned operands, it serves both. Note that it consumes its inputs: `R0`-`R7` and `R12` are all clobbered, so copy anything that is still needed before calling it.

- `int32_div`: Divides `R0`-`R3` by `R4`-`R7` and returns the quotient in `R8`-`R11`. Both operands are treated as unsigned, and dividing by zero yields `0xFFFFFFFF` rather than failing, so a caller that wants signed division has to handle the signs itself (see `examples/calculator_int32.kasm`). The routine subtracts the divisor over and over and counts the subtractions, so its run time grows with the quotient. It returns no remainder and destroys `R0`-`R3` (plus `R12` and `R13`) on the way, which is why `int32_write` recovers each digit as `A - (A / 10) * 10`.

- `float32_add`: Adds the two IEEE 754 single precision values in `R0`-`R3` and `R4`-`R7` and returns the sum in `R8`-`R11`, clobbering `R0`-`R7` and `R12`-`R15`. The four bytes are ordered least significant first like the `int32_*` operands, so `R3` and `R7` carry the sign bit and the top seven exponent bits. Both operands are taken apart into sign, 8 bit exponent and 24 bit mantissa (with the implicit leading one put back in) by `float32_unpack`, the mantissa with the smaller exponent is shifted right until the two exponents match, the mantissas are added or, for opposite signs, the smaller one is subtracted from the larger one, and `float32_pack` reassembles the renormalized result. Both mantissas carry an eight bit guard byte below their 24 bits, which the alignment shift fills and the renormalization shifts back in, so that subtracting two close values stays within one unit in the last place. This file also holds `float32_unpack` and `float32_pack`, which every other `float32_*` routine in `math/` uses as well.

- `float32_sub`: Subtracts `R4`-`R7` from `R0`-`R3` and returns the difference in `R8`-`R11`, with the same registers clobbered as `float32_add`. It flips the sign bit of the second operand and leaves everything else to `float32_add`, i.e., subtracting is adding the negated second operand. Because a zero operand is returned as the other operand unchanged, `x - 0` keeps the sign of `x`, while `0 - x` negates `x` as usual.

- `float32_mul`: Multiplies the two values in `R0`-`R3` and `R4`-`R7` and returns the product in `R8`-`R11`, clobbering `R0`-`R7` and `R12`-`R15`. The signs are XORed, the exponents are added and the bias of 127 is taken out once. `int32_mul` is of no use for the mantissas: their product is 48 bit wide and only its top half is wanted, while `int32_mul` keeps the low 32 bit. So the product is accumulated the other way round, shifting a 40 bit accumulator right before every partial product instead of shifting the partial products left, which leaves the top 25 bit of the product plus eight guard bits.

- `float32_div`: Divides `R0`-`R3` by `R4`-`R7` and returns the quotient in `R8`-`R11`, clobbering `R0`-`R7` and `R12`-`R15`. The signs are XORed, the exponents are subtracted and the bias of 127 is put back in once. `int32_div` is of no use for the mantissas either: it divides by repeated subtraction, so a quotient of about 2^24 would cost it 16 million rounds. Instead the quotient is built one bit per round by restoring division, 25 rounds of 'subtract the divisor from the remainder, add it back again if that borrowed, and shift'.

- `float32_from_int32`: Converts the 32 bit signed integer in `R0`-`R3` into the single precision value in `R8`-`R11`, clobbering `R0`-`R3` and `R12`-`R15`. The magnitude is shifted left until its top bit sits in bit 31, which counts the exponent down from 158, and the top 24 bit of that are the mantissa. A value that needs more than 24 bit loses its low bits without rounding; -2147483648 converts exactly, as its magnitude is a power of two.

- `float32_to_int32`: Converts the single precision value in `R0`-`R3` into the 32 bit signed integer in `R8`-`R11`, truncated towards zero, clobbering `R0`-`R7` and `R12`-`R15`. The mantissa is shifted by the unbiased exponent and the sign is applied afterwards. A magnitude below 1 yields 0, and one that does not fit into a signed 32 bit integer saturates to 2147483647 or -2147483648 rather than wrapping, which is also where an operand with exponent 255 ends up.

- `float32_pow10`: Returns 10 raised to the power in `R0` (0 to 38) in `R8`-`R11`, clobbering `R0`-`R7` and `R12`-`R15`. It is built from the six constants 10, 1e2, 1e4, 1e8, 1e16 and 1e32, one per bit of the exponent, so it costs at most three multiplications. Only 1e1 to 1e10 are exact in single precision and every multiplication truncates, so a large power is off by a few units in the last place. This is what `float32_read` and `float32_write` scale with.
