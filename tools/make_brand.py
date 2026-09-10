#!/usr/bin/env python3
"""Generate the brand assets Home Assistant and HACS look for.

Since Home Assistant 2026.3.0 a custom component may ship its own brand icons
rather than submitting them to the home-assistant/brands repository, whose
`custom_integrations` folder is now marked legacy.

    python3 tools/make_brand.py

Writes custom_components/tripshot_tracker/brand/{icon,icon@2x,logo,logo@2x}.png
at the sizes Home Assistant specifies: 256px, and 512px for the hDPI variant,
square, PNG, trimmed.

The mark is TripShot's, reproduced from the publicly distributed Android client
to identify the service this integration talks to. It is NOT covered by this
project's MIT licence -- see NOTICE and the LICENSE carve-out. Everything is
measured from the app's own launcher icon rather than approximated:

    tile            96x96 (mipmap), rounded square
    background      #AA1EF5
    mark            white chevron, 46% x 40% of the tile, centred
    corner radius   ~8% of the tile

The high-resolution chevron comes from the adaptive-icon foreground layer
(108dp at 3x = 324px), so nothing is upscaled from the 96px tile.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "custom_components" / "tripshot_tracker" / "brand"

#: Adaptive-icon foreground: the chevron, white on transparent, 324x324.
FOREGROUND = ROOT / "nocommit" / "resextract" / "res" / "Lf.png"

BACKGROUND = (0xAA, 0x1E, 0xF5)
MARK_WIDTH_FRAC = 0.46          # measured off the shipped launcher icon
CORNER_RADIUS_FRAC = 0.08


def build(size: int) -> Image.Image:
    if not FOREGROUND.exists():
        raise SystemExit(
            f"missing {FOREGROUND}.\n"
            "Extract the APK resources first:\n"
            "  cd nocommit && unzip -o -q <apk> 'res/*' -d resextract"
        )

    s = size * 4  # supersample for clean curves, then downscale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle(
        [0, 0, s, s], radius=CORNER_RADIUS_FRAC * s, fill=(*BACKGROUND, 255))

    mark = Image.open(FOREGROUND).convert("RGBA").crop(
        Image.open(FOREGROUND).convert("RGBA").getbbox())
    target_w = int(MARK_WIDTH_FRAC * s)
    target_h = int(target_w * mark.height / mark.width)
    mark = mark.resize((target_w, target_h), Image.LANCZOS)

    img.alpha_composite(mark, ((s - target_w) // 2, (s - target_h) // 2))
    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, size in (("icon.png", 256), ("icon@2x.png", 512),
                       ("logo.png", 256), ("logo@2x.png", 512)):
        build(size).save(OUT / name, "PNG", optimize=True)
        print(f"  {name:14} {size}x{size}  {(OUT / name).stat().st_size:>6} bytes")


if __name__ == "__main__":
    main()
