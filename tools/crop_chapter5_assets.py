"""Render and crop Chapter 5 figures, photos, tables from scanned PDF pages."""

import argparse
import subprocess
from pathlib import Path

from PIL import Image


WORKSPACE = Path(__file__).resolve().parents[1]
SOURCE = WORKSPACE / "tmp" / "pdfs" / "chapter5" / "source-pages"
DESTINATION = WORKSPACE / "src" / "chapter-05" / "images"
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
    # === Page 151 ===
    "fig-05-01.png": (151, 136, 1063, 1070, 1675),
    # === Page 152 ===
    "table-05-01.png": (152, 131, 180, 1168, 1015),
    # === Page 153 ===
    "fig-05-02.png": (153, 100, 700, 1150, 1020),
    # === Page 154 ===
    "fig-05-03.png": (154, 140, 160, 1180, 920),
    "fig-05-04.png": (154, 340, 1100, 1100, 1450),
    # === Page 156 ===
    "fig-05-05.png": (156, 527, 399, 978, 914),
    "fig-05-06.png": (156, 411, 1010, 1083, 1431),
    # === Page 157 ===
    "fig-05-07.png": (157, 292, 336, 856, 868),
    # === Page 158 ===
    "fig-05-08.png": (158, 180, 150, 1180, 780),
    "fig-05-09.png": (158, 380, 850, 1100, 1450),
    # === Page 159 ===
    "fig-05-10.png": (159, 327, 357, 850, 680),
    "fig-05-11.png": (159, 165, 700, 1128, 1130),
    # === Page 161 ===
    "fig-05-12.png": (161, 260, 600, 1040, 1200),
    # === Page 162 ===
    "fig-05-13.png": (162, 230, 193, 1166, 902),
    "fig-05-14.png": (162, 354, 944, 1161, 1676),
    # === Page 163 ===
    "fig-05-15.png": (163, 245, 287, 900, 1720),
    # === Page 164 ===
    "fig-05-16.png": (164, 227, 750, 1156, 1424),
    # === Page 165 ===
    "fig-05-17.png": (165, 140, 250, 1160, 950),
    "fig-05-18.png": (165, 240, 1040, 930, 1320),
    # === Page 166 ===
    "fig-05-19.png": (166, 299, 193, 1152, 1086),
    "fig-05-20.png": (166, 356, 1124, 1017, 1555),
    # === Page 167 ===
    "fig-05-21.png": (167, 200, 680, 1050, 920),
    # === Page 168 ===
    "fig-05-22.png": (168, 350, 160, 960, 450),
    "fig-05-23.png": (168, 300, 520, 980, 820),
    # === Page 169 ===
    "fig-05-24.png": (169, 288, 269, 848, 713),
    "fig-05-25.png": (169, 371, 1014, 779, 1293),
    # === Page 170 ===
    "fig-05-26.png": (170, 564, 305, 1097, 722),
    "fig-05-27.png": (170, 430, 650, 1030, 970),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_SOURCE_PDF)
    parser.add_argument("--pdftoppm", type=Path, default=DEFAULT_PDFTOPPM)
    return parser.parse_args()


def ensure_source_pages(source: Path, source_pdf: Path, pdftoppm: Path) -> None:
    expected = [source / f"pdf-page-{page:03d}.png" for page in range(151, 171)]
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
            "-f", "151",
            "-l", "170",
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
