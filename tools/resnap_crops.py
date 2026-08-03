"""Recompute every figure crop in tools/crop_*.py by snapping to real page content.

Usage:
    python tools/resnap_crops.py --pdf <scan.pdf> [--apply] [--report out.json]

Reads the CROPS table out of each crop script (AST literal, no import needed, so
the scripts' Windows-only default paths do not matter), renders the pages it
needs at 200 dpi, snaps each seed rectangle onto the figure block that actually
carries the graphic, and reports how far each crop moved.

With --apply the corrected coordinates are written back into the crop scripts in
place, so `git diff` shows exactly which figures were repaired.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import figure_blocks as fb  # noqa: E402
import figure_labels as fl  # noqa: E402

TOOLS = Path(__file__).resolve().parent
WORKSPACE = TOOLS.parent

SCRIPTS = [
    ("chapter-01", TOOLS / "crop_chapter1_figures.py"),
    ("chapter-02", TOOLS / "crop_chapter2_figures.py"),
    ("chapter-03", TOOLS / "crop_chapter3_assets.py"),
    ("chapter-03", TOOLS / "crop_appendix_ab_assets.py"),
    ("chapter-04", TOOLS / "crop_chapter4_assets.py"),
    ("chapter-05", TOOLS / "crop_chapter5_assets.py"),
    ("chapter-06", TOOLS / "crop_chapter6_assets.py"),
    ("chapter-07", TOOLS / "crop_chapter7_assets.py"),
    ("chapter-08", TOOLS / "crop_chapter8_assets.py"),
]

# Assets that are deliberately partial: a wide table or a long code listing that
# the book itself continues across pages, split here with an a/b/c suffix.
# Snapping would merge each piece into its neighbour or shrink it to one band, so
# these keep their hand-set coordinates.
SUFFIXED_RE = re.compile(r"^(?:table|list)-(?:[0-9]{2}|[a-d])-[0-9]{2}[a-z]$")

# Coordinates verified by eye that automatic detection gets wrong, because the
# page's own printed caption is misleading or unreadable:
#   fig-03-06   was recorded against p87, which holds List 3.6; 图 3.6 is on p74
#   fig-06-14   图 6.14 is on p180, a page no crop script referenced, so it was
#               never rendered and the number could not be found anywhere
#   fig-06-15   图 6.15 is on p181, below the equations the old seed pointed at
#   fig-06-16   图 6.16 is on p182, another page no crop script referenced, so it
#               is absent from the caption index and the seed drifts to p183's plot
#   fig-06-17   图 6.17's caption sits above the plot and OCRs as "6.26" from the
#               "依据式(6.26)" callout printed inside the graph
#   fig-06-21   the only "6.21" the OCR finds is the equation reference 式(6.21)
#               on p181, so the index sends the crop to the wrong page entirely
#   list-03-03  a listing set entirely in monospace type, with no graphic band to
#   list-03-04  anchor on, so snapping finds only one line of it
#   list-b-01   likewise, and its seed was a copy of fig-b-01's, so it showed the
#               figure above instead of the netlist; coordinates read off p108
PINNED = {
    "fig-03-06", "fig-06-14", "fig-06-15", "fig-06-16", "fig-06-17",
    "fig-06-21", "list-03-03", "list-03-04", "list-b-01",
    # Same-page split assets whose rough rectangles intentionally select
    # separate regions and must not be reassigned by collision ordering.
    "fig-06-26", "fig-06-27", "table-07-01", "table-07-02",
    "table-07-03",
}

OCR_AVAILABLE = shutil.which("tesseract") is not None


def is_manual(stem: str) -> bool:
    return stem in PINNED or bool(SUFFIXED_RE.match(stem))


def build_caption_index(pages, cache) -> dict[str, list[tuple[int, int]]]:
    """number -> [(page, caption top), ...] for the whole book.

    Some assets were recorded against the wrong page entirely, so knowing where
    each printed number actually appears lets us relocate across pages, not just
    within one.
    """
    index: dict[str, list[tuple[int, int]]] = {}
    if not OCR_AVAILABLE:
        return index
    for page in sorted(pages):
        png = Path(cache) / f"p-{page:03d}.png"
        if not png.exists():
            continue
        for lab in fl.find_labels(fb.load_page(png), f"{page:03d}", cache):
            index.setdefault(lab.number, []).append((page, lab.top))
    return index


def resolve(img, stem: str, seed: tuple[int, int, int, int],
            cache_key: str | None = None, cache_dir=None,
            number: str | None = None):
    """Best crop for one asset, plus a confidence verdict.

    The seed rectangle decides *which* graphic is meant; the pixels decide its
    true extent. The page's own printed caption is then used as an independent
    check on identity: if the block we picked carries (or abuts) a caption whose
    number matches the asset name, the crop is confirmed. A mismatch means the
    original coordinates probably pointed at the wrong figure, so the asset is
    flagged for a human look rather than silently rewritten.

    `number` overrides the number parsed from the filename, for the assets whose
    filename and printed number disagree.
    """
    parsed = fl.asset_number(stem)
    kind = parsed[0] if parsed else "fig"
    # tables and listings carry their caption above the block, figures below
    blk = fb.snap(img, seed, caption_above=kind in {"table", "list"})
    if blk is None:
        return None, "none"

    if not parsed:
        return blk, "unchecked"
    number = number or parsed[1]

    labels = (fl.find_labels(img, cache_key, cache_dir)
              if OCR_AVAILABLE else [])
    if not labels:
        return blk, "unchecked"

    # Which caption belongs to this block? Figures and photos are captioned
    # underneath, so snap() has already pulled the caption inside the block;
    # anything above the block is the *previous* figure's caption and must not
    # be counted. Tables and listings are captioned above, so for those we also
    # accept a caption sitting just before the block.

    def belongs(lab: fl.Label) -> bool:
        if blk.top - 6 <= lab.top and lab.bottom <= blk.bottom + 6:
            return True
        if abs(lab.top - blk.bottom) <= fb.CAPTION_GAP_MAX and centred(lab):
            return True
        if kind in {"table", "list"}:
            return abs(blk.top - lab.bottom) <= fb.CAPTION_GAP_MAX
        return False

    def centred(lab: fl.Label) -> bool:
        """Is this line set under the block, the way a caption is?

        A numbered line just below the block is the figure's own caption only if
        it sits under the figure. The next *section heading* is also numbered
        ("B.8 被电流源驱动的基极接地电路"), also read as a label, and can fall within
        CAPTION_GAP_MAX of a correct crop — but it is set flush to the text
        margin, well left of a centred figure. p111 图 B.5 was flagged as a
        mismatch against that heading and so was never repaired.
        """
        span = max(1, blk.right - blk.left)
        mid = (lab.left + lab.right) / 2
        return abs(mid - (blk.left + blk.right) / 2) <= span * 0.2

    own = [lab for lab in labels if belongs(lab)]

    def matches(lab: fl.Label) -> bool:
        if lab.number == number:
            return True
        # The Chinese label glyph (图/表) sometimes OCRs as a leading digit, so
        # "图 6.26" can read as "16.26". Accept a number whose tail matches.
        return lab.number.endswith("." + number.split(".")[1]) and (
            lab.number.split(".")[0].endswith(number.split(".")[0])
        )

    if own and any(matches(lab) for lab in own):
        return blk, "confirmed"

    # The block we landed on carries the wrong number, so the seed pointed at
    # the wrong figure. If this page prints the number we want, relocate to that
    # caption's block instead.
    wanted = [lab for lab in labels if matches(lab)]
    # "List" is Latin and really is read by the OCR, unlike 图/表; when a listing's
    # number appears twice on a page, only the caption that says "List" is its own.
    if kind == "list":
        wanted = [lab for lab in wanted if lab.is_list] or wanted
    if wanted:
        # The caption must sit adjacent to a block on the side its kind is
        # captioned from, and have nothing on the other side. Without that, p71's
        # "续表 3.4" — a table continuation header, with its table *below* it — was
        # accepted as the caption of 图 3.4, whose graph is further down the page,
        # and the crop jumped to the wrong content entirely. When no block passes,
        # the seed's own block is kept: a caption we cannot place is no evidence.
        relocated = fl.block_for_label(img, wanted[0], kind, strict=True)
        if relocated is not None:
            return relocated, "relabelled"

    # A caption whose chapter component disagrees with the asset's chapter is
    # almost always a bad read rather than a real identity clash, so don't raise
    # a false alarm on it.
    chapter_part = number.split(".")[0]
    credible = [
        lab for lab in own if lab.number.split(".")[0] == chapter_part
    ]
    if not credible:
        return blk, "unchecked"
    return blk, "mismatch:" + ",".join(sorted({lab.number for lab in credible}))


def read_crops(path: Path) -> dict[str, tuple[int, ...]]:
    """Pull the CROPS dict out of a crop script without executing it."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if "CROPS" in names:
                return {
                    k: tuple(v)
                    for k, v in ast.literal_eval(node.value).items()
                }
    raise SystemExit(f"no CROPS table in {path.name}")


MD_REF_RE = re.compile(
    r"!\[\s*(?:图|表|照片|List)\s*([A-Da-d]|\d{1,2})\s*[.．]\s*(\d{1,2})[^\]]*\]"
    r"\(\s*(?:\./)?images/([A-Za-z0-9-]+)\.png\s*\)"
)


def printed_numbers() -> dict[str, str]:
    """asset stem -> the number the book actually prints, per the markdown.

    Asset filenames do not always agree with the printed numbering: the table
    files run one ahead of the 表 numbers from 表 7.2 onward, because 表 7.2 is
    continued on a second page and was saved as two files. The markdown captions
    were transcribed from the scan, so they are the authority on what each crop is
    supposed to show — and the caption check needs that, or every table after the
    split reports a false mismatch against the page it correctly landed on.
    """
    out: dict[str, str] = {}
    for md in sorted(WORKSPACE.glob("src/**/*.md")):
        for chap, num, stem in MD_REF_RE.findall(md.read_text(encoding="utf-8")):
            chap_norm = chap.lower() if chap.isalpha() else str(int(chap))
            out.setdefault(stem, f"{chap_norm}.{int(num)}")
    return out


def render(pdf: Path, pages: set[int], cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    missing = sorted(p for p in pages if not (cache / f"p-{p:03d}.png").exists())
    if not missing:
        return
    # render in contiguous runs to keep the number of pdftoppm calls small
    runs: list[tuple[int, int]] = []
    start = prev = missing[0]
    for p in missing[1:]:
        if p == prev + 1:
            prev = p
            continue
        runs.append((start, prev))
        start = prev = p
    runs.append((start, prev))
    for first, last in runs:
        subprocess.run(
            [
                "pdftoppm", "-f", str(first), "-l", str(last),
                "-r", "200", "-png", str(pdf), str(cache / "p"),
            ],
            check=True,
        )


def analyse(job):
    """Worker: resolve one asset. Returns a plain dict (picklable)."""
    chapter, script_name, name, seed, cache, index, printed = job
    page, l, t, r, b = seed
    stem = name.removesuffix(".png")
    base = {
        "chapter": chapter, "script": script_name, "asset": stem,
        "page": page, "old": [l, t, r, b], "old_page": page,
    }
    if is_manual(stem):
        return {**base, "new": [l, t, r, b], "shift": 0,
                "how": "manual", "status": "manual"}
    page_png = Path(cache) / f"p-{page:03d}.png"
    if not page_png.exists():
        return {**base, "new": [l, t, r, b], "shift": 0,
                "how": "none", "status": "missing-page"}
    img = fb.load_page(page_png)
    blk, how = resolve(img, stem, (l, t, r, b), f"{page:03d}", cache,
                       printed.get(stem))

    # The page recorded in the crop table is authoritative. OCR often confuses
    # a nearby continuation, equation, or section heading with the requested
    # caption. Silently moving to that label can select a different asset (for
    # example, Fig. 3.1 was moved onto the page containing Table 3.1). This
    # repair pass refines the rectangle on the recorded page only; page changes
    # must be made explicitly by a human.

    if blk is None:
        return {**base, "new": [l, t, r, b], "shift": 0,
                "how": "none", "status": "failed"}
    new = blk.as_box()
    shift = max(abs(new[0] - l), abs(new[1] - t),
                abs(new[2] - r), abs(new[3] - b))
    status = "same" if shift <= 15 else ("nudged" if shift <= 60 else "moved")
    return {**base, "new": list(new), "shift": shift,
            "how": how, "status": status}


def resolve_collisions(results, cache) -> int:
    """Give each asset on a page its own block, in printed order.

    Two assets can snap to the same block when a caption line gets absorbed into
    the graphic above it, leaving the lower figure without its own anchor. Within
    a page, figure numbers run top to bottom, so when several assets share a page
    we assign them to that page's blocks in order to break the tie. Assets whose
    own caption already confirmed them keep their block.

    Only assets of the same kind contest a block. A table and a figure that happen
    to carry the same number ("表 8.2" and "图 8.2") are indistinguishable to the
    English-only OCR, so they collide constantly — but they are different objects
    on different pages, and reassigning one to the other's neighbouring block just
    turns one wrong crop into two.
    """
    fixed = 0
    by_page: dict[tuple[str, int, str], list[dict]] = {}
    for r in results:
        if r["status"] in {"manual", "failed", "missing-page"}:
            continue
        parsed = fl.asset_number(r["asset"])
        kind = parsed[0] if parsed else "?"
        by_page.setdefault((r["chapter"], r["page"], kind), []).append(r)

    for (_, page, _), group in by_page.items():
        boxes = [tuple(r["new"]) for r in group]
        if len(group) < 2 or len(set(boxes)) == len(boxes):
            continue

        png = Path(cache) / f"p-{page:03d}.png"
        if not png.exists():
            continue
        blocks = sorted(fb.find_blocks(fb.load_page(png)), key=lambda b: b.top)

        def order_key(r):
            parsed = fl.asset_number(r["asset"])
            if not parsed:
                return (99,)
            chap, num = parsed[1].split(".")
            return (chap, int(num))

        ordered = sorted(group, key=order_key)
        taken = {tuple(r["new"]) for r in ordered if r["how"] == "confirmed"}
        for r in ordered:
            if r["how"] == "confirmed":
                continue
            box = tuple(r["new"])
            if box not in taken:
                taken.add(box)
                continue
            # lost the tie: claim the next unused block below the contested one
            floor = box[1]
            for blk in blocks:
                cand = blk.as_box()
                if cand in taken or blk.top < floor:
                    continue
                r["new"] = list(cand)
                r["how"] = "ordered"
                r["status"] = "moved"
                taken.add(cand)
                fixed += 1
                break
    return fixed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--cache", type=Path,
                    default=Path(tempfile.gettempdir()) / "opamp-pages")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report", type=Path)
    ap.add_argument("--only", help="substring filter on asset name")
    ap.add_argument("--waiting", action="store_true",
                    help="process only tracked PNGs currently changed in git")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    args = ap.parse_args()

    tables = {script: read_crops(script) for _, script in SCRIPTS}
    pages = {c[0] for crops in tables.values() for c in crops.values()}
    render(args.pdf, pages, args.cache)

    index = build_caption_index(pages, str(args.cache))
    printed = printed_numbers()

    waiting = set()
    if args.waiting:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", "--", "src"], text=True
        )
        waiting = {Path(line.strip()).stem for line in out.splitlines()
                   if line.strip().endswith(".png")}

    jobs = []
    for chapter, script in SCRIPTS:
        for name, seed in tables[script].items():
            if args.only and args.only not in name:
                continue
            if args.waiting and name.removesuffix(".png") not in waiting:
                continue
            jobs.append((chapter, script.name, name, seed,
                         str(args.cache), index, printed))

    with Pool(args.jobs) as pool:
        results = pool.map(analyse, jobs, chunksize=1)

    if not args.only:
        # only meaningful when the whole book is in view
        n = resolve_collisions(results, str(args.cache))
        if n:
            print(f"resolved {n} same-page block collisions by printed order")

    by_script = {script.name: script for _, script in SCRIPTS}
    if args.apply:
        for _, script in SCRIPTS:
            updates = {
                r["asset"] + (".png" if r["asset"] + ".png"
                              in tables[script] else ""): (r["page"], *r["new"])
                for r in results
                if r["script"] == script.name
                and r["status"] not in {"manual", "failed", "missing-page"}
                and not r["how"].startswith("mismatch")
            }
            if updates:
                rewrite(script, updates)

    counts: dict[str, int] = {}
    hows: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        key = r["how"].split(":")[0]
        hows[key] = hows.get(key, 0) + 1
    print(f"\n{len(results)} assets")
    print("  extent: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print("  caption check: " +
          ", ".join(f"{k}={v}" for k, v in sorted(hows.items())))

    flagged = [r for r in results if r["how"].startswith("mismatch")]
    if flagged:
        print(f"\n  {len(flagged)} caption mismatches — the old coordinates may "
              f"have pointed at the wrong figure:")
        for r in flagged:
            print(f"    {r['asset']:<16} p{r['page']:<4} "
                  f"page says {r['how'].split(':')[1]:<8} {r['old']} -> {r['new']}")

    big = [r for r in results
           if r["status"] == "moved" and not r["how"].startswith("mismatch")]
    print(f"\n  {len(big)} crops substantially resized/repositioned")

    if args.report:
        args.report.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"report: {args.report}")
    return 0


def rewrite(script: Path, updates: dict[str, tuple[int, int, int, int, int]]) -> None:
    """Replace the coordinate tuples for the given assets, keeping comments."""
    text = script.read_text(encoding="utf-8")
    for name, coords in updates.items():
        pat = re.compile(
            r'(^\s*"' + re.escape(name) + r'"\s*:\s*)\([^)]*\)',
            re.MULTILINE,
        )
        new = "(" + ", ".join(str(c) for c in coords) + ")"
        text, n = pat.subn(lambda m: m.group(1) + new, text, count=1)
        if n == 0:
            print(f"  !! could not rewrite {name} in {script.name}")
    script.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
