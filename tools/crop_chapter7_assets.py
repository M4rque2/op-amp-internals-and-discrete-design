"""Crop Chapter 7 figures and tables from rendered PDF pages (refined coordinates).

Pages 193-218 (chapter 7, original book pp. 177-204).
Each source page is rendered at 200 DPI = 1324 x 1856.

Assets (31 total):
- 7 tables: table-07-01 through table-07-07
- 25 figures: fig-07-01 through fig-07-25
"""
from pathlib import Path
from PIL import Image

SRC_PAGES_DIR = Path("D:/op-amp-internals-and-discrete-design/tmp/pdfs/chapter7/source-pages")
OUT_DIR = Path("D:/op-amp-internals-and-discrete-design/src/chapter-07/images")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# (page, left, top, right, bottom) — refined crops to exclude adjacent text/equations
CROPS = {
    # 7.1 VFB section figures & tables
    "table-07-01": (194, 666, 360, 1300, 880),   # Table 7.1
    "table-07-02": (194, 666, 970, 1300, 1810),  # Table 7.2 part 1
    "table-07-03": (195, 90, 200, 660, 430),     # Table 7.2 part 2
    "fig-07-01":   (195, 80, 1020, 1280, 1620),  # Fig 7.1 LM6361 circuit (excludes eq 7.1)
    "fig-07-02":   (198, 250, 830, 1100, 1300),  # Fig 7.2 CB Process cross-section
    "fig-07-03":   (199, 90, 250, 1280, 830),    # Fig 7.3 AD847 circuit
    "fig-07-04":   (199, 240, 890, 1100, 1490),  # Fig 7.4 AD848 distortion (chart only)
    "fig-07-05":   (200, 230, 640, 1180, 1380),  # Fig 7.5 OPA655 circuit

    # 7.2 CFA section figures & tables
    "fig-07-06":   (201, 220, 640, 1100, 1330),  # Fig 7.6 GB=10MHz VFB response
    "table-07-04": (202, 90, 410, 1240, 1060),   # Table 7.3 CFA specs
    "fig-07-07":   (203, 90, 220, 1280, 830),    # Fig 7.7 AD844 circuit
    "fig-07-08":   (203, 220, 950, 1090, 1450),  # Fig 7.8 AD844 non-inv amp
    "fig-07-09":   (204, 230, 530, 1080, 1180),  # Fig 7.9 CFA freq response
    "fig-07-10":   (205, 230, 380, 1100, 850),   # Fig 7.10 CFA equivalent circuit (full + caption)
    "fig-07-11":   (205, 90, 1200, 1280, 1500), # Fig 7.11 Non-inv equivalent circuit (after 式中 text)
    "fig-07-12":   (207, 90, 1230, 1280, 1810),  # Fig 7.12 Inverting CFA amp
    "table-07-05": (207, 380, 230, 1180, 1050),  # Table 7.4 AD844 closed-loop
    "fig-07-13":   (208, 90, 720, 1280, 1330),   # Fig 7.13 EL2880C equivalent
    "fig-07-14":   (209, 90, 830, 1280, 1450),   # Fig 7.14 AD811 AC-DC
    "fig-07-15":   (210, 240, 660, 1100, 1280),  # Fig 7.15 AC-DC freq response
    "fig-07-16":   (211, 230, 240, 1080, 940),   # Fig 7.16 AC-DC input/output

    # 7.3 JFET section figures & tables
    "table-07-06": (211, 230, 1050, 1280, 1810), # Table 7.5 JFET op-amp specs
    "fig-07-17":   (212, 230, 340, 1140, 870),   # Fig 7.17 AD845 circuit
    "table-07-07": (212, 230, 1080, 1140, 1810), # Table 7.6 THD measurements
    "fig-07-18":   (213, 90, 230, 1280, 580),    # Fig 7.18 THD+N test (excl 7.3.2 below)
    "fig-07-19":   (213, 90, 1030, 1280, 1700),  # Fig 7.19 OPA627/637 circuit (excludes eq 7.24)
    "fig-07-20":   (214, 240, 970, 1100, 1490),  # Fig 7.20 Settling time (skip heading)
    "fig-07-21":   (215, 90, 600, 1280, 1430),   # Fig 7.21 CS5396 balanced amp
    "fig-07-22":   (215, 620, 1300, 1010, 1640),  # Fig 7.22 Balanced amp gain
    "fig-07-23":   (216, 90, 870, 1280, 1340),   # Fig 7.23 Diff/CM gain concepts (skip eq 7.27 above)
    "fig-07-24":   (217, 90, 230, 1280, 700),    # Fig 7.24 Op-amp diff/CM
    "fig-07-25":   (217, 90, 830, 1280, 1370),   # Fig 7.25 Common-mode feedback equiv
}


def main():
    failed = []
    for name, (page, left, top, right, bottom) in CROPS.items():
        src = SRC_PAGES_DIR / f"pdf-page-{page}.png"
        out = OUT_DIR / f"{name}.png"
        try:
            img = Image.open(src)
            w, h = img.size
            left = max(0, min(left, w))
            right = max(0, min(right, w))
            top = max(0, min(top, h))
            bottom = max(0, min(bottom, h))
            crop = img.crop((left, top, right, bottom))
            crop.save(out, "PNG")
            print(f"  {name}: page {page} ({left},{top})-({right},{bottom}) -> {crop.size}")
        except Exception as e:
            failed.append((name, str(e)))
            print(f"  {name}: FAILED {e}")
    print(f"\n{len(CROPS) - len(failed)}/{len(CROPS)} cropped successfully")
    if failed:
        for name, err in failed:
            print(f"FAILED: {name} - {err}")


if __name__ == "__main__":
    main()