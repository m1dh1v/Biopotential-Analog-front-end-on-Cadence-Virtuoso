# Biopotential AFE — Phase 1 report (gpdk180, Spectre 21.1)

All numbers are from Spectre simulations. Final OTA results (§3–§7) come from the **schematic netlist** of
`AFE_lib/tb_ota` (netlisted by OCEAN `createNetlist`, run with `net/final.scs`). Plots are in `plots/`.

Library `AFE_lib` = `/home/ISDL_UG_86/Work_1/Biopot_afe/AFE_lib` (DEFINEd in `~/Desktop/cmos65/cds.lib`, tech gpdk180).
Cells: `tb_gmid`, `nmos_u5`, `pmos_u2`, `ota_fc`, `ota_fc_dcop` (annotated copy, not simulated), `tb_ota`.

## 1. PDK report (Step 0)
| Item | Value |
|---|---|
| PDK | Cadence Generic PDK **gpdk180** (180 nm), `/cad/FOUNDRY/analog/180nm`, Spectre models `gpdk.scs` sections NN/SS/SF/FS/FF/stat — **NN used** |
| VDD | **1.8 V** (core) |
| Core MOS | cells `nmos`/`pmos` (4-terminal; `nmos3`/`pmos3` 3-terminal) → models `nmos1`/`pmos1`, BSIM3v3 (`version 3.1`), noimod=2, tox(N)=4.0 nm |
| L range | **Lmin = 0.18 µm**; Lmax = 20 µm per device (model bins); W per device ≤ 100 µm (bins 0.4–10 µm and 10–100 µm) |
| |Vth| (model `vth`, |VDS|=0.9 V, VSB=0) | NMOS 0.56 V @Lmin, 0.49 V @1 µm, 0.45 V @4 µm; PMOS 0.53 V @Lmin, 0.46 V @1 µm, 0.43 V @4 µm |
| Capacitors | `mimcap`: cj = 1e-3 F/m² = **1.0 fF/µm²** (+ cjsw 0.1 fF/µm perimeter); also `nmoscap`/`pmoscap` (MOS caps) |
| Thick oxide | **Yes**: `nmoshv`/`pmoshv` (models `nmos25`/`pmos25`, tox ≈ 5.5/5.75 nm, 2.5 V-class) |
| Other | poly/nplus/pplus/nwell/metal resistors, npn/pnp/vpnp, diodes, varactors, inductor |

## 2. gm/ID characterization (Step 1) — `AFE_lib/tb_gmid`
W = 10 µm, L ∈ {0.18, 0.5, 1, 2, 4} µm, |VDS| = 0.9 V, VSB = 0, VGS 0→1.8 V step 5 mV (points with ID < 1 pA dropped).
Plots: `1a_gmid_vs_idw.png`, `1b_gain_vs_gmid.png`, `1c_ft_vs_gmid.png` (fT = gm/(2π·cgg)), `1d_idw_vs_vgs.png`.
CSV: `plots/gmid_lut.csv` (type, L, VGS, ID/W, gm/ID, gm/gds, fT); extended `gmid_lut_ext.csv` (+vth, vdsat, region, cgg/W).
Extra (for sizing): L = 8, 12, 20 µm (`raw/gmid_long`).

| L | NMOS max gm/ID | NMOS n | PMOS max gm/ID | PMOS n |
|---|---|---|---|---|
| 0.18 µm | 28.6 | 1.35 (80.6 mV/dec) | 30.2 | 1.28 (76.2 mV/dec) |
| 0.5 µm | 30.2 | 1.28 | 30.9 | 1.25 |
| 1 µm | 31.1 | 1.24 (73.9 mV/dec) | 31.8 | 1.22 (72.5 mV/dec) |
| 2 µm | 31.5 | 1.23 | 31.9 | 1.21 |
| 4 µm | 31.6 | 1.22 | 31.8 | 1.21 |

n = 1/(Ut·max(gm/ID)), Ut = 25.86 mV (27 °C).

**Flicker comparison** (W/L = 20u/2u, ID = 100 nA, |VDS| = 0.9 V; VGS(N) = 0.2767 V, VSG(P) = 0.3448 V). Plot `1e_flicker_nmos_pmos.png`.

| | gm | S_vg @1 Hz | @10 Hz | @1 kHz | 1/f corner | white floor |
|---|---|---|---|---|---|---|
| NMOS | 2.67 µS | 3.47e-12 V²/Hz (1.86 µV/√Hz) | 4.59e-13 (677 nV/√Hz) | 1.23e-14 (111 nV/√Hz) | **1.85 kHz** | 66 nV/√Hz |
| PMOS | 2.45 µS | 2.82e-12 V²/Hz (1.68 µV/√Hz) | 2.49e-13 (499 nV/√Hz) | 7.82e-15 (88 nV/√Hz) | **324 Hz** | 76 nV/√Hz |

Note: PMOS 1/f is only ~1.2× lower than NMOS at 1 Hz (model ef: PMOS 1.064 vs NMOS 0.883), ~2.5× lower at 1 kHz.

## 3. Folded-cascode OTA (Step 2) — `AFE_lib/ota_fc`
Schematic: `plots/2_ota_fc_schematic.png`. PMOS input pair (body tied to source/tail), NMOS folding sinks, NMOS cascodes,
wide-swing PMOS cascode mirror load (M7/M8 gates on x1 = drain of M9), single-ended out.

**Composite unit devices** (needed because gm/ID 6–8 at 50–300 nA requires W/L ≈ 0.004–0.03; W ≥ 0.4 µm and L ≤ 20 µm per model bin):
- `nmos_u5` = 5 series × nmos 0.4u/20u (L_eff 100 µm), 50 nA unit: composite gm/ID 5.98, Vdsat,eff 0.242 V, gm/gds 3934
- `pmos_u2` = 2 series × pmos 1u/20u (L_eff 40 µm), 50 nA unit: composite gm/ID 6.74, Vdsat,eff 0.215 V, gm/gds 2259
  (characterized in `comp_char.py`; mirror ratios are exact unit counts)

**Sizing calculation (LUT → simulation)**

| device | ID | W_total | L | ID/W [A/m] | LUT gm/ID | LUT gm/gds | sim gm/ID |
|---|---|---|---|---|---|---|---|
| M1/M2 input | 200 nA | 500 µm (10×50u) | 4 µm | 4.0e-4 | 27.4 | 963 | 27.8 |
| M5/M6 NMOS casc | 100 nA | 0.4 µm (min W) | 1 µm | 0.25 | 20.5 | 286 | 19.8 |
| M9/M10 PMOS casc | 100 nA | 0.6 µm | 1 µm | 0.167 | 17.4 | 275 | 17.2 |
| M7/M8 PMOS load | 100 nA | 2×0.5 µm | 20 µm | 0.10 | 6.9 | 1339 | 6.8 |
| M3/M4 sinks | 300 nA | 6×nmos_u5 | 5×20 µm | — | 5.98 (composite) | 3934 | — |
| M0 tail / MBP | 400 / 50 nA | 8× / 1× pmos_u2 | 2×20 µm | — | 6.74 (composite) | 2259 | — |

**Final sizing table** (DC op from schematic sim; composites: stack |VDS| vs Vdsat,eff)

| device | W | L | m | ID | gm/ID | region | Vds−Vdsat |
|---|---|---|---|---|---|---|---|
| MBP (bias diode) | 1u | 2×20u (pmos_u2) | 1 | 50 nA | 6.7 | sat (stack) | 0.47 V |
| M0 (tail) | 1u | 2×20u (pmos_u2) | 8 | 400 nA | 6.7 | sat (stack) | 0.42 V |
| M1, M2 (input) | 50u | 4u | 10 | 200 nA | 27.8 | subthreshold (VSD 0.70 V ≫ 4Ut) | 0.66 V |
| M3, M4 (fold sinks) | 0.4u | 5×20u (nmos_u5) | 6 | 300 nA | 6.0 | sat (stack) | 0.23 V |
| MBN (bias diode) | 0.4u | 5×20u (nmos_u5) | 1 | 50 nA | 6.0 | sat (stack) | 0.49 V |
| M5, M6 (NMOS casc) | 0.4u | 1u | 1 | 100 nA | 19.8 | subthreshold (sat) | 0.57 / 0.36 V |
| M7, M8 (PMOS load) | 0.5u | 20u | 2 | 100 nA | 6.8 | sat | 0.19 V |
| M9, M10 (PMOS casc) | 0.6u | 1u | 1 | 100 nA | 17.2 | sat | 0.16 / 0.38 V |

Input pair W·L = 2000 µm² per device. **Bias values (ideal, Phase-1):** IREF = 50 nA into MBP and MBN diodes
(×2 ideal current sources), VCN = 1.00 V, VCP = 0.75 V, VCM = 0.9 V, VDD = 1.8 V.
Op nodes: tail 1.169, f1/f2 0.471/0.470, x1 1.113, p1/p2 1.366/1.365, nbn 0.732, nbp 1.110, vout 0.900 V.

## 4. DC-op annotated schematic (3a)
`plots/3a_ota_fc_dcop.png` (cell `ota_fc_dcop`: copy of ota_fc + labels generated from the Spectre op point).
All devices saturated; M1/M2/M5/M6 in subthreshold (region 3) with Vds ≫ 4Ut. Lower segments of the series
stacks are in triode by construction (normal for composite devices); the stack as a whole is saturated.

## 5. AC and stability (3b, 3c)
Plots: `3b_ac_bode.png`, `3c_stb_loopgain.png`.

| CL | DC gain | −3 dB | GBW (open-loop UGF) | phase @UGF | stb loop gain T0 | **PM** | GM | stb crossover |
|---|---|---|---|---|---|---|---|---|
| 1 pF | 102.9 dB | 6.27 Hz | 437 kHz | −150.5° | 102.9 dB | **54.4°** | 16.2 dB | 211 kHz |
| 2 pF | 102.9 dB | 3.14 Hz | 302 kHz | −139.1° | 102.9 dB | **59.7°** | 18.2 dB | 173 kHz |
| 5 pF | 102.9 dB | 1.26 Hz | 158 kHz | −118.7° | 102.9 dB | **69.5°** | 22.3 dB | 111 kHz |

Open-loop AC has the inverting input AC-grounded; the buffer stb additionally sees the large M2 gate capacitance
on the output, so its crossover is lower and PM higher than the open-loop "phase @UGF" suggests.

**Stability iteration (before → after):** with the first sizing (PMOS load = 2× pmos_u2, Icasc = Itail/4)
PM @5 pF = **59.8°** (fail). Limiting non-dominant pole = **mirror node x1 ≈ 211 kHz** (C ≈ 0.74 pF from the large
composite load gates, g ≈ 1 µS); fold nodes f1/f2 ≈ 1.1 MHz (0.67 pF); tail ≈ 250 kHz (CM only).
Options tried (netlist level, CL = 1/2/5 pF):
- Icasc = Itail/2 (200 nA): PM 55.5/58.0/63.7°, Itot 899 nA
- Icasc = 150 nA: PM 53.3/56.1/62.4°, Itot 799 nA
- **Adopted:** keep Icasc = Itail/4, load = 2× single pmos 0.5u/20u (x1 cap ÷ ~4): PM 54.4/59.7/**69.5°**, Itot 700 nA,
  noise 1.80 → 1.88 µVrms, A0 103.7 → 102.9 dB.

## 6. Noise (3d)
Plot `3d_noise.png`. Open-loop bench, input-referred (iprobe = VIP1), 0.1 Hz–100 kHz.

| quantity | value |
|---|---|
| Vni, 0.5–200 Hz | **1.877 µVrms** |
| Vni, 300 Hz–5 kHz | **5.899 µVrms** |
| in @1 Hz / 1 kHz / 10 kHz | 631 / 86.7 / 85.3 nV/√Hz |
| 1/f corner (flicker part = thermal part) | **44 Hz** |
| Itot = I(VDD1) | **699.5 nA** (incl. 2×50 nA ideal reference currents) |

Top contributors (input-referred) @1 Hz: M1 flicker 37.1 %, M2 flicker 37.1 %, M7 flicker 9.9 %, M8 flicker 9.9 %, M3 flicker 2.1 %.
@1 kHz: M1 thermal 34.6 %, M2 thermal 34.6 %, M3 thermal 10.5 %, M4 thermal 10.5 %, M7 thermal 3.1 %.

**NEF (0.5–200 Hz):** NEF = Vni·√(2·Itot / (π·Ut·4kT·BW))
= 1.877e-6 · √(2·6.995e-7 / (π·0.0259·1.6568e-20·199.5))
= 1.877e-6 · √(5.202e12) = 1.877e-6 · 2.281e6 = **4.28**

## 7. Extras (3e)
- Output swing (inverting gain −10, R1 = 1 GΩ, R2 = 10 GΩ, DC sweep; `3e_swing.png`): max |gain| = 9.997;
  Vout range with gain ≥ −3 dB of max: **0.273–1.599 V (1.33 Vpp)**; within 1 % gain error: 0.476–1.409 V.
- @10 Hz: Adm = 84.8 dB, Acm = −54.7 dB, Avdd = −22.7 dB → **CMRR = 139.6 dB, PSRR(VDD) = 107.6 dB**
  (nominal, no mismatch — not realistic; Monte-Carlo needed). `3e_cmrr_psrr.png`.

## 8. Summary
| Spec | Target | Achieved | Pass/Fail |
|---|---|---|---|
| DC gain | > 60 dB | 102.9 dB | PASS |
| PM @ 5 pF (stb) | > 60° | 69.5° | PASS (after fix; 59.8° before) |
| GM @ 5 pF | > 10 dB | 22.3 dB | PASS |
| Vni 0.5–200 Hz | < 2 µVrms | 1.877 µVrms | PASS (6 % margin) |
| NEF (0.5–200 Hz) | < 3 | 4.28 | **FAIL** |
| Itot | ~0.5 µA | 0.700 µA (0.600 core + 0.100 ref) | **FAIL / deviation** |
| CMRR @10 Hz | (report) | 139.6 dB (nominal) | n/a (no mismatch) |
| PSRR @10 Hz | (report) | 107.6 dB (nominal) | n/a (no mismatch) |
| Output swing | (report) | 0.27–1.60 V (−3 dB), 0.48–1.41 V (1 %) | — |
| PM @1 pF / 2 pF | (not specified) | 54.4° / 59.7° | below 60° |

## 9. Problems, assumptions, deviations
1. **Itot spec is inconsistent with the sizing rules**: Itail 400 nA + 2×Itail/4 cascode = 600 nA core before any bias.
   Measured 699.5 nA includes the two ideal 50 nA reference branches.
2. **NEF < 3 not met (4.28)**. Even the thermal floor alone (86 nV/√Hz → 1.22 µVrms in 199.5 Hz) gives NEF ≈ 2.8 at
   0.7 µA; flicker of the input pair (74 % at 1 Hz) and M7/M8 adds the rest. Closing it needs chopping, or less
   current in non-input branches, or more input area (input C already large).
3. **Input-pair capacitance is large** (2 × 500u/4u, WL = 2000 µm² each, Cox ≈ 8.6 fF/µm²) — important for the
   capacitive-coupled AFE in Phase 2 (gain-loss / noise from Cin divider).
4. **Composite (series-stacked) devices** used for sinks, tail and bias diodes because gm/ID 6–8 at 50–300 nA is
   impossible with W ≥ 0.4 µm and L ≤ 20 µm. Their gm/ID / Vdsat,eff are from a separate unit characterization.
5. **L/C open-loop trick deviates from spec values**: with L = 1 GH the inductor (jωL = 6.3 MΩ at 1 mHz) loads the
   ~GΩ output and shows a false 31 dB "DC gain". Used L = C = 1e16 H/F instead (gain flat to 1 mHz, verified).
6. **Gain-of-10 swing bench**: 1M/10M resistors load the OTA (gain only 8.3); used 1G/10G.
7. **CMRR/PSRR are nominal** (perfectly matched devices) — will drop to mismatch-limited values in Monte Carlo.
8. Spectre `pz` analysis was unreliable here (huge L/C), so non-dominant poles were found by injecting AC test
   currents into each internal node (`node_poles.py`).
9. An earlier netlist-level stb result (PM 61.6°) was wrong (a second OTA shared the bias diodes, halving currents);
   discarded — the schematic-level 59.8° was the true "before" value.
10. Body of input pair tied to its source (tail) — VSB = 0 for M1/M2; all other NMOS bodies at vss, PMOS at vdd.
11. Temperature 27 °C, NN corner only; no corners / Monte Carlo yet. All bias sources ideal (Phase 2 replaces them).
12. Schematic nets use wire stubs with net labels (one gnd symbol in tb_ota, net `gnd!`).

## Files
- Scripts: `step1_gmid.py`, `step1_flicker.py`, `size_ota.py`, `comp_char.py`, `ota_design.py`, `iter_ol.py`,
  `iter_stb.py`, `node_poles.py`, `final_tb.py`, `final_results.py`, `make_dcop_labels.py`, `psf.py`, `runsim.py`
- SKILL: `skill/afe_util.il`, `skill/tb_gmid.il`, `skill/ota_cells.il`, `skill/tb_ota.il`, `skill/dcop.il`
- Raw PSF: `raw/`; netlists: `net/`

## Design Journal
See `../DESIGN_JOURNAL.md` (challenges, trade-offs, hand-calc vs sim, critic view, rebuild recipe).
