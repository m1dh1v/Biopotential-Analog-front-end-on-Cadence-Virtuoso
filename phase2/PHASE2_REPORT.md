# Biopotential AFE — Phase 2 report: CCIA LNA (gpdk180, Spectre 21.1, NN)

All final numbers come from the **schematic netlists** of `AFE_lib/tb_lna` and `AFE_lib/tb_pseudo_r`
(OCEAN `createNetlist` → `p2_sims.py` control files). Plots are in `phase2/plots/`. Netlist-level prototypes
(`lna_design.py`, `proto.py`, `pr_char.py`) were used only for exploration.

New cells in AFE_lib: `bias_gen`, `ota_fc_lna`, `pseudo_r`, `lna_cci`, `tb_pseudo_r`, `tb_lna`
(+ maestro views `tb_lna/maestro`, `tb_pseudo_r/maestro`).

---
## 1. ota_fc_lna + bias network
Changes from `ota_fc`:
- **Cascode current 100 → 50 nA** per branch: loads M7/M8 = 1 × pmos 0.5u/20u (m = 1); sinks carry 250 nA = 10 × nmos_u5 at 25 nA each.
- **On-chip bias from one ideal IREF = 25 nA** (cell `bias_gen`, schematic `plots/sch_bias_gen.png`):
  - IREF → **MC** (nmos 4u/1u, diode) stacked on **MBN** (nmos_u5 diode). MBN gives nbn; MC on top gives
    **VCN = nbn + VGS(MC) = 1.091 V**. This costs no current beyond IREF.
  - **MBS** (nmos_u5 at nbn, 25 nA) sinks the PMOS branch: **MBP** (pmos_u2 diode) gives nbp, and **MCP**
    (pmos 20u/1u diode) under it gives **VCP = nbp − VSG(MCP) = 0.746 V**.
  - The tail is 16 × pmos_u2 at 25 nA = 400 nA. Every mirror is an exact unit count.
- Input pair: 10 × 50u/L_in, L_in swept (§6), chosen **L_in = 4 µm**.
- OTA schematic: `plots/sch_ota_fc_lna.png`.

**Current breakdown (I(VDD1) at op, L_in = 4u):**

| branch | current |
|---|---|
| tail M0 (16 × pmos_u2) | 400.1 nA |
| load M7 | 49.9 nA |
| load M8 | 49.9 nA |
| bias MBP–MCP–MBS branch | 25.0 nA |
| **OTA + bias network (excl. IREF)** | **524.9 nA** (target ≤ 550 nA ✔) |
| ideal IREF (MC–MBN branch) | 25.0 nA |
| total from VDD | 549.9 nA |
| (internal) sinks M3/M4 | 250.0 nA each |
| (internal) input M1/M2 | 200.1 nA each |
| (internal) cascodes M5/M6/M9/M10 | 49.9 nA each |

Op nodes: vout 0.900, ninv/nnon 0.900, VCN 1.091, nbn 0.632, nbp 1.198, VCP 0.746, tail 1.170, f1/f2 0.573/0.572,
x1 1.113, p1/p2 1.333 V. All devices are in their intended region (sat, or subthreshold-sat for M1/M2/M5/M6/MC/MCP).
Smallest margins: M9 VDS − Vdsat = 0.148 V, M7/M8 0.224 V, M6 0.267 V.

## 2. pseudo_r
Cell: MPA (D = G = mid, S = B = a) + MPB (D = G = mid, S = B = b), both **gpdk180 pmos 0.4u/4u** (`plots/sch_pseudo_r.png`).
Bench `tb_pseudo_r`: b = 0.9 V, a = 0.9 + DV, DV −1 → +1 V step 1 mV (reltol 1e-6, iabstol 1e-20, gmin 1e-20).
Plot `plots/2_pseudo_r_IV_R.png`.

| dV | −0.5 | −0.3 | −0.1 | 0 | +0.1 | +0.3 | +0.5 V |
|---|---|---|---|---|---|---|---|
| R (27 °C) | 8.1e8 | 2.26e10 | 5.75e11 | **8.67e11** | 5.75e11 | 2.26e10 | 8.1e8 Ω |

| T | 0 °C | 27 °C | 37 °C | 80 °C |
|---|---|---|---|---|
| R(dV = 0), one element | 4.65e12 | 8.67e11 | 4.72e11 | 1.16e10 Ω |
| R of the 6-element chain used | 2.8e13 | 5.2e12 | 2.8e12 | 7.0e10 Ω |

**Sizing note (another sizing is better than 1u/1u):** 1u/1u gives only 2.0e11 Ω (f_HP ≈ 4 Hz with Cf = 200 fF).
Long devices raise R but their gate capacitance shunts the element (τ ∝ L²). In the LNA, f_HP at 37 °C was
0.58 Hz for 2 × 0.4u/20u, 0.50 Hz for 3 × 0.4u/10u, 0.585 Hz for 4 × 0.4u/4u, **0.39 Hz for 6 × 0.4u/4u (chosen)** and
0.44 Hz for 8 × 0.4u/2u. So each feedback path uses **six `pseudo_r` cells in series** (deviation from "one element").

## 3. lna_cci and tb_lna
`plots/sch_lna_cci.png`. vinp → CIN1 → ninv (OTA vin); CF1 and the PR1 chain from vfb to ninv; **IPRB (iprobe) between
OTA vout and vfb**. vinn → CIN2 → nnon (OTA vip); CF2 and the PR2 chain from nnon to vref.
mimcap (1 fF/µm² + 0.1 fF/µm perimeter, square plates): Cin = 20 pF ↔ 141.22 µm, Cf = 200 fF ↔ 13.943 µm
(10 pF ↔ 99.80 µm, 100 fF ↔ 9.802 µm). Mismatch: CIN1 length LCIN1 = 1.001·WCIN.
`plots/sch_tb_lna.png`: four benches, each with its own LNA, VDD and IREF; a single VREF = 0.9 V; CL = CL (2 pF).
(1) differential vsin ±AMP/2 (AC ±0.5), VIP1 DC = VCM + VOS; (2) 50 Hz CM vsin (AC 1) + 10 Hz differential;
(3) DC inputs, VDD AC = 1 (PSRR); (4) ±VSTEP/2 pulses at 0.1 s.

## 4. AC (`plots/4_bode.png`)
| condition | midband | f_HP | f_LP |
|---|---|---|---|
| CL 2 pF, 27 °C | 39.94 dB | 0.240 Hz | 3201 Hz |
| CL 5 pF, 27 °C | 39.94 dB | 0.240 Hz | 1342 Hz |
| CL 2 pF, 0 °C | 39.94 dB | 0.078 Hz | 3391 Hz |
| **CL 2 pF, 37 °C** | 39.94 dB | **0.390 Hz** | 3130 Hz |
| CL 2 pF, 80 °C | 39.94 dB | **10.97 Hz** | 2804 Hz |

f_HP moves 140× from 0 to 80 °C (subthreshold/leakage-dominated pseudo-R). At 80 °C the LNA would cut ECG content.

## 5. Stability (`plots/5_stb.png`; iprobe I1.IPRB, stb 1 mHz–10 MHz)
| CL | loop gain @10 Hz | max loop gain | crossover | PM | GM |
|---|---|---|---|---|---|
| 2 pF | 45.3 dB | 94.3 dB | 3147 Hz | **89.4°** | 51.0 dB (@516 kHz) |
| 5 pF | 41.2 dB | 94.3 dB | 1333 Hz | **89.9°** | 58.4 dB |

## 6. Noise
**Comparison (all from tb_lna schematic, CL = 2 pF, Itot = 549.9 nA incl. IREF):**

| Cin/Cf | L_in | W·L | Cgg(M1) | (Cin+Cf+Cp)/Cin | gain | f_HP | f_LP | in@1 Hz | in@1 kHz | Vni 0.5–200 Hz | Vni_total | NEF | PEF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20p/200f | 1 µm | 500 | 1.39 pF | 1.079 | 39.93 | 0.240 | 3851 | 1601 n | 93.3 n | 3.646 µV | 7.934 µV | 3.65 | 24.0 |
| 20p/200f | 2 µm | 1000 | 2.43 pF | 1.132 | 39.94 | 0.240 | 3603 | 1230 n | 96.5 n | 2.843 µV | 7.680 µV | 3.65 | 24.0 |
| **20p/200f** | **4 µm** | **2000** | **4.51 pF** | **1.235** | 39.94 | 0.240 | 3201 | 1018 n | 106.9 n | **2.465 µV** | 7.869 µV | 3.97 | 28.4 |
| 20p/200f | 8 µm (extra) | 4000 | 8.68 pF | 1.444 | 39.94 | 0.240 | 2630 | — | — | 2.487 µV | 8.510 µV | 4.74 | — |
| 10p/100f | 1 µm | 500 | 1.39 pF | 1.149 | 39.88 | 0.477 | 3697 | 2077 n | 99.7 n | 4.248 µV | 8.423 µV | 3.96 | 28.2 |
| 10p/100f | 2 µm | 1000 | 2.43 pF | 1.253 | 39.89 | 0.477 | 3334 | 1794 n | 107.2 n | 3.576 µV | 8.374 µV | 4.14 | 30.9 |
| 10p/100f | 4 µm | 2000 | 4.51 pF | 1.461 | 39.89 | 0.478 | 2792 | 1652 n | 126.7 n | 3.345 µV | 8.878 µV | 4.80 | 41.5 |

(in = input-referred noise in V/√Hz; gm/ID of M1 = 29.6 / 28.8 / 27.8 / 26.6 for L = 1 / 2 / 4 / 8 µm.)
**Chosen: Cin = 20 pF, L_in = 4 µm** (minimum in-band Vni, as the spec asks). L = 8 µm is no better and fails f_LP.

**Chosen design** (`plots/6_noise.png`):
- Vni (0.5–200 Hz, brick-wall) = **2.465 µVrms**; Vni_total = √(∫ out² 10 mHz–100 kHz)/G = **7.869 µVrms**
- BW = f_LP − f_HP = 3201 − 0.24 = 3200.9 Hz
- **NEF** = 7.869e-6·√(2·5.4993e-7/(π·0.0259·1.6568e-20·3200.9)) = 7.869e-6·√2.549e11 = 7.869e-6·5.049e5 = **3.97**
  (with Itot excluding the ideal IREF, 524.9 nA: 3.88)
- **PEF** = NEF²·VDD = 3.973²·1.8 = **28.4**
- Cp = Cgg(M2) = 4.507 pF → (Cin + Cf + Cp)/Cin = (20 + 0.2 + 4.507)/20 = **1.235**

Contributors (input-referred):

| @1 Hz | V²/Hz | share |
|---|---|---|
| pseudo-R chains PR1 + PR2 (24 PMOS) | 4.82e-13 | 46.5 % |
| M2 flicker | 2.26e-13 | 21.7 % |
| M1 flicker | 2.26e-13 | 21.7 % |
| M8 flicker | 3.18e-14 | 3.1 % |
| M7 flicker | 3.18e-14 | 3.1 % |

| @1 kHz | V²/Hz | share |
|---|---|---|
| M1 thermal | 3.98e-15 | 34.8 % |
| M2 thermal | 3.98e-15 | 34.8 % |
| M4 sinks thermal | 1.35e-15 | 11.8 % |
| M3 sinks thermal | 1.35e-15 | 11.8 % |
| M7/M8 thermal | 1.9e-16 each | 1.6 % each |

Capacitors are noiseless in the model. Their effect is the gain/penalty factor, i.e. the input pair is amplified by 1.235.
Band shares (0.5–200 Hz): M1 32.4 %, M2 32.4 %, pseudo-R 15.8 %, M3/M4 sinks 5.7 % each, M7/M8 3.3 % each.

## 7. CMRR / PSRR
| case | f | Adm | Acm | Avdd | CMRR | PSRR |
|---|---|---|---|---|---|---|
| nominal | 10 Hz | 39.94 dB | −70.8 dB | −49.1 dB | 110.8 dB | 89.0 dB |
| nominal | 50 Hz | 39.94 dB | −57.0 dB | −49.1 dB | 97.0 dB | 89.0 dB |
| Cin1 +0.1 % | 10 Hz | 39.95 dB | −54.6 dB | −49.1 dB | 94.6 dB | 89.0 dB |
| Cin1 +0.1 % | 50 Hz | 39.95 dB | −52.7 dB | −49.1 dB | **92.7 dB** | 89.0 dB |

(Device mismatch is still not included, so CMRR is optimistic.)

## 8. Transient (`plots/8_T1.png`, `8_T2.png`, `8_T3.png`, `8_T4.png`; tran maxstep 100 µs, strobe 100 µs, errpreset conservative)
- **T1** (1 mV, 10 Hz, +300 mV on vin+ in its DC value): output DC = **0.9001 V**, fundamental 99.3 mV (39.94 dB), **THD = 0.026 %** (FFT 2–4 s, 10 harmonics).
- **T2** (VOS = 300 mV, 2 s, FFT 1–2 s):

| amplitude | output fundamental | h2 | h3 | THD | output range |
|---|---|---|---|---|---|
| 1 mV | 99.3 mV | 25 µV | 7 µV | **0.027 %** | 0.801–1.000 V |
| 3 mV | 295.8 mV | 1.87 mV | 1.30 mV | **0.85 %** | 0.610–1.199 V |
| 5 mV | 462.1 mV | 24.5 mV | 13.9 mV | **6.2 %** | 0.480–1.383 V |
| 8 mV | 665.9 mV | 51.6 mV | 34.7 mV | **9.6 %** | 0.312–1.582 V |

  Diagnosis: the distortion is mainly **OTA output swing (low side)**, not pseudo-R. The waveform compresses
  asymmetrically (5 mV: +0.48 / −0.42 V). The low limit is ≈ f2 + Vdsat(M6) ≈ 0.57 + 0.06 = 0.63 V, raised by
  VCN = 1.09 V. At 10 Hz the pseudo-R chain (≈ 3–5 TΩ) is negligible next to Zcf = 1/(2π·10·200 fF) = 80 GΩ, and each
  element sees < 80 mV even at 8 mV input.
- **T3** (100 mV, 50 Hz CM + 100 µV, 10 Hz differential): 10 Hz output = 9.93 mV; **residual 50 Hz at output = 141 µV**
  (CM gain −57.0 dB, ≈ 1.4 µV referred to the input).
- **T4** (50 mV differential step at 0.1 s; separate 40 s run, maxstep 2 ms): output saturates to 0.078 V, then is
  **within 10 mV of VREF after 6.70 s**.

## 9. Summary
| Spec | Target | Achieved | Pass/Fail |
|---|---|---|---|
| Midband gain | 40 ± 0.5 dB | 39.94 dB | PASS |
| f_HP @ 37 °C | < 0.5 Hz | 0.390 Hz | PASS (only with the 6-element chain) |
| f_LP @ 2 pF | ≥ 3 kHz | 3201 Hz | PASS (7 % margin; 1342 Hz @ 5 pF) |
| PM | > 60° | 89.4° (2 pF), 89.9° (5 pF) | PASS |
| Vni (0.5–200 Hz) | < 2 µVrms | 2.465 µVrms | **FAIL** |
| NEF | < 3.5 | 3.97 (3.88 excl. IREF) | **FAIL** |
| Itot (OTA + bias, excl. IREF) | ≤ 550 nA | 524.9 nA | PASS |
| CMRR @50 Hz with 0.1 % Cin mismatch | > 80 dB | 92.7 dB | PASS (no device mismatch) |
| THD @ 1 mV | < 1 % | 0.026 % | PASS |

## 10. Saved setups and files
- **Maestro (ADE Explorer) setups, created by SKILL** (`skill/p2_maestro.il`) and read back to verify:
  - `AFE_lib/tb_lna/maestro`, tests:
    - `LNA_AC` (dc op + ac 1 m–1 M, 20/dec; outputs gain_dB, f_HP, f_LP, CMRR_50Hz, PSRR_50Hz, Itot)
    - `LNA_STB` (stb 1 m–10 M, probe /I1/IPRB; PM, GM)
    - `LNA_NOISE` (noise /vout1 vs /gnd!, 10 m–100 k, iprobe /VIP1; rmsNoise)
    - `LNA_TRAN` (tran 4 s, maxstep 100u, strobe 100u, conservative, VOS = 0.3 test override)
  - `AFE_lib/tb_pseudo_r/maestro`, test `PR_DC`: dc sweep DV −1 → 1 step 1m, reltol 1e-6, gmin 1e-20; outputs I_PR, R_PR.
  - Design variables are stored in both setups. **The maestro setups were not run from the GUI.** The reported numbers come
    from Spectre runs of the same schematic netlists. Temperature runs, the CL sweep, the 0.1 % mismatch alter and the THD amplitude sweep
    were done as Spectre sweeps/alters and are **not** in the maestro setups (add them as Corners / Parametric sets).
- PNGs (all in `E:\EDA_MCP-main\EDA_MCP-main\bioafe_data\phase2\plots\`): `sch_bias_gen.png`, `sch_ota_fc_lna.png`,
  `sch_pseudo_r.png`, `sch_tb_pseudo_r.png`, `sch_lna_cci.png`, `sch_tb_lna.png`, `2_pseudo_r_IV_R.png`, `4_bode.png`,
  `5_stb.png`, `6_noise.png`, `8_T1.png`, `8_T2.png`, `8_T3.png`, `8_T4.png`; JSON: `geo_table.json`, `main_results.json`,
  `pseudo_r.json`, `tran_results.json`.

## 11. Problems, assumptions, deviations
1. **Vni 2.47 µV and NEF 3.97 fail.** The input-pair flicker (65 % of in-band power, after the 1.235 Cp penalty) and the pseudo-R noise
   (16 %) dominate. Even with zero pseudo-R noise Vni would be ≈ 2.26 µV. A larger input pair does not help (L = 8 µm: 2.49 µV). Chopping is
   the realistic fix.
2. **Pseudo-R: 6 elements in series per path** (spec: one element). With one element, f_HP@37 °C is 1.7–7 Hz depending on size.
   Each element is 2 × pmos 0.4u/4u instead of 1u/1u.
3. **Long pseudo-R devices bypass themselves** through their gate capacitance (2 × 0.4u/20u: f_HP 0.37 Hz vs 0.116 Hz predicted).
   Found by swapping in an ideal 6.84 TΩ resistor. The chosen chain is still 1.6× above 1/(2πRCf).
4. **f_HP temperature sensitivity**: 0.078 Hz (0 °C) → 0.39 Hz (37 °C) → 11 Hz (80 °C).
5. **Phase-1 AC-magnitude leak recurred**: new analogLib vdc instances got acm = 1. The generator now deletes it, and the netlist was
   checked (AC only on VIP1, VIN1, VC2, VDD3).
6. **Output swing limits THD above ~3 mV** (VCN = 1.09 V lifts the fold node). A wider MC (lower VCN) or a separate VCN branch would
   help, at the cost of sink headroom or current. Not done in this phase.
7. VIN1 phase 180° gives the differential drive. The output polarity is inverted for vinp (gain is −Cin/Cf); magnitudes are reported.
8. Ideal: IREF (25 nA), VREF (0.9 V). No device mismatch / Monte Carlo, no corners other than temperature, no layout parasitics
   (mimcap bottom-plate parasitic is not in the gpdk model).
9. NEF uses the total VDD current including the 25 nA ideal IREF (3.88 if excluded). T = 300 K, Ut = 25.9 mV as specified, while
   the sims ran at 27 °C (37 °C only for f_HP).
10. The mimcap symbol's displayed "c" is a text note; the netlisted value comes from w/l (WCIN, LCIN1, WCF variables).
11. Schematic nets use stubs and net labels (single gnd symbol on `gnd!` in the testbenches).

## Design Journal
See `../DESIGN_JOURNAL.md` (sections A–E cover Phase 1 + Phase 2).
