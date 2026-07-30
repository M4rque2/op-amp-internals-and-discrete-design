# Project Memory: op-amp-internals-and-discrete-design

## Goal
Convert scanned PDF book 《电子元器件应用技术 基于OP放大器与晶体管的放大电路设计》(黑田徹) into mdbook-compatible markdown. Chapters 1–5 done; chapters 6–8 + appendices remain.

## Format conventions (established)
- Each chapter = `src/chapter-NN/` with `chapter-NN.md` (assembled), `source-sections/*.md` (canonical source, use `../images/` links), `images/*.png`, `verification.md`.
- Figure crop script: `tools/crop_chapterN_assets.py` (pdftoppm @ cached poppler, 200 DPI → 1324×1856). Build via `tools/build_chapterN.ps1`.
- Chapter boundary mapping (PDF page : original book page):
  - Ch1: ~p14–? ; Ch2: ~p? ; Ch3: ? ; Ch4: PDF 113–150 ; Ch5: PDF 151–170 (orig 137–156) ; Ch6: PDF 171–~194 ; Ch7: ~195–220 ; Ch8: ~221–235. Full PDF = 235 pages, 8 chapters + 附录A/B/C.
- **Circuit symbols in body text MUST be written in MathJax inline math**: `\(Q_1\)`, `\(V_{CE}\)`, `\(I_{C1}\)`, `\(R_3\)` (single-char subscript no braces, multi-char subscript uses braces), `\(g_m\)`, `\(h_{FE}\)`, `\(\tau_F\)`, `\(f_T\)`. Type acronyms (FET/BJT/NPN/PNP/CMOS/BiFET/Lateral/Wilson/Widler) and units (μA, V, kΩ, pF) stay plain text. Do NOT wrap symbols inside existing `\(...\)`/`\[...\]`, HTML comments, or image alt-text.
- Source annotations: `<!-- 来源：PDF 第 X 页；原书第 Y 页 -->`.

## Environment notes
- Windows OCR (PowerShell `ocr_scanned_chinese.ps1`) fails in this env (`RecognizeAsync` throws even after Bgra8 convert). Use the Read tool to visually transcribe pages instead.
- PowerShell tool returns no stdout; write results to files and read them via Read tool.
- Reusable transform: `tmp/wrap_symbols.py` wraps inline circuit symbols in `\(...\)` (handles protected math/comments/alt-text). Reuse for chapters 6–8.
