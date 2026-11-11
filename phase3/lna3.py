"""Phase 3 netlist-level description: bias_gen_v2 / ota_fc_lna_v2 (swing fix), ota_fc_chop (CH1/CH2[/CH3]),
lna_chop (Cin/Cf, NPR-element pseudo-R chains, optional reset TGs). Mirrors the Virtuoso cells built by gen_skill3.py."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "phase2"))
import lna_design as ld

NU, PU, mos = ld.NU, ld.PU, ld.mos

# ------------------------------------------------------------------ swing-fix knobs (tuned in s1_swing.py)
CFG = dict(
    WCN1=0.4, LCN1=10.0,     # MCN1: upper VCN diode (source on vcm1, body vss)
    WCN2=0.4, LCN2=10.0,     # MCN2: lower VCN diode
    NPV=8,                   # VCN branch current source = NPV pmos_u2 in series (25 nA / NPV)
    WCP=20.0, LCP=1.0, CPB="nbp",   # MCP: PMOS cascode-bias diode, bulk tied to source (own n-well)
    WL=2.0, LL=20.0,         # M7/M8 load mirror
    L56=4.0,                 # M5/M6 NMOS cascode length
    PCAS=False, WPC=50.0, LPC=1.0, MPC=4,   # optional PMOS cascodes on the input-pair drains (gate = vcm1)
    WSN=0.8, WSP=0.8, LS=0.18,      # chopper TG switch sizes (nmos / pmos), dummies half width (Wmin=0.4u)
)


def bias_v2(c=CFG):
    B = {
        "MBN": (NU, "iref", "iref", "vss", "vss", 1),                      # reference diode, IREF straight in
        "MBS": (NU, "vcp", "iref", "vss", "vss", 1),                       # 25 nA sink for the PMOS branch
        "MCP": (mos("p", c["WCP"], c["LCP"]), "vcp", "vcp", "nbp", c["CPB"].replace("nbp", "nbp"), 1),
        "MBP": (PU, "nbp", "nbp", "vdd", "vdd", 1),
        "MCN1": (mos("n", c["WCN1"], c["LCN1"]), "vcn", "vcn", "vcm1", "vss", 1),
        "MCN2": (mos("n", c["WCN2"], c["LCN2"]), "vcm1", "vcm1", "vss", "vss", 1),
    }
    nodes = ["vdd"] + ["mpv%d" % k for k in range(1, c["NPV"])] + ["vcn"]
    for k in range(c["NPV"]):
        B["MPV%d" % (k + 1)] = (PU, nodes[k + 1], "nbp", nodes[k], "vdd", 1)
    return B


def core_v2(c=CFG, chop=False, ch3=False):
    g1, g2 = ("g1", "g2") if chop else ("vip", "vin")
    s5, s6 = ("s5", "s6") if chop else ("f1", "f2")
    q9, q10 = ("q9", "q10") if ch3 else ("p1", "p2")
    d1, d2 = ("d1", "d2") if c["PCAS"] else ("f1", "f2")
    C = {
        "M0": (PU, "tail", "nbp", "vdd", "vdd", 16),
        "M1": (mos("p", "WINF", "LIN"), d1, "g1x" if chop else g1, "tail", "tail", 10),
        "M2": (mos("p", "WINF", "LIN"), d2, g2, "tail", "tail", 10),
        "M3": (NU, "f1", "nbn", "vss", "vss", 10),
        "M4": (NU, "f2", "nbn", "vss", "vss", 10),
        "M5": (mos("n", 0.4, c["L56"]), "x1", "vcn", s5, "vss", 1),
        "M6": (mos("n", 0.4, c["L56"]), "vout", "vcn", s6, "vss", 1),
        "M7": (mos("p", c["WL"], c["LL"]), "p1", "x1", "vdd", "vdd", 1),
        "M8": (mos("p", c["WL"], c["LL"]), "p2", "x1", "vdd", "vdd", 1),
        "M9": (mos("p", 0.6, 1), "x1", "vcp", q9, "vdd", 1),
        "M10": (mos("p", 0.6, 1), "vout", "vcp", q10, "vdd", 1),
    }
    if c["PCAS"]:
        C["MC1"] = (mos("p", c["WPC"], c["LPC"]), "f1", "vcm1", "d1", "d1", c["MPC"])
        C["MC2"] = (mos("p", c["WPC"], c["LPC"]), "f2", "vcm1", "d2", "d2", c["MPC"])
    return C


def mos_line(name, c, d, g, s, b, m):
    if isinstance(c["W"], str):   # parameterised single device (input pair)
        W = c["W"]; model = "nmos1" if c["type"] == "n" else "pmos1"
        return ["%s (%s %s %s %s) %s w=%s l=%s m=%d ad=%s*0.6u as=%s*0.6u pd=2*%s+1.2u ps=2*%s+1.2u" % (
            name, d, g, s, b, model, W, c["L"], m, W, W, W, W)]
    return ld.mos_line(name, c, d, g, s, b, m)


def geo(W):
    return "ad=%gp as=%gp pd=%gu ps=%gu" % (W * 0.6, W * 0.6, 2 * W + 1.2, 2 * W + 1.2)


def sw(name, a, b, cn, cp, c=CFG, dummies_on=None):
    """CMOS transmission gate a<->b, nmos gate cn, pmos gate cp; optional half-size dummies on node dummies_on.
    Junction geometry is always given (without ad/as Spectre's default junction leaks ~10 pA -> volts on TOhm nodes)."""
    W, P, L = c["WSN"], c["WSP"], c["LS"]
    L_ = ["%sN (%s %s %s vss) nmos1 w=%gu l=%gu %s" % (name, a, cn, b, W, L, geo(W)),
          "%sP (%s %s %s vdd) pmos1 w=%gu l=%gu %s" % (name, a, cp, b, P, L, geo(P))]
    if dummies_on:
        d = dummies_on
        L_ += ["%sDN (%s %s %s vss) nmos1 w=%gu l=%gu %s" % (name, d, cp, d, W / 2, L, geo(W / 2)),   # complement of nmos clock
               "%sDP (%s %s %s vdd) pmos1 w=%gu l=%gu %s" % (name, d, cn, d, P / 2, L, geo(P / 2))]
    return L_


def chopper(pre, ina, inb, outa, outb, p1, p1b, p2, p2b, dummies=True, c=CFG):
    """phase 1: ina->outa, inb->outb ; phase 2: ina->outb, inb->outa. Dummies on the out side."""
    L = []
    L += sw(pre + "A", ina, outa, p1, p1b, c, outa if dummies else None)
    L += sw(pre + "B", inb, outb, p1, p1b, c, outb if dummies else None)
    L += sw(pre + "C", ina, outb, p2, p2b, c, outb if dummies else None)
    L += sw(pre + "D", inb, outa, p2, p2b, c, outa if dummies else None)
    return L


CLK = "c1 c1b c2 c2b o1 o1b o2 o2b"


def subckts(c=CFG, chop=True, ch3=False, npr=6, reset=False, vos_src=False, mism=1.0):
    L = ["subckt bias_gen_v2 vdd vss iref nbn nbp vcp vcn vcm1"]
    for n, a in bias_v2(c).items():
        L += ["    " + x for x in mos_line(n, *a)]
    L += ["    RNB (iref nbn) resistor r=1", "ends bias_gen_v2"]
    # ---- non-chopped v2 OTA
    L += ["subckt ota_fc_lna_v2 vip vin vout vdd vss iref"]
    for n, a in core_v2(c).items():
        L += ["    " + x for x in mos_line(n, *a)]
    L += ["    XB (vdd vss iref nbn nbp vcp vcn vcm1) bias_gen_v2", "ends ota_fc_lna_v2"]
    # ---- chopped OTA
    L += ["subckt ota_fc_chop vip vin vout vdd vss iref %s" % CLK]
    core = core_v2(c, chop=True, ch3=ch3)
    if not vos_src:
        core["M1"] = core["M1"][:2] + ("g1",) + core["M1"][3:]
    for n, a in core.items():
        L += ["    " + x for x in mos_line(n, *a)]
    if vos_src:
        L += ["    VOSI (g1x g1) vsource dc=VOSI"]
    ch1 = chopper("CH1", "vip", "vin", "g1", "g2", "c1", "c1b", "c2", "c2b", True, c)
    if mism != 1.0:   # one CH1 nmos switch wider (charge-injection mismatch test)
        ch1[0] = ch1[0].replace("w=%gu" % c["WSN"], "w=%gu" % (c["WSN"] * mism))
    L += ["    " + x for x in ch1]
    L += ["    " + x for x in chopper("CH2", "f1", "f2", "s5", "s6", "o1", "o1b", "o2", "o2b", False, c)]
    if ch3:
        L += ["    " + x for x in chopper("CH3", "p1", "p2", "q9", "q10", "o1", "o1b", "o2", "o2b", False, c)]
    L += ["    XB (vdd vss iref nbn nbp vcp vcn vcm1) bias_gen_v2", "ends ota_fc_chop"]
    # ---- pseudo-R + LNAs
    L += ["subckt pseudo_r a b",
          "    MPA (mid mid a a) pmos1 w=WPR l=LPR ad=WPR*0.6u as=WPR*0.6u pd=2*WPR+1.2u ps=2*WPR+1.2u",
          "    MPB (mid mid b b) pmos1 w=WPR l=LPR ad=WPR*0.6u as=WPR*0.6u pd=2*WPR+1.2u ps=2*WPR+1.2u",
          "ends pseudo_r"]

    def chain(name, a, b):
        nodes = [a] + ["%s_m%d" % (name.lower(), k) for k in range(1, npr)] + [b]
        return ["    %s_%d (%s %s) pseudo_r" % (name, k, nodes[k], nodes[k + 1]) for k in range(npr)]

    for cell, ota, pins in [("lna_v2", "ota_fc_lna_v2", ""), ("lna_chop", "ota_fc_chop", " " + CLK)]:
        L += ["subckt %s vinp vinn vref vout vdd vss iref%s%s" % (cell, pins, " rst rstb" if reset else ""),
              "    CIN1 (vinp ninv) mimcap area=WCIN*LCIN1 perim=2*WCIN+2*LCIN1",
              "    CIN2 (vinn nnon) mimcap area=WCIN*WCIN perim=4*WCIN",
              "    CF1 (vfb ninv) mimcap area=WCF*WCF perim=4*WCF",
              "    CF2 (nnon vref) mimcap area=WCF*WCF perim=4*WCF"] + chain("PR1", "vfb", "ninv") + chain("PR2", "nnon", "vref") + [
              "    IPRB (vout vfb) iprobe",
              "    I0 (nnon ninv vout vdd vss iref%s) %s" % (pins, ota)]
        if reset:
            L += ["    " + x for x in sw("RS1", "vfb", "ninv", "rst", "rstb", c) + sw("RS2", "nnon", "vref", "rst", "rstb", c)]
        L += ["ends %s" % cell]
    return "\n".join(L)


PARAMS = dict(WINF=50e-6, VDD=1.8, VCM=0.9, VREF=0.9, IREF=25e-9, CL=2e-12, LIN=4e-6, WPR=0.4e-6, LPR=4e-6,
              WCIN=141.22e-6, LCIN1=141.22e-6, WCF=13.943e-6, VOS=0, AMP=1e-3, FSIG=10, VOSI=0,
              FCH=10e3, TNO=30e-9, TOV=30e-9, TR=5e-9)


def header(over=None, opts="reltol=1e-5 vabstol=1e-8 iabstol=1e-15 gmin=1e-15", **kw):
    p = dict(PARAMS); p.update(over or {})
    return "\n".join([
        "simulator lang=spectre", "global 0",
        'include "/cad/FOUNDRY/analog/180nm/models/spectre/gpdk.scs" section=NN',
        "parameters " + " ".join("%s=%g" % kv for kv in p.items()),
        "simulatorOptions options %s temp=27 tnom=27" % opts,
        subckts(**kw)])


def clocks(static=False):
    """Ideal 0/1.8 V clocks, period 1/FCH, phase 1 active at t=0 (so the DC point is the static phase-1 circuit).
    c1/c2 (+b): non-overlapping, gap TNO edge-to-edge (CH1).  o1/o2 (+b): overlapping by TOV (CH2/CH3)."""
    if static:
        return ["Vc1 (c1 0) vsource dc=VDD", "Vc1b (c1b 0) vsource dc=0", "Vc2 (c2 0) vsource dc=0", "Vc2b (c2b 0) vsource dc=VDD",
                "Vo1 (o1 0) vsource dc=VDD", "Vo1b (o1b 0) vsource dc=0", "Vo2 (o2 0) vsource dc=0", "Vo2b (o2b 0) vsource dc=VDD"]
    T = "(1/FCH)"
    # (name, starts high?, delay, width)
    spec = [("c1", True, "%s/2-TNO-TR" % T, "%s/2+TNO" % T),
            ("c2", False, "%s/2" % T, "%s/2-TNO-2*TR" % T),
            ("o1", True, "%s/2+TR+TOV" % T, "%s/2-2*TR-TOV" % T),
            ("o2", False, "%s/2" % T, "%s/2+TOV" % T)]
    L = []
    for nm, hi, td, pw in spec:
        a, b = ("VDD", "0") if hi else ("0", "VDD")
        L.append("V%s (%s 0) vsource type=pulse val0=%s val1=%s delay=%s rise=TR fall=TR width=%s period=%s" % (nm, nm, a, b, td, pw, T))
        L.append("V%sb (%sb 0) vsource type=pulse val0=%s val1=%s delay=%s rise=TR fall=TR width=%s period=%s" % (nm, nm, b, a, td, pw, T))
    return L
