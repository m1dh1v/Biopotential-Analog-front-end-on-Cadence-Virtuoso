"""Phase 2 netlist-level prototype: ota_fc_lna (+ bias_gen), pseudo_r, lna_cci. Mirrors the Virtuoso cells."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "phase1"))
import ota_design as od

NU = dict(type="n", W=0.4, L=20, ns=5)          # nmos_u5
PU = dict(type="p", W=1.0, L=20, ns=2)          # pmos_u2
mos = lambda t, W, L: dict(type=t, W=W, L=L, ns=1)

# bias generator (pins: vdd vss vcn nbn nbp vcp); IREF (ideal, testbench) is injected into vcn
BIAS = {
    "MC":  (mos("n", 4.0, 1), "vcn", "vcn", "nbn", "vss", 1),    # cascode-bias diode stacked on reference diode
    "MBN": (NU, "nbn", "nbn", "vss", "vss", 1),                 # reference diode (IREF = 25 nA)
    "MBS": (NU, "vcp", "nbn", "vss", "vss", 1),                 # 25 nA sink for the PMOS branch
    "MCP": (mos("p", 20.0, 1), "vcp", "vcp", "nbp", "vdd", 1),   # PMOS cascode-bias diode
    "MBP": (PU, "nbp", "nbp", "vdd", "vdd", 1),                 # PMOS reference diode (tail mirror input)
}
CORE = {
    "M0":  (PU, "tail", "nbp", "vdd", "vdd", 16),               # 16 x 25 nA = 400 nA
    "M1":  (mos("p", 50, "LIN"), "f1", "vip", "tail", "tail", 10),
    "M2":  (mos("p", 50, "LIN"), "f2", "vin", "tail", "tail", 10),
    "M3":  (NU, "f1", "nbn", "vss", "vss", 10),                 # 10 x 25 nA = 250 nA
    "M4":  (NU, "f2", "nbn", "vss", "vss", 10),
    "M5":  (mos("n", 0.4, 1), "x1", "iref", "f1", "vss", 1),
    "M6":  (mos("n", 0.4, 1), "vout", "iref", "f2", "vss", 1),
    "M7":  (mos("p", 0.5, 20), "p1", "x1", "vdd", "vdd", 1),     # 50 nA
    "M8":  (mos("p", 0.5, 20), "p2", "x1", "vdd", "vdd", 1),
    "M9":  (mos("p", 0.6, 1), "x1", "vcp", "p1", "vdd", 1),
    "M10": (mos("p", 0.6, 1), "vout", "vcp", "p2", "vdd", 1),
}


def mos_line(name, c, d, g, s, b, m):
    model = "nmos1" if c["type"] == "n" else "pmos1"
    W = c["W"]; L = c["L"]
    ls = L if isinstance(L, str) else "%gu" % L
    geo = "w=%gu l=%s m=%d ad=%gp as=%gp pd=%gu ps=%gu" % (W, ls, m, W * 0.6, W * 0.6, 2 * W + 1.2, 2 * W + 1.2)
    if c["ns"] == 1:
        return ["%s (%s %s %s %s) %s %s" % (name, d, g, s, b, model, geo)]
    nodes = [d] + ["%s_s%d" % (name, k) for k in range(1, c["ns"])] + [s]
    return ["%s_%d (%s %s %s %s) %s %s" % (name, k, nodes[k], g, nodes[k + 1], b, model, geo) for k in range(c["ns"])]


NPR = 6   # pseudo_r elements in series per feedback path


def chain(name, a, b):
    nodes = [a] + ["%s_m%d" % (name.lower(), k) for k in range(1, NPR)] + [b]
    return ["    %s_%d (%s %s) pseudo_r" % (name, k, nodes[k], nodes[k + 1]) for k in range(NPR)]


def subckts():
    L = ["subckt bias_gen vdd vss vcn nbn nbp vcp"]
    for n, a in BIAS.items():
        L += ["    " + x for x in mos_line(n, *a)]
    L += ["ends bias_gen", "subckt ota_fc_lna vip vin vout vdd vss iref"]
    for n, a in CORE.items():
        L += ["    " + x for x in mos_line(n, *a)]
    L += ["    XB (vdd vss iref nbn nbp vcp) bias_gen", "ends ota_fc_lna",
          # vcn == iref node (IREF injected into the cascode-bias diode)
          "subckt pseudo_r a b",
          "    MPA (mid mid a a) pmos1 w=WPR l=LPR ad=WPR*0.6u as=WPR*0.6u pd=2*WPR+1.2u ps=2*WPR+1.2u",
          "    MPB (mid mid b b) pmos1 w=WPR l=LPR ad=WPR*0.6u as=WPR*0.6u pd=2*WPR+1.2u ps=2*WPR+1.2u",
          "ends pseudo_r",
          "subckt lna_cci vinp vinn vref vout vdd vss iref",
          "    CIN1 (vinp ninv) mimcap area=WCIN*LCIN1 perim=2*WCIN+2*LCIN1",
          "    CIN2 (vinn nnon) mimcap area=WCIN*WCIN perim=4*WCIN",
          "    CF1 (vfb ninv) mimcap area=WCF*WCF perim=4*WCF",
          ] + chain("PR1", "vfb", "ninv") + [
          "    CF2 (nnon vref) mimcap area=WCF*WCF perim=4*WCF",
          ] + chain("PR2", "nnon", "vref") + [
          "    IPRB (vout vfb) iprobe",
          "    I0 (nnon ninv vout vdd vss iref) ota_fc_lna",
          "ends lna_cci"]
    return "\n".join(L)


PARAMS = dict(VDD=1.8, VCM=0.9, VREF=0.9, IREF=25e-9, CL=2e-12, LIN=4e-6, WPR=0.4e-6, LPR=4e-6,
              WCIN=141.22e-6, LCIN1=141.22e-6, WCF=13.943e-6, VOS=0, AMP=1e-3, FSIG=10)


def header(over=None, opts="reltol=1e-5 vabstol=1e-8 iabstol=1e-15 gmin=1e-15"):
    p = dict(PARAMS); p.update(over or {})
    return "\n".join([
        "simulator lang=spectre", "global 0",
        'include "/cad/FOUNDRY/analog/180nm/models/spectre/gpdk.scs" section=NN',
        "parameters " + " ".join("%s=%g" % kv for kv in p.items()),
        "simulatorOptions options %s temp=27 tnom=27" % opts,
        subckts()])


if __name__ == "__main__":
    print(header())
