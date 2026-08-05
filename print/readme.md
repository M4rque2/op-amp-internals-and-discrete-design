# Building the book as a print-quality PDF

This directory contains the files used by `mdbook-pandoc` to turn the mdBook
source into a typeset PDF:

- `preamble.tex` adjusts the page design, headings, tables, figures, and other
  LaTeX details.
- `heading-math.lua` protects mathematics embedded in Markdown headings while
  Pandoc converts the book.
- The `[output.pandoc]` sections in the repository's `book.toml` define the PDF
  profile, XeLaTeX engine, B5 paper size, Chinese fonts, margins, and table of
  contents.

## Requirements

Install these programs and make sure they are available on `PATH`:

1. `mdbook`
2. `mdbook-pandoc`
3. `pandoc`
4. A LaTeX distribution containing `xelatex` and the `ctex` package (MiKTeX or
   TeX Live)

The current configuration expects these Windows fonts:

- Times New Roman
- Arial
- Cascadia Mono
- SimSun
- Microsoft YaHei

If a font is unavailable, replace its name under
`[output.pandoc.profile.pdf.variables]` in `book.toml`. Source Han Serif SC and
Source Han Sans SC are good alternatives for the Chinese fonts.

After installing or updating Pandoc, restart the terminal if `pandoc` is not
found. Check the toolchain with:

```powershell
mdbook --version
pandoc --version
xelatex --version
Get-Command mdbook-pandoc
```

Do not run `mdbook-pandoc` directly as a version check: it is an mdBook renderer
and expects mdBook to send it JSON on standard input.

## Build

Run this from the repository root:

```powershell
mdbook build -d output
```

The finished file is:

```text
output/pdf/op-amp-internals.pdf
```

The normal HTML book is generated during the same build under `output/html/`.
LaTeX distributions may download missing packages during the first build, so
that run can take longer.

## Rebuilding a future release

1. Check out the desired release or commit.
2. Confirm that `book.toml` still contains the `[output.pandoc]`,
   `[output.pandoc.profile.pdf]`, and
   `[output.pandoc.profile.pdf.variables]` sections from the current version.
3. Keep `print/preamble.tex` and `print/heading-math.lua` at these paths, or
   update their paths in `book.toml`.
4. Review newly added chapters, images, tables, code blocks, and equations in
   the generated PDF.
5. Run `mdbook build -d output` again.

When carrying this setup to a release whose `book.toml` has changed, merge only
the Pandoc sections instead of replacing the whole file. This preserves any new
mdBook settings introduced by that release.

## Common problems

- **`pandoc` or `xelatex` is not recognized:** restart the terminal and add the
  installation directory to `PATH`.
- **A LaTeX package is missing:** allow MiKTeX to install missing packages, or
  install the named package with the LaTeX distribution's package manager.
- **A font cannot be found:** install it or change the corresponding font entry
  in `book.toml`.
- **A build succeeds but pagination looks wrong:** adjust `preamble.tex` or the
  B5 `geometry` values in `book.toml`, then rebuild and inspect the affected
  pages.
- **A new heading containing mathematics renders incorrectly:** check whether
  `heading-math.lua` needs to handle the new Markdown pattern.
