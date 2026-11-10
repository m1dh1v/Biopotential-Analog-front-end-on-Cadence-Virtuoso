"""Phase-1 final results from raw/final (schematic netlist of AFE_lib/tb_ota). Prints tables, writes plots."""
import os, re, sys, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psf

HERE = os.path.dirname(os.path.abspath(__file__))
RD = os.path.join(HERE, "raw", "final")
OUT = os.path.join(HERE, "plots")
CLS = [1, 2, 5]
kB, q, T = 1.380649e-23, 1.602176634e-19, 300.0
Ut_nef = 25.9e-3
res = {}

# ------------------------------------------------------------------ DC operating point
op = psf.read(os.path.join(RD, "op.dc"))
g = lambda k: float(np.atleast_1d(op[k])[0])
Itot = abs(g("VDD1:p"))
res["Itot"] = Itot
print("== DC operating point (bench I1, open loop, VCM=0.9 V) ==")
print("I(VDD1) = %.1f nA   (other benches: %s nA)" % (Itot * 1e9, ", ".join("%.1f" % (abs(g("VDD%d:p" % k)) * 1e9) for k in range(2, 6))))
print("nodes: " + "  ".join("%s=%.3f" % (k.replace("I1.", ""), g(k)) for k in
                           ["vout1", "vin1", "I1.tail", "I1.f1", "I1.f2", "I1.x1", "I1.p1", "I1.p2", "nbn1", "nbp1"]))
devs = sorted({k.split(":")[0] for k in op if k.startswith("I1.") and ":" in k})
optab = []
print("%-16s %8s %6s %7s %7s %7s %7s %6s %3s" % ("instance", "ID[nA]", "gm/ID", "|VGS|", "|VDS|", "Vdsat", "margin", "gm/gds", "reg"))
for d in devs:
    p = lambda n: g("%s:%s" % (d, n))
    idd = abs(p("ids"))
    row = dict(dev=d.replace("I1.", "").replace("\\", ""), id=idd, gmid=abs(p("gm")) / idd, vgs=abs(p("vgs")),
               vds=abs(p("vds")), vdsat=abs(p("vdsat")), margin=abs(p("vds")) - abs(p("vdsat")),
               gain=abs(p("gm")) / abs(p("gds")), region=int(p("region")))
    optab.append(row)
    print("%-16s %8.2f %6.2f %7.3f %7.3f %7.3f %7.3f %6.0f %3d" % (row["dev"], idd * 1e9, row["gmid"], row["vgs"], row["vds"],
                                                                    row["vdsat"], row["margin"], row["gain"], row["region"]))
res["op"] = optab
res["nodes"] = {k: g(k) for k in ["vout1", "I1.tail", "I1.f1", "I1.f2", "I1.x1", "I1.p1", "I1.p2", "nbn1", "nbp1"]}

# composite device terminal voltages (whole stack)
comp = {"M0 (8x pmos_u2)": ("vdd", "I1.tail"), "M3 (6x nmos_u5)": ("I1.f1", "0"), "M4 (6x nmos_u5)": ("I1.f2", "0"),
        "M7": ("vdd", "I1.p1"), "M8": ("vdd", "I1.p2")}
V = lambda n: 1.8 if n == "vdd" else (0.0 if n == "0" else g(n))
res["comp_vds"] = {k: abs(V(a) - V(b)) for k, (a, b) in comp.items()}
print("composite |VDS|: " + ", ".join("%s=%.3f V" % (k, v) for k, v in res["comp_vds"].items()))

# ------------------------------------------------------------------ open-loop AC (bench I1)
fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
res["ac"] = []
for k, cl in enumerate(CLS):
    r = psf.read(os.path.join(RD, "swc-%03d_ac1.ac" % k))
    f = r["freq"]; H = r["vout1"]
    A = 20 * np.log10(np.abs(H)); ph = np.unwrap(np.angle(H)) * 180 / np.pi
    i0 = np.where(A < 0)[0][0]
    fu = np.exp(np.interp(0, [A[i0], A[i0 - 1]], [np.log(f[i0]), np.log(f[i0 - 1])]))
    phu = np.interp(np.log(fu), np.log(f), ph)
    f3 = np.exp(np.interp(A[0] - 3, A[::-1], np.log(f[::-1])))
    res["ac"].append(dict(CL=cl, A0=A[0], f3=f3, fu=fu, phu=phu, pm_ol=180 + phu))
    a1.semilogx(f, A, label="CL=%d pF" % cl); a2.semilogx(f, ph, label="CL=%d pF" % cl)
    if cl == 5:
        Adm10 = np.abs(np.interp(np.log(10), np.log(f), np.abs(H)))
        f_cm = f; Hcm = r["vout4"]; Hps = r["vout5"]; Hdm = H
a1.set_ylabel("|Av| [dB]"); a2.set_ylabel("phase [deg]"); a2.set_xlabel("Frequency [Hz]")
a1.set_title("ota_fc open-loop AC (L/C DC feedback, L=C=1e16), VCM=0.9 V")
for a in (a1, a2):
    a.grid(True, which="both", alpha=0.3); a.legend(fontsize=8)
a1.axhline(0, color="k", lw=0.6)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "3b_ac_bode.png"), dpi=150); plt.close(fig)
print("\n== Open-loop AC ==")
for r_ in res["ac"]:
    print("CL=%dp  A0=%.1f dB  f-3dB=%.3g Hz  GBW(UGF)=%.4g kHz  phase@UGF=%.1f deg  (PM_ol=%.1f)" % (
        r_["CL"], r_["A0"], r_["f3"], r_["fu"] / 1e3, r_["phu"], r_["pm_ol"]))

# CMRR / PSRR
Acm10 = np.abs(np.interp(np.log(10), np.log(f_cm), np.abs(Hcm)))
Aps10 = np.abs(np.interp(np.log(10), np.log(f_cm), np.abs(Hps)))
res["CMRR10"] = 20 * np.log10(Adm10 / Acm10); res["PSRR10"] = 20 * np.log10(Adm10 / Aps10)
res["Adm10"], res["Acm10"], res["Aps10"] = 20 * np.log10(Adm10), 20 * np.log10(Acm10), 20 * np.log10(Aps10)
print("@10 Hz: Adm=%.1f dB  Acm=%.1f dB  Avdd=%.1f dB  ->  CMRR=%.1f dB  PSRR(VDD)=%.1f dB" % (
    res["Adm10"], res["Acm10"], res["Aps10"], res["CMRR10"], res["PSRR10"]))
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.semilogx(f_cm, 20 * np.log10(np.abs(Hdm) / np.abs(Hcm)), label="CMRR")
ax.semilogx(f_cm, 20 * np.log10(np.abs(Hdm) / np.abs(Hps)), label="PSRR (VDD)")
ax.set_xlim(1e-2, 1e7); ax.set_xlabel("Frequency [Hz]"); ax.set_ylabel("[dB]"); ax.grid(True, which="both", alpha=0.3)
ax.legend(); ax.set_title("CMRR / PSRR (CL=5 pF)")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "3e_cmrr_psrr.png"), dpi=150); plt.close(fig)

# ------------------------------------------------------------------ stb
fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
res["stb"] = []
for k, cl in enumerate(CLS):
    r = psf.read(os.path.join(RD, "swc-%03d_stb1.stb" % k)); m = psf.read(os.path.join(RD, "swc-%03d_stb1.margin.stb" % k))
    f = r["freq"]; lg = r["loopGain"]
    A = 20 * np.log10(np.abs(lg)); ph = np.unwrap(np.angle(lg)) * 180 / np.pi
    mm = {}
    for kk, v in m.items():
        try:
            mm[kk] = float(np.atleast_1d(v)[0])
        except (ValueError, TypeError):
            mm[kk] = str(np.atleast_1d(v)[0])
    res["stb"].append(dict(CL=cl, T0=A[0], PM=mm.get("phaseMargin"), GM=mm.get("gainMargin"),
                           fu=mm.get("phaseMarginFreq"), f180=mm.get("gainMarginFreq")))
    a1.semilogx(f, A, label="CL=%d pF" % cl); a2.semilogx(f, ph, label="CL=%d pF" % cl)
a1.set_ylabel("|T| [dB]"); a2.set_ylabel("phase(T) [deg]"); a2.set_xlabel("Frequency [Hz]")
a1.set_title("Loop gain, unity-gain buffer (iprobe, Spectre stb)")
for a in (a1, a2):
    a.grid(True, which="both", alpha=0.3); a.legend(fontsize=8)
a1.axhline(0, color="k", lw=0.6)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "3c_stb_loopgain.png"), dpi=150); plt.close(fig)
print("\n== stb (unity-gain buffer) ==")
for s in res["stb"]:
    print("CL=%dp  T0=%.1f dB  fu=%.4g kHz  PM=%.1f deg  GM=%.1f dB (at %.4g kHz)" % (
        s["CL"], s["T0"], s["fu"] / 1e3, s["PM"], s["GM"], s["f180"] / 1e3))

# ------------------------------------------------------------------ noise
nz = psf.read(os.path.join(RD, "nz.noise"))
fn = nz["freq"]; vin = np.abs(nz["in"]); g2 = np.abs(nz["gain"]) ** 2
fl = np.zeros_like(fn); th = np.zeros_like(fn)
groups = {}
for key, v in nz.items():
    if not key.startswith("I1.") or not isinstance(v, np.ndarray) or v.ndim != 2 or v.shape[1] not in (5, 14):
        continue
    base = key[3:].replace("\\", "")
    base = re.sub(r"<\d+>", "", base).split(".")[0]          # composite: M3<k>.Mj -> M3
    if v.shape[1] == 14:      # separatenoise layout: rd.src rd.xf2 rd.out ... fn.out totalsrc total
        fl_k = v[:, 11]; th_k = v[:, 2] + v[:, 5] + v[:, 8]
    else:                     # rd rs id fn total (output-referred V^2/Hz)
        fl_k = v[:, 3]; th_k = v[:, 0] + v[:, 1] + v[:, 2]
    fl += fl_k; th += th_k
    G = groups.setdefault(base, dict(fl=np.zeros_like(fn), th=np.zeros_like(fn)))
    G["fl"] += fl_k; G["th"] += th_k
fl_in, th_in = fl / g2, th / g2
kc = np.where(np.diff(np.sign(np.log(fl_in) - np.log(th_in))) != 0)[0]
fcorner = float(np.exp(np.interp(0, [np.log(fl_in / th_in)[kc[0] + 1], np.log(fl_in / th_in)[kc[0]]],
                                 [np.log(fn[kc[0] + 1]), np.log(fn[kc[0]])]))) if len(kc) else float("nan")


def band(a, b):
    x = np.logspace(np.log10(a), np.log10(b), 4000)
    return np.sqrt(np.trapezoid(np.exp(np.interp(np.log(x), np.log(fn), np.log(vin ** 2))), x))


res["Vn_lo"] = band(0.5, 200); res["Vn_hi"] = band(300, 5e3); res["fcorner"] = fcorner
res["vin_1"] = np.interp(1, fn, vin); res["vin_1k"] = np.interp(1e3, fn, vin); res["vin_10k"] = np.interp(1e4, fn, vin)
print("\n== Noise (input-referred, bench I1) ==")
print("in(1 Hz)=%.0f nV/rtHz  in(1 kHz)=%.1f nV/rtHz  in(10 kHz)=%.1f nV/rtHz" % (res["vin_1"] * 1e9, res["vin_1k"] * 1e9, res["vin_10k"] * 1e9))
print("Vni(0.5-200 Hz) = %.3f uVrms   Vni(300 Hz-5 kHz) = %.3f uVrms   1/f corner = %.0f Hz" % (
    res["Vn_lo"] * 1e6, res["Vn_hi"] * 1e6, fcorner))
res["contrib"] = {}
for fx in (1.0, 1e3):
    i = np.argmin(abs(fn - fx))
    tot = vin[i] ** 2
    items = []
    for n_, G in groups.items():
        items.append(("%s flicker" % n_, G["fl"][i] / g2[i])); items.append(("%s thermal" % n_, G["th"][i] / g2[i]))
    items.sort(key=lambda x: -x[1])
    res["contrib"][fx] = [(n_, v_, 100 * v_ / tot) for n_, v_ in items[:5]]
    print("  top-5 @ %g Hz (input-referred V^2/Hz, %% of total %.3g):" % (fx, tot))
    for n_, v_, pc in res["contrib"][fx]:
        print("     %-16s %.3e  (%.1f nV/rtHz)  %5.1f %%" % (n_, v_, np.sqrt(v_) * 1e9, pc))
fig, ax = plt.subplots(figsize=(8, 4.8))
ax.loglog(fn, vin * 1e9, "k", lw=1.6, label="total input-referred")
ax.loglog(fn, np.sqrt(fl_in) * 1e9, "C3:", label="flicker part")
ax.loglog(fn, np.sqrt(th_in) * 1e9, "C0:", label="thermal part")
ax.axvline(fcorner, color="gray", ls="--", lw=0.8)
ax.text(fcorner * 1.1, vin.max() * 1e9 * 0.5, "1/f corner\n%.0f Hz" % fcorner, fontsize=8)
for a_, b_, c_ in [(0.5, 200, "C2"), (300, 5e3, "C1")]:
    ax.axvspan(a_, b_, color=c_, alpha=0.07)
ax.set_xlabel("Frequency [Hz]"); ax.set_ylabel("Input-referred noise [nV/rtHz]")
ax.set_title("ota_fc input-referred noise: %.2f uVrms (0.5-200 Hz), %.2f uVrms (0.3-5 kHz)" % (res["Vn_lo"] * 1e6, res["Vn_hi"] * 1e6), fontsize=10)
ax.grid(True, which="both", alpha=0.3); ax.legend(fontsize=8); ax.set_xlim(0.1, 1e5)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "3d_noise.png"), dpi=150); plt.close(fig)

# NEF
BW = 199.5
fourkT = 4 * kB * T
NEF = res["Vn_lo"] * np.sqrt(2 * Itot / (np.pi * Ut_nef * fourkT * BW))
res["NEF"] = NEF
print("\nNEF = Vni*sqrt(2*Itot/(pi*Ut*4kT*BW)) = %.3e*sqrt(2*%.4e/(pi*%.4f*%.4e*%.1f)) = %.3f" % (
    res["Vn_lo"], Itot, Ut_nef, fourkT, BW, NEF))
print("   (inner term = %.4e, sqrt = %.4e)" % (2 * Itot / (np.pi * Ut_nef * fourkT * BW), np.sqrt(2 * Itot / (np.pi * Ut_nef * fourkT * BW))))

# ------------------------------------------------------------------ swing (gain of -10)
d = psf.read(os.path.join(RD, "dcs.dc"))
vs = d["VS"]; vo = d["vout3"]
gi = np.gradient(vo, vs)
gmax = np.max(np.abs(gi))
ok = np.abs(gi) >= gmax / np.sqrt(2)
lo, hi = vo[ok].min(), vo[ok].max()
ok1 = np.abs(gi) >= 0.99 * gmax
res["swing3dB"] = (lo, hi); res["swing1pct"] = (vo[ok1].min(), vo[ok1].max()); res["g10max"] = gmax
print("\n== Output swing (inverting gain -10, R1=1G/R2=10G) ==")
print("max |dVout/dVs| = %.3f; Vout range with |gain| >= -3 dB of max: %.3f .. %.3f V (%.2f Vpp); within 1%%: %.3f .. %.3f V" % (
    gmax, lo, hi, hi - lo, res["swing1pct"][0], res["swing1pct"][1]))
fig, (a1, a2) = plt.subplots(2, 1, figsize=(7, 6), sharex=True)
a1.plot(vs, vo); a1.set_ylabel("Vout [V]"); a1.grid(alpha=0.3)
a2.plot(vs, np.abs(gi)); a2.axhline(gmax / np.sqrt(2), color="r", ls="--", lw=0.8); a2.set_ylabel("|dVout/dVs|")
a2.set_xlabel("VS [V]"); a2.grid(alpha=0.3)
a1.set_title("Output swing: inverting gain-of-10 (R1=1G, R2=10G), VCM=0.9 V")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "3e_swing.png"), dpi=150); plt.close(fig)

json.dump(res, open(os.path.join(OUT, "final_results.json"), "w"), indent=1, default=lambda o: float(o) if np.isscalar(o) else str(o))
