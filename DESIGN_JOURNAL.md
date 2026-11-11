# Design Journal — Biopotential AFE (gpdk180)

Status: **Phase 1 and Phase 2 complete (2026-11-10).** Phase-1 numbers come from `phase1/` (schematic netlist of
`AFE_lib/tb_ota`); Phase-2 numbers from `phase2/` (schematic netlists of `AFE_lib/tb_lna`, `tb_pseudo_r`), NN, 27 °C unless noted.

---------------------------------------------------------------------------------------------------------
## A. Challenges faced

Read each one as: what we saw → which simulation showed it → how we found the root cause → the fix → what it cost.

### A1. "DC gain = 31 dB" — the L/C open-loop trick was loading the output (Phase 1)
- **Symptom:** open-loop AC gave A0 = 30.3 dB with f−3dB = 7.14 kHz. Two different sizings both gave *exactly*
  7.14 kHz — a red flag that something outside the OTA set the pole.
- **Revealed by:** open-loop AC (`it_ol`, `it2`), L = 1 GH, C = 1 GF as in the spec.
- **Diagnosis:** magnitude at 1 mHz was 34.8 with phase +90° and still *rising* to 4.2e4 at 1 Hz, i.e. a high-pass
  shape. With every device long (gm/gds 200–900), Rout is tens of GΩ. The inductor is a load jωL to an AC-ground
  (the 1 GF cap): at 1 mHz jωL = 6.3 MΩ ≪ Rout, so it shunts the output. Hand check: Rout ≈ 24 GΩ (see C1), so
  1 GH only "disappears" above f = Rout/(2πL) ≈ 4 Hz.
- **Fix:** L = C = 1e16 (jωL = 6.3e13 Ω at 1 mHz ≫ Rout). Gain became flat 103.7 dB to 1 mHz; cross-checked
  against gm1·Rout from the op point.
- **Cost:** none in the circuit; it's a testbench deviation from the spec's 1 GH and is documented. The `pz` analysis
  becomes ill-conditioned with 1e16 elements (see A5).

### A2. Gain-of-10 swing bench gave a gain of only 8.3 (Phase 1)
- **Symptom:** max |dVout/dVs| = 8.316 instead of ≈10.
- **Revealed by:** DC sweep of VS in the inverting −10 bench (R1 = 1 MΩ, R2 = 10 MΩ).
- **Diagnosis:** an OTA is a transconductor, not a low-Zout op-amp. The resistors load the output:
  A_loaded ≈ gm1·(Rout‖11 MΩ) = 5.55 µS·11 MΩ ≈ 61, loop gain ≈ 61/11 ≈ 5.5, closed loop ≈ 10·5.5/6.5 ≈ 8.5 — matches 8.3.
- **Fix:** R1 = 1 GΩ, R2 = 10 GΩ (ideal resistors) → max gain 9.997.
- **Cost:** none in silicon (test only). Lesson for Phase 2: any resistive load on this OTA (e.g. a following
  stage, a probe) collapses the gain, and the AFE feedback must be capacitive.

### A3. Shared-bias bug gave a wrong (optimistic) phase margin (Phase 1)
- **Symptom:** netlist-level stb said PM = 61.6° at 5 pF (pass), but the schematic-level stb said 59.8° (fail), with
  crossover 52 kHz vs 95 kHz.
- **Revealed by:** comparing `it_stb` (netlist) with `final` (schematic) — the schematic run was the cross-check.
- **Diagnosis:** the netlist stb file also contained a second OTA (for a pz run) wired to the *same* nbn/nbp nodes.
  The bias diodes live inside each OTA, so two OTAs on one 50 nA reference split it to 25 nA each — all currents
  halved, gm halved, crossover halved, PM looked better. A clean single-OTA netlist reproduced 59.8° exactly.
- **Fix:** every OTA instance gets its own reference sources (tb_ota benches have their own IBN/IBP/VDD).
- **Cost:** none; it cost a re-run. Lesson: with diode-referenced mirrors *inside* a cell, the bias pins are not
  "global" voltages — never tie them across instances.

### A4. Phase margin 59.8° at 5 pF (spec > 60°) (Phase 1)
- **Symptom:** PM = 49.5 / 52.7 / 59.8° at CL = 1 / 2 / 5 pF, GM 23.6 dB.
- **Revealed by:** Spectre `stb`, unity-gain buffer with iprobe.
- **Diagnosis:** injected a 1 A AC current into each internal node of the open-loop OTA and read the −3 dB corner of
  |Z| (`node_poles`): mirror node **x1 ≈ 211 kHz (0.74 pF, g ≈ 1 µS)**, fold nodes f1/f2 ≈ 1.09 MHz (0.67 pF), tail ≈ 250 kHz
  (common mode only). x1 was the closest to the ~95 kHz crossover. Its capacitance was the gate area of the
  composite PMOS mirror (2 × 2 × [1u × 40u]).
- **Fix options (simulated):**

  | option | Itot | PM 1/2/5 pF | note |
  |---|---|---|---|
  | baseline (Icasc = Itail/4, load = 2× pmos_u2) | 700 nA | 49.5 / 52.7 / 59.8° | fail |
  | Icasc = 150 nA | 799 nA | 53.3 / 56.1 / 62.4° | +100 nA |
  | Icasc = Itail/2 = 200 nA | 899 nA | 55.5 / 58.0 / 63.7° | +200 nA |
  | **load = 2× single pmos 0.5u/20u (chosen)** | **700 nA** | **54.4 / 59.7 / 69.5°** | x1 pole → 698 kHz (0.27 pF) |

  More cascode current barely moves the x1 pole (gm and C both scale with the number of unit devices); shrinking
  the mirror gate area does.
- **Cost:** load gate area 4×40 → 2×2×10 µm²; load flicker share at 1 Hz went from ~6 % to 19.8 %; Vni 1.80 → 1.88 µVrms
  (+4 %); A0 103.7 → 102.9 dB; load headroom margin 0.19 V. Zero extra power.

### A5. Spectre pz analysis returned nonsense (Phase 1)
- **Symptom:** one pole at −4.6e-23 Hz and zeros at 1e-17 Hz.
- **Diagnosis:** the 1e16 (and even 1 GH/1 GF) elements make the eigenvalue problem ill-conditioned; Spectre
  also warned about "large capacitance … may be inaccurate".
- **Fix:** used the node-impedance method (A4) instead. **Cost:** six extra short AC runs.

### A6. Tool / flow issues (Phase 1, short)
- gpdk180 schematic netlisted `w=((10u)/1)` from a string expression → Spectre error; fixed by writing numeric widths.
- BSIM3v3 has no `nf` instance parameter → parallel devices use `m`.
- Setting `acm` on one analogLib `vdc` via CDF ended up as `acm=1` on **every** vdc in tb_ota (all supplies and bias
  sources had AC magnitude) — caught by reading the netlist; fixed by deleting the prop. Always check AC sources in the netlist.
- Extension-less netlist included from a control file is parsed as SPICE → copy to `.scs` first.

### A7. f_HP = 4.24 Hz with the spec's 1u/1u pseudo-resistor (Phase 2)
- **Symptom:** first LNA prototype: gain 39.86 dB, f_LP 3.23 kHz fine, but f_HP = 4.24 Hz (spec < 0.5 Hz @37 °C).
- **Revealed by:** AC of the netlist prototype; then a `tb_pseudo_r`-style DC sweep: R(0) = 2.0e11 Ω @27 °C, 1.1e11 @37 °C.
- **Diagnosis:** f_HP = 1/(2πRCf) = 1/(2π·2e11·200f) = 4.0 Hz matches. R must exceed 1.6e12 Ω at 37 °C, about 15× more.
- **Fix:** smaller W/L and series stacking (A8). **Cost:** area (24 PMOS), slower overload recovery (A10).

### A8. Long pseudo-R devices "short themselves" with their gate capacitance (Phase 2)
- **Symptom:** 2 × (0.4u/20u) elements, R = 6.8e12 Ω → expected f_HP 0.12 Hz, simulated 0.37 Hz (27 °C), 0.58 Hz (37 °C).
- **Revealed by:** AC of the LNA; the pseudo-R DC characterization said R was big enough, so the gap had to be AC.
- **Diagnosis:** replaced the chains with an ideal 6.84 TΩ resistor → f_HP = 0.116 Hz (exact). So the element isn't a pure R at
  0.1–1 Hz. Each 0.4u/20u device has ≈ 69 fF of gate oxide between its mid node and its well (tied to a terminal). That
  capacitance bypasses half the element above f ≈ 1/(2π·1.7e12·69 fF) ≈ 1.3 Hz. Since τ ∝ (L/W)·(W·L) = L², shorter devices are much better.
- **Fix (in-situ sweep, f_HP 27/37 °C):** 2×0.4/20: 0.37/0.58; 3×0.4/10: 0.31/0.50; 4×0.4/4: 0.36/0.585; **6×0.4/4: 0.24/0.39**;
  8×0.4/2: 0.26/0.44 Hz → 6 × (2 × pmos 0.4u/4u) per path.
- **Cost:** 24 PMOS of 1.6 µm² gate each (tiny area); still 1.6× above the ideal-R f_HP; slower recovery (6.7 s);
  pseudo-R noise is 16 % of in-band power.

### A9. AC-magnitude leak again, and a stub-routing short (Phase 2)
- New `vdc` instances (VREF, VDD1/2/4, VIP3/VIN3) were netlisted with `mag=1`, which would have injected AC on the reference and
  supplies in every AC/noise run. Caught by reading the netlist; the generator now deletes `acm` on every vdc that should have none.
- The automatic stub router first chose stub directions from the symbol's bounding box (which includes label text). In
  `ota_fc_lna` that shorted nbn–nbp–vcp at the `bias_gen` instance. Schematic Check reported "Short between nbp and nbn". Fixed by
  using pin extents and fixed directions for MOS. **Cost:** none, but every schematic needs a Check before it can be trusted.

### A10. THD rises fast above 3 mV, and it is not the pseudo-R (Phase 2)
- **Symptom:** THD 0.027 / 0.85 / 6.2 / 9.6 % at 1 / 3 / 5 / 8 mV (10 Hz).
- **Revealed by:** T2 transient sweep (FFT of the last second).
- **Diagnosis:** the clipping is asymmetric (5 mV: +0.483 / −0.42 V around 0.9 V). The low limit ≈ f2 + Vdsat(M6) = 0.57 + 0.06 V ≈ 0.63 V,
  where M6 leaves saturation. The pseudo-R can't matter at 10 Hz: Z(Cf) = 80 GΩ vs ≈ 3–5 TΩ, and each element sees < 80 mV.
- **Fix (not applied, recommended):** lower VCN (wider MC: −n·Ut·ln(k), ~−50 mV per 4×; or a separate VCN branch) to bring the
  fold node down to ~0.45 V. That buys ~0.15 V of low-side swing, at the cost of sink headroom (sink stack Vdsat,eff ≈ 0.24 V).
- **Cost of not fixing:** usable input range ~3 mV (≈ 0.6 Vpp output), fine for ECG/EEG but tight with motion artefacts.

### A11. Overload recovery (Phase 2)
- A 50 mV differential step saturates the output (0.078 V). The input node is then pulled back by the pseudo-R chain, whose R is
  low at large |dV| but rises steeply as it approaches 0. Within ±10 mV after **6.70 s** (40 s tran). The 4 s run wasn't long enough
  to see this, so it was rerun at 40 s with maxstep 2 ms.

---------------------------------------------------------------------------------------------------------
## B. Trade-offs

### B1. Input-pair area: flicker noise vs gate capacitance Cp
| input pair (per device) | W·L | Vni 0.5–200 Hz | in @1 Hz | gm/ID | oxide cap W·L·Cox |
|---|---|---|---|---|---|
| 4 × 50u/4u | 800 µm² | 2.10 µVrms (iter 1, different VCP) | 730 nV/√Hz | 26.2 | 6.9 pF |
| **10 × 50u/4u (chosen)** | **2000 µm²** | **1.80 µVrms** (1.88 after A4 fix) | 583 (631) nV/√Hz | 27.8 | 17.2 pF |

(Cox ≈ ε_ox/t_ox = 3.45e-11/4e-9 ≈ 8.6 fF/µm², NMOS t_ox; PMOS assumed similar.) In weak inversion the actual Cgs is
a fraction of W·L·Cox (Cgs ≈ (n−1)/n·Cox·WL ≈ 0.2·Cox·WL plus overlap ≈ 3–4 pF); in the unity-gain buffer the
crossover dropped from 158 kHz (open loop, CL = 5 pF) to 111 kHz, implying ≈ 2.4 pF extra effective load from the
M2 gate. A 2.5× area increase bought only 14 % less noise: the thermal floor (1.22 µVrms in 199.5 Hz) does not scale
with area. **Sacrificed:** input capacitance → in a capacitively-coupled AFE the noise is multiplied by
(Cin + Cf + Cp)/Cin.

**Phase 2, in the real LNA (Cin = 20 pF, Cf = 200 fF, W = 500 µm, 200 nA):**

| L_in | W·L | Cp = Cgg | penalty | in@1 Hz | in@1 kHz | Vni 0.5–200 Hz | f_LP (2 pF) | NEF |
|---|---|---|---|---|---|---|---|---|
| 1 µm | 500 | 1.39 pF | 1.079 | 1601 nV | 93 nV | 3.65 µV | 3851 Hz | 3.65 |
| 2 µm | 1000 | 2.43 pF | 1.132 | 1230 nV | 97 nV | 2.84 µV | 3603 Hz | 3.65 |
| **4 µm** | **2000** | **4.51 pF** | **1.235** | 1018 nV | 107 nV | **2.47 µV** | 3201 Hz | 3.97 |
| 8 µm | 4000 | 8.68 pF | 1.444 | — | — | 2.49 µV | 2630 Hz | 4.74 |

The flicker reduction (∝ 1/WL) is cancelled by the penalty² ∝ (1 + Cp/Cin)² beyond ~2000 µm². Bigger Cp also lowers β
and therefore f_LP. 4 µm is the in-band-noise optimum. 1–2 µm is the NEF optimum (NEF uses the whole 3.2 kHz bandwidth where the thermal
floor dominates). Choice: 4 µm (in-band noise is the clinical spec). **Sacrificed:** 0.3 NEF, 650 Hz of f_LP margin.

### B2. Cin = 10 pF vs 20 pF
MIM density 1.0 fF/µm² (+0.1 fF/µm perimeter): Cin = 20 pF ≈ 141.22 × 141.22 µm = 19 943 µm² (+ Cf 194 µm²) per input,
**≈ 40 300 µm² for the differential pair**. Cin = 10 pF ≈ 99.8 × 99.8 µm = 9 960 µm² → ≈ 20 100 µm² per channel.
|Z_in| at 50 Hz: 20 pF → 159 MΩ, 10 pF → 318 MΩ (electrode impedance mismatch × 1/Z_in sets CM-to-DM conversion, so 10 pF is better for CMRR).

| (best L each) | Vni 0.5–200 Hz | penalty | f_HP 27 °C | NEF |
|---|---|---|---|---|
| 20 pF / 200 fF, L 4 µm | **2.47 µV** | 1.235 | 0.24 Hz | 3.97 |
| 10 pF / 100 fF, L 4 µm | 3.35 µV | 1.461 | 0.48 Hz (≈0.78 Hz @37 °C, fails) | 4.80 |
| 10 pF / 100 fF, L 1 µm | 4.25 µV | 1.149 | 0.48 Hz | 3.96 |

Halving Cin raises Vni ~36 % (bigger penalty with the same Cp) and doubles f_HP (same pseudo-R, half Cf). **Choice: 20 pF.**
**Sacrificed:** 20 000 µm² of MIM per channel and half the input impedance.

### B3. Cascode branch current: power vs nondominant pole / PM vs folding-device noise
| Icasc | Itot | PM @5 pF | fold-node pole | notes |
|---|---|---|---|---|
| **100 nA (Itail/4)** | 700 nA | 59.8° (69.5° after load fix) | ≈1.04–1.09 MHz | chosen |
| 150 nA | 799 nA | 62.4° | ↑ (gm5 ×1.5) | |
| 200 nA (Itail/2) | 899 nA | 63.7° | ↑ (gm5 ×2) | |

Noise: the sinks carry Iin/2 + Icasc. More Icasc means more sink gm (gm3 ∝ I at fixed gm/ID), so the sink thermal
share rises (currently 2 × 10.5 % at 1 kHz with 300 nA sinks); at 200 nA Icasc the sinks carry 400 nA → about
(4/3)× their noise power. NEF ∝ √Itot: +200 nA alone is ×1.13 on NEF. **Chosen:** 100 nA plus the load-sizing fix
(A4); **sacrificed:** PM at 1 pF stays 54°.

Phase 2 went the other way: in the LNA the loop crossover is ≈ f_LP ≈ 3 kHz (β ≈ 1/124), far below the
~0.7–1 MHz non-dominant poles, so PM = 89° even at 50 nA. Icasc was cut to 50 nA (−100 nA, NEF ∝ √I helps) and the sinks
dropped to 250 nA. Sink thermal share is still 2 × 11.8 % at 1 kHz.

### B4. Pseudo-resistor sizing
| per path | R(0) 27 °C | f_HP 27 / 37 °C | R(±0.3 V) per element | T-sensitivity R(0 °C)/R(80 °C) | overload recovery |
|---|---|---|---|---|---|
| 1 × (2 × 1u/1u) | 2.0e11 | ≈4 / 7 Hz | 7.9e9 | 230× | fast (not simulated) |
| 1 × (2 × 0.4u/20u) | 3.4e12 | 0.37 / 0.58 Hz* (×2 elements) | 5.3e10 | 1570× | — |
| **6 × (2 × 0.4u/4u)** | **5.2e12** | **0.24 / 0.39 Hz** | 2.26e10 | 400× | **6.7 s** to ±10 mV |
| 8 × (2 × 0.4u/2u) | — | 0.26 / 0.44 Hz | — | — | — |

(*with gate-cap bypass, see A8.)
- **Linearity:** R falls ~38× from 0 to ±0.3 V per element; splitting the voltage over 6 elements keeps each < 80 mV even at 8 mV
  input, so pseudo-R THD is not the limiter (A10).
- **Temperature:** f_HP = 0.078 / 0.24 / 0.39 / 11 Hz at 0 / 27 / 37 / 80 °C. Unusable above ~50 °C without a tunable (biased) pseudo-R.
- **Recovery:** larger R means a lower f_HP but slower recovery (τ ≈ R·Cf ≈ 1 s near equilibrium).
- **Choice:** 6 × 0.4u/4u: smallest chain meeting f_HP@37 °C with margin. **Sacrificed:** recovery time, 1.6× above ideal-R f_HP, temperature robustness.

### B5. Bias-network overhead
Phase 1 reference = 2 × 50 nA (ideal sources) = 100 nA of 700 nA (14 %). NEF ∝ √Itot: removing it would give
NEF = 4.28·√(600/700) = 3.96. If one reference serves N channels the per-channel overhead is 100/N nA
(N = 8 → 12.5 nA, NEF penalty < 1 %). The risk is shared-bias crosstalk/noise (a common-mode coupling path between
channels) and IR drop on the long bias lines. Bias pins of `ota_fc` are diode nodes, so sharing a reference means
splitting the current (see A3).

**Phase 2 real network:** IREF 25 nA (ideal) + one 25 nA branch (MBP–MCP–MBS) = 50 nA of 549.9 nA (9 %). Stacking MC on the
reference diode generates VCN with no extra current. Noise: bias_gen devices contribute < 0.5 % of in-band noise (the nbn/nbp
nodes are filtered by ~3 pF of composite gate cap; their noise enters only through the tail/sinks as common-mode or as
sink current noise). NEF: 3.97 (incl. IREF) vs 3.88 (excl.). Sharing one IREF + bias branch across 8 channels would cut the
overhead to ~6 nA/channel, but nbn/nbp/VCN/VCP become shared nodes (crosstalk, and diode-referenced mirrors must not be
paralleled; see A3). The safest split is one reference per chip, buffered per channel.

### B6. Series-stacked composite devices (Phase 1)
- **Why:** gm/ID 6–8 at 50–300 nA needs W/L ≈ 0.004–0.03 (LUT: NMOS gm/ID 7 at 300 nA needs W = 0.51 µm *at L = 20 µm*,
  and the unit 50 nA mirror cell would need W = 0.086 µm). W ≥ 0.4 µm and L ≤ 20 µm (model bins), and exact
  mirror ratios need identical 50 nA units. A single device can't do it, so I stacked them: `nmos_u5` = 5 × 0.4u/20u
  (L_eff 100 µm, gm/ID 5.98, Vdsat,eff 0.242 V) and `pmos_u2` = 2 × 1u/20u (L_eff 40 µm, gm/ID 6.74, Vdsat,eff 0.215 V).
- **Area:** nmos_u5 40 µm² gate per unit × 13 units (M3 6 + M4 6 + MBN 1) = 520 µm²; pmos_u2 40 µm² × 9 (M0 8 + MBP 1)
  = 360 µm² → 880 µm² of gate area, plus diffusion and the inter-segment junctions. (The input pair is 4000 µm².)
- **Capacitance:** the nbn bias node sees ≈ 13 × 40 µm² × 8.6 fF × ~0.7 ≈ 3 pF; that's fine for a bias node (it even
  filters). But as a *signal* node it was the cause of A4 (the mirror version was replaced).
- **Matching:** large W·L helps (σVt ∝ 1/√(WL)); series segments with lower segments in triode behave as one long device,
  but the inner nodes add junction leakage and body effect on the upper segments. Not yet verified with Monte Carlo (gpdk `stat` section).
- **Headroom:** effective Vdsat 0.21–0.24 V is like a single device at gm/ID ≈ 6–7, so no extra cost there.

---------------------------------------------------------------------------------------------------------
## C. Hand calculation vs simulation

| quantity | hand estimate (formula → number) | simulated | error |
|---|---|---|---|
| OTA DC gain | A0 = gm1·(Rn‖Rp); gm1 = 27.8·200 nA = 5.55 µS; Rn = gm6·ro6·(ro2‖ro4) = 209·(164 MΩ‖2.19 GΩ) = 31.9 GΩ; Rp = gm10·ro10·ro8 = 253·406 MΩ = 102.7 GΩ → Rout = 24.3 GΩ → A0 = 1.35e5 = **102.6 dB** | 102.9 dB (1.40e5) | −3.5 % (linear) |
| dominant pole | f−3dB = 1/(2π·Rout·CL) = 1/(2π·24.3 GΩ·5 pF) = **1.31 Hz** | 1.26 Hz | +4 % |
| GBW (open loop, 5 pF) | gm1/(2π·CL) = 5.55 µS/(2π·5 pF) = **176.7 kHz** | 157.9 kHz | +12 % |
| loop crossover (buffer, 5 pF) | same formula = 176.7 kHz | 111.1 kHz | +59 % |
| PM (buffer, 5 pF) | 90° − atan(fu/f_x1) + atan(fu/2f_x1) − atan(fu/f_f2) = 90 − 14.2 + 7.2 − 9.7 = **73.4°** (fu 176.7 kHz, f_x1 698 kHz, f_f2 1.04 MHz) | 69.5° | +5.6 % |
| thermal floor | 2·[2q/((gm/ID)·gm1) + 4kT·⅔·gm3/gm1² + 4kT·⅔·gm7/gm1²] = 2·(2.08e-15 + 6.4e-16 + 2.4e-16) = 5.93e-15 V²/Hz → **77 nV/√Hz** | 85.3 nV/√Hz (10 kHz) | −9.7 % |
| Vni 0.5–200 Hz | thermal 77 nV·√199.5 = 1.09 µV; flicker scaled from the 20u/2u device: 2 × 2.82e-12·(40/2000) = 1.13e-13 V²/Hz @1 Hz × ln(400) = 6.8e-13 → √(1.19e-12 + 6.8e-13) = **1.37 µVrms** | 1.877 µVrms | −27 % |
| NEF | 1.37e-6 · 2.281e6 = **3.12** (thermal-only: 1.09e-6·2.281e6 = 2.48) | 4.28 | −27 % |
| **LNA** midband gain | G = (Cin/Cf)/(1 + 1/(Aβ)); β = Cf/(Cin+Cf+Cp) = 0.2/24.71 = 8.09e-3, loop gain @10 Hz = 45.3 dB (184) → 100/(1+1/184) = 99.46 = **39.95 dB** | 39.94 dB | +0.01 dB |
| LNA f_HP (27 °C) | 1/(2π·R·Cf), R = 6 × 8.67e11 = 5.2e12 Ω → **0.153 Hz** | 0.240 Hz | −36 % |
| LNA f_HP (37 °C) | R = 6 × 4.72e11 = 2.83e12 → **0.281 Hz** | 0.390 Hz | −28 % |
| LNA f_LP (2 pF) | gm1·β/(2π·(CL + Cf)) = 5.56 µS·8.09e-3/(2π·2.2 pF) = **3.25 kHz** | 3201 Hz | +1.6 % |
| LNA loop crossover / PM (2 pF) | crossover ≈ f_LP = 3.25 kHz; PM = 90° − atan(3.25k/698k) − atan(3.25k/1.04M) = **89.6°** | 3147 Hz / 89.4° | +3 % / +0.2 % |
| LNA thermal floor | penalty × OTA floor: 1.235 × √(2·[2q/(27.8·5.56 µS) + 4kT⅔·1.75 µS/gm1² + 4kT⅔·0.34 µS/gm1²]) = 1.235 × 75 nV = **92.7 nV/√Hz** | ≈104 nV/√Hz (1 kHz, minus 2.6 % flicker) | −11 % |
| LNA NEF | Vni_tot ≈ √((92.7 nV)²·(π/2)·3201 + (2.47 µV)²) = 7.03 µV → 7.03e-6 × 5.049e5 = **3.55** | 3.97 | −11 % |

**Explaining the big gaps:**
- **GBW/crossover:** the hand estimate ignores output-node parasitics (≈0.6 pF from M6/M10 drains → 5.55 µS/(2π·5.6 pF) = 158 kHz,
  exact match) and, in the buffer, the M2 gate capacitance hanging on the output (effective C = gm1/(2π·111 kHz) = 7.96 pF,
  i.e. ≈2.4 pF from the 500u/4u input device). In a buffer the tail node (≈250 kHz, ~9 pF) also enters the loop, which is why
  the simulated PM is lower than the hand estimate even though the crossover is lower.
- **Thermal floor:** the WI shot-noise formula 2qI/gm² underestimates the input pair by ~25 % (sim M1 2.60e-15 vs 2.08e-15 V²/Hz;
  BSIM3 noimod=2 channel-noise model in moderate inversion). γ = ⅔ for the composite sinks fits within 20 % (sim 7.9e-16 vs 6.4e-16).
- **Flicker (largest gap):** BSIM3 noimod=2 flicker is not a pure K/(W·L·f). It depends on bias/current density and L
  (Leff² terms in the model), so scaling a 100 nA, L = 2 µm device to 200 nA, L = 4 µm underestimates the
  input-pair 1/f by ~2.6× (sim M1+M2 at 1 Hz: 2.96e-13 vs hand 1.13e-13). The load M7/M8 flicker (19.8 %) was also
  left out of the hand estimate. → The NEF hand estimate misses mainly because of flicker modelling.
- **LNA f_HP (−28…−36 %):** the pseudo-R chain is not a pure resistor at 0.1–1 Hz; its internal gate capacitance bypasses part of it
  (A8). With an ideal resistor the formula is exact (0.116 Hz for 6.84 TΩ). Also R(0) is taken from a DC sweep with no bias across
  the element; in situ, the chain mid-nodes sit at slightly different potentials.
- **LNA thermal floor / NEF (−11 %):** the same 2qI underestimate for the subthreshold input pair as in Phase 1. The NEF estimate
  also uses a first-order (π/2) noise bandwidth, while the real roll-off has the sink/mirror poles and the 1/f² pseudo-R tail below
  1 Hz (Vni_total integrates from 10 mHz, where pseudo-R noise is large).

---------------------------------------------------------------------------------------------------------
## D. Critic's view

What a reviewer / sign-off engineer would attack:
1. **NEF 4.28 vs target 3** — fails, flicker-dominated. A chopper (or a much larger input pair, which hurts Cin
   division) is the real fix. The ~0.5 µA current target is also missed (0.70 µA).
2. **Only NN @ 27 °C, ideal biasing.** No SS/FF/SF/FS, no −20…85 °C, no supply ±10 %. Subthreshold devices (input pair,
   NMOS cascodes) move a lot with temperature; VCN/VCP are fixed ideal voltages, so a real tracking bias generator is mandatory.
3. **CMRR 139.6 dB / PSRR 107.6 dB are fiction** (perfect matching). Needs Monte Carlo (`stat` section) — expect CMRR ~60–80 dB from
   offset/mirror mismatch. Offset itself was not evaluated.
4. **Margins:** M9 VSD − Vdsat = 0.16 V, M7/M8 0.19 V; PM 54° at 1 pF and 59.7° at 2 pF. If the Phase 2 load is lighter than
   5 pF, stability must be re-checked (the open-loop "phase @UGF" at 1 pF is only 29.5° with the inverting input AC-grounded).
5. **Input pair 2 × 2000 µm²** → several pF of Cgs; the noise penalty in a capacitive-feedback AFE is not yet quantified.
6. **Composite devices:** the inner nodes add leakage and their own matching uncertainty; long-L devices are slow to settle (start-up, overload recovery).
7. **No layout parasitics, no ESD/input protection, no start-up check of the bias, no transient/large-signal (slew,
   settling, overload recovery) yet.** Slew = Itail/CL = 400 nA/5 pF = 0.08 V/ms — fine for ECG, but overload recovery from
   electrode-motion artifacts must be simulated.
8. **Testbench deviations** (L/C = 1e16, 1G/10G resistors) are justified but differ from the spec text.

With more time: chopper-stabilized input or a dedicated low-1/f input stage; trim Icasc/sizes against Monte Carlo PM;
corner + temperature sweeps; a real bias generator with start-up; layout of the input pair (common-centroid) and the long stacks.

**Phase 2 additions:**
9. **LNA Vni 2.47 µV and NEF 3.97 fail** (input-pair flicker × 1.235 penalty + pseudo-R noise). A reviewer will say: the design is
   flicker-limited, so the architecture (no chopping) is wrong for < 2 µV in 0.5–200 Hz at 0.5 µA.
10. **f_HP is not controlled:** 0.078–11 Hz over 0–80 °C, and the pseudo-R is sensitive to leakage and process (no SS/FF run). A
    tunable/biased pseudo-R or a duty-cycled resistor is needed for a product.
11. **Bias generator has no start-up circuit** and was only checked at its one DC solution. VCN = 1.09 V is high and costs output
    swing (THD 0.85 % at 3 mV, 6 % at 5 mV). No supply/temperature sweep of the bias.
12. **CMRR 92.7 dB** includes only a 0.1 % Cin mismatch; input-pair Vt mismatch, pseudo-R mismatch and electrode-impedance
    imbalance are not modelled. The T3 residual (141 µV at the output for 100 mV CM) is the nominal-only value.
13. **6.7 s overload recovery** — long for ECG after a lead-off/motion event; a fast-reset switch is customary.
14. **Huge MIM area** (≈ 40 000 µm² per channel) and no bottom-plate parasitic in the mimcap model (bottom-plate caps to substrate
    on the ninv/nnon nodes would add to Cp and to the penalty).
15. **Not verified:** maestro setups were created but not run from the GUI; no Monte Carlo, no process corners, no layout
    parasitics, no ESD on the inputs, no electrode DC offset beyond +300 mV, no large-signal startup transient.

---------------------------------------------------------------------------------------------------------
## E. Rebuild recipe (Phase 1)

### E1. Technology / globals
- Library `AFE_lib` attached to tech `gpdk180`. Models: `/cad/FOUNDRY/analog/180nm/models/spectre/gpdk.scs`, section **NN**.
- Design variables: VDD = 1.8, VCM = 0.9, VCN = 1.0, VCP = 0.75, IREF = 50n, CL = 5p (swept 1p/2p/5p), LBIG = 1e16, VS = 0.9 (swept).
- Simulator options (final runs): reltol = 1e-5, vabstol = 1e-8, iabstol = 1e-15, gmin = 1e-15, temp = tnom = 27. No maxstep (no transient).
  gm/ID sweeps: reltol 1e-5, vabstol 1e-8, iabstol 1e-16, gmin 1e-16. Flicker bench: reltol 1e-6, iabstol 1e-16, gmin 1e-16.
- Every gpdk180 MOS: fingers = 1, fw = w, ad = as = 0.6 µm·w, pd = ps = 2w + 1.2 µm.

### E2. Cell `tb_gmid` (schematic)
| inst | lib/cell | params | D | G | S | B / − |
|---|---|---|---|---|---|---|
| M0 | gpdk180/nmos | w = 10u, l = Lx, m = 1 | dn | gn | gnd | gnd |
| VGN | analogLib/vdc | vdc = VGS | + gn | | | − gnd |
| VDN | analogLib/vdc | vdc = 0.9 | + dn | | | − gnd |
| M1 | gpdk180/pmos | w = 10u, l = Lx, m = 1 | dp | gp | vdd | vdd |
| VDD | analogLib/vdc | vdc = VDD | + vdd | | | − gnd |
| VGP | analogLib/vdc | vdc = VDD − VGS | + gp | | | − gnd |
| VDP | analogLib/vdc | vdc = VDD − 0.9 | + dp | | | − gnd |

Analyses: DC sweep VGS 0 → 1.8 V, step 5 mV, inside a parametric sweep Lx ∈ {0.18u, 0.5u, 1u, 2u, 4u} (extra 8u, 12u, 20u).
Saved: M0/M1 op params ids, gm, gds, cgg, vth, vdsat, region.
Extraction: gm/ID = OP("M0" "gm")/OP("M0" "ids"); ID/W = ids/10u; gm/gds; fT = gm/(2π·cgg); n = 1/(Ut·max(gm/ID)), Ut = kT/q at 300.15 K.

Flicker bench (netlist `net/flick_*.scs`): nmos/pmos w = 20u, l = 2u, |VDS| = 0.9 V; VGS(N) = 0.27672 V, VSG(P) = 0.34482 V
(found from a DC sweep 0.2–0.6 V, step 0.25 mV, interpolating ln(ID) = ln(100 nA)). Noise 0.1 Hz–10 MHz, 20 pts/dec,
oprobe = drain vsource, iprobe = gate vsource → "in" = input-referred gate noise. Corner = f where fn/(gain²) = (id+rd+rs)/(gain²).

### E3. Cell `nmos_u5` (pins D, G, S, B)
5 × gpdk180/nmos w = 0.4u, l = 20u, m = 1, in series: M0 (D, G, n1, B), M1 (n1, G, n2, B), M2 (n2, G, n3, B), M3 (n3, G, n4, B), M4 (n4, G, S, B).
Symbol: copy of the gpdk180 nmos symbol, param labels removed, text "0.4u/(5x20u)", label [@instanceName].

### E4. Cell `pmos_u2` (pins D, G, S, B)
2 × gpdk180/pmos w = 1u, l = 20u, m = 1: M1 (D, G, n1, B), M0 (n1, G, S, B). Symbol likewise ("1u/(2x20u)").

### E5. Cell `ota_fc` (pins: vip, vin, nbp, nbn, vcp, vcn = input; vout = output; vdd, vss = inputOutput)
| inst | cell | W / L / m | D | G | S | B |
|---|---|---|---|---|---|---|
| MBP | pmos_u2 | unit ×1 | nbp | nbp | vdd | vdd |
| M0<0:7> | pmos_u2 | unit ×8 (iterated) | tail | nbp | vdd | vdd |
| M1 | gpdk180/pmos | 50u / 4u / m = 10 | f1 | vip | tail | tail |
| M2 | gpdk180/pmos | 50u / 4u / m = 10 | f2 | vin | tail | tail |
| M3<0:5> | nmos_u5 | unit ×6 | f1 | nbn | vss | vss |
| M4<0:5> | nmos_u5 | unit ×6 | f2 | nbn | vss | vss |
| MBN | nmos_u5 | unit ×1 | nbn | nbn | vss | vss |
| M5 | gpdk180/nmos | 0.4u / 1u / 1 | x1 | vcn | f1 | vss |
| M6 | gpdk180/nmos | 0.4u / 1u / 1 | vout | vcn | f2 | vss |
| M7 | gpdk180/pmos | 0.5u / 20u / m = 2 | p1 | x1 | vdd | vdd |
| M8 | gpdk180/pmos | 0.5u / 20u / m = 2 | p2 | x1 | vdd | vdd |
| M9 | gpdk180/pmos | 0.6u / 1u / 1 | x1 | vcp | p1 | vdd |
| M10 | gpdk180/pmos | 0.6u / 1u / 1 | vout | vcp | p2 | vdd |

Symbol: auto-generated (inputs left, vout right, vdd/vss top).

### E6. Cell `tb_ota` (one gnd symbol; five independent benches k = 1…5, each with its own `ota_fc` Ik)
Shared: VCN vdc = VCN (vcn–gnd), VCP vdc = VCP (vcp–gnd).
Per bench: Ik pins vip→vipk, vin→vink, vout→voutk, vdd→vddk, vss→gnd, nbn→nbnk, nbp→nbpk, vcn→vcn, vcp→vcp;
VDDk vdc = VDD (vddk–gnd; **acm = 1 only for k = 5**); IBNk idc = IREF (+ vddk, − nbnk); IBPk idc = IREF (+ nbpk, − gnd);
CLk cap c = CL (voutk–gnd).
- k = 1 open loop: VIP1 vdc = VCM, **acm = 1** (vip1–gnd); LFB1 ind l = LBIG (vout1–vin1); CFB1 cap c = LBIG (vin1–gnd).
- k = 2 buffer: VIP2 vdc = VCM (vip2–gnd); IPRB analogLib/iprobe (+ vout2, − vin2).
- k = 3 inverting −10: VIP3 vdc = VCM; VS3 vdc = VS (vs3–gnd); R1 res r = 1G (vs3–vin3); R2 res r = 10G (vin3–vout3).
- k = 4 CM: VIP4 vdc = VCM, **acm = 1**; LFB4 ind l = LBIG (vout4–vin4); CFB4 cap c = LBIG (**vin4–vip4**).
- k = 5 PSRR: VIP5 vdc = VCM (no ac); LFB5 (vout5–vin5); CFB5 (vin5–gnd); VDD5 acm = 1.
Check the netlist: only VIP1, VIP4 and VDD5 may have `mag=1`.

### E7. Analyses on tb_ota (control file `phase1/net/final.scs`)
1. `op dc` — saves I1 device op params (ids, gm, gds, vgs, vds, vth, vdsat, region, cgg) and VDDk:p.
2. `noise (vout1 0)` 0.1 Hz–100 kHz, 40 pts/dec, iprobe = VIP1.
3. Parametric CL ∈ {1p, 2p, 5p}: `ac` 1 mHz–100 MHz, 40 pts/dec; `stb` 1 mHz–100 MHz, 40 pts/dec, probe = IPRB.
4. `dc` sweep VS 0.7 → 1.1 V, step 0.5 mV.

### E8. How each number was extracted (ADE calculator equivalents)
- Itot = abs(IDC("/VDD1/PLUS")) at op.
- DC gain = value(dB20(VF("/vout1")) 0.001); f−3dB = bandwidth(VF("/vout1") 3 "low");
  GBW = cross(dB20(VF("/vout1")) 0 1 "falling"); phase@UGF = value(phaseDeg(VF("/vout1")) GBW).
- PM, GM, crossover: Spectre stb margin outputs (phaseMargin, gainMargin, phaseMarginFreq, gainMarginFreq)
  = ADE `phaseMargin(getData("loopGain" ?result "stb"))` etc.
- Input-referred noise: getData("in" ?result "noise"); Vni(f1–f2) = sqrt(integ(in**2 f1 f2)) (log-spaced trapezoid,
  4000 pts) → ADE `rmsNoise(f1 f2)` on input-referred noise. 1/f corner = f where Σ flicker = Σ thermal (rd + rs + id)
  input-referred contributions. Top contributors = per-instance noise summary at 1 Hz / 1 kHz, composite segments summed.
- NEF = Vni·sqrt(2·Itot/(π·Ut·4kT·BW)), Ut = 25.9 mV, T = 300 K, BW = 199.5 Hz.
- CMRR(10 Hz) = dB20(VF("/vout1")/VF("/vout4")) at 10 Hz; PSRR = dB20(VF("/vout1")/VF("/vout5")) at 10 Hz.
- Swing: g = deriv(VS("/vout3")) vs VS; range of vout3 where |g| ≥ max|g|/√2 (and ≥ 0.99·max).
- Node poles: 1 A AC isource into each node of the open-loop OTA; pole = f where |Z| = |Z(DC)|/√2; C = 1/(2π·f·|Z|) at 10× the corner.

### E9. Phase 2 recipe
Variables: VDD 1.8, VCM 0.9, VREF 0.9, IREF 25n, CL 2p (also 5p), LIN 4u (also 1u, 2u, 8u), WCIN 141.22u, LCIN1 141.22u
(mismatch: WCIN·1.001), WCF 13.943u (10 pF option: WCIN = LCIN1 = 99.80u, WCF = 9.802u), VOS 0 (0.3 for T1/T2), AMP 1m
(T2: 1m/3m/5m/8m), FSIG 10, VCMA 0.1, VDA 100u, VSTEP 50m, DV 0.
Options: reltol 1e-5, vabstol 1e-8, iabstol 1e-15, gmin 1e-15, temp 27 (0/37/80 by alter). Pseudo-R bench: reltol 1e-6,
vabstol 1e-9, iabstol 1e-20, gmin 1e-20. All gpdk MOS: fingers 1, ad = as = 0.6 µm·w, pd = ps = 2w + 1.2 µm.

**`pseudo_r`** (pins a, b): MPA pmos 0.4u/4u (D mid, G mid, S a, B a); MPB pmos 0.4u/4u (D mid, G mid, S b, B b).

**`bias_gen`** (pins vdd, vss, iref, nbn, nbp, vcp):

| inst | cell | size | D | G | S | B |
|---|---|---|---|---|---|---|
| MC | gpdk nmos | 4u/1u | iref | iref | nbn | vss |
| MBN | nmos_u5 | unit | nbn | nbn | vss | vss |
| MBS | nmos_u5 | unit | vcp | nbn | vss | vss |
| MCP | gpdk pmos | 20u/1u | vcp | vcp | nbp | vdd |
| MBP | pmos_u2 | unit | nbp | nbp | vdd | vdd |
(VCN of the OTA = node iref.)

**`ota_fc_lna`** (pins vip, vin, iref = input; vout = output; vdd, vss):

| inst | cell | W / L / m | D | G | S | B |
|---|---|---|---|---|---|---|
| M0<0:15> | pmos_u2 | unit × 16 | tail | nbp | vdd | vdd |
| M1 | pmos | 50u / LIN / 10 | f1 | vip | tail | tail |
| M2 | pmos | 50u / LIN / 10 | f2 | vin | tail | tail |
| M3<0:9> | nmos_u5 | unit × 10 | f1 | nbn | vss | vss |
| M4<0:9> | nmos_u5 | unit × 10 | f2 | nbn | vss | vss |
| M5 | nmos | 0.4u / 1u / 1 | x1 | iref | f1 | vss |
| M6 | nmos | 0.4u / 1u / 1 | vout | iref | f2 | vss |
| M7 | pmos | 0.5u / 20u / 1 | p1 | x1 | vdd | vdd |
| M8 | pmos | 0.5u / 20u / 1 | p2 | x1 | vdd | vdd |
| M9 | pmos | 0.6u / 1u / 1 | x1 | vcp | p1 | vdd |
| M10 | pmos | 0.6u / 1u / 1 | vout | vcp | p2 | vdd |
| XB | bias_gen | — | vdd→vdd, vss→vss, iref→iref, nbn→nbn, nbp→nbp, vcp→vcp | | | |

**`lna_cci`** (pins vinp, vinn, vref, iref = input; vout = output; vdd, vss):
CIN1 mimcap w = WCIN, l = LCIN1 (vinp → ninv); CIN2 mimcap w = l = WCIN (vinn → nnon); CF1 mimcap w = l = WCF (vfb → ninv);
CF2 mimcap w = l = WCF (nnon → vref); IPRB analogLib iprobe (+ vout, − vfb); PR1_0…PR1_5 pseudo_r in series vfb → pr1_m1 → … →
pr1_m5 → ninv; PR2_0…PR2_5 in series nnon → pr2_m1 → … → pr2_m5 → vref; I0 ota_fc_lna (vip nnon, vin ninv, vout vout, vdd, vss, iref).

**`tb_pseudo_r`**: X0 pseudo_r (a, b); VA vdc 0.9+DV (a–gnd); VB vdc 0.9 (b–gnd); one gnd.

**`tb_lna`** (one gnd, VREF vdc = VREF on net vref shared); for each bench k: Ik lna_cci (vinp k, vinn k, vref, vout k, vdd k,
gnd!, iref k), VDDk vdc VDD (acm 1 only for k = 3), IREFk idc IREF (+ vdd k → − iref k), CLk cap CL (vout k–gnd).
- k = 1: VIP1 vsin vdc = vo = VCM+VOS, va = AMP/2, freq FSIG, acm 0.5; VIN1 vsin vdc = vo = VCM, va AMP/2, sinephase 180, acm 0.5, acp 180.
- k = 2: VC2 vsin vdc = vo = VCM, va VCMA, freq 50, acm 1 (cm2–gnd); VDP2 vsin va VDA/2, 10 Hz (vinp2–cm2); VDN2 same, sinephase 180 (vinn2–cm2).
- k = 3: VIP3, VIN3 vdc VCM (no AC).
- k = 4: VP4 / VN4 vpulse v1 VCM, v2 VCM ± VSTEP/2, td 0.1, tr = tf 1u, pw 100, per 200.
Check the netlist: `mag` only on VIP1, VIN1, VC2, VDD3.

**Analyses (control files `phase2/net/p2_*.scs`):**
- `p2_pseudo_r`: sweep temp [0 27 37 80] { dc DV −1 → 1 step 1m }; save VA:p. R = dV/dI (numerical derivative; ADE: 1/deriv(-IDC("/VA/PLUS"))).
- `p2_geo_20p` / `p2_geo_10p`: sweep LIN [1u 2u 4u] { op; ac 1m–1M 20/dec; noise (vout1 0) 10m–100k 20/dec }; saves M1/M2 cgg, gm, ids, VDD1:p.
- `p2_main` (LIN 4u): op; noise (vout1 0) 10m–100k 20/dec; sweep CL [2p 5p] { ac 1m–1M 20/dec; stb 1m–10M 20/dec probe = I1.IPRB };
  alter temp 0/37/80 → ac; alter temp 27, LCIN1 = WCIN·1.001 → ac.
- `p2_tran` (VOS 0.3): tran 4 s maxstep 100u strobeperiod 100u errpreset conservative. `p2_thd`: sweep AMP [1m 3m 5m 8m] { same, 2 s }.
  `p2_t4long`: tran 40 s maxstep 2m strobe 2m.

**Extraction:**
- gain = ymax(dB20(VF("/vout1"))); f_HP/f_LP = cross(dB20(VF("/vout1")), gain − 3, 1, "rising"/"falling").
- PM/GM/crossover = Spectre stb margins (phaseMargin(getData("loopGain" ?result "stb"))).
- Input-referred noise = out/|H(f)| (H from the differential AC); Vni(0.5–200) = √∫(out/|H|)² df; Vni_total = √∫out² df (10 m–100 k)/10^(gain/20);
  NEF = Vni_total·√(2·Itot/(π·Ut·4kT·BW)), BW = f_LP − f_HP, Itot = |I(VDD1)|; PEF = NEF²·1.8.
- Contributors: per-instance noise summary (rd, rs, id, fn, total), composites summed, divided by |H|².
- Cp = OP("/I1/I0/M2" "cgg").
- CMRR = dB20(VF(vout1)/VF(vout2)), PSRR = dB20(VF(vout1)/VF(vout3)) at 10/50 Hz.
- THD = √(Σ h2…h10²)/h1 from an FFT of an integer number of 10 Hz periods (T1: 2–4 s; T2: 1–2 s). T3: FFT bins at 10/50 Hz of vout2.
- T4 recovery = last time |vout4 − 0.9| > 10 mV, minus 0.1 s.
- Maestro: `AFE_lib/tb_lna/maestro` (LNA_AC, LNA_STB, LNA_NOISE, LNA_TRAN) and `AFE_lib/tb_pseudo_r/maestro` (PR_DC) contain these
  analyses and expressions; temperature/CL/mismatch/amplitude sweeps must be added there as Corners/Parametric sets.
