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
make format     # clang-format, run before finishing
bin/kone -b bin/hello.bin [-t USEC] [-v0..3] [-l]
bin/kasm -i examples/x.kasm -o bin/x.bin
```

`make clean` also deletes `$(PREFIX)/bin/{kone,kasm}`; `make debug` depends on `clean`, so
it uninstalls as a side effect. kasm emits no depfiles, so any klib edit rebuilds every
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
sees it. 40x24 grid; a full row advances to the next (cleared) row, a full last row clears
the whole display. Chars outside 32-126 occupy a cell but render blank. Writing 8 to `R19`
steps back one cell and clears it; at column 0 it does nothing.

The display has no readable cursor, so `disp_putc`/`disp_bs`/`disp_nl`/`disp_cls` track the
column at `0x8000` and the row at `0x8022`. In a program that uses them, never write
`R18`/`R19` directly — the counters drift. There is no clear command either: `disp_cls`
pads the grid with spaces up to the last cell, which is where the display clears itself,
so a clear costs up to 960 handshakes.

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
binary for up to 20 s waiting for that summary, then scrapes the last complete display frame.
Optional `test_<name>.in` is piped to stdin as keystrokes; optional `test_<name>.expect`
lists display rows that must match exactly. The protocol is also written up in `README.md`,
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

`logisim/python/` generates the `.circ` files that build kone out of 74xx chips: `core.py`
is the document model (`Component`, `Wire`, `Circuit`, `Project`, grid and net checks),
`components.py` the concrete parts and their port geometry, one `build_*.py` per circuit.
`make circ` runs them all, `make regfile` and `make alu` one each. Reference is
`logisim/python/README.md`; what costs time:

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
