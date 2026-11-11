# Biopotential AFE — Phase 4 report: tunable Gm-C low-pass filter (gpdk180, Spectre 21.1, NN, 27 °C)

All final numbers come from the netlists of the Virtuoso schematics:
- `AFE_lib/tb_lpf` (filter alone) and `AFE_lib/tb_chain` (lna_v2 → lpf_gmc);
- for Step 0, `AFE_lib/tb_lna_v2`.

Netlist-level prototypes are `lpf.py`, `p4_proto.py` and `p4_cmp.py`. Final runs are `p4_sims.py`, extraction is `p4_results.py` and `p4_step0_results.py`, and results are in `plots/phase4_results.json` and `plots/step0.json`. The design journal has the Phase 4 sections A20–A24, B12–B15, a Phase 4 C table, D25–D31 and E11.

**Bottom line:**
- **The filter meets spec at NN, 27 °C, 0.5 Vpp.** It is a 2nd-order Butterworth OTA-C biquad built from multi-tanh-doublet gm cells: fc 150.1 Hz, Q fit 0.735 (peaking 0.003 dB), THD 0.535 %, output noise 28.1 µVrms (0.28 µV referred to the LNA input), 8.9 nA, tunable 100 Hz–1 kHz with one bias current.
- **What it costs or misses:**
  - The caps are 36 pF each (the guideline is ≤ 20 pF), forced by the noise spec.
  - THD is 3.6 % at 0.8 Vpp and 1.65 % at 80 °C.
  - The stopband flattens at −41 dB above 4 kHz because of capacitive feedthrough.
- **Surprise:** lna_v2's f_HP is really **0.152 Hz (27 °C) / 0.277 Hz (37 °C)**, not 0.240 / 0.390 Hz. The Phase 2/3 values were a simulator-tolerance artefact (iabstol = 1e-15); see §11.

---------------------------------------------------------------------------------------------------------
## 0. Cleanup of earlier phases (Step 0)

**0a. Readable schematics** (Virtuoso hiExportImage, zoomed tiles of 2400 × 1600 px; device names, sizes and net labels legible):
- `plots/sch_ota_fc_lna_v2_tile_r1c1.png`, `…r1c2`, `…r2c1`, `…r2c2` (four tiles);
- `plots/sch_lna_v2_tile_r1c1.png`, `…r1c2` (two tiles).

**0b. DC operating point of ota_fc_lna_v2** (tb_lna_v2, VOS = 0, all 171 BSIM3 instances in `plots/step0.json["op"]`). One line per unit; composite stacks show the top (saturated) segment, and the lower segments are in triode by design:

| device | I_D | gm/ID | V_GS | V_DS | V_dsat | margin | region |
|---|---|---|---|---|---|---|---|
| M0<0:15> (pmos_u2, top seg.) | 25.02 nA each | 12.6 | 0.549 | 0.578 | 0.131 | +0.446 | sat |
| M1 / M2 | 200.1 nA | 27.8 | 0.269 | 0.867 / 0.868 | 0.041 | +0.83 | subth |
| M3/M4<0:9> (nmos_u5, top seg.) | 24.93 nA each | 15.5 | 0.512 | 0.182 | 0.110 | **+0.072** | sat |
| M5 / M6 | 49.19 nA | 20.9 | 0.454 | 0.969 / 0.599 | 0.060 | +0.909 / +0.539 | subth |
| M7 / M8 | 49.19 nA | 12.7 | 0.529 | 0.331 / 0.332 | 0.129 | +0.20 | sat |
| M9 / M10 | 49.19 nA | 19.8 | 0.549 | 0.199 / 0.568 | 0.071 | +0.127 / +0.498 | sat |
| XB.MBN / MBS (top seg.) | 25.0 nA | 15.7 | 0.512 | 0.512 / 0.800 | 0.110 | +0.40 / +0.69 | sat |
| XB.MBP (top seg.) | 25.0 nA | 12.6 | 0.549 | 0.549 | 0.131 | +0.42 | sat |
| XB.MCP | 25.0 nA | 28.0 | 0.278 | 0.278 | 0.041 | +0.24 | subth |
| XB.MCN1 / MCN2 | 2.95 nA | 22.7 | 0.422 / 0.334 | = V_GS | 0.054 | +0.37 / +0.28 | subth |
| XB.MPV1–8 (16 segments) | 2.95 nA | 5–20 | | only MPV8.M1 has V_DS (0.892) | | +0.83 | sat |

**0c. CMRR and PSRR vs frequency** (`plots/0c_lna_v2_cmrr_psrr.png`; CM = both inputs in phase, PSRR = VDD1 AC, ratio to the differential gain):

| f | CMRR nominal | CMRR, Cin1 +0.1 % | PSRR |
|---|---|---|---|
| 0.1 Hz | 103.0 dB | 90.1 dB | 88.5 dB |
| 1 Hz | 127.1 dB | 94.7 dB | 88.5 dB |
| 10 Hz | 111.0 dB | 94.7 dB | 88.5 dB |
| 50 Hz | 96.9 dB | **92.7 dB** | 88.5 dB |
| 100 Hz | 90.9 dB | 89.4 dB | 88.5 dB |
| 1 kHz | 70.9 dB | 70.9 dB | 88.5 dB |
| 10 kHz | 51.0 dB | 51.0 dB | 81.2 dB |

Above about 50 Hz the CMRR falls 20 dB/decade. With the single-ended feedback (CF2 to vref), the common-mode transfer has a zero, and the differential gain rolls off above f_LP.

**0d. Input-pair L sweep, unchopped lna_v2** (W = 500 µm, 200 nA/device; `plots/0d_lna_v2_Lsweep_noise.png`, PSDs overlaid, Vni/NEF in the legend):

| L | Cp | f_LP | Vni 0.5–200 Hz | Vni_total | NEF |
|---|---|---|---|---|---|
| 1 µm | 1.39 pF | 3845 Hz | 3.633 µV | 7.94 µV | 3.66 |
| 2 µm | 2.43 pF | 3595 Hz | 2.827 µV | 7.71 µV | 3.68 |
| **4 µm** | 4.51 pF | 3192 Hz | **2.445 µV** | 7.91 µV | 4.01 |
| 8 µm | 8.68 pF | 2621 Hz (< 3 kHz) | 2.457 µV | 8.57 µV | 4.79 |

The noise has a minimum at 4 µm. That confirms the Phase 2 choice; 8 µm loses on penalty, f_LP and NEF.

**0e. Running the Phase 2/3 maestro setups from the GUI: not done.** The GUI Virtuoso session (yours, via MobaXterm) stopped responding to the MCP bridge during this phase, apparently waiting on a modal dialog: every command times out. All Phase 4 cells were built and netlisted with a separate headless Virtuoso instead. The maestro views exist and were read back in Phases 2/3, but no GUI run or screenshot was possible. To-do: close the dialog in the GUI, then run `tb_lna/maestro` and `tb_lna_chop/maestro` (`STATIC_STB` or `CHOP_PSS_PAC_PNOISE`).

---------------------------------------------------------------------------------------------------------
## 1. Specifications (Step 1)

| spec | target |
|---|---|
| topology | 2nd-order Butterworth (Q = 0.707) Gm-C low-pass after the LNA |
| fc | 150 Hz nominal; tunable ≥ 100 Hz–1 kHz with one bias current |
| passband gain | 0 dB |
| input range / linearity | LNA swing ±0.5 V around 0.9 V; THD < 1 % at 0.5 Vpp, fc/5 |
| noise | < 30 µVrms at the output, 0.1 Hz–3·fc (< 0.3 µV referred to the LNA input) |
| current | ≤ 100 nA total at nominal fc |
| input capacitance | ≪ 2 pF (the LNA is specified with CL = 2 pF) |
| output CM / margins | 0.9 V; all devices saturated or weak inversion, margin ≥ 50 mV |
| internal loops | PM > 60° if any |
| fc drift | characterise at 0/27/37/80 °C |

**Single-ended, chosen.** The LNA output is single-ended (referenced to VREF), and Phase 5's PGA can follow the same convention. A differential filter would need a single-to-differential stage plus common-mode feedback, which roughly doubles the current and area for no benefit while the LNA's own common-mode rejection is ≈ 93 dB.

---------------------------------------------------------------------------------------------------------
## 2. Design and hand calculations (Step 2)

**Topology: OTA-C biquad with two integrators.**
- C1·dV1/dt = Gm1·(Vin − Vout) and C2·dVout/dt = Gm2·(V1 − Vout).
- So H(s) = Gm1Gm2 / (s²C1C2 + s·C1Gm2 + Gm1Gm2), with ω0 = √(Gm1Gm2/(C1C2)) and Q = √(Gm1C2/(Gm2C1)).
- **C1 = C2 = C and Gm2 = 2·Gm1** give Q = 1/√2 and ω0 = √2·Gm1/C.
- Gm2 is two identical gm cells in parallel (G2<0:1>), so the ratio is exact by construction. The DC gain is exactly 1 because both cells compare against Vout.
- There is no internal loop with its own gain (each integrator is a one-pole Gm-C), so PM isn't defined beyond the biquad itself. The step response (4.45 % overshoot; ideal Butterworth 4.3 %) confirms Q.

**Required gm:** Gm1 = 2π·fc·C/√2.

| C | Gm1 | Gm2 | tail current, plain WI pair (I_T = 2·n·U_T·Gm, n ≈ 1.3) |
|---|---|---|---|
| 5 pF | 3.33 nS | 6.66 nS | 0.22 / 0.45 nA |
| 20 pF | 13.3 nS | 26.7 nS | 0.90 / 1.80 nA |
| **36 pF (chosen)** | **24.0 nS** | **48.0 nS** | 1.62 / 3.24 nA |

Sub-nA currents are biasable in this model: junction leakage with real ad/as is ≈ 0.07 fA, i.e. 10⁻⁴ of 1 nA, and the BSIM3 weak-inversion law holds there. No degeneration or moderate inversion is needed for *biasing*; it is needed for **linearity**.

**Linearity is the central problem.** At fc/5 the Gm cells see only the *error* signals, not the full input:
- Gm1 sees Vin − Vout = |1 − H(j0.2)|·Vin = 0.285·Vin, i.e. **±71 mV** at 0.5 Vpp;
- Gm2 sees V1 − Vout = (ω/ω0)·√(C2Gm1/(C1Gm2))·Vout = 0.141·Vin, i.e. **±35 mV**.

But both inputs of each cell move with the full **±0.25 V common mode**, so the input stage needs a wide common-mode range. A weak-inversion pair is linear (10 % gm drop) only to about ±nU_T·0.65 ≈ ±22 mV.

**Linearisation methods compared** (netlist prototypes, same biquad with C = 20 pF, each re-biased to fc ≈ 150 Hz):

| gm cell | gm / I_T | linear range (gm −10 %) | THD 0.5 Vpp @ 30 Hz | output noise | I total |
|---|---|---|---|---|---|
| A: plain WI PMOS pair | 1/(2nU_T) | ±22 mV | 3.92 % | 36.1 µV | 3.7 nA |
| **B: multi-tanh doublet, a = 4** (two pairs with ±nU_T·ln a offset) | 4a/((1+a)²·nU_T) = 0.64/(nU_T) for two tails | **±52–54 mV** | **0.51 %** | 43.1 µV | 5.0 nA |
| C: diode source degeneration (diode-connected PMOS in series with each source) | ≈ 1/(4nU_T) | ±46 mV | 0.69 % | 45.3 µV | 7.3 nA |

**Chosen: B.** It has the widest linear range and the lowest THD, and it adds no extra stacked V_GS (C needs one more diode drop, so the top input CM limit drops by ≈ 0.25 V). Its gm stays ∝ I_T, so tuning by one current still works. The noise penalty of B over A is (1+a)²/(4a) = 1.56 in noise power for the same gm.

**Noise and capacitor size.** In a Gm-C filter the output noise is kT/C-like, v_n² ≈ ξ·kT/C, and does not depend on the current. ξ is the excess factor from the number of noisy devices, n/2 per WI device, and the doublet penalty.
- **Hand:** ξ ≈ 2 cells × 2 (pair + mirror) × n/2 × 1.56 ≈ 4.1, so C ≥ ξkT/v_n² = 4.1·4.14e-21/(30 µV)² = **18.9 pF**.
- **Simulation with C = 20 pF:** 38–43 µV, i.e. ξ_eff ≈ 7 (−42 % hand error; see the journal C table). The mirror and the doublet's separate tails add more than estimated.
- **Mitigations tried:** mirror loads as 5-segment stacks (0.4u/20u each: nmos_u5, reused) and 5-segment tails (pmos_t5 = 5 × 2u/20u, new). These lower gm/ID and flicker and brought the noise from 43 to 38 µV.
- **Result:** the remaining noise is the thermal floor of the input pairs, so **C = 36 pF** each (WCL = 189.4 µm square mimcap, ≈ 1.0 fF/µm²) gives 28 µV. MIM area is 2 × 35 870 µm² = **0.072 mm²** (vs 0.040 mm² for the LNA's Cin/Cf). Total transistor gate area is ≈ 4 600 µm².

**Tuning:** IB (pulled from pin `ib`) biases the pmos_t5 diode MB, and every tail (MTA/MTB in each cell, also pmos_t5) mirrors it 1:1, so I_T = IB. fc = √2·Gm1/(2πC) with Gm1 = 0.64·IB/(nU_T), so **fc ≈ 118 Hz/nA·IB** by hand (n = 1.3). Total current = 7·IB (MB + 3 cells × 2 tails). On chip, IB = IREF/N from a ratioed nmos_u5 mirror: IREF 25 nA / 20 → 1.25 nA for 150 Hz.

**Cells reused / respecting the PDK limits:**
- **Reused:** nmos_u5 (mirror loads).
- **New:** pmos_t5 (5 × pmos 2u/20u in series) and gm_cell.
- **PDK limits:** every device has W ≥ 0.4 µm, L ≤ 20 µm and ad/as/pd/ps (0.6 µm·w, 2w + 1.2 µm).

---------------------------------------------------------------------------------------------------------
## 3. Schematics

Exported from the headless Virtuoso (see §0e). Schematic Check was run on every cell. The only warnings are intended:
- "shorted output" on G2<0:1>, i.e. the two cells in parallel;
- floating outputs in the testbenches (unloaded vout).

| cell | pins | contents |
|---|---|---|
| `pmos_t5` | D G S B | 5 × pmos 2u/20u series (L_eff 100 µm), common gate |
| `gm_cell` | vdd vss inp inn nbt out | MTA/MTB pmos_t5 tails (G nbt); M1A pmos 10u/10u m4 (d1, inp, ta, ta), M2A m1 (out, inn, ta, ta), M1B m1 (d1, inp, tb, tb), M2B m4 (out, inn, tb, tb); MN1 nmos_u5 diode (d1), MN2 nmos_u5 (out, G d1) |
| `lpf_gmc` | vdd vss vin ib vout | MB pmos_t5 diode on ib; G1 gm_cell (inp vin, inn vout, out v1); G2<0:1> gm_cell (inp v1, inn vout, out vout); C1 (v1) and C2 (vout) mimcap WCL × WCL |
| `tb_lpf` | — | bench 1: vsin VIN1 (VCM, AMP, FSIG, AC mag 1); bench 2: vpulse step (VSTEP at TSTEP); bench 3: two-tone vsin (VA1/F1 + VA2/F2); own VDDk and IBk each |
| `tb_chain` | — | lna_v2 (own VDDL, IREFL, CL 2 pF, VIP/VIN ±0.5 AC) → lpf_gmc (own VDDF, IBF); VREF is the only shared net (a reference, not a bias node) |

Schematic screenshots (headless Virtuoso under xvfb, hiExportImage, zoomed tiles 2400 × 1600):
- new cells: `plots/sch_gm_cell_tile_r1c1/2.png`, `sch_lpf_gmc_tile_r1c1/2.png`, `sch_tb_lpf_tile_r1c1..3.png`, `sch_tb_chain_tile_r1c1/2.png`, `sch_pmos_t5_tile_r1c1.png`;
- Step 0a: `sch_ota_fc_lna_v2_tile_*`, `sch_lna_v2_tile_*`.

**Netlist hygiene** (`tb_lpf_sch.scs`, `tb_chain_sch.scs`, copied from the netlister output to `.scs` names):
- `mag` appears only on VIN1 (tb_lpf) and VIP/VIN (tb_chain);
- no pacmag;
- no shared bias nodes between the LNA and the filter (separate VDD, IREF/IB).

---------------------------------------------------------------------------------------------------------
## 4. Verification (Step 3; tb_lpf unless noted)

**1. DC operating point** (IB = 1.27 nA):
- **Bias points:** vout = 0.8995 V and v1 = 0.9000 V. I(VDD) = **8.90 nA** including IB (= 7 × IB exactly).
- **All devices in weak inversion** (BSIM region 3):
  - input pairs: I_D = 1.016 / 0.254 nA (4:1 split), gm/ID 29.9, V_SG 0.188 V;
  - mirrors: gm/ID 23, V_GS 0.343 V;
  - tails: gm/ID 23.7, V_SG 0.349 V.
- **Smallest margin** (single devices and top stack segments): **M2A/M2B +0.147 V** (V_SD 0.188, V_dsat 0.040). The full table is in `phase4_results.json["op"]`.
- **Input common-mode limits:**
  - top: 1.8 − V_SG,pair (0.19) − tail stack (≈ 0.15) ≈ 1.46 V;
  - bottom: the V_SD of M2A/B (V_out − V_mirror) stays ≥ 50 mV down to ≈ 0.45 V.

**2. AC** (`plots/2_ac_vs_butterworth.png`, overlaid with the ideal Butterworth at the same fc):

| quantity | value |
|---|---|
| passband gain | −0.006 dB |
| fc (−3 dB) | **150.1 Hz** |
| peaking | 0.003 dB |
| LS fit | f0 = 144.8 Hz, **Q = 0.735** (ideal 0.707) |
| deviation from Butterworth in band (< 3 fc) | ≤ 0.9 dB (largest just below the notch) |
| roll-off 2 fc–6 fc | −46.8 dB/dec (the notch steepens it) |
| notch | 1.50 kHz at −68.5 dB |
| stopband floor | **−40.8 dB above 4 kHz** (feedthrough, see §5) |
| phase at fc | −90.5° (ideal −90°) |
| group delay | 1.48 ms at 1 Hz, 1.54 ms at fc/5, 1.53 ms at fc; peak 1.8 ms at ≈ 100 Hz, same as ideal |
| input capacitance | 0.019 pF @ 10 Hz, 0.060 pF @ 50 Hz, **0.384 pF @ 150 Hz**, 0.389 pF @ 1 kHz (≪ 2 pF) |

The input capacitance is bootstrapped in the passband because the doublet sources follow the input.

**3. Tuning** (`plots/3_tuning.png`):

| IB | fc | I(VDD) | gain | peaking | noise (0.1 Hz–3 fc) |
|---|---|---|---|---|---|
| 0.85 nA | 101.4 Hz | 5.96 nA | −0.006 dB | 0.003 dB | 28.5 µV |
| **1.27 nA** | **149.6 Hz** | **8.90 nA** | −0.006 dB | 0.003 dB | 28.1 µV |
| 2.50 nA | 288.6 Hz | 17.5 nA | −0.006 dB | 0.004 dB | 27.4 µV |
| 4.20 nA | 474.7 Hz | 29.4 nA | −0.006 dB | 0.005 dB | 26.8 µV |
| 6.30 nA | 700.6 Hz | 44.1 nA | −0.006 dB | 0.006 dB | 26.4 µV |
| 8.50 nA | 928.9 Hz | 59.5 nA | −0.006 dB | 0.007 dB | 26.0 µV |
| 9.20 nA | **1004 Hz** | 64.4 nA | | | |
| 10.0 nA | 1086 Hz | 70.0 nA | | | |

fc ≈ 118 Hz/nA × IB at the low end, falling to 109 Hz/nA at 9 nA as the pairs move toward moderate inversion. The 100 Hz–1 kHz range costs 5.9–64 nA, all ≤ 100 nA. Noise is nearly independent of fc, as expected for kT/C.

**4. Noise** (`plots/4_noise.png`):
- **Output:** **28.13 µVrms** over 0.1 Hz–450 Hz. Divided by the LNA gain (99.3), that is **0.283 µV** referred to the LNA input.
- **Contributors** (share of output noise power; flicker part in brackets):

| contributor | share (flicker) |
|---|---|
| Gm1 input pairs | 26.8 % (2.3 %) |
| Gm1 mirror | 23.8 % (1.1 %) |
| Gm2 pairs | 17.7 % (0.2 %) |
| Gm2 mirrors | 16.3 % (0.2 %) |
| Gm1 tails | 9.0 % |
| Gm2 tails | 6.1 % |
| bias diode MB | 0.2 % |

  Thermal noise dominates (the flicker total is ≈ 4 %).
- **Chain** (`plots/7_chain.png`): Vni(0.5–150 Hz) at the LNA input is **2.314 µV with the filter vs 2.301 µV for the LNA alone (+0.6 %)**. The LNA stays the dominant block.

**5. THD at fc/5 = 30 Hz** (`plots/5_thd.png`; FFT over 6 cycles after 0.1 s, uniform resample, harmonics 2–10):

| input | THD | HD2 | HD3 |
|---|---|---|---|
| 0.10 Vpp | 0.007 % | 0.007 % | 0.001 % |
| 0.25 Vpp | 0.032 % | 0.017 % | 0.027 % |
| **0.50 Vpp** | **0.535 %** | 0.041 % | 0.528 % |
| 0.80 Vpp | 3.57 % | 0.12 % | 3.53 % |

HD3 dominates: this is the doublet's compressive tanh, reached when Gm1's error input (±71 mV at 0.5 Vpp, ±114 mV at 0.8 Vpp) exceeds its ±54 mV linear range.

**Two-tone** 30 + 37.5 Hz at 0.25 Vpp each: **IM3 −43.3 dBc** (`plots/6_step_im3.png`).

**6. Transient:**
- **100 mV step:** final 99.93 mV, **overshoot 4.45 %** (ideal Butterworth 4.3 %), 1 % settling 7.16 ms.
- **1 Hz + 40 Hz, 0.2 Vpp each** (3 s; `plots/6_sine_1_40Hz.png`): gain 0.9993 at 1 Hz and 0.9983 at 40 Hz (ideal 0.9975). Output mean 0.8995 V; CM drift −0.00 mV between consecutive whole 1 Hz periods.
- **Output DC offset** vs the input CM: −0.5 mV (vout 0.8995 V for vin 0.9 V).

**7. Temperature:**

| T | fc | gain | noise | THD 0.5 Vpp | I(VDD) | vout DC |
|---|---|---|---|---|---|---|
| 0 °C | 165.6 Hz | −0.006 dB | 27.0 µV | 0.450 % | 8.90 nA | 0.8996 V |
| 27 °C | 150.1 Hz | −0.006 dB | 28.1 µV | 0.535 % | 8.90 nA | 0.8995 V |
| 37 °C | 144.3 Hz | −0.006 dB | 28.5 µV | 0.569 % | 8.90 nA | 0.8995 V |
| 80 °C | **101.4 Hz** | −0.007 dB | 31.7 µV | **1.651 %** | 8.90 nA | 0.8990 V |

**Explanation:**
- **fc drift:** with a constant (ideal) IB, gm = I/(nU_T) ∝ 1/T, which by itself gives fc ∝ 1/T: 165.6 → 150.1 → 144.3 Hz from 0 to 37 °C tracks 1/T almost exactly. At 80 °C, fc drops more (101 Hz instead of the 1/T value of 128 Hz). The likely cause, **not yet isolated by simulation**, is junction leakage and the temperature dependence of n and of the mirror/tail matching at sub-nA currents, which shift the doublet's current split and its effective gm. An IB-vs-T and leakage-current check is on the to-do list.
- **THD:** the linear range (∝ nU_T) only grows ∝ T, while the leakage-induced imbalance at 80 °C moves the doublet off its flat region, hence 1.65 %.
- **Fixes:** a PTAT IB (gm = I_PTAT/(nU_T) ≈ constant) would cancel the 1/T part. The 80 °C part needs higher currents (moderate IB, larger C) or a leakage-tolerant layout.

**8. Power:** 8.90 nA (16.0 nW) at 150 Hz; 5.96 nA at 100 Hz; 64.4 nA at 1 kHz. Current = 7·IB.

**9. Chain** (lna_v2 → lpf_gmc):
- **AC band:** gain 39.94 dB, band **0.152 Hz – 150.5 Hz** (−3 dB).
- **Noise:** 2.314 µV at the chain input (0.5–150 Hz).
- **DC:** LNA output 0.9000 V, filter output **0.8995 V**.
- **Current:** LNA 551.6 nA, filter 8.90 nA.
- **T1** (1 mV 10 Hz + 300 mV electrode offset, 4 s): output DC 0.8996 V, fundamental 99.30 mV, **THD 0.007 %**.

**10. ECG PWL file:** none in `bioafe_data`, so this was skipped (Phase 6).

---------------------------------------------------------------------------------------------------------
## 5. Results vs spec

| spec | target | achieved | pass/fail |
|---|---|---|---|
| fc nominal | 150 Hz | 150.1 Hz | **pass** |
| response | Butterworth, Q = 0.707 | Q fit 0.735 (peaking 0.003 dB); in-band dev ≤ 0.9 dB | **pass** |
| tuning range by one current | ≥ 100 Hz–1 kHz | 101 Hz (0.85 nA) – 1004 Hz (9.2 nA), single IB | **pass** |
| passband gain | 0 dB | −0.006 dB | **pass** |
| THD @ 0.5 Vpp, fc/5 | < 1 % | 0.535 % (27 °C); 0.45–0.57 % (0–37 °C) | **pass** |
| THD @ 0.5 Vpp, 80 °C | (characterise) | 1.65 % | over 1 % |
| full LNA swing ±0.5 V | (input range) | 0.8 Vpp → 3.6 % THD; 1 Vpp not linear | **partial** |
| output noise 0.1 Hz–3 fc | < 30 µVrms | 28.1 µV (0.283 µV at the LNA input) | **pass** (7 % margin) |
| current at nominal fc | ≤ 100 nA | 8.90 nA | **pass** |
| filter input capacitance | ≪ 2 pF | 0.38 pF (fc and above), 0.02 pF at 10 Hz | **pass** |
| output CM | 0.9 V | 0.8995 V | **pass** |
| device margins | ≥ 50 mV, saturated or WI | min +0.147 V, all WI | **pass** |
| internal loop PM | > 60° if any | no separate loops; step overshoot 4.45 % = Butterworth | n/a |
| fc drift 0/27/37/80 °C | characterise | 165.6 / 150.1 / 144.3 / 101.4 Hz | reported |
| caps ≤ 20 pF "if possible" | guideline | 36 pF each | **not met** (noise-driven) |

---------------------------------------------------------------------------------------------------------
## 6. What did not meet spec (honest list)

1. **Capacitors are 36 pF, not ≤ 20 pF.** With 20 pF the noise is 38 µV (fails < 30 µV). Gm-C dynamic range is DR ∝ V_lin·√(C/(ξkT)), so with this linearisation either C or V_lin had to give. Cost: 0.072 mm² of MIM.
2. **The full LNA swing (±0.5 V) is not handled linearly.** THD is 3.6 % at 0.8 Vpp. The filter is linear (< 1 %) up to ≈ 0.6 Vpp at fc/5. At lower frequencies the margin is larger, since the Gm1 error signal ∝ f.
3. **80 °C:** THD 1.65 % and fc −32 %. Of that, −15 % is the expected 1/T; the rest is not yet explained (see §7). PTAT biasing would remove the 1/T part.
4. **Stopband floor −41 dB above 4 kHz.** The input reaches V1 and Vout through the pair's C_gs and the source-follower action of the tails: a feedforward path that cancels the main path at 1.5 kHz (notch) and then sets a flat floor. The floor is fine for 50/60 Hz harmonics (−68 to −45 dB), but it limits any anti-aliasing role. Fixes: smaller pair devices (less C_gs), a cascode/source-follower input buffer, or a 3rd-order or extra passive RC pole.
5. **Step 0e** (running maestro from the GUI) was not possible: the GUI session is blocked.
6. **Not done:** Monte Carlo (the doublet's 4:1 ratio matching and the 1:2 Gm2/Gm1 ratio set Q and THD), process corners (SS/FF), supply variation, layout parasitics, a real IREF/N and PTAT bias generator.

---------------------------------------------------------------------------------------------------------
## 7. Surprises (hand numbers off by more than 20 %, and others)

1. **lna_v2's f_HP is 0.152 Hz (27 °C) / 0.277 Hz (37 °C), not 0.240 / 0.390 Hz.** The Phase 2/3 benches used iabstol = 1e-15. Rerunning the same netlist with iabstol = 1e-18 and 1e-21 (and reltol 1e-6/1e-7) converges to 0.152 / 0.276–0.277 Hz, with identical DC node voltages. The pseudo-R chain's small-signal conductance at fA bias currents is resolved only at the tighter tolerance. The Phase 2 hand calculation (0.153 Hz) was **right to within 1 %**, and the "−36 % hand error" in the journal was a simulator artefact. The spec (< 0.5 Hz at 37 °C) passes with more margin. *All Phase 4 runs use iabstol = 1e-18.*
2. **Noise excess ξ was ≈ 7, not ≈ 4** (hand C ≥ 18.9 pF vs 32–36 pF needed). The mirror loads and the doublet's two tail sources contribute more than the "n/2 per device" estimate, because at these currents the mirrors run at gm/ID ≈ 23, almost as high as the pairs.
3. **Diode degeneration (C) was noisier and no more linear than the doublet,** although it halves gm/I_T (twice the current for the same Gm).
4. **The biquad is more linear than the gm-cell DC transfer alone suggests.** Gm1's error input (±71 mV at 0.5 Vpp) exceeds its ±54 mV (−10 % gm) linear range, yet the THD is only 0.53 %: the loop suppresses part of the cell's distortion.
5. **The 80 °C fc drop (−32 %) is twice the 1/T prediction (−15 %).** I suspect sub-nA leakage and matching effects, but haven't verified it.

---------------------------------------------------------------------------------------------------------
## 8. Files

- **Report / data:** `phase4/PHASE4_REPORT.md`, `plots/phase4_results.json`, `plots/step0.json`.
- **Plots:**
  - Step 0: `0c_lna_v2_cmrr_psrr.png`, `0d_lna_v2_Lsweep_noise.png`;
  - filter: `2_ac_vs_butterworth.png`, `3_tuning.png`, `4_noise.png`, `5_thd.png`, `6_step_im3.png`, `6_sine_1_40Hz.png`;
  - chain: `7_chain.png`;
  - schematics: `sch_ota_fc_lna_v2_tile_r*c*.png`, `sch_lna_v2_tile_r1c*.png`.
- **Scripts:** `lpf.py`, `p4_proto.py`, `p4_cmp.py` (prototype comparison), `gen_skill4.py` (cells), `p4_sims.py` (final runs), `p4_results.py`, `p4_step0.py`, `p4_step0_results.py`, `opinfo.py` (op.info reader).
- **SKILL:** `skill/p4_cells.il`, `skill/p4_export.il`.
- **Raw PSF:** `raw/p4_*`.
