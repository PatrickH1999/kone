# The keyboard and display bridge

The `io` board brings both device protocols out to the backplane as plain 5 V
logic: seven data lines and two handshake lines per side. Neither a USB
keyboard nor an HD44780 display speaks that, so one **Arduino Mega 2560** sits
between them and implements both protocols. It is 5 V, like the io board, so
no level shifting is needed anywhere.

A Nano does not fit: its 18 usable GPIO are spent on the USB Host Shield (4 SPI
plus an interrupt) and the LCD (2 for I2C) long before the 18 lines the io
board needs. The Mega has 54 digital pins.

## What hangs off the Mega

| Part | Connection |
| --- | --- |
| USB Host Shield (MAX3421E) | SPI, `SS` on 53 or the shield's 10, `INT` on 9 |
| Freenove I2C LCD2004, 20x4 | I2C on 20 (SDA) and 21 (SCL), +5 V, GND |
| kone `io` board | 18 signal lines, see below, plus a shared GND |

**Uno-format shield on a Mega.** A USB Host Shield is an Uno shield and takes
SPI from pins 11, 12 and 13, which on a Mega are ordinary GPIO. Use a shield
revision that takes SPI from the **ICSP header** (the USB Host Shield 2.0
boards do, and the ICSP header carries the Mega's hardware SPI), or lift the
shield's 11/12/13 pins and jumper them to 51 (MOSI), 50 (MISO) and 52 (SCK).
`SS` and `INT` are on 10 and 9 in both cases, which exist on the Mega.

## Pin map

The signals are the ones `kicad/BACKPLANE.md` lists for the `io` board;
direction is from the machine's point of view.

| kone signal | Backplane | Direction | Mega pin | Mega mode |
| --- | --- | --- | --- | --- |
| `TTYD0` | BP4.4 | out | 22 | input |
| `TTYD1` | BP4.5 | out | 23 | input |
| `TTYD2` | BP4.6 | out | 24 | input |
| `TTYD3` | BP4.7 | out | 25 | input |
| `TTYD4` | BP4.8 | out | 26 | input |
| `TTYD5` | BP4.9 | out | 27 | input |
| `TTYD6` | BP4.10 | out | 28 | input |
| `DISPNZ` | BP2.6 | out | 29 | input |
| `DISPCLR` | BP2.5 | in | 30 | output |
| `KBD0` | BP2.9 | in | 31 | output |
| `KBD1` | BP2.10 | in | 32 | output |
| `KBD2` | BP2.11 | in | 33 | output |
| `KBD3` | BP2.12 | in | 34 | output |
| `KBD4` | BP2.13 | in | 35 | output |
| `KBD5` | BP2.14 | in | 36 | output |
| `KBD6` | BP2.15 | in | 37 | output |
| `KBAV` | BP2.8 | in | 38 | output |
| `KBACK` | BP2.7 | out | 39 | input |
| `GND` | BP1.2 | - | GND | - |

`KBSET` (BP2.16) is the same event as `KBAV` as a one-clock pulse, for a device
that wants an edge. The bridge uses the level, so it stays unconnected. The
data lines are seven bits wide, so the bridge passes ASCII 0-127 and nothing
above it; the vm's keyboard accepts 32-255, but a real keyboard has no way to
send the upper half anyway.

Do not feed the stack from the Mega's 5 V pin. The backplane's supply and the
Mega's USB supply are separate; tie only their grounds together.

## Display protocol

`R19` holds the character and `R18` the handshake, exactly as
`src/display_functions.c` implements it:

1. `DISPNZ` goes high once the program has written the character and set `R18`.
2. Read the seven `TTYD` lines. That is the character.
3. Write it to the LCD, keeping the kone semantics below.
4. Raise `DISPCLR` and hold it until `DISPNZ` falls; that is what clears `R18`
   and lets the program push the next character. Then drop `DISPCLR`.

The semantics the bridge owes the program, because klib's `disp_putc` counts on
them (`klib/io/disp.kasm` keeps its own column and row pointer and never reads
the display back):

- The grid is 20x4 and the cursor advances one cell per character.
- A character on the last cell of a row moves the cursor to the start of the
  next row **and clears that row** before writing further characters into it.
- A character on the last cell of the **last** row clears the whole display and
  puts the cursor back on the first cell.
- Character 8 is a backspace: step back one cell and clear it. At column 0 it
  does nothing -- the row above has scrolled past.
- Characters outside 32-126 occupy a cell but render blank.

An HD44780's DDRAM rows are not contiguous (0x00, 0x40, 0x14, 0x54 for 20x4),
so the row start has to be set with a `setCursor` per row rather than by
writing on.

## Keyboard protocol

`R16` is the set flag and `R17` the character, as in
`src/keyboard_functions.c`. Per key the bridge does:

1. Translate the USB HID key to ASCII. Normalize as the vm does: CR (13)
   becomes 10, backspace stays 8 (127 is also accepted), printable 32-126 pass
   through, everything else becomes a space (32).
2. Put the code on `KBD0`-`KBD6` and raise `KBAV`.
3. Wait for `KBACK` to go high. The machine has taken the character into `R17`
   and set `R16`.
4. Drop `KBAV`.
5. Wait for `KBACK` to go low again -- the program has acknowledged by writing
   0 to `R16`. Only then offer the next character.

Holding `KBAV` high while `KBACK` is already high would offer the same
character twice, since `KBSET` is `KBAV AND NOT R16`. A character typed while
the program is not polling is lost rather than buffered, which is the vm's
behaviour too; a small ring buffer in the bridge is a deliberate deviation, not
a fix, so a program's `INPUT` prompt still has to be reached before the user
types.

## Sketch

Not in the repo. There is no `arduino-cli` on this machine to compile it
against, and an unverified sketch is worse than none; the two protocols above
are complete enough to write it (`USB Host Shield 2.0` for the keyboard,
`LiquidCrystal_I2C` for the display).
