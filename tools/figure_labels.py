"""Locate printed figure/table labels ("图 A.3", "表 7.2", "照片 4.1", "List 3.1").

Snapping a crop to a content block is only half the job: the seed coordinates in
the original crop scripts were often wrong enough that "the block the seed
overlaps" is the wrong figure. So we anchor on the page's own labels instead.

Full Chinese OCR of this scan is unreliable, but the *numeric* part of a caption
("A.3", "7.2", "3.1") is Latin text and survives tesseract at 2x upscale. We OCR
the short caption-like bands on a page, pull out the numbers, and use them to
decide which block belongs to which asset. The Chinese label word (图/表/照片) is
inferred from position instead of read: in this book figure captions sit *below*
the graphic and table captions sit *above* it.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image

import figure_blocks as fb

# "A.3", "7.12", "3.1" — the numeric core of a caption
# "A.3", "7.12" — the numeric core of a caption. The scan's OCR sometimes reads
# the separator dot as a letter, so accept a few look-alikes. The Chinese label
# glyph is often welded onto the number as a stray capital ("表 8.4" -> "K8.4"),
# which defeats \b, so allow a leading letter run in place of a word boundary.
NUM_RE = re.compile(r"(?:\b|(?<=[A-Z]))([A-Da-d]|\d{1,2})\s*[.,:lI|]\s*(\d{1,2})\b")
LIST_RE = re.compile(r"(?i)\bl\s*i\s*s\s*t\b")
# "8.1.3 ..." is a numbered section heading, not a caption
SECTION_RE = re.compile(r"^\W{0,4}\d{1,2}\s*[.,]\s*\d{1,2}\s*[.,]\s*\d")
# A number wrapped in brackets is an equation reference ("式(6.21)"), which body
# text uses freely; a caption never parenthesises its own number.
BRACKETED_RE = re.compile(r"[(\[{）]\s*[A-Da-d0-9]{1,2}\s*[.,]\s*\d{1,2}\s*[)\]}）]")


@dataclass(frozen=True)
class Label:
    """A caption line found on the page."""

    top: int
    bottom: int
    left: int
    right: int
    number: str          # normalised, e.g. "a.3" or "7.12"
    is_list: bool
    text: str

    @property
    def mid(self) -> float:
        return (self.top + self.bottom) / 2


def _ocr_page_words(img: Image.Image) -> list[tuple[int, int, int, int, str]]:
    """One tesseract pass over the whole page -> (left, top, right, bottom, word).

    Spawning tesseract per caption candidate was the dominant cost; a single TSV
    pass over the page is roughly an order of magnitude faster, and the word
    boxes let us reassemble any line we care about afterwards.
    """
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "page.png"
        img.save(src)
        out = subprocess.run(
            ["tesseract", str(src), str(Path(tmp) / "out"),
             "--psm", "6", "-l", "eng", "tsv"],
            capture_output=True, text=True,
        )
        tsv = Path(tmp) / "out.tsv"
        if not tsv.exists():
            return []
        words = []
        for line in tsv.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
            f = line.split("\t")
            if len(f) < 12:
                continue
            text = f[11].strip()
            if not text:
                continue
            try:
                l, t, w, h = (int(f[6]), int(f[7]), int(f[8]), int(f[9]))
            except ValueError:
                continue
            words.append((l, t, l + w, t + h, text))
        return words


def _line_text(words, box: tuple[int, int, int, int]) -> str:
    """Reassemble the OCR words whose centres fall inside a band."""
    inside = [
        w for w in words
        if box[1] <= (w[1] + w[3]) / 2 <= box[3]
        and box[0] - 10 <= (w[0] + w[2]) / 2 <= box[2] + 10
    ]
    inside.sort(key=lambda w: w[0])
    return " ".join(w[4] for w in inside)


def find_labels(img: Image.Image, cache_key: str | None = None,
                cache_dir: Path | None = None) -> list[Label]:
    """OCR every caption-shaped band and keep the plausible figure captions.

    Captions in this book are single short lines, inset from both margins
    (centred), that begin with the figure number — the Chinese label word
    (图/表/照片) is dropped by the English-only OCR, so the number lands at the
    start of the line. Justified body text reaches both margins, display
    equations tag their number at the *end* of the line, and numbered section
    headings carry a third number group; all three are excluded.

    OCR dominates the runtime, so results are memoised per page on disk when a
    cache location is given.
    """
    cache_file = None
    if cache_key and cache_dir:
        cache_file = Path(cache_dir) / f"labels-{cache_key}.json"
        if cache_file.exists():
            return [Label(**d) for d in json.loads(cache_file.read_text())]

    bands = fb.find_bands(img)
    mask = fb._ink_mask(img)
    col_l, col_r = fb._column_extent(mask)
    col_l, col_r = fb.text_measure(bands, col_l, col_r)
    col_w = max(1, col_r - col_l)
    # The body measure, taken from the page's own widest line of type. A
    # paragraph's first line is indented, so it clears the inset test below, and
    # this book's prose often opens a paragraph with "表 5.1 所示的…" — which then
    # reads exactly like a table caption. A caption is set short; a body line runs
    # the full measure, so width is what separates them.
    text_widths = [b.right - b.left for b in bands if b.is_text]
    body_w = max(text_widths) if text_widths else col_w
    candidates = []
    for b in bands:
        if not b.is_text or b.height > fb.TEXT_LINE_MAX_H + 8:
            continue
        if (b.right - b.left) >= body_w * 0.9:
            continue
        left_inset = (b.left - col_l) / col_w
        right_inset = (col_r - b.right) / col_w
        # A caption is centred, so it clears both margins by a real amount. A
        # paragraph's first line is indented too, so its left inset looks the
        # same — but it is justified, so its right edge lands on the margin. This
        # book opens paragraphs with "图 6.14 所示…" constantly, and at 0.03 those
        # lines were being read as the caption for a figure pages away.
        if left_inset < 0.06 or right_inset < 0.08:
            continue
        candidates.append(b)

    labels: list[Label] = []
    if candidates:
        words = _ocr_page_words(img)
        for b in candidates:
            text = _line_text(words, (b.left, b.top, b.right, b.bottom))
            if SECTION_RE.match(text):
                continue
            m = NUM_RE.search(text)
            if not m or m.start() > 6:
                continue
            # "式(6.21)" and friends: an equation reference inside running text
            if BRACKETED_RE.search(text):
                continue
            number = f"{m.group(1).lower()}.{int(m.group(2))}"
            labels.append(Label(
                top=b.top, bottom=b.bottom, left=b.left, right=b.right,
                number=number, is_list=bool(LIST_RE.search(text)), text=text,
            ))

    if cache_file is not None:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(
            json.dumps([asdict(l) for l in labels]), encoding="utf-8"
        )
    return labels


# asset stem -> printed number, e.g. "fig-07-12" -> "7.12", "fig-a-03" -> "a.3"
ASSET_RE = re.compile(
    r"^(fig|table|photo|list)-([0-9]{2}|[a-d])-([0-9]{2})([a-z])?$"
)


def asset_number(stem: str) -> tuple[str, str] | None:
    """Split an asset filename into (kind, printed number)."""
    m = ASSET_RE.match(stem)
    if not m:
        return None
    kind, chap, num = m.group(1), m.group(2), m.group(3)
    chap_norm = chap.lower() if chap.isalpha() else str(int(chap))
    return kind, f"{chap_norm}.{int(num)}"


def match_label(labels: list[Label], stem: str) -> Label | None:
    """Find the caption on this page that belongs to the given asset."""
    parsed = asset_number(stem)
    if not parsed:
        return None
    kind, number = parsed
    hits = [l for l in labels if l.number == number]
    if not hits:
        return None
    if kind == "list":
        listy = [l for l in hits if l.is_list]
        if listy:
            return listy[0]
    return hits[0]


def block_for_label(
    img: Image.Image, label: Label, kind: str, strict: bool = False
) -> fb.Block | None:
    """The figure block a caption refers to.

    Figures and photos are captioned underneath, tables and listings above, so
    we look on the appropriate side of the caption line first and fall back to
    the other side if nothing is there.

    With `strict` the fallback is dropped and the caption must be *adjacent* to its
    block on the expected side. The English-only OCR discards the label glyph, so
    "表 8.1" and "图 8.1" read alike, and searching the whole book for a number will
    happily hand a table the identically-numbered figure. Adjacency separates them:
    a figure caption has its graphic close above it, a table caption close below,
    and neither has one close on the other side. Cross-page relocation insists on
    this, because there the number is the only other evidence available.
    """
    blocks = fb.find_blocks(img)
    if not blocks:
        return None
    # A block "contains" the caption band when the caption was merged into it.
    # For a figure that is proof they belong together — snap() pulls a figure's
    # caption inside the block — so the case is decisive even under `strict`. For a
    # table it proves the opposite: a table's caption is set above its block and is
    # never absorbed, so a "表 8.2" that turns out to be inside a block is really
    # the identically-numbered 图 8.2, whose glyph the OCR dropped.
    containing = [
        b for b in blocks
        if b.top - 6 <= label.top and b.bottom + 6 >= label.bottom
    ]
    if containing:
        if strict and kind not in {"fig", "photo"}:
            return None
        return min(containing, key=lambda b: b.bottom - b.top)

    above = [b for b in blocks if b.bottom <= label.top + 6]
    below = [b for b in blocks if b.top >= label.bottom - 6]

    def gap(b: fb.Block) -> int:
        return min(abs(label.top - b.bottom), abs(b.top - label.bottom))

    if kind in {"fig", "photo"}:
        want, other = above, below
    else:
        want, other = below, above
    if strict:
        near = [b for b in want if gap(b) <= fb.CAPTION_GAP_MAX]
        if not near or any(gap(b) <= fb.CAPTION_GAP_MAX for b in other):
            return None
        return min(near, key=gap)
    for group in (want, other):
        if group:
            return min(group, key=gap)
    return None
