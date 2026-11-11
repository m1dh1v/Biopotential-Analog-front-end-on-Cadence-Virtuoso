"""Step 2 prototype: chopped LNA (lna_chop) - clock check, short transient, PSS/PAC/Pnoise."""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psf, runsim, lna3


def bench(over=None, kw=None, static=False, pss=True, tran=None, extra=()):
    over = over or {}; kw = kw or {}
    L = [lna3.header(over, **kw)] + lna3.clocks(static) + [
        "VDD (vdd 0) vsource dc=VDD", "IREF (vdd iref1) isource dc=IREF", "VREF (vref 0) vsource dc=VREF",
        "VIP (vinp 0) vsource type=sine dc=VCM+VOS sinedc=VCM+VOS ampl=AMP/2 freq=FSIG mag=0.5 pacmag=0.5",
        "VIN (vinn 0) vsource type=sine dc=VCM sinedc=VCM ampl=AMP/2 freq=FSIG sinephase=180 mag=0.5 phase=180 pacmag=0.5 pacphase=180",
        "CL (vout 0) capacitor c=CL",
        "I1 (vinp vinn vref vout vdd 0 iref1 %s) lna_chop" % lna3.CLK,
        "save vout I1.ninv I1.nnon I1.I0.g1 I1.I0.g2 I1.I0.f1 I1.I0.f2 I1.I0.s5 I1.I0.s6 c1 c2 o1 o2 VDD:p"]
    L += list(extra)
    return "\n".join(L)


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "pss":
        ex = ["pss1 pss fund=FCH harms=20 tstab=5/FCH errpreset=conservative saveinit=yes",
              "pac1 pac start=0.1 stop=5k dec=10 sweeptype=absolute maxsideband=10",
              "pn1 (vout 0) pnoise start=0.1 stop=5k dec=10 sweeptype=absolute maxsideband=30 noisetype=timeaverage"]
        rd = runsim.run("s2_pss", bench({"AMP": 0}, extra=ex))
