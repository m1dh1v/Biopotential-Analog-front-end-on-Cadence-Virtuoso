"""Insert the Phase-4 additions into DESIGN_JOURNAL.md (sections A, B, C, D, E)."""
import os
J = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "DESIGN_JOURNAL.md")
s = open(J, encoding="utf-8").read()
SEP = "---------------------------------------------------------------------------------------------------------\n"

A = r"""
### A20. The LNA's f_HP was a simulator-tolerance artefact for two phases (Phase 4)
- **Symptom:** in tb_chain the lna_v2 high-pass corner came out at 0.152 Hz, while tb_lna_v2 (Phase 3) and tb_lna (Phase 2) gave 0.240 Hz.
- **How it showed:** the chain AC; then the same tb_lna_v2 netlist rerun with only the options changed.

  | options | f_HP 27 °C | f_HP 37 °C |
  |---|---|---|
  | iabstol 1e-15 / reltol 1e-5 | 0.240 Hz | 0.390 Hz |
  | 1e-18 / 1e-6 | 0.152 Hz | 0.277 Hz |
  | 1e-21 / 1e-7 | 0.152 Hz | 0.276 Hz |

  The DC node voltages are identical in all three.
- **Root cause:** the pseudo-R chain runs at fA currents. With iabstol = 1e-15 A, Newton stops before its small-signal conductance is resolved, so R is underestimated by ≈ 1.6× and f_HP is overestimated.
- **Fix:** iabstol ≤ 1e-18 for anything containing pseudo-resistors (all Phase 4 runs).
- **Cost / consequences:**
  - Every f_HP in the Phase 2 and Phase 3 reports is ≈ 1.6× too high (still passes, with more margin).
  - The Phase 2 hand calculation (0.153 Hz) was right; the "−36 % hand error" and the gate-capacitance-bypass explanation (A8, C table) overstated the effect.
  - The 6-vs-10-element pseudo-R trade (B10) has its absolute numbers shifted, but its direction holds.

### A21. Plain weak-inversion pair: THD 3.9 % in the biquad (Phase 4)
- **Symptom:** a 0.5 Vpp, 30 Hz sine gave THD 3.9 % (spec 1 %).
- **How it showed:** netlist prototype, tran + FFT; DC transfer of the cell: ±22 mV (−10 % gm).
- **Root cause:** Gm1 sees the error Vin − Vout = 0.285·Vin, i.e. ±71 mV ≈ 3·(0.65·nU_T), beyond its linear range.
- **Fix:** a multi-tanh doublet (a = 4): ±54 mV, THD 0.51–0.54 %. Diode degeneration (±46 mV, 0.69 %) was rejected: more current, more noise, and one extra diode drop of headroom.
- **Cost:** noise power ×1.56 at the same gm, and 4:1 device matching now sets the linearity.

### A22. Noise 38–43 µV with 20 pF caps (Phase 4)
- **Symptom:** 0.1 Hz–450 Hz output noise was 43 µV (spec 30 µV).
- **How it showed:** the noise contributors: the NMOS mirror loads were the largest (16 % each); the doublet's tails were visible.
- **Root cause:** Gm-C noise is ξ·kT/C. At nA currents every device is in weak inversion, so the mirror and tail devices (gm/ID ≈ 23) are almost as noisy as the pair (gm/ID ≈ 30), giving ξ ≈ 7.
- **Fix:**
  - mirrors as nmos_u5 stacks and tails as pmos_t5 stacks (lower gm/ID, less flicker): 43 → 38 µV;
  - then C = 36 pF: 28.1 µV.
- **Cost:** 0.072 mm² of MIM (C > 20 pF guideline).

### A23. Bias current pumped into the PMOS diode (Phase 4)
- **Symptom:** the first biquad had vout = 1 mV and the filter was dead.
- **Root cause:** IB was an isource from vdd *into* the PMOS diode; it must pull current out to gnd.
- **Fix:** `IB (ib 0)`. A one-line testbench slip, but it cost one full run to spot.

### A24. GUI Virtuoso blocked; cell name locked (Phase 4)
- **Symptom:** while building `pmos_s5`, the GUI session stopped answering the bridge (likely a modal dialog) and kept an edit lock on that cell.
- **Fix:** built everything in a headless Virtuoso, renamed the composite `pmos_t5`, and exported PNGs with xvfb.
- **Cost:** Step 0e (running maestro from the GUI) was not possible, and a stale `pmos_s5` (schematic only, unused) remains in AFE_lib.
"""

B = r"""
### B12. Linearisation method (Phase 4)

| cell | linear range | THD 0.5 Vpp | noise (20 pF) | I (150 Hz) | headroom |
|---|---|---|---|---|---|
| plain WI pair | ±22 mV | 3.92 % | 36 µV | 3.7 nA | best |
| **doublet, a = 4** | **±54 mV** | **0.51 %** | 43 µV | 5.0 nA | same as plain |
| diode degeneration | ±46 mV | 0.69 % | 45 µV | 7.3 nA | −1 V_SG (≈ 0.2–0.3 V) at the top of the CM range |
| capacitive attenuation ×K | ±K·22 mV | (not simulated) | ×√K | ×K | best; needs pseudo-R gate biasing (TΩ nodes again) |

**Chosen: the doublet.** It is the only option that kept the CM range (≈ 0.45–1.46 V) and gm ∝ I for tuning.

### B13. C size vs noise vs area (Phase 4)

| C each | noise (0.1 Hz–3 fc) | MIM area (2 caps) | IB at 150 Hz | I_total |
|---|---|---|---|---|
| 20 pF | 38 µV (fail) | 0.040 mm² | 0.71 nA | 5.0 nA |
| 32 pF | 29.8 µV (no margin) | 0.064 mm² | 1.13 nA | 7.9 nA |
| **36 pF** | **28.1 µV** | **0.072 mm²** | **1.27 nA** | **8.9 nA** |

Noise ∝ 1/√C as expected; the current only scales the gm, i.e. it is "free" here.

### B14. IB vs fc (Phase 4)
- fc ≈ 118 Hz/nA·IB, falling to 109 Hz/nA at 9 nA (moderate inversion), with I_total = 7·IB.
- **Low limit:** 100 Hz needs 0.85 nA, getting close to where leakage and matching at sub-nA matter.
- **High limit:** 1 kHz needs 9.2 nA (64 nA total).
- **Without PTAT biasing**, fc ∝ 1/T: −15 % from 27 to 80 °C from U_T alone, −32 % measured.

### B15. Single-ended vs differential filter (Phase 4)
- **Single-ended (chosen):** half the current and area, no CMFB, and it matches the single-ended lna_v2 output (vs VREF).
- **Cost:** no rejection of supply or substrate coupling in the filter itself (the filter PSRR wasn't characterised), and the input CM equals the signal, which forces the wide-CM doublet.
"""

C = r"""
**Phase 4 (Gm-C LPF):**

| quantity | hand | simulated | error |
|---|---|---|---|
| doublet gm at I_T = IB = 1.27 nA | 4a/((1+a)²·nU_T)·I_T = 0.64·1.27 nA/(1.3·25.9 mV) = **24.1 nS** | 24.3 nS (DC transfer) | −1 % |
| fc | √2·Gm1/(2πC) = 1.414·24.3 nS/(2π·36 pF) = **151.9 Hz** | 150.1 Hz | +1.2 % |
| Q | √(Gm1C2/(Gm2C1)) = **0.707** | 0.735 (LS fit) | −4 % |
| fc/IB | √2·0.64/(nU_T·2πC) = **118.6 Hz/nA** | 118 Hz/nA (≤ 1.3 nA), 109 Hz/nA (9 nA) | +0.5 … +9 % |
| total current | 7·IB = **8.89 nA** | 8.90 nA | 0 % |
| doublet linear range | ≈ nU_T·ln a = 33.7 mV·1.386 = **±47 mV** | ±54 mV (gm −10 %) | −13 % |
| Gm1 error input at fc/5, 0.5 Vpp | 0.285·0.25 V = **±71 mV** | beyond the linear range: HD3 dominates (0.53 %) | — |
| output noise, C = 36 pF | √(ξkT/C), ξ = 2 cells·2·n/2·1.56 = 4.1 → **21.7 µV** | 28.1 µV | −23 % |
| C needed for 30 µV | ξkT/v² = **18.9 pF** | ≈ 32 pF | −41 % |
| fc(80 °C)/fc(27 °C) | T27/T80 = **0.850** | 0.676 | −20 % |
| step overshoot (Q = 0.707) | e^(−π/√(4Q²−1)) = **4.3 %** | 4.45 % | −3 % |

**Why the misses:**
- **ξ (noise):** the "n/2 per device" count ignores that the mirror and tail run at gm/ID ≈ 23 (almost as noisy as the pair). The doublet's tails don't cancel as in a symmetric pair, because the two pairs are asymmetric.
- **80 °C fc:** the extra drop beyond 1/T is not explained yet. Leakage and n(T) at sub-nA currents are suspected but not isolated.
- **Correction to the Phase 2 rows "LNA f_HP (27 °C): hand 0.153 Hz vs sim 0.240 Hz, −36 %" and "(37 °C): 0.281 vs 0.390 Hz":** with a converged simulation (iabstol 1e-18) the simulated values are 0.152 Hz and 0.277 Hz, so the errors are **+0.7 %** and **+1.4 %**. See A20.
"""

D = r"""
**Phase 4 additions:**

25. **Tolerance artefact:** two phases of f_HP numbers depended on a simulator tolerance (A20). Any TΩ/fA node needs a tolerance convergence check before a number is quoted. A reviewer would ask what else in Phases 1–3 used iabstol 1e-15 at fA nodes: the pseudo-R table, f_HP vs T, T4 recovery.
26. **Caps:** 36 pF each × 2 per channel, plus 40 pF for the LNA, is ≈ 0.11 mm² of MIM per channel; an 8-channel ECG/EEG chip pays ≈ 1 mm². A switched-capacitor filter would be smaller but needs clocks (Phase 3 lesson: careful at TΩ nodes).
27. **Sub-nA biasing:** 1.27 nA reference and 0.25–1 nA per device. Leakage, mismatch and temperature (fc −32 % at 80 °C) are serious. Monte Carlo on the 4:1 doublet ratio and the 1:2 Gm2/Gm1 ratio (which sets Q) is essential and not done.
28. **The full ±0.5 V LNA swing is not handled linearly** (3.6 % at 0.8 Vpp). Either reduce the LNA gain ahead of the filter (move gain to the PGA after it), or give the filter more linear range, which needs more C for the same noise.
29. **Stopband floor −41 dB** above 4 kHz from capacitive feedthrough. Fine for 50/60 Hz harmonics, but it limits any anti-alias role ahead of an ADC.
30. **Single-ended, with no filter PSRR measurement.** VDD noise couples through the stacked tails (gate tied to a diode referenced to VDD).
31. **Not done:** Monte Carlo, SS/FF corners, supply ±10 %, layout parasitics, a real IREF/N + PTAT bias generator, a filter-PSRR sweep, an ECG PWL run (no file), and GUI maestro runs (Step 0e).
"""

E = r"""
### E11. Phase 4 recipe
**Variables (tb_lpf / tb_chain):**
- filter: VDD 1.8, VCM 0.9, IB 1.27n (tuning 0.85n–10n), WCL 189.4u (36 pF; 20 pF = 141.22u);
- stimuli: AMP (sine amplitude, tb_lpf: 0.05/0.125/0.25/0.4), FSIG 30, VSTEP 0.1, TSTEP 0.05, VA1/F1/VA2/F2 (0.125/30/0.125/37.5; 0.1/1/0.1/40);
- tb_chain also: VREF 0.9, IREF 25n, CL 2p, LIN 4u, WCIN = LCIN1 = 141.22u, WCF 13.943u, VOS 0 (0.3), AMP 0 (1m), FSIG 10.

**Options:** reltol 1e-6, vabstol 1e-9, **iabstol 1e-18**, gmin 1e-15, temp 27 (0/37/80 by alter). All gpdk MOS: ad = as = 0.6 µm·w, pd = ps = 2w + 1.2 µm.

**`pmos_t5`** (pins D, G, S, B): M0…M4 pmos 2u/20u in series, D → n1 → n2 → n3 → n4 → S, all gates G, bulks B.

**`gm_cell`** (pins vdd, vss, inp, inn, nbt = input; out = output):

| inst | cell | W/L, m | D | G | S | B |
|---|---|---|---|---|---|---|
| MTA | pmos_t5 | 5 × 2u/20u | ta | nbt | vdd | vdd |
| MTB | pmos_t5 | 5 × 2u/20u | tb | nbt | vdd | vdd |
| M1A | pmos | 10u/10u, m = 4 | d1 | inp | ta | ta |
| M2A | pmos | 10u/10u, m = 1 | out | inn | ta | ta |
| M1B | pmos | 10u/10u, m = 1 | d1 | inp | tb | tb |
| M2B | pmos | 10u/10u, m = 4 | out | inn | tb | tb |
| MN1 | nmos_u5 | 5 × 0.4u/20u | d1 | d1 | vss | vss |
| MN2 | nmos_u5 | 5 × 0.4u/20u | out | d1 | vss | vss |

**`lpf_gmc`** (pins vdd, vss, vin, ib = input; vout = output):
- MB pmos_t5 (D ib, G ib, S vdd, B vdd);
- G1 gm_cell (inp vin, inn vout, out v1, nbt ib);
- G2<0:1> gm_cell (inp v1, inn vout, out vout, nbt ib);
- C1 mimcap w = l = WCL (v1 → vss); C2 mimcap w = l = WCL (vout → vss).

**`tb_lpf`** (one gnd; three benches, each with its own vdc VDDk = VDD and idc IBk = IB from ibk to gnd):
- X1: VIN1 vsin (vdc = vo = VCM, va = AMP, freq = FSIG, acm = 1);
- X2: VIN2 vpulse (v1 VCM, v2 VCM + VSTEP, td TSTEP, tr = tf = 10u, pw 100);
- X3: VIN3 vsin (vo VCM, va VA1, freq F1, va2 VA2, freq2 F2).

**`tb_chain`:**
- VREF vdc;
- IL lna_v2 (vinp, vinn, vref, vout → vlna, vdd → vddl, iref → irefl) with VDDL vdc, IREFL idc (vddl → irefl), CL cap (vlna);
- VIP/VIN vsin (VCM + VOS / VCM, va AMP/2, FSIG, acm 0.5 / 0.5∠180);
- XF lpf_gmc (vin vlna, vout, vdd vddf, ib ibf) with VDDF vdc and IBF idc (ibf → gnd).

**Analyses (`phase4/p4_sims.py`):**
- **main:** `op dc oppoint=rawfile`; `ac 0.1–100k dec=40`; `noise (vout1 0) 0.1–100k dec=20`; `sweep IB [0.85n 1.27n 2.5n 4.2n 6.3n 8.5n] { op; ac; noise }`; `alter temp 0/37/80 → op, ac, noise`.
- **thd:** `sweep AMP [0.05 0.125 0.25 0.4] { tran stop=0.3 maxstep=1/(30·400) conservative }`, at 27/0/37/80 °C.
- **tran:** tr1 (step bench 2 + two-tone 30/37.5 Hz, 0.45 s, maxstep 1/(37.5·400)); then alter VSTEP 0, VA1 0.1, F1 1, VA2 0.1, F2 40, tr2 3 s maxstep 50 µs.
- **chain:** `op`; `ac 0.01–100k dec=40`; `noise` at vout and vlna; alter AMP 1m, VOS 0.3 → tran 4 s maxstep 100 µs.
- **top of the tuning range:** `sweep IB [9.2n 10n] { op; ac }`.

**Extraction (`p4_results.py`):**
- fc = −3 dB crossing re the DC gain; Q and f0 = least-squares fit of a 2nd-order low-pass up to 3·fc; group delay = −dφ/dω.
- Noise = √∫|out|² over 0.1 Hz–3·fc; contributors = per-instance noise, grouped into pair, mirror, tail and bias per cell.
- THD = FFT of a uniform resample over 6 periods after 0.1 s, harmonics 2–10; IM3 = max(2f1 − f2, 2f2 − f1)/fundamental.
- Step: overshoot and 1 % settling. C_in = Im(I_VIN1)/(2πf·1 V).
- Chain: input-referred = out/|H_chain|; band = −3 dB re the peak.
- `opinfo.py` reads op.info (oppoint = rawfile) into per-device dictionaries.

**Netlists:** `~/simulation/<tb>/spectre/schematic/netlist/netlist` copied to `sim/afe/<tb>_sch.scs`. Check: `mag` only on VIN1, VIP and VIN.

**PNG export:** `sim/afe/xexport.sh sim/afe/p4_export_replay.il` (Virtuoso under xvfb, `P4_expTiles`: zoomed tiles, hiExportImage 'visibleArea).
"""

i = s.index(SEP + "## B. Trade-offs"); s = s[:i] + A.lstrip("\n") + "\n" + s[i:]
i = s.index(SEP + "## C. Hand calculation"); s = s[:i] + B.lstrip("\n") + "\n" + s[i:]
i = s.index(SEP + "## D. Critic"); s = s[:i] + C.lstrip("\n") + "\n" + s[i:]
i = s.index(SEP + "## E. Rebuild recipe"); s = s[:i] + D.lstrip("\n") + "\n" + s[i:]
s = s.rstrip("\n") + "\n\n" + E.lstrip("\n")
s = s.replace("Status: **Phases 1, 2 and 3 complete (2026-11-10).**", "Status: **Phases 1–4 complete (Phase 4: 2026-11-11).**")
s = s.replace("`phase3/` (schematic netlists of `AFE_lib/tb_lna_v2`, `tb_lna_chop`), NN, 27 °C unless noted.",
              "`phase3/` (schematic netlists of `AFE_lib/tb_lna_v2`, `tb_lna_chop`); Phase-4 numbers from `phase4/` (`AFE_lib/tb_lpf`,\n"
              "`tb_chain`), NN, 27 °C unless noted. **Note (Phase 4, A20):** f_HP values from Phases 2–3 used iabstol 1e-15 and are ≈ 1.6× too high.")
open(J, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
