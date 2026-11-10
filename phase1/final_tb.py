"""Final Phase-1 runs on the SCHEMATIC netlist of AFE_lib/tb_ota (created by OCEAN createNetlist)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runsim, ota_design as od

NET = "/home/ISDL_UG_86/Desktop/cmos65/sim/afe/tb_ota_sch.scs"
P = od.P
SINGLE = ["M1", "M2", "M5", "M6", "M7", "M8", "M9", "M10"]
COMP = {"MBP": 2, "M0\\<0\\>": 2, "MBN": 5, "M3\\<0\\>": 5, "M4\\<0\\>": 5}
PAR = ["ids", "gm", "gds", "vgs", "vds", "vth", "vdsat", "region", "cgg"]


def saves(b="I1"):
    names = ["%s.%s" % (b, s) for s in SINGLE]
    for c, ns in COMP.items():
        names += ["%s.%s.M%d" % (b, c, k) for k in range(ns)]
    return " ".join("%s:%s" % (n, p) for n in names for p in PAR)


def control():
    return "\n".join([
        "simulator lang=spectre", "global 0",
        'include "/cad/FOUNDRY/analog/180nm/models/spectre/gpdk.scs" section=NN',
        "parameters VDD=%g VCM=%g VCN=%g VCP=%g IREF=%g CL=5p LBIG=1e16 VS=0.9" % (
            P["VDD"], P["VCM"], P["VCN"], P["VCP"], P["IREF"]),
        'include "%s"' % NET,
        "simulatorOptions options reltol=1e-5 vabstol=1e-8 iabstol=1e-15 temp=27 tnom=27 gmin=1e-15",
        "save vout1 vin1 vip1 vout2 vout3 vin3 vs3 vout4 vout5 I1.tail I1.f1 I1.f2 I1.x1 I1.p1 I1.p2 nbn1 nbp1 "
        "VDD1:p VDD2:p VDD3:p VDD4:p VDD5:p " + saves(),
        "op dc",
        "nz (vout1 0) noise start=0.1 stop=100k dec=40 iprobe=VIP1",
        "swc sweep param=CL values=[1p 2p 5p] {",
        "  ac1 ac start=1m stop=100M dec=40",
        "  stb1 stb start=1m stop=100M dec=40 probe=IPRB",
        "}",
        "dcs dc param=VS start=0.7 stop=1.1 step=0.5m",
    ])


if __name__ == "__main__":
    import subprocess
    subprocess.run(["ssh", "eda-uni", "cp ~/simulation/tb_ota/spectre/schematic/netlist/netlist ~/Desktop/cmos65/sim/afe/tb_ota_sch.scs"], check=True)
    runsim.run("final", control())
