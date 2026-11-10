# Low-power biopotential AFE in Cadence Virtuoso (gpdk180)

A sub-microwatt ECG/EEG recording channel in 180 nm CMOS, designed from scratch with the gm/ID method and checked
against hand calculations at every step.

This started from my analog circuits assignment, where we had to simulate and analyse a single-stage OTA. I was
building a digital stethoscope in parallel and thought: what if I designed a better AFE for it? All I knew going in was
OTA theory, so the rest (LNA, pseudo-resistors, noise, chopping) is something I'm learning as I go, from a few TAs, the
internet and AI tools. The AI agent helps with schematic/testbench automation and simulation runs; I set the targets,
check results against hand calcs, and I'm rebuilding the core blocks by hand in ADE to own the details.

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

What I learned the hard way (full story in the Phase 2 folder):
- Noise is flicker-limited: about 48 % MOS flicker, 36 % MOS thermal, 16 % pseudo-resistor of the in-band noise power. That's exactly what chopping targets.
- The input pair has an optimum size: more gate area cuts flicker but adds capacitance that multiplies noise by (Cin + Cf + Cp)/Cin = 1.235.
- Long pseudo-resistor devices bypass themselves with their own gate capacitance. I found that by swapping in an ideal resistor.
- Output clips at about 0.63 V on the low side, so THD rises quickly above 3 mV input.
- Overload recovery takes 6.7 s, and f_HP moves from 0.08 Hz to 11 Hz across 0–80 °C.

### Honest limits right now
Typical corner only, no Monte Carlo yet, ideal bias reference, no layout. CMRR is optimistic since only capacitor mismatch is modelled.

## Roadmap
| Phase | What | Status |
|---|---|---|
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
