# CircuitikZ reconstruction

This folder contains the editable CircuitikZ redraw of Chapter 3, Figure 3.1, based on the `OPAMP5A.CIR` netlist and compared with the scanned book image.

Files:

- `OPAMP5A_circuitikz.tex` - editable LaTeX/CircuitikZ source.
- `OPAMP5A_circuitikz.pdf` - latest rendered schematic.
- `OPAMP5A_circuitikz_preview.png` - PNG preview used for visual checking.
- `OPAMP5A_circuitikz.log` and `.aux` - LaTeX build artifacts.

Compile from this folder with:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error OPAMP5A_circuitikz.tex
```

The redraw is an approximation: CircuitikZ symbols and typography differ from the scanned, hand-drawn original. We have tried GPT-5.6 Luna High, GPT-5.6 Terra High, and GPT-5.6 Sol High; so far, the result is barely satisfactory and remains open to further refinement.
