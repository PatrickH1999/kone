"""The ten EEPROM images, one file per chip.

Every file is named after the label on the chip's silkscreen, so `uLIT.bin`
goes into the 28C256 marked `28C256 uLIT`. The nine microcode images are 256
bytes: the boards ground the address lines above A7, so the rest of the chip is
never read.
"""

import sys
from pathlib import Path

# The microprogram is the sequencer's, so it lives with the circuits.
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "logisim" / "python")
)

from kone_microcode import assemble  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "roms"
DEFAULT_PROGRAM = Path(__file__).resolve().parents[2] / "bin" / "display.bin"

BANKS = ("LIT", "AOP", "NEXT", "ALT", "WE", "SEL", "MISC")


def roms(program):
    """-> [(chip label, image)] for the sequencer's nine and memory's one."""
    banks, dispatch_a, dispatch_b, _, _ = assemble()
    out = [(f"u{tag}", bytes(banks[i])) for i, tag in enumerate(BANKS)]
    out.append(("dispA", bytes(dispatch_a)))
    out.append(("dispB", bytes(dispatch_b)))
    out.append(("prog", program.read_bytes()))
    return out


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PROGRAM
    if not path.exists():
        sys.exit(f"no program image at {path} -- run `make examples` first")
    OUT.mkdir(exist_ok=True)
    for label, data in roms(path):
        (OUT / f"{label}.bin").write_bytes(data)
        print(f"{OUT / f'{label}.bin'} ({len(data)} bytes)")
