"""Phase-4 results from the schematic tb_lpf / tb_chain runs."""
import os, re, json, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import psf, opinfo
from p2_metrics import integ, noise_metrics
from thd import thd, spectrum, amp_at

HERE = os.path.dirname(os.path.abspath(__file__)); RAW = os.path.join(HERE, "raw"); OUT = os.path.join(HERE, "plots")
R = lambda *p: os.path.join(RAW, *p)
res = {}
IBS = [0.85e-9, 1.27e-9, 2.5e-9, 4.2e-9, 6.3e-9, 8.5e-9]


def acm(f, H):
    A = 20 * np.log10(np.abs(H)); g0 = A[0]
    fc = float(np.exp(np.interp(-(g0 - 3), -A, np.log(f))))
    return float(g0), fc, float(A.max() - g0)


def but(f, fc):
    s = 1j * f / fc; return 1 / (1 + np.sqrt(2) * s + s ** 2)


def group(k):
    k = k.replace("X1.", "").replace("\\<", "<").replace("\\>", ">")
    m = re.match(r"(G1|G2<\d>)\.(M\w+?)(\.M\d)?$", k)
    if m:
        dev = m.group(2)
        role = {"M1A": "pair", "M2A": "pair", "M1B": "pair", "M2B": "pair", "MN1": "mirror", "MN2": "mirror", "MTA": "tail", "MTB": "tail"}.get(dev, dev)
        return ("Gm1 " if m.group(1) == "G1" else "Gm2 ") + role
    if k.startswith("MB"):
        return "bias diode MB"
    return k


# ---------------- op table
d = opinfo.read(R("p4_main", "op.info")); rows = []
for k, p in sorted(d.items()):
    if not k.startswith("X1."):
        continue
    i = abs(p["ids"])
    rows.append(dict(dev=k.replace("X1.", "").replace("\\", ""), id=i, gmid=abs(p["gm"]) / i if i else 0, vgs=abs(p["vgs"]), vds=abs(p["vds"]),
                     vdsat=abs(p["vdsat"]), margin=abs(p["vds"]) - abs(p["vdsat"]), region=int(p["region"])))
res["op"] = rows
op = psf.read(R("p4_main", "op.dc")); g = lambda k: float(np.atleast_1d(op[k])[0])
res["I_nom"] = abs(g("VDD1:p")); res["vout_dc"] = g("vout1"); res["v1_dc"] = g("X1.v1")
print("op: I(VDD1) = %.3f nA (incl. IB %.2f nA), vout %.4f V, v1 %.4f V" % (res["I_nom"] * 1e9, 1.27, res["vout_dc"], res["v1_dc"]))
sat = [r for r in rows if not re.search(r"\.M[1-4]$", r["dev"])]   # skip lower segments of series stacks (triode by design)
print("min saturation margin (excluding lower stack segments): %+.3f V (%s)" % (min(r["margin"] for r in sat), min(sat, key=lambda r: r["margin"])["dev"]))

# ---------------- AC
ac = psf.read(R("p4_main", "ac1.ac")); f = ac["freq"]; H = ac["vout1"]
G0, fc, pk = acm(f, H)
A = 20 * np.log10(np.abs(H)); ph = np.unwrap(np.angle(H))
slope = float((np.interp(np.log10(6 * fc), np.log10(f), A) - np.interp(np.log10(2 * fc), np.log10(f), A)) / np.log10(3))
floor = float(np.median(A[f > 4e3])); notch = (float(f[np.argmin(A)]), float(A.min()))
gd = -np.gradient(ph, 2 * np.pi * f)
Hb = but(f, fc)
dev = float(np.max(np.abs(A[f < 3 * fc] - 20 * np.log10(np.abs(Hb[f < 3 * fc])))))
# Q from a least-squares fit of |H| to a 2nd-order low-pass in the band up to 3 fc
from itertools import product
best = (1e9, 0, 0)
for f0, Q in product(np.linspace(0.9 * fc, 1.1 * fc, 81), np.linspace(0.5, 0.9, 81)):
    s = 1j * f / f0; Hm = 1 / (1 + s / Q + s ** 2); m = f < 3 * fc
    e = np.sum((A[m] - G0 - 20 * np.log10(np.abs(Hm[m]))) ** 2)
    if e < best[0]:
        best = (e, f0, Q)
res["ac"] = dict(G0=G0, fc=fc, peak=pk, slope_dB_per_dec=slope, phase_fc=float(np.interp(fc, f, ph) * 180 / np.pi), f0_fit=best[1], Q_fit=best[2],
                 gd_1Hz_ms=float(np.interp(1, f, gd) * 1e3), gd_fc5_ms=float(np.interp(fc / 5, f, gd) * 1e3), gd_fc_ms=float(np.interp(fc, f, gd) * 1e3),
                 max_dev_vs_butterworth_dB=dev, stopband_floor_dB=floor, notch=notch)
a = res["ac"]
print("AC: G0 %.3f dB, fc %.1f Hz, peaking %.3f dB, fit f0 %.1f Hz Q %.3f, slope %.1f dB/dec (2fc-6fc), stopband floor %.1f dB (>4 kHz), notch %.0f Hz %.1f dB, phase@fc %.1f deg, "
      "group delay 1 Hz / fc/5 / fc = %.2f / %.2f / %.2f ms, max |dev| vs Butterworth %.2f dB" % (
          G0, fc, pk, a["f0_fit"], a["Q_fit"], slope, floor, notch[0], notch[1], a["phase_fc"], a["gd_1Hz_ms"], a["gd_fc5_ms"], a["gd_fc_ms"], dev))
Iin = ac["VIN1:p"]; res["Cin"] = {"%g Hz" % fx: float(abs(np.interp(fx, f, Iin.imag)) / (2 * np.pi * fx)) for fx in (10, 50, 150, 1000)}
print("filter input capacitance: " + ", ".join("%s %.3f pF" % (k, v * 1e12) for k, v in res["Cin"].items()))
fig, ax = plt.subplots(3, 1, figsize=(8, 9), sharex=True)
ax[0].semilogx(f, A, label="lpf_gmc (schematic)"); ax[0].semilogx(f, G0 + 20 * np.log10(np.abs(Hb)), "k--", label="ideal Butterworth, fc = %.1f Hz" % fc)
ax[0].set_ylim(-80, 5); ax[0].set_ylabel("gain [dB]"); ax[0].legend(fontsize=8)
ax[1].semilogx(f, ph * 180 / np.pi); ax[1].semilogx(f, np.unwrap(np.angle(Hb)) * 180 / np.pi, "k--"); ax[1].set_ylabel("phase [deg]")
ax[2].semilogx(f, gd * 1e3); ax[2].semilogx(f, -np.gradient(np.unwrap(np.angle(Hb)), 2 * np.pi * f) * 1e3, "k--"); ax[2].set_ylabel("group delay [ms]")
ax[2].set_xlabel("Hz"); ax[2].set_xlim(0.1, 1e5)
for x in ax:
    x.grid(True, which="both", alpha=0.3)
ax[0].set_title("Gm-C biquad: AC response vs ideal 2nd-order Butterworth (IB = 1.27 nA)")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "2_ac_vs_butterworth.png"), dpi=150); plt.close(fig)

# ---------------- tuning
res["tuning"] = []
fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
for k, ib in enumerate(IBS):
    a_ = psf.read(R("p4_main", "swIB-%03d_aci.ac" % k)); o_ = psf.read(R("p4_main", "swIB-%03d_opi.dc" % k))
    n_ = psf.read(R("p4_main", "swIB-%03d_nzi.noise" % k))
    g0, fck, pkk = acm(a_["freq"], a_["vout1"]); I = abs(float(np.atleast_1d(o_["VDD1:p"])[0]))
    vn = np.sqrt(integ(n_["freq"], np.abs(n_["out"]) ** 2, 0.1, 3 * fck))
    res["tuning"].append(dict(IB=ib, fc=fck, G0=g0, peak=pkk, I=I, noise=float(vn)))
    ax[0].semilogx(a_["freq"], 20 * np.log10(np.abs(a_["vout1"])), label="IB %.2f nA: fc %.0f Hz" % (ib * 1e9, fck))
    print("tuning IB=%.2f nA: fc=%.1f Hz, G0=%.3f dB, peak %.3f dB, I(VDD)=%.2f nA, noise(0.1Hz-3fc)=%.1f uV" % (ib * 1e9, fck, g0, pkk, I * 1e9, vn * 1e6))
ax[0].set_ylim(-60, 5); ax[0].set_xlabel("Hz"); ax[0].set_ylabel("dB"); ax[0].legend(fontsize=7); ax[0].grid(True, which="both", alpha=0.3)
t = res["tuning"]; ibv = np.array([x["IB"] for x in t]); fcv = np.array([x["fc"] for x in t])
ax[1].loglog(ibv * 1e9, fcv, "o-", label="fc (sim)"); ax[1].loglog(ibv * 1e9, fcv[1] * ibv / ibv[1], "k--", label="fc ~ IB (ideal WI)")
ax2 = ax[1].twinx(); ax2.plot(ibv * 1e9, [x["I"] * 1e9 for x in t], "s:C1"); ax2.set_ylabel("I(VDD) [nA]", color="C1")
ax[1].set_xlabel("IB [nA]"); ax[1].set_ylabel("fc [Hz]"); ax[1].grid(True, which="both", alpha=0.3); ax[1].legend(fontsize=8)
fig.suptitle("fc tuning by one bias current IB"); fig.tight_layout(); fig.savefig(os.path.join(OUT, "3_tuning.png"), dpi=150); plt.close(fig)

# ---------------- noise
nz = psf.read(R("p4_main", "nz.noise")); fn = nz["freq"]; o = np.abs(nz["out"])
vn = float(np.sqrt(integ(fn, o ** 2, 0.1, 3 * fc))); res["noise"] = dict(out_rms=vn, lna_in_ref=vn / 10 ** (39.94 / 20))
G = {}
for k, v in nz.items():
    if isinstance(v, np.ndarray) and v.ndim == 2 and k.startswith("X1."):
        b = group(k); x = G.setdefault(b, dict(tot=np.zeros(len(fn)), fl=np.zeros(len(fn))))
        x["tot"] += v[:, -1]
        if v.shape[1] >= 5:
            x["fl"] += v[:, 3]
tot = vn ** 2
res["noise"]["contrib"] = sorted(((b, float(integ(fn, np.maximum(x["tot"], 1e-60), 0.1, 3 * fc) / tot * 100),
                                   float(integ(fn, np.maximum(x["fl"], 1e-60), 0.1, 3 * fc) / tot * 100)) for b, x in G.items()), key=lambda z: -z[1])
print("noise: %.2f uVrms (0.1 Hz - 3fc) at the output -> %.3f uV referred to the LNA input (/99.3)" % (vn * 1e6, res["noise"]["lna_in_ref"] * 1e6))
print("  contributors (% of output noise power, flicker part): " + "; ".join("%s %.1f%% (fl %.1f%%)" % c for c in res["noise"]["contrib"][:8]))
fig, ax = plt.subplots(figsize=(8, 4.5)); ax.loglog(fn, o * 1e9); ax.axvline(3 * fc, color="r", ls=":", label="3 fc")
ax.set_xlabel("Hz"); ax.set_ylabel("output noise [nV/rtHz]"); ax.grid(True, which="both", alpha=0.3); ax.legend()
ax.set_title("lpf_gmc output noise PSD: %.1f uVrms in 0.1 Hz - %.0f Hz" % (vn * 1e6, 3 * fc))
fig.tight_layout(); fig.savefig(os.path.join(OUT, "4_noise.png"), dpi=150); plt.close(fig)

# ---------------- temperature
res["temp"] = {}
for T, acn, nzn, opn in [(0, "acT0", "nzT0", "opT0"), (27, "ac1", "nz", "op"), (37, "acT37", "nzT37", "opT37"), (80, "acT80", "nzT80", "opT80")]:
    a_ = psf.read(R("p4_main", acn + ".ac")); n_ = psf.read(R("p4_main", nzn + ".noise")); o_ = psf.read(R("p4_main", opn + ".dc"))
    g0, fck, pkk = acm(a_["freq"], a_["vout1"])
    res["temp"][T] = dict(fc=fck, G0=g0, peak=pkk, noise=float(np.sqrt(integ(n_["freq"], np.abs(n_["out"]) ** 2, 0.1, 3 * fck))),
                          I=abs(float(np.atleast_1d(o_["VDD1:p"])[0])), vout=float(np.atleast_1d(o_["vout1"])[0]))
for T in (0, 27, 37, 80):
    p = R("p4_thd" if T == 27 else "p4_thd_T%d" % T, "swA-002_tr.tran.tran")
    if os.path.exists(p):
        r = psf.read(p); tu = np.arange(0.1, 0.3, 1 / 30 / 200); vu = np.interp(tu, r["time"], r["vout1"])
        res["temp"][T]["thd_0p5Vpp"] = float(thd(tu, vu, 30, 0.1, 0.1 + 6 / 30)[0])
for T, v in res["temp"].items():
    print("T=%2d C: fc %.1f Hz, G0 %.3f dB, peak %.3f dB, noise %.1f uV, I %.2f nA, vout %.4f V, THD(0.5Vpp) %s" % (
        T, v["fc"], v["G0"], v["peak"], v["noise"] * 1e6, v["I"] * 1e9, v["vout"], "%.3f %%" % (v["thd_0p5Vpp"] * 100) if "thd_0p5Vpp" in v else "n/a"))

# ---------------- THD vs amplitude (27 C)
p = R("p4_thd")
if os.path.isdir(p):
    res["thd"] = []
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    for k, amp in enumerate([0.05, 0.125, 0.25, 0.4]):
        r = psf.read(os.path.join(p, "swA-%03d_tr.tran.tran" % k)); tu = np.arange(0.1, 0.3, 1 / 30 / 200)
        vu = np.interp(tu, r["time"], r["vout1"]); th, h = thd(tu, vu, 30, 0.1, 0.1 + 6 / 30)
        res["thd"].append(dict(Vpp=2 * amp, thd=float(th), h2=float(h[1] / h[0]), h3=float(h[2] / h[0]), dc=float(vu.mean())))
        ax[0].plot(tu, vu, lw=0.8, label="%.2f Vpp: THD %.3f %%" % (2 * amp, th * 100))
        print("THD %.2f Vpp @ 30 Hz: %.3f %% (HD2 %.3f %%, HD3 %.3f %%), output mean %.4f V" % (2 * amp, th * 100, h[1] / h[0] * 100, h[2] / h[0] * 100, vu.mean()))
    ax[0].set_xlabel("s"); ax[0].set_ylabel("vout [V]"); ax[0].legend(fontsize=7); ax[0].grid(alpha=0.3)
    ax[1].plot([x["Vpp"] for x in res["thd"]], [x["thd"] * 100 for x in res["thd"]], "o-"); ax[1].axhline(1, color="r", ls=":")
    ax[1].set_xlabel("input [Vpp]"); ax[1].set_ylabel("THD [%]"); ax[1].grid(alpha=0.3)
    fig.suptitle("THD at fc/5 = 30 Hz (FFT over 6 cycles after 0.1 s, harmonics 2-10)"); fig.tight_layout()
    fig.savefig(os.path.join(OUT, "5_thd.png"), dpi=150); plt.close(fig)

# ---------------- transients (step, IM3, 1 Hz + 40 Hz)
p = R("p4_tran", "tr1.tran.tran")
if os.path.exists(p):
    r = psf.read(p); t = r["time"]
    v2 = r["vout2"]; m = t > 0.05; vf = v2[(t > 0.3) & (t < 0.45)].mean(); v0 = v2[(t > 0.03) & (t < 0.05)].mean()
    over = (v2[m].max() - vf) / (vf - v0) * 100
    bad = np.where(m & (np.abs(v2 - vf) > 0.01 * abs(vf - v0)))[0]; ts = t[bad[-1]] - 0.05 if len(bad) else np.nan
    res["step"] = dict(step=float(vf - v0), overshoot_pct=float(over), settle_1pct_ms=float(ts * 1e3))
    print("step 100 mV: final %.2f mV, overshoot %.2f %%, 1 %% settling %.2f ms" % ((vf - v0) * 1e3, over, ts * 1e3))
    tu = np.arange(0.1, 0.1 + 2 / 7.5, 1 / 37.5 / 200); vu = np.interp(tu, t, r["vout3"]); fs, X = spectrum(tu, vu, tu[0], tu[-1] + 1e-9)
    f1, f2 = 30, 37.5; a1, a2 = amp_at(fs, X, f1), amp_at(fs, X, f2); im3 = max(amp_at(fs, X, 2 * f1 - f2), amp_at(fs, X, 2 * f2 - f1))
    res["im3"] = dict(a1=float(a1), a2=float(a2), im3=float(im3), im3_dBc=float(20 * np.log10(im3 / a1)))
    print("two-tone 30 + 37.5 Hz (0.25 Vpp each): IM3 %.1f dBc (%.3g V at 22.5/45 Hz)" % (res["im3"]["im3_dBc"], im3))
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].plot(t * 1e3, r["vin2"], label="vin2"); ax[0].plot(t * 1e3, v2, label="vout2"); ax[0].set_xlim(40, 120)
    ax[0].set_xlabel("ms"); ax[0].set_title("100 mV step: overshoot %.1f %%, 1 %% settling %.1f ms" % (over, ts * 1e3)); ax[0].legend(); ax[0].grid(alpha=0.3)
    ax[1].semilogy(fs, X + 1e-9); ax[1].set_xlim(0, 120); ax[1].set_xlabel("Hz"); ax[1].grid(alpha=0.3)
    ax[1].set_title("two-tone 30/37.5 Hz: IM3 %.1f dBc" % res["im3"]["im3_dBc"])
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "6_step_im3.png"), dpi=150); plt.close(fig)
p = R("p4_tran", "tr2.tran.tran")
if os.path.exists(p):
    r = psf.read(p); t = r["time"]; v = r["vout3"]
    tu = np.arange(1.0, 3.0, 1 / 40 / 100); vu = np.interp(tu, t, v); fs, X = spectrum(tu, vu, 1.0, 3.0)
    g1 = amp_at(fs, X, 1) / 0.1; g40 = amp_at(fs, X, 40) / 0.1
    drift = float(np.mean(vu[(tu >= 2.0) & (tu < 3.0)]) - np.mean(vu[(tu >= 1.0) & (tu < 2.0)]))   # whole 1 Hz periods
    res["sine_1_40"] = dict(gain_1Hz=float(g1), gain_40Hz=float(g40), cm_mean=float(vu.mean()), cm_drift=drift)
    print("1 Hz + 40 Hz (0.2 Vpp each): gain %.4f / %.4f (ideal Butterworth %.4f at 40 Hz), output mean %.4f V, drift %.2f mV over 1 s (whole periods)" % (
        g1, g40, abs(but(40, fc)), vu.mean(), drift * 1e3))
    fig, ax = plt.subplots(figsize=(9, 4)); ax.plot(t, r["vin3"], lw=0.5, label="vin3"); ax.plot(t, v, lw=0.5, label="vout3")
    ax.set_xlabel("s"); ax.legend(); ax.grid(alpha=0.3); ax.set_title("1 Hz + 40 Hz input through the filter")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "6_sine_1_40Hz.png"), dpi=150); plt.close(fig)

# ---------------- chain
p = R("p4_chain")
if os.path.isdir(p):
    ac = psf.read(os.path.join(p, "ac1.ac")); fch = ac["freq"]; Hc = ac["vout"]; Hl = ac["vlna"]
    Ac = 20 * np.log10(np.abs(Hc)); i = np.argmax(Ac); Am = Ac[i]
    fl = float(np.exp(np.interp(Am - 3, Ac[:i + 1], np.log(fch[:i + 1])))); fh = float(np.exp(np.interp(-(Am - 3), -Ac[i:], np.log(fch[i:]))))
    nz = psf.read(os.path.join(p, "nz.noise")); nzl = psf.read(os.path.join(p, "nzl.noise"))
    opc = psf.read(os.path.join(p, "op.dc")); gg = lambda k: float(np.atleast_1d(opc[k])[0])
    Hn = np.interp(nz["freq"], fch, np.abs(Hc)); vin = np.abs(nz["out"]) / Hn
    vb = float(np.sqrt(integ(nz["freq"], vin ** 2, 0.5, 150)))
    Hln = np.interp(nzl["freq"], fch, np.abs(Hl)); vinl = np.abs(nzl["out"]) / Hln
    vbl = float(np.sqrt(integ(nzl["freq"], vinl ** 2, 0.5, 150)))
    res["chain"] = dict(G=float(Am), fhp=fl, flp=fh, vni_0p5_150=vb, vni_lna_only_0p5_150=vbl, vout_dc=gg("vout"), vlna_dc=gg("vlna"),
                        I_lna=abs(gg("VDDL:p")), I_lpf=abs(gg("VDDF:p")))
    c = res["chain"]
    print("chain: gain %.2f dB, band %.3f Hz - %.1f Hz; Vni(0.5-150 Hz) at the chain input %.3f uV (LNA alone %.3f uV); "
          "output DC %.4f V (LNA out %.4f V); I LNA %.1f nA, LPF %.2f nA" % (c["G"], fl, fh, vb * 1e6, vbl * 1e6, c["vout_dc"], c["vlna_dc"], c["I_lna"] * 1e9, c["I_lpf"] * 1e9))
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ax[0].semilogx(fch, 20 * np.log10(np.abs(Hl)), label="LNA out (vlna)"); ax[0].semilogx(fch, Ac, label="filter out (vout)")
    ax[0].set_ylim(-20, 45); ax[0].set_xlabel("Hz"); ax[0].set_ylabel("dB"); ax[0].legend(); ax[0].grid(True, which="both", alpha=0.3)
    ax[0].set_title("lna_v2 -> lpf_gmc: band %.2f Hz - %.0f Hz" % (fl, fh))
    ax[1].loglog(nz["freq"], vin * 1e9, label="chain, input-referred"); ax[1].loglog(nzl["freq"], vinl * 1e9, "--", label="LNA alone")
    ax[1].set_xlim(0.01, 1e4); ax[1].set_xlabel("Hz"); ax[1].set_ylabel("nV/rtHz"); ax[1].legend(); ax[1].grid(True, which="both", alpha=0.3)
    ax[1].set_title("input-referred noise: %.2f uV (chain) vs %.2f uV (LNA), 0.5-150 Hz" % (vb * 1e6, vbl * 1e6))
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "7_chain.png"), dpi=150); plt.close(fig)
    pt = os.path.join(p, "tr1.tran.tran")
    if os.path.exists(pt):
        r = psf.read(pt); t = r["time"]; m = t > 2
        tu = np.arange(2, 4, 1e-4); vu = np.interp(tu, t, r["vout"]); th, h = thd(tu, vu, 10, 2, 4)
        c["T1"] = dict(dc=float(vu.mean()), fund=float(h[0]), thd=float(th))
        print("chain T1 (1 mV 10 Hz + 300 mV offset): out DC %.4f V, fund %.2f mV, THD %.3f %%" % (vu.mean(), h[0] * 1e3, th * 100))
json.dump(res, open(os.path.join(OUT, "phase4_results.json"), "w"), indent=1, default=float)
