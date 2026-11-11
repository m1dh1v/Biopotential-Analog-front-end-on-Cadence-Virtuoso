"""Phase-2 final simulations on the SCHEMATIC netlists of AFE_lib/tb_lna and AFE_lib/tb_pseudo_r."""
import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runsim

R = "/home/ISDL_UG_86/Desktop/cmos65/sim/afe"
NETS = {"tb_lna": R + "/tb_lna_sch.scs", "tb_pseudo_r": R + "/tb_pseudo_r_sch.scs"}
CIN = {"20p": dict(WCIN=141.22e-6, LCIN1=141.22e-6, WCF=13.943e-6),
       "10p": dict(WCIN=99.80e-6, LCIN1=99.80e-6, WCF=9.802e-6)}
BASE = dict(VDD=1.8, VCM=0.9, VREF=0.9, IREF=25e-9, CL=2e-12, LIN=4e-6, VOS=0, AMP=1e-3, FSIG=10,
            VCMA=0.1, VDA=100e-6, VSTEP=50e-3, DV=0)
OPTS = "reltol=1e-5 vabstol=1e-8 iabstol=1e-15 gmin=1e-15"


def copy_nets():
    for c, dst in NETS.items():
        subprocess.run(["ssh", "eda-uni", "cp ~/simulation/%s/spectre/schematic/netlist/netlist %s" % (c, dst)], check=True)


def hdr(cell, over=None, opts=OPTS):
    p = dict(BASE); p.update(CIN["20p"]); p.update(over or {})
    return "\n".join(["simulator lang=spectre", "global 0",
                      'include "/cad/FOUNDRY/analog/180nm/models/spectre/gpdk.scs" section=NN',
                      "parameters " + " ".join("%s=%g" % kv for kv in p.items()),
                      'include "%s"' % NETS[cell],
                      "simulatorOptions options %s temp=27 tnom=27" % opts])


OTA_DEVS = ["M1", "M2", "M5", "M6", "M7", "M8", "M9", "M10", "M0\\<0\\>.M1", "M0\\<0\\>.M0",
            "M3\\<0\\>.M0", "M4\\<0\\>.M0", "XB.MC", "XB.MCP", "XB.MBN.M0", "XB.MBS.M0", "XB.MBP.M1", "XB.MBP.M0"]
PAR = ["ids", "gm", "gds", "vgs", "vds", "vth", "vdsat", "region", "cgg"]


def save_op(b="I1"):
    return " ".join("%s.I0.%s:%s" % (b, d, p) for d in OTA_DEVS for p in PAR)


def run_pseudo_r():
    t = "\n".join([hdr("tb_pseudo_r", opts="reltol=1e-6 vabstol=1e-9 iabstol=1e-20 gmin=1e-20"), "save VA:p",
                   "swT sweep param=temp values=[0 27 37 80] {", "  sw dc param=DV start=-1 stop=1 step=1m", "}"])
    return runsim.run("p2_pseudo_r", t)


def run_geometry(cin):
    t = "\n".join([hdr("tb_lna", CIN[cin]),
                   "save vout1 VDD1:p I1.I0.M1:cgg I1.I0.M1:gm I1.I0.M1:ids I1.I0.M2:cgg",
                   "swL sweep param=LIN values=[1u 2u 4u] {",
                   "  op dc",
                   "  ac1 ac start=1m stop=1M dec=20",
                   "  nz (vout1 0) noise start=10m stop=100k dec=20",
                   "}"])
    return runsim.run("p2_geo_%s" % cin, t)


def run_main(LIN):
    t = "\n".join([hdr("tb_lna", {"LIN": LIN}),
                   "save vout1 vout2 vout3 vout4 I1.ninv I1.nnon I1.vfb I1.I0.tail I1.I0.f1 I1.I0.f2 I1.I0.x1 I1.I0.p1 "
                   "I1.I0.p2 I1.I0.nbn I1.I0.nbp I1.I0.vcp iref1 VDD1:p VDD2:p VDD3:p VDD4:p IREF1:p " + save_op(),
                   "op dc",
                   "nz (vout1 0) noise start=10m stop=100k dec=20",
                   "swc sweep param=CL values=[2p 5p] {",
                   "  ac1 ac start=1m stop=1M dec=20",
                   "  stb1 stb start=1m stop=10M dec=20 probe=I1.IPRB",
                   "}",
                   "t0 alter param=temp value=0", "ac_T0 ac start=1m stop=1M dec=20",
                   "t37 alter param=temp value=37", "ac_T37 ac start=1m stop=1M dec=20",
                   "t80 alter param=temp value=80", "ac_T80 ac start=1m stop=1M dec=20",
                   "t27 alter param=temp value=27",
                   "mm alter param=LCIN1 value=WCIN*1.001", "ac_mm ac start=1m stop=1M dec=20"])
    return runsim.run("p2_main", t)


def run_tran(LIN, amps=None, tstop=4.0, name="p2_tran"):
    sweep = amps is not None
    lines = [hdr("tb_lna", {"LIN": LIN, "VOS": 0.3}),
             "save vout1 vout2 vout4 vinp1 vinn1 vinp2 vinn2 vinp4 vinn4"]
    an = "tr tran stop=%g maxstep=100u strobeperiod=100u errpreset=conservative" % tstop
    if sweep:
        lines += ["swA sweep param=AMP values=[%s] {" % " ".join("%gm" % (a * 1e3) for a in amps), "  " + an, "}"]
    else:
        lines.append(an)
    return runsim.run(name, "\n".join(lines))


if __name__ == "__main__":
    what = sys.argv[1]
    copy_nets()
    if what == "pr":
        run_pseudo_r()
    elif what == "geo":
        run_geometry("20p"); run_geometry("10p")
    elif what == "main":
        run_main(float(sys.argv[2]))
    elif what == "tran":
        run_tran(float(sys.argv[2]), tstop=float(sys.argv[3]) if len(sys.argv) > 3 else 4.0)
    elif what == "thd":
        run_tran(float(sys.argv[2]), amps=[1e-3, 3e-3, 5e-3, 8e-3], tstop=2.0, name="p2_thd")
