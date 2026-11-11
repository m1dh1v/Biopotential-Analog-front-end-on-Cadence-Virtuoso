# Low-power biopotential AFE in Cadence Virtuoso (gpdk180)

A sub-microwatt ECG/EEG recording channel in 180 nm CMOS, designed from scratch with the gm/ID method and checked
against hand calculations at every step.

I thought of this project from my analog circuits assignment, where we had to simulate and analyse a single-stage OTA. I was
building a digital stethoscope in parallel and thought what if I designed a better AFE for it? All I knew going in was
OTA theory, so the rest (LNA, pseudo-resistors, noise, chopping) is something I'm learning as I go, from a few TAs, the
internet and AI tools. I plan to continue beyond phase 3 in winter vacations. For now I have used some ECG data available on web but hopefully in future, I will test the AFE with the data I acquire myself.

**Tools:** Cadence Virtuoso + Spectre, gpdk180 (BSIM3v3), Python for post-processing.
**Data:** public recordings from the web for now (PhysioNet-style); hopefully my own recordings from the stethoscope later.

## What I'm aiming for

One channel of an analog front end: electrodes → capacitively-coupled LNA → band-pass filter → PGA → ADC.

| Target | Value |
|---|---|
| Gain | 40 dB at the LNA |
| Band | high-pass < 0.5 Hz, low-pass ≥ 3 kHz (later narrowed by a Gm-C filter) |
| Input noise (0.5–200 Hz) | < 2 µVrms |
| NEF | < 3.5 |
| Current | ≤ 550 nA at 1.8 V (about 1 µW) |
| CMRR @ 50 Hz | > 80 dB |
| Stability | phase margin > 60° |
| Linearity | THD < 1 % at 1 mV |

Design choices that run through the whole project:
- **gm/ID sizing**: characterize the PDK once (gm/ID, ID/W, gm/gds, fT vs L), then size every device by its job. Input pair in weak inversion for noise efficiency, mirrors and sinks at low gm/ID for low noise current.
- **Capacitively-coupled LNA** (Harrison-style): gain from a capacitor ratio, electrode DC offset (±300 mV) blocked, high-pass corner from MOS pseudo-resistors.
- **Chopping** (Phase 3) to beat the flicker noise that limits the current design.

## What's done so far

### Phase 1: gm/ID characterization + folded-cascode OTA (done)
- gm/ID, ID/W, gm/gds, fT and flicker data for gpdk180 across L = 0.18–20 µm. Max gm/ID is about 29–32, so the slope factor n is 1.21–1.35.
- PMOS-input folded cascode, input pair at gm/ID 27.8 (weak inversion), sinks/mirrors at about 6–7 using series-stacked unit devices (needed because of the model's W/L limits).
- Results: **102.9 dB** gain, **PM 54 / 60 / 70°** at 1 / 2 / 5 pF, 700 nA, 1.88 µVrms input noise.
- Hand calcs match the sim (gain within 4 %). The PM problem was traced to one internal pole and fixed without extra power.

### Phase 2: capacitively-coupled LNA (done, pushed in two parts)
- Cin = 20 pF, Cf = 200 fF, pseudo-resistor feedback, OTA re-biased down to **550 nA** total (0.99 µW).
- Pseudo-resistor chain sized as 6 × (2 × 0.4u/4u) per path, which gives f_HP of 0.24 Hz at 27 °C and 0.39 Hz at 37 °C.

| Metric | Result | Spec |
|---|---|---|
| Gain | 39.94 dB | 40 dB, pass |
| f_HP / f_LP | 0.24 Hz / 3.2 kHz (2 pF load) | pass |
| Phase margin | 89° | > 60°, pass |
| Input noise 0.5–200 Hz | 2.47 µVrms | < 2 µV, **fail** |
| NEF | 3.97 | < 3.5, **fail** |
| CMRR @ 50 Hz (0.1 % Cin mismatch) | 92.7 dB | > 80 dB, pass |
| THD at 1 mV | 0.027 % | < 1 %, pass |

What I learned (details in the Phase 2 folder):
- Noise is flicker-limited: about 48 % MOS flicker, 36 % MOS thermal, 16 % pseudo-resistor of the in-band noise power. That's exactly what chopping targets.
- The input pair has an optimum size: more gate area cuts flicker but adds capacitance that multiplies noise by (Cin + Cf + Cp)/Cin = 1.235.
- Long pseudo-resistor devices bypass themselves with their own gate capacitance. I found that by swapping in an ideal resistor.
- Output clips at about 0.63 V on the low side, so THD rises quickly above 3 mV input.
- Overload recovery takes 6.7 s, and f_HP moves from 0.08 Hz to 11 Hz across 0–80 °C.

## Roadmap
Phase

| 1 | gm/ID characterization + weak-inversion folded-cascode OTA | done |

| 2 | Capacitively-coupled LNA (CCIA) + pseudo-resistors | done |

| 3 | Chopper-stabilized LNA (goal: in-band noise under 2 µV; NEF will need a smaller input pair too) | next |

| 4 | Tunable Gm-C low-pass filter | later |

| 5 | PGA | later |

| 6 | Full chain: PVT corners, Monte Carlo, real ECG/EEG playback | later |

| 7 | Layout (common-centroid input pair, guard rings), DRC/LVS | I plan to do it in winters |

## Repo layout
- `phase1/`: report, plots, netlists, SKILL scripts, gm/ID characterization data (`gmid_char/`)
- `phase2/`: LNA, bias and pseudo-resistor work (results, report and design journal arriving in the next commit)

Each phase folder has its own report, plots, netlists and scripts. Big raw simulation data is not tracked.

## Update: Phase 3 and Phase 4 results

(Added later; the sections above are as written when only Phases 1–2 were done.)

### Phase 3: output-swing fix + chopper (`phase3/`)
- **Swing fix worked:** a separate low-current VCN branch lowered the fold nodes from 0.57 V to 0.30 V. THD at 5 mV went from 6.2 % to 0.09 %.
- **Chopper did not beat the unchopped LNA:** chopping inside the OTA removed the flicker above about 4 Hz, but in-band noise got worse (2.99 µV vs 2.47 µV, NEF 5.7). Offset 12 mV, ripple 77 mVpp at 0.5 mV pair offset, and the output saturates with a 10 % switch mismatch.
- **Why:** the input chopper switches the gate capacitance on high-impedance nodes whose only DC path is the TΩ pseudo-resistor. That acts as a switched-capacitor resistor (noise rising as 1/f below a few Hz) and turns femtoamps of charge injection into volts. Details in `phase3/PHASE3_REPORT.md`.
- **Next for chopping (not done):** chop before Cin with a DC servo, impedance boosting and a ripple loop. `lna_v2` (Phase 2 + swing fix, 2.45 µV) is the baseline used afterwards.

### Phase 4: tunable Gm-C low-pass filter (`phase4/`)
2nd-order Butterworth OTA-C biquad from multi-tanh-doublet gm cells, placed after `lna_v2`.

| Metric | Result | Target |
|---|---|---|
| fc | 150.1 Hz, tunable 101 Hz–1 kHz with one bias current | 150 Hz, 100 Hz–1 kHz |
| Q (fit) | 0.735 | 0.707 |
| THD at 0.5 Vpp, fc/5 | 0.535 % | < 1 % |
| Output noise | 28.1 µVrms (0.28 µV at the LNA input) | < 30 µV |
| Current | 8.9 nA at 150 Hz | ≤ 100 nA |
| Caps | 36 pF each | ≤ 20 pF (not met, noise-driven) |

- Chain (LNA + filter): band 0.152 Hz – 150.5 Hz, input-referred noise 2.31 µV vs 2.30 µV for the LNA alone.
- Weak spots: THD 3.6 % at 0.8 Vpp, 1.65 % at 80 °C (fc drops 32 % there, cause not isolated), stopband floor at −41 dB above 4 kHz.

### Correction to the Phase 2 and 3 numbers
The LNA's high-pass corner was reported as 0.240 Hz (27 °C) and 0.390 Hz (37 °C). Re-running with tighter simulator tolerance (`iabstol` 1e-18 instead of 1e-15) gives **0.152 Hz and 0.277 Hz**. The old value was a simulator-tolerance artefact on the fA-level pseudo-resistor nodes, so the earlier f_HP numbers (and the "gate-capacitance bypass" explanation) overstated the effect. The spec still passes, with more margin. See `phase4/PHASE4_REPORT.md` §7 and journal entry A20. Temperature-sweep f_HP values from Phase 2 were also run at the loose tolerance and should be re-checked.

Layout of the repo: `phase1/` to `phase4/`, each with report, plots, netlists, scripts; `DESIGN_JOURNAL.md` collects challenges, trade-offs, hand calcs vs simulation and rebuild recipes for all phases.
