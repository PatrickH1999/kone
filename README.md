# Kone
The goal of this project ('kone' means 'device' or 'gadget' in Finnish) is to design and build a computer using simple logic chips (e.g., from the 74xx series) and other components. Under no circumstances is the use of ICs that resemble a full-blown CPU allowed.

The architecture, the instruction set, the devices, the assembler, `klib`, the examples and the BASIC interpreter are documented in the **[wiki](https://github.com/PatrickH1999/kone/wiki)**.

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

## Folder structure
- __bin__: `kone`, `kasm`, `kone` binaries (*.bin), tests (test_*)
- __examples__: `kasm` examples
- __kicad__: the machine as six stackable KiCad boards, see [`kicad/README.md`](kicad/README.md). Nothing has been built yet, and the `memory` board carries a known defect, so hold that one back when ordering.
- __klib__: `kasm` standard library
- __logisim__: the machine as Logisim Evolution circuits from 74xx chips, see [`logisim/README.md`](logisim/README.md)
- __src__: source code
    - __kone__: the virtual machine
    - __kasm__: the assembler
- __tests__: unit tests of the virtual machine, the assembler and `klib`
- __tools__: development tools

## Make targets
`make` also builds the __kasm__ assembler and every example. Other useful targets are:
 - `make test`: run the whole test suite, i.e. the three groups below one after the other (a failing group does not keep the others from running)
 - `make test-kone`: run only the C unit tests of the virtual machine
 - `make test-kasm`: run only the C unit test of the assembler
 - `make test-klib`: run only the `klib` tests, i.e. one kasm program per routine, run on the vm
 - `make debug`: build with debugging symbols and no optimization
 - `make kasm`: build only the assembler
 - `make logisim_<target>`: anything in `logisim/`, forwarded to its own makefile
 - `make kicad_<target>`: anything in `kicad/`, forwarded to its own makefile
 - `make format`: clang-format over the C sources, `ruff format` (or `black`) over the python; a missing formatter is reported rather than fatal
 - `make hooks`: install the pre-commit hook, which runs `make format` and re-stages what it changed
 - `make install`: install `kone` and `kasm` to `$(HOME)/.local/bin` (Note that `$(HOME)/.local/bin` needs to be in your `$PATH` variable to enable the `kone` and `kasm` commands. Override default target path with `PREFIX=...`)

The full list and how a test is written are on the wiki's [Building](https://github.com/PatrickH1999/kone/wiki/Building) page.

## `kone` usage
The virtual machine loads a boot file into memory and runs it until it is interrupted (`Ctrl-C`): A kone program never halts on its own. It takes the following arguments:
 - `-b BOOTFILE`, `--bootfile BOOTFILE`: path to the binary boot file that is loaded into memory before execution starts. This argument is required and has no default.
 - `-t USEC`, `--clockspeed USEC`: number of microseconds to sleep between clock cycles (default: `0`, run as fast as possible). A value like `-t 100000` is useful for watching an example step through its instructions.
 - `-v [0-3]`, `--verbose [0-3]`: verbosity level of the output (default: `0`). The levels are cumulative:
    - `0`: only the 20x4 display
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

The language and its limits are on the wiki's [Assembler](https://github.com/PatrickH1999/kone/wiki/Assembler) page.
