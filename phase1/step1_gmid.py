"""Step 1: gm/ID characterization plots, n extraction, LUT export (gpdk180, W=10u, |VDS|=0.9, VSB=0)."""
import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(__file__))
import psf

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw", "gmid_char")
OUT = os.path.join(HERE, "plots")
os.makedirs(OUT, exist_ok=True)
Ls = [0.18e-6, 0.5e-6, 1e-6, 2e-6, 4e-6]
W = 10e-6
kB, q = 1.380649e-23, 1.602176634e-19
T = 300.15
Ut = kB * T / q
IMIN = 1e-12   # drop |ID| below 1 pA (numerical floor / junction leakage)

dev = {"nmos": "M0", "pmos": "M1"}
data = {d: {} for d in dev}
for k, L in enumerate(Ls):
    r = psf.read(os.path.join(RAW, "swL-%03d_dcsw.dc" % k))
    for d, m in dev.items():
        vgs = r["VGS"]
        idd = np.abs(r[m + ":ids"]); gm = np.abs(r[m + ":gm"]); gds = np.abs(r[m + ":gds"])
        cgg = np.abs(r[m + ":cgg"]); vth = np.abs(r[m + ":vth"]); vds = np.abs(r[m + ":vdsat"])
        reg = r[m + ":region"]
        ok = idd > IMIN
        data[d][L] = dict(vgs=vgs[ok], id=idd[ok], gm=gm[ok], gds=gds[ok], cgg=cgg[ok], vth=vth[ok],
                          vdsat=vds[ok], region=reg[ok], idw=idd[ok] / W, gmid=gm[ok] / idd[ok],
                          gain=gm[ok] / gds[ok], ft=gm[ok] / (2 * np.pi * cgg[ok]),
                          id_all=idd, vgs_all=vgs)

lab = lambda L: "L=%gu" % (L * 1e6)
colors = plt.cm.viridis(np.linspace(0, 0.9, len(Ls)))


def fig4(name, fn, xl, yl, logx=False, logy=False, title=""):
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    for a, d in zip(ax, dev):
        for c, L in zip(colors, Ls):
            x, y = fn(data[d][L])
            a.plot(x, y, color=c, label=lab(L))
        if logx: a.set_xscale("log")
        if logy: a.set_yscale("log")
        a.set_xlabel(xl); a.set_ylabel(yl); a.grid(True, which="both", alpha=0.3)
        a.set_title("%s  %s  (W=10u, |VDS|=0.9 V, VSB=0)" % (d.upper(), title), fontsize=10)
        a.legend(fontsize=8)
    fig.tight_layout()
    p = os.path.join(OUT, name)
    fig.savefig(p, dpi=150); plt.close(fig)
    return p


fig4("1a_gmid_vs_idw.png", lambda D: (D["idw"], D["gmid"]), "ID/W  [A/m] (= uA/um)", "gm/ID  [1/V]", logx=True,
     title="gm/ID vs ID/W")
fig4("1b_gain_vs_gmid.png", lambda D: (D["gmid"], D["gain"]), "gm/ID  [1/V]", "gm/gds  [V/V]", logy=True,
     title="intrinsic gain vs gm/ID")
fig4("1c_ft_vs_gmid.png", lambda D: (D["gmid"], D["ft"]), "gm/ID  [1/V]", "fT = gm/(2 pi cgg)  [Hz]", logy=True,
     title="fT vs gm/ID")
fig4("1d_idw_vs_vgs.png", lambda D: (D["vgs_all"], np.maximum(D["id_all"] / W, 1e-9)), "|VGS|  [V]",
     "ID/W  [A/m]", logy=True, title="ID/W vs |VGS|")

# ---- summary numbers
print("Ut = %.2f mV (T = %.2f K)" % (Ut * 1e3, T))
summary = []
for d in dev:
    for L in Ls:
        D = data[d][L]
        # subthreshold slope from max d(lnID)/dVGS over the sweep region with ID > 1 pA
        mx = D["gmid"].max()
        n = 1.0 / (Ut * mx)
        S = np.log(10) * n * Ut * 1e3  # mV/dec
        # Vth as reported by model at |VGS| = 0.6 V (moderate inversion), plus at the max
        vth = np.interp(0.6, D["vgs"], D["vth"])
        i_mx = np.argmax(D["gmid"])
        summary.append((d, L, mx, D["id"][i_mx] / W, n, S, vth))
        print("%s %-6s max gm/ID = %5.1f /V (at ID/W=%.2e A/m, |VGS|=%.3f)  n = %.3f  S = %.1f mV/dec  |Vth|(model)= %.3f V"
              % (d, lab(L), mx, D["id"][i_mx] / W, D["vgs"][i_mx], n, S, vth))

# ---- CSV LUT (requested columns) + extended
with open(os.path.join(OUT, "gmid_lut.csv"), "w") as f:
    f.write("type,L,VGS,ID/W,gm/ID,gm/gds,fT\n")
    for d in dev:
        for L in Ls:
            D = data[d][L]
            for i in range(len(D["vgs"])):
                f.write("%s,%g,%.4f,%.6e,%.5f,%.5e,%.5e\n" % (d, L, D["vgs"][i], D["idw"][i], D["gmid"][i],
                                                             D["gain"][i], D["ft"][i]))
with open(os.path.join(OUT, "gmid_lut_ext.csv"), "w") as f:
    f.write("type,L,VGS,ID/W,gm/ID,gm/gds,fT,vth,vdsat,region,cgg_per_W\n")
    for d in dev:
        for L in Ls:
            D = data[d][L]
            for i in range(len(D["vgs"])):
                f.write("%s,%g,%.4f,%.6e,%.5f,%.5e,%.5e,%.5f,%.5f,%d,%.5e\n" % (
                    d, L, D["vgs"][i], D["idw"][i], D["gmid"][i], D["gain"][i], D["ft"][i], D["vth"][i],
                    D["vdsat"][i], D["region"][i], D["cgg"][i] / W))
np.save(os.path.join(OUT, "gmid_data.npy"), data, allow_pickle=True)
print("wrote plots + CSV to", OUT)
