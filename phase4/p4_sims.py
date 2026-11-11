"""Phase-4 final simulations on the SCHEMATIC netlists of AFE_lib/tb_lpf and AFE_lib/tb_chain."""
import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runsim

R = "/home/ISDL_UG_86/Desktop/cmos65/sim/afe"
NETS = {"tb_lpf": R + "/tb_lpf_sch.scs", "tb_chain": R + "/tb_chain_sch.scs"}
IBN = 1.27e-9
BASE = dict(VDD=1.8, VCM=0.9, VREF=0.9, IREF=25e-9, CL=2e-12, LIN=4e-6, WCIN=141.22e-6, LCIN1=141.22e-6, WCF=13.943e-6,
            VOS=0, AMP=0, FSIG=30, IB=IBN, WCL=189.4e-6, VSTEP=0, TSTEP=0.05, VA1=0, F1=30, VA2=0, F2=37.5)
OPTS = "reltol=1e-6 vabstol=1e-9 iabstol=1e-18 gmin=1e-15"
IBS = [0.85e-9, 1.27e-9, 2.5e-9, 4.2e-9, 6.3e-9, 8.5e-9]


def copy_nets():
    for c, dst in NETS.items():
        subprocess.run(["ssh", "eda-uni", "cp ~/simulation/%s/spectre/schematic/netlist/netlist %s" % (c, dst)], check=True)


def hdr(cell, over=None, temp=27):
    p = dict(BASE); p.update(over or {})
    return "\n".join(["simulator lang=spectre", "global 0",
                      'include "/cad/FOUNDRY/analog/180nm/models/spectre/gpdk.scs" section=NN',
                      "parameters " + " ".join("%s=%g" % kv for kv in p.items()),
                      'include "%s"' % NETS[cell],
                      "simulatorOptions options %s temp=%g tnom=27" % (OPTS, temp)])


def tr(stop, f):
    return "tran stop=%g maxstep=%g errpreset=conservative" % (stop, 1 / f / 400)


def run_main():
    """op, AC, noise, tuning sweep, temperature (AC + noise) on bench 1."""
    L = [hdr("tb_lpf"), "save vout1 vin1 vout2 vout3 VDD1:p VIN1:p X1.v1",
         "op dc oppoint=rawfile", "ac1 ac start=0.1 stop=100k dec=40", "nz (vout1 0) noise start=0.1 stop=100k dec=20",
         "swIB sweep param=IB values=[%s] {" % " ".join("%g" % v for v in IBS), "  opi dc", "  aci ac start=0.1 stop=100k dec=20",
         "  nzi (vout1 0) noise start=0.1 stop=100k dec=10", "}"]
    for T in (0, 37, 80):
        L += ["t%d alter param=temp value=%d" % (T, T), "opT%d dc" % T, "acT%d ac start=0.1 stop=100k dec=20" % T,
              "nzT%d (vout1 0) noise start=0.1 stop=100k dec=10" % T]
    return runsim.run("p4_main", "\n".join(L))


def run_thd(temp=27, name="p4_thd"):
    L = [hdr("tb_lpf", {"FSIG": 30}, temp), "save vout1 vin1 VDD1:p",
         "swA sweep param=AMP values=[0.05 0.125 0.25 0.4] {", "  tr " + tr(0.3, 30), "}"]
    return runsim.run(name, "\n".join(L))


def run_tran():
    """bench 2: step; bench 3: two-tone IM3 (30 + 37.5 Hz, 0.25 Vpp each) - then 1 Hz + 40 Hz."""
    L = [hdr("tb_lpf", {"VSTEP": 0.1, "TSTEP": 0.05, "VA1": 0.125, "F1": 30, "VA2": 0.125, "F2": 37.5}), "save vout2 vin2 vout3 vin3",
         "tr1 " + tr(0.45, 37.5),
         "a0 alter param=VSTEP value=0", "a1 alter param=VA1 value=0.1", "a2 alter param=F1 value=1", "a3 alter param=VA2 value=0.1", "a4 alter param=F2 value=40",
         "tr2 tran stop=3 maxstep=50u errpreset=conservative"]
    return runsim.run("p4_tran", "\n".join(L))


def run_chain():
    L = [hdr("tb_chain", {"FSIG": 10}), "save vout vlna vinp vinn VDDL:p VDDF:p XF.v1",
         "op dc oppoint=rawfile", "ac1 ac start=0.01 stop=100k dec=40", "nz (vout 0) noise start=0.01 stop=100k dec=20",
         "nzl (vlna 0) noise start=0.01 stop=100k dec=20",
         "a1 alter param=AMP value=1m", "a2 alter param=VOS value=0.3",
         "tr1 tran stop=4 maxstep=100u errpreset=conservative"]
    return runsim.run("p4_chain", "\n".join(L))


if __name__ == "__main__":
    what = sys.argv[1]
    if "nocopy" not in sys.argv:
        copy_nets()
    {"main": run_main, "thd": run_thd, "tran": run_tran, "chain": run_chain}[what]()
    if what == "thd":
        for T in (0, 37, 80):
            run_thd(T, "p4_thd_T%d" % T)
