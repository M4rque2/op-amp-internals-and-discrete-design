#!/usr/bin/env python3
"""Convert the first page of each PDF in ./pdf to a matching SVG in ./svg.

PyMuPDF is preferred and trims blank page margins by default. Use --no-trim to
preserve the complete PDF page area.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


Result = tuple[bool, str]
Converter = Callable[..., Result]


def run_command(command: list[str]) -> Result:
    """Run an external converter and return its status and error message."""
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
        return True, completed.stdout.strip()
    except subprocess.CalledProcessError as exc:
        return False, (exc.stderr or exc.stdout or "").strip()
    except FileNotFoundError as exc:
        return False, str(exc)


def visible_content_bbox(
    page: "fitz.Page", render_scale: float = 2.0
) -> "fitz.Rect | None":
    """Return the bounds of pixels visibly painted inside a PDF page."""
    scale = max(1.0, render_scale)
    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=True)
    samples = memoryview(pixmap.samples)
    channels = pixmap.n
    alpha_channel = channels - 1

    left, top = pixmap.width, pixmap.height
    right = bottom = -1

    for y in range(pixmap.height):
        row_start = y * pixmap.stride
        for x in range(pixmap.width):
            if samples[row_start + x * channels + alpha_channel]:
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)

    if right < left or bottom < top:
        return None

    return fitz.Rect(
        left / scale,
        top / scale,
        (right + 1) / scale,
        (bottom + 1) / scale,
    )


def trim_page(page: "fitz.Page", margin: float) -> None:
    """Crop blank page margins while preserving all visible content."""
    content = visible_content_bbox(page)
    if content is None:
        return

    margin = max(0.0, margin)
    crop = fitz.Rect(
        content.x0 - margin,
        content.y0 - margin,
        content.x1 + margin,
        content.y1 + margin,
    )
    crop &= page.rect

    if crop.width > 0 and crop.height > 0:
        page.set_cropbox(crop)


def convert_with_pymupdf(
    source: Path,
    destination: Path,
    trim: bool = True,
    trim_margin: float = 12.0,
) -> Result:
    """Convert the first PDF page to SVG with PyMuPDF."""
    if fitz is None:
        return False, "PyMuPDF is not installed. Install it with: pip install pymupdf"

    try:
        with fitz.open(source) as document:
            if not document.page_count:
                return False, "PDF has no pages"

            page = document[0]
            if trim:
                trim_page(page, trim_margin)

            destination.write_text(page.get_svg_image(), encoding="utf-8")
        return True, ""
    except Exception as exc:
        return False, str(exc)


def convert_with_inkscape(source: Path, destination: Path) -> Result:
    return run_command(
        [
            "inkscape",
            str(source),
            "--export-type=svg",
            f"--export-filename={destination}",
        ]
    )


def convert_with_pdftocairo(source: Path, destination: Path) -> Result:
    return run_command(
        [
            "pdftocairo",
            "-svg",
            "-singlefile",
            str(source),
            str(destination.with_suffix("")),
        ]
    )


def pick_converter() -> tuple[str, Converter] | None:
    if fitz is not None:
        return "pymupdf", convert_with_pymupdf
    if shutil.which("inkscape"):
        return "inkscape", convert_with_inkscape
    if shutil.which("pdftocairo"):
        return "pdftocairo", convert_with_pdftocairo
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert the first page of each PDF to a matching SVG."
    )
    parser.add_argument(
        "--input",
        default="./pdf",
        help="Input folder containing PDFs (default: ./pdf)",
    )
    parser.add_argument(
        "--output",
        default="./svg",
        help="Output folder for SVGs (default: ./svg)",
    )
    parser.add_argument(
        "--no-trim",
        action="store_true",
        help="Preserve complete PDF page areas instead of trimming blank margins",
    )
    parser.add_argument(
        "--trim-margin",
        type=float,
        default=12.0,
        help="Margin around detected content in PDF points (default: 12.0)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()

    if not input_dir.is_dir():
        print(f"Input folder not found: {input_dir}", file=sys.stderr)
        return 1

    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in: {input_dir}")
        return 0

    converter = pick_converter()
    if converter is None:
        print(
            "No supported converter found. Install PyMuPDF, Inkscape, "
            "or pdftocairo.",
            file=sys.stderr,
        )
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)
    converter_name, convert = converter
    print(f"Using converter: {converter_name}")

    succeeded = 0
    failed = 0
    for pdf_path in pdf_files:
        svg_path = output_dir / f"{pdf_path.stem}.svg"
        if converter_name == "pymupdf":
            ok, message = convert(
                pdf_path,
                svg_path,
                not args.no_trim,
                args.trim_margin,
            )
        else:
            ok, message = convert(pdf_path, svg_path)

        if ok and svg_path.exists():
            succeeded += 1
            print(f"[OK]   {pdf_path.name} -> {svg_path.name}")
        else:
            failed += 1
            print(f"[FAIL] {pdf_path.name}", file=sys.stderr)
            if message:
                print(f"       {message}", file=sys.stderr)

    print(f"Done. Success: {succeeded}, Failed: {failed}")
    return 0 if failed == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
