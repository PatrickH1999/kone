"""Generate Logisim Evolution .circ files from Python.

    from logisim import *

    c = Circuit("main")
    a = c.add(Pin(100, 100, "A"))
    g = c.add(NotGate(200, 100))
    c.connect(g, "in", a)

    p = Project()
    p.add(c)
    p.save("logisim/example.circ")
"""

from .core import (GRID, Circuit, Component, GridError, PortError, Project,
                   Subcircuit, Wire, on_grid, rotate)
from .components import *  # noqa: F401,F403
from . import components

__all__ = ["GRID", "Circuit", "Component", "GridError", "PortError", "Project",
           "Subcircuit", "Wire", "on_grid", "rotate"] + [
    name for name in dir(components)
    if not name.startswith("_") and name[0].isupper()
]
