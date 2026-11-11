"""Step 1 prototype: swing fix on the non-chopped LNA (lna_v2). op + margins (+ optional T2 THD sweep)."""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psf, runsim, lna3

DEVS = ["M1", "M2", "M3_0", "M3_4", "M5", "M6", "M7", "M8", "M9", "M10",
        "XB.MBN_0", "XB.MBS_0", "XB.MCP", "XB.MBP_0", "XB.MCN1", "XB.MCN2", "XB.MPV1_0"]
P = ["ids", "gm", "vds", "vdsat", "region", "vgs"]


def tb(cfg, tran_amps=None, tstop=2.0):
    sv = " ".join("I1.I0.%s:%s" % (d, p) for d in DEVS for p in P)
    L = [lna3.header({"VOS": 0.3}, c=cfg),
         "VDD (vdd 0) vsource dc=VDD", "IREF (vdd iref1) isource dc=IREF", "VREF (vref 0) vsource dc=VREF",
         "VIP (vinp 0) vsource type=sine dc=VCM+VOS sinedc=VCM+VOS ampl=AMP/2 freq=FSIG mag=0.5",
         "VIN (vinn 0) vsource type=sine dc=VCM sinedc=VCM ampl=AMP/2 freq=FSIG sinephase=180 mag=0.5 phase=180",
         "CL (vout 0) capacitor c=CL",
         "I1 (vinp vinn vref vout vdd 0 iref1) lna_v2",
         "save vout I1.I0.f1 I1.I0.f2 I1.I0.x1 I1.I0.p1 I1.I0.p2 I1.I0.vcn I1.I0.vcp I1.I0.nbp I1.I0.nbn I1.I0.tail VDD:p " + sv,
         "op dc", "ac1 ac start=1m stop=1M dec=10"]
    if tran_amps:
        L += ["swA sweep param=AMP values=[%s] {" % " ".join("%g" % a for a in tran_amps),
              "  tr tran stop=%g maxstep=100u strobeperiod=100u errpreset=conservative" % tstop, "}"]
    return "\n".join(L)


def report(rd):
    op = psf.read(os.path.join(rd, "op.dc")); g = lambda k: float(np.atleast_1d(op[k])[0])
    out = dict(I=abs(g("VDD:p")))
    print("I(VDD) = %.1f nA (excl IREF %.1f)" % (out["I"] * 1e9, out["I"] * 1e9 - 25))
    nodes = ["vout", "I1.I0.f1", "I1.I0.f2", "I1.I0.x1", "I1.I0.p1", "I1.I0.p2", "I1.I0.vcn", "I1.I0.vcp", "I1.I0.nbp", "I1.I0.nbn", "I1.I0.tail"]
    out["nodes"] = {k.split(".")[-1]: g(k) for k in nodes}
    print("  ".join("%s=%.3f" % kv for kv in out["nodes"].items()))
    out["dev"] = {}
    for d in DEVS:
        p = lambda n: g("I1.I0.%s:%s" % (d, n)); i = abs(p("ids"))
        out["dev"][d] = dict(id=i, gmid=abs(p("gm")) / i, vds=abs(p("vds")), vdsat=abs(p("vdsat")), vgs=abs(p("vgs")), reg=p("region"))
        print("%-10s ID=%7.2fn gm/ID=%5.1f VGS=%.3f VDS=%.3f Vdsat=%.3f margin=%+.3f reg=%d" % (
            d, i * 1e9, abs(p("gm")) / i, abs(p("vgs")), abs(p("vds")), abs(p("vdsat")), abs(p("vds")) - abs(p("vdsat")), p("region")))
    return out


if __name__ == "__main__":
    cfg = dict(lna3.CFG); cfg.update(json.loads(sys.argv[1]) if len(sys.argv) > 1 else {})
    amps = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    name = sys.argv[3] if len(sys.argv) > 3 else "s1"
    rd = runsim.run(name, tb(cfg, amps))
    report(rd)
