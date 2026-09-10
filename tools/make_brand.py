#!/usr/bin/env python3
"""Generate the brand assets Home Assistant and HACS look for.

HACS requires an integration to either be listed in the home-assistant/brands
repository or ship its own assets. Shipping them keeps the icon working without
waiting on a pull request to another repo, and is what stops the integration
page showing "icon not available".

    python3 tools/make_brand.py

Writes custom_components/tripshot_tracker/brand/{icon,icon@2x,logo,logo@2x}.png.
Home Assistant expects icons square and trimmed: 256px, and 512px for @2x.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = (Path(__file__).resolve().parent.parent
       / "custom_components" / "tripshot_tracker" / "brand")

BG = (14, 99, 156)        # deep transit blue
BODY = (255, 255, 255)
GLASS = (14, 99, 156)
ACCENT = (249, 168, 37)   # amber, for the punctuality dial
TYRE = (33, 41, 54)


def draw(size: int) -> Image.Image:
    """A bus, with a clock face for the punctuality this measures."""
    s = size * 4  # supersample, then downscale for clean edges
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = s / 256.0  # design in a 256 grid

    d.rounded_rectangle([0, 0, s, s], radius=56 * u, fill=BG)

    # Bus body.
    d.rounded_rectangle([38 * u, 54 * u, 196 * u, 168 * u],
                        radius=22 * u, fill=BODY)
    # Windscreen band.
    d.rounded_rectangle([54 * u, 72 * u, 180 * u, 112 * u],
                        radius=10 * u, fill=GLASS)
    # Window divider.
    d.rectangle([ofs := 115 * u, 72 * u, ofs + 5 * u, 112 * u], fill=BODY)
    # Wheels.
    for cx in (72 * u, 156 * u):
        d.ellipse([cx - 16 * u, 152 * u, cx + 16 * u, 184 * u], fill=TYRE)
        d.ellipse([cx - 6 * u, 162 * u, cx + 6 * u, 174 * u], fill=BODY)

    # Punctuality dial, overlapping the lower-right corner of the bus.
    cx, cy, r = 198 * u, 196 * u, 46 * u
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BG)
    d.ellipse([cx - r + 7 * u, cy - r + 7 * u, cx + r - 7 * u, cy + r - 7 * u],
              fill=ACCENT)
    # Hands at roughly ten-past-two: reads as a clock at any size.
    d.line([cx, cy, cx, cy - 23 * u], fill=BG, width=int(7 * u))
    d.line([cx, cy, cx + 18 * u, cy + 10 * u], fill=BG, width=int(7 * u))

    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, size in (("icon.png", 256), ("icon@2x.png", 512),
                       ("logo.png", 256), ("logo@2x.png", 512)):
        img = draw(size)
        img.save(OUT / name, "PNG", optimize=True)
        print(f"  {name:14} {size}x{size}  {(OUT / name).stat().st_size:>6} bytes")


if __name__ == "__main__":
    main()
