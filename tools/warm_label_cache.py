"""Pre-populate the caption OCR cache for a range of pages.

Caption OCR is the slow part of resnap_crops.py. Running it in page ranges keeps
each invocation short and makes the work resumable: results are memoised next to
the rendered pages, so a later full run reuses them.

    python tools/warm_label_cache.py --first 15 --last 60
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import figure_blocks as fb  # noqa: E402
import figure_labels as fl  # noqa: E402


def one(job) -> str:
    page, cache = job
    png = Path(cache) / f"p-{page:03d}.png"
    if not png.exists():
        return f"p{page}: no render"
    labels = fl.find_labels(fb.load_page(png), f"{page:03d}", cache)
    return f"p{page}: {len(labels)} captions"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", type=int, required=True)
    ap.add_argument("--last", type=int, required=True)
    ap.add_argument("--cache", type=Path,
                    default=Path(tempfile.gettempdir()) / "opamp-pages")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = ap.parse_args()

    # tesseract is internally multithreaded; let the process pool provide the
    # parallelism instead, or the two fight over a small core count.
    os.environ.setdefault("OMP_THREAD_LIMIT", "1")

    pages = [
        p for p in range(args.first, args.last + 1)
        if (args.cache / f"p-{p:03d}.png").exists()
        and not (args.cache / f"labels-{p:03d}.json").exists()
    ]
    if not pages:
        print("cache already warm for this range")
        return 0
    jobs = [(p, str(args.cache)) for p in pages]
    done = 0
    if args.jobs <= 1:
        for job in jobs:
            one(job)
            done += 1
    else:
        with Pool(args.jobs) as pool:
            for _ in pool.imap_unordered(one, jobs):
                done += 1
    print(f"warmed {done} pages in range {args.first}-{args.last}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
