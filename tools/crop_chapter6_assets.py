"""Render and crop Chapter 6 figures, photos, tables from scanned PDF pages."""

import argparse
import subprocess
from pathlib import Path

from PIL import Image


WORKSPACE = Path(__file__).resolve().parents[1]
SOURCE = WORKSPACE / "tmp" / "pdfs" / "chapter6" / "source-pages"
DESTINATION = WORKSPACE / "src" / "chapter-06" / "images"
DEFAULT_SOURCE_PDF = (
    WORKSPACE
    / "电子元器件应用技术 基于OP放大器与晶体管的放大电路设计.pdf"
)
DEFAULT_PDFTOPPM = (
    Path.home()
    / ".cache"
    / "codex-runtimes"
    / "codex-primary-runtime"
    / "dependencies"
    / "native"
    / "poppler"
    / "Library"
    / "bin"
    / "pdftoppm.exe"
)

# filename: (PDF_page, left, top, right, bottom)
# Coordinates in 200-DPI pixel space (page size 1324 x 1856)
CROPS = {
    # === Page 171 ===
    "table-06-01.png": (171, 140, 1030, 1000, 1450),
    # === Page 172 ===
    "fig-06-01.png": (172, 140, 160, 1180, 920),
    "fig-06-02.png": (172, 250, 1210, 720, 1710),
    # === Page 173 ===
    "fig-06-03.png": (173, 360, 380, 900, 800),
    "fig-06-04.png": (173, 320, 920, 980, 1420),
    # === Page 174 ===
    "fig-06-05.png": (174, 350, 860, 700, 1280),
    # === Page 175 ===
    "fig-06-06.png": (175, 350, 120, 850, 450),
    "fig-06-07.png": (175, 280, 550, 820, 780),
    # === Page 176 ===
    "fig-06-08.png": (176, 330, 130, 950, 440),
    "fig-06-09.png": (176, 450, 820, 1100, 1240),
    # === Page 177 ===
    "fig-06-10.png": (177, 290, 180, 750, 420),
    # === Page 179 ===
    "fig-06-11.png": (179, 250, 120, 870, 400),
    "fig-06-12.png": (179, 260, 480, 820, 650),
    "fig-06-13.png": (179, 200, 890, 1020, 1280),
    # === Page 181 ===
    "fig-06-14.png": (180, 477, 1230, 1050, 1589),
    # === Page 182 ===
    "fig-06-15.png": (182, 345, 500, 905, 820),
    # === Page 183 ===
    "fig-06-16.png": (183, 430, 600, 930, 880),
    # === Page 184 ===
    "fig-06-17.png": (184, 220, 120, 980, 460),
    "fig-06-18.png": (184, 340, 720, 740, 1080),
    # === Page 185 ===
    "fig-06-19.png": (185, 315, 280, 835, 440),
    "fig-06-20.png": (185, 210, 560, 920, 820),
    "fig-06-21.png": (185, 135, 620, 855, 1040),
    # === Page 187 ===
    "table-06-02.png": (187, 165, 170, 1154, 993),
    "fig-06-22.png": (187, 179, 1047, 1000, 1571),
    # === Page 188 ===
    "fig-06-23.png": (188, 440, 860, 1020, 1331),
    # === Page 190 ===
    "fig-06-24.png": (190, 230, 120, 980, 460),
    "fig-06-25.png": (190, 270, 540, 920, 820),
    # === Page 192 ===
    "fig-06-26.png": (192, 465, 257, 1062, 930),
    "fig-06-27.png": (192, 170, 900, 1130, 1240),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_SOURCE_PDF)
    parser.add_argument("--pdftoppm", type=Path, default=DEFAULT_PDFTOPPM)
    return parser.parse_args()


def ensure_source_pages(source: Path, source_pdf: Path, pdftoppm: Path) -> None:
    expected = [source / f"pdf-page-{page:03d}.png" for page in range(171, 193)]
    if all(path.exists() for path in expected):
        return
    if not source_pdf.exists():
        raise FileNotFoundError(source_pdf)
    if not pdftoppm.exists():
        raise FileNotFoundError(pdftoppm)
    source.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            str(pdftoppm),
            "-f", "171",
            "-l", "192",
            "-r", "200",
            "-png",
            str(source_pdf),
            str(source / "pdf-page"),
        ],
        check=True,
    )


def main() -> None:
    args = parse_args()
    ensure_source_pages(args.source, args.pdf, args.pdftoppm)
    DESTINATION.mkdir(parents=True, exist_ok=True)

    for output_name, (page, left, top, right, bottom) in CROPS.items():
        source_path = args.source / f"pdf-page-{page:03d}.png"
        with Image.open(source_path) as source:
            if source.width != 1324 or source.height not in {1856, 1857, 1858}:
                raise ValueError(f"Unexpected page size for {source_path}: {source.size}")
            cropped = source.crop((left, top, right, bottom))
            cropped.save(DESTINATION / output_name, optimize=True)
        print(f"{source_path.name}[{left},{top},{right},{bottom}] -> {output_name} ({cropped.size})")


if __name__ == "__main__":
    main()
