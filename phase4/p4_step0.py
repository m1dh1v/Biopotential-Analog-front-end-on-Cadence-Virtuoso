"""Phase 4 Step 0: lna_v2 (schematic netlist tb_lna_v2_sch.scs) - full op table, CMRR/PSRR vs f, input-pair L sweep."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runsim
NET = "/home/ISDL_UG_86/Desktop/cmos65/sim/afe/tb_lna_v2_sch.scs"
P = dict(VDD=1.8, VCM=0.9, VREF=0.9, IREF=25e-9, CL=2e-12, LIN=4e-6, VOS=0, AMP=0, FSIG=10,
         WCIN=141.22e-6, LCIN1=141.22e-6, WCF=13.943e-6)
def hdr(over=None):
    p = dict(P); p.update(over or {})
    return "\n".join(["simulator lang=spectre", "global 0",
                      'include "/cad/FOUNDRY/analog/180nm/models/spectre/gpdk.scs" section=NN',
                      "parameters " + " ".join("%s=%g" % kv for kv in p.items()), 'include "%s"' % NET,
                      "simulatorOptions options reltol=1e-5 vabstol=1e-8 iabstol=1e-15 gmin=1e-15 temp=27 tnom=27"])
AC = "ac start=0.1 stop=10k dec=20"
what = sys.argv[1]
if what == "op":
    runsim.run("p4_op", hdr() + "\nop dc oppoint=rawfile\n")
elif what == "cmrr":
    L = [hdr(), "save vout1 VDD1:p",
         "dm %s" % AC,
         "a1 alter dev=VIN1 param=phase value=0", "cm %s" % AC,
         "a2 alter dev=VIP1 param=mag value=0", "a3 alter dev=VIN1 param=mag value=0", "a4 alter dev=VDD1 param=mag value=1", "ps %s" % AC,
         "b1 alter param=LCIN1 value=WCIN*1.001",
         "b2 alter dev=VDD1 param=mag value=0", "b3 alter dev=VIP1 param=mag value=0.5", "b4 alter dev=VIN1 param=mag value=0.5",
         "b5 alter dev=VIN1 param=phase value=180", "dm_mm %s" % AC,
         "b6 alter dev=VIN1 param=phase value=0", "cm_mm %s" % AC,
         "b7 alter dev=VIP1 param=mag value=0", "b8 alter dev=VIN1 param=mag value=0", "b9 alter dev=VDD1 param=mag value=1", "ps_mm %s" % AC]
    runsim.run("p4_cmrr", "\n".join(L))
elif what == "lsweep":
    L = [hdr(), "save vout1 VDD1:p I1.I0.M1:cgg",
         "swL sweep param=LIN values=[1u 2u 4u 8u] {", "  op dc", "  ac1 ac start=10m stop=100k dec=20",
         "  nz (vout1 0) noise start=10m stop=100k dec=20", "}"]
    runsim.run("p4_lsweep", "\n".join(L))
