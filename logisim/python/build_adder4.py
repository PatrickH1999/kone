#!/usr/bin/env python3
"""Smoke test: a 4-bit ripple-carry adder out of gates.

Exercises every part of the library the kone build will need: a subcircuit
instantiated four times, connect() by port name, splitters, tunnels and
explicit trunk routing.
"""

from pathlib import Path

from logisim import *

OUT = Path(__file__).resolve().parents[1] / "adder4.circ"

SPACING = 300           # horizontal pitch of the four full adders
ROW = 400               # top edge of the adder row


def full_adder():
    """S = A^B^Cin, Cout = AB + (A^B)Cin. Inputs reach the gates by tunnel."""
    c = Circuit("full_adder")
    for i, name in enumerate(("A", "B", "Cin")):
        pin = c.add(Pin(100, 100 + 200 * i, name))
        c.connect(c.add(Tunnel(200, 100 + 200 * i, name)), None, pin)

    def feed(gate, port, net):
        x, y = gate.port(port)
        c.connect(c.add(Tunnel(x - 60, y, net)), None, gate, port)

    xor1 = c.add(XorGate(400, 200))
    and1 = c.add(AndGate(400, 400))
    xor2 = c.add(XorGate(700, 300))
    and2 = c.add(AndGate(700, 500))
    or1 = c.add(OrGate(950, 400))

    feed(xor1, "A", "A"), feed(xor1, "B", "B")
    feed(and1, "A", "A"), feed(and1, "B", "B")
    feed(xor2, "B", "Cin")
    feed(and2, "B", "Cin")

    # A^B drives both second-stage gates; a tunnel keeps that fan-out tidy.
    c.connect(xor1, "out", c.add(Tunnel(500, 200, "AxB", facing="east")))
    feed(xor2, "A", "AxB")
    feed(and2, "A", "AxB")

    c.connect(and1, "out", c.add(Tunnel(500, 400, "AB", facing="east")))
    feed(or1, "A", "AB")
    c.connect(and2, "out", c.add(Tunnel(800, 500, "AxBC", facing="east")))
    feed(or1, "B", "AxBC")

    c.connect(xor2, "out", c.add(Pin(1100, 300, "S", output=True)))
    c.connect(or1, "out", c.add(Pin(1100, 400, "Cout", output=True)))
    return c


def trunk(c, src, dst, x):
    """Route src to dst down a vertical trunk of its own, so nets never merge."""
    c.route(src, (x, src[1]), (x, dst[1]), dst)


def main_circuit(adder):
    c = Circuit("main")

    a_pin = c.add(Pin(100, 100, "A", width=4))
    a_split = c.add(Splitter(200, 100, fanout=4, incoming=4, appear="right"))
    c.connect(a_pin, None, a_split, "in")

    b_pin = c.add(Pin(100, 200, "B", width=4))
    b_split = c.add(Splitter(200, 200, fanout=4, incoming=4, appear="right"))
    c.connect(b_pin, None, b_split, "in")

    cin_pin = c.add(Pin(100, 300, "Cin"))

    s_split = c.add(Splitter(1600, 600, fanout=4, incoming=4, facing="west"))
    c.connect(s_split, "in", c.add(Pin(1700, 600, "S", width=4, output=True)))

    stages = [c.add(adder.instance(400 + SPACING * i, ROW)) for i in range(4)]

    for i, stage in enumerate(stages):
        trunk(c, a_split.port(str(i)), stage.port("A"), 360 + SPACING * i)
        trunk(c, b_split.port(str(i)), stage.port("B"), 340 + SPACING * i)
        trunk(c, stage.port("S"), s_split.port(str(i)), 560 + SPACING * i)

    trunk(c, cin_pin.port(), stages[0].port("Cin"), 320)
    for lower, upper in zip(stages, stages[1:]):
        c.connect(lower, "Cout", upper, "Cin", style="vh")
    trunk(c, stages[-1].port("Cout"),
          c.add(Pin(1700, 300, "Cout", output=True)).port(), 1500)
    return c


if __name__ == "__main__":
    adder = full_adder()
    project = Project(main="main")
    project.add(main_circuit(adder))
    project.add(adder)
    print(project.save(OUT))
