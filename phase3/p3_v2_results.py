"""Step 1 results (schematic tb_lna_v2): bias, saturation margins, AC/noise, T2 THD (non-chopped)."""
import os, json, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import psf
from thd import thd
from p2_metrics import noise_metrics
HERE = os.path.dirname(os.path.abspath(__file__)); RD = os.path.join(HERE, "raw", "p3_v2"); OUT = os.path.join(HERE, "plots")
op = psf.read(os.path.join(RD, "op.dc")); g = lambda k: float(np.atleast_1d(op[k])[0])
res = {"I_vdd": abs(g("VDD1:p")), "nodes": {}}
for k in ["vout1", "iref1", "I1.I0.vcn", "I1.I0.vcp", "I1.I0.nbp", "I1.I0.XB.vcm1", "I1.I0.tail", "I1.I0.f1", "I1.I0.f2",
          "I1.I0.x1", "I1.I0.p1", "I1.I0.p2", "I1.ninv", "I1.nnon"]:
    res["nodes"][k] = g(k)
print("I(VDD1) = %.1f nA (excl. IREF %.1f nA)" % (res["I_vdd"] * 1e9, res["I_vdd"] * 1e9 - 25))
print("  ".join("%s=%.3f" % (k.split(".")[-1], v) for k, v in res["nodes"].items()))
res["dev"] = []
for d in ["M1", "M2"] + ["M3\<0\>.M%d" % k for k in range(5)] + ["M4\<0\>.M%d" % k for k in range(5)] + \
         ["M5", "M6", "M7", "M8", "M9", "M10", "XB.MCN1", "XB.MCN2", "XB.MCP"]:
    p = lambda n: g("I1.I0.%s:%s" % (d, n)); i = abs(p("ids"))
    r = dict(dev=d.replace("\\", ""), id=i, gmid=abs(p("gm")) / i, vgs=abs(p("vgs")), vds=abs(p("vds")), vdsat=abs(p("vdsat")),
             margin=abs(p("vds")) - abs(p("vdsat")), region=int(p("region")))
    res["dev"].append(r)
    print("%-12s ID=%7.2fn gm/ID=%5.1f VGS=%.3f VDS=%.3f Vdsat=%.3f margin=%+.3f region=%d" % (
        r["dev"], i * 1e9, r["gmid"], r["vgs"], r["vds"], r["vdsat"], r["margin"], r["region"]))
ac = psf.read(os.path.join(RD, "ac1.ac")); nz = psf.read(os.path.join(RD, "nz.noise"))
m = noise_metrics(nz["freq"], np.abs(nz["out"]), ac["freq"], ac["vout1"], res["I_vdd"])
res["noise"] = {k: float(v) for k, v in m.items() if k != "vin"}
print("AC: G=%.2f dB f_HP=%.3f Hz f_LP=%.0f Hz | Vni(0.5-200)=%.3f uV Vni_tot=%.3f uV NEF=%.2f" % (
    m["G"], m["fhp"], m["flp"], m["vni_band"] * 1e6, m["vni_tot"] * 1e6, m["NEF"]))
res["T2"] = []
fig, ax = plt.subplots(figsize=(8, 4.5))
for k, A in enumerate([1, 3, 5, 8]):
    r2 = psf.read(os.path.join(RD, "swA-%03d_tr.tran.tran" % k)); t = r2["time"]; v = r2["vout1"]
    th, h = thd(t, v, 10, 1.0, 2.0); mm = t > 1
    res["T2"].append(dict(amp_mV=A, thd=float(th), fund=float(h[0]), vmin=float(v[mm].min()), vmax=float(v[mm].max())))
    ax.plot(t[mm], v[mm], label="%d mV (THD %.3f %%)" % (A, th * 100))
    print("T2 %d mV: fund %.4f V THD %.3f %% out %.3f..%.3f V" % (A, h[0], th * 100, v[mm].min(), v[mm].max()))
ax.axhline(0.45, color="k", ls=":", lw=0.8); ax.set_xlabel("time [s]"); ax.set_ylabel("vout1 [V]"); ax.grid(alpha=0.3)
ax.set_title("Step 1: lna_v2 (swing fix, no chopping) T2: 10 Hz, +300 mV offset"); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "1_T2_lna_v2.png"), dpi=150); plt.close(fig)
json.dump(res, open(os.path.join(OUT, "step1_v2.json"), "w"), indent=1)
