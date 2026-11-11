"""Phase-2 transient results: T1 (1 mV 10 Hz + 300 mV offset), T2 (THD vs amplitude), T3 (50 Hz CM), T4 (overload)."""
import os, json, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psf

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "plots")
res = {}


def spectrum(t, v, t0, t1):
    m = (t >= t0 - 1e-9) & (t < t1 - 1e-9)
    x = v[m] - v[m].mean(); N = len(x)
    X = np.abs(np.fft.rfft(x)) * 2 / N
    f = np.fft.rfftfreq(N, t[1] - t[0])
    return f, X


def amp_at(f, X, f0):
    i = np.argmin(abs(f - f0)); return X[max(i - 1, 0):i + 2].max()


def thd(t, v, f0, t0, t1, nh=10):
    f, X = spectrum(t, v, t0, t1)
    h = [amp_at(f, X, k * f0) for k in range(1, nh + 1)]
    return np.sqrt(np.sum(np.square(h[1:]))) / h[0], h


# ---- T1 / T3 from p2_tran (4 s, strobe 100 us)
r = psf.read(os.path.join(HERE, "raw", "p2_tran", "tr.tran.tran")); t = r["time"]
v1 = r["vout1"]; m = t >= 2.0
th1, h1 = thd(t, v1, 10, 2.0, 4.0)
res["T1"] = dict(dc=float(v1[m].mean()), amp=float(h1[0]), thd=float(th1), h=[float(x) for x in h1[:5]])
print("T1: output DC (2-4 s mean) = %.4f V, fundamental = %.2f mV (gain %.2f dB), THD = %.4f %% (h2=%.3g h3=%.3g V)" % (
    res["T1"]["dc"], h1[0] * 1e3, 20 * np.log10(h1[0] / 1e-3), th1 * 100, h1[1], h1[2]))
fig, ax = plt.subplots(2, 1, figsize=(9, 6))
ax[0].plot(t, v1); ax[0].set_ylabel("vout1 [V]"); ax[0].set_xlabel("time [s]")
ax[0].set_title("T1: 1 mV 10 Hz differential, +300 mV DC on vin+ (absorbed in op point), CL=2 pF"); ax[0].grid(alpha=0.3)
f, X = spectrum(t, v1, 2.0, 4.0)
ax[1].semilogy(f, X + 1e-12); ax[1].set_xlim(0, 120); ax[1].set_xlabel("Hz"); ax[1].set_ylabel("|Vout| [V]")
ax[1].set_title("spectrum 2-4 s, THD = %.3f %%" % (th1 * 100)); ax[1].grid(alpha=0.3)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "8_T1.png"), dpi=150); plt.close(fig)

v2 = r["vout2"]
f, X = spectrum(t, v2, 2.0, 4.0)
a50, a10 = amp_at(f, X, 50), amp_at(f, X, 10)
res["T3"] = dict(res50=float(a50), sig10=float(a10))
print("T3: residual 50 Hz at output = %.3g V (%.1f uV) for 100 mV CM input -> CM gain %.1f dB; 10 Hz signal = %.3f mV (100 uV in)" % (
    a50, a50 * 1e6, 20 * np.log10(a50 / 0.1), a10 * 1e3))
fig, ax = plt.subplots(2, 1, figsize=(9, 6))
ax[0].plot(t, v2); ax[0].set_ylabel("vout2 [V]"); ax[0].set_xlabel("time [s]"); ax[0].grid(alpha=0.3)
ax[0].set_title("T3: 100 mV 50 Hz common mode + 100 uV 10 Hz differential")
ax[1].semilogy(f, X + 1e-12); ax[1].set_xlim(0, 120); ax[1].set_xlabel("Hz"); ax[1].set_ylabel("|Vout| [V]"); ax[1].grid(alpha=0.3)
ax[1].set_title("spectrum 2-4 s: 10 Hz = %.2f mV, 50 Hz residual = %.1f uV" % (a10 * 1e3, a50 * 1e6))
fig.tight_layout(); fig.savefig(os.path.join(OUT, "8_T3.png"), dpi=150); plt.close(fig)

# ---- T2 THD sweep
p = os.path.join(HERE, "raw", "p2_thd")
if os.path.isdir(p):
    res["T2"] = []
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for k, A in enumerate([1, 3, 5, 8]):
        r2 = psf.read(os.path.join(p, "swA-%03d_tr.tran.tran" % k)); t2 = r2["time"]; v = r2["vout1"]
        th, h = thd(t2, v, 10, 1.0, 2.0)
        res["T2"].append(dict(amp_mV=A, thd=float(th), fund=float(h[0]), h2=float(h[1]), h3=float(h[2]),
                              vmin=float(v[t2 > 1].min()), vmax=float(v[t2 > 1].max())))
        ax.plot(t2[t2 > 1], v[t2 > 1], label="%d mV (THD %.2f %%)" % (A, th * 100))
    ax.set_xlabel("time [s]"); ax.set_ylabel("vout1 [V]"); ax.set_title("T2: 10 Hz, +300 mV offset, amplitude sweep"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "8_T2.png"), dpi=150); plt.close(fig)
    print("T2: amp  fund     h2        h3        THD     out range")
    for d in res["T2"]:
        print("    %d mV  %.4f V  %.3g  %.3g  %.3f %%  %.3f..%.3f V" % (d["amp_mV"], d["fund"], d["h2"], d["h3"], d["thd"] * 100, d["vmin"], d["vmax"]))

# ---- T4 overload recovery
p = os.path.join(HERE, "raw", "p2_t4long", "tr.tran.tran")
if os.path.exists(p):
    r4 = psf.read(p); t4 = r4["time"]; v4 = r4["vout4"]
    bad = np.where((t4 > 0.1) & (np.abs(v4 - 0.9) > 0.010))[0]
    trec = (t4[bad[-1]] - 0.1) if len(bad) and bad[-1] < len(t4) - 1 else float("nan")
    res["T4"] = dict(trec=float(trec), vmin=float(v4.min()), v_end=float(v4[-1]), t_end=float(t4[-1]))
    print("T4: 50 mV diff step at 0.1 s: output min %.3f V; back within 10 mV of VREF after %.2f s (end %.4f V at %.0f s)" % (
        v4.min(), trec, v4[-1], t4[-1]))
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(t4, v4); ax.axhspan(0.89, 0.91, color="C2", alpha=0.2, label="VREF +-10 mV")
    if np.isfinite(trec):
        ax.axvline(0.1 + trec, color="r", ls="--", label="recovered at t = %.2f s" % (0.1 + trec))
    ax.set_xlabel("time [s]"); ax.set_ylabel("vout4 [V]"); ax.set_title("T4: 50 mV differential step at t = 0.1 s (overload recovery)")
    ax.grid(alpha=0.3); ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "8_T4.png"), dpi=150); plt.close(fig)
json.dump(res, open(os.path.join(OUT, "tran_results.json"), "w"), indent=1)
