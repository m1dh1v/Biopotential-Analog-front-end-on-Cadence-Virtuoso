"""Phase 4 netlist-level prototype: single-ended OTA-C biquad (Butterworth LPF) with three gm-cell variants.
gm cell = PMOS input pair (bulk tied to source) + NMOS mirror load, tail mirrored from the bias pin nbt.
  A: plain weak-inversion pair
  B: multi-tanh doublet (two pairs, W ratio 1:a and a:1, separate tails, outputs summed)
  C: diode source degeneration (diode-connected PMOS between tail and each pair source)
Biquad: C1*dV1/dt = Gm1*(Vin - Vout);  C2*dVout/dt = Gm2*(V1 - Vout);  C1 = C2 = CF, Gm2 = 2*Gm1 -> Q = 0.707."""

DEF = dict(WP=10, LP=10, WN=1, LN=20, NS=1, WT=2, LT=20, NT=1, A=4, MT1=1, MT2=2)


def g(W):
    return "ad=%gp as=%gp pd=%gu ps=%gu" % (W * 0.6, W * 0.6, 2 * W + 1.2, 2 * W + 1.2)


def mos(name, t, d, gg, s, b, W, L, m=1):
    return "    %s (%s %s %s %s) %s w=%gu l=%gu m=%d %s" % (name, d, gg, s, b, "nmos1" if t == "n" else "pmos1", W, L, m, g(W))


def stack(name, t, d, gg, s, b, W, L, n, m="1"):
    nodes = [d] + ["%s_s%d" % (name.lower(), k) for k in range(1, n)] + [s]
    return [mos("%s_%d" % (name, k), t, nodes[k], gg, nodes[k + 1], b, W, L).replace("m=1", "m=%s" % m) for k in range(n)]


def gm_cell(name, var, c=DEF):
    """pins: inp inn out vdd vss nbt ; tail current = mirror of the nbt diode (MTn = multiplier)."""
    W, L = c["WP"], c["LP"]
    L_ = ["subckt %s inp inn out vdd vss nbt" % name, "    parameters mt=1"]
    if var == "A":
        L_ += [mos("MT", "p", "tail", "nbt", "vdd", "vdd", c["WT"], c["LT"], 1).replace("m=1", "m=mt"),
               mos("M1", "p", "d1", "inp", "tail", "tail", W, L), mos("M2", "p", "out", "inn", "tail", "tail", W, L)]
    elif var == "B":
        a = c["A"]
        L_ += stack("MTA", "p", "ta", "nbt", "vdd", "vdd", c["WT"], c["LT"], c["NT"], "mt")
        L_ += stack("MTB", "p", "tb", "nbt", "vdd", "vdd", c["WT"], c["LT"], c["NT"], "mt")
        L_ += [
               mos("M1A", "p", "d1", "inp", "ta", "ta", W, L, a), mos("M2A", "p", "out", "inn", "ta", "ta", W, L, 1),
               mos("M1B", "p", "d1", "inp", "tb", "tb", W, L, 1), mos("M2B", "p", "out", "inn", "tb", "tb", W, L, a)]
    elif var == "C":
        L_ += [mos("MT", "p", "tail", "nbt", "vdd", "vdd", c["WT"], c["LT"]).replace("m=1", "m=mt"),
               mos("MD1", "p", "s1", "s1", "tail", "tail", W, L), mos("MD2", "p", "s2", "s2", "tail", "tail", W, L),
               mos("M1", "p", "d1", "inp", "s1", "s1", W, L), mos("M2", "p", "out", "inn", "s2", "s2", W, L)]
    ns = c["NS"]   # mirror devices = ns series segments WN/LN, common gate d1
    for nm, top in (("MN1", "d1"), ("MN2", "out")):
        nodes = [top] + ["%s_s%d" % (nm.lower(), k) for k in range(1, ns)] + ["vss"]
        L_ += [mos("%s_%d" % (nm, k), "n", nodes[k], "d1", nodes[k + 1], "vss", c["WN"], c["LN"]) for k in range(ns)]
    L_ += ["ends %s" % name]
    return L_


def subckts(var, c=DEF):
    L = gm_cell("gmc", var, c)
    L += ["subckt lpf vin vout vdd vss ib",
          ] + stack("MB", "p", "nbt", "nbt", "vdd", "vdd", c["WT"], c["LT"], c["NT"]) + [   # IB -> PMOS diode
          "    RIB (ib nbt) resistor r=1",
          "    G1 (vin vout v1 vdd vss nbt) gmc mt=%d" % c["MT1"],
          "    G2 (v1 vout vout vdd vss nbt) gmc mt=%d" % c["MT2"],
          "    C1 (v1 vss) mimcap area=WC*WC perim=4*WC",
          "    C2 (vout vss) mimcap area=WC*WC perim=4*WC",
          "ends lpf"]
    return "\n".join(L)


PAR = dict(VDD=1.8, VCM=0.9, IB=1e-9, WC=141.22e-6, AMP=0.25, FSIG=30, VD=0)


def header(var, over=None, c=DEF):
    p = dict(PAR); p.update({k: c[k] for k in ("WC",) if k in c}); p.update(over or {})
    return "\n".join(["simulator lang=spectre", "global 0",
                      'include "/cad/FOUNDRY/analog/180nm/models/spectre/gpdk.scs" section=NN',
                      "parameters " + " ".join("%s=%g" % kv for kv in p.items()),
                      "simulatorOptions options reltol=1e-6 vabstol=1e-9 iabstol=1e-18 gmin=1e-15 temp=27 tnom=27",
                      subckts(var, c)])
