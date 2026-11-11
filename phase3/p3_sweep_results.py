"""Step 3 (input-pair sweep under chopping), f_chop sweep and CH3 on/off from schematic PSS/PAC/Pnoise runs."""
import os, json, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import psf
from p2_metrics import bw, integ, UT_NEF, FOURKT
from contrib import table

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "plots")
CP = json.load(open(os.path.join(OUT, "cp_sweep.json")))


def pm(name):
    rd = os.path.join(HERE, "raw", name)
    p = psf.read(rd + "/pac1.0.pac"); f = p["freq"]; H = p["vout1"]; G, fhp, flp = bw(f, H)
    n = psf.read(rd + "/pn1.pnoise"); fn = n["freq"]; out = np.abs(n["out"])
    Hn = np.exp(np.interp(np.log(fn), np.log(f), np.log(np.abs(H)))); vin = out / Hn
    td = psf.read(rd + "/pss1.td.pss"); t = td["time"]
    I = float(np.trapezoid(-td["VDD1:p"], t) / (t[-1] - t[0]))
    vb = np.sqrt(integ(fn, vin ** 2, 0.5, 200)); vt = np.sqrt(integ(fn, out ** 2, 0.1, 1e5)) / 10 ** (G / 20)
    BW = flp - fhp; nef = vt * np.sqrt(2 * I / (np.pi * UT_NEF * FOURKT * BW))
    fl = np.median(vin[(fn > 300) & (fn < 1000)]); lo = np.where((vin > np.sqrt(2) * fl) & (fn < 300))[0]
    _, band, bandfl, totb = table(n, fn, out, Hn ** 2)
    sh = lambda *ks: 100 * sum(band.get(k, 0) for k in ks) / totb
    return dict(G=G, fhp=fhp, flp=flp, vni_band=vb, vni_tot=vt, I=I, NEF=nef, PEF=nef ** 2 * 1.8, floor=float(fl),
                corner=float(fn[lo[-1]]) if len(lo) else float("nan"), vout_dc=float(np.mean(td["vout1"])),
                sh_ch1=sh("CH1 switches"), sh_pair=sh("M1", "M2"), sh_pr=sh("pseudo-R chains"),
                sh_load=sh("M7", "M8"), sh_loadfl=100 * (bandfl.get("M7", 0) + bandfl.get("M8", 0)) / totb,
                fn=fn, vin=vin)


res = {}
rows = [("s3_W500_L4", "W500u_L4u", "W=500u L=4u (Phase 2 pair)"), ("s3_W500_L2", "W500u_L2u", "W=500u L=2u"),
        ("s3_W500_L1", "W500u_L1u", "W=500u L=1u"), ("s3_W100_L1", "W100u_L1u", "W=100u L=1u (ext.)"),
        ("s3_W40_L1", "W40u_L1u", "W=40u L=1u (ext.)"), ("s3_W20_L1", "W20u_L1u", "W=20u L=1u (ext.)"),
        ("p3_main", "W10u_L1u", "W=10u L=1u (chosen)")]
print("== Step 3: input-pair sweep under chopping (f_chop=5 kHz, 200 nA/device, pair cascodes, CH1-3 on, NPR=6)")
print("%-28s %8s %8s %9s %8s %8s %8s %9s %8s %7s %6s" % ("pair", "Cp[pF]", "penalty", "gm/ID", "G[dB]", "fHP", "fLP", "Vni[uV]", "tot[uV]", "NEF", "CH1%"))
fig, ax = plt.subplots(figsize=(8, 5))
for nm, key, lab in rows:
    if not os.path.exists(os.path.join(HERE, "raw", nm, "pn1.pnoise")):
        print("missing", nm); continue
    r = pm(nm); c = CP[key]; r["Cp"] = c["Cp"]; r["penalty"] = (20e-12 + 0.2e-12 + c["Cp"]) / 20e-12; r["gmid"] = c["gmid"]
    print("%-28s %8.3f %8.3f %9.1f %8.2f %8.3f %8.0f %9.3f %8.2f %7.2f %6.1f" % (
        lab, c["Cp"] * 1e12, r["penalty"], c["gmid"], r["G"], r["fhp"], r["flp"], r["vni_band"] * 1e6, r["vni_tot"] * 1e6, r["NEF"], r["sh_ch1"]))
    ax.loglog(r["fn"], r["vin"] * 1e9, label="%s: %.2f uV" % (lab, r["vni_band"] * 1e6))
    res["pair " + lab] = {k: v for k, v in r.items() if k not in ("fn", "vin")}
ax.set_xlabel("Hz"); ax.set_ylabel("input-referred [nV/rtHz]"); ax.grid(True, which="both", alpha=0.3); ax.legend(fontsize=7)
ax.set_xlim(0.1, 1e5); ax.set_title("Input-pair sweep under chopping (Pnoise, f_chop = 5 kHz)")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "3_pair_sweep_psd.png"), dpi=150); plt.close(fig)

print("\n== f_chop sweep (chosen pair W=10u L=1u)")
for nm, lab in [("p3_main", "5 kHz"), ("fch_10k", "10 kHz"), ("fch_20k", "20 kHz")]:
    if not os.path.exists(os.path.join(HERE, "raw", nm, "pn1.pnoise")):
        print("missing", nm); continue
    r = pm(nm); res["fchop " + lab] = {k: v for k, v in r.items() if k not in ("fn", "vin")}
    print("  f_chop=%-7s G=%.2f fHP=%.3f fLP=%.0f Vni=%.3f uV tot=%.2f uV NEF=%.2f I=%.1f nA vout_dc=%.4f CH1 %.1f%% pair %.1f%% PR %.1f%%" % (
        lab, r["G"], r["fhp"], r["flp"], r["vni_band"] * 1e6, r["vni_tot"] * 1e6, r["NEF"], r["I"] * 1e9, r["vout_dc"], r["sh_ch1"], r["sh_pair"], r["sh_pr"]))

print("\n== CH3 (load-mirror chopper) before/after")
for nm, lab in [("ch3off", "CH3 off (static)"), ("p3_main", "CH3 on")]:
    if not os.path.exists(os.path.join(HERE, "raw", nm, "pn1.pnoise")):
        print("missing", nm); continue
    r = pm(nm); res[lab] = {k: v for k, v in r.items() if k not in ("fn", "vin")}
    print("  %-18s Vni=%.3f uV tot=%.2f uV  M7/M8 share %.1f%% (flicker %.1f%%)  CH1 %.1f%%" % (
        lab, r["vni_band"] * 1e6, r["vni_tot"] * 1e6, r["sh_load"], r["sh_loadfl"], r["sh_ch1"]))
json.dump(res, open(os.path.join(OUT, "sweep_results.json"), "w"), indent=1, default=float)
