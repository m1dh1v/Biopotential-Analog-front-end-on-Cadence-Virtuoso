"""Phase-2 main results (L_in = 4u, Cin = 20p): op/currents, Bode + temperature, stb, noise, CMRR/PSRR."""
import os, re, sys, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psf
from p2_metrics import noise_metrics, integ, bw, UT_NEF, FOURKT

HERE = os.path.dirname(os.path.abspath(__file__)); RD = os.path.join(HERE, "raw", "p2_main"); OUT = os.path.join(HERE, "plots")
res = {}
op = psf.read(os.path.join(RD, "op.dc")); g = lambda k: float(np.atleast_1d(op[k])[0])

# ---------------- currents / op
I_vdd = abs(g("VDD1:p")); IREF = 25e-9
br = {}
gi = lambda d: abs(g("I1.I0.%s:ids" % d))
br["tail M0 (16x pmos_u2)"] = gi("M0\\<0\\>.M1") * 16
br["load M7"] = gi("M7"); br["load M8"] = gi("M8")
br["bias: MBP-MCP-MBS branch"] = gi("XB.MBP.M1")
br["bias: IREF -> MC -> MBN (ideal IREF)"] = gi("XB.MC")
br["(internal) sinks M3/M4 each"] = gi("M3\\<0\\>.M0") * 10
br["(internal) input M1/M2 each"] = gi("M1")
br["(internal) cascodes M5/M6, M9/M10 each"] = gi("M5")
res["I_vdd"] = I_vdd; res["I_excl_iref"] = I_vdd - IREF; res["branches"] = br
print("== Supply current (bench 1) ==  I(VDD1) = %.1f nA ; excluding ideal IREF = %.1f nA" % (I_vdd * 1e9, (I_vdd - IREF) * 1e9))
for k, v in br.items():
    print("   %-42s %7.1f nA" % (k, v * 1e9))
nodes = ["vout1", "I1.ninv", "I1.nnon", "I1.vfb", "iref1", "I1.I0.nbn", "I1.I0.nbp", "I1.I0.vcp", "I1.I0.tail", "I1.I0.f1",
         "I1.I0.f2", "I1.I0.x1", "I1.I0.p1", "I1.I0.p2"]
res["nodes"] = {n: g(n) for n in nodes}
print("nodes: " + "  ".join("%s=%.3f" % (n.split(".")[-1].replace("iref1", "VCN(iref)"), g(n)) for n in nodes))
REG = {0: "off", 1: "triode", 2: "sat", 3: "subth"}
optab = []
for d in ["M1", "M2", "M5", "M6", "M7", "M8", "M9", "M10", "M0\\<0\\>.M1", "M3\\<0\\>.M0", "M4\\<0\\>.M0", "XB.MC", "XB.MCP",
          "XB.MBN.M0", "XB.MBS.M0", "XB.MBP.M1"]:
    p = lambda n: g("I1.I0.%s:%s" % (d, n)); i = abs(p("ids"))
    optab.append(dict(dev=d.replace("\\", ""), id=i, gmid=abs(p("gm")) / i, vds=abs(p("vds")), vdsat=abs(p("vdsat")),
                      margin=abs(p("vds")) - abs(p("vdsat")), region=REG.get(int(p("region")), "?"), cgg=abs(p("cgg"))))
print("%-12s %8s %6s %6s %6s %7s %s" % ("device", "ID[nA]", "gm/ID", "VDS", "Vdsat", "margin", "region"))
for r in optab:
    print("%-12s %8.2f %6.1f %6.3f %6.3f %7.3f %s" % (r["dev"], r["id"] * 1e9, r["gmid"], r["vds"], r["vdsat"], r["margin"], r["region"]))
res["op"] = optab
Cp = abs(g("I1.I0.M2:cgg")); res["Cp"] = Cp

# ---------------- Bode, f_HP / f_LP, temperature
fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
res["bode"] = {}
for lab, fn_ in [("CL=2 pF, 27C", "swc-000_ac1.ac"), ("CL=5 pF, 27C", "swc-001_ac1.ac"), ("CL=2 pF, 0C", "ac_T0.ac"),
                 ("CL=2 pF, 37C", "ac_T37.ac"), ("CL=2 pF, 80C", "ac_T80.ac")]:
    r = psf.read(os.path.join(RD, fn_)); f = r["freq"]; H = r["vout1"]
    G, fl, fh = bw(f, H); res["bode"][lab] = dict(G=G, fhp=fl, flp=fh)
    a1.semilogx(f, 20 * np.log10(np.abs(H)), label=lab); a2.semilogx(f, np.unwrap(np.angle(H)) * 180 / np.pi, label=lab)
a1.set_ylabel("|Vout/Vin,diff| [dB]"); a2.set_ylabel("phase [deg]"); a2.set_xlabel("Frequency [Hz]")
a1.set_title("lna_cci closed-loop response (Cin=20 pF, Cf=200 fF, L_in=4 um)"); a1.set_ylim(-20, 45)
for a in (a1, a2):
    a.grid(True, which="both", alpha=0.3); a.legend(fontsize=7)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "4_bode.png"), dpi=150); plt.close(fig)
print("\n== AC ==")
for k, v in res["bode"].items():
    print("  %-14s midband %.2f dB  f_HP=%.3f Hz  f_LP=%.0f Hz" % (k, v["G"], v["fhp"], v["flp"]))

# ---------------- stb
fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
res["stb"] = []
for k, cl in enumerate([2, 5]):
    r = psf.read(os.path.join(RD, "swc-%03d_stb1.stb" % k)); m = psf.read(os.path.join(RD, "swc-%03d_stb1.margin.stb" % k))
    f = r["freq"]; lg = r["loopGain"]; A = 20 * np.log10(np.abs(lg))
    i = (np.abs(f - 10)).argmin()
    res["stb"].append(dict(CL=cl, T_mid=A[i], Tmax=A.max(), PM=float(m["phaseMargin"][0]), GM=float(m["gainMargin"][0]),
                           fu=float(m["phaseMarginFreq"][0]), f180=float(m["gainMarginFreq"][0])))
    a1.semilogx(f, A, label="CL=%d pF" % cl); a2.semilogx(f, np.unwrap(np.angle(lg)) * 180 / np.pi, label="CL=%d pF" % cl)
a1.axhline(0, color="k", lw=0.6); a1.set_ylabel("|T| [dB]"); a2.set_ylabel("phase(T) [deg]"); a2.set_xlabel("Frequency [Hz]")
a1.set_title("LNA loop gain (iprobe between OTA out and Cf/pseudo-R node, Spectre stb)")
for a in (a1, a2):
    a.grid(True, which="both", alpha=0.3); a.legend(fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "5_stb.png"), dpi=150); plt.close(fig)
print("\n== stb ==")
for s in res["stb"]:
    print("  CL=%dp  loop gain @10 Hz=%.1f dB (max %.1f dB)  crossover=%.0f Hz  PM=%.1f deg  GM=%.1f dB (@%.3g Hz)" % (
        s["CL"], s["T_mid"], s["Tmax"], s["fu"], s["PM"], s["GM"], s["f180"]))

# ---------------- noise
ac = psf.read(os.path.join(RD, "swc-000_ac1.ac")); nz = psf.read(os.path.join(RD, "nz.noise"))
fn = nz["freq"]; out = np.abs(nz["out"])
m = noise_metrics(fn, out, ac["freq"], ac["vout1"], I_vdd)
m2 = noise_metrics(fn, out, ac["freq"], ac["vout1"], I_vdd - IREF)
res["noise"] = {k: v for k, v in m.items() if k != "vin"}; res["NEF_exclIREF"] = m2["NEF"]
H2 = np.interp(np.log(fn), np.log(ac["freq"]), np.abs(ac["vout1"])) ** 2
groups = {}
for k, v in nz.items():
    if k.startswith("I1.") and isinstance(v, np.ndarray) and v.ndim == 2:
        b = k[3:]
        if b.startswith("PR"):
            b = "pseudo-R chains (PR1+PR2, 24 PMOS)"
            fl, th = np.zeros_like(fn), v[:, -1]
        else:
            if b.startswith("I0.XB"):
                b = "bias_gen (" + b.split(".")[2] + ")"
            else:
                b = re.sub(r"\\<\d+\\>", "", b).split(".")[1]
                b = {"M3": "M3 sinks (10x nmos_u5)", "M4": "M4 sinks (10x nmos_u5)", "M0": "M0 tail (16x pmos_u2)"}.get(b, b)
            fl, th = v[:, 3], v[:, 0] + v[:, 1] + v[:, 2]
        G_ = groups.setdefault(b, dict(fl=np.zeros_like(fn), th=np.zeros_like(fn), tot=np.zeros_like(fn)))
        G_["fl"] += fl; G_["th"] += th; G_["tot"] += v[:, -1]
res["contrib"] = {}
for fx in (1.0, 1e3):
    i = np.argmin(abs(fn - fx)); tot = out[i] ** 2
    items = []
    for b, G_ in groups.items():
        if b.startswith("pseudo"):
            items.append((b + " (shot/thermal)", G_["tot"][i]))
        else:
            items.append((b + " flicker", G_["fl"][i])); items.append((b + " thermal", G_["th"][i]))
    items.sort(key=lambda x: -x[1])
    res["contrib"][fx] = [(n, x / H2[i], 100 * x / tot) for n, x in items[:8]]
bandc = sorted(((b, integ(fn, G_["tot"] / H2, 0.5, 200)) for b, G_ in groups.items()), key=lambda x: -x[1])
res["band_contrib"] = [(b, x) for b, x in bandc[:8]]
print("\n== Noise (input-referred) ==")
print("  midband %.2f dB, f_HP %.3f Hz, f_LP %.0f Hz, BW=%.0f Hz" % (m["G"], m["fhp"], m["flp"], m["BW"]))
print("  in@1Hz %.0f nV/rtHz, in@1kHz %.1f nV/rtHz" % (m["vin1"] * 1e9, m["vin1k"] * 1e9))
print("  Vni(0.5-200 Hz, brick-wall) = %.3f uVrms" % (m["vni_band"] * 1e6))
print("  Vni_total = sqrt(int out^2, 10mHz-100kHz)/G = %.3f uVrms" % (m["vni_tot"] * 1e6))
print("  NEF = %.3e*sqrt(2*%.4e/(pi*%.4f*%.4e*%.1f)) = %.3f   (with Itot excl. IREF %.1f nA: %.3f)" % (
    m["vni_tot"], I_vdd, UT_NEF, FOURKT, m["BW"], m["NEF"], (I_vdd - IREF) * 1e9, m2["NEF"]))
print("  PEF = NEF^2*VDD = %.3f^2*1.8 = %.2f" % (m["NEF"], m["PEF"]))
print("  Cp = Cgg(M2) = %.3f pF -> (Cin+Cf+Cp)/Cin = (20+0.2+%.3f)/20 = %.3f" % (Cp * 1e12, Cp * 1e12, (20.2e-12 + Cp) / 20e-12))
for fx, lst in res["contrib"].items():
    print("  contributors @%g Hz:" % fx)
    for n, v, pc in lst:
        print("     %-44s %.3e V2/Hz (%.0f nV/rtHz in-ref)  %5.1f %%" % (n, v, np.sqrt(v) * 1e9, pc))
print("  band (0.5-200 Hz) shares: " + ", ".join("%s %.1f%%" % (b, 100 * x / m["vni_band"] ** 2) for b, x in bandc[:6]))
fig, ax = plt.subplots(figsize=(8, 4.8))
ax.loglog(fn, m["vin"] * 1e9, "k", lw=1.6, label="total, input-referred (out/|H|)")
for b, c in [("pseudo-R chains (PR1+PR2, 24 PMOS)", "C3"), ("M1", "C0"), ("M2", "C9")]:
    ax.loglog(fn, np.sqrt(groups[b]["tot"] / H2) * 1e9, color=c, ls=":", label=b + " part")
ax.axvspan(0.5, 200, color="C2", alpha=0.07)
ax.set_xlabel("Frequency [Hz]"); ax.set_ylabel("Input-referred noise [nV/rtHz]"); ax.set_xlim(1e-2, 1e5)
ax.set_title("LNA input-referred noise: %.2f uVrms (0.5-200 Hz), %.2f uVrms total" % (m["vni_band"] * 1e6, m["vni_tot"] * 1e6), fontsize=10)
ax.grid(True, which="both", alpha=0.3); ax.legend(fontsize=7)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "6_noise.png"), dpi=150); plt.close(fig)

# ---------------- CMRR / PSRR
def at(fname, node, f0):
    r = psf.read(os.path.join(RD, fname)); return np.interp(np.log(f0), np.log(r["freq"]), np.abs(r[node]))
res["cmrr"] = {}
print("\n== CMRR / PSRR ==")
for tag, fname in [("nominal", "swc-000_ac1.ac"), ("Cin1 +0.1%", "ac_mm.ac")]:
    for f0 in (10, 50):
        Ad = at(fname, "vout1", f0); Acm = at(fname, "vout2", f0); Aps = at(fname, "vout3", f0)
        c, p = 20 * np.log10(Ad / Acm), 20 * np.log10(Ad / Aps)
        res["cmrr"]["%s@%d" % (tag, f0)] = dict(Adm=20 * np.log10(Ad), Acm=20 * np.log10(Acm), Aps=20 * np.log10(Aps), CMRR=c, PSRR=p)
        print("  %-11s %2d Hz: Adm=%.2f dB  Acm=%.1f dB  Avdd=%.1f dB  CMRR=%.1f dB  PSRR=%.1f dB" % (
            tag, f0, 20 * np.log10(Ad), 20 * np.log10(Acm), 20 * np.log10(Aps), c, p))
json.dump(res, open(os.path.join(OUT, "main_results.json"), "w"), indent=1, default=lambda o: float(o) if np.isscalar(o) else str(o))
