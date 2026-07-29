"""Crop Chapter 1 figures from the rendered Chinese scan.

The source pages are rendered at 200 dpi and measure 1324 x 1856-1858 pixels.
Coordinates include the printed figure caption so each crop remains identifiable
when viewed outside the Markdown chapter.
"""

import argparse
import subprocess
from pathlib import Path

from PIL import Image


WORKSPACE = Path(__file__).resolve().parents[1]
SOURCE = WORKSPACE / "tmp" / "pdfs" / "chapter1" / "source-pages"
DEFAULT_SOURCE_PDF = (
    Path.home()
    / "Desktop"
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
DESTINATION = WORKSPACE / "src" / "chapter-01" / "images"

# filename: (PDF page, left, top, right, bottom)
CROPS = {
    "fig-01-01.png": (16, 300, 1185, 1160, 1555),
    "fig-01-02.png": (17, 195, 610, 1015, 1135),
    "fig-01-03.png": (18, 430, 450, 1080, 805),
    "fig-01-04.png": (18, 350, 1060, 1170, 1600),
    "fig-01-05.png": (19, 195, 520, 965, 1035),
    "photo-01-01.png": (19, 195, 1035, 965, 1545),
    "fig-01-06.png": (20, 165, 370, 1170, 650),
    "fig-01-07.png": (20, 180, 930, 1145, 1340),
    "fig-01-08.png": (21, 105, 1060, 1200, 1440),
    "fig-01-09.png": (22, 335, 175, 750, 525),
    "fig-01-10.png": (22, 490, 1050, 1040, 1550),
    "fig-01-11.png": (24, 155, 150, 1160, 750),
    "fig-01-12.png": (24, 120, 930, 1200, 1720),
    "fig-01-13.png": (25, 255, 435, 1065, 870),
    "fig-01-14.png": (25, 110, 1100, 1210, 1535),
    "fig-01-15.png": (26, 245, 600, 1090, 1100),
    "fig-01-16.png": (27, 105, 610, 1210, 1330),
    "fig-01-17.png": (28, 285, 245, 1040, 600),
    "fig-01-18.png": (28, 235, 1100, 1100, 1440),
    "fig-01-19.png": (30, 450, 320, 1070, 730),
    "fig-01-20.png": (30, 370, 735, 1050, 1125),
    "fig-01-21.png": (31, 120, 165, 1200, 900),
    "fig-01-22.png": (32, 145, 940, 1170, 1350),
    "fig-01-23.png": (33, 105, 960, 1180, 1460),
    "fig-01-24.png": (35, 55, 165, 1265, 900),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=DEFAULT_SOURCE_PDF)
    parser.add_argument("--pdftoppm", type=Path, default=DEFAULT_PDFTOPPM)
    return parser.parse_args()


def ensure_source_pages(source_pdf: Path, pdftoppm: Path) -> None:
    expected = [SOURCE / f"pdf-page-{page:03d}.png" for page in range(15, 39)]
    if all(path.exists() for path in expected):
        return

    if not source_pdf.exists():
        raise FileNotFoundError(f"Source PDF not found: {source_pdf}")
    if not pdftoppm.exists():
        raise FileNotFoundError(f"pdftoppm not found: {pdftoppm}")

    SOURCE.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            str(pdftoppm),
            "-f",
            "15",
            "-l",
            "38",
            "-r",
            "200",
            "-png",
            str(source_pdf),
            str(SOURCE / "pdf-page"),
        ],
        check=True,
    )


def main() -> None:
    args = parse_args()
    ensure_source_pages(args.pdf, args.pdftoppm)
    DESTINATION.mkdir(parents=True, exist_ok=True)

    for output_name, (page, left, top, right, bottom) in CROPS.items():
        source_path = SOURCE / f"pdf-page-{page:03d}.png"
        with Image.open(source_path) as source:
            if source.width != 1324 or source.height not in {1856, 1857, 1858}:
                raise ValueError(
                    f"{source_path.name} is {source.size}; expected 1324 x 1856-1858."
                )
            source.crop((left, top, right, bottom)).save(
                DESTINATION / output_name,
                optimize=True,
            )

        print(f"{source_path.name} -> {output_name}")


if __name__ == "__main__":
    main()
