"""Shared page-layout analysis used to snap figure crops onto real content blocks.

The book is a 200 dpi scan (1324 x ~1856 px per page). The original crop scripts
carried hand-typed pixel coordinates, and many of them were off: cutting a
diagram in half, drifting onto the neighbouring figure, or swallowing body text.

This module reconstructs the page layout from the pixels instead:

1. binarize the page and drop the scan border / page furniture,
2. collapse ink to a row profile and split the text column into "bands"
   (maximal runs of inked rows separated by whitespace gutters),
3. classify each band as body text or figure content, using the fact that body
   text in this book is a dense, near-full-width, fixed-height ribbon while
   circuit diagrams are sparse and ragged,
4. merge adjacent figure bands (plus the caption line that belongs to them) into
   figure blocks, and tighten the horizontal extent to the actual ink.

`snap(page_img, seed)` takes a rough seed rectangle and returns the figure block
it overlaps, which is what the crop scripts use.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image

# --- page geometry (200 dpi renders) -----------------------------------------
INK_THRESHOLD = 170        # 8-bit grey level below which a pixel counts as ink
BORDER_MARGIN = 40         # ignore the scanner's black edge
HEADER_LIMIT = 165         # running head / page number live above this row
FOOTER_MARGIN = 60         # ignore the very bottom of the sheet

# --- band segmentation --------------------------------------------------------
ROW_INK_MIN = 3            # a row needs this many ink pixels to be "inked"
GUTTER = 9                 # whitespace rows that separate two bands
TEXT_LINE_MAX_H = 46       # a single line of body type is no taller than this
TEXT_FILL_MIN = 0.34       # body text covers at least this fraction of column width
TEXT_DENSITY_MIN = 0.055   # body text ink density inside its own bbox
TEXT_INK_DARK = 0.14       # set type is this dark; line art never is
CAPTION_GAP_MAX = 60       # a caption sits at most this far from its figure
PAD = 12                   # breathing room added around a finished block


SIDE_GUTTER = 22           # blank columns separating a figure from text beside it


@dataclass(frozen=True)
class Band:
    top: int
    bottom: int
    left: int
    right: int
    is_text: bool
    fill: float = 0.0        # band width as a fraction of the text column
    density: float = 0.0     # ink density inside the band's own bbox

    @property
    def height(self) -> int:
        return self.bottom - self.top


EQ_MAX_H = 60              # a display equation is at most this tall
EQ_MAX_DENSITY = 0.05      # ...and this sparse, being mostly whitespace


def _is_display_equation(band: Band, col_w: int) -> bool:
    """A numbered display equation set on its own line.

    Band classification calls these graphics: they are sparse and their glyph
    heights are ragged. But they are type, not artwork, and a figure that grows
    up or down through one swallows a line of mathematics that belongs to the
    body (p182 图 6.16 took equation (6.25) with it). What distinguishes them
    from a real figure is the combination of all three: they reach across nearly
    the whole measure, they are only a line or two tall, and they are far sparser
    than any diagram that wide.
    """
    return (
        band.height <= EQ_MAX_H
        and (band.right - band.left) / col_w >= 0.75
        and band.density <= EQ_MAX_DENSITY
    )


@dataclass(frozen=True)
class Block:
    """A figure/table/listing region, caption included."""

    left: int
    top: int
    right: int
    bottom: int

    def as_box(self) -> tuple[int, int, int, int]:
        return (self.left, self.top, self.right, self.bottom)

    def overlap(self, other: tuple[int, int, int, int]) -> int:
        """Vertical overlap in pixels with a (l, t, r, b) rectangle."""
        return max(0, min(self.bottom, other[3]) - max(self.top, other[1]))


def load_page(path) -> Image.Image:
    return Image.open(path).convert("L")


def _ink_mask(img: Image.Image) -> np.ndarray:
    a = np.asarray(img)
    mask = a < INK_THRESHOLD
    # blank the scan border and page furniture so they cannot glue bands together
    mask[:HEADER_LIMIT, :] = False
    mask[-FOOTER_MARGIN:, :] = False
    mask[:, :BORDER_MARGIN] = False
    mask[:, -BORDER_MARGIN:] = False
    return mask


def _column_extent(mask: np.ndarray) -> tuple[int, int]:
    """Left/right edge of the printed text column."""
    cols = mask.sum(axis=0)
    inked = np.flatnonzero(cols > 4)
    if inked.size == 0:
        return BORDER_MARGIN, mask.shape[1] - BORDER_MARGIN
    return int(inked[0]), int(inked[-1]) + 1


def _is_internal_label(band: Band, col_w: int, core_l: int, core_r: int,
                       margin: int = 30) -> bool:
    """A short caption-like line that is really lettering inside the graphic.

    Axis titles ("频率/Hz"), callout boxes ("噪声增益"), node names — these are set
    type, and short and centred enough to pass every caption test, but they belong
    to the drawing. What marks them is that they sit inside the graphic's own
    horizontal span, which neither a caption nor a line of body text does. p203
    图 7.8 is the cautionary case: its "噪声增益" callout is printed halfway down the
    circuit, and reading it as text stopped the block from growing past it, so the
    crop kept only the formula underneath and lost the circuit entirely.

    `margin` is how far inside the span the line must sit. Judging a *trailing*
    line we want room to spare, so a genuine caption centred under a wide figure
    is not mistaken for lettering; judging a line we are bridging *between* two
    graphic bands, mere enclosure is enough.
    """
    return (
        band.is_text
        and band.height <= TEXT_LINE_MAX_H
        and (band.right - band.left) < col_w * 0.36
        and band.left > core_l + margin
        and band.right < core_r - margin
    )


def _bridges_graphic(bands: list[Band], k: int, step: int, gfx: set[int],
                     core: list[Band], col_w: int) -> bool:
    """Is bands[k] lettering sandwiched between two parts of one drawing?

    Growth stops at set type, which is right for a caption or a paragraph but
    wrong for a label printed inside the figure. If more graphic follows close by,
    and it horizontally encloses the label together with the core we came from,
    the label is interior and growth should continue.

    Several label bands can sit between two panels of a multi-part figure — an
    axis row and then a panel title, as under each of p85 图 3.17's three plots —
    so the search skips over a short run of them rather than only one.
    """
    b = bands[k]
    nxt = k + step
    prev = b
    far = None
    for _ in range(3):
        if not (0 <= nxt < len(bands)):
            return False
        cand = bands[nxt]
        # measure each step from the band before it, not from the label: a run of
        # two label lines plus the leading around them easily exceeds one gutter
        gap = prev.top - cand.bottom if step < 0 else cand.top - prev.bottom
        if gap > GUTTER * 4:
            return False
        if id(cand) in gfx:
            far = cand
            break
        if cand.height > TEXT_LINE_MAX_H:
            return False
        prev = cand
        nxt += step
    if far is None:
        return False
    span_l = min(far.left, min(x.left for x in core))
    span_r = max(far.right, max(x.right for x in core))
    return _is_internal_label(b, col_w, span_l, span_r, margin=0)


def text_measure(bands: list[Band], col_l: int, col_r: int) -> tuple[int, int]:
    """Left/right margin of the *body text*, not of all ink on the page.

    `_column_extent` measures every inked column, so a figure that is wider than
    the type block — a callout box, a wide plot's axis labels — pushes the
    apparent column out past the real margin. Captions and headings are then
    judged against the wrong measure: a heading that hugs the left text margin
    looks inset (so it passes for a centred caption), and a real caption looks
    too narrow to matter. Taking the margins from the page's own full-measure
    text lines fixes both.
    """
    text = [b for b in bands if b.is_text]
    if not text:
        return col_l, col_r
    widest = max(b.right - b.left for b in text)
    full = [b for b in text if (b.right - b.left) >= widest * 0.9]
    if not full:
        return col_l, col_r
    return min(b.left for b in full), max(b.right for b in full)


def find_bands(img: Image.Image) -> list[Band]:
    mask = _ink_mask(img)
    col_l, col_r = _column_extent(mask)
    col_w = max(1, col_r - col_l)

    row_ink = mask.sum(axis=1)
    inked = row_ink >= ROW_INK_MIN

    bands: list[Band] = []
    y = 0
    n = len(inked)
    while y < n:
        if not inked[y]:
            y += 1
            continue
        start = y
        gap = 0
        while y < n and gap < GUTTER:
            y += 1
            if y < n and inked[y]:
                gap = 0
            else:
                gap += 1
        end = y - gap
        if end <= start:
            continue

        sub = mask[start:end]
        cols = np.flatnonzero(sub.sum(axis=0) > 0)
        if cols.size == 0:
            continue
        left, right = int(cols[0]), int(cols[-1]) + 1
        height = end - start
        fill = (right - left) / col_w
        density = sub[:, left:right].mean() if right > left else 0.0

        is_text = (
            height <= TEXT_LINE_MAX_H
            and fill >= TEXT_FILL_MIN
            and density >= TEXT_DENSITY_MIN
        )
        # A paragraph's last line can be very short — "为零。" is 12% of the
        # measure — so the width test alone calls it a graphic and lets a figure
        # grow up through it. Type is much darker than line art at this scale
        # (~0.20 ink vs ~0.05), so a line-height band that dense is text too.
        if not is_text and height <= TEXT_LINE_MAX_H and density >= TEXT_INK_DARK:
            is_text = True
        # Two body lines whose descenders and ascenders nearly touch can be
        # glued into one band by a gap just under GUTTER. The merged band is
        # then too tall to pass for text and a figure can grow up through it.
        # Splitting on the widest interior blank run recovers both lines.
        if (
            not is_text
            and TEXT_LINE_MAX_H < height <= TEXT_LINE_MAX_H * 2
            and sub[:, left:right][inked[start:end]].mean() >= TEXT_INK_DARK
        ):
            inner = ~inked[start:end]
            best_len = best_at = 0
            run = 0
            for y2 in range(len(inner)):
                if inner[y2]:
                    run += 1
                    if run > best_len:
                        best_len, best_at = run, y2 + 1 - run
                else:
                    run = 0
            if best_len >= 4 and 0 < best_at < height:
                for s2, e2 in ((start, start + best_at),
                               (start + best_at + best_len, end)):
                    if e2 - s2 <= 0:
                        continue
                    part = mask[s2:e2]
                    pc = np.flatnonzero(part.sum(axis=0) > 0)
                    if pc.size == 0:
                        continue
                    pl, pr = int(pc[0]), int(pc[-1]) + 1
                    bands.append(Band(
                        s2, e2, pl, pr, True,
                        (pr - pl) / col_w, part[:, pl:pr].mean(),
                    ))
                continue
        bands.append(Band(start, end, left, right, is_text, fill, density))
    # splitting a merged band appends out of order, so restore top-to-bottom
    bands.sort(key=lambda b: b.top)
    return bands


def _line_pitch(bands: list[Band]) -> float:
    """Baseline-to-baseline distance of this page's body type."""
    tops = sorted(b.top for b in bands
                  if b.is_text and b.height <= TEXT_LINE_MAX_H)
    steps = [b - a for a, b in zip(tops, tops[1:]) if 0 < b - a <= 70]
    return float(np.median(steps)) if steps else float(TEXT_LINE_MAX_H)


def _is_isolated_line(bands: list[Band], k: int, pitch: float) -> bool:
    """Does bands[k] stand alone, rather than inside a paragraph?

    Some captions in this book run the full measure ("图 2.15 由图 2.9 的等效电路
    计算出的…" on p55), so the centred-and-inset test rejects them and the figure
    loses its caption. What still separates such a line from body copy is that it
    is set on its own: the next line of type is further away than the page's line
    pitch, because a paragraph follows after extra leading. A paragraph's own first
    line always has its second line at exactly the pitch.
    """
    nxt = next((b for b in bands[k + 1:]
                if b.is_text and b.height <= TEXT_LINE_MAX_H), None)
    return nxt is None or (nxt.top - bands[k].top) > pitch * 1.35


def _is_caption(band: Band, col_w: int, col_l: int, col_r: int) -> bool:
    """Is this line a figure caption rather than body text or a heading?

    Captions are centred under their figure, so they are inset from *both*
    margins by a similar amount. Body text is justified to the full measure, and
    section headings ("1.1.5 理想运算放大器") sit hard against the left margin with
    a large ragged gap on the right. Panel labels — "(a) ... (b) ..." — are also
    centred as a group and are wanted, so the test is deliberately symmetric
    rather than keyed to the caption word.
    """
    if not band.is_text or band.height > TEXT_LINE_MAX_H:
        return False
    left_inset = (band.left - col_l) / col_w
    right_inset = (col_r - band.right) / col_w
    if left_inset < 0.02 or right_inset < 0.02:
        return False       # reaches a margin: body text or a heading
    # centred: the two insets are comparable
    return abs(left_inset - right_inset) <= 0.22


def _has_interior_gutter(rows: np.ndarray, left: int, right: int) -> bool:
    """Is there a wide blank vertical channel inside this slice of rows?

    Used to tell a single justified body line from two columns of type set side by
    side. Inter-character spacing in this book never approaches SIDE_GUTTER, so any
    such channel means two separate blocks of text share these rows.
    """
    blank = rows[:, left:right].sum(axis=0) == 0
    run = 0
    for b in blank:
        run = run + 1 if b else 0
        if run >= SIDE_GUTTER:
            return True
    return False


def _isolated_row_run(full: np.ndarray, start: int, end: int,
                      pitch: float) -> bool:
    """Does the run of rows [start, end) stand alone on the page?

    The row-profile counterpart of `_is_isolated_line`, for the narrow-column
    caption pass, which works on raw rows rather than on bands. A caption that
    fills the whole measure looks like body copy (p223 图 8.5), but a paragraph's
    line always has another one following at the page's pitch.
    """
    rows = full[end:].sum(axis=1) >= ROW_INK_MIN
    nxt = np.flatnonzero(rows)
    if nxt.size == 0:
        return True
    return (end + int(nxt[0]) - start) > pitch * 1.35


def _widen_to_gutter(
    mask: np.ndarray, start: int, end: int, left: int, right: int,
    col_l: int, col_r: int
) -> tuple[int, int]:
    """Open a one-line search window out to the whitespace channels beside it.

    Walks outward from each edge over the line's own rows and stops just inside the
    first SIDE_GUTTER-wide run of blank columns, which is the gutter separating this
    figure from whatever is printed alongside. If no such channel is within reach,
    the full reach is used: there is nothing but blank paper out there.
    """
    blank = ~mask[start:end].any(axis=0)
    reach = SIDE_GUTTER * 2

    lo = max(col_l, left - reach)
    run = 0
    for x in range(left - 1, lo - 1, -1):
        run = run + 1 if blank[x] else 0
        if run >= SIDE_GUTTER:
            return x + run, _widen_right(blank, right, col_r, reach)
    return lo, _widen_right(blank, right, col_r, reach)


def _widen_right(blank: np.ndarray, right: int, col_r: int, reach: int) -> int:
    hi = min(col_r, right + reach)
    run = 0
    for x in range(right, hi):
        run = run + 1 if blank[x] else 0
        if run >= SIDE_GUTTER:
            return x - run + 1
    return hi


def _caption_within_column(
    mask: np.ndarray, top: int, bottom: int, left: int, right: int,
    col_l: int, col_r: int, pitch: float
) -> tuple[int, int, int]:
    """Extend `bottom` over the caption lines printed inside a narrow column.

    Restricted to the column's own width, a caption is again what it looks like
    elsewhere in the book: one or two short lines of set type, close below the
    graphic, that do not reach the column's edges. Returns the new bottom
    together with the horizontal extent of the caption lines taken, which can
    reach past the graphic on either side — p215 图 7.22's caption starts a little
    left of the drawing, so keeping the graphic's own width sliced the 图 glyph off
    the front of the line.
    A caption is often set a little wider than the graphic it sits under, so the
    search window is opened out towards the page margin the block already faces —
    nothing else is printed on that side — otherwise a caption overhanging the
    block by a few pixels reads as reaching the edge and is rejected (p215 图 7.22
    lost both of its caption lines that way).
    """
    # widen towards the nearer page margin, where only this figure is printed
    graphic_l, graphic_r = left, right
    if (left - col_l) <= (col_r - right):
        left = max(col_l, left - (right - left) // 3)
    else:
        right = min(col_r, right + (right - left) // 3)
    base_l, base_r = left, right
    band_w = right - left
    inked = mask[:, left:right].sum(axis=1) >= ROW_INK_MIN
    full = mask[:, col_l:col_r]
    y = bottom
    n = len(inked)
    taken = 0
    cap_l, cap_r = base_r, base_l
    # `bottom` is the block's last row as measured across the *text measure*, so over
    # this narrower window it can still land a row or two inside the graphic's own
    # ink — p133 图 4.22's does. Stepping over that leftover keeps the loop below from
    # taking it for a first caption line, failing the set-type test on its couple of
    # rows of pixels, and giving up before the real caption further down.
    #
    # Only stepped over when the block still ends in *artwork*: if its last band is
    # set type then the caption is already inside, and skipping onward makes the loop
    # consider the following section's heading instead, which fifteen figures then
    # grew into (p53 图 2.11 took in "发射极跟随器的小信号等效电路"). The two cases are
    # plain from the last band's ink density — 图 4.22's drawing is 0.07, 图 2.11's
    # caption line 0.22.
    tail_end = bottom
    while tail_end > top and not inked[tail_end - 1]:
        tail_end -= 1
    tail_start, run = tail_end, 0
    while tail_start > top and (inked[tail_start - 1] or run < GUTTER):
        run = 0 if inked[tail_start - 1] else run + 1
        tail_start -= 1
    tail_start += run
    if mask[tail_start:tail_end, base_l:base_r].mean() < TEXT_INK_DARK:
        sliver = 0
        while y < len(inked) and inked[y] and sliver < 4:
            y += 1
            sliver += 1
    while taken < 2 and y < n:
        # skip the gap to the next line
        gap = 0
        while y < n and not inked[y] and gap <= CAPTION_GAP_MAX:
            y += 1
            gap += 1
        if y >= n or gap > CAPTION_GAP_MAX:
            break
        start = y
        run = 0
        while y < n and (inked[y] or run < GUTTER):
            run = 0 if inked[y] else run + 1
            y += 1
        end = y - run
        if end - start > TEXT_LINE_MAX_H:
            break
        # A caption is centred on the graphic only roughly, so it can overhang the
        # search window: on p215 图 7.22 it starts some 40 px left of the drawing,
        # and on p133 图 4.22 just 8 px, which was still enough for the 图 glyph to
        # land against the window's edge and fail the inset test below. So open the
        # window out over this line, stopping at a SIDE_GUTTER-wide blank channel —
        # the same whitespace that separates a figure from the text column printed
        # beside it. Widening by a fixed margin instead crosses that channel and
        # pulls in the tail of a body line, which lands hard against the edge and
        # makes the caption read as reaching the margin (p133 图 4.22 and 图 4.23
        # both lost their captions that way). The channel is looked for on this
        # line's own rows: measured over the whole search window, ink from the
        # other lines fills the gutter in and no channel is ever found.
        left, right = _widen_to_gutter(mask, start, end, base_l, base_r,
                                       col_l, col_r)
        band_w = right - left
        line = mask[start:end, left:right]
        cols = np.flatnonzero(line.sum(axis=0) > 0)
        # The density is deliberately judged across the whole *base* search window
        # rather than inside the line's own bounding box, or inside the widened one.
        # Measuring it tightly instead admits the *next section's heading* as a second
        # caption line on some twenty figures (the cost is p174 图 6.5's second caption
        # line, just "负载电阻", which is lost) — and the widened window is tight in
        # the same way, since it stops at the whitespace flanking the line: judged
        # there, p16 图 1.1's following heading "1.1.5 理想运算放大器" reads as dense
        # set type and ten figures grew into their next heading.
        dens = mask[start:end, base_l:base_r]
        if cols.size == 0 or dens.mean() < TEXT_INK_DARK:
            break
        # ...and the first line taken is centred on the graphic, because that is what
        # a caption is. Skipping over the graphic's leftover sliver above (which the
        # 图 4.22 comment describes) means the loop no longer stops there, so on a
        # figure that already has its caption inside the block the next line up for
        # consideration is the following section's *heading* — set flush left and
        # short, so inset on both sides of a window that widened out over the blank
        # paper beside a centred figure, and otherwise indistinguishable. Measured
        # against the graphic it is plainly lopsided (p16 图 1.1's "1.1.5 理想运算放大器"
        # overhangs 127 px to the left and stops 187 px short on the right), while a
        # caption sits square under the drawing to within a few percent of its width.
        # Judged against the *graphic*, not the widened window: that window is pushed
        # out to one side by the widening above, which would make a properly centred
        # caption look lopsided (p215 图 7.22 lost both its lines that way).
        if taken == 0:
            over_l = (left + int(cols[0])) - graphic_l
            over_r = graphic_r - (left + int(cols[-1]))
            if abs(over_l - over_r) > (graphic_r - graphic_l) * 0.15:
                break
        # a caption is inset from both sides of its own column
        if cols[0] < band_w * 0.04 and (band_w - cols[-1]) < band_w * 0.04:
            break
        # ...and it is never flush with the page's own margin, whichever side. A
        # figure centred in the measure has blank paper down both sides, so the
        # window can widen all the way out to the margin, and then a *heading* below
        # the caption — set flush left, and short, so inset on the right — passes the
        # test above (p16 图 1.1 grew into "1.1.5 理想运算放大器", and nine others did
        # the same). A caption centred on its graphic always stops short of the margin.
        if (left + cols[0]) <= col_l + 2 or (left + cols[-1]) >= col_r - 2:
            break
        # ...and once the text resumes across the *whole* measure, the figure's
        # side-by-side layout has ended and we are back in body copy. A line that
        # merely *spans* the measure is not enough: while the side-by-side layout
        # lasts, the caption and the paragraph beside it together span it too. What
        # tells them apart is the gutter between them — a justified body line is
        # inked right across, with no wide interior gap.
        page_cols = np.flatnonzero(full[start:end].sum(axis=0) > 0)
        if page_cols.size and (
            page_cols[-1] - page_cols[0]
        ) >= (col_r - col_l) * 0.9 and not _has_interior_gutter(
            full[start:end], int(page_cols[0]), int(page_cols[-1]) + 1
        ) and not _isolated_row_run(full, start, end, pitch):
            break
        bottom = end
        cap_l = min(cap_l, left + int(cols[0]))
        cap_r = max(cap_r, left + int(cols[-1]) + 1)
        taken += 1
    return bottom, cap_l, cap_r


def _retighten_rows(
    mask: np.ndarray, top: int, bottom: int, left: int, right: int
) -> tuple[int, int]:
    """Re-derive the vertical extent once the horizontal one is final.

    The row profile that produced `top`/`bottom` was measured across the whole
    text measure. After a side text column is dropped, rows that were inked only
    by that column are now blank — typically the tail of the *previous* figure's
    caption, which would otherwise ride along at the top of the crop. Trim any
    such newly-empty rows, and drop a leading fragment that a wide gap separates
    from the real content.
    """
    sub = mask[top:bottom, left:right]
    if sub.size == 0:
        return top, bottom
    rows = np.flatnonzero(sub.sum(axis=1) >= ROW_INK_MIN)
    if rows.size == 0:
        return top, bottom
    first, last = int(rows[0]), int(rows[-1]) + 1

    # A wide blank gap near the start can mean the first inked run belongs to
    # something else — typically the tail of the neighbouring figure's caption,
    # left behind when the side text column was clipped away. Only drop it when
    # it really is a stray single line and the bulk of the block lies below it,
    # otherwise this would throw away the graphic and keep just its own caption.
    inked = sub.sum(axis=1) >= ROW_INK_MIN
    run_end = first
    while run_end < last and inked[run_end]:
        run_end += 1
    gap_end = run_end
    while gap_end < last and not inked[gap_end]:
        gap_end += 1
    if (
        run_end - first <= TEXT_LINE_MAX_H
        and gap_end - run_end > GUTTER * 4
        and last - gap_end > (run_end - first) * 3
    ):
        first = gap_end
    return top + first, top + last


def _looks_like_text_column(sub: np.ndarray) -> bool:
    """Is this slice a stack of set type rather than part of a drawing?

    Counts bands of line height whose ink is as dark as type. A column of body
    text is almost entirely such bands; a diagram has few or none.
    """
    rows = sub.sum(axis=1) >= 2
    n = len(rows)
    y = total = texty = 0
    while y < n:
        if not rows[y]:
            y += 1
            continue
        start = y
        gap = 0
        while y < n and gap < GUTTER:
            y += 1
            gap = 0 if (y < n and rows[y]) else gap + 1
        end = y - gap
        total += 1
        if 12 <= end - start <= TEXT_LINE_MAX_H and sub[start:end].mean() >= TEXT_INK_DARK:
            texty += 1
    return total >= 3 and texty >= 3 and texty / total >= 0.6


def _clip_to_column_beside_text(
    mask: np.ndarray,
    top: int,
    bottom: int,
    left: int,
    right: int,
    seed: tuple[int, int, int, int],
    col_l: int,
    col_r: int,
) -> tuple[int, int]:
    """Drop running text that flows *alongside* a narrow figure.

    A few pages set a half-width figure beside a half-width column of body text
    (p130 图 4.19, p215 图 7.22). Row profiling cannot separate them — every row
    is inked on both sides — but a tall blank vertical gutter can. Find the
    widest interior gutter and, if exactly one side of it reads as a stack of set
    type, discard that side. Requiring a clear text/graphic asymmetry keeps this
    from slicing wide plots at their internal whitespace.
    """
    if right - left < 300:
        return left, right
    sub = mask[top:bottom, left:right]
    if sub.size == 0:
        return left, right

    # a gutter may carry a little ink from the caption line, which spans the
    # whole measure, so allow a few percent rather than demanding pure white
    blank = sub.sum(axis=0) <= (bottom - top) * 0.03
    runs: list[tuple[int, int]] = []
    start = None
    for x, b in enumerate(blank):
        if b and start is None:
            start = x
        elif not b and start is not None:
            if x - start >= SIDE_GUTTER:
                runs.append((start, x))
            start = None
    # ignore gutters hugging either edge: those are just margins
    runs = [r for r in runs if r[0] > 40 and r[1] < len(blank) - 40]
    if not runs:
        return left, right

    cut = max(runs, key=lambda r: r[1] - r[0])
    # A real side-by-side layout splits the measure roughly in half. A sliver off
    # one edge is something else: the axis labels down the left of a plot, sitting
    # beyond the plot frame's own whitespace, read as a stack of set type and were
    # being discarded together with the left half of the caption below (p204
    # 图 7.9 lost its "图 7.9" and kept only the tail of the line).
    width = right - left
    if min(cut[0], width - cut[1]) < width * 0.25:
        return left, right
    left_is_text = _looks_like_text_column(sub[:, : cut[0]])
    right_is_text = _looks_like_text_column(sub[:, cut[1] :])
    if left_is_text and not right_is_text:
        return left + cut[1], right
    if right_is_text and not left_is_text:
        return left, left + cut[0]
    return left, right


def _median_line_height(bands: list[Band]) -> float:
    """Typical body-line height on this page, used as a size yardstick."""
    heights = [b.height for b in bands if 8 <= b.height <= TEXT_LINE_MAX_H]
    if not heights:
        return float(TEXT_LINE_MAX_H)
    return float(np.median(heights))


def _is_body_text(band: Band, col_w: int) -> bool:
    """A justified body-text line runs the full measure of the column."""
    return band.is_text and (band.right - band.left) / col_w >= 0.93


def snap(
    img: Image.Image,
    seed: tuple[int, int, int, int],
    caption: bool = True,
    caption_above: bool = False,
) -> Block | None:
    """Grow a rough seed rectangle out to the real figure block on the page.

    The seed only has to *touch* the intended graphic; the true extent comes
    from the pixels. Growth stops at body text, at a wide whitespace gutter
    (which separates two different figures), or at the caption line.

    `caption_above` says this asset's kind — a table or a listing — is captioned
    from above rather than below, which loosens what counts as a caption there.
    """
    bands = find_bands(img)
    if not bands:
        return None
    mask = _ink_mask(img)
    col_l, col_r = _column_extent(mask)
    # judge captions and headings against the type block, not against every
    # inked column: a figure wider than the measure would otherwise skew both
    col_l, col_r = text_measure(bands, col_l, col_r)
    col_w = max(1, col_r - col_l)
    h, w = mask.shape

    graphics = [b for b in bands if not b.is_text]
    if not graphics:
        return None

    # seed the core with the graphic band the seed overlaps most; if the seed
    # misses every graphic, take the nearest one.
    #
    # A numbered display equation classifies as a graphic but is never a figure,
    # so it must not be taken as the core either — growth already refuses to
    # cross one. The hand-typed seeds are rough enough that an equation printed
    # in the paragraph above a drawing can out-overlap the drawing itself, and
    # the crop then shows one line of mathematics: p102 图 A.8 came out as
    # "Q_e = τ_F I_C  (A.13)", p103 图 A.9 as (A.16) and p111 图 B.5 as (B.8).
    # Equations set narrow enough to miss `_is_display_equation`'s width test
    # (p103's (A.16) reaches only 0.69 of the measure) are caught by height:
    # whatever else it is, a band no taller than a line of type is not a
    # *drawing*. It can still be part of one — growth reaches it from a real
    # graphic band either side. If every graphic on the page is line-shaped,
    # keep them as candidates rather than failing outright.
    seed_mid = (seed[1] + seed[3]) / 2

    def voverlap(b: Band) -> int:
        return max(0, min(b.bottom, seed[3]) - max(b.top, seed[1]))

    line_h = _median_line_height(bands)

    def could_be_figure(b: Band) -> bool:
        """Could this graphic band be the *start* of a drawing?

        Growth reaches the rest of a figure from any one of its bands, so this
        only has to rule out bands that cannot be a figure at all. Two shapes
        cannot: a band no taller than a line of type, and a band that is line-
        shaped and spans the measure — which is a display equation, whatever its
        density. `_is_display_equation` requires sparseness because it also
        governs where growth *stops*, and there a false positive splits a real
        drawing in two; here the worst case is starting from a neighbouring band
        of the same figure.
        """
        if b.height <= line_h * 1.5:
            return False
        return not (b.height <= EQ_MAX_H
                    and (b.right - b.left) / col_w >= 0.7)

    graphics = [b for b in graphics if could_be_figure(b)] or graphics
    best = max(graphics, key=voverlap)
    if voverlap(best) == 0:
        # Nearest by the *gap* to the seed rather than by centre distance: a seed
        # that lands in the body text between two figures is a poor guide to
        # either centre (p102 图 A.8's seed sits 519 px below one drawing's centre
        # and 524 px above the right one's), but the edge it nearly touches is
        # the figure it means.
        best = min(graphics, key=lambda b: max(
            0, b.top - seed[3], seed[1] - b.bottom))
    core = [best]
    idx = bands.index(best)
    gfx = {id(b) for b in graphics}

    # grow upwards / downwards through further graphic bands
    i = idx - 1
    while i >= 0:
        b = bands[i]
        if core[0].top - b.bottom > GUTTER * 4:
            break
        if id(b) not in gfx:
            if _bridges_graphic(bands, i, -1, gfx, core, col_w):
                core.insert(0, b)
                i -= 1
                continue
            break
        if _is_display_equation(b, col_w):
            break
        core.insert(0, b)
        i -= 1
    j = idx + 1
    while j < len(bands):
        b = bands[j]
        if b.top - core[-1].bottom > GUTTER * 4:
            break
        if id(b) not in gfx:
            # lettering printed inside the drawing is not a boundary: step over it
            # and keep growing, provided more graphic follows below it.
            if _bridges_graphic(bands, j, 1, gfx, core, col_w):
                core.append(b)
                j += 1
                continue
            break
        if _is_display_equation(b, col_w):
            break
        core.append(b)
        j += 1

    group = list(core)
    if caption:
        # A figure can be trailed by panel labels — "(a) ... (b) ..." — and then
        # by its real caption. Absorb up to two such short inset lines, stopping
        # at the first full-measure body line.
        k = j
        taken = 0
        first_w = None
        core_l = min(x.left for x in core)
        core_r = max(x.right for x in core)
        # The body measure: the widest line of set type on the page. Unlike the
        # column extent this is unaffected by a figure's callout boxes, which can
        # stick out past the text margin and make every caption look narrow.
        text_widths = [x.right - x.left for x in bands if x.is_text]
        body_w = max(text_widths) if text_widths else col_w
        pitch = _line_pitch(bands)
        # Where is this figure's caption? Finding it before the loop starts lets
        # everything above it be treated as part of the drawing, instead of the
        # figure's own trailing lines — panel labels, component values, a "(注)"
        # footnote — spending the two caption slots before the caption is reached
        # (p223 图 8.5, p100 图 A.5).
        #
        # The search stops at the first line that reads as a caption by any of the
        # ordinary tests, and must not reach past it, or it would find the paragraph
        # below and swallow both: p187 图 6.22 is captioned normally, and the
        # isolated wide line two rows further down is body copy ("总之，A 点与 B 点
        # 属同电位。"). Lettering printed inside the drawing is not such a line — that
        # is exactly what this lookahead exists to step over.
        cap_idx = None
        y = group[-1].bottom
        for c in range(j, len(bands)):
            if bands[c].top - y > CAPTION_GAP_MAX:
                break
            y = bands[c].bottom
            if _is_internal_label(bands[c], col_w, core_l, core_r,
                                  margin=(core_r - core_l) // 50):
                continue
            # a caption either looks like one, or fills the measure and stands alone
            if _is_caption(bands[c], col_w, col_l, col_r) or (
                _is_body_text(bands[c], col_w)
                and _is_isolated_line(bands, c, pitch)
            ):
                cap_idx = c
                break
        # A caption normally sits within CAPTION_GAP_MAX of its figure, but the
        # leading below a tall plot's axis-label row can be a shade more: p123
        # 图 4.10's caption is 63 px under the graph. Scaling the allowance to the
        # page's own line pitch covers that without letting a figure that has no
        # caption at all reach the paragraph below, which is what the caption and
        # isolation tests further down are for. It applies only while nothing but
        # the graphic itself has been absorbed: once a trailing label has been
        # stepped over, the caption follows it at ordinary leading, and the extra
        # allowance would instead reach the next section's heading (p46 图 2.6,
        # whose "▶ 小信号电流放大倍数…" heading is 62 px below the caption).
        cap_gap = max(CAPTION_GAP_MAX, int(pitch * 1.6))
        while k < len(bands) and taken < 2:
            b = bands[k]
            limit = cap_gap if (taken == 0 and len(group) == len(core)) \
                else CAPTION_GAP_MAX
            if b.top - group[-1].bottom > limit:
                break
            # Lettering inside the drawing (an axis title, a callout) is short and
            # centred enough to pass for a caption, and counting it as the
            # caption's first line makes the width rule below reject the real
            # caption underneath. Step over it without spending a caption slot.
            # Only before the caption, though: once the caption has been read the
            # figure is finished, and a short centred line after it is the next
            # section's heading ("▶ 失真率特性" under p222 图 8.4).
            if taken == 0 and _is_internal_label(
                b, col_w, core_l, core_r, margin=(core_r - core_l) // 50
            ):
                group.append(b)
                k += 1
                continue
            # ...and anything still standing between us and a caption we can
            # already see is part of the figure too, whether or not it looks like
            # lettering: p223 图 8.5 ends with a row of component values ("220µ"
            # beside "闭环增益:20dB"), then "(b) 测试电路", then its full-measure
            # caption, and both slots were spent before the caption was reached.
            # The line must still sit inside the graphic's own span, which a caption
            # centred on the measure never does; and as with the internal-label
            # bypass, only before any caption has been read — a short line *after*
            # the caption is the next section's heading, and the wide body line that
            # set `cap_idx` is then simply the paragraph under that heading. A little
            # slack is allowed on the span, because a plot's row of axis ticks can
            # overhang the plot frame by the width of its last label (p144 图 4.34's
            # "…6M 10M" reaches 22 px past the graphic, so both caption slots went to
            # the tick row and the axis title and the caption itself was left out;
            # eleven figures were losing their captions this way). That tick row is
            # also wider than a label — 0.61 of the measure — so the width ceiling
            # here is generous, which the `k < cap_idx` gate makes safe: we only ever
            # step over lines standing between the figure and a caption already found.
            if taken == 0 and cap_idx is not None and k < cap_idx \
                    and b.is_text \
                    and b.height <= TEXT_LINE_MAX_H \
                    and (b.right - b.left) < col_w * 0.8 \
                    and b.left >= core_l - PAD * 2 and b.right <= core_r + PAD * 2:
                group.append(b)
                k += 1
                continue
            if not _is_caption(b, col_w, col_l, col_r):
                # A long caption can fill the whole measure, and then it looks
                # exactly like a line of body copy. What still marks it out is that
                # it stands alone: a paragraph's first line is followed by another
                # at the page's line pitch, a caption is followed by the next
                # paragraph after extra leading. Only ever the *first* line taken —
                # a caption's continuation is short and centred.
                #
                # A caption under a figure that is *wider* than the measure is
                # centred on the figure instead, so it can overhang the right margin
                # and fail `_is_caption` on that side while still falling short of a
                # full body line (p119 图 4.6 spans 255..1039 against a 157..1039
                # measure, so it was neither). Being centred within the graphic's own
                # span, clear of the left margin, and standing alone identifies it;
                # an indented paragraph opening is clear of the margin too but is
                # followed by its own next line at the page pitch.
                centred_on_figure = (
                    b.left > core_l + 8 and b.right < core_r + PAD
                    and (b.left - col_l) > col_w * 0.05
                    and abs((b.left - core_l) - (core_r - b.right))
                    <= (core_r - core_l) * 0.25
                )
                if not (
                    taken == 0
                    and _is_isolated_line(bands, k, pitch)
                    and (_is_body_text(b, col_w) or centred_on_figure)
                ):
                    break
            # A paragraph's first line is indented, so it too can look centred.
            # What separates it from a real caption is that the body resumes at
            # nearly the full measure, while a caption — even when it is wider
            # than the panel label above it ("(b) 对应于…" then "图 5.22 …") —
            # stays well short of it. The measure is taken from the page's own
            # widest line of type rather than from the column extent, which a
            # figure's callout box can inflate well past the text margin.
            if first_w is not None and (b.right - b.left) > first_w + 8 \
                    and (b.right - b.left) >= body_w * 0.9:
                break
            # A caption's continuation follows at the caption's own leading. The
            # next *paragraph* is set off by more, so measuring the gap separates
            # them even when the width rule above is inconclusive: p120 图 4.7's
            # caption is followed 80 px later by "从第 3 章附录 B 的式(B.2)可得…",
            # which is indented, ends short of the margin before a display formula,
            # and so passes for a centred second line — and misses the width test by
            # a single pixel. Only a near-full-measure line is judged this way: when
            # the line already taken was a panel label rather than the caption, the
            # caption below it legitimately sits a little further off (p138 图 4.27,
            # p139 图 4.29), and it is always well short of the measure.
            if first_w is not None \
                    and (b.right - b.left) >= body_w * 0.8 \
                    and (b.top - group[-1].top) > pitch * 1.35:
                break
            # A caption's *continuation* is centred under the same graphic as its
            # first line, so its midpoint sits within a few percent of the
            # graphic's. A section heading below the caption can be short enough
            # and inset enough to pass every test above — p111 图 B.5's caption is
            # followed 54 px later by "B.8 被电流源驱动的基极接地电路", inset 0.12
            # of the measure on the left and 0.32 on the right, which `_is_caption`
            # accepts — but being set flush to the text margin rather than under
            # the drawing, its midpoint is 148 px off (419 against 567). Only the
            # continuation is judged this way: a first line may legitimately be
            # centred on something wider than the core when the figure has panels.
            if taken:
                mid = (b.left + b.right) / 2
                if abs(mid - (core_l + core_r) / 2) > (core_r - core_l) * 0.12:
                    break
            first_w = b.right - b.left if first_w is None else first_w
            group.append(b)
            taken += 1
            k += 1
            # A caption line that fills the whole measure has no room left to wrap,
            # so what follows is usually the next paragraph — which, sitting within
            # CAPTION_GAP_MAX, would otherwise be absorbed (p104 图 A.10 and p231
            # 图 8.16 each trailed one line of body copy). Usually, not always: a
            # long caption does wrap, and then the second line follows at the
            # caption's own leading rather than after the extra space that precedes
            # a paragraph, so the leading is what decides (p208 图 7.13's caption
            # runs onto a second line and must keep it).
            if _is_body_text(b, col_w) and _is_isolated_line(bands, k - 1, pitch):
                break
        if taken == 0:
            # Tables and listings caption above the block instead. Such a caption is
            # often set flush to the left margin rather than centred, so
            # `_is_caption` — which wants both margins clear — rejects it (p64 表 3.2,
            # whose header row was then cut off the top of the crop). What still marks
            # it out is the *right* margin: the body is justified to it, a caption
            # stops short. Restricted to a kind that really is captioned from above,
            # since for a figure the line above is the end of the preceding paragraph,
            # which stands alone just the same.
            heading_above = (
                caption_above
                and i >= 0 and bands[i].is_text
                and bands[i].height <= TEXT_LINE_MAX_H
                and (col_r - bands[i].right) > col_w * 0.015
                and _is_isolated_line(bands, i, pitch)
            )
            if i >= 0 and (_is_caption(bands[i], col_w, col_l, col_r)
                           or heading_above):
                if core[0].top - bands[i].bottom <= CAPTION_GAP_MAX:
                    group.insert(0, bands[i])

    top = min(b.top for b in group)
    bottom = max(b.bottom for b in group)
    left = min(b.left for b in group)
    right = max(b.right for b in group)
    left, right = _clip_to_column_beside_text(
        mask, top, bottom, left, right, seed, col_l, col_r
    )
    top, bottom = _retighten_rows(mask, top, bottom, left, right)
    if caption and right - left < (col_r - col_l) * 0.75:
        # The block turned out to occupy only part of the measure, so its caption
        # shares its rows with the text column beside it and was rejected above
        # as a full-width body line. Re-run the caption test against the narrowed
        # column, where the caption really is a short centred line.
        bottom, cap_l, cap_r = _caption_within_column(
            mask, top, bottom, left, right, col_l, col_r, _line_pitch(bands)
        )
        # the caption may overhang the graphic; keep it whole
        left, right = min(left, cap_l), max(right, cap_r)
    return Block(
        left=max(0, left - PAD),
        top=max(0, top - PAD),
        right=min(w, right + PAD),
        bottom=min(h, bottom + PAD),
    )


def find_blocks(img: Image.Image) -> list[Block]:
    """All figure blocks on a page (diagnostics / orphan hunting).

    Display equations are sparse and ragged, so band classification calls them
    graphics — but they are not figures, and offering them here lets the
    same-page ordering pass hand a figure the equation instead of its diagram.
    A real figure is always several lines deep, so height screens them out.
    """
    bands = find_bands(img)
    mask = _ink_mask(img)
    col_l, col_r = _column_extent(mask)
    col_w = max(1, col_r - col_l)
    blocks: list[Block] = []
    seen: set[tuple[int, int, int, int]] = set()
    for band in bands:
        if band.is_text or _is_display_equation(band, col_w):
            continue
        blk = snap(img, (band.left, band.top, band.right, band.bottom))
        if blk is None or blk.as_box() in seen:
            continue
        if blk.bottom - blk.top < TEXT_LINE_MAX_H * 1.8:
            continue
        seen.add(blk.as_box())
        blocks.append(blk)
    return blocks
