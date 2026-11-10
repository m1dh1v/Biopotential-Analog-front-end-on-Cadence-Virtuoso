# Low-power biopotential AFE in Cadence Virtuoso (gpdk180)

ECG/EEG recording channel in 180 nm CMOS, under 1 µW. I'm building it phase by phase, sizing everything with gm/ID
and checking every number against hand calcs. The project was inspired by my Analog circuits assignment where we had to simulate and analysi single stage OTA and I was making a digital stethoscope parallaly so I thought if I could design a better AFE for it, I might make something on par with industry. And since all I know right now is theory of OTA, implementation and other components of AFE are a challange and I am actively learning theory as well as simulation from few TAs, internet and AI. 

Tools: Cadence Virtuoso + Spectre, gpdk180 (BSIM3v3), Python for post-processing. Dataset from web and hopefully will use the data that I acquire myself from something I design

Phasewise Division
| 1 | gm/ID characterization + weak-inversion folded-cascode OTA
| 2 | Capacitively-coupled LNA (CCIA) + pseudo-resistors
| 3 | Chopper-stabilized LNA
| 4–7 | Gm-C filter, PGA, full chain PVT/Monte Carlo, layout (I plan to do it later in winters)

Each phase folder has its own report, plots, netlists and scripts. Big raw simulation data is not tracked.
