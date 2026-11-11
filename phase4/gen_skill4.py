"""Generate SKILL for the Phase-4 AFE_lib cells: pmos_t5, gm_cell, lpf_gmc, tb_lpf, tb_chain."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))


def inst(name, lib, cell, xy, params, conns, orient="R0"):
    ps = []
    for p in params:
        if p[0] == "mos":
            ps.append('A_mos(i %s "%s" 1 %d)' % (repr(float(p[1])), p[2], p[3]))
        else:
            ps.append('dbReplaceProp(i "%s" "string" "%s")' % (p[0], p[1]))
    if cell in ("vdc", "vsin", "vpulse"):
        given = [p[0] for p in params]
        for a in ("acm", "pacm"):
            if a not in given:
                ps.append('dbDeletePropByName(i "%s")' % a)
    cs = " ".join('list("%s" "%s")' % kv for kv in conns.items())
    return ('i = A_inst(cv "%s" "%s" "%s" %g:%g "%s" nil) %s A_conn(cv i list(%s))'
            % (lib, cell, name, xy[0], xy[1], orient, " ".join(ps), cs))


def note(xy, text, h=0.15):
    return 'schCreateNoteLabel(cv %g:%g "%s" "lowerLeft" "R0" "stick" %g "normalLabel")' % (xy[0], xy[1], text, h)


def mosi(name, t, W, L, xy, d, g, s, b, m=1):
    return inst(name, "gpdk180", "nmos" if t == "n" else "pmos", xy, [("mos", W, L, m)], {"D": d, "G": g, "S": s, "B": b})


def comp(name, unit, xy, conns):
    return inst(name, "AFE_lib", unit, xy, [], conns)


def cell(name, pins, body, symbol=True):
    L = ["procedure(P4_%s()" % name, " let((cv i)",
         '  cv = dbOpenCellViewByType("AFE_lib" "%s" "schematic" "schematic" "w")' % name]
    y = 1.0
    for p, d in pins:
        master = {"input": "ipin", "output": "opin", "inputOutput": "iopin"}[d]
        L.append('  schCreatePin(cv dbOpenCellViewByType("basic" "%s" "symbol") "%s" "%s" nil -3.5:%g "R0")' % (master, p, d, y))
        L.append('  A_w(cv list(-3.5:%g -3.0:%g)) schCreateWireLabel(cv nil -3.0:%g "%s" "lowerLeft" "R0" "stick" 0.0625 nil)' % (y, y, y, p))
        y -= 0.5
    L += ["  " + b for b in body]
    L += ["  schCheck(cv) dbSave(cv)"]
    if symbol:
        L += ['  when(ddGetObj("AFE_lib" "%s" "symbol") ddDeleteObj(ddGetObj("AFE_lib" "%s" "symbol")))' % (name, name),
              '  schPinListToSymbol("AFE_lib" "%s" "symbol" schSchemToPinList("AFE_lib" "%s" "schematic"))' % (name, name)]
    L += ['  list(cv~>modifiedButNotSaved length(cv~>instances))))', ""]
    return L


def gnd(xy):
    return ('A_inst(cv "analogLib" "gnd" "GND0" %g:%g "R0" nil) A_w(cv list(%g:%g %g:%g)) '
            'schCreateWireLabel(cv nil %g:%g "gnd!" "lowerLeft" "R0" "stick" 0.0625 nil)' % (
                xy[0], xy[1], xy[0], xy[1], xy[0], xy[1] + 0.25, xy[0], xy[1] + 0.25))


out = [open(os.path.join(HERE, "..", "phase2", "skill", "p2_util.il")).read()]
PU = [("D", "inputOutput"), ("G", "input"), ("S", "inputOutput"), ("B", "inputOutput")]

# ---- pmos_t5: 5 x pmos 2u/20u in series, common gate (tail / bias stack)
nodes = ["D", "n1", "n2", "n3", "n4", "S"]
out += cell("pmos_t5", PU, [note((0, 1.2), "pmos_t5: 5 x pmos 2u/20u in series (L_eff 100 um), common gate")] +
            [mosi("M%d" % k, "p", 2, "20u", (2.5 * k, 0), nodes[k], "G", nodes[k + 1], "B") for k in range(5)])

# ---- gm_cell: multi-tanh doublet
gb = [note((0, 1.4), "gm_cell: multi-tanh doublet. Pair A: M1A (4x) on inp / M2A (1x) on inn, tail MTA; pair B: M1B (1x) / M2B (4x), tail MTB."),
      note((0, 1.1), "PMOS 10u/10u per unit, bulk = own tail. Load: nmos_u5 mirror (MN1 diode d1 -> MN2 out). Tails: pmos_t5 mirrors of nbt."),
      comp("MTA", "pmos_t5", (0, 0), {"D": "ta", "G": "nbt", "S": "vdd", "B": "vdd"}),
      comp("MTB", "pmos_t5", (2.5, 0), {"D": "tb", "G": "nbt", "S": "vdd", "B": "vdd"}),
      mosi("M1A", "p", 10, "10u", (0, -2.5), "d1", "inp", "ta", "ta", 4),
      mosi("M2A", "p", 10, "10u", (2.5, -2.5), "out", "inn", "ta", "ta", 1),
      mosi("M1B", "p", 10, "10u", (5, -2.5), "d1", "inp", "tb", "tb", 1),
      mosi("M2B", "p", 10, "10u", (7.5, -2.5), "out", "inn", "tb", "tb", 4),
      comp("MN1", "nmos_u5", (0, -5), {"D": "d1", "G": "d1", "S": "vss", "B": "vss"}),
      comp("MN2", "nmos_u5", (2.5, -5), {"D": "out", "G": "d1", "S": "vss", "B": "vss"})]
out += cell("gm_cell", [("vdd", "inputOutput"), ("vss", "inputOutput"), ("inp", "input"), ("inn", "input"), ("nbt", "input"),
                        ("out", "output")], gb)

# ---- lpf_gmc: OTA-C biquad
lb = [note((0, 1.6), "lpf_gmc: 2nd-order Butterworth Gm-C LPF. C1 dV1/dt = Gm1 (vin - vout); C2 dvout/dt = Gm2 (v1 - vout); Gm2 = 2 Gm1 (G2<0:1>), C1 = C2"),
      note((0, 1.3), "fc = sqrt(2) Gm1 / (2 pi C); Q = 0.707. Tuning: IB into the pmos_t5 diode MB sets every tail (gm ~ IB, weak inversion)."),
      comp("MB", "pmos_t5", (0, 0), {"D": "ib", "G": "ib", "S": "vdd", "B": "vdd"}),
      inst("G1", "AFE_lib", "gm_cell", (3, 0), [], {"inp": "vin", "inn": "vout", "out": "v1", "vdd": "vdd", "vss": "vss", "nbt": "ib"}),
      inst("G2<0:1>", "AFE_lib", "gm_cell", (7, 0), [], {"inp": "v1", "inn": "vout", "out": "vout", "vdd": "vdd", "vss": "vss", "nbt": "ib"}),
      inst("C1", "gpdk180", "mimcap", (3, -3), [("w", "WCL"), ("l", "WCL")], {"PLUS": "v1", "MINUS": "vss"}),
      inst("C2", "gpdk180", "mimcap", (7, -3), [("w", "WCL"), ("l", "WCL")], {"PLUS": "vout", "MINUS": "vss"})]
out += cell("lpf_gmc", [("vdd", "inputOutput"), ("vss", "inputOutput"), ("vin", "input"), ("ib", "input"), ("vout", "output")], lb)


# ---- testbenches
def lpf_bench(k, x0, src):
    b = str(k)
    return [inst("X%s" % b, "AFE_lib", "lpf_gmc", (x0, 0), [], {"vin": "vin" + b, "vout": "vout" + b, "vdd": "vdd" + b, "vss": "gnd!", "ib": "ib" + b}),
            inst("VDD" + b, "analogLib", "vdc", (x0 + 3, 2), [("vdc", "VDD")], {"PLUS": "vdd" + b, "MINUS": "gnd!"}),
            inst("IB" + b, "analogLib", "idc", (x0 + 4, 2), [("idc", "IB")], {"PLUS": "ib" + b, "MINUS": "gnd!"})] + src


sin = lambda vdc, va, f, extra=(): [("vdc", vdc), ("vo", vdc), ("va", va), ("freq", f)] + list(extra)
body = [gnd((-3, -5)),
        note((-3, 4), "tb_lpf: bench 1 sine (AMP, FSIG) + AC 1 V; bench 2 step VSTEP at TSTEP; bench 3 two-tone (VA1/F1 + VA2/F2). Own VDD and IB per bench.")]
body += lpf_bench(1, 0, [inst("VIN1", "analogLib", "vsin", (-1.5, -2), sin("VCM", "AMP", "FSIG", [("acm", "1")]), {"PLUS": "vin1", "MINUS": "gnd!"})])
body += lpf_bench(2, 8, [inst("VIN2", "analogLib", "vpulse", (6.5, -2), [("vdc", "VCM"), ("v1", "VCM"), ("v2", "VCM+VSTEP"), ("td", "TSTEP"),
                                                                       ("tr", "10u"), ("tf", "10u"), ("pw", "100")], {"PLUS": "vin2", "MINUS": "gnd!"})])
body += lpf_bench(3, 16, [inst("VIN3", "analogLib", "vsin", (14.5, -2), sin("VCM", "VA1", "F1", [("va2", "VA2"), ("freq2", "F2")]),
                               {"PLUS": "vin3", "MINUS": "gnd!"})])
out += cell("tb_lpf", [], body, symbol=False)

# tb_chain: lna_v2 -> lpf_gmc (separate supplies / biases)
body = [gnd((-3, -5)),
        note((-3, 4), "tb_chain: lna_v2 (own VDDL, IREFL, CL) -> lpf_gmc (own VDDF, IBF). VREF shared reference only (no shared bias node)."),
        inst("VREF", "analogLib", "vdc", (-3, 0), [("vdc", "VREF")], {"PLUS": "vref", "MINUS": "gnd!"}),
        inst("IL", "AFE_lib", "lna_v2", (0, 0), [], {"vinp": "vinp", "vinn": "vinn", "vref": "vref", "vout": "vlna", "vdd": "vddl",
                                                    "vss": "gnd!", "iref": "irefl"}),
        inst("VDDL", "analogLib", "vdc", (3, 2), [("vdc", "VDD")], {"PLUS": "vddl", "MINUS": "gnd!"}),
        inst("IREFL", "analogLib", "idc", (4, 2), [("idc", "IREF")], {"PLUS": "vddl", "MINUS": "irefl"}),
        inst("CL", "analogLib", "cap", (3, -2), [("c", "CL")], {"PLUS": "vlna", "MINUS": "gnd!"}),
        inst("VIP", "analogLib", "vsin", (-1.5, -2), sin("VCM+VOS", "AMP/2", "FSIG", [("acm", "0.5")]), {"PLUS": "vinp", "MINUS": "gnd!"}),
        inst("VIN", "analogLib", "vsin", (-0.5, -2), sin("VCM", "AMP/2", "FSIG", [("sinephase", "180"), ("acm", "0.5"), ("acp", "180")]),
             {"PLUS": "vinn", "MINUS": "gnd!"}),
        inst("XF", "AFE_lib", "lpf_gmc", (7, 0), [], {"vin": "vlna", "vout": "vout", "vdd": "vddf", "vss": "gnd!", "ib": "ibf"}),
        inst("VDDF", "analogLib", "vdc", (10, 2), [("vdc", "VDD")], {"PLUS": "vddf", "MINUS": "gnd!"}),
        inst("IBF", "analogLib", "idc", (11, 2), [("idc", "IB")], {"PLUS": "ibf", "MINUS": "gnd!"})]
out += cell("tb_chain", [], body, symbol=False)

open(os.path.join(HERE, "skill", "p4_cells.il"), "w", newline="\n").write("\n".join(out) + "\n")
print("wrote", len(out))
