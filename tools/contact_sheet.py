"""Build contact sheets of the regenerated crops for visual review.

Each sheet tiles the finished images with their asset name and printed page, so a
whole chapter can be eyeballed at once for the failure modes that matter:
a diagram cut in half, a crop that drifted onto the neighbouring figure, or a
caption that belongs to a different figure number.

    python tools/contact_sheet.py --chapter chapter-06
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

WORKSPACE = Path(__file__).resolve().parents[1]

CELL_W, CELL_H = 470, 330
COLS = 3
LABEL_H = 20
PAD = 6


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--count", type=int, default=24)
    args = ap.parse_args()

    img_dir = WORKSPACE / "src" / args.chapter / "images"
    files = sorted(img_dir.glob("*.png"))[args.start:args.start + args.count]
    if not files:
        print("no images")
        return 1

    rows = (len(files) + COLS - 1) // COLS
    sheet = Image.new(
        "RGB",
        (COLS * (CELL_W + PAD), rows * (CELL_H + LABEL_H + PAD)),
        "white",
    )
    draw = ImageDraw.Draw(sheet)

    for i, path in enumerate(files):
        col, row = i % COLS, i // COLS
        x = col * (CELL_W + PAD)
        y = row * (CELL_H + LABEL_H + PAD)
        im = Image.open(path).convert("RGB")
        im.thumbnail((CELL_W, CELL_H))
        sheet.paste(im, (x + (CELL_W - im.width) // 2, y + LABEL_H))
        draw.text((x + 3, y + 4), path.stem, fill="black")
        draw.rectangle(
            [x, y, x + CELL_W, y + LABEL_H + CELL_H], outline="#bbbbbb"
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(f"{args.out}  ({len(files)} images)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
