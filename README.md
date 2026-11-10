# Low-power biopotential AFE in Cadence Virtuoso (gpdk180)

ECG/EEG recording channel in 180 nm CMOS, under 1 µW. I'm building it phase by phase, sizing everything with gm/ID
and checking every number against hand calcs.

Tools: Cadence Virtuoso + Spectre, gpdk180 (BSIM3v3), Python for post-processing.

## Roadmap
| Phase | What | Status |
|---|---|---|
| 1 | gm/ID characterization + weak-inversion folded-cascode OTA | done |
| 2 | Capacitively-coupled LNA (CCIA) + pseudo-resistors | done (pushed in 2 parts) |
| 3 | Chopper-stabilized LNA | next |
| 4–7 | Gm-C filter, PGA, full chain PVT/Monte Carlo, layout | later |

Each phase folder has its own report, plots, netlists and scripts. Big raw simulation data is not tracked.
