import os, json, re, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import psf
from p2_metrics import noise_metrics
OUT = "plots"; res = {}
# ---- 0c CMRR / PSRR
rd = "raw/p4_cmrr"
if os.path.isdir(rd):
    g = lambda n: psf.read(os.path.join(rd, n + ".ac"))
    fig, ax = plt.subplots(figsize=(8, 5))
    res["cmrr"] = {}
    for suf, lab, ls in (("", "nominal", "-"), ("_mm", "Cin1 +0.1 %", "--")):
        dm, cm, ps = g("dm" + suf), g("cm" + suf), g("ps" + suf); f = dm["freq"]
        Adm = np.abs(dm["vout1"]); Acm = np.abs(cm["vout1"]) / 0.5; Aps = np.abs(ps["vout1"])
        cmrr = 20 * np.log10(Adm / Acm); psrr = 20 * np.log10(Adm / Aps)
        ax.semilogx(f, cmrr, "C0" + ls, label="CMRR " + lab); ax.semilogx(f, psrr, "C1" + ls, label="PSRR " + lab)
        res["cmrr"][lab] = {"%g Hz" % fx: dict(CMRR=float(np.interp(fx, f, cmrr)), PSRR=float(np.interp(fx, f, psrr))) for fx in (0.1, 1, 10, 50, 100, 1000, 10000)}
    ax.set_xlabel("Hz"); ax.set_ylabel("dB"); ax.grid(True, which="both", alpha=0.3); ax.legend()
    ax.set_title("lna_v2: CMRR and PSRR vs frequency (Adm/Acm, Adm/Avdd), nominal and 0.1 % Cin mismatch")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "0c_lna_v2_cmrr_psrr.png"), dpi=150); plt.close(fig)
    for lab, d in res["cmrr"].items():
        print("CMRR/PSRR %s: " % lab + "  ".join("%s %.1f/%.1f" % (k, v["CMRR"], v["PSRR"]) for k, v in d.items()))
# ---- 0d L sweep
rd = "raw/p4_lsweep"
if os.path.isdir(rd):
    fig, ax = plt.subplots(figsize=(8, 5)); res["lsweep"] = []
    for k, L in enumerate([1, 2, 4, 8]):
        ac = psf.read(os.path.join(rd, "swL-%03d_ac1.ac" % k)); nz = psf.read(os.path.join(rd, "swL-%03d_nz.noise" % k))
        op = psf.read(os.path.join(rd, "swL-%03d_op.dc" % k)); I = abs(float(np.atleast_1d(op["VDD1:p"])[0]))
        m = noise_metrics(nz["freq"], np.abs(nz["out"]), ac["freq"], ac["vout1"], I)
        cp = float(np.atleast_1d(op["I1.I0.M1:cgg"])[0])
        res["lsweep"].append(dict(L=L, G=m["G"], fhp=m["fhp"], flp=m["flp"], vni=m["vni_band"], vtot=m["vni_tot"], NEF=m["NEF"], Cp=cp, I=I))
        ax.loglog(nz["freq"], m["vin"] * 1e9, label="L = %d um: Vni %.2f uV, NEF %.2f, f_LP %.0f Hz, Cp %.2f pF" % (L, m["vni_band"] * 1e6, m["NEF"], m["flp"], cp * 1e12))
        print("L=%d: G %.2f fHP %.3f fLP %.0f Vni %.3f uV tot %.2f NEF %.2f Cp %.2f pF" % (L, m["G"], m["fhp"], m["flp"], m["vni_band"] * 1e6, m["vni_tot"] * 1e6, m["NEF"], cp * 1e12))
    ax.axvspan(0.5, 200, color="C2", alpha=0.07); ax.set_xlim(0.01, 1e5)
    ax.set_xlabel("Hz"); ax.set_ylabel("input-referred noise [nV/rtHz]"); ax.grid(True, which="both", alpha=0.3); ax.legend(fontsize=7)
    ax.set_title("lna_v2 (unchopped): input-pair L sweep, W = 500 um, 200 nA/device")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "0d_lna_v2_Lsweep_noise.png"), dpi=150); plt.close(fig)
# ---- 0b op table
p = "raw/p4_op/op.dc"
if os.path.exists(p):
    op = psf.read(p); devs = sorted(set(k.rsplit(":", 1)[0] for k in op if ":" in k and k.startswith("I1.I0.")))
    rows = []
    for d in devs:
        get = lambda n: float(np.atleast_1d(op.get(d + ":" + n, [np.nan]))[0])
        i = abs(get("ids"))
        if not np.isfinite(i): continue
        rows.append(dict(dev=d.replace("I1.I0.", "").replace("\\", ""), id=i, gmid=abs(get("gm")) / i if i else np.nan, vgs=abs(get("vgs")), vds=abs(get("vds")),
                         vdsat=abs(get("vdsat")), margin=abs(get("vds")) - abs(get("vdsat")), region=int(get("region"))))
    res["op"] = rows; print("op devices:", len(rows))
json.dump(res, open(os.path.join(OUT, "step0.json"), "w"), indent=1, default=float)
