# SPICE examples

This folder contains the SPICE netlists used throughout Chapters 3 and 4.

The extracted circuits are:

- `CB.CIR` — Chapter 3 Appendix B, transistor DC analysis.
- `OPAMP5A.CIR` — Chapter 3, five-transistor amplifier.
- `OPAMP7A.CIR` — Chapter 3, improved amplifier.
- `OPAMP10B.CIR` — Chapter 3, further amplifier revision.
- `OPAMP22I.CIR` — Chapter 4, larger final amplifier circuit.

The book also mentions `OPAMP7B.CIR` and `OPAMP7C.CIR` in operating-point result listings, but their netlist text is not included in the source; only their result tables are reproduced, so no corresponding circuit files could be extracted.

## Micro-Cap download

The official Micro-Cap website is still visitable, but its executable is no longer downloadable. A Micro-Cap 12 archive is available here: [NeelPatra/Micro-Cap-12-Archive](https://github.com/NeelPatra/Micro-Cap-12-Archive).

## OPAMP5A.CIR

`OPAMP5A.CIR` is a plain SPICE netlist. It describes the circuit, device models, power supplies, and two analyses:

```spice
.TRAN 3.92927e-006 0.002 0 1e-005
.AC DEC 63 1 1e+008
```

The first line is the circuit title. It has no electrical effect. Lines beginning with `*` are comments in Micro-Cap/SPICE.

### Signal source

This line defines the source used as the amplifier input:

```spice
V1  2  0  AC 1V  SIN(0 1 1000)
```

It connects node 2 to ground (node 0). During transient analysis, `SIN(0 1 1000)` means:

- 0 V DC offset
- 1 V peak amplitude
- 1 kHz frequency

During AC analysis, `AC 1V` gives the source a 1 V small-signal magnitude. The `.AC` card sweeps the frequency from 1 Hz to 100 MHz at 63 points per decade.

SPICE does not have a built-in concept of “input” or “output.” It calculates all node voltages and branch currents. The author calls V1 the input because it is connected to the amplifier input node. The output is selected when a quantity such as `V(OUT)` is plotted.

`V2` and `V3` are the DC power supplies:

```spice
V2  11  0  15V
V3  0   4   15V
```

Because V3 is oriented from ground to node 4, node 4 is at -15 V relative to ground.

## Running in Micro-Cap

For interactive viewing:

1. Open `OPAMP5A.CIR` with **File → Open**. Do not open it through **Analysis → Run Script**.
2. Choose **Analysis → Transient**, then click **Run**.
3. Choose **Analysis → AC**, then click **Run**.

The transient plot can show `V(OUT)` and `V(2)`. For the open-loop AC response, the useful expression is:

```text
V(OUT) / (V(2) - V(5))
```

Its magnitude and phase give the gain and phase versus frequency.

## Batch running

`OPAMP5A.BAT` is a Micro-Cap batch script:

```text
D:\op-amp-internals-and-discrete-design\spice\OPAMP5A.CIR /T /A /S
```

- `/T` runs transient analysis.
- `/A` runs AC analysis.
- `/S` saves the waveform results for later retrieval.

Run this file from **Analysis → Run Script**. Select `OPAMP5A.BAT`, not `OPAMP5A.CIR`. Selecting the `.CIR` file as a script makes Micro-Cap interpret every netlist line as a batch-job line and produces “Did not specify what to run.”

Batch mode may flash the plots and then close them. To view saved results, open the circuit, choose the relevant analysis, set **Run Options** to **Retrieve**, and click **Run**. Without `/S`, batch results are not retained for later retrieval.

## Commented `* #` commands

These lines are retained from the original listing:

```spice
* #destroy all
* #run
* #plot tran1.v(out) tran1.v(2)
* #plot ab(ac1.v(out)/(ac1.v(2)-ac1.v(5)))
* #plot ph(ac1.v(out)/(ac1.v(2)-ac1.v(5))) * 180/pi
```

In this Micro-Cap file they are comments; Micro-Cap does not use them to configure its plots. They describe the intended post-processing:

- clear previous results;
- run the analyses;
- plot output and input during transient analysis;
- plot gain magnitude and phase during AC analysis.

The `*#` form (with no space) is recognized as an embedded control-command convention by some WinSPICE/Spice3-compatible programs. `* #` with a space is not the same thing.

## Files produced by Micro-Cap

- `OPAMP5A.TNO` — transient numeric output.
- `OPAMP5A.ANO` — AC numeric output.
- Saved waveform files may also be created when **Run Options → Save** or batch `/S` is used.
