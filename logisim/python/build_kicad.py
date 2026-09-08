#!/usr/bin/env python3
"""KiCad projects for the boards, from the circuits the .circ files come from.

    python3 logisim/python/build_kicad.py [board ...]
    python3 logisim/python/build_kicad.py --route [board ...]

One directory per board under logisim/kicad/, each a KiCad project with its own
symbol and footprint library: KiCad's own libraries are a separate install and
this way the boards do not depend on which version of them is present.

--route insists on the .ses Freerouting wrote for a board; without it, a session
lying next to the board is used anyway, so regenerating keeps the routing.
"""

import re
import sys
from pathlib import Path

from logisim.kicad import (
    Board,
    HEADER_PINS,
    RAILS,
    backplane,
    parse_ses,
    ses_fits,
    system_nets,
    write,
)
from build_alu import alu
from build_kone import datapath, io, kone, memory, sequencer
from build_regfile import regfile
from kone_microcode import assemble

OUT = Path(__file__).resolve().parents[1] / "kicad"

# name -> chips per row on the board
BOARDS = {
    "regfile": 8,
    "alu": 6,
    "datapath": 6,
    "sequencer": 4,
    "memory": 3,
    "io": 6,
}

# The board the whole stack is fed through.
ENTRY = "io"


def blocks():
    """The six circuits of the CPU, in the order kone() takes them."""
    rom, dispatch_a, dispatch_b, _, _ = assemble()
    return {
        "regfile": regfile(),
        "alu": alu(),
        "sequencer": sequencer(rom, dispatch_a, dispatch_b),
        "datapath": datapath(),
        "memory": memory(b""),
        "io": io(),
    }


# What to actually order: the generic 74xx name a circuit uses, the part it
# becomes, and what it does. HC throughout, which is what the current draw in
# BACKPLANE.md assumes; LS works as well but takes about five times the supply.
CHIPS = {
    "7404": ("74HC04", "hex inverter"),
    "7408": ("74HC08", "quad 2-input AND"),
    "7411": ("74HC11", "triple 3-input AND"),
    "7421": ("74HC21", "dual 4-input AND"),
    "7427": ("74HC27", "triple 3-input NOR"),
    "7432": ("74HC32", "quad 2-input OR"),
    "7486": ("74HC86", "quad 2-input XOR"),
    "74138": ("74HC138", "3-to-8 decoder"),
    "74151": ("74HC151", "8:1 multiplexer"),
    "74153": ("74HC153", "dual 4:1 multiplexer"),
    "74157": ("74HC157", "quad 2:1 multiplexer"),
    "74245": ("74HC245", "octal bus transceiver"),
    "74283": ("74HC283", "4-bit binary adder"),
    "74377": ("74HC377", "octal register, clock enable"),
    "28C256": ("AT28C256-15PU", "32K x 8 EEPROM, parallel"),
    "62256": ("AS6C62256-55PCN", "32K x 8 SRAM"),
}

# Everything a board needs that is not a chip.
PASSIVES = {
    "100n": ("ceramic 100nF, 5.08mm", "one per IC, decoupling"),
    "100u": ("electrolytic 100uF/16V, 2.5mm", "bulk, one per board"),
    "220R": ("resistor 220R, 1/4W", "power LED series resistor"),
    "PWR": ("LED 3mm", "power indicator"),
    "5V IN": ("screw terminal 2x5.08mm", "supply entry"),
    "Power": ("pin header 1x02", "supply header"),
    "M3": ("M3 hole, screw and standoff", "stacking"),
}


def bom(path, boards, out):
    """Every part the six boards need, per board and in total.

    The counts come from the placed parts and are checked against the
    footprints in the generated .kicad_pcb, so a board and its section of the
    list cannot drift apart.
    """
    def parts_of(board):
        count = {}
        for part in board.parts:
            if part.symbol == "PWR":
                continue
            value = (
                "Backplane"
                if part.value.startswith("Backplane")
                else part.value
            )
            count[value] = count.get(value, 0) + 1
        return count

    def placed(name):
        text = (out / name / f"{name}.kicad_pcb").read_text()
        count = {}
        for value in re.findall(r'\(property "Value" "([^"]*)"', text):
            value = "Backplane" if value.startswith("Backplane") else value
            count[value] = count.get(value, 0) + 1
        return count

    per = {name: parts_of(board) for name, board in boards.items()}
    for name in boards:
        if (out / name / f"{name}.kicad_pcb").exists():
            if per[name] != placed(name):
                sys.exit(f"{name}: parts list and board disagree")

    total = {}
    for count in per.values():
        for value, n in count.items():
            total[value] = total.get(value, 0) + n

    def describe(value):
        if value in CHIPS:
            return CHIPS[value][0], CHIPS[value][1]
        if value in PASSIVES:
            return PASSIVES[value]
        return value, "board to board"

    def package(value):
        if value == "Backplane":
            return "2.54mm"
        if value not in CHIPS:
            return "-"
        for board in boards.values():
            for part in board.parts:
                if part.value == value:
                    return part.footprint.split("_")[0]
        return "-"

    def table(count):
        rows = [
            "| Part | Package | Function | Count |",
            "| --- | --- | --- | --- |",
        ]
        for value in sorted(count, key=lambda v: (v not in CHIPS, -count[v], v)):
            part, what = describe(value)
            rows.append(
                f"| `{part}` | {package(value)} | {what} | {count[value]} |"
            )
        return rows

    rows = [
        "# Parts list",
        "",
        "Generated by `build_kicad.py` from the boards themselves and checked",
        "against the footprints on them, so it counts what is actually placed.",
        "Every logic part is a DIP; 74HC throughout, which is what the supply",
        "estimate in `BACKPLANE.md` assumes. The interface section at the end",
        "is the exception: those parts sit on no board and are kept by hand.",
        "",
    ]
    for name in boards:
        rows += [f"## {name}", "", *table(per[name]), ""]
    chips = sum(n for v, n in total.items() if v in CHIPS)
    rows += [
        "## Total",
        "",
        *table(total),
        "",
        f"{chips} chips over the six boards. Sockets are worth it for the two",
        "memory types, which are the parts you will want to reprogram.",
        "`74HC21` and `74HC27` are the two that are thinly stocked; the LS or",
        "HCT versions drop in.",
        "",
        "## Interface",
        "",
        "Hand kept, not derived from a board: the bridge between the io board",
        "and the two devices, which `README.md` wires up and programs.",
        "",
        "| Part | Function | Count |",
        "| --- | --- | --- |",
        "| Arduino Mega 2560 (5 V) | runs both device protocols | 1 |",
        "| USB Host Shield, MAX3421E | the USB keyboard | 1 |",
        "| Freenove I2C LCD2004, 20x4 | the display, HD44780 behind a PCF8574 | 1 |",
        "| pin header 2x20, stackable | the io board's free stack connector | 2 |",
        "| jumper wires, female to female | 18 signals and a ground to the Mega | 19 |",
        "| resistor 4.7k | I2C pull-ups, only if the LCD module has none | 2 |",
        "",
        "A USB Host Shield is an Uno shield: on a Mega it has to take SPI from",
        "the ICSP header (the 2.0 boards do) or have 11/12/13 jumpered to",
        "51/50/52. Its supply stays the Mega's; only the grounds are tied.",
        "",
    ]
    path.write_text("\n".join(rows) + "\n")
    return path


def pinout(path, signals, boards):
    """The backplane table and how the stack is powered, both generated."""
    rows = [
        "# Backplane pinout",
        "",
        "Generated by `build_kicad.py` from the top level of `kone.circ`, so a",
        f"pin means the same thing on every board. {HEADER_PINS} pins per 2x20",
        "connector.",
        "",
        "**Every board carries every connector**, at the same coordinates and",
        "the same way round, and so are the four M3 holes -- the generator",
        "fails the build if a board disagrees. A pin whose signal a board has",
        "no use for is a pass-through: the pad is there and carries the",
        "backplane net, nothing on that board is on it. The stacking order is",
        "therefore electrically irrelevant, and so is which board sits at the",
        "top or the bottom; only pin 1 has to line up, which the square pad",
        "and the dot beside it mark on the silkscreen.",
        "",
        "The `Boards` column says where a signal comes from or goes to, not",
        "which boards carry the pin -- that is all of them.",
        "",
        "| Connector | Pin | Signal | Boards |",
        "| --- | --- | --- | --- |",
    ]
    for i, signal in enumerate(signals):
        on = (
            list(boards)  # the rails, which every board takes off the bus
            if i < len(RAILS)
            else [n for n, board in boards.items() if i in board.driven]
        )
        rows.append(
            f"| BP{i // HEADER_PINS + 1} | {i % HEADER_PINS + 1} | "
            f"`{signal}` | {', '.join(on) or '-'} |"
        )

    ics = {
        name: sum(1 for p in board.parts if p.ref.startswith("U"))
        for name, board in boards.items()
    }
    rows += [
        "",
        "## Power",
        "",
        f"The stack has one supply entry, on the `{ENTRY}` board: a 2-pin screw",
        "terminal (J5) feeding `+5V` and `GND` into the backplane. Every other",
        "board is powered through the backplane connectors alone -- there is no",
        "regulator anywhere on the stack, so the supply has to be regulated 5 V.",
        "`io` also carries the power indicator, an LED with a 220 ohm resistor",
        "(about 14 mA). Each board has a 100 uF bulk capacitor beside its",
        "connectors, and every IC its own 100 nF.",
        "",
        "| Board | ICs |",
        "| --- | --- |",
    ]
    for name, count in sorted(ics.items(), key=lambda kv: (-kv[1], kv[0])):
        rows.append(f"| {name} | {count} |")
    rows += [
        f"| **total** | **{sum(ics.values())}** |",
        "",
        f"Supply: **5 V regulated**. {sum(ics.values())} packages, ten of them",
        "28-pin memories. With 74HC parts at a few mA each and 10-30 mA per",
        "memory, the stack draws roughly 0.5 to 1 A at a low clock, so a 5 V /",
        "2 A supply leaves headroom. 74LS parts instead would multiply that by",
        "about five, which is worth checking before choosing a supply.",
    ]
    path.write_text("\n".join(rows) + "\n")
    return path


def outline(size):
    """Warn when the README's board format no longer states the real outline."""
    readme = Path(__file__).resolve().parents[1] / "README.md"
    stated = re.search(r"outline, \*\*([\d.]+) x ([\d.]+) mm\*\*", readme.read_text())
    if not stated:
        print(f"{readme}: no board format line to check", file=sys.stderr)
    elif tuple(float(v) for v in stated.groups()) != tuple(round(v, 2) for v in size):
        print(
            f"{readme}: board format says {stated.group(1)} x {stated.group(2)} mm, "
            f"boards are {size[0]:.2f} x {size[1]:.2f} mm",
            file=sys.stderr,
        )


def stacking(boards, connectors):
    """Guard the mechanics of the stack.

    Every board has to carry every connector, and the connectors and the M3
    holes have to sit at the same place on all of them, or two boards short
    through the backplane or do not go together at all. Nothing on a board is
    rotated, so a position is the whole story.
    """

    def fixture(board):
        return (board.width, board.height), sorted(
            (part.value, part.footprint, round(part.x, 3), round(part.y, 3))
            for part in board.parts
            if part.value.startswith("Backplane") or part.value == "M3"
        )

    for name, board in boards.items():
        n = sum(1 for p in board.parts if p.value.startswith("Backplane"))
        if n != connectors:
            sys.exit(f"{name}: {n} backplane connectors, expected {connectors}")
    (first, want), *rest = ((n, fixture(b)) for n, b in boards.items())
    for name, got in rest:
        if got != want:
            sys.exit(f"{name}: connectors or M3 holes do not line up with {first}")


if __name__ == "__main__":
    args = sys.argv[1:]
    route = "--route" in args
    # --fix writes the design with what is routed already protected, so the
    # next run of the router only has to close what it left open.
    fixed = "--fix" in args
    wanted = [a for a in args if not a.startswith("--")] or list(BOARDS)
    circuits = blocks()
    system = system_nets(kone(tuple(circuits.values())))
    signals = backplane(system)
    positions = {signal: i for i, signal in enumerate(signals)}

    def make(name, size=None):
        return Board(
            name,
            circuits[name],
            columns=BOARDS[name],
            ports={
                port: net
                for (block, port), net in system.items()
                if block == name
            },
            positions=positions,
            size=size,
            entry=name == ENTRY,
        )

    # Every board gets the outline the largest one needs, so a stack of them
    # lines up on its standoffs.
    measured = [make(name) for name in BOARDS]
    size = (
        max(b.width for b in measured),
        max(b.height for b in measured),
    )
    boards = {name: make(name, size) for name in BOARDS}
    outline(size)
    stacking(boards, len(signals) // HEADER_PINS)
    for name in wanted:
        if name not in BOARDS:
            sys.exit(f"no board {name!r}; have {', '.join(BOARDS)}")
        board = boards[name]
        tracks, vias = (), ()
        # A session from an earlier run is kept, so regenerating a board does
        # not silently throw its routing away.
        session = OUT / name / f"{name}.ses"
        if (route or fixed) and not session.exists():
            sys.exit(f"no {session}; run the router first")
        if session.exists():
            text = session.read_text()
            if ses_fits(text, board):
                tracks, vias = parse_ses(text, board)
            else:
                # The board has changed under the routing; keeping it would
                # lay tracks through parts that were not there before.
                session.unlink()
                print(f"{session}: stale, board changed -- route again")
        print(
            write(board, OUT / name, tracks, vias, fixed),
            f"({len(board.parts)} parts, {len(board.nets())} nets"
            + (
                f", {sum(len(p) - 1 for *_, p in tracks)} segments, "
                f"{len(vias)} vias)"
                if tracks
                else ")"
            ),
        )
    print(pinout(OUT / "BACKPLANE.md", signals, boards))
    # The parts list is documentation, not a build artifact, so it lives
    # beside the README rather than in the ignored kicad/ tree.
    print(bom(OUT.parent / "PARTS.md", boards, OUT))
