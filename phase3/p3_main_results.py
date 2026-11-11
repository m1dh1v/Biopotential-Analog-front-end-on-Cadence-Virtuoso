"""Phase-3 main results from the schematic tb_lna_chop PSS/PAC/Pnoise/PSTB run (+ Phase 2 overlay)."""
import os, sys, json, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import psf
from p2_metrics import bw, integ, UT_NEF, FOURKT
from contrib import table

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "plots")
name = sys.argv[1] if len(sys.argv) > 1 else "p3_main"
tag = sys.argv[2] if len(sys.argv) > 2 else ""
RD = os.path.join(HERE, "raw", name)
P2 = os.path.join(HERE, "..", "phase2", "raw", "p2_main")
res = {}


def pac(fn_, node):
    p = psf.read(os.path.join(RD, fn_)); return p["freq"], p[node]


# ---------------- PSS operating point / currents / clock power
td = psf.read(os.path.join(RD, "pss1.td.pss")); t = td["time"]
res["I_vdd1_pss"] = float(np.trapezoid(-td["VDD1:p"], t) / (t[-1] - t[0]))
pclk = 0.0
for k in td:
    if k.startswith("VK") and k.endswith(":p"):
        nd = k[2:-2]
        pclk += np.trapezoid(td[nd] * (-td[k]), t) / (t[-1] - t[0]) if nd in td else 0.0
res["P_clk_total"] = float(pclk)
res["vout1_dc"] = float(np.mean(td["vout1"])); res["vout6_dc"] = float(np.mean(td["vout6"]))
res["ninv_dc"] = float(np.mean(td["I1.ninv"])); res["nnon_dc"] = float(np.mean(td["I1.nnon"]))
print("PSS: <I(VDD1)> = %.1f nA, vout1 = %.4f V, vout6 = %.4f V, ninv=%.4f nnon=%.4f; clock sources avg power (all 5 LNAs) = %.3g W" % (
    res["I_vdd1_pss"] * 1e9, res["vout1_dc"], res["vout6_dc"], res["ninv_dc"], res["nnon_dc"], pclk))

# ---------------- PAC Bode
f, H = pac("pac1.0.pac", "vout1"); G, fhp, flp = bw(f, H)
res["bode"] = {"NPR6 27C": dict(G=G, fhp=fhp, flp=flp)}
f6, H6 = pac("pac1.0.pac", "vout6"); res["bode"]["NPR10 27C"] = dict(zip(("G", "fhp", "flp"), bw(f6, H6)))
for T in (37,):
    fn_ = "pac%d.0.pac" % T
    if os.path.exists(os.path.join(RD, fn_)):
        a, b = pac(fn_, "vout1"); res["bode"]["NPR6 %dC" % T] = dict(zip(("G", "fhp", "flp"), bw(a, b)))
        a, b = pac(fn_, "vout6"); res["bode"]["NPR10 %dC" % T] = dict(zip(("G", "fhp", "flp"), bw(a, b)))
for k, v in res["bode"].items():
    print("  PAC %-10s G=%.2f dB f_HP=%.3f Hz f_LP=%.0f Hz" % (k, v["G"], v["fhp"], v["flp"]))
# CMRR (bench 2 has a 1 V PAC common-mode source) and Zin (current of VIP1, 0.5 V PAC)
fc, Hc = pac("pac1.0.pac", "vout2")
i50 = np.argmin(abs(f - 50)); res["CMRR50"] = float(20 * np.log10(abs(H[i50]) / abs(Hc[i50])))
_, Ivip = pac("pac1.0.pac", "VIP1:p")
res["Zin50"] = float(0.5 / abs(Ivip[i50]))
print("  CMRR @50 Hz = %.1f dB (Adm %.2f dB, Acm %.2f dB);  Zin(vinp) @50 Hz = %.1f MOhm (1/(wCin)=%.1f MOhm)" % (
    res["CMRR50"], 20 * np.log10(abs(H[i50])), 20 * np.log10(abs(Hc[i50])), res["Zin50"] / 1e6, 1 / (2 * np.pi * 50 * 20e-12) / 1e6))

# Phase 2 reference
p2ac = psf.read(os.path.join(P2, "swc-000_ac1.ac")); p2nz = psf.read(os.path.join(P2, "nz.noise"))
fig, ax = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
ax[0].semilogx(p2ac["freq"], 20 * np.log10(abs(p2ac["vout1"])), "k--", label="Phase 2 lna_cci (AC)")
ax[0].semilogx(f, 20 * np.log10(abs(H)), label="Phase 3 lna_chop (PAC sb 0), 27 C")
if "NPR6 37C" in res["bode"]:
    a, b = pac("pac37.0.pac", "vout1"); ax[0].semilogx(a, 20 * np.log10(abs(b)), label="Phase 3, 37 C")
ax[1].semilogx(p2ac["freq"], np.angle(p2ac["vout1"], deg=True), "k--"); ax[1].semilogx(f, np.angle(H, deg=True))
ax[0].set_ylabel("gain [dB]"); ax[1].set_ylabel("phase [deg]"); ax[1].set_xlabel("Hz"); ax[0].set_ylim(0, 45)
ax[0].set_title("Differential gain: Phase 2 (AC) vs Phase 3 chopped (PAC, f_chop=5 kHz)")
for a_ in ax:
    a_.grid(True, which="both", alpha=0.3)
ax[0].legend(fontsize=8); fig.tight_layout(); fig.savefig(os.path.join(OUT, "5_pac_bode%s.png" % tag), dpi=150); plt.close(fig)

# ---------------- PSTB
if os.path.exists(os.path.join(RD, "pstb1.0.margin.pstb")):
    m = psf.read(os.path.join(RD, "pstb1.0.margin.pstb")); lg = psf.read(os.path.join(RD, "pstb1.0.pstb"))
    num = lambda x: float(np.atleast_1d(x)[0])
    res["pstb"] = dict(PM=num(m["phaseMargin"]), GM=num(m["gainMargin"]), fu=num(m["phaseMarginFreq"]), f180=num(m["gainMarginFreq"]))
    A = 20 * np.log10(abs(lg["loopGain"])); res["pstb"]["T10"] = float(np.interp(10, lg["freq"], A))
    print("  PSTB: PM=%.1f deg @ %.0f Hz, GM=%.1f dB @ %.3g Hz, |T| @10 Hz = %.1f dB" % (
        res["pstb"]["PM"], res["pstb"]["fu"], res["pstb"]["GM"], res["pstb"]["f180"], res["pstb"]["T10"]))
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    a1.semilogx(lg["freq"], A); a2.semilogx(lg["freq"], np.unwrap(np.angle(lg["loopGain"])) * 180 / np.pi)
    a1.axhline(0, color="k", lw=0.6); a1.set_ylabel("|T| [dB]"); a2.set_ylabel("phase [deg]"); a2.set_xlabel("Hz")
    a1.set_title("Phase 3 loop gain, Spectre PSTB (probe I1.IPRB), CL=2 pF: PM %.1f deg" % res["pstb"]["PM"])
    for a_ in (a1, a2):
        a_.grid(True, which="both", alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "5_pstb%s.png" % tag), dpi=150); plt.close(fig)

# ---------------- Pnoise
n = psf.read(os.path.join(RD, "pn1.pnoise")); fn = n["freq"]; out = np.abs(n["out"])
Hn = np.exp(np.interp(np.log(fn), np.log(f), np.log(np.abs(H)))); vin = out / Hn; H2 = Hn ** 2
Gl = 10 ** (G / 20); BW = flp - fhp
vb = np.sqrt(integ(fn, vin ** 2, 0.5, 200)); vt = np.sqrt(integ(fn, out ** 2, 0.1, 1e5)) / Gl
I_st = 549.9e-9   # static analog current incl. ideal IREF (op of static bench), replaced below if available
try:
    op = psf.read(os.path.join(HERE, "raw", "p3_static", "op.dc")); I_st = abs(float(np.atleast_1d(op["VDD1:p"])[0]))
    res["Cp"] = float(np.atleast_1d(op["I1.I0.M1:cgg"])[0])
except Exception:
    pass
nef = lambda I: vt * np.sqrt(2 * I / (np.pi * UT_NEF * FOURKT * BW))
res["noise"] = dict(vni_band=vb, vni_tot=vt, BW=BW, I_static=I_st, NEF=nef(I_st), NEF_exIREF=nef(I_st - 25e-9),
                    NEF_pss=nef(res["I_vdd1_pss"]), vin1=float(np.interp(1, fn, vin)), vin1k=float(np.interp(1e3, fn, vin)))
res["noise"]["PEF"] = res["noise"]["NEF"] ** 2 * 1.8
fl = np.median(vin[(fn > 300) & (fn < 1000)]); lo = np.where((vin > np.sqrt(2) * fl) & (fn < 300))[0]
res["noise"]["floor"] = float(fl); res["noise"]["corner"] = float(fn[lo[-1]]) if len(lo) else float("nan")
N = res["noise"]
print("  Pnoise: Vni(0.5-200 Hz) = %.3f uVrms; Vni_tot (0.1 Hz-100 kHz out / G) = %.3f uVrms; floor %.0f nV/rtHz; 1/f corner %.3g Hz" % (
    vb * 1e6, vt * 1e6, fl * 1e9, N["corner"]))
print("  NEF = %.4g*sqrt(2*%.4g/(pi*%.4f*%.4g*%.1f)) = %.3f  (excl IREF %.3f; with PSS-average I %.1f nA: %.3f)  PEF=%.1f" % (
    vt, I_st, UT_NEF, FOURKT, BW, N["NEF"], N["NEF_exIREF"], res["I_vdd1_pss"] * 1e9, N["NEF_pss"], N["PEF"]))
ctab, band, bandfl, totb = table(n, fn, out, H2)
res["contrib"] = {str(k): v for k, v in ctab.items()}
res["band_share"] = sorted(((b, 100 * x / totb) for b, x in band.items()), key=lambda x: -x[1])[:10]
res["load_flicker_share"] = 100 * (bandfl.get("M7", 0) + bandfl.get("M8", 0)) / totb
res["pr_share"] = 100 * band.get("pseudo-R chains", 0) / totb
for fx, l in ctab.items():
    print("  contributors @ %g Hz: " % fx + "; ".join("%s %.0f nV/rtHz (%.1f%%)" % (a, b * 1e9, c) for a, b, c in l))
print("  in-band (0.5-200 Hz) shares: " + "; ".join("%s %.1f%%" % x for x in res["band_share"]))
print("  load (M7/M8) flicker share in band = %.1f %%, pseudo-R share = %.1f %%" % (res["load_flicker_share"], res["pr_share"]))
# pr6 noise
if os.path.exists(os.path.join(RD, "pn6.pnoise")):
    n6 = psf.read(os.path.join(RD, "pn6.pnoise")); o6 = np.abs(n6["out"])
    H6n = np.exp(np.interp(np.log(n6["freq"]), np.log(f6), np.log(np.abs(H6)))); v6 = o6 / H6n
    G6 = res["bode"]["NPR10 27C"]
    t6, b6, _, tb6 = table({k.replace("I6.", "I1."): v for k, v in n6.items()}, n6["freq"], o6, H6n ** 2)
    res["noise6"] = dict(vni_band=float(np.sqrt(integ(n6["freq"], v6 ** 2, 0.5, 200))), pr_share=100 * b6.get("pseudo-R chains", 0) / tb6)
    print("  NPR=10 bench (I6): Vni(0.5-200) = %.3f uV, pseudo-R share %.1f %%" % (res["noise6"]["vni_band"] * 1e6, res["noise6"]["pr_share"]))
# overlay with Phase 2
f2 = p2nz["freq"]; o2 = np.abs(p2nz["out"]); H2p = np.exp(np.interp(np.log(f2), np.log(p2ac["freq"]), np.log(np.abs(p2ac["vout1"]))))
fig, ax = plt.subplots(figsize=(8, 5))
ax.loglog(f2, o2 / H2p * 1e9, "k--", label="Phase 2 lna_cci (noise), Vni=2.47 uV")
ax.loglog(fn, vin * 1e9, label="Phase 3 lna_chop (Pnoise, timeaverage, maxsideband 30), Vni=%.2f uV" % (vb * 1e6))
ax.axvspan(0.5, 200, color="C2", alpha=0.08, label="0.5-200 Hz band")
ax.set_xlabel("Hz"); ax.set_ylabel("input-referred noise [nV/rtHz]"); ax.grid(True, which="both", alpha=0.3); ax.legend(fontsize=8)
ax.set_xlim(0.1, 1e5); ax.set_title("Input-referred noise PSD: Phase 2 vs Phase 3 (chopped, f_chop=5 kHz)")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "6_psd_overlay%s.png" % tag), dpi=150); plt.close(fig)
# output noise around f_chop
if os.path.exists(os.path.join(RD, "pnfc.pnoise")):
    nf = psf.read(os.path.join(RD, "pnfc.pnoise"))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.semilogy(nf["freq"], np.abs(nf["out"]) * 1e9); ax.axvline(5e3, color="r", ls=":", label="f_chop")
    ax.set_xlabel("Hz"); ax.set_ylabel("output noise [nV/rtHz]"); ax.grid(True, which="both", alpha=0.3); ax.legend()
    ax.set_title("Output noise around f_chop: up-converted flicker (input pair, sinks, load)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "6_outnoise_fchop%s.png" % tag), dpi=150); plt.close(fig)
    res["out_noise_at_fchop"] = float(np.interp(5e3, nf["freq"], np.abs(nf["out"])))
json.dump(res, open(os.path.join(OUT, "main_results%s.json" % tag), "w"), indent=1, default=float)
