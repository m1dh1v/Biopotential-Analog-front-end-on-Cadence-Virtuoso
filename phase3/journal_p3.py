"""Insert the Phase-3 additions into DESIGN_JOURNAL.md (sections A, B, C, D, E)."""
import os
J = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "DESIGN_JOURNAL.md")
s = open(J, encoding="utf-8").read()
SEP = "---------------------------------------------------------------------------------------------------------\n"

A = r"""
### A12. VCN could not be lowered by resizing MC (Phase 3)
- **Symptom:** Phase 2 clipped low at ≈ 0.63 V (THD 6.2 % at 5 mV).
- **How it showed:** the Phase 2 op: f1/f2 = 0.572 V, M6 Vds − Vdsat = 0.27 V, but vout_min = f2 + Vdsat(M6) ≈ 0.63 V.
- **Root cause:** VCN = V(nbn) + Vgs(MC) = 0.632 + 0.458 V. Even an infinitely wide MC keeps Vgs ≈ Vth(body) ≈ 0.35 V, so VCN ≥ 0.98 V.
  I also tried tying VCN to VCP (zero current). It fails because p2 − f2 = Vgs(M6) + Vsg(M10) ≈ 1.08 V leaves less than 1.0 V of swing.
- **Fix:** a separate ≈ 3 nA VCN branch (MPV1–8, 8 pmos_u2 in series; MCN1/MCN2 0.4u/10u diodes): VCN = 0.756 V, f1 = 0.302 V.
  M7/M8 widened to 2u/20u (Vdsat 0.243 → 0.129 V) and the MCP bulk tied to its source (VCP 0.746 → 0.920 V) for the high side.
- **Cost:** +2.95 nA (526.6 nA excl. IREF); sink-stack margin only +85 mV (stack Vdsat 0.217 V at 98 % current).

### A13. Femtoamp switch leakage moved the TΩ input nodes by volts (Phase 3)
- **Symptom:** the first chopped PSS had ninv = nnon = 0.015 V instead of 0.9 V.
- **How it showed:** DC op with static clocks; saving ibd/ibs of the CH1 switches showed ≈ 7–12 pA per junction.
- **Root cause:** the switch lines had no ad/as/pd/ps. Spectre's default junction is then far larger (11.7 pA vs 0.07 fA with real
  geometry, measured on one 0.8u device). The NMOS/PMOS leakage imbalance flowed through the 5 TΩ chain.
- **Fix:** junction geometry on every device (the schematic gpdk cells get it from A_mos/A_mosv).
- **Residual cost:** even with geometry, ≈ 18 fA of net leakage shifts ninv/nnon to 0.99–1.07 V (a common-mode shift only).
  This is the first sign that anything attached to these nodes is amplified by 5 TΩ.

### A14. CH2 kickback made f_HP 15 Hz and cost 3.6 dB of gain (Phase 3)
- **Symptom:** first PAC: gain 36.4 dB, f_HP 14.9 Hz; PSS output DC 1.27 V; Pnoise in-band ≈ 1 mV.
- **How it showed:** PAC, then a 0.25 s transient (gain 31.3 dB at 10 Hz; output DC settled in 50 ms, far faster than the pseudo-R
  τ, so the DC path was not the pseudo-R). The static-clock run (STAT = 1) was perfect (39.94 dB, 0.21 Hz), so the problem was
  in the switching.
- **Root cause (two switched-capacitor paths):**
  1. At every CH2 swap, f1/f2 jump by Δ(s5 − s6) ∝ vout/(gm·ro). The jump couples through M1/M2 C_gd onto the gates, and CH1
     carries that charge to ninv/nnon. That is a switched-capacitor resistor from vout to the input, ≈ 60 GΩ, in parallel with Cf → f_HP.
  2. CH1 swaps the gate capacitance between ninv and nnon: R_SC ≈ 1/(2·f_chop·C_s) of tens of MΩ across the OTA input. That lowers
     the feedback factor at low frequency (gain error) and creates a noise gain rising as 1/f (A16).
- **Fix for (1):** M5/M6 at 4 µm brought f_HP to 5.6 Hz; **PMOS cascodes on the input-pair drains** (MC1/MC2, gate = vcm1, no extra
  current) brought it to 0.22 Hz. Path (2) is intrinsic, so I could only shrink it (A15).
- **Cost:** 2 × 200 µm × 1 µm cascode devices; ≈ 0.4 V of pair headroom (the pair Vsd is still 0.47 V).

### A15. The specified W = 500 µm pair is 16–50× off the noise spec when chopped (Phase 3)
- **Symptom:** the Step 3 sweep at W = 500 µm gave Vni 48–151 µV.
- **How it showed:** Pnoise with PAC referral; contributors at 1 Hz were the post-CH2 devices and the CH1 switches, i.e. noise
  multiplied by the low-frequency noise gain, not flicker.
- **Root cause:** A14 (2). The excess scales with C_s × f_chop: ≈ 33 µV per pF at 5 kHz, plus ≈ 38 fF of switch parasitics.
- **Fix:** smallest pair with gm/ID ≥ 24 and f_LP ≥ 3 kHz → 10 × 1u/1u (Cp 34 fF), and f_chop = 5 kHz.
- **Cost:** a tiny pair. Offset σ ≈ several mV (chopped, so it shows up as ripple); large flicker up-converted to f_chop
  (a 650 nV/√Hz peak); f_LP margin only 7 %.

### A16. Pseudo-R count: 10 elements is noisier when chopped (Phase 3)
- **Symptom:** with the same pair, the 10-element chain gave 3.63 µV vs 2.99 µV for 6.
- **How it showed:** the same schematic run with benches I1 (6 elements) and I6 (10 elements); the CH1-switch share is 65 % vs 43 %.
- **Root cause:** the switched-capacitor noise current integrates on ninv until the pseudo-R removes it. A larger R lets more of it
  reach the output below f_HP·(R/R_SC)…, so the larger R hurts more than its own lower noise helps.
- **Fix:** keep 6 elements; reset handles recovery.
- **Cost:** f_HP at 37 °C is 0.403 Hz (0.1 Hz margin), and the pseudo-R share is 12 %.

### A17. 10 % CH1 switch mismatch saturates the output; PSS cannot converge (Phase 3)
- **Symptom:** PSS with WS1A = 0.88 µm failed in three configurations (gear2only, steadyratio 0.01, tstab 40 periods; the
  log showed Vgd > 12 V, a numerical runaway).
- **How it showed:** a 4 s transient, ≈ 5.5 τ: vout settled at 1.630 V (+730 mV, saturated), ninv − nnon = −315 µV.
  The nominal case gives +12.3 mV, which matches PSS.
- **Root cause:** charge-injection imbalance is a DC current pump into the TΩ node (Δq·f ≈ 0.06 fA). The only DC sink is the
  5 TΩ pseudo-R, so the output must move by ≈ I·R ≈ 0.3–0.7 V. The offset also scales with f_chop (12 / 25 / 52 mV at 5/10/20 kHz).
- **Fix (not implemented, design change):** a low-impedance DC path at ninv/nnon, e.g. a DC-servo loop that integrates the
  output and injects current there. Alternatively, chop before Cin as in the classic CCIA.
- **Cost of not fixing:** the chopped LNA is not manufacturable as it stands; Pelgrom mismatch of 0.8u/0.18u switches is several %.

### A18. Virtuoso GUI crash while regenerating cells (Phase 3)
- Deleting `lna_chop_pr6` while it was open (the testbench referenced it) crashed the GUI session (Qt stack in CDS.log).
- **Fix:** continued with the MCP standalone `virtuoso -nograph` for SKILL/netlisting, and exported PNGs from a Virtuoso run
  under `xvfb-run` (`sim/afe/xexport.sh` + `p3_export.il`). Panic files exist only for earlier, saved cellviews.
- Also: the local result fetchers died with the shell, so I pulled the PSF data with tar/scp; I fixed two Python heredoc
  `"\n"` escaping slips in the runner.
"""

B = r"""
### B7. f_chop choice (Phase 3)
| f_chop | Vni 0.5–200 Hz | LF excess (above 1.82 µV) | ripple (0.5 mV) | nominal output offset | switch drive |
|---|---|---|---|---|---|
| **5 kHz** | **2.99 µV** | 2.37 µV | 77.3 mVpp | 12.3 mV | 0.77 nW |
| 10 kHz | 4.96 µV | 4.61 µV | 46.8 mVpp | 25.2 mV | 1.5 nW |
| 20 kHz | 9.42 µV | 9.24 µV | 24.4 mVpp | 52.4 mV | 3.1 nW |

- The noise excess and the offset are proportional to f_chop; the ripple goes as 1/f_chop. No f_chop meets both the ripple and noise targets.
- f_chop must also stay above f_LP (3.2 kHz) so the signal band and the up-converted flicker don't overlap.
- I chose 5 kHz to optimise the primary spec (noise). Ripple would need a ripple-reduction loop or a post-filter at any f_chop.

### B8. CH2 placement (Phase 3)
- **At f1/f2 (chosen, as specified):** chops the pair and sink flicker (sink flicker in-band ≈ 0 %). Creates the C_gd kickback path (A14),
  fixed with the pair cascodes: f_HP 5.6 → 0.22 Hz, gain 36.3 → 39.95 dB.
- **At the cascode drains (x1/vout):** would switch the mirror diode and put a switched-capacitor resistor directly on the high-Z output.
  Rejected by analysis (output impedance).
- **At the pair drains only (sinks unchopped):** same kickback, and sink flicker unchopped (sinks were 10 % of in-band noise in Phase 2). Rejected.

### B9. Overlap vs non-overlap (Phase 3)
- **CH1 non-overlap (35 ns gap):** an overlap would short vip to vin, i.e. ninv to nnon, through two switches each cycle. That is an
  extra Ron path in parallel with R_SC, adding charge sharing between the TΩ nodes. With break-before-make the gates float for
  35 ns, with negligible droop (τ_leak ≫ 35 ns).
- **CH2/CH3 overlap (35 ns):** the folding current (≈ 250 nA) must always have a path. In a 35 ns non-overlap, f1/f2 (≈ 0.3 pF incl.
  the cascode drain) would slew by 250 nA·35 ns/0.3 pF ≈ 29 mV, giving a larger kick per edge (A14). With overlap the f nodes are
  briefly shorted together, which only averages the two currents. Cost: a 35 ns/100 µs = 0.07 % gain error.

### B10. Pseudo-R count 6 vs 10 (Phase 3)
See the Step 4 table in PHASE3_REPORT §4.

| | 6 elements | 10 elements |
|---|---|---|
| f_HP 27 / 37 °C | 0.219 / 0.403 Hz | 0.135 / 0.285 Hz |
| Vni | **2.99 µV** | 3.63 µV |
| pseudo-R share | 12.3 % | 5.0 % |
| natural recovery | **4.89 s** | 7.69 s |
| with reset | 10.1 ms | 10.1 ms |

The 10-element chain only wins on f_HP margin (37 °C: 0.285 vs 0.403 Hz) and at 80 °C. Chosen: 6, for the noise (A16).

### B11. Input-pair size under chopping (Phase 3)
- In-band excess ≈ k·(Cp + 38 fF)·f_chop with k ≈ 33 µV/(pF·5 kHz), so the trade is no longer flicker vs penalty: it is Cp vs gm and f_LP.
- **W = 500 µm (any L):** 48–151 µV.
- **W = 10–20 µm:** 3.0–3.6 µV.
- **Below 10 µm:** gm/ID < 24 and f_LP < 3 kHz.

Mismatch grows as 1/√(WL) (σVos ≈ 1.5 mV at 10 µm²); it becomes ripple, not DC error. Its up-converted flicker sits at
f_chop (650 nV/√Hz input-referred peak), outside the band but inside the Vni_total integral (11.3 µV, so NEF 5.7).
"""

C = r"""
**Phase 3 (chopped LNA):**

| quantity | hand estimate (formula → number) | simulated | error |
|---|---|---|---|
| ripple @ 5 kHz (0.5 mV) | triangle: Vpp = gm·Vos·(T/2)/C_eff, C_eff = gm·β/(2π·f_LP) → Vpp = Vos·π·f_LP/(β·f_chop), β = 0.2/20.23 = 9.9e-3 → **102 mV** | 77.3 mVpp | +32 % |
| ripple @ 10 kHz | same → **51.2 mV** | 46.8 mVpp | +9 % |
| ripple @ 20 kHz | same → **25.6 mV** | 24.4 mVpp | +5 % |
| charge-injection offset, 10 % CH1A mismatch | q_ch = W·L·Cox·Vov = 0.8·0.18 µm²·8.6 fF/µm²·0.18 V = 0.22 fC; Δq ≈ 0.1·q/2 = 0.011 fC; I = Δq·f = 0.056 fA; ΔV = I·R(0) = 0.056 fA·5.2 TΩ → **0.29 V** | +0.718 V (saturated) | −60 % |
| expected Vni after chopping (Phase 2 minus flicker) | thermal floor 105 nV·√199.5 = 1.48 µV ⊕ pseudo-R 1.05 µV → **1.82 µV** | 2.99 µV | −39 % |
| LF excess per pF swapped (5 kHz) | noise-gain model: v_n·f_chop·C_s/(π·Cin)·√2 = 105 nV·5 kHz/(π·20 pF)·1.41 → **11.8 µV/pF** | ≈ 33 µV/pF (fit over the W/L sweep) | −64 % |
| f_HP 27 °C (6 elements) | 1/(2π·6·8.67e11·0.2 pF) → **0.153 Hz** | 0.219 Hz | −30 % |
| switch-drive power | C·V²·f = 47.6 fF·3.24·5 kHz → **0.77 nW** | ≈ 0 (ideal sources, reactive) | — |

**Explaining the gaps:**
- **Ripple at 5 kHz:** f_chop is only 1.55× f_LP, so the loop still partly tracks the square wave and the triangle (integrator)
  model overestimates. At 10–20 kHz the model is within 10 %.
- **Charge injection:** the turn-on/turn-off charge split is not 50/50 (one side is a 20 pF node, the other 34 fF + switch caps),
  and the pseudo-R at 0.7 V bias is far below R(0), so a larger pumped current is needed for the same ΔV. The hand calculation only
  shows that the order of magnitude is "volts", which is the important conclusion.
- **Expected vs simulated noise:** the gap of 2.37 µV is the switched-capacitor excess (A14/A15), which "Phase 2 minus flicker" does not include.
- **Switched-capacitor coefficient:** the effective swapped charge includes C_gd Miller charge (the d-node moves with the swap), the cascode
  C_gs on d1/d2 and the switch kT/C noise itself (the CH1 switches are the top contributor). The simple model counts only the
  noise gain of the OTA's white noise.
"""

D = r"""
**Phase 3 additions:**
16. **The chopped LNA is worse than the unchopped one in the spec band** (2.99 vs 2.47 µV; NEF 5.7 vs 4.0). Chopping inside the OTA,
    behind Cin, at a node whose only DC path is TΩ is the wrong place. The data show the flicker benefit (PSD lower above 4 Hz, 1/f corner 14 Hz)
    is lost to the switched-capacitor excess below 4 Hz.
17. **Offset robustness is the real killer:** 10 % mismatch on one switch rails the output. Monte Carlo would fail nearly every sample.
    A DC-servo (low-Z DC path at ninv/nnon) is mandatory for any chopper here.
18. **Ripple 77 mVpp** at 0.5 mV offset; the realistic σVos of the 10 µm² pair is ≈ 1.5 mV, which gives ≈ 230 mVpp, over half the swing.
    A ripple-reduction loop (or an output chopper + LPF, i.e. an SC/LPF back end) is required.
19. **Pnoise accuracy:** maxsideband 30 covers ±150 kHz; the switch kT/C bandwidth is hundreds of MHz, so folded switch noise is likely
    underestimated. A transient-noise run should confirm. The 2.99 µV is probably optimistic.
20. **The tiny pair** (10 × 1u/1u) has poor matching, high up-converted flicker (NEF counts it: Vni_total 11.3 µV) and only 7 % f_LP
    margin; with CL = 5 pF f_LP fails.
21. **f_HP at 37 °C = 0.403 Hz** (0.1 Hz margin), and still 0.08–11 Hz over 0–80 °C (pseudo-R unchanged).
22. **Bias:** the VCN branch is 3 nA through 16 series 20 µm PMOS (very slow start-up, leakage-sensitive at 80 °C); there is still no
    start-up circuit. The sink-stack margin is 85 mV; the SS corner will likely push the sinks out of saturation.
23. **Reset** works (10 ms), but the 2.4 mV release step depends on matching of the RS switches; it was not checked with mismatch.
24. **Recommended path:** keep `lna_v2` (Phase 2 + swing fix: 2.45 µV, THD 0.09 %) as the baseline. For chopping, move to a CCIA
    with the input chopper before Cin, a DC-servo loop (for electrode offset) and a positive-feedback impedance-boosting loop
    (Zin would otherwise be 1/(4·f_chop·Cin) = 2.5 MΩ at 5 kHz).
"""

E = r"""
### E10. Phase 3 recipe
**Variables (tb_lna_chop):** VDD 1.8, VCM 0.9, VREF 0.9, IREF 25n, CL 2p, LIN 1u, WINF 1u, WS1A 0.8u (mismatch 0.88u), VOS 0 (T1/T2 0.3),
AMP 0 (T1 1m; T2 1m/3m/5m/8m), FSIG 10, VCMA 0 (T3 0.1), VDA 0 (T3 100u), VSTEP 0 (50m), VSTEP6 0, TSTEP 10m (0.2), TRD 10m,
TRW 1m, RSTEN 0 (1), VOSI 0 (0.5m), FCH 5k (10k, 20k), TNO 30n, TOV 30n, TR 5n, STAT 0 (1 = static), CH3EN 1, WCIN 141.22u,
LCIN1 141.22u, WCF 13.943u. **tb_lna_v2:** as tb_lna (Phase 2) with LIN 4u.
Options: reltol 1e-5, vabstol 1e-8, iabstol 1e-15, gmin 1e-15, temp 27 (37 by alter).

**`bias_gen_v2`** (pins vdd, vss, iref, nbp, vcp, vcn, vcm1):

| inst | cell | size | D | G | S | B |
|---|---|---|---|---|---|---|
| MBN | nmos_u5 | unit | iref | iref | vss | vss |
| MBS | nmos_u5 | unit | vcp | iref | vss | vss |
| MCP | pmos | 20u/1u | vcp | vcp | nbp | nbp |
| MBP | pmos_u2 | unit | nbp | nbp | vdd | vdd |
| MPV1…MPV8 | pmos_u2 | unit, series | mpv1…mpv7, vcn | nbp | vdd, mpv1…mpv7 | vdd |
| MCN1 | nmos | 0.4u/10u | vcn | vcn | vcm1 | vss |
| MCN2 | nmos | 0.4u/10u | vcm1 | vcm1 | vss | vss |

**`ota_fc_lna_v2`**: as ota_fc_lna, but with these changes:
- M3/M4 gate on iref;
- M5/M6 gate vcn, 0.4u/1u;
- M7/M8 pmos 2u/20u;
- XB = bias_gen_v2 (nbp, vcp, vcn, vcm1 local nets).

**`lna_v2`**: lna_cci with ota_fc_lna_v2 (6 pseudo-R per path).

**`ota_fc_chop`** (pins vdd, vss, vip, vin, iref, vout, c1, c1b, c2, c2b, o1, o1b, o2, o2b, o3, o3b, o4, o4b):

| inst | cell | W / L / m | D | G | S | B |
|---|---|---|---|---|---|---|
| M0<0:15> | pmos_u2 | unit × 16 | tail | nbp | vdd | vdd |
| M1 / M2 | pmos | WINF / LIN / 10 | d1 / d2 | g1 / g2 | tail | tail |
| MC1 / MC2 | pmos | 50u / 1u / 4 | f1 / f2 | vcm1 | d1 / d2 | d1 / d2 |
| M3<0:9> / M4<0:9> | nmos_u5 | unit × 10 | f1 / f2 | iref | vss | vss |
| M5 / M6 | nmos | 0.4u / 4u | x1 / vout | vcn | s5 / s6 | vss |
| M7 / M8 | pmos | 2u / 20u | p1 / p2 | x1 | vdd | vdd |
| M9 / M10 | pmos | 0.6u / 1u | x1 / vout | vcp | q9 / q10 | vdd |
| XB | bias_gen_v2 | | | | | |

**Transmission gates** `TG(a, b, cn, cp)` = nmos 0.8u/0.18u (D a, G cn, S b, B vss) + pmos 0.8u/0.18u (D a, G cp, S b, B vdd).
Dummies on node d: nmos 0.4u/0.18u (D = S = d, G cp, B vss) and pmos 0.4u/0.18u (D = S = d, G cn, B vdd). All have ad = as = 0.6 µm·w, pd = ps = 2w + 1.2 µm.
- **CH1:** A = TG(vip, g1, c1, c1b) (nmos w = WS1A) + dummies on g1; B = TG(vin, g2, c1, c1b) + dummies on g2;
  C = TG(vip, g2, c2, c2b) + dummies on g2; D = TG(vin, g1, c2, c2b) + dummies on g1.
- **CH2:** TG(f1, s5, o1, o1b), TG(f2, s6, o1, o1b), TG(f1, s6, o2, o2b), TG(f2, s5, o2, o2b).
- **CH3:** TG(p1, q9, o3, o3b), TG(p2, q10, o3, o3b), TG(p1, q10, o4, o4b), TG(p2, q9, o4, o4b).

**`ota_fc_chop_os`:** the same, with M1 gate = g1x and VOSI vdc (+ g1x, − g1, vdc = VOSI).

**`lna_chop`** (pins vdd, vss, vinp, vinn, vref, iref, vout, 12 clocks, rst, rstb):
- lna_cci structure, with 6 pseudo_r per path and I0 = ota_fc_chop (clocks through);
- RS1 = TG(vfb, ninv, rst, rstb) and RS2 = TG(nnon, vref, rst, rstb), no dummies.

**`lna_chop_pr10`:** 10 pseudo-R per path. **`lna_chop_os`:** uses ota_fc_chop_os.

**`tb_lna_chop`:**
- **Clocks:** vpulse (0/VDD), period 1/FCH, tr = tf = TR.

| clock | v1 → v2 | td | pw |
|---|---|---|---|
| c1 | VDD → VDD·STAT | T/2 − TNO − TR | T/2 + TNO |
| c2 | 0 → VDD·(1 − STAT) | T/2 | T/2 − TNO − 2TR |
| o1 | VDD → VDD·STAT | T/2 + TR + TOV | T/2 − 2TR − TOV |
| o2 | 0 → VDD·(1 − STAT) | T/2 | T/2 + TOV |
| o3 / o4 | as o1 / o2 with STAT → max(STAT, 1 − CH3EN) | | |

  Complements (·b) swap v1/v2. Phase 1 is active at t = 0, so the DC point is the static phase-1 circuit.
- **Benches** (each with its own vdc VDDk, idc IREFk (vdd k → iref k), cap CLk):
  - I1 lna_chop: VIP1/VIN1 vsin (VCM+VOS / VCM, va AMP/2, FSIG, pacm 0.5 / 0.5∠180).
  - I2: VC2 vsin 50 Hz VCMA (pacm 1) + VDP2/VDN2 10 Hz VDA/2.
  - I4: VP4/VN4 vpulse VCM ± VSTEP/2 at TSTEP; VRST4/VRSTB4 vpulse 0 → VDD·RSTEN (inverted) at TSTEP + TRD, width TRW.
  - I5 lna_chop_os: VIP5/VIN5 vdc VCM.
  - I6 lna_chop_pr10: VP6/VN6 vpulse (VSTEP6, pacm ±0.5).

  rst = gnd and rstb = vdd k on the benches without reset. Check the netlist: pacmag only on VIP1, VIN1, VC2, VP6, VN6; no `mag`.

**Analyses (`phase3/p3_sims.py`, netlists `phase3/net/*.scs`):**
- **PSS:** `pss1 pss fund=FCH harms=20 tstab=5/FCH errpreset=conservative`. The mismatch case does not converge, so it uses a 4 s transient instead.
- **PAC:** `pac1 pac start=0.1 stop=100k dec=20 sweeptype=absolute maxsideband=10`; output = sideband 0 (`pac1.0.pac`).
- **Pnoise:** `pn1 (vout1 0) pnoise start=0.1 stop=100k dec=20 sweeptype=absolute maxsideband=30 noisetype=timeaverage` (same for vout6);
  around f_chop: `pnfc (vout1 0) pnoise start=FCH*0.2 stop=FCH*2 lin=360 ...`.
- **PSTB:** `pstb1 pstb start=0.1 stop=1M dec=20 probe=I1.IPRB` (GM from the static stb, STAT = 1). 37 °C: `alter temp=37` + pss/pac.
- **Transient:** `tran stop=1 maxstep=1/(20·FCH) strobeperiod=1/(40·FCH) errpreset=moderate`; T2 = sweep AMP; 10/20 kHz runs 0.3 s.
- **Natural recovery:** STAT = 1, tran 40 s, maxstep 2 ms. **Offset:** PSS (nominal) and 4 s tran (mismatch), maxstep 10 µs, strobe 20 µs.
- **Step 3:** PSS/PAC/Pnoise per (WINF, LIN); Cp = cgg(M1) from a STAT = 1 op with alter WINF/LIN.

**Extraction:**
- Gain/f_HP/f_LP from |PAC sb 0| (−3 dB crossings). Input PSD = |pnoise out| / |PAC sb 0|.
- Vni(0.5–200) = √∫PSD²; Vni_tot = √∫out²(0.1 Hz–100 kHz)/G; NEF and PEF as in Phase 2 with Itot = I(VDD1) and BW = f_LP − f_HP.
- Contributors = Pnoise per-instance totals (flicker = 'fn' column), grouped (composites summed; CH1A–D incl. dummies = "CH1 switches").
- Ripple = max − min of vout5 over one PSS period. Offset = mean(vout1) − VREF.
- Recovery = last time the one-period moving average of vout4 is outside ±10 mV of VREF, minus the step time.
- Zin = 0.5 V/|I(VIP1)| (PAC sb 0) at 50 Hz. THD = FFT over 0.5–1 s (uniform resample at T/40), harmonics 2–10.
- Clock gap/overlap = 50 % crossing differences in the PSS waveform.

**Maestro:** `AFE_lib/tb_lna_chop/maestro` (CHOP_PSS_PAC_PNOISE, CHOP_PSTB, STATIC_STB, CHOP_TRAN), `AFE_lib/tb_lna_v2/maestro` (V2_T2).

**PNG export:** `ssh … sim/afe/xexport.sh sim/afe/p3_export.il` (Virtuoso under xvfb-run, hiExportImage 3000×2000, entireDesign).
"""

# insert
iB = s.index(SEP + "## B. Trade-offs"); s = s[:iB] + A.lstrip("\n") + "\n" + s[iB:]
iC = s.index(SEP + "## C. Hand calculation"); s = s[:iC] + B.lstrip("\n") + "\n" + s[iC:]
iD = s.index(SEP + "## D. Critic"); s = s[:iD] + C.lstrip("\n") + "\n" + s[iD:]
iE = s.index(SEP + "## E. Rebuild recipe"); s = s[:iE] + D.lstrip("\n") + "\n" + s[iE:]
s = s.rstrip("\n") + "\n\n" + E.lstrip("\n")
s = s.replace("Status: **Phase 1 and Phase 2 complete (2026-11-10).**", "Status: **Phases 1, 2 and 3 complete (2026-11-10).**")
s = s.replace("`AFE_lib/tb_ota`); Phase-2 numbers from `phase2/` (schematic netlists of `AFE_lib/tb_lna`, `tb_pseudo_r`), NN, 27 °C unless noted.",
              "`AFE_lib/tb_ota`); Phase-2 numbers from `phase2/` (schematic netlists of `AFE_lib/tb_lna`, `tb_pseudo_r`); Phase-3 numbers from\n"
              "`phase3/` (schematic netlists of `AFE_lib/tb_lna_v2`, `tb_lna_chop`), NN, 27 °C unless noted.")
open(J, "w", encoding="utf-8", newline="\n").write(s)
print("ok", s.count("### A1"), s.count("Phase 3"))
