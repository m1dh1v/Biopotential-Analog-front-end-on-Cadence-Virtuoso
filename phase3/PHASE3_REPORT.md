# Biopotential AFE — Phase 3 report: chopper-stabilized CCIA LNA (gpdk180, Spectre 21.1, NN, 27 °C)

All final numbers come from the netlists of the Virtuoso schematics `AFE_lib/tb_lna_v2` and `AFE_lib/tb_lna_chop`. Scripts,
netlists and raw PSF are in `bioafe_data/phase3/` (`p3_sims.py`, `p3_*_results.py`; netlist-level prototypes are `lna3.py`,
`s1_swing.py`, `s2_proto.py`, `s3_sweep.py`). Plots are in `bioafe_data/phase3/plots/`. The design journal
(`bioafe_data/DESIGN_JOURNAL.md`) has the Phase 3 sections A12–A18, B7–B11, C (Phase 3 table), D16–D24 and E10.

**Bottom line.**
- **The swing fix works.** THD at 5 mV drops from 6.2 % to 0.093 % with no chopping, and to 0.057 % with chopping.
- **Chopping inside the OTA, as specified, removes the input-pair and load flicker plateau** (the PSD is lower than Phase 2 above about 4 Hz).
- **It also creates a switched-capacitor path at the high-impedance input nodes.** In this architecture, the chopper switching the input-pair gate capacitance between ninv and nnon, with the TΩ pseudo-R as the only DC path, causes two problems:
  - Excess noise rising as 1/f below about 4 Hz, which makes the 0.5–200 Hz integral worse than Phase 2: **2.99 µV vs 2.47 µV**.
  - A femtoamp charge pump that the 5 TΩ pseudo-R turns into a large DC offset: **12 mV nominal, and the output saturates for a 10 % switch mismatch**.

  With the pair re-optimised (W = 10 µm, L = 1 µm), input-pair cascodes, a load-mirror chopper and f_chop = 5 kHz, that is the best I could get. It fails the noise, NEF, ripple and offset specs. Section 11 explains the root cause, and the journal (A14–A16, D) gives the fixes.

---------------------------------------------------------------------------------------------------------
## 1. Output-swing fix (Step 1): `bias_gen_v2`, `ota_fc_lna_v2`, `lna_v2`

**Problem (Phase 2):** VCN was 1.091 V (MC diode stacked on the MBN reference), so the folding nodes sat at 0.57 V. vout could not go below ≈ 0.63 V.

**Why resizing MC does not work:** VCN = V(nbn) + Vgs(MC) ≥ 0.632 + ≈ 0.35 V (a very wide MC with body effect) ≈ 0.98 V. That is still too high.

**What I did:**
- **Separate VCN branch:** MPV1–8 (8 × pmos_u2 in series, gate nbp) supply ≈ 3 nA into two stacked NMOS diodes, MCN1/MCN2 (0.4u/10u each). This gives VCN = 0.756 V, and the mid-node vcm1 = 0.334 V is reused in Step 2.
- **MC removed:** IREF goes straight into MBN, so nbn = iref = 0.632 V.
- **Load mirror widened:** M7/M8 changed from 0.5u/20u to 2u/20u. Vdsat drops from 0.243 to 0.129 V, which gives the high side room.
- **PMOS cascode-bias diode:** MCP (20u/1u) now has its bulk tied to its source (own n-well), so VCP = 0.920 V.

The input-referred load flicker stays the same (strong inversion, so it scales as 1/L).

| node | Phase 2 | Phase 3 (v2) |
|---|---|---|
| VCN | 1.091 V | **0.756 V** |
| VCP | 0.746 V | 0.920 V |
| folding nodes f1/f2 | 0.572 V | **0.302 V** |
| x1 / p1 / p2 | 1.113 / 1.333 / 1.333 V | 1.271 / 1.469 / 1.468 V |
| I(VDD) incl. / excl. ideal IREF | 549.9 / 524.9 nA | **551.6 / 526.6 nA** |

The VCN branch costs 2.95 nA. The loads now carry 49.2 instead of 49.9 nA. By the Phase 2 convention (excluding the ideal reference), current is 526.6 nA, which meets ≤ 550 nA. Including IREF it is 551.6 nA, 0.3 % over.

**Saturation margins (schematic op, `plots/step1_v2.json`)**

| device | V_DS | V_dsat | margin |
|---|---|---|---|
| M3/M4 stack, top segment (M3<0>.M0) | 0.182 V | 0.110 V | **+0.072 V** |
| M3/M4 whole stack (f1 = 0.302 V) vs stack "Vdsat" (I = 98 % of I(0.6 V), measured on nmos_u5) | 0.302 V | 0.217 V | **+0.085 V** |
| M5 / M6 | 0.969 / 0.599 V | 0.060 V | +0.909 / **+0.539 V** |
| M7 / M8 | 0.331 / 0.332 V | 0.129 V | +0.20 V |
| M9 / M10 | 0.199 / 0.568 V | 0.071 V | +0.127 / +0.498 V |
| M1 / M2 | 0.867 V | 0.041 V | +0.83 V |

The lower four segments of each nmos_u5 stack are in triode by design (series-stacked device).

**THD, T2 on the non-chopped lna_v2** (`plots/1_T2_lna_v2.png`; 10 Hz, +300 mV electrode offset, CL = 2 pF, FFT over 1–2 s):

| amplitude | Phase 2 THD | **Phase 3 lna_v2 THD** | output range |
|---|---|---|---|
| 1 mV | 0.026 % | 0.014 % | 0.801–1.000 V |
| 3 mV | 0.85 % | 0.024 % | 0.602–1.199 V |
| 5 mV | 6.2 % | **0.093 %** (target < 1 %) | 0.405–1.399 V |
| 8 mV | 9.6 % | 5.9 % | **0.233**–1.645 V |

The low-side limit is now **≈ 0.23 V** (target ≤ 0.45 V). AC and noise are unchanged from Phase 2: 39.94 dB, f_HP 0.240 Hz, f_LP 3192 Hz, Vni 2.445 µV, NEF 4.01.

---------------------------------------------------------------------------------------------------------
## 2. Chopper OTA and schematics (Step 2)

**Screenshots** (Virtuoso hiExportImage, `plots/`):
- `sch_ota_fc_chop.png`: CH1/CH2/CH3 groups annotated on the schematic.
- `sch_ota_fc_chop_os.png`: test copy with VOSI in series with the M1 gate.
- `sch_bias_gen_v2.png`, `sch_ota_fc_lna_v2.png`, `sch_lna_v2.png`.
- `sch_lna_chop.png` (6-element pseudo-R) and `sch_lna_chop_pr10.png`.
- `sch_tb_lna_chop.png`, `sch_tb_lna_v2.png`.
- Clock waveforms: `2_clocks.png`.

**`ota_fc_chop`** (pins vdd, vss, vip, vin, iref, vout, c1, c1b, c2, c2b, o1, o1b, o2, o2b, o3, o3b, o4, o4b):
- **Core:** the Phase 3 v2 core, with three deviations, each justified in A14/A15/B8:
  - input pair M1/M2 = pmos w = WINF (1 µm) × m = 10, l = LIN (1 µm);
  - **input-pair PMOS cascodes MC1/MC2** (50u/1u × 4, gate vcm1 = 0.334 V, d1/d2 ≈ 0.70 V);
  - **M5/M6 0.4u/4u** (was 1u).
- **CH1 (input chopper):** vip/vin → g1/g2 (M1/M2 gates).
  - Four CMOS transmission gates (nmos 0.8u/0.18u + pmos 0.8u/0.18u), each with **half-size dummies** (0.4u/0.18u, D = S = gate node, driven by the complementary clock) on the g side.
  - **Non-overlapping c1/c2: gap 35 ns** (50 % crossings).
  - The CH1A nmos width is the variable WS1A (0.8 µm), used for the mismatch test.
- **CH2 (demodulator):** f1/f2 (pair-cascode drains + sinks) → s5/s6 (M5/M6 sources). Four TGs, **overlapping o1/o2: 35 ns** (make-before-break).
- **CH3 (added, see Step 2 load test):** p1/p2 (M7/M8 drains) → q9/q10 (M9/M10 sources). Four TGs, overlapping o3/o4.
- **Clocks:** ideal vpulse sources in the testbench (0/1.8 V, rise/fall TR = 5 ns, period 1/FCH, TNO = TOV = 30 ns).
  - STAT = 1 freezes every chopper in phase 1 (static reference).
  - CH3EN = 0 freezes CH3 only.

**CH2 placement.** I kept the specified placement: CH2 at the folding nodes, which also chops the sink flicker; the sinks' flicker share in-band is ≈ 0. It caused one problem, which I fixed with the pair cascodes instead of moving CH2.
- **Problem:** the f1/f2 voltages jump by Δ(s5 − s6) ∝ vout/(gm·ro) at every CH2 swap. The jump couples through M1/M2 C_gd into the gates, and CH1 delivers it to ninv/nnon. This is a switched-capacitor feedback path from vout to the input.
- **Effect** (netlist prototype, L56 = 1 µm, no cascode): f_HP 14.9 Hz, gain 36.4 dB, output DC 1.27 V.
- **Fixes:** M5/M6 at 4 µm brought f_HP to 5.6 Hz. Cascoding the input pair (MC1/MC2) brought it to **0.22 Hz**.

Alternative placements would swap the x1/vout nodes, which switches the mirror diode, or chop the drains of the pair only. The first creates an SC resistor directly on the high-Z output. The second leaves the same Cgd path. Neither is better.

**Load-mirror (M7/M8) flicker share:** **27.7 %** of the in-band noise with CH3 frozen (> 15 %), so CH3 was added.

| CH3 | Vni 0.5–200 Hz | M7/M8 share (flicker) | Vni_total |
|---|---|---|---|
| off (o3/o4 static) | 3.515 µV | 29.6 % (27.7 %) | 12.67 µV |
| **on** | **2.989 µV** | 2.7 % (0.0 %) | 11.30 µV |

`lna_chop` is a copy of lna_cci with ota_fc_chop, plus reset TGs RS1 (vfb–ninv) and RS2 (nnon–vref) on rst/rstb, and **6** pseudo-R elements per path (Step 4). `lna_chop_pr10` has 10. `lna_chop_os` uses ota_fc_chop_os.

`tb_lna_chop` (benches):

| bench | cell | purpose |
|---|---|---|
| I1 | lna_chop | PSS/PAC/Pnoise/PSTB, T1/T2, Zin |
| I2 | lna_chop | T3 (50 Hz common mode); its CM source has pacmag 1, giving CMRR from PAC |
| I4 | lna_chop | overload step + reset |
| I5 | lna_chop_os | ripple/offset |
| I6 | lna_chop_pr10 | 10-element pseudo-R comparison |

Each bench has its own VDD/IREF/CL, and the clocks are shared.

---------------------------------------------------------------------------------------------------------
## 3. Input-pair re-optimisation under chopping (Step 3)

f_chop = 5 kHz, 200 nA per device, pair cascodes + CH1/CH2/CH3 on, 6-element pseudo-R. Pnoise is timeaverage, maxsideband 30; Vni is referred with the PAC gain. Cp = cgg(M1) from the static op. `plots/3_pair_sweep_psd.png`.

| pair (total W / L) | Cp | penalty | gm/ID | gain | f_HP | f_LP | **Vni 0.5–200 Hz** | Vni_tot | NEF | CH1-switch share |
|---|---|---|---|---|---|---|---|---|---|---|
| 500u / 4u (Phase 2 pair) | 4.507 pF | 1.235 | 27.8 | 38.24 dB | 0.733 Hz | 3918 Hz | 151.2 µV | 152.1 µV | 69.4 | 21.7 % |
| 500u / 2u | 2.431 pF | 1.132 | 28.8 | 39.05 dB | 0.501 Hz | 3993 Hz | 77.4 µV | 92.8 µV | 42.0 | 27.4 % |
| 500u / 1u | 1.386 pF | 1.079 | 29.5 | 39.44 dB | 0.379 Hz | 4082 Hz | 48.1 µV | 65.2 µV | 29.2 | 27.0 % |
| 100u / 1u (extension) | 0.279 pF | 1.024 | 27.4 | 39.85 dB | 0.238 Hz | 3789 Hz | 10.9 µV | 19.7 µV | 9.1 | 30.0 % |
| 40u / 1u (extension) | 0.115 pF | 1.016 | 26.0 | 39.92 dB | 0.225 Hz | 3567 Hz | 5.28 µV | 12.7 µV | 6.1 | 34.3 % |
| 20u / 1u (extension) | 0.061 pF | 1.013 | 25.0 | 39.94 dB | 0.221 Hz | 3386 Hz | 3.62 µV | 11.5 µV | 5.6 | 39.0 % |
| **10u / 1u (chosen)** | **0.034 pF** | **1.012** | 24.5 | **39.95 dB** | **0.219 Hz** | **3222 Hz** | **2.99 µV** | 11.3 µV | 5.7 | 42.6 % |

**Hypothesis ("with flicker chopped away, the shorter device wins"): confirmed, much more strongly than expected, but not for the reason expected.**
- The Cp noise penalty only changes by 1.235 → 1.079.
- What dominates is the low-frequency excess created by chopping the gate capacitance itself. The in-band excess above the white floor scales with Cp and with f_chop: ≈ 33 µV per pF at 5 kHz, plus ≈ 38 fF of switch/junction parasitics. See C in the journal.

So the best pair is the smallest one that still has gm/ID ≈ 24 and f_LP ≥ 3 kHz: **10 × 1u/1u**. Going smaller fails f_LP: gm drops and f_LP falls with it. I extended the sweep beyond the specified W = 500 µm because the W = 500 µm points are 16–50× off the spec.

---------------------------------------------------------------------------------------------------------
## 4. Reset switch and pseudo-R count (Step 4)

**Reset** (`plots/4_reset_recovery.png`). Bench 4: 50 mV differential step at 0.2 s, then a 1 ms RST pulse (TG 0.8u/0.18u across each pseudo-R chain) at 0.21 s, f_chop = 5 kHz.
- **Recovery:** within ±10 mV of VREF (one-period average) **10.1 ms after the step**. The output recovers at the RST edge, so this is set by the 10 ms wait, not by the circuit.
- **Offset step on RST release (charge injection):** 0.9027 → 0.9050 V = **+2.38 mV**.

**6 vs 10 pseudo-R elements per path** (the same schematic run, benches I1/I6):

| | **6 elements (chosen)** | 10 elements |
|---|---|---|
| f_HP 27 °C (PAC) | 0.219 Hz | 0.135 Hz |
| f_HP 37 °C (PAC) | **0.403 Hz** | 0.285 Hz |
| Vni 0.5–200 Hz | **2.989 µV** | 3.625 µV |
| pseudo-R share of in-band noise | 12.3 % | 5.0 % |
| CH1-switch share | 42.6 % | 64.8 % |
| natural recovery (no reset, clocks frozen; `plots/4_natural_recovery.png`) | **4.89 s** | 7.69 s |

**Choice: 6 elements.** Counter-intuitively, the 10-element chain is noisier with chopping. A larger DC resistance lets more of the CH1 switched-capacitor noise current integrate on the input node: its share goes from 43 % to 65 %. That outweighs the lower pseudo-R noise. Six elements still meet f_HP < 0.5 Hz at 37 °C (margin 0.1 Hz, as in Phase 2) and recover faster. Reset makes the 10-element recovery penalty irrelevant, but not the noise penalty.

---------------------------------------------------------------------------------------------------------
## 5. PAC Bode and stability (Steps 5a/5b/5d)

**PSS:** fund = FCH = 5 kHz, harms 20 (output only; shooting uses the full waveform), tstab = 5/FCH, errpreset conservative. It converged on the TΩ nodes without any pseudo-R substitution. The linear-resistor fallback was **not** needed for the nominal circuit; see A17 for the mismatch case that does not converge.

**PAC:** 0.1 Hz–100 kHz, 20/dec, sweeptype absolute, maxsideband 10, output sideband 0. `plots/5_pac_bode.png` overlays the Phase 2 AC.

| | Phase 2 (AC) | **Phase 3 (PAC sb 0)** |
|---|---|---|
| midband gain | 39.94 dB | **39.95 dB** |
| f_HP 27 / 37 °C | 0.240 / 0.390 Hz | **0.219 / 0.403 Hz** |
| f_LP (CL 2 pF) | 3201 Hz | **3222 Hz** (37 °C: 3087 Hz) |
| CMRR @ 50 Hz (nominal) | 97.0 dB | 96.5 dB |

**Stability:**
- **Spectre PSTB** (probe I1.IPRB, sideband 0): **PM 89.5° at 3180 Hz**, loop gain at 10 Hz 47.6 dB (`plots/5_pstb.png`).
- **PSTB gain margin:** it reports "GM = 0 dB @ 501 kHz". That point is far above f_chop/2, where the sideband-0 loop gain of a 5 kHz periodic linearisation is not meaningful (folding), so I don't use it.
- **Static-switch stb** (STAT = 1, same netlist) for the GM: **PM 89.3° @ 3182 Hz, GM 58.8 dB @ 987 kHz**.

---------------------------------------------------------------------------------------------------------
## 6. Pnoise (Step 5c)

Pnoise settings: (vout1 0), timeaverage (sources), maxsideband 30, 0.1 Hz–100 kHz, 20/dec, absolute; also a 1–10 kHz linear run around f_chop. The PSD is referred to the input with the sideband-0 PAC gain.
- `plots/6_psd_overlay.png`: input-referred PSD on the same axes as Phase 2.
- `plots/6_outnoise_fchop.png`: output noise around f_chop, where the up-converted flicker now sits as a narrow peak at 5 kHz (≈ 650 nV/√Hz input-referred).

| | Phase 2 | **Phase 3** |
|---|---|---|
| Vni 0.5–200 Hz | 2.465 µV | **2.989 µV** |
| Vni_total (out, 0.1 Hz–100 kHz / G) | 7.869 µV | 11.296 µV |
| white floor (300 Hz–1 kHz) | 108 nV/√Hz | 105 nV/√Hz |
| 1/f corner (PSD = √2 × floor) | 35.5 Hz | **14.1 Hz** |
| at 1 Hz | 1018 nV/√Hz | 1836 nV/√Hz |
| at 4 Hz (crossover) | 409 nV/√Hz | 415 nV/√Hz |
| at 10 Hz | 253 nV/√Hz | **188 nV/√Hz** |
| at 100 Hz | 124 nV/√Hz | **106 nV/√Hz** |

**NEF / PEF (same convention as Phase 2):** Itot = I(VDD1) = 549.9 nA (incl. IREF; the PSS average is the same), BW = f_LP − f_HP = 3221.4 Hz.

NEF = 1.130e-5 · √(2·549.9e-9 / (π·0.0259·1.657e-20·3221.4)) = **5.69** (excl. IREF 5.55). PEF = NEF²·VDD = **58.2**.

Contributors (input-referred, % of the output noise PSD):

| @ 1 Hz | | @ 1 kHz | |
|---|---|---|---|
| CH1 switches (kT/C-type switched-cap noise) | 1371 nV/√Hz, 55.7 % | M1 + M2 thermal | 55 + 55 nV/√Hz, 55.4 % |
| pseudo-R chains | 741 nV/√Hz, 16.3 % | M3 + M4 sinks thermal | 36 + 36 nV/√Hz, 23.8 % |
| M1 + M2 thermal | 494 + 494 nV/√Hz, 14.4 % | M1 + M2 flicker (residual at f) | 27 + 27 nV/√Hz, 13.0 % |
| M3 + M4 thermal | 323 + 323 nV/√Hz, 6.2 % | M7 + M8 thermal | 18 + 18 nV/√Hz, 6.0 % |
| M1 + M2 flicker | 221 + 221 nV/√Hz, 2.8 % | | |

In-band (0.5–200 Hz) shares: CH1 switches 42.6 %, M1 + M2 29.8 %, pseudo-R 12.3 %, sinks 10.6 %, loads 2.6 %, cascodes 1.2 %.

**What is left:** thermal noise of the pair and sinks (≈ 1.48 µV in-band), the pseudo-R (≈ 1.05 µV), and the switched-capacitor excess at the input nodes (≈ 1.95 µV). The 1/f of the pair, sinks and loads is gone. The "CH1 switches" entry is the noise of the switched-capacitor path from swapping Cp.

---------------------------------------------------------------------------------------------------------
## 7. Ripple and offset (Steps 5e/5f)

**Ripple:** 0.5 mV in series with the M1 gate (lna_chop_os, bench 5). Values are from the PSS steady state; a 1 s transient at 5 kHz agrees.

| f_chop | **ripple at vout (p-p)** | output DC | Phase 2 LNA, same 0.5 mV |
|---|---|---|---|
| 5 kHz | **77.3 mVpp** | 0.9127 V | no ripple, DC shift +0.500 mV |
| 10 kHz | 46.8 mVpp | 0.9252 V | — |
| 20 kHz | 24.4 mVpp | 0.9524 V | — |

`plots/7_ripple_vs_fchop.png` (one period) and `7_ripple_tran_5k.png` (transient). The offset itself adds < 0.4 mV of DC. The DC level shifts with f_chop because of the charge-injection pump below.

**Residual offset from charge injection** (output DC wrt VREF; input sources at VCM):

| case | 5 kHz |
|---|---|
| nominal switches (PSS; 4 s transient agrees: 12.28 mV) | **+12.3 mV** (10 kHz: +25.2 mV; 20 kHz: +52.4 mV) |
| CH1A nmos 10 % wider (WS1A = 0.88u), 4 s transient, settled | **+730 mV, output saturated at 1.630 V** (ninv − nnon = −315 µV) |

PSS did not converge for the mismatched case (the circuit has no linear operating region; A17). The transient was run for 4 s, ≈ 5.5 pseudo-R time constants, and was flat over its last 2 s.

---------------------------------------------------------------------------------------------------------
## 8. Transients, input impedance, power (Steps 5g/5h/5i)

**Transients:** f_chop = 5 kHz, maxstep = T_chop/20 = 10 µs, strobe = T_chop/40 = 5 µs, errpreset moderate.
- The pulse breakpoints force time steps at every clock edge (5 ns rise), so maxstep only has to resolve the triangular ripple (≥ 20 points per period).
- The strobe is uniform for the FFT, which uses the 0.5–1 s window: 5 cycles of 10 Hz, 2 Hz bins, harmonics 2–10.

| test | result |
|---|---|
| T1 (1 mV 10 Hz + 300 mV on vin+) | gain 39.97 dB, output DC 0.910 V, THD **0.153 %** (`8_T1.png`) |
| T2, THD at 1 / 3 / 5 / 8 mV | 0.153 / 0.073 / **0.057** / 4.15 % (`8_T2.png`) |
| T3 (100 mV 50 Hz CM + 100 µV 10 Hz) | 50 Hz residual **140 µV** at the output (CM gain −57.1 dB); 10 Hz signal 10.13 mV (`8_T3.png`) |

The 0.15 % at 1 mV is an amplitude-independent ≈ 150 µV component in the harmonic bins. It comes from the slow output-DC settling (τ ≈ 0.7 s) still under way in the 0.5–1 s window, not from nonlinearity: THD falls as the amplitude rises.

**Input impedance at 50 Hz** (PAC current of VIP1, differential ±0.5 V drive): **80.0 MΩ** (Phase 2: 80.2 MΩ), i.e. the Cin-limited value. Chopping inside the OTA did **not** lower Zin. A CCIA with the chopper in front of Cin would give 1/(4·f_chop·Cin) = 2.5 MΩ at 5 kHz.

**Power:**
- **Analog:** I(VDD1) = **549.9 nA incl. ideal IREF (524.9 nA excluding it)**, 0.99 µW. The PSS average equals the static value; the switch junction currents are negligible.
- **Switch drive (estimate):** per LNA, 24 switches of 0.8u/0.18u (C_g ≈ W·L·Cox + 2·Cov·W = 1.21 + 0.48 = 1.7 fF) and 8 dummies of 0.4u (0.85 fF) give C = 47.6 fF. P = C·V²·f_chop = 47.6 fF·3.24 V²·5 kHz = **0.77 nW** (1.5 nW at 10 kHz, 3.1 nW at 20 kHz). That is less than 0.1 % of the analog power, excluding the clock generator and non-overlap logic, which are not designed. The ideal clock sources' simulated average v·i is ≈ 0, as expected for purely reactive loads.

---------------------------------------------------------------------------------------------------------
## 9. Headline comparison: Phase 2 LNA vs Phase 3 LNA

| | Phase 2 (`lna_cci`) | Phase 3 (`lna_chop`, f_chop 5 kHz) |
|---|---|---|
| Vni 0.5–200 Hz | **2.465 µV** | 2.989 µV |
| 1/f corner | 35.5 Hz | **14.1 Hz** |
| NEF | **3.97** | 5.69 |
| PEF | **28.4** | 58.2 |
| Itot (analog, incl. / excl. IREF) | 549.9 / 524.9 nA | 549.9 / 524.9 nA (+ 0.77 nW clocks) |
| f_HP 27 / 37 °C | 0.240 / 0.390 Hz | 0.219 / 0.403 Hz |
| f_LP (2 pF) | 3201 Hz | 3222 Hz |
| THD @ 5 mV | 6.2 % | **0.057 %** (non-chopped lna_v2: 0.093 %) |
| output offset (nominal) | **≈ 0 mV** (+0.5 mV per 0.5 mV pair offset) | 12.3 mV; saturates with a 10 % switch mismatch |
| ripple @ f_chop (0.5 mV offset) | **none** | 77.3 mVpp |
| recovery (50 mV step) | 6.70 s (natural) | **10.1 ms with reset** (natural 4.89 s) |
| Zin @ 50 Hz | 80.2 MΩ | 80.0 MΩ |
| MIM area | 40 275 µm² (2 × 141.2² + 2 × 13.9²) | 40 275 µm² |

---------------------------------------------------------------------------------------------------------
## 10. Summary table

| spec | target | achieved | pass/fail |
|---|---|---|---|
| gain | 40 dB ± 0.5 | 39.95 dB (PAC) | **pass** |
| f_HP @ 37 °C | < 0.5 Hz | 0.403 Hz | **pass** |
| f_LP | ≥ 3 kHz | 3222 Hz | **pass** |
| Vni 0.5–200 Hz | < 2 µVrms | 2.989 µVrms | **FAIL** |
| NEF | < 3.5 | 5.69 | **FAIL** |
| Itot (analog) | ≤ 550 nA | 524.9 nA excl. ideal IREF (549.9 incl.) | **pass** |
| THD @ 5 mV | < 1 % | 0.057 % | **pass** |
| ripple @ 0.5 mV offset | < 10 mVpp | 77.3 mVpp (5 kHz); 24.4 mVpp even at 20 kHz | **FAIL** |
| output offset | < 10 mV | 12.3 mV nominal; rails with a 10 % CH1 switch mismatch | **FAIL** |
| recovery with reset | < 50 ms | 10.1 ms | **pass** |

---------------------------------------------------------------------------------------------------------
## 11. Problems, deviations and what they mean

**1. Root cause of the noise and offset failures.** The specified architecture puts CH1 between Cin and the input-pair gates. The nodes CH1 switches (ninv/nnon) are high-impedance: their only DC path is the 5 TΩ pseudo-R. Two consequences:
- **Noise.** Swapping the gate (and switch) capacitance C_s between ninv and nnon each half period behaves like a resistor R_SC ≈ 1/(2·f_chop·C_s) across the OTA input. Below f ≈ 1/(2π·R_SC·Ctot), the OTA's white noise and the switches' kT/C noise see a noise gain rising as 1/f. The sweeps confirm the scaling:
  - **with f_chop:** the excess over the 1.82 µV thermal + pseudo-R level is 2.37 / 4.61 / 9.24 µV at 5 / 10 / 20 kHz;
  - **with C_s:** about 33 µV per pF of Cp, plus about 38 fF of switch parasitics.
- **Offset.** Any charge-injection imbalance is a femtoamp DC current into the same TΩ node. 0.056 fA × 5 TΩ ≈ 0.3 V by hand; the simulation gives 0.73 V, which saturates. Even the nominal, symmetric layout gives 12 mV.

The Phase 2 unchopped LNA has neither problem. These are properties of chopping at a virtual-ground node that has no low-impedance DC path, not of this particular sizing. The fixes are a DC servo / low-impedance DC path at ninv/nnon, or chopping before Cin with an impedance-boosting loop and a DC-servo loop. They are discussed in the journal (D).

**2. Deviations from the spec:**
- **Input-pair cascodes MC1/MC2 and M5/M6 = 0.4u/4u** were added to ota_fc_chop. Without them, CH2 kickback through C_gd gives f_HP = 5–15 Hz.
- **CH3 (load-mirror chopper)** was added, as the spec allows (share > 15 %).
- **f_chop = 5 kHz** instead of the 10 kHz baseline. Noise ∝ f_chop. 10 and 20 kHz were also run.
- **Pair W = 10 µm** (outside the specified W = 500 µm sweep, which was also run).
- **Pseudo-R count:** 6 elements (kept from Phase 2) rather than 10.
- **Output DC** is VREF + 12 mV, set by charge pumping, not by VREF.

**3. Tools:**
- **PSS:** worked for every nominal case. It does not converge for the 10 %-mismatch case, which has no in-range steady state, so that case used a transient.
- **PSTB:** GM above f_chop/2 is not meaningful, so GM comes from static-switch stb.
- **Pnoise maxsideband 30** folds noise up to 150 kHz. The switch kT/C bandwidth (Ron ≈ 5–10 kΩ with ≈ 50–100 fF) is a few hundred MHz, so the kT/C part of the CH1 switch noise may be **under**-estimated. Treat 2.99 µV as optimistic. A transient-noise cross-check was not run.
- **Virtuoso GUI:** the session crashed when I deleted an open cell (`lna_chop_pr6`). The cells were regenerated with a standalone `virtuoso -nograph`, and the PNGs were exported with Virtuoso under xvfb-run. Panic files were written only for cellviews still open from earlier phases, all of which had been saved; nothing was lost.

**4. Not done:** Monte Carlo (the mismatch result shows it is essential), process corners, supply variation, layout parasitics, a real clock generator, and a transient-noise check of the Pnoise result.

**5. Saved ADE Explorer (maestro) setups:**
- **`AFE_lib/tb_lna_chop/maestro`**, read back from SKILL, with four tests:
  - CHOP_PSS_PAC_PNOISE (pss fund = FCH, harms 20, tstab 5/FCH, conservative; pac 0.1–100k absolute, maxsideband 10; pnoise /vout1, timeaverage, maxsideband 30);
  - CHOP_PSTB (pss + pstb probe /I1/IPRB);
  - STATIC_STB (STAT = 1);
  - CHOP_TRAN (1 s, maxstep 10 µs).
- **`AFE_lib/tb_lna_v2/maestro`**, test V2_T2.
- The Phase 2 setups `tb_lna/maestro` and `tb_pseudo_r/maestro` are unchanged.

None of them were run from the GUI. Sweeps (WINF/LIN, FCH, CH3EN, WS1A, temperature) need to be added as parametric sets.

## Design Journal
Phase 3 challenges, trade-offs, hand calculations, critic's view and rebuild recipe: `../DESIGN_JOURNAL.md` (A12–A18, B7–B11, C Phase 3 table, D16–D24, E10).
