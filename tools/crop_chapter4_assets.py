"""Render and crop Chapter 4 figures, photos, tables, and the SPICE listing."""

import argparse
import subprocess
from pathlib import Path

from PIL import Image


WORKSPACE = Path(__file__).resolve().parents[1]
SOURCE = WORKSPACE / "tmp" / "pdfs" / "chapter4" / "source-pages"
DESTINATION = WORKSPACE / "src" / "chapter-04" / "images"
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
    "fig-04-01.png": (116, 260, 230, 1080, 760),
    "fig-04-02.png": (116, 270, 760, 1070, 1390),
    "fig-04-03.png": (117, 260, 260, 1070, 860),
    "fig-04-04.png": (118, 360, 190, 1130, 820),
    "fig-04-05.png": (119, 280, 300, 1020, 650),
    "fig-04-06.png": (119, 160, 700, 1190, 1570),
    "fig-04-07.png": (120, 420, 300, 1050, 885),
    "fig-04-08.png": (122, 400, 1270, 1100, 1660),
    "fig-04-09.png": (123, 350, 160, 1040, 870),
    "fig-04-10.png": (123, 330, 980, 1050, 1530),
    "fig-04-11.png": (124, 330, 210, 1030, 810),
    "fig-04-12.png": (124, 350, 900, 1050, 1510),
    "fig-04-13.png": (125, 300, 920, 1030, 1440),
    "fig-04-14.png": (126, 450, 235, 1050, 980),
    "fig-04-15.png": (127, 200, 180, 1160, 1190),
    "fig-04-16.png": (128, 330, 200, 1080, 790),
    "fig-04-17.png": (129, 300, 780, 1040, 1420),
    "fig-04-18.png": (130, 170, 150, 1120, 650),
    "fig-04-19.png": (130, 280, 620, 930, 1320),
    "fig-04-20.png": (131, 200, 640, 950, 1290),
    "fig-04-21.png": (132, 200, 150, 1120, 700),
    "fig-04-22.png": (133, 590, 140, 1130, 760),
    "fig-04-23.png": (133, 130, 760, 670, 1450),
    "fig-04-24.png": (134, 140, 100, 1180, 1780),
    "fig-04-25.png": (135, 130, 100, 1190, 1770),
    "fig-04-26.png": (138, 250, 150, 1080, 780),
    "fig-04-27.png": (138, 250, 780, 1080, 1450),
    "fig-04-28.png": (139, 260, 190, 1070, 760),
    "fig-04-29.png": (139, 300, 760, 1050, 1420),
    "fig-04-30.png": (140, 340, 700, 1020, 1480),
    "fig-04-31.png": (141, 240, 180, 1100, 1050),
    "fig-04-32.png": (142, 140, 650, 1180, 1580),
    "fig-04-33.png": (143, 270, 500, 1060, 1110),
    "fig-04-34.png": (144, 400, 720, 1030, 1310),
    "fig-04-35.png": (145, 240, 170, 950, 920),
    "fig-04-36.png": (146, 300, 150, 1120, 690),
    "photo-04-01.png": (142, 400, 260, 1100, 740),
    "photo-04-02.png": (144, 380, 170, 1050, 720),
    "table-04-01.png": (115, 380, 110, 1050, 650),
    "table-04-02.png": (115, 300, 790, 1080, 1450),
    "table-04-03.png": (122, 220, 120, 1130, 970),
    "list-04-01a.png": (136, 170, 150, 1150, 1780),
    "list-04-01b.png": (137, 170, 100, 1150, 1280),
    "fig-c-01.png": (147, 330, 1110, 850, 1730),
    "list-c-01a.png": (148, 280, 370, 1160, 1810),
    "list-c-01b.png": (149, 170, 180, 1160, 1810),
    "list-c-01c.png": (150, 330, 140, 1060, 1530),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_SOURCE_PDF)
    parser.add_argument("--pdftoppm", type=Path, default=DEFAULT_PDFTOPPM)
    return parser.parse_args()


def ensure_source_pages(source: Path, source_pdf: Path, pdftoppm: Path) -> None:
    expected = [source / f"pdf-page-{page:03d}.png" for page in range(113, 151)]
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
            "113",
            "-l",
            "150",
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
