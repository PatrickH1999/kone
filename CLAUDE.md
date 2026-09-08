# kone

`kone` ("device" in Finnish) is a VM in C implementing a custom 8-bit CPU architecture,
written so the machine can later be built from 74xx-series logic chips — no IC that
resembles a full CPU is allowed, so every ISA decision has to stay buildable from gates.
`kasm` is its two-pass assembler; `klib/` is an assembly standard library; `examples/` are
kasm programs run on the VM. `README.md` is the canonical user-facing spec (ISA tables,
device contract, klib index) — keep it in sync with any change to those.

## Hard rules

- **Never run git.** No `add`, `commit`, `push`, `tag`, `checkout`, `merge`, `stash`.
  The author does all of it. Report what changed and stop.
- **`make test` must pass after every change.** All three groups.
- No dead code, no commented-out code, no leftover debug prints.

## Build / run

```
make            # bin/kone, bin/kasm, all examples
make test       # test-kone + test-kasm + test-klib (a failing group does not stop the others)
make format     # clang-format + ruff (or black), run before finishing
make hooks      # install the pre-commit hook that runs make format
make logisim_<t>    # forwarded to logisim/Makefile, which owns circ, cpu, test,
                    # kicad, route, gerbers, clean (see logisim/README.md)
bin/kone -b bin/hello.bin [-t USEC] [-v0..3] [-l]
bin/kasm -i examples/x.kasm -o bin/x.bin
```

`make clean` also deletes `$(PREFIX)/bin/{kone,kasm}`, the generated `.circ` files and
`logisim/kicad/` (`make logisim_clean` for only those, and it leaves a hand-drawn circuit
alone; the routing goes with them and has to be recomputed); `make debug`
depends on `clean`, so it uninstalls as a side effect. `make -n clean` is not a dry run
either — the recursive `$(MAKE) -C src/kasm clean` runs for real and takes `bin/kasm` with
it. kasm emits no depfiles, so any klib edit rebuilds every
example — intended.

## Running a program by hand

A kone program never halts, so `timeout` is what ends a run, and a frame scraper only
emits once its stdin hits EOF. Take the **last complete** frame: split the output on
`\x1b[3J\x1b[H\x1b[2J` and drop the trailing partial one.

```
( cat prog.txt; sleep 14; printf 'RUN\n'; sleep 6; printf '42\n'; sleep 12 ) \
    | timeout -k 2 45 bin/kone -b bin/basic.bin | python3 lastframe.py
```

Two things make this harder than it looks, and both cost real debugging time:

- **The keyboard reads one byte per poll at 20 Hz**, i.e. 20 chars/s. A 240-byte program
  takes ~12 s just to type in; size every timeout from that, not from the VM's speed.
- **Pipe writes queue ahead of the reader.** `( cat prog; sleep 5; printf '42\n' )` does
  *not* deliver `42` five seconds after the program is typed — the shell dumps everything
  into the pipe at once and the VM drains it at 20 chars/s. A sleep only delays delivery if
  it exceeds the drain time of everything already queued. Getting this wrong silently feeds
  input to the wrong part of the program.

Input that arrives while the program is not polling `R16` is **lost**, not buffered (see
Device protocols), so keystrokes meant for an `INPUT` prompt have to land after the program
reaches it.

The scraper is not in the repo; it is four lines:

```python
import sys
frames = sys.stdin.buffer.read().decode('utf-8', 'replace').split('\x1b[3J\x1b[H\x1b[2J')
last = next(f for f in reversed(frames[:-1]) if f.strip())   # [:-1] drops the partial one
print('\n'.join(l.rstrip() for l in last.splitlines() if l.strip()))
```

## Layout

| Path | Contents |
| --- | --- |
| `src/` | VM: `cpu_*`, `alu_*`, `display_*`, `keyboard_*`, `args`, `utility`, `kone.c` |
| `src/kasm/` | assembler: `isa`, `symtab`, `assembler`, `kasm.c` (own Makefile) |
| `klib/<class>/` | one routine per file; `klib/<class>.kasm` umbrella `.include`s them |
| `examples/` | `*.kasm` → `bin/*.bin`, auto-discovered by wildcard |
| `tests/` | C unit tests, one `test_<module>.{c,h}` per `src/<module>.c` |
| `tests/klib/` | klib tests as kasm programs, plus optional `.in` / `.expect` |
| `logisim/` | the machine as hardware: own `Makefile` and `README.md`, the generator in `python/`, the harness in `java/` |

| `tools/` | `bin2bits.sh` and `hooks/pre-commit`, which `make hooks` installs |

A new klib file must be `.include`d from its group file (`klib/math/int32.kasm`,
`klib/math/float32.kasm`, `klib/io.kasm`, `klib/mem.kasm`, `klib/str.kasm`) or it is
never assembled. New C module → add `tests/test_<module>.{c,h}`; both are picked up by
wildcard, no Makefile edit needed.

## Style

**C** — `make format` (clang-format: LLVM base, indent 4, column 80, `PointerAlignment:
Right`, `SortIncludes: false`). Beyond what it decides, follow Google C++ style. Observed:
`module_verb()` function names, `CamelCase` typedef'd structs, `UPPER_SNAKE` macros, own
header first then system then project includes, `const` on value parameters, trailing
underscore to dodge keywords (`char_`).

**Python** — `make format` runs `ruff format` (or `black`) over `logisim/**/*.py` with the
line length in `pyproject.toml`, 80, the same column limit `.clang-format` uses. Neither tool is a
build dependency: without one, `make format` says so and leaves the files alone.

**Commits** — `make hooks` installs `tools/hooks/pre-commit`, which runs `make format` and
re-stages what it changed, so formatting never lands in a later commit. It refuses to run
when a file is both staged and modified in the tree, because formatting would sweep the
unstaged half into the commit.

**Comments** — explain only what the code does not. Do not restate an instruction, a
signature, or a name.

**Where a fact belongs** — say it once, in one of three places:

- `README.md`: the user- and contributor-facing what and why — language, usage, per-example
  description, klib index, how a test is written and run.
- a code header: the calling convention, the memory map, any non-obvious mechanism.
- this file: working conventions and the traps that cost time, not reference material.

A rule shared by a group is stated once in `README.md` and pointed at from the files, as the
float32 routines do, rather than repeated per file. This file stays on `development` and is
not merged into `release`, so anything a reader of the released repo needs — the klib test
protocol, for one — belongs in `README.md`, not only here.

**kasm** — labels at column 0, instructions indented 4, inline `//` comments starting at
column 21. Entry label `routine`, internal labels `routine__sub` (double underscore).
File header at most 3–4 lines of prose; if `README.md` already describes the routine, omit
the prose entirely. A memory map or record layout is exempt — it has no other home, which
is why `examples/basic.kasm` and `klib/io/disp.kasm` carry long ones. Keep the `in: / out: / clobbers:` block on klib routines — it is
the calling contract, not prose.

Program skeleton (`JMP main` must be first so address 0 is the entry point):

```
    JMP main

.include "../klib/io/disp.kasm"

main:
    ...
prog__halt:
    JMP prog__halt      // a kone program never halts on its own
```

Includes go **at the top**, right after `JMP main` — deliberate (commit 0220967).

## ISA quirks

- 8-bit data, 16-bit addresses, 64 KiB RAM, 32 registers. `R0`-`R15` general, `R16`-`R19`
  devices, `R20`-`R21` unused, `R22/23` SP, `R24` I, `R25` A, `R26` F, `R27`-`R29` IR,
  `R30/31` PC.
- The architectural registers are ordinary registers: `LDR 26` reads the flag byte (bit 0
  = carry) — that is how `int32_add` carries between bytes. `LDR 25` reads the accumulator.
- **Only `ADD` writes carry** (unsigned overflow). `NOT`, `BSL`, `BSR`, `BRL`, `BRR`,
  `ORR`, `AND`, `XOR` leave it untouched.
- No compare and no subtract instruction. Compare by adding the two's complement:
  `LDI 256-k` / `ADD r` / `JA0 eq` tests `r == k`; `JC1` after it tests `r >= k`. This is
  why `LDI 246 // 256 - 10` reads as "is it ASCII 10".
- Branches are only `JA0`/`JA1` (accumulator zero / nonzero) and `JC0`/`JC1` (carry).
- No register-indirect addressing. `LDM`/`STM` take an absolute address only; a computed
  address needs `mem_peek`/`mem_poke`, which patch an `LDM`/`STM` into scratch and `CLL` it.
- Stack grows **down** from `0xFC3F`. `PSH` pre-decrements; `POP` reads, zeroes the cell,
  increments. `CLL`/`RET` share that stack, so `PSH`/`POP` must balance across a call.
- Binary is loaded flat at address 0 and PC starts at 0. An invalid opcode exits the VM.

### kasm quirks

- Two passes, so forward label references are fine.
- `LDM`/`STM` **do not accept labels** — numeric addresses only. Labels work only as the
  operand of `JMP`, `JC0`, `JC1`, `JA0`, `JA1`, `CLL`.
- No `.org`, no `.equ`, no `.db`, no data or string emission. Constants go through `LDI`;
  tables are built at run time (see the keyword table at the top of `examples/basic.kasm`).
- `.include "path"` (relative to the including file) is the only directive, and it has **no
  include guards** — only circular includes are caught. A file reached twice is assembled
  twice, doubles in memory, and every call resolves to the second copy. Include *either* an
  umbrella *or* the files under it, never both.
- **Duplicate labels silently overwrite**; the last definition wins.
- Jumping (not calling) to a shared routine that ends in `RET` returns from the *caller's*
  frame. `examples/basic.kasm` uses this throughout: `JC0 basic__fail` sets the error flag
  and unwinds the current parse step in one instruction.
- Literals: decimal, `0x`, `0b`, `0o`. No negatives — write `256-n`. Ranges: reg ≤ `0x1F`,
  imm ≤ `0xFF`, mem ≤ `0xFFFF`. Max 8 tokens per line. `//` must be its own whitespace-
  separated token.

## Memory map

```
0x0000..        program, assembled flat from 0
0x8000-0x803F   klib scratch — full map in klib/io/disp.kasm, extend it there
                (klib tests keep their own state at 0x8040 and above)
0x8100+         free for the program (basic.kasm claims 0x8100-0x899B)
0xFC3F          stack top, grows down
0xFC40-0xFFFF   reserved display-sized block
```

## klib calling convention

`R0`-`R3` = A, `R4`-`R7` = B, `R8`-`R11` = C (result), `R12`-`R15` scratch/clobbered,
byte order LSB → MSB. Enter with `CLL`, leave with `RET`. That is the `math` contract;
`io`, `mem` and `str` deviate, and each file's `in: / out: / clobbers:` header is
authoritative — read it rather than assuming.

- Every float32 routine truncates toward zero, flushes an exponent below 1 to a signed zero
  (no subnormals), and treats exponent 255 as an ordinary number — infinities and NaNs are
  not carried through the arithmetic.
- `int32_div` is repeated subtraction: cost is the quotient itself (~300k rounds/s). Use
  the float32 group for anything with a large quotient.

## Device protocols

**Keyboard** (own process, polled at 20 Hz) — poll `R16` until nonzero, read the char from
`R17`, write 0 to `R16` to acknowledge. `R17` carries printable 32-255 through; Enter
arrives as ASCII 10 (CR 13 is normalized to 10 in `keyboard_push_cpu`); backspace is 8 or
127 depending on the terminal, so handle both; every other byte becomes `' '`.

**Display** (own process) — write the char to `R19`, write 1 to `R18`, then poll `R18`
until it is 0 before pushing the next char, or the char is overwritten before the display
sees it. 20x4 grid — the geometry of the LCD2004 the machine is built for, see
`logisim/README.md`; a full row advances to the next (cleared) row, a full last row clears
the whole display. Chars outside 32-126 occupy a cell but render blank. Writing 8 to `R19`
steps back one cell and clears it; at column 0 it does nothing.

The display has no readable cursor, so `disp_putc`/`disp_bs`/`disp_nl`/`disp_cls` track the
column at `0x8000` and the row at `0x8022`. In a program that uses them, never write
`R18`/`R19` directly — the counters drift. There is no clear command either: `disp_cls`
pads the grid with spaces up to the last cell, which is where the display clears itself,
so a clear costs up to 80 handshakes.

## Testing

Every C function and every klib routine needs a test, unless testing it is genuinely
impossible (terminal I/O, the fork/mmap wiring in `kone.c`).

**C** (`tests/test_<module>.c` + `.h`) — `TEST_MODULE_BEGIN` / `RUN_TEST` /
`TEST_MODULE_END` from `tests/test_common.h`, `return TEST_EXIT_CODE`. `RUN_TEST` forks, so
a failed `assert` kills only that test. Adding a test means: declare it in the `.h`, add the
`RUN_TEST` line, and bump the count in both `TEST_MODULE_*` calls.

Two traps in C tests, both hit while writing `tests/test_args.c`:

- `RUN_TEST` already forks. A test that forks *again* inherits the parent's buffered
  stdout, and any `exit()` in that child — or a `freopen` of `stdout` — flushes it, so the
  whole report so far prints twice. Point the descriptors at `/dev/null` with `dup2`
  instead; it leaves the buffer alone.
- `getopt_long` keeps scanning state between calls: set `optind = 0` before each
  `parse_args`, or every case after the first sees an exhausted argv.

**klib** (`tests/klib/test_<name>.kasm` → `bin/test_klib_<name>.bin`) — print one
`PASS:<case>` or `FAIL:<case>` display row per case (case name must match `[a-z0-9_]+`),
then a summary row `ALL PASS` or `<n> FAILED`, then halt in a loop. The harness runs the
binary for up to 20 s waiting for that summary; the case list is scraped from the whole run,
the `.expect` rows from the last complete frame.
Optional `test_<name>.in` is piped to stdin as keystrokes; optional `test_<name>.expect`
lists display rows that must match exactly.

Four rows is what the display holds, and the test protocol lives with it:

- The summary must be the **last thing printed and must not end its row**. Padding the last
  row out writes the last cell, which is exactly what clears the grid — the report then
  vanishes between two 20 Hz frames and the harness sees an empty screen. This cost an hour.
- A `.expect` row has to be on screen at the end, so a test that uses one clears the display
  and prints its checked rows as the last three, right above the summary.
- `PASS:` plus a case name over 15 characters wraps, and the report shows the name cut in
  half. The verdict is unaffected — it comes from the summary row. The protocol is also written up in `README.md`,
so a new test file states its cases and nothing else. An example's own scratch goes **above
`0x803F`**, clear of klib and in the same range the klib tests use.

## Known quirks — do not "fix" without discussing first

- CPU, display and keyboard are three `fork`ed processes sharing one `mmap`ed `CPU` struct
  with no locking. The `R18` handshake is the only synchronization; the residual race in
  `display_fetch` (reading `R19` and `R18` non-atomically while the CPU writes them) is
  known and accepted.
- `cycle_sleep` defaults to 0 — the CPU runs flat out. `-t USEC` slows it for watching.
- The display child redraws at `DISP_FRAME_RATE` (20 Hz) and polls device registers at
  `DISP_POLL_RATE` (2000 Hz); the keyboard at `KEYBOARD_POLL_RATE` (20 Hz). Each frame
  emits `\033[3J\033[H\033[2J`, which is what the klib test harness splits on.
- `kone.c` mmaps `sizeof(CPU)` for the `Display` — an over-allocation, harmless.
- `ISSUES.md` lists the open items; design limits that will not change belong in
  `README.md` instead.
- A BASIC program line is a fixed 40-byte record, which is what bounds expression length
  (five terms) and string literals (29 chars). Extending either means widening the slot and
  moving the program area, not touching the parser.

## Logisim

`logisim/` has its own `Makefile` (the root forwards `logisim_%` to it) and its own
`README.md`, which is where the reference material lives. `logisim/python/` generates the
`.circ` files that build kone out of 74xx chips: `core.py`
is the document model (`Component`, `Wire`, `Circuit`, `Project`, grid and net checks),
`components.py` the concrete parts and their port geometry, one `build_*.py` per circuit.
`make logisim_circ` runs them all, `make logisim_regfile` and `make logisim_alu` one
each; every Logisim target and variable carries that prefix. Reference is
`logisim/README.md`; what costs time:

- Port offsets are read out of Logisim's own jar, never guessed. A new part needs the same
  treatment — for a TTL chip, `AbstractTtlGate.portNames` and `outputPorts` give the pinout
  (DIP order, GND and VCC skipped) and `getOffsetBounds` the row spacing.
- Fan-out is the one thing to route by hand: two `connect()` calls from one port lay two
  wires that overlap into one silent short. Give each net its own column or a `Tunnel`.
- `Project.save()` refuses a floating TTL input, two tunnel labels on one net and duplicate
  pin labels, so that class of bug fails the build instead of showing up as `E` in the
  simulator.
- Put the chips first on the canvas. Logisim opens at the top left, and a pin block there
  hides a grid of chips 5000px further down.

`regfile.circ` — 32 x 8 bit from 32 74377 and 32 74245, selected by a two-level 74138 tree;
`BUS_IN`, `BUS_OUT`, `ADDR`, `RD`, `WR`, `CLK`. Logisim has no bidirectional pin, so the
parent ties `BUS_IN` and `BUS_OUT` to one net; `BUS_OUT` is high-Z unless `RD` selects.

`alu.circ` — the nine ALU opcodes and nothing else: `L`, `R` and `OP` in, `OUT`, `C`, `Z`
and `CWR` out. `OP` is the opcode byte itself, so the ALU reads the same bits the decoder
does: bit 7 picks two-operand over one-operand, bits 5-4 ORR/AND/XOR/ADD, bits 2-0
NOT/BSL/BSR/BRL/BRR. Any other opcode leaves `OUT` undefined — nothing latches `A` then.
`CWR` is high only for ADD, which is how "only ADD writes carry" is wired.

`kone.circ` — the whole CPU, generated by `build_kone.py` from `regfile.circ`, `alu.circ` and
`kone_microcode.py`. `make logisim_cpu` builds it, `LOGISIM_PROG=bin/<name>.bin` picks the
program baked into its ROM, `make logisim_test` boots `display`, `hello`, `keyboard` and the
`mem` klib test headlessly and checks the TTY -- the klib one runs `mem_poke`, so it is also
the proof that the machine executes from RAM.

The top level is a block diagram: `regfile`, `alu`, `sequencer`, `datapath`, `memory` and
`io`, plus the `Clock`, the `UADDR`/`BUS`/`MAR` probe pins and the two devices. The TTY and
the keyboard sit at the top on purpose -- inside a block, a running program's output is only
visible after descending into that subcircuit. Every chip belongs to exactly one block, so
put a new one where its signals already are:

| Block | Owns |
| --- | --- |
| `sequencer` | microprogram counter, the nine ROMs, next-address muxes, the condition mux |
| `datapath` | main bus mux, ALU operand mux, `T` / `T2` / `AL` / `CY` latches, address mux |
| `memory` | `MAR`, program ROM, RAM, the `MA15` split that drops a write below 0x8000 |
| `io` | `R16`-`R19`, their decode, and the handshakes the TTY and keyboard hang off |

A block's tunnels are private to it; anything crossing a boundary is a labelled pin, and the
microcode's control byte crosses as a whole (`WE`, `SEL`) and is split inside each consumer.

It is microcoded: every register the ISA names stays in the register file at the VM's index,
seven 256-byte ROMs hold the microprogram and two more map an opcode to its entry point,
which is `cpu_decode_exec()`'s switch. What that costs, and what to know before touching it:

- The register file has **one address port**, so a microstep reads one register or writes
  one, never two. A register-to-register move is two steps through the `T` latch, and the
  ALU's opcode `0x00` (NOP) is the pass-through that makes the second step work.
- Only `ADD` writes carry, so the microcode reads `F`, masks bit 0 and ORs the `CY` latch
  back in rather than writing the byte. `CY` is internal — it is not `F`, and the 16-bit
  increments and decrements in FETCH, PSH and RET use it without touching the flag.
- Memory is ROM below `0x8000` and RAM above it: a **write below 0x8000 is dropped**, which
  the VM would honour. Nothing in `klib` or `examples/` writes there, and `mem_poke`'s
  patched instructions live at `0x8000`, so they still execute from RAM.
- The display is a Logisim TTY, 20x4 like the vm's. It takes the same handshake (`R19`, then
  `R18`, cleared once the char is taken) and the same backspace, but a full screen scrolls
  instead of clearing the next row and then the whole grid the way `display_push_char()`
  does.
- `R18` is cleared by the **device**, over `DISPCLR`, not by io itself: a real display is
  slower than one clock. In `kone.circ` the line is the strobe buffered through a 7404, so
  the simulation still has an always-ready device; on the boards it is a backplane pin. The
  keyboard's other half of that is `KBACK`, the level a controller watches.
- A Logisim RAM does **not** keep its contents in the `.circ` — only a ROM does, through its
  `contents` attribute (`addr/data: <bits> 8`, then hex with `N*v` runs). That is why the
  program sits in ROM.
- A component label that repeats a component's own name (`ram` on a RAM, `rom` on a ROM)
  makes Logisim raise a Swing dialog while loading, which kills a headless run with a
  `HeadlessException` that `Loader.showError` does not catch. Label them anything else.
- In a headless harness a memory has no state until the first `propagate()`, so patch a
  ROM's contents after that, then `markComponentAsDirty()`.
- The circuit carries `simulationFrequency 4096`, Logisim's fastest auto-tick, because the
  1 Hz default shows nothing: a cycle is two ticks and an instruction some 20 cycles, so
  4 kHz is about 100 instructions a second. `count` spends some 500 instructions on a
  number, nearly all of it in `disp_nl` padding the row out.
- Logisim leaves a `.<name>.circ.autosave` beside a file it has open, and its loader stops on
  one with a dialog — fatal headless, and not routed through `Loader.showError`. `logisim_test`
  therefore runs on a copy in `logisim/bin/`, so a GUI session cannot break it.


## KiCad

`logisim/python/logisim/kicad.py` is a second backend on the same `Circuit` objects the
`.circ` writer uses: `Netlist` resolves the tunnels and splitters into real nets, `Board`
adds what Logisim does not model (VCC/GND pins, a 100nF per IC, headers) and `write()` emits
a KiCad 10 project. A change to a `build_*.py` therefore reaches both outputs, and nothing
parses a generated `.circ`. `build_kicad.py` builds the boards listed in its `BOARDS` table
and writes `logisim/kicad/BACKPLANE.md`, the pinout every board carries, and
`logisim/PARTS.md`, what to order — one section per board, a total, and a hand kept
interface section, with the per-board counts checked against the placed footprints. It lives
beside the README because `logisim/kicad/` is generated and `clean` deletes it.
`logisim/README.md` is the only hand written doc on the hardware side: it also carries the
board format, and the Arduino Mega 2560 bridge that runs the USB keyboard and the LCD2004 —
its pin map onto the io board's device signals and the two protocols it implements.
`build_kicad.py` warns when the outline the README states no longer matches the boards.

All six blocks are boards: `regfile` (86 ICs), `alu` (27), `io` (23), `sequencer` (20),
`datapath` (15) and `memory` (8), each four layers -- signals outside, a GND plane on
`In1.Cu` and a +5V plane on `In2.Cu` -- with a 100nF per IC, a 100uF bulk cap, the backplane
connectors it needs and a power header. They are meant to stack, so every board carries the
**same outline** (the size the largest one needs), four M3 holes 6 mm in from the corners and
its backplane connectors at the same coordinates. The stack is fed at one point: a screw
terminal on `io` puts `+5V` and `GND` on the backplane, with an LED and its resistor beside
it. There is no regulator anywhere -- the supply has to be regulated 5 V, and
`BACKPLANE.md`, which is generated, says what it has to deliver. `BACKPLANE.md` is generated from the top level of `kone.circ`, so a
header pin means the same signal on every board. What costs time here:

- Tunnels with the same label are **one net**, and `Netlist` has to union them: a block's
  8-bit port reaches its splitter only that way, and without it a connector pin ends up on a
  net named after the bus (`SEL5`) that no chip is on.
- A Logisim `ROM` or `RAM` is not a part; `PARTS` maps it onto the 28-pin JEDEC pinout
  (28C256, 62256). A ROM is tied selected and output-enabled; the SRAM takes `OE#` from the
  write strobe and `WE#` from the net named `n<STROBE>`, which the circuit has to provide --
  that is what the extra inverter in `memory()` is for. Logisim's separate `din` and `dout`
  are one bus on the chip, so the board merges those two nets.
- The board grid follows the largest package on it, or a 0.6 inch memory overlaps its own
  decoupling cap. Since every board carries the largest board's outline, a small one spreads
  its chips over the whole of it: `sequencer` and `io` were the two the router could not
  finish while their chips sat crowded in one corner.
- A DIP pad is **1.4 mm** on a 0.8 mm drill, not the usual 1.6: `2.54 - 1.4` leaves 1.14 mm
  between two pins, and a 0.25 mm track with the widest clearance the router is given
  (0.35 mm) needs 0.95 of it. At 1.6 mm the
  gap is 0.94, vertical channels through a chip run out, and one bus bit stays open no matter
  how long the router tries. Header pins take the plane solid (`zone_connect 2`); in a
  2.54 mm grid there is no room for the two thermal spokes DRC wants.
- A track is **0.2 mm**, not 0.25. What matters is the room between two DIP pins, not the
  current a bus bit carries, and 0.2 is still twice JLCPCB's minimum: it took `regfile` from
  six open connections to one.
- The last connection is closed by a **second pass with the routing so far protected**:
  `build_kicad.py --fix` writes the design with every track it already has as
  `(type protect)` in the wiring section, so the router only has to solve what it left open.
  That is seconds of work and it is what `route` does after the clearances are exhausted.
  Freerouting on its own stops at pass 18 of 25 and reports the connection rather than
  laying it, so more passes are wasted time.
- Grouping the decode tree's five 74138 side by side (they sort apart, `group` before the
  16 OR gates, `sel0`-`sel3` after) makes it **worse**, six open instead of one: fanning
  four selects out of one row costs more than the long way round. Tried, reverted, do not
  try it again.
- The router is far more deterministic than it looks: `-is random` and `-us global` both
  reproduced the same short down to the coordinate, so retrying a board unchanged is wasted
  time. The clearance in the `.dsn` is the input that changes its mind, which is why `route`
  retries with the next `FREEROUTING_CLEARANCES` value (0.3, 0.35, 0.25 mm) — `regfile` only
  finishes at 0.3, `datapath` only at 0.35. All three are wider than KiCad's 0.2 rule on
  purpose, so the router's rounding stays inside it.
- KiCad's own symbol and footprint libraries are a **separate package** (`kicad-library`)
  and are not installed on this machine, so the backend generates a project-local library.
  A DIP symbol is a rectangle with numbered pins, which is what a 74xx symbol is anyway.
- In a schematic's `lib_symbols` the symbol name has to be the **full lib_id**
  (`kone:74377`), while its `_0_1`/`_1_1` children keep the bare name. Get it wrong and the
  instance has no pins: every label dangles and ERC reports thousands of violations.
- Every pin, wire end and label has to sit on the **1.27 mm connection grid**, so the sheet
  origin and cell pitch are multiples of it. Off-grid ends still connect, but ERC warns once
  per pin.
- Logisim's TTL model has no VCC and GND, `dip()` adds them back from the package size, and
  their nets are `+5V` and `GND`. Naming them after the pin instead leaves a "VCC" net that
  nothing drives -- which is what ERC's `power_pin_not_driven` is for.
- The gate is `--severity-error --exit-code-violations` on both tools, and open connections
  are **errors**, so a board that is not fully routed cannot pass. `logisim_kicad` checks a
  board that has no tracks yet, so it is the one step that lets that class through — it fails
  on anything else. DRC runs with `--refill-zones --save-board`: the planes have to be poured
  before connectivity means anything, and the poured board is what the gerbers export.
- Every board carries **every** backplane connector, and a pin whose signal a board has not
  got is a pass-through: the pad carries the backplane net and nothing else on that board is
  on it, so it is a one pad net the router ignores. `stacking()` in `build_kicad.py` fails
  the build unless all six boards agree on the connector count, the connector and M3 hole
  coordinates and the outline — nothing on a board is rotated, so a position is the whole
  story. That check is what keeps the stack mechanically honest; do not weaken it.
- A `.ses` is only valid for the board it was routed against. Applying a stale one puts
  copper through pads that were not there before — it cost alu 12 DRC errors — so
  `ses_fits()` drops the session instead. It compares the **footprint and the position** of
  every part: references are positional, so after a placement change the same `U65` is a
  different chip, and comparing names alone let a stale session through for another 378
  violations. The comparison skips `PWR` parts and anything without pins, since the `.dsn`
  does not place those either.
- `BACKPLANE.md` and `PARTS.md` are written from all six boards on every run, not from the
  ones a `--route <board>` invocation happened to touch.
- A mounting hole is a hole to KiCad but nothing to the router, so `dsn()` puts a keepout
  circle over each one on both layers. Without it tracks run straight through the M3 holes.
- Routing runs through Freerouting, which is not packaged: put its jar where
  `FREEROUTING_JAR` points (`~/.cache/freerouting/freerouting.jar`) and `make logisim_route`
  writes the `.dsn`, runs it and reads the `.ses` back into the board. KiCad 10's CLI has
  neither Specctra export nor import, so both ends live in `kicad.py`.
- **Every dimension in a `.dsn` uses the same scale** as its coordinates (`resolution um 10`
  is 0.1 um per unit): pad and via shapes, track width, clearance. Getting the pads wrong by
  a factor of ten lets the router pull tracks straight through them, and the board comes back
  with hundreds of shorts that are not the router's fault.
- Freerouting writes its session at a **different scale than the design it was given**, so
  `parse_ses()` calibrates on the placements it echoes rather than trusting the resolution it
  declares.
- The `.dsn` boundary is the board outline **inset by 1 mm**, or the router lays tracks along
  the edge and every one of them is a `copper_edge_clearance` error. For the same reason the
  clearance it is given (0.25 mm) is wider than the rule KiCad checks (0.2 mm): its rounding
  has to stay inside. It also emits zero-length track fragments, which DRC reports as
  clearance violations, so `parse_ses()` drops points closer together than 0.01 mm.

## Where this stands

The VM, kasm, klib and the Logisim circuits are done and green: `make test` 3/3,
`make logisim_test` 5/5 — `display`, `hello`, `keyboard` and the `mem` klib test all boot on
`kone.circ` in Logisim's own simulator.

All six boards are generated, ERC clean and fully routed: `make logisim_clean && make
logisim_route && make logisim_gerbers` ends 6/6 with every board at 0 unrouted connections
and 0 DRC violations, no manual pass in pcbnew, and the ZIPs in `logisim/kicad/out/`. That
took **four layers** — `In1.Cu` is a GND plane, `In2.Cu` a +5V plane — which costs more per
board than two but is what takes the two rails off the signal layers. Freerouting is not in
the repo — v2.4.1 sits at `~/.cache/freerouting/freerouting.jar`, where `FREEROUTING_JAR`
points. `logisim_clean` and `clean` delete `logisim/kicad/`, the `.ses` with it, so routing
has to be recomputed rather than restored after either.

The chain takes about 25 minutes, and two things about running it cost a night each:

- **Never run it next to another one.** Two runs write the same `kicad/<board>/` files and
  delete each other's sessions; it looks exactly like a board that will not route, and it
  sent me chasing a placement bug that was not there.
- A long run in the background was killed twice from outside, once in the middle of `alu`,
  which then reported `no alu.ses; run the router first`. Start it detached
  (`setsid nohup sh -c '...' &`) and read the log rather than the exit code.

What is left:

1. **The display and keyboard connectors.** The TTY and keyboard lines reach the backplane
   but no board carries a socket for them: the Arduino bridge is wired to the stack
   connector by hand, which `logisim/README.md` describes. The clock is done — `io` carries
   the can oscillator (X1), the source jumper (J6) and the external clock header (J7).
2. **A bill of materials.** `kicad-cli sch export bom` would do it; there is no target.

One question for the author is still open: KiCad's own symbol and footprint libraries are a
separate package (`kicad-library`) and are not installed, so the boards carry generated ones.
Installing it would let them use the official 74xx symbols, at the price of dealing with
multi-unit gate symbols in a generated schematic.
