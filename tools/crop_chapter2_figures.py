"""Crop the 21 numbered Chapter 2 figures from the Chinese scan."""

import argparse
import subprocess
from pathlib import Path

from PIL import Image


WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = WORKSPACE / "tmp" / "pdfs" / "chapter2" / "source-pages"
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
DESTINATION = WORKSPACE / "src" / "chapter-02" / "images"

# filename: (PDF page, left, top, right, bottom)
CROPS = {
    "fig-02-01.png": (39, 270, 1310, 835, 1695),
    "fig-02-02.png": (40, 400, 160, 1120, 820),
    "fig-02-03.png": (41, 245, 215, 900, 565),
    "fig-02-04.png": (43, 230, 480, 930, 950),
    "fig-02-05.png": (44, 406, 255, 1089, 635),
    "fig-02-06.png": (46, 185, 710, 1190, 1135),
    "fig-02-07.png": (47, 130, 720, 1190, 1740),
    "fig-02-08.png": (50, 200, 390, 1190, 880),
    "fig-02-09.png": (51, 300, 195, 910, 610),
    "fig-02-10.png": (52, 475, 185, 1135, 595),
    "fig-02-11.png": (53, 240, 520, 1060, 875),
    "fig-02-12.png": (53, 335, 1125, 850, 1470),
    "fig-02-13.png": (54, 175, 185, 1130, 600),
    "fig-02-14.png": (55, 265, 315, 960, 625),
    "fig-02-15.png": (55, 275, 825, 1165, 1385),
    "fig-02-16.png": (56, 465, 785, 1060, 1285),
    "fig-02-17.png": (57, 180, 180, 1051, 1190),
    "fig-02-18.png": (59, 220, 280, 920, 980),
    "fig-02-19.png": (60, 475, 355, 1050, 800),
    "fig-02-20.png": (60, 445, 1025, 1180, 1540),
    "fig-02-21.png": (61, 145, 195, 895, 690),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_SOURCE_PDF)
    parser.add_argument("--pdftoppm", type=Path, default=DEFAULT_PDFTOPPM)
    return parser.parse_args()


def ensure_source_pages(source: Path, source_pdf: Path, pdftoppm: Path) -> None:
    expected = [source / f"pdf-page-{page:03d}.png" for page in range(39, 62)]
    if all(path.exists() for path in expected):
        return

    if not source_pdf.exists():
        raise FileNotFoundError(f"Source PDF not found: {source_pdf}")
    if not pdftoppm.exists():
        raise FileNotFoundError(f"pdftoppm not found: {pdftoppm}")

    source.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            str(pdftoppm),
            "-f",
            "39",
            "-l",
            "61",
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
        if not source_path.exists():
            raise FileNotFoundError(source_path)

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
