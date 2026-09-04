# Kone
The goal of this project ('kone' means 'device' or 'gadget' in Finnish) is to design and build a computer using simple logic chips (e.g., from the 74xx series) and other components. Under no circumstances is the use of ICs that resemble a full-blown CPU allowed.

## Start
This project provides a virtual machine (called `kone`), which is written in the C programming language and follows the __kone__ CPU architecture. To build the virtual machine, run:
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
    - [`io`](#io)
    - [`math`](#math)
    - [`mem`](#mem)
    - [`str`](#str)

## Make targets
`make` also builds the __kasm__ assembler. Other useful targets are:
 - `make test`: run the whole test suite, i.e. the three groups below one after the other (a failing group does not keep the others from running)
 - `make test-kone`: run only the C unit tests of the virtual machine
 - `make test-kasm`: run only the C unit test of the assembler
 - `make test-klib`: run only the `klib` tests, i.e. one kasm program per routine, run on the vm
 - `make debug`: build with debugging symbols and no optimization
 - `make kasm`: build only the assembler
 - `make install`: install `kone` and `kasm` to `$(HOME)/.local/bin` (Note that `$(HOME)/.local/bin` needs to be in your `$PATH` variable to enable the `kone` and `kasm` commands. Override default target path with `PREFIX=...`)

A C test is `tests/test_<module>.c` and is picked up by the wildcard, no makefile edit needed. A `klib` test is a kasm program in `tests/klib/` that prints one `PASS:<case>` or `FAIL:<case>` row per case and then a summary row, `ALL PASS` or `<n> FAILED`, and halts; the harness runs it on the vm, waits up to 20 s for that summary and reads the last complete display frame. A `test_<name>.in` beside it is piped in as keystrokes, and a `test_<name>.expect` lists display rows that have to match exactly, which is how output that cannot be read back from inside the vm is checked.

## `kone` usage
The virtual machine loads a boot file into memory and runs it until it is interrupted (`Ctrl-C`): A kone program never halts on its own. It takes the following arguments:
 - `-b BOOTFILE`, `--bootfile BOOTFILE`: path to the binary boot file that is loaded into memory before execution starts. This argument is required and has no default.
 - `-t USEC`, `--clockspeed USEC`: number of microseconds to sleep between clock cycles (default: `0`, run as fast as possible). A value like `-t 100000` is useful for watching an example step through its instructions.
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
Every `examples/*.kasm` is built by `make` into `bin/<name>.bin` and run with `bin/kone -b bin/<name>.bin`.

### `basic`
A BASIC interpreter with the keyboard as its terminal and the display as its screen, built from klib's `io/disp`, `math` (both groups), `io/int32_write`, `io/float32_write`, `io/float32_read`, `mem` and `str`. It prints `READY.` and a `>` prompt and takes one line at a time: a line behind a line number goes into the program, a bare line number deletes it again, anything else runs at once. Variables are the single letters `A` - `Z` and the program holds 32 lines of 40 bytes. Every value is a single precision float, so `LET A = 1 / 3` then `PRINT A` gives `0.333333` while a whole value prints without a decimal point; literals may carry a decimal point and an exponent (`1.5e-7`, `-.5`). A line ends with ENTER (ASCII 10, see [Devices](#devices)) and is parsed only once it is complete, so backspace works anywhere in it, down to the prompt.

The three commands, which are typed without a line number and act at once:

| Command | Description |
| --- | --- |
| `RUN` | runs the stored program from the lowest line number upward |
| `LIST` | prints the stored program in line number order, as it was typed |
| `CLEAR` | drops every stored line and every loop, and prints `READY.` |

The statements, which are stored behind a line number. A `<term>` is a literal, a variable, `ABS(<var>)` (its magnitude) or `INT(<var>)` (its floor, so `INT(-2.5)` is `-3`):

| Statement | Description |
| --- | --- |
| `LET <var> = <term> [<op> <term>]...` | works out the expression and assigns it; `<op>` is `+`, `-`, `*`, `/` or `MOD` |
| `PRINT "<text>"` | prints a string literal, at most 29 chars |
| `PRINT <term>` | prints a value with six significant digits |
| `PRINT "<text>"; <term>` | prints both on one row |
| `IF <term> <op> <term> THEN <line>` | jumps when the comparison holds; `<op>` is `=`, `<` or `>` |
| `GOTO <line>` | jumps to that line |
| `GOSUB <line>` | calls that line; `RETURN` comes back to the line behind the `GOSUB` |
| `RETURN` | returns from the innermost `GOSUB` |
| `FOR <var> = <term> TO <term>` | counts `<var>` up from the first term, in steps of one |
| `NEXT <var>` | counts that loop on and goes back into it unless it has passed the limit |
| `INPUT <var>` | prints a `? ` prompt and reads a number from the keyboard into `<var>` |
| `CLS` | clears the display and puts the cursor back in its top left corner |
| `REM <text>` | a comment, at most 36 chars; it does nothing when it is run |
| `END` | stops the run and prints `DONE.` |

A `LET` expression chains up to five terms: `*`, `/` and `MOD` are worked out first, left to right, then `+` and `-`, also left to right, so `2 + 3 * 4` is `14` and `10 - 2 * 3` is `4`. There is no bracketing, and five terms is what the 40 byte line record holds; a sixth is a syntax error. `LET` is also the only statement that takes an operator at all: the rest take a bare `<term>`, and anything behind one is ignored rather than reported, so `PRINT A * B` prints `A`. Type
```
10 FOR I = 1 TO 5
20 LET S = I * I
30 PRINT "SQUARE: "; S
40 NEXT I
50 END
RUN
```
which prints the five squares and `DONE.`. Errors are reported as `?SYNTAX ERROR`, `?UNDEF'D LINE`, `?DIVISION BY ZERO`, `?PROGRAM FULL`, `?NEXT WITHOUT FOR`, `?RETURN WITHOUT GOSUB`, `?FOR NESTING` and `?GOSUB NESTING`.

What it deliberately leaves out, and why:

| Not supported | Reason |
| --- | --- |
| string variables `A$`, `LEFT$`, `MID$`, `CHR$` | they need a heap and garbage collection; there are 26 fixed four byte cells |
| `DIM` and arrays | the same |
| `INPUT` of several variables, `INPUT "prompt"; var` | the record holds one variable |
| multi-statement lines with `:` | a slot holds one statement and the run loop steps line by line |
| `ON ... GOTO`, `DEF FN`, `READ`/`DATA`/`RESTORE`, `STEP`, `AND`/`OR`/`NOT` | only `LET` takes an expression, and it has no bracketing |
| `TAB()`, `SPC()` | feasible in themselves, but `PRINT` would need an ordered item list where the record holds one string and one term |

`GOSUB` nests eight deep and `FOR` four, bounded by their fixed stacks. `ABS()` and `INT()` are the only functions, and both take a variable rather than an expression.

Every indexed access into the 32 slots goes through klib's `mem_peek` and `mem_poke`, since the ISA has no register indirect addressing; `examples/basic.kasm` maps the layout at the top. Numbers are printed with `float32_puts` but read out of a stored line by the interpreter itself, as klib's readers poll the keyboard and a line already typed cannot be fed back into them; `INPUT` is the one statement that does reach the keyboard, through `float32_read`. `CLS` calls `disp_cls`, which pads the whole grid because the display clears itself only on the last cell, so a clear takes a visible moment.

### `calculator_float32`
An interactive 32 bit floating point calculator, the same program as `calculator_int32` below but on IEEE 754 single precision values, built from klib's `io/disp`, `math/int32`, `math/float32`, `io/float32_read`, and `io/float32_write`. Magnitudes run from about 1.2e-38 to 3.4e38 and six significant digits are printed, so `1` followed by `/3` comes out as `0.333333`. A number may carry a decimal point and an exponent (`1.5e-7`) as well as a leading `-`, and a line that starts with a digit or a `.` replaces the accumulator. Dividing by zero would give an infinity, which klib does not carry through its arithmetic, so it prints `ERR` and keeps the accumulator just like the integer version does. Backspace walks back through the number being typed and then through the operator, so a line can always be taken back to the bare prompt. Type, e.g., `1.5`, then `*2.0`, then `+0.25`.

### `calculator_int32`
An interactive 32 bit signed integer decimal calculator built from klib's `io/disp`, `math/int32`, `io/int32_read`, and `io/int32_write`, covering the range -2147483648 to 2147483647. A line that starts with a digit replaces the accumulator and starts a new calculation, a line that starts with `+`, `-`, `*` or `/` applies that operator and the number behind it to the accumulator. A leading `-` is always the operator and never a sign, so a negative accumulator is entered as `0` and then `-5`. Backspace walks back through the number being typed and then through the operator, so a line can always be taken back to the bare prompt. Type, e.g., `1000`, then `/8`.

### `count`
Counts up in `R0`-`R3` in an endless loop and prints every value to the display as a decimal number, one per row. Both halves of the loop are klib routines, `int32_add` for the counting and `int32_write` for the printing, which the example pulls in through the two class includes `klib/math.kasm` and `klib/io.kasm`; every row therefore carries the `=` that `int32_write` always prefixes. The counter is a 32 bit signed integer, so it runs up to 2147483647 and then wraps around to -2147483648. Add `-vvv` to watch the counter in the register dump as well.

### `display`
Cycles endlessly through the printable ASCII chars (32 to 126) and pushes each one to the display via `R19`/`R18`, which fills the character grid row by row. It waits for the display to clear `R18` again before it pushes the next char, the same handshake `disp_putc` does, since the display runs beside the cpu and takes a char only every so often. Add `-t 20000` to follow the wrapping.

### `hello`
Prints `Hello, World!` and then loops forever. The smallest program here and the one to read first: it does nothing but call `disp_putc` from klib once per char, spelled out as ASCII codes because kasm cannot emit data and so has no string constant to point at.

### `keyboard`
Polls the keyboard set-bit (`R16`), copies every received char to the display and clears the set-bit again to acknowledge it, i.e., it echoes what you type. `R1` counts the chars on the display, so backspace erases the last one and is ignored once there is nothing left to erase. Press some keys.

### `pi`
Approximates π the way Archimedes did, by doubling the corner count of a polygon inscribed in the unit circle: the hexagon's side is the radius, and a polygon with the side `s` doubles into one with the side `s / sqrt(2 + 2 * sqrt(1 - (s/2)^2))`, i.e., Pythagoras on the two right triangles over half an edge. Half the perimeter approaches π and is printed after every doubling, from the 12-gon (`=3.10583`) up to the 6144-gon (`=3.14159`). It is built from klib's `math/float32` group, `io/disp` and `io/float32_write`, and does its own square roots by Newton's iteration, since klib has none. Six significant digits are all that single precision carries and all that `float32_write` prints, and the polygons settle onto them by the 1536-gon. It prints ten lines and then loops in place.

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
- __Keyboard:__ pressed keys are polled in the background and, once received, exposed via `R16` (set flag) and `R17` (char, ASCII 32-255, plus backspace: 8 or 127, depending on the terminal, and ENTER as ASCII 10, whether the terminal sends LF or CR); every other char is reported as a space. kasm programs should clear the set flag after reading to acknowledge the char (see `examples/keyboard.kasm`).
- __Display:__ writing an ASCII char (32-126) to `R19` and setting `R18` pushes it to the next cell of a 40x24 character grid, wrapping to a new (cleared) row once the current row is full and starting over on a cleared display once the last row is full (see `examples/display.kasm`). Writing a backspace (8) instead steps back onto the previous cell and clears it, which is how a program erases what it printed; at the start of a row it does nothing. The display clears `R18` once it has taken the char, and it does that on its own schedule rather than per instruction, so a program has to wait for `R18` to go back to 0 before it pushes the next char or the char is overwritten before the display ever sees it.

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

`klib/` is split into the four classes below, one routine or one closely related group per file, with `klib/io.kasm`, `klib/math.kasm`, `klib/mem.kasm` and `klib/str.kasm` next to the folders to pull in a whole class at once. Every routine documents its own calling convention (in, out, clobbered registers) at the top of its file; the lists here only say what each one is for. Note that an include is not idempotent and kasm has no include guards, i.e., a file that is reached along two paths is quietly assembled twice, taking up the memory twice over and resolving every call to it to the second copy, so include either a class file or the single files below it, never both.

### `io`

The routines that talk to the two devices. `disp` is the one every other file here needs, and the readers and writers sit on the `math` groups as well, so `klib/io.kasm` only ever works together with `klib/math.kasm`.

- `disp`: the display helpers `disp_putc`, `disp_bs`, `disp_nl` and `disp_cls` that every other `io` routine prints through. The kone display has no cursor a program could read back, so these keep the column at `0x8000` and the row at `0x8022`; `disp_cls` clears by padding the grid, as the display only clears itself on its last cell. This file also documents the whole klib scratch memory map.
- `int32_read`: reads a decimal number from the keyboard into `R0`-`R3` and echoes it, taking a leading `-`, thousands separators and backspace; the char that ended the number is left in `R14`.
- `int32_write`: prints the 32 bit signed integer in `R0`-`R3` as a decimal number, prefixed with `=` and followed by a newline. `int32_puts`, which prints the bare digits without either of them, lives here as well and is what a program that prints a number of its own wants.
- `float32_read`: reads `[-] digits [ . digits ] [ (e|E) [+|-] digits ]` from the keyboard into `R0`-`R3` as a single precision value; backspace undoes any typed char, the decimal point and the `e` included.
- `float32_write`: prints the single precision value in `R0`-`R3` with six significant digits, in the layout of printf's `%g`, prefixed with `=` and followed by a newline. `float32_puts` prints it without either of them, and the digit generator `float32_digits` that both sit on lives here as well and is what the test covers.

### `math`

Two independent groups, `math/int32.kasm` and `math/float32.kasm`, which `klib/math.kasm` pulls in together. Include a group rather than the single files as soon as a program needs more than one routine from it, and only the group it needs: the two do not depend on each other.

- `int32_add`, `int32_sub`: 32 bit two's complement addition and subtraction of `R0`-`R3` and `R4`-`R7` into `R8`-`R11`. Carry and borrow out of the MSB are discarded, so both wrap around and serve signed and unsigned operands alike.
- `int32_mul`: shift-and-add multiplication that keeps the low 32 bit of the product, which is the same for signed and unsigned operands. It consumes both of them.
- `int32_cmp`: compares two 32 bit signed integers and says which is the larger one. Two values of the same sign are told apart by the sign of their difference, which cannot overflow in that case, two of different signs by the sign of the first alone.
- `int32_div`: unsigned division, yielding `0xFFFFFFFF` rather than failing when the divisor is zero. It subtracts the divisor over and over, so its run time grows with the quotient: a nine digit quotient costs a few hundred million rounds.
- `float32_add`, `float32_sub`: IEEE 754 single precision addition and subtraction, with a guard byte below both mantissas so that subtracting two close values stays within one unit in the last place. This file also holds `float32_unpack` and `float32_pack`, which every other float32 routine uses.
- `float32_mul`, `float32_div`: single precision multiplication and division. Neither can build on the integer routines: the mantissa product is 48 bit wide and only its top half is wanted, while `int32_mul` keeps the low 32 bit, and `int32_div` would need 16 million rounds for a 24 bit quotient, so the quotient is built one bit per round by restoring division.
- `float32_from_int32`, `float32_to_int32`: the conversions in both directions. A value that needs more than 24 bit loses its low bits, and a magnitude that does not fit into a signed 32 bit integer saturates rather than wrapping.
- `float32_mod`: the remainder of a division, `A - B * trunc(A / B)`, which truncates towards zero and so keeps the sign of `A`: `-7 MOD 3` is `-1`. It sits on `float32_div`, `float32_mul`, `float32_sub` and the two conversions, so it needs the whole group.
- `float32_cmp`: compares two single precision values and says which is the larger one. It compares the bit patterns rather than the values, which needs no arithmetic: the magnitude bits grow with the value, so two of the same sign are ordered by them and two of different signs by the sign alone. Both zeros count as equal.
- `float32_pow10`: 10 raised to a power of 0 to 38, built from the six constants 10, 1e2, 1e4, 1e8, 1e16 and 1e32, one per bit of the exponent. This is what `float32_read` and `float32_write` scale with.

Every float32 routine truncates towards zero, flushes an exponent below 1 to a signed zero (subnormals are not produced) and treats an operand with exponent 255 as an ordinary number, so infinities and NaNs are not carried through the arithmetic.

### `mem`

The kone ISA has no register indirect addressing: `LDM` and `STM` take an absolute address and nothing can point them at a computed one. These routines fill that gap by patching the address into an `LDM`/`STM` that they write into scratch memory and then call, so a program can walk a table at run time.

- `mem_peek`, `mem_poke`: read and write the byte at the address in `R12`/`R13`.
- `mem_copy`: copies a block of up to 255 bytes from one address to another through the two above.

### `str`

- `str_eq`: compares two null terminated strings and returns 0 or 1 in `R0`. It reads them through `mem_peek`, so `klib/mem.kasm` has to be included alongside `klib/str.kasm`.
