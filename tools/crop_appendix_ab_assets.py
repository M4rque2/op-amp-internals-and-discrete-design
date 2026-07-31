"""Crop Appendix A/B figures from rendered PDF pages 95-112 into chapter-03/images/.
Appendix A: PDF 95-107 (orig 81-93), 14 figs + 1 table.
Appendix B: PDF 107-112 (orig 93-98), 6 figs + 1 netlist.
Naming: fig-a-XX, table-a-01, fig-b-XX, list-b-01.
"""
from pathlib import Path
from PIL import Image

SRC = Path("D:/op-amp-internals-and-discrete-design/tmp/pdfs/appendix-ab/source-pages")
OUT = Path("D:/op-amp-internals-and-discrete-design/src/chapter-03/images")
OUT.mkdir(parents=True, exist_ok=True)

CROPS = {
    # Appendix A
    "fig-a-01":   (95, 230, 1150, 1100, 1700), # 图 A.1 Ebers-Moll (bottom third)
    "table-a-01": (96, 230, 590, 1100, 1070),  # 表 A.1 工作领域 (5 rows)
    "fig-a-02":   (97, 130, 200, 1200, 850),   # 图 A.2 活性领域 (a)(b)
    "fig-a-03":   (98, 130, 430, 1200, 1050),  # 图 A.3 反接领域 (a)(b)
    "fig-a-04":   (99, 230, 170, 1100, 620),   # 图 A.4 Hybrid pi + caption
    "fig-a-05":   (100, 230, 280, 1100, 640),  # 图 A.5 基极宽
    "fig-a-06":   (100, 130, 700, 1200, 1060), # 图 A.6 Ic-Vce Early (a)(b)
    "fig-a-07":   (102, 330, 130, 1000, 420),  # 图 A.7 PN 结电容
    "fig-a-08":   (102, 130, 660, 1200, 1060), # 图 A.8 Vbe 变化载波
    "fig-a-09":   (103, 330, 480, 1000, 800),  # 图 A.9 beta-f
    "fig-a-10":   (104, 130, 100, 1200, 330),  # 图 A.10 Hybrid pi 计算
    "fig-a-11":   (105, 230, 130, 1100, 460),  # 图 A.11 Cb/Cjc/Cje-Ic
    "fig-a-12":   (106, 230, 240, 1100, 560),  # 图 A.12 fT-Ic 倾向
    "fig-a-13":   (106, 330, 600, 1000, 900),  # 图 A.13 2SC1815 fT-Ic
    "fig-a-14":   (107, 130, 480, 1200, 850),  # 图 A 专栏 tauF 测试电路
    # Appendix B
    "fig-b-01":   (108, 130, 230, 1200, 600),  # 图 B.1 基极接地静特性
    "list-b-01":  (108, 230, 640, 1100, 960),  # List B.1 网表
    "fig-b-02":   (109, 130, 130, 1200, 460),  # 图 B.2 射极接地静特性
    "fig-b-03":   (109, 130, 600, 1200, 880),  # 图 B.3 基极接地小信号
    "fig-b-04":   (110, 130, 100, 1200, 330),  # 图 B.4 变形等效
    "fig-b-05":   (111, 230, 480, 1100, 760),  # 图 B.5 频率特性
    "fig-b-06":   (112, 130, 130, 1200, 400),  # 图 B.6 电流源驱动
}

def main():
    failed = []
    for name, (page, l, t, r, b) in CROPS.items():
        src = SRC / f"pdf-page-{page:03d}.png"
        out = OUT / f"{name}.png"
        try:
            img = Image.open(src)
            w, h = img.size
            crop = img.crop((max(0, l), max(0, t), min(r, w), min(b, h)))
            crop.save(out, "PNG")
            print(f"  {name}: p{page} ({l},{t})-({r},{b}) -> {crop.size}")
        except Exception as e:
            failed.append(name); print(f"  {name}: FAILED {e}")
    print(f"\n{len(CROPS)-len(failed)}/{len(CROPS)} cropped")

if __name__ == "__main__":
    main()
