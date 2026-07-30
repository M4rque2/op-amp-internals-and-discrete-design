"""Render and crop Chapter 3 figures, tables, and SPICE listings."""

import argparse
import subprocess
from pathlib import Path

from PIL import Image


WORKSPACE = Path(__file__).resolve().parents[1]
SOURCE = WORKSPACE / "tmp" / "pdfs" / "chapter3" / "source-pages"
DESTINATION = WORKSPACE / "src" / "chapter-03" / "images"
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

# filename: (PDF page, left, top, right, bottom)
CROPS = {
    "fig-03-01.png": (67, 160, 850, 1160, 1650),
    "fig-03-02.png": (69, 360, 420, 980, 810),
    "fig-03-03.png": (69, 250, 830, 1080, 1660),
    "fig-03-04.png": (71, 220, 750, 1050, 1390),
    "fig-03-05.png": (74, 80, 280, 1230, 870),
    "fig-03-06.png": (74, 320, 850, 1030, 1460),
    "fig-03-07.png": (75, 260, 520, 1080, 1160),
    "fig-03-08.png": (76, 300, 950, 1080, 1510),
    "fig-03-09.png": (77, 300, 180, 1080, 790),
    "fig-03-10.png": (77, 280, 930, 1050, 1450),
    "fig-03-11.png": (81, 300, 170, 1030, 720),
    "fig-03-12.png": (82, 60, 140, 1240, 930),
    "fig-03-13.png": (82, 300, 930, 1070, 1480),
    "fig-03-14.png": (83, 160, 1030, 1160, 1460),
    "fig-03-15.png": (84, 300, 240, 980, 610),
    "fig-03-16.png": (84, 300, 750, 980, 1130),
    "fig-03-17.png": (85, 260, 140, 1080, 1380),
    "fig-03-18.png": (86, 360, 240, 950, 660),
    "fig-03-19.png": (86, 280, 620, 1080, 1510),
    "fig-03-20.png": (90, 260, 230, 1080, 970),
    "fig-03-21.png": (90, 330, 900, 1000, 1400),
    "fig-03-22.png": (91, 220, 500, 1110, 1210),
    "fig-03-23.png": (92, 250, 300, 1100, 900),
    "fig-03-24.png": (93, 70, 620, 1250, 1320),
    "fig-03-25.png": (93, 250, 1250, 1080, 1740),
    "fig-03-26.png": (94, 320, 470, 1080, 900),
    "fig-03-27.png": (94, 280, 950, 1080, 1480),
    "table-03-01.png": (64, 170, 430, 1170, 1010),
    "table-03-02.png": (64, 170, 1040, 1170, 1490),
    "table-03-03a.png": (65, 250, 560, 1120, 1760),
    "table-03-03b.png": (66, 120, 130, 1190, 1420),
    "table-03-04a.png": (70, 450, 800, 1080, 1630),
    "table-03-04b.png": (71, 140, 120, 1100, 480),
    "list-03-01a.png": (68, 190, 430, 1110, 1770),
    "list-03-01b.png": (69, 120, 120, 1130, 430),
    "list-03-02a.png": (72, 170, 940, 1160, 1780),
    "list-03-02b.png": (73, 160, 100, 1140, 1080),
    "list-03-03.png": (78, 230, 680, 1130, 1230),
    "list-03-04.png": (79, 220, 650, 1120, 1390),
    "list-03-05a.png": (79, 270, 1320, 1120, 1770),
    "list-03-05b.png": (80, 120, 110, 1130, 620),
    "list-03-06a.png": (87, 160, 260, 1160, 1770),
    "list-03-06b.png": (88, 160, 110, 1120, 900),
    "list-03-07.png": (89, 140, 250, 1160, 1260),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_SOURCE_PDF)
    parser.add_argument("--pdftoppm", type=Path, default=DEFAULT_PDFTOPPM)
    return parser.parse_args()


def ensure_source_pages(source: Path, source_pdf: Path, pdftoppm: Path) -> None:
    expected = [source / f"pdf-page-{page:03d}.png" for page in range(63, 96)]
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
            "-f",
            "63",
            "-l",
            "95",
            "-r",
            "200",
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
            source.crop((left, top, right, bottom)).save(
                DESTINATION / output_name,
                optimize=True,
            )
        print(f"{source_path.name} -> {output_name}")


if __name__ == "__main__":
    main()
