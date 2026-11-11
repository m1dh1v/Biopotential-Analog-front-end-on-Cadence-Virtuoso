"""Phase-3 final simulations on the SCHEMATIC netlists (AFE_lib/tb_lna_v2, AFE_lib/tb_lna_chop)."""
import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runsim

R = "/home/ISDL_UG_86/Desktop/cmos65/sim/afe"
NETS = {"tb_lna_v2": R + "/tb_lna_v2_sch.scs", "tb_lna_chop": R + "/tb_lna_chop_sch.scs",
        "tb_lna": R + "/tb_lna_sch.scs"}
BASE = dict(VDD=1.8, VCM=0.9, VREF=0.9, IREF=25e-9, CL=2e-12, LIN=1e-6, WINF=1e-6, WS1A=0.8e-6, VOS=0, AMP=0, FSIG=10,
            VCMA=0, VDA=0, VSTEP=0, TSTEP=10e-3, TRD=10e-3, TRW=1e-3, RSTEN=0, VOSI=0, FCH=5e3, TNO=30e-9, TOV=30e-9,
            TR=5e-9, VSTEP6=0, STAT=0, CH3EN=1, WCIN=141.22e-6, LCIN1=141.22e-6, WCF=13.943e-6, DV=0)
OPTS = "reltol=1e-5 vabstol=1e-8 iabstol=1e-15 gmin=1e-15"


def copy_nets():
    for c in ("tb_lna_v2", "tb_lna_chop"):
        subprocess.run(["ssh", "eda-uni", "cp ~/simulation/%s/spectre/schematic/netlist/netlist %s" % (c, NETS[c])], check=True)


def hdr(cell, over=None, opts=OPTS):
    p = dict(BASE); p.update(over or {})
    if cell == "tb_lna_v2":
        p["LIN"] = over.get("LIN", 4e-6) if over else 4e-6
    return "\n".join(["simulator lang=spectre", "global 0",
                      'include "/cad/FOUNDRY/analog/180nm/models/spectre/gpdk.scs" section=NN',
                      "parameters " + " ".join("%s=%g" % kv for kv in p.items()),
                      'include "%s"' % NETS[cell],
                      "simulatorOptions options %s temp=27 tnom=27" % opts])


V2DEVS = ["M1", "M2", "M5", "M6", "M7", "M8", "M9", "M10"] + ["M3\<0\>.M%d" % k for k in range(5)] + \
         ["M4\<0\>.M%d" % k for k in range(5)] + ["XB.MCN1", "XB.MCN2", "XB.MCP"]
PAR = ["ids", "gm", "gds", "vgs", "vds", "vth", "vdsat", "region", "cgg"]


def run_v2():
    sv = " ".join("I1.I0.%s:%s" % (d, p) for d in V2DEVS for p in PAR)
    t = "\n".join([hdr("tb_lna_v2", {"VOS": 0.3}),
                   "save vout1 VDD1:p IREF1:p I1.I0.f1 I1.I0.f2 I1.I0.x1 I1.I0.p1 I1.I0.p2 I1.I0.vcn I1.I0.vcp I1.I0.nbp iref1 "
                   "I1.I0.tail I1.I0.XB.vcm1 I1.ninv I1.nnon " + sv,
                   "op dc", "ac1 ac start=1m stop=1M dec=20", "nz (vout1 0) noise start=10m stop=100k dec=20",
                   "swA sweep param=AMP values=[1m 3m 5m 8m] {",
                   "  tr tran stop=2 maxstep=100u strobeperiod=100u errpreset=conservative", "}"])
    return runsim.run("p3_v2", t)



SAVE = ("save vout1 vout2 vout4 vout5 vout6 VDD1:p VDD6:p VIP1:p VIN1:p I1.ninv I1.nnon I1.vfb I1.I0.g1 I1.I0.g2 I1.I0.f1 I1.I0.f2 "
        "I1.I0.s5 I1.I0.s6 I1.I0.d1 I1.I0.p1 I1.I0.q9 c1 c2 o1 o2 o3 "
        "VKc1:p VKc1b:p VKc2:p VKc2b:p VKo1:p VKo1b:p VKo2:p VKo2b:p VKo3:p VKo3b:p VKo4:p VKo4b:p")
PSS = "pss1 pss fund=FCH harms=20 tstab=5/FCH errpreset=conservative"
PAC = "pac1 pac start=0.1 stop=100k dec=20 sweeptype=absolute maxsideband=10"
PN = "pn%s (vout%s 0) pnoise start=0.1 stop=100k dec=20 sweeptype=absolute maxsideband=30 noisetype=timeaverage"


def run_main(name="p3_main", over=None, extra_pn6=True, pstb=True, fc=True, temps=(37,)):
    L = [hdr("tb_lna_chop", over), SAVE, PSS, PAC, PN % ("1", "1")]
    if extra_pn6:
        L.append(PN % ("6", "6"))
    if fc:
        L.append("pnfc (vout1 0) pnoise start=FCH*0.2 stop=FCH*2 lin=360 sweeptype=absolute maxsideband=30 noisetype=timeaverage")
    if pstb:
        L.append("pstb1 pstb start=0.1 stop=1M dec=20 probe=I1.IPRB maxsideband=10")
    for T in temps:
        L += ["t%d alter param=temp value=%d" % (T, T), "pss%d pss fund=FCH harms=20 tstab=5/FCH errpreset=conservative" % T,
              "pac%d pac start=0.1 stop=100k dec=20 sweeptype=absolute maxsideband=10" % T]
    return runsim.run(name, "\n".join(L))


def run_static(name="p3_static", over=None):
    o = dict(STAT=1); o.update(over or {})
    L = [hdr("tb_lna_chop", o), SAVE + " I1.I0.M1:cgg I1.I0.M1:gm I1.I0.M1:ids I1.I0.M2:cgg",
         "op dc", "ac1 ac start=0.1 stop=100k dec=20", "nz (vout1 0) noise start=0.1 stop=100k dec=20",
         "stb1 stb start=0.1 stop=10M dec=20 probe=I1.IPRB"]
    return runsim.run(name, "\n".join(L))


TSAVE = "save vout1 vout2 vout4 vout5 vout6 vinp1 vinn1 rst4 I1.ninv I1.nnon I4.ninv I4.nnon c1 o1"
TBASE = dict(AMP=1e-3, VOS=0.3, VCMA=0.1, VDA=100e-6, VOSI=0.5e-3, VSTEP=50e-3, TSTEP=0.2, TRD=10e-3, TRW=1e-3, RSTEN=1)


def run_tran(name, fch, tstop, over=None, sweep=None):
    o = dict(TBASE); o["FCH"] = fch; o.update(over or {})
    an = "tr tran stop=%g maxstep=%g strobeperiod=%g errpreset=moderate" % (tstop, 1 / (fch * 20), 1 / (fch * 40))
    L = [hdr("tb_lna_chop", o), TSAVE]
    if sweep:
        L += ["sw sweep param=%s values=[%s] {" % (sweep[0], " ".join("%g" % v for v in sweep[1])), "  " + an, "}"]
    else:
        L.append(an)
    return runsim.run(name, "\n".join(L))


def run_natural(name="p3_natural", tstop=40.0):
    """natural (no reset) overload recovery of NPR=10 (bench 4) and NPR=6 (bench 6), clocks frozen (STAT=1)."""
    o = dict(STAT=1, VSTEP=50e-3, VSTEP6=50e-3, TSTEP=0.1, RSTEN=0)
    L = [hdr("tb_lna_chop", o), "save vout4 vout6",
         "tr tran stop=%g maxstep=2m errpreset=conservative" % tstop]
    return runsim.run(name, "\n".join(L))


def run_pss_point(name, over, pn6=False):
    return run_main(name, over, extra_pn6=pn6, pstb=False, fc=False, temps=())


if __name__ == "__main__":
    what = sys.argv[1]
    copy_nets()
    if what == "v2":
        run_v2()
    elif what == "main":
        run_main()
    elif what == "static":
        run_static()
    elif what == "tran":
        fch = float(sys.argv[2]); run_tran("p3_tran_%dk" % int(fch / 1e3), fch, float(sys.argv[3]))
    elif what == "thd":
        run_tran("p3_thd", 5e3, 1.0, sweep=("AMP", [1e-3, 3e-3, 5e-3, 8e-3]))
    elif what == "offset":
        run_tran("p3_off_nom", 5e3, 0.2, dict(VOSI=0, AMP=0, VOS=0, VCMA=0, VDA=0, VSTEP=0, RSTEN=0))
        run_tran("p3_off_mm", 5e3, 0.2, dict(VOSI=0, AMP=0, VOS=0, VCMA=0, VDA=0, VSTEP=0, RSTEN=0, WS1A=0.88e-6))
    elif what == "natural":
        run_natural()
    elif what == "psso":  # PSS only: name json-overrides
        import json; runsim.run(sys.argv[2], "\n".join([hdr("tb_lna_chop", json.loads(sys.argv[3])), SAVE,
                                                          "pss1 pss fund=FCH harms=50 tstab=5/FCH errpreset=conservative"]))
    elif what == "pss":   # name json-overrides
        import json; run_pss_point(sys.argv[2], json.loads(sys.argv[3]))
