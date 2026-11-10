# Phase 2 — Capacitively-coupled LNA (part 1: structure, bias, pseudo-resistors)

Goal: 40 dB gain, 0.5 Hz-ish high-pass, ~3 kHz low-pass, around 0.5 µA. Part 2 has the results.

## What's in the LNA
- **CCIA:** Cin = 20 pF, Cf = 200 fF, so gain = Cin/Cf = 100 (40 dB). Caps block the ±300 mV electrode offset.
- **OTA:** the Phase 1 folded cascode, re-biased for the LNA (`ota_fc_lna`), input pair 10 × 50u/4u. Cascode legs cut to 50 nA, so total current drops to ~550 nA.
- **Bias:** one 25 nA reference. Stacking MC on the reference diode gives VCN (1.09 V) for free.
- **Pseudo-resistors:** MOS-bipolar elements in feedback set the high-pass corner: f_HP = 1/(2π·R·Cf).

## Pseudo-resistor sizing (the interesting bit)
| try | result |
|---|---|
| 1 × (2 × 1u/1u) | f_HP ≈ 4 Hz, way too high (R ≈ 2e11 Ω) |
| 2 × (0.4u/20u) | R big enough but f_HP 0.37 Hz, not the 0.12 Hz expected |
| swap in ideal 6.84 TΩ | 0.116 Hz, so the chain isn't acting as a pure R |
| why | gate-oxide cap (~69 fF) bypasses the element above ~1 Hz, tau goes as L² |
| **6 × (2 × 0.4u/4u) per path** | f_HP 0.24 Hz at 27 °C, 0.39 Hz at 37 °C |

## Files
- `lna_design.py`, `proto.py`: LNA sizing and first prototype
- `pr_char.py`, `p2_pr_results.py`: pseudo-resistor I-V / R(V) / temperature characterisation
- `net/`: netlists (prototype, pseudo-R variants `pr_*`, `prch_*` chain sweep, ideal-R debug)
- `skill/`: SKILL code that builds the cells in Virtuoso
- `gen_skill.py`, `runsim.py`, `psf.py`: schematic generator, Spectre runner, PSF reader
- `plots/`: schematics (bias_gen, lna_cci, ota_fc_lna, pseudo_r, testbenches), pseudo-R I-V/R plot

Raw simulation data isn't tracked (too big).
