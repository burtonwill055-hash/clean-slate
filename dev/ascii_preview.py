"""Print coarse ASCII previews of screenshots (for terminals / agents)."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

CHARS = " .:-=+*#%@"
OUT = Path("/tmp/opencode/clean-slate-shots")


def render(path: Path, width: int = 110) -> str:
    image = Image.open(path).convert("L")
    height = max(1, int(image.height / image.width * width * 0.48))
    image = image.resize((width, height))
    pixels = list(image.getdata())
    lines = []
    for row in range(height):
        line = "".join(
            CHARS[min(len(CHARS) - 1, pixels[row * width + col] * len(CHARS) // 256)]
            for col in range(width)
        )
        lines.append(line)
    return "\n".join(lines)


if __name__ == "__main__":
    paths = sorted(OUT.glob("*.png"))
    if len(sys.argv) > 1:
        paths = [OUT / name for name in sys.argv[1:]]
    for path in paths:
        print(f"\n===== {path.name} ({Image.open(path).size[0]}x{Image.open(path).size[1]}) =====")
        print(render(path))
