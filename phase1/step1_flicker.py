"""Flicker comparison: NMOS vs PMOS, W/L=20u/2u, ID=100nA, |VDS|=0.9 V. Input-referred gate noise."""
import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psf

HERE = os.path.dirname(os.path.abspath(__file__))
# b3v3 noise struct field order: rd.src rd.xf2 rd.out rs.src rs.xf2 rs.out id.src id.xf2 id.out fn.src fn.xf2 fn.out totalsrc total
I_ID, I_FN = 8, 11
fig, ax = plt.subplots(figsize=(7, 4.6))
rows = []
for tag, inst, col in [("nN", "MN", "C0"), ("nP", "MP", "C3")]:
    r = psf.read(os.path.join(HERE, "raw", "flick", tag + ".noise"))
    f = r["freq"]; vin = np.abs(r["in"]); g2 = np.abs(r["gain"]) ** 2
    S = vin ** 2
    st = np.array(r[inst])
    th = st[:, I_ID] / g2; fl = st[:, I_FN] / g2
    # corner: flicker part = thermal (channel) part
    d = np.log(fl) - np.log(th)
    k = np.where(np.diff(np.sign(d)) != 0)[0][0]
    fc = np.exp(np.interp(0, [d[k + 1], d[k]], [np.log(f[k + 1]), np.log(f[k])]))
    vals = [np.exp(np.interp(np.log(x), np.log(f), np.log(S))) for x in (1, 10, 1e3)]
    gm = np.sqrt(g2[0])
    rows.append((inst, gm, vals, fc, th[-1]))
    ax.loglog(f, vin, col, label="%s total (input-ref.)" % ("NMOS" if inst == "MN" else "PMOS"))
    ax.loglog(f, np.sqrt(fl), col + ":", lw=1)
    ax.axvline(fc, color=col, ls="--", lw=0.8)
ax.set_xlabel("Frequency [Hz]"); ax.set_ylabel("Input-referred gate noise [V/rtHz]")
ax.set_title("W/L = 20u/2u, ID = 100 nA, |VDS| = 0.9 V  (dotted: 1/f part, dashed: corner)", fontsize=9)
ax.grid(True, which="both", alpha=0.3); ax.legend(fontsize=8); ax.set_xlim(0.1, 1e7)
fig.tight_layout(); fig.savefig(os.path.join(HERE, "plots", "1e_flicker_nmos_pmos.png"), dpi=150)

print("dev  gm[uS]   S(1Hz) V2/Hz (V/rtHz)      S(10Hz)                 S(1kHz)                 fcorner   white floor")
for inst, gm, v, fc, wt in rows:
    print("%s  %.3f  " % (inst, gm * 1e6) + "  ".join("%.3e (%.1f nV/rtHz)" % (x, np.sqrt(x) * 1e9) for x in v)
          + "  %.1f Hz  %.1f nV/rtHz" % (fc, np.sqrt(wt) * 1e9))
