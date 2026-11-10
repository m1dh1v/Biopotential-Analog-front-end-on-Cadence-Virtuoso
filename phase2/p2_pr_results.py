import os, numpy as np, psf, json
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); RD = os.path.join(HERE, "raw", "p2_pseudo_r")
Ts = [0, 27, 37, 80]; res = {}
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.6))
for k, T in enumerate(Ts):
    r = psf.read(os.path.join(RD, "swT-%03d_sw.dc" % k)); dv = r["DV"]; i = -r["VA:p"]
    R = np.gradient(dv, i)
    a1.semilogy(dv, np.abs(i), label="%d C" % T); a2.semilogy(dv, np.abs(R), label="%d C" % T)
    res[T] = {"R0": float(np.interp(0, dv, R))}
    if T == 27:
        res["table"] = {x: float(np.interp(x, dv, R)) for x in (-0.5, -0.3, -0.1, 0.0, 0.1, 0.3, 0.5)}
        res["I"] = {x: float(np.interp(x, dv, i)) for x in (-0.5, -0.3, -0.1, 0.1, 0.3, 0.5)}
a1.set_xlabel("dV = V(a) - V(b) [V]  (V(b) = 0.9 V)"); a1.set_ylabel("|I| [A]"); a1.set_title("pseudo_r I-V (2 x pmos 0.4u/4u)")
a2.set_xlabel("dV [V]"); a2.set_ylabel("R = dV/dI [ohm]"); a2.set_title("small-signal resistance")
for a in (a1, a2): a.grid(True, which="both", alpha=0.3); a.legend()
fig.tight_layout(); fig.savefig(os.path.join(HERE, "plots", "2_pseudo_r_IV_R.png"), dpi=150)
print("R (27C): " + "  ".join("dV=%+.1f: %.3g" % kv for kv in res["table"].items()))
print("R(0) vs T: " + "  ".join("%dC: %.3g" % (T, res[T]["R0"]) for T in Ts))
print("chain of 6 per path: R(0)= " + "  ".join("%dC: %.3g" % (T, 6 * res[T]["R0"]) for T in Ts))
json.dump(res, open(os.path.join(HERE, "plots", "pseudo_r.json"), "w"), indent=1)
