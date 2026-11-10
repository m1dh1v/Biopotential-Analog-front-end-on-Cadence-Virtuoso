"""Pseudo-resistor characterization: element across (0.9+dV, 0.9). Sizes x temperatures."""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psf, runsim, lna_design as ld

SIZES = [(1, 1), (0.4, 4), (0.4, 10), (0.4, 20)]
def net(W, L):
    return "\n".join([ld.header({"WPR": W * 1e-6, "LPR": L * 1e-6}, opts="reltol=1e-6 vabstol=1e-9 iabstol=1e-20 gmin=1e-20"),
        "parameters DV=0", "VB (b 0) vsource dc=0.9", "VA (a 0) vsource dc=0.9+DV", "X (a b) pseudo_r", "save VA:p",
        "swT sweep param=temp values=[0 27 37 80] {", "  sw dc param=DV start=-1 stop=1 step=1m", "}"])
if __name__ == "__main__":
    res = {}
    for W, L in SIZES:
        tag = "pr_%gx%g" % (W, L)
        rd = runsim.run(tag.replace(".", "p"), net(W, L), quiet=True)
        for k, T in enumerate([0, 27, 37, 80]):
            r = psf.read(os.path.join(rd, "swT-%03d_sw.dc" % k)); dv = r["DV"]; i = -r["VA:p"]
            R = np.gradient(dv, i)
            R0 = np.interp(0, dv, R)
            if T == 27:
                Rs = {x: np.interp(x, dv, R) for x in (-0.5, -0.3, -0.1, 0.1, 0.3, 0.5)}
                print("%-10s T=27  R(0)=%.3g  " % (tag, R0) + "  ".join("R(%+.1f)=%.2g" % kv for kv in Rs.items()))
            res[(W, L, T)] = R0
        print("           R(0) vs T: " + "  ".join("%dC: %.3g" % (T, res[(W, L, T)]) for T in [0, 27, 37, 80]) +
              "   f_HP(Cf=200f) @37C = %.3g Hz" % (1 / (2 * np.pi * res[(W, L, 37)] * 200e-15)))
