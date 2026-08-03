"""Regenerate every figure PNG from the crop tables in tools/crop_*.py.

The individual crop scripts hard-code Windows paths from the original authoring
machine. This driver reads just their CROPS tables (as literals, without
importing them) and writes the images to src/chapter-*/images/, so the crops can
be rebuilt on any platform with poppler and Pillow installed.

    python tools/rebuild_images.py --pdf "<scan>.pdf"
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

from resnap_crops import SCRIPTS, read_crops, render  # noqa: E402

WORKSPACE = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--cache", type=Path,
                    default=Path(tempfile.gettempdir()) / "opamp-pages")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--waiting", action="store_true",
                    help="regenerate only tracked PNGs currently changed in git")
    ap.add_argument("--only", help="substring filter on asset name")
    args = ap.parse_args()

    tables = {script: read_crops(script) for _, script in SCRIPTS}
    pages = {c[0] for crops in tables.values() for c in crops.values()}
    render(args.pdf, pages, args.cache)

    waiting = set()
    if args.waiting:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", "--", "src"], text=True
        )
        waiting = {Path(line.strip()).stem for line in out.splitlines()
                   if line.strip().endswith(".png")}

    written = 0
    for chapter, script in SCRIPTS:
        dest = WORKSPACE / "src" / chapter / "images"
        dest.mkdir(parents=True, exist_ok=True)
        for name, (page, l, t, r, b) in tables[script].items():
            if args.only and args.only not in name:
                continue
            if args.waiting and name.removesuffix(".png") not in waiting:
                continue
            src = args.cache / f"p-{page:03d}.png"
            if not src.exists():
                print(f"  !! {name}: page {page} missing")
                continue
            stem = name if name.endswith(".png") else name + ".png"
            img = Image.open(src)
            w, h = img.size
            crop = img.crop((max(0, l), max(0, t), min(r, w), min(b, h)))
            if not args.dry_run:
                crop.save(dest / stem, "PNG", optimize=True)
            written += 1
    print(f"{'would write' if args.dry_run else 'wrote'} {written} images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
