"""Prototype: DC op + AC of one LNA (netlist level)."""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psf, runsim, lna_design as ld

def devs():
    out = []
    for grp, pre in [(ld.CORE, "I1.I0."), (ld.BIAS, "I1.I0.XB.")]:
        for n, (c, *_r) in grp.items():
            out += [pre + n] if c["ns"] == 1 else [pre + "%s_0" % n]
    return out

def net(over=None):
    sv = " ".join("%s:%s" % (d, p) for d in devs() for p in ["ids", "gm", "vds", "vdsat", "region", "cgg"])
    return "\n".join([ld.header(over),
        "VDD (vdd 0) vsource dc=VDD", "IREF (vdd iref1) isource dc=IREF", "VREF (vref 0) vsource dc=VREF",
        "VIP (vinp 0) vsource dc=VCM mag=0.5", "VIN (vinn 0) vsource dc=VCM mag=0.5 phase=180",
        "CL (vout 0) capacitor c=CL",
        "I1 (vinp vinn vref vout vdd 0 iref1) lna_cci",
        "save vout iref1 I1.ninv I1.nnon I1.I0.tail I1.I0.f1 I1.I0.f2 I1.I0.x1 I1.I0.p1 I1.I0.p2 I1.I0.nbn I1.I0.nbp I1.I0.vcp VDD:p " + sv,
        "op dc", "ac1 ac start=1m stop=1M dec=20"])

if __name__ == "__main__":
    rd = runsim.run("proto", net())
    op = psf.read(os.path.join(rd, "op.dc")); g = lambda k: float(np.atleast_1d(op[k])[0])
    print("I(VDD)=%.1f nA" % (abs(g("VDD:p")) * 1e9))
    print("  ".join("%s=%.3f" % (k.split(".")[-1], g(k)) for k in ["vout", "iref1", "I1.ninv", "I1.nnon", "I1.I0.tail", "I1.I0.f1", "I1.I0.f2", "I1.I0.x1", "I1.I0.p1", "I1.I0.p2", "I1.I0.nbn", "I1.I0.nbp", "I1.I0.vcp"]))
    for d in devs():
        p = lambda n: g("%s:%s" % (d, n)); i = abs(p("ids"))
        print("%-16s ID=%7.2fn gm/ID=%5.1f VDS=%.3f Vdsat=%.3f reg=%d" % (d.replace("I1.I0.", ""), i * 1e9, abs(p("gm")) / i, abs(p("vds")), abs(p("vdsat")), p("region")))
    ac = psf.read(os.path.join(rd, "ac1.ac")); f = ac["freq"]; A = 20 * np.log10(np.abs(ac["vout"]))
    Am = A.max(); i = np.argmax(A)
    fl = np.exp(np.interp(Am - 3, A[:i], np.log(f[:i]))); fh = np.exp(np.interp(-(Am - 3), -A[i:], np.log(f[i:])))
    print("midband %.2f dB  f_HP=%.3g Hz  f_LP=%.4g Hz" % (Am, fl, fh))
