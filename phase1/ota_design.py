"""Folded-cascode OTA design database + Spectre netlist generator.

Composite devices = `ns` series segments (common gate) of W x L each, `m` in parallel.
Same description is used by the SKILL schematic generator so netlist and schematic match.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ design parameters
P = dict(
    IREF=50e-9,           # ideal reference current (each diode mirror)
    VCN=1.0, VCP=0.75,   # ideal cascode gate voltages (documented, replaced in Phase 2)
    VDD=1.8, VCM=0.9,
)
# unit cells (one unit = 50 nA)
NU = dict(type="n", W=0.4, L=20, ns=5, nf=1)      # NMOS unit:  0.4u x (5 x 20u)  -> L_eff 100u
PU = dict(type="p", W=1.0, L=20, ns=2, nf=1)      # PMOS unit:  1u   x (2 x 20u)  -> L_eff 40u

# name: (cell, d, g, s, b, m)   cell = dict or unit
DEV = {
    # bias diodes
    "MBP": (PU, "nbp", "nbp", "vdd", "vdd", 1),
    "MBN": (NU, "nbn", "nbn", "vss", "vss", 1),
    # tail 8 x 50n = 400n
    "M0":  (PU, "tail", "nbp", "vdd", "vdd", 8),
    # input pair, body to source (tail)
    "M1":  (dict(type="p", W=50, L=4, ns=1, nf=1), "f1", "vip", "tail", "tail", 10),
    "M2":  (dict(type="p", W=50, L=4, ns=1, nf=1), "f2", "vin", "tail", "tail", 10),
    # NMOS folding sinks 6 x 50n = 300n
    "M3":  (NU, "f1", "nbn", "vss", "vss", 6),
    "M4":  (NU, "f2", "nbn", "vss", "vss", 6),
    # NMOS cascodes
    "M5":  (dict(type="n", W=0.4, L=1, ns=1, nf=1), "x1", "vcn", "f1", "vss", 1),
    "M6":  (dict(type="n", W=0.4, L=1, ns=1, nf=1), "vout", "vcn", "f2", "vss", 1),
    # PMOS wide-swing cascode mirror load (2 x 50n = 100n)
    # (stability fix, Phase-1 rev B: single 0.5u/20u devices instead of 2x pmos_u2 -> x1 node cap / ~4)
    "M7":  (dict(type="p", W=0.5, L=20, ns=1, nf=1), "p1", "x1", "vdd", "vdd", 2),
    "M8":  (dict(type="p", W=0.5, L=20, ns=1, nf=1), "p2", "x1", "vdd", "vdd", 2),
    "M9":  (dict(type="p", W=0.6, L=1, ns=1, nf=1), "x1", "vcp", "p1", "vdd", 1),
    "M10": (dict(type="p", W=0.6, L=1, ns=1, nf=1), "vout", "vcp", "p2", "vdd", 1),
}


def mos_line(name, c, d, g, s, b, m):
    model = "nmos1" if c["type"] == "n" else "pmos1"
    fw = c["W"]
    geo = "w=%gu l=%gu m=%d ad=%gp as=%gp pd=%gu ps=%gu" % (
        fw, c["L"], m, fw * 0.6, fw * 0.6, 2 * fw + 1.2, 2 * fw + 1.2)
    if c["ns"] == 1:
        return ["%s (%s %s %s %s) %s %s" % (name, d, g, s, b, model, geo)]
    lines = []
    nodes = [d] + ["%s_s%d" % (name, k) for k in range(1, c["ns"])] + [s]
    for k in range(c["ns"]):
        lines.append("%s_%d (%s %s %s %s) %s %s" % (name, k, nodes[k], g, nodes[k + 1], b, model, geo))
    return lines


def subckt(dev=DEV):
    L = ["subckt ota_fc vip vin vout vdd vss nbn nbp vcn vcp"]
    for n, (c, d, g, s, b, m) in dev.items():
        L += ["    " + x for x in mos_line(n, c, d, g, s, b, m)]
    L.append("ends ota_fc")
    return "\n".join(L)


def bias_block(p=P):
    return "\n".join([
        "IBP (nbp 0) isource dc=%g" % p["IREF"],          # sinks 50n out of PMOS diode
        "IBN (vdd nbn) isource dc=%g" % p["IREF"],        # sources 50n into NMOS diode
        "VCN (vcn 0) vsource dc=%g" % p["VCN"],
        "VCP (vcp 0) vsource dc=%g" % p["VCP"],
    ])


def header(params=""):
    return "\n".join([
        "simulator lang=spectre", "global 0",
        'include "/cad/FOUNDRY/analog/180nm/models/spectre/gpdk.scs" section=NN',
        "parameters VDD=%g VCM=%g CL=5p %s" % (P["VDD"], P["VCM"], params),
        "simulatorOptions options reltol=1e-5 vabstol=1e-8 iabstol=1e-15 temp=27 tnom=27 gmin=1e-15",
        subckt(), bias_block(),
        "VDD (vdd 0) vsource dc=VDD",
    ])


if __name__ == "__main__":
    print(header())
