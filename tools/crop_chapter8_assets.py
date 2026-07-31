"""Crop Chapter 8 figures/tables/photo from rendered PDF pages 219-235.
200 DPI = 1324 x 1856 per page.
Assets: 20 figs + 6 tables + 1 photo = 27.
"""
from pathlib import Path
from PIL import Image

SRC = Path("D:/op-amp-internals-and-discrete-design/tmp/pdfs/chapter8/source-pages")
OUT = Path("D:/op-amp-internals-and-discrete-design/src/chapter-08/images")
OUT.mkdir(parents=True, exist_ok=True)

CROPS = {
    # 8.1 section
    "fig-08-01":   (220, 100, 100, 1230, 560),   # R-R operation (a)+(b)
    "fig-08-02":   (221, 100, 150, 1230, 830),   # AD8532 circuit (full incl Q7/Q10 rail)
    "table-08-01": (221, 100, 820, 1230, 1080),  # AD8532 specs
    "fig-08-03":   (222, 100, 100, 1230, 460),   # Headphone amp
    "fig-08-04":   (222, 230, 750, 1100, 1080),  # OPA340/350 internal
    "table-08-02": (223, 100, 200, 1230, 460),   # OPA340/350 specs
    "fig-08-05":   (223, 230, 580, 1100, 1080),  # Distortion (a)+(b)
    "fig-08-06":   (224, 230, 380, 1100, 700),   # mid-swing (a)+(b)
    "fig-08-07":   (225, 230, 100, 1100, 460),   # OP279 circuit
    "fig-08-08":   (225, 230, 500, 1100, 800),   # Line driver
    "fig-08-09":   (226, 330, 330, 1000, 560),   # Line driver THD
    "table-08-03": (227, 100, 100, 1230, 330),   # LMV751/TLC2201 specs
    "fig-08-10":   (227, 330, 380, 1000, 700),   # noise-freq LMV751
    "fig-08-11":   (227, 230, 760, 1100, 1080),  # LMV751 test circuit
    "fig-08-12":   (228, 330, 100, 1000, 330),   # LF356 vs LMV751
    "table-08-04": (228, 100, 850, 1230, 1080),  # TLC4501 specs
    # 8.2 section
    "table-08-05": (229, 230, 100, 1100, 330),   # TLC450x Vos
    "fig-08-13":   (229, 330, 380, 1000, 640),   # TLC4502 Vos test
    "fig-08-14":   (229, 330, 680, 1000, 1010),  # TLC4502 Vos-temp
    "fig-08-15":   (230, 230, 190, 1100, 700),   # TLC4501/4502 block (full, no caption)
    "fig-08-16":   (231, 100, 250, 1230, 660),   # Precision V source
    "table-08-06": (232, 100, 250, 1230, 440),   # NJU7096 specs
    "fig-08-17":   (232, 230, 490, 1100, 1080),  # NJU7096 (a)+(b)
    "fig-08-18":   (233, 330, 170, 1000, 380),   # Zener oscillator
    "fig-08-19":   (233, 100, 500, 1230, 960),   # Comparator oscillator
    "fig-08-20":   (235, 230, 150, 1100, 530),   # Oscillator measured
    "photo-08-01": (235, 330, 560, 1000, 1000),  # Output waveform photo
}

def main():
    failed = []
    for name, (page, l, t, r, b) in CROPS.items():
        src = SRC / f"pdf-page-{page}.png"
        out = OUT / f"{name}.png"
        try:
            img = Image.open(src)
            w, h = img.size
            crop = img.crop((max(0,l), max(0,t), min(r,w), min(b,h)))
            crop.save(out, "PNG")
            print(f"  {name}: p{page} ({l},{t})-({r},{b}) -> {crop.size}")
        except Exception as e:
            failed.append(name); print(f"  {name}: FAILED {e}")
    print(f"\n{len(CROPS)-len(failed)}/{len(CROPS)} cropped")

if __name__ == "__main__":
    main()
