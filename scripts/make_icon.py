"""Generate the app icon (circular crop) from assets/icon-source.jpg.

Run after replacing the source image:
    .venv\\Scripts\\python.exe scripts\\make_icon.py
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

BASE = Path(__file__).resolve().parents[1]
SOURCE = BASE / "assets" / "icon-source.jpg"
ICO = BASE / "assets" / "neolunaruby.ico"
PNG = BASE / "assets" / "neolunaruby.png"

# Drop the top of the frame (window trim above the plush) and keep the rest.
TOP_CROP = 0.20
SUPERSAMPLE = 4
SIZE = 256


def main() -> None:
    if not SOURCE.is_file():
        sys.exit(f"No source image at {SOURCE}")
    img = Image.open(SOURCE).convert("RGB")
    w, h = img.size

    img = img.crop((0, int(h * TOP_CROP), w, h))
    w, h = img.size

    # Centered square from the remaining frame, then a circular mask.
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))

    big = SIZE * SUPERSAMPLE
    img = img.resize((big, big), Image.LANCZOS)
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, big - 1, big - 1), fill=255)

    out = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    out = out.resize((SIZE, SIZE), Image.LANCZOS)

    out.save(PNG)
    out.save(ICO, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"wrote {PNG.name} and {ICO.name}")


if __name__ == "__main__":
    main()
