"""Phase-3 transient + PSS-steady-state results: T1/T2/T3 (chopped), reset recovery, ripple vs f_chop, offset vs switch mismatch,
clock waveforms."""
import os, json, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import psf
from thd import thd

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "plots"); RAW = os.path.join(HERE, "raw")
res = {}


def uni(t, v, dt):
    tu = np.arange(t[0], t[-1], dt); return tu, np.interp(tu, t, v)


def avg_period(t, v, T):
    """moving average over one chopper period (removes chopper ripple)."""
    n = max(1, int(round(T / (t[1] - t[0])))); k = np.ones(n) / n
    return np.convolve(v, k, mode="same")


def cross(x, y, lvl, rising):
    s = np.sign(y - lvl); i = np.where(np.diff(s) > 0 if rising else np.diff(s) < 0)[0]
    return [x[j] + (lvl - y[j]) * (x[j + 1] - x[j]) / (y[j + 1] - y[j]) for j in i]


# ---------------- clock waveforms (from PSS of the main run)
td = psf.read(os.path.join(RAW, "p3_main", "pss1.td.pss")); t = td["time"] - td["time"][0]
fig, ax = plt.subplots(2, 1, figsize=(9, 6))
for nm in ("c1", "c2", "o1", "o2", "o3"):
    ax[0].plot(t * 1e6, td[nm] + 0.0, label=nm)
ax[0].set_xlabel("t [us]"); ax[0].set_ylabel("V"); ax[0].legend(fontsize=8, ncol=5); ax[0].grid(alpha=0.3)
ax[0].set_title("Chopper clocks, one period (f_chop = 5 kHz): c1/c2 non-overlapping (CH1), o1/o2 overlapping (CH2), o3 = CH3")
T = 1 / 5e3; e0 = cross(t, td["c2"], 0.9, True)[0]; m = (t > e0 - 150e-9) & (t < e0 + 120e-9)
for nm in ("c1", "c2", "o1", "o2"):
    ax[1].plot((t[m] - e0) * 1e9, td[nm][m], ".-", ms=3, label=nm)
ax[1].set_xlabel("t - (c2 rising 50%) [ns]"); ax[1].set_ylabel("V"); ax[1].grid(alpha=0.3); ax[1].legend(fontsize=8)
ax[1].set_title("Zoom on the phase-1 -> phase-2 edge: c-gap (break-before-make) and o-overlap (make-before-break)")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "2_clocks.png"), dpi=150); plt.close(fig)
# measure the gap / overlap at the mid-supply crossings
def wrapgap(a_list, b_list):   # smallest (b - a) mod T
    return min(((b - a) % T) for a in a_list for b in b_list)
c1d, c2u = cross(t, td["c1"], 0.9, False), cross(t, td["c2"], 0.9, True)
c2d, c1u = cross(t, td["c2"], 0.9, False), cross(t, td["c1"], 0.9, True)
o1d, o2u = cross(t, td["o1"], 0.9, False), cross(t, td["o2"], 0.9, True)
o2d, o1u = cross(t, td["o2"], 0.9, False), cross(t, td["o1"], 0.9, True)
gap = min(wrapgap(c1d, c2u), wrapgap(c2d, c1u)); ovl = min(wrapgap(o2u, o1d), wrapgap(o1u, o2d))
tc2r, tc1f, to1f, to2r = gap, 0.0, ovl, 0.0
res["clk"] = dict(nonoverlap_ns=(tc2r - tc1f) * 1e9, overlap_ns=(to1f - to2r) * 1e9)
print("clocks: CH1 non-overlap gap = %.1f ns, CH2 overlap = %.1f ns (50 %% crossings)" % (res["clk"]["nonoverlap_ns"], res["clk"]["overlap_ns"]))

# ---------------- ripple vs f_chop (PSS steady state, VOSI = 0.5 mV in bench 5)
res["ripple"] = {}
fig, ax = plt.subplots(figsize=(8, 4.5))
for f in (5, 10, 20):
    p = os.path.join(RAW, "rip_%dk" % f, "pss1.td.pss")
    if not os.path.exists(p):
        print("missing", p); continue
    r = psf.read(p); tt = r["time"] - r["time"][0]; v5 = r["vout5"]
    res["ripple"][f] = dict(pp=float(v5.max() - v5.min()), dc=float(v5.mean()), dc1=float(r["vout1"].mean()))
    ax.plot(tt * f * 1e3, (v5 - v5.mean()) * 1e3, label="%d kHz: %.1f mVpp, DC %.4f V" % (f, res["ripple"][f]["pp"] * 1e3, v5.mean()))
    print("ripple f_chop=%2d kHz: %.2f mVpp, output DC %.4f V (bench without VOSI: %.4f V) -> offset-induced DC shift %.2f mV" % (
        f, res["ripple"][f]["pp"] * 1e3, v5.mean(), r["vout1"].mean(), (v5.mean() - r["vout1"].mean()) * 1e3))
ax.set_xlabel("t / T_chop"); ax.set_ylabel("vout5 - mean [mV]"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
ax.set_title("Output ripple with 0.5 mV input-pair offset (PSS steady state, one chopper period)")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "7_ripple_vs_fchop.png"), dpi=150); plt.close(fig)

# ---------------- residual offset from charge injection (PSS)
res["offset"] = {}
for nm, lab in (("off_nom", "nominal switches"), ("off_mm", "CH1A nmos 10 % wider")):
    p = os.path.join(RAW, nm, "pss1.td.pss")
    if os.path.exists(p):
        r = psf.read(p)
        res["offset"][lab] = dict(vout1=float(r["vout1"].mean()), vout5=float(r["vout5"].mean()), pp1=float(r["vout1"].max() - r["vout1"].min()),
                                  ninv=float(r["I1.ninv"].mean()), nnon=float(r["I1.nnon"].mean()))
        print("offset (%s): vout1 DC = %.4f V (offset %.2f mV wrt VREF), ripple %.2f mVpp, ninv=%.4f nnon=%.4f" % (
            lab, r["vout1"].mean(), (r["vout1"].mean() - 0.9) * 1e3, (r["vout1"].max() - r["vout1"].min()) * 1e3, r["I1.ninv"].mean(), r["I1.nnon"].mean()))

# ---------------- 1 s transient at 5 kHz: T1, T3, ripple waveform, reset
p = os.path.join(RAW, "p3_tran_5k", "tr.tran.tran")
if os.path.exists(p):
    r = psf.read(p); t = r["time"]; dt = 1 / 5e3 / 40
    tu, v1 = uni(t, r["vout1"], dt)
    th1, h1 = thd(tu, v1, 10, 0.5, 1.0)
    res["T1"] = dict(dc=float(v1[tu > 0.5].mean()), fund=float(h1[0]), thd=float(th1))
    print("T1 (5 kHz): output DC %.4f V, fundamental %.2f mV (gain %.2f dB), THD %.3f %%" % (v1[tu > 0.5].mean(), h1[0] * 1e3, 20 * np.log10(h1[0] / 1e-3), th1 * 100))
    fig, ax = plt.subplots(2, 1, figsize=(9, 6))
    ax[0].plot(tu, v1, lw=0.5); ax[0].set_xlabel("time [s]"); ax[0].set_ylabel("vout1 [V]"); ax[0].grid(alpha=0.3)
    ax[0].set_title("T1 chopped: 1 mV 10 Hz differential + 300 mV electrode offset, f_chop = 5 kHz, CL = 2 pF")
    m = (tu > 0.7) & (tu < 0.7 + 4 / 5e3); ax[1].plot((tu[m] - 0.7) * 1e3, v1[m] * 1e3); ax[1].set_xlabel("t - 0.7 s [ms]")
    ax[1].set_ylabel("vout1 [mV]"); ax[1].grid(alpha=0.3); ax[1].set_title("zoom: 4 chopper periods (residual ripple)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "8_T1.png"), dpi=150); plt.close(fig)
    _, v2 = uni(t, r["vout2"], dt)
    from thd import spectrum, amp_at
    f_, X = spectrum(tu, v2, 0.5, 1.0); a50, a10 = amp_at(f_, X, 50), amp_at(f_, X, 10)
    res["T3"] = dict(res50=float(a50), sig10=float(a10))
    print("T3: 50 Hz residual at output %.1f uV for 100 mV CM (CM gain %.1f dB); 10 Hz signal %.3f mV" % (a50 * 1e6, 20 * np.log10(a50 / 0.1), a10 * 1e3))
    fig, ax = plt.subplots(2, 1, figsize=(9, 6))
    ax[0].plot(tu, v2, lw=0.5); ax[0].set_xlabel("time [s]"); ax[0].set_ylabel("vout2 [V]"); ax[0].grid(alpha=0.3)
    ax[0].set_title("T3 chopped: 100 mV 50 Hz common mode + 100 uV 10 Hz differential")
    ax[1].semilogy(f_, X + 1e-12); ax[1].set_xlim(0, 120); ax[1].set_xlabel("Hz"); ax[1].grid(alpha=0.3)
    ax[1].set_title("spectrum 0.5-1 s: 10 Hz = %.2f mV, 50 Hz residual = %.1f uV" % (a10 * 1e3, a50 * 1e6))
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "8_T3.png"), dpi=150); plt.close(fig)
    # ripple waveform (bench 5, VOSI = 0.5 mV) - transient view
    _, v5 = uni(t, r["vout5"], dt); m = (tu > 0.9) & (tu < 0.9 + 4 / 5e3)
    res["ripple_tran_5k"] = float(v5[m].max() - v5[m].min())
    fig, ax = plt.subplots(figsize=(8, 4)); ax.plot((tu[m] - 0.9) * 1e3, v5[m] * 1e3)
    ax.set_xlabel("t - 0.9 s [ms]"); ax.set_ylabel("vout5 [mV]"); ax.grid(alpha=0.3)
    ax.set_title("Transient ripple, 0.5 mV offset, f_chop = 5 kHz: %.1f mVpp" % (res["ripple_tran_5k"] * 1e3))
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "7_ripple_tran_5k.png"), dpi=150); plt.close(fig)
    # reset test (bench 4): step at 0.2 s, RST 1 ms at 0.21 s
    _, v4 = uni(t, r["vout4"], dt); v4a = avg_period(tu, v4, 1 / 5e3)
    pre = v4a[(tu > 0.15) & (tu < 0.199)].mean(); post = v4a[(tu > 0.30) & (tu < 0.95)].mean()
    bad = np.where((tu > 0.2) & (np.abs(v4a - 0.9) > 0.010) & (tu < 0.98))[0]
    trec = tu[bad[-1]] - 0.2 if len(bad) else float("nan")
    res["reset"] = dict(trec=float(trec), pre=float(pre), post=float(post), step=float(post - pre), vmin=float(v4.min()))
    print("reset: recovery to +-10 mV of VREF %.2f ms after the step (RST at +10 ms, 1 ms); output DC before %.4f V, after %.4f V -> "
          "charge-injection step %.2f mV" % (trec * 1e3, pre, post, (post - pre) * 1e3))
    fig, ax = plt.subplots(2, 1, figsize=(9, 6))
    ax[0].plot(tu, v4, lw=0.5, label="vout4"); ax[0].plot(tu, v4a, label="1-period average"); ax[0].axhspan(0.89, 0.91, color="C2", alpha=0.2)
    ax[0].set_xlabel("time [s]"); ax[0].set_ylabel("V"); ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)
    ax[0].set_title("Overload (50 mV step at 0.2 s) + 1 ms reset pulse at 0.21 s: recovery %.1f ms, release step %.2f mV" % (trec * 1e3, (post - pre) * 1e3))
    m = (tu > 0.195) & (tu < 0.24); ax[1].plot((tu[m] - 0.2) * 1e3, v4[m], lw=0.6); ax[1].plot((tu[m] - 0.2) * 1e3, v4a[m])
    _, rs = uni(t, r["rst4"], dt); ax[1].plot((tu[m] - 0.2) * 1e3, 0.1 + rs[m] * 0.2, "k", lw=0.8, label="RST (scaled)")
    ax[1].set_xlabel("t - 0.2 s [ms]"); ax[1].grid(alpha=0.3); ax[1].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "4_reset_recovery.png"), dpi=150); plt.close(fig)

# ---------------- T2 THD sweep (5 kHz, 1 s each)
p = os.path.join(RAW, "p3_thd")
if os.path.isdir(p):
    res["T2"] = []
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for k, A in enumerate([1, 3, 5, 8]):
        fn = os.path.join(p, "sw-%03d_tr.tran.tran" % k)
        if not os.path.exists(fn):
            continue
        r = psf.read(fn); tu, v = uni(r["time"], r["vout1"], 1 / 5e3 / 40)
        th, h = thd(tu, v, 10, 0.5, 1.0); m = tu > 0.5
        res["T2"].append(dict(amp_mV=A, thd=float(th), fund=float(h[0]), vmin=float(v[m].min()), vmax=float(v[m].max())))
        ax.plot(tu[m], v[m], lw=0.5, label="%d mV (THD %.3f %%)" % (A, th * 100))
        print("T2 %d mV: fund %.4f V THD %.3f %% out %.3f..%.3f V" % (A, h[0], th * 100, v[m].min(), v[m].max()))
    ax.set_xlabel("time [s]"); ax.set_ylabel("vout1 [V]"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
    ax.set_title("T2 chopped (f_chop = 5 kHz): 10 Hz, +300 mV offset")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "8_T2.png"), dpi=150); plt.close(fig)

res["natural"] = json.load(open(os.path.join(OUT, "natural.json")))
json.dump(res, open(os.path.join(OUT, "tran_results.json"), "w"), indent=1, default=float)
