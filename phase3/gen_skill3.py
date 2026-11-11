"""Generate SKILL for the Phase-3 AFE_lib cells (same topology as lna3.py, frozen design values)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase2"))
import lna_design as ld

NPR_MAIN = 6


def inst(name, lib, cell, xy, params, conns, orient="R0"):
    ps = []
    for p in params:
        if p[0] == "mos":       # numeric width (um), L string, m
            ps.append('A_mos(i %s "%s" 1 %d)' % (repr(float(p[1])), p[2], p[3]))
        elif p[0] == "mosv":    # width expression, L string, m
            ps.append('A_mosv(i "%s" "%s" %d)' % (p[1], p[2], p[3]))
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


def cell(name, pins, body, symbol=True):
    L = ["procedure(P3_%s()" % name, " let((cv i)",
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


def comp(name, unit, xy, conns, m=1):
    iname = name if m == 1 else "%s<0:%d>" % (name, m - 1)
    return inst(iname, "AFE_lib", unit, xy, [], conns)


def mosi(name, t, W, L, xy, d, g, s, b, m=1, var=False):
    return inst(name, "gpdk180", "nmos" if t == "n" else "pmos", xy,
                [("mosv" if var else "mos", W, L, m)], {"D": d, "G": g, "S": s, "B": b})


out = [open(os.path.join(HERE, "..", "phase2", "skill", "p2_util.il")).read(),
       open(os.path.join(HERE, "skill", "p3_util.il")).read()]

# ------------------------------------------------------------------ bias_gen_v2
b = [note((0, 1.2), "bias_gen_v2: IREF->MBN (nbn = iref); MBS/MCP/MBP -> vcp, nbp; separate VCN branch MPV1-8 (~3 nA) -> MCN1/MCN2"),
     comp("MBN", "nmos_u5", (0, 0), {"D": "iref", "G": "iref", "S": "vss", "B": "vss"}),
     comp("MBS", "nmos_u5", (2.5, 0), {"D": "vcp", "G": "iref", "S": "vss", "B": "vss"}),
     mosi("MCP", "p", 20, "1u", (5, 0), "vcp", "vcp", "nbp", "nbp"),
     comp("MBP", "pmos_u2", (7.5, 0), {"D": "nbp", "G": "nbp", "S": "vdd", "B": "vdd"}),
     mosi("MCN1", "n", 0.4, "10u", (10, 0), "vcn", "vcn", "vcm1", "vss"),
     mosi("MCN2", "n", 0.4, "10u", (12.5, 0), "vcm1", "vcm1", "vss", "vss")]
nodes = ["vdd"] + ["mpv%d" % k for k in range(1, 8)] + ["vcn"]
for k in range(8):
    b.append(comp("MPV%d" % (k + 1), "pmos_u2", (2.5 * k, -2.5), {"D": nodes[k + 1], "G": "nbp", "S": nodes[k], "B": "vdd"}))
out += cell("bias_gen_v2", [("vdd", "inputOutput"), ("vss", "inputOutput"), ("iref", "input"), ("nbp", "output"),
                            ("vcp", "output"), ("vcn", "output"), ("vcm1", "output")], b)
XB = lambda xy: inst("XB", "AFE_lib", "bias_gen_v2", xy, [],
                     {"vdd": "vdd", "vss": "vss", "iref": "iref", "nbp": "nbp", "vcp": "vcp", "vcn": "vcn", "vcm1": "vcm1"})


# ------------------------------------------------------------------ ota_fc_lna_v2 (non-chopped, swing fix)
def core(chop):
    d1, d2 = ("d1", "d2") if chop else ("f1", "f2")
    g1, g2 = ("g1x" if chop == "os" else "g1", "g2") if chop else ("vip", "vin")
    s5, s6 = ("s5", "s6") if chop else ("f1", "f2")
    q9, q10 = ("q9", "q10") if chop else ("p1", "p2")
    L56 = "4u" if chop else "1u"
    B = [comp("M0", "pmos_u2", (0, 0), {"D": "tail", "G": "nbp", "S": "vdd", "B": "vdd"}, 16)]
    if chop:
        B += [mosi("M1", "p", "WINF", "LIN", (2.5, 0), d1, g1, "tail", "tail", 10, var=True),
              mosi("M2", "p", "WINF", "LIN", (5, 0), d2, g2, "tail", "tail", 10, var=True),
              mosi("MC1", "p", 50, "1u", (7.5, 0), "f1", "vcm1", "d1", "d1", 4),
              mosi("MC2", "p", 50, "1u", (10, 0), "f2", "vcm1", "d2", "d2", 4)]
    else:
        B += [mosi("M1", "p", 50, "LIN", (2.5, 0), "f1", "vip", "tail", "tail", 10),
              mosi("M2", "p", 50, "LIN", (5, 0), "f2", "vin", "tail", "tail", 10)]
    B += [comp("M3", "nmos_u5", (0, -2.5), {"D": "f1", "G": "iref", "S": "vss", "B": "vss"}, 10),
          comp("M4", "nmos_u5", (2.5, -2.5), {"D": "f2", "G": "iref", "S": "vss", "B": "vss"}, 10),
          mosi("M5", "n", 0.4, L56, (5, -2.5), "x1", "vcn", s5, "vss"),
          mosi("M6", "n", 0.4, L56, (7.5, -2.5), "vout", "vcn", s6, "vss"),
          mosi("M7", "p", 2, "20u", (0, -5), "p1", "x1", "vdd", "vdd"),
          mosi("M8", "p", 2, "20u", (2.5, -5), "p2", "x1", "vdd", "vdd"),
          mosi("M9", "p", 0.6, "1u", (5, -5), "x1", "vcp", q9, "vdd"),
          mosi("M10", "p", 0.6, "1u", (7.5, -5), "vout", "vcp", q10, "vdd"),
          XB((0, -8))]
    return B


out += cell("ota_fc_lna_v2", [("vdd", "inputOutput"), ("vss", "inputOutput"), ("vip", "input"), ("vin", "input"),
                              ("iref", "input"), ("vout", "output")],
            [note((0, 1.2), "ota_fc_lna_v2: Phase-2 OTA + bias_gen_v2 (VCN lowered -> folding nodes ~0.30 V), M7/M8 2u/20u")] + core(False))


# ------------------------------------------------------------------ ota_fc_chop (+ offset test copy)
def tg(name, a, bnode, cn, cp, xy, dummy=None, wn=None):
    L = [mosi(name + "N", "n", wn or 0.8, "180n", xy, a, cn, bnode, "vss", var=bool(wn)) if not wn else
         mosi(name + "N", "n", wn, "180n", xy, a, cn, bnode, "vss", var=True),
         mosi(name + "P", "p", 0.8, "180n", (xy[0] + 1.6, xy[1]), a, cp, bnode, "vdd")]
    if dummy:
        L += [mosi(name + "DN", "n", 0.4, "180n", (xy[0] + 3.2, xy[1]), dummy, cp, dummy, "vss"),
              mosi(name + "DP", "p", 0.4, "180n", (xy[0] + 4.8, xy[1]), dummy, cn, dummy, "vdd")]
    return L


def chopper(pre, ia, ib, oa, ob, p1, p1b, p2, p2b, y, dummies, x0=0, wA=None):
    dx = 7.0 if dummies else 4.0
    return (tg(pre + "A", ia, oa, p1, p1b, (x0, y), oa if dummies else None, wn=wA) +
            tg(pre + "B", ib, ob, p1, p1b, (x0 + dx, y), ob if dummies else None) +
            tg(pre + "C", ia, ob, p2, p2b, (x0 + 2 * dx, y), ob if dummies else None) +
            tg(pre + "D", ib, oa, p2, p2b, (x0 + 3 * dx, y), oa if dummies else None))


CLK = ["c1", "c1b", "c2", "c2b", "o1", "o1b", "o2", "o2b", "o3", "o3b", "o4", "o4b"]


def ota_chop(os_):
    B = [note((0, 1.2), "ota_fc_chop: folded cascode, input-pair PMOS cascodes MC1/MC2 (gate vcm1), M5/M6 0.4u/4u"),
         note((0, -10.6), "CH1 input chopper vip/vin -> g1/g2 (M1/M2 gates): CMOS TGs 0.8u/0.18u + half-size dummies, NON-overlapping c1/c2"),
         note((0, -13.6), "CH2 demodulator f1/f2 -> s5/s6 (M5/M6 sources): CMOS TGs, OVERLAPPING o1/o2 (make-before-break)"),
         note((0, -16.6), "CH3 load-mirror chopper p1/p2 -> q9/q10 (M9/M10 sources): CMOS TGs, overlapping o3/o4")]
    B += core("os" if os_ else True)
    B += chopper("CH1", "vip", "vin", "g1", "g2", "c1", "c1b", "c2", "c2b", -12, True, wA="WS1A")
    B += chopper("CH2", "f1", "f2", "s5", "s6", "o1", "o1b", "o2", "o2b", -15, False)
    B += chopper("CH3", "p1", "p2", "q9", "q10", "o3", "o3b", "o4", "o4b", -18, False)
    if os_:
        B += [note((10, -2.0), "TEST COPY: VOSI in series with M1 gate"),
              inst("VOSI", "analogLib", "vdc", (12.5, -2.5), [("vdc", "VOSI")], {"PLUS": "g1x", "MINUS": "g1"})]
    return B


pins_ota = [("vdd", "inputOutput"), ("vss", "inputOutput"), ("vip", "input"), ("vin", "input"), ("iref", "input"),
            ("vout", "output")] + [(c, "input") for c in CLK]
out += cell("ota_fc_chop", pins_ota, ota_chop(False))
out += cell("ota_fc_chop_os", pins_ota, ota_chop(True))


# ------------------------------------------------------------------ LNAs
def lna(ota, npr, chop, reset):
    body = [inst("CIN1", "gpdk180", "mimcap", (0, 0), [("w", "WCIN"), ("l", "LCIN1")], {"PLUS": "vinp", "MINUS": "ninv"}),
            inst("CIN2", "gpdk180", "mimcap", (0, -2), [("w", "WCIN"), ("l", "WCIN")], {"PLUS": "vinn", "MINUS": "nnon"}),
            inst("CF1", "gpdk180", "mimcap", (2.5, 0), [("w", "WCF"), ("l", "WCF")], {"PLUS": "vfb", "MINUS": "ninv"}),
            inst("CF2", "gpdk180", "mimcap", (2.5, -2), [("w", "WCF"), ("l", "WCF")], {"PLUS": "nnon", "MINUS": "vref"}),
            inst("IPRB", "analogLib", "iprobe", (5, 0), [], {"PLUS": "vout", "MINUS": "vfb"})]
    oc = {"vip": "nnon", "vin": "ninv", "vout": "vout", "vdd": "vdd", "vss": "vss", "iref": "iref"}
    if chop:
        oc.update({c: c for c in CLK})
    body.append(inst("I0", "AFE_lib", ota, (7.5, -1), [], oc))
    for side, a, bb, y in [("PR1", "vfb", "ninv", 2.0), ("PR2", "nnon", "vref", -4.0)]:
        nodes = [a] + ["%s_m%d" % (side.lower(), k) for k in range(1, npr)] + [bb]
        for k in range(npr):
            body.append(inst("%s_%d" % (side, k), "AFE_lib", "pseudo_r", (2.0 * (k % 6), y + (1.2 if k >= 6 else 0) * (1 if y > 0 else -1)),
                             [], {"a": nodes[k], "b": nodes[k + 1]}))
    if reset:
        body.append(note((0, 4.6), "reset TGs RS1 (vfb-ninv), RS2 (nnon-vref): rst/rstb"))
        body += tg("RS1", "vfb", "ninv", "rst", "rstb", (0, 4))
        body += tg("RS2", "nnon", "vref", "rst", "rstb", (4, 4))
    pins = [("vdd", "inputOutput"), ("vss", "inputOutput"), ("vinp", "input"), ("vinn", "input"), ("vref", "input"),
            ("iref", "input"), ("vout", "output")]
    if chop:
        pins += [(c, "input") for c in CLK]
    if reset:
        pins += [("rst", "input"), ("rstb", "input")]
    return pins, body


p, bd = lna("ota_fc_lna_v2", 6, False, False); out += cell("lna_v2", p, bd)
p, bd = lna("ota_fc_chop", NPR_MAIN, True, True); out += cell("lna_chop", p, bd)
p, bd = lna("ota_fc_chop", 10, True, True); out += cell("lna_chop_pr10", p, bd)
p, bd = lna("ota_fc_chop_os", NPR_MAIN, True, True); out += cell("lna_chop_os", p, bd)


# ------------------------------------------------------------------ testbenches
def gnd(xy):
    return ('A_inst(cv "analogLib" "gnd" "GND0" %g:%g "R0" nil) A_w(cv list(%g:%g %g:%g)) '
            'schCreateWireLabel(cv nil %g:%g "gnd!" "lowerLeft" "R0" "stick" 0.0625 nil)' % (
                xy[0], xy[1], xy[0], xy[1], xy[0], xy[1] + 0.25, xy[0], xy[1] + 0.25))


sin = lambda vdc, va, f, ph="0", acm=None, acp=None, pacm=None, pacp=None: (
    [("vdc", vdc), ("vo", vdc), ("va", va), ("freq", f), ("sinephase", ph)] +
    ([("acm", acm)] if acm else []) + ([("acp", acp)] if acp else []) +
    ([("pacm", pacm)] if pacm else []) + ([("pacp", pacp)] if pacp else []))


def supplies(k, x0, cell_, conns_extra, chop=True, reset=True):
    b = str(k)
    c = {"vinp": "vinp" + b, "vinn": "vinn" + b, "vref": "vref", "vout": "vout" + b, "vdd": "vdd" + b,
         "vss": "gnd!", "iref": "iref" + b}
    if chop:
        c.update({x: x for x in CLK})
    if reset:
        c.update({"rst": "gnd!", "rstb": "vdd" + b})
    c.update(conns_extra)
    return [inst("I%s" % b, "AFE_lib", cell_, (x0, 0), [], c),
            inst("VDD" + b, "analogLib", "vdc", (x0 + 3, 2), [("vdc", "VDD")], {"PLUS": "vdd" + b, "MINUS": "gnd!"}),
            inst("IREF" + b, "analogLib", "idc", (x0 + 4, 2), [("idc", "IREF")], {"PLUS": "vdd" + b, "MINUS": "iref" + b}),
            inst("CL" + b, "analogLib", "cap", (x0 + 3, -2), [("c", "CL")], {"PLUS": "vout" + b, "MINUS": "gnd!"})]


# tb_lna_v2 : one bench (op / AC / noise / T2)
body = [gnd((-3, -5)), inst("VREF", "analogLib", "vdc", (-3, 0), [("vdc", "VREF")], {"PLUS": "vref", "MINUS": "gnd!"})]
body += supplies(1, 0, "lna_v2", {}, chop=False, reset=False)
body += [inst("VIP1", "analogLib", "vsin", (-1.5, -2), sin("VCM+VOS", "AMP/2", "FSIG", "0", "0.5"), {"PLUS": "vinp1", "MINUS": "gnd!"}),
         inst("VIN1", "analogLib", "vsin", (-0.5, -2), sin("VCM", "AMP/2", "FSIG", "180", "0.5", "180"), {"PLUS": "vinn1", "MINUS": "gnd!"})]
out += cell("tb_lna_v2", [], body, symbol=False)

# tb_lna_chop
body = [gnd((-6, -5)), inst("VREF", "analogLib", "vdc", (-6, 0), [("vdc", "VREF")], {"PLUS": "vref", "MINUS": "gnd!"}),
        note((-22, 4.0), "Clocks: c1/c2 non-overlapping (TNO), o1/o2 and o3/o4 overlapping (TOV), period 1/FCH, 0/VDD, TR edges."),
        note((-22, 3.6), "STAT=1 freezes all choppers in phase 1 (static reference for stb/DC); CH3EN=0 freezes CH3 only.")]
T = "1/FCH"
S3 = "max(STAT,1-CH3EN)"
clk = [("c1", "VDD", "VDD*STAT", "%s/2-TNO-TR" % T, "%s/2+TNO" % T),
       ("c1b", "0", "VDD*(1-STAT)", "%s/2-TNO-TR" % T, "%s/2+TNO" % T),
       ("c2", "0", "VDD*(1-STAT)", "%s/2" % T, "%s/2-TNO-2*TR" % T),
       ("c2b", "VDD", "VDD*STAT", "%s/2" % T, "%s/2-TNO-2*TR" % T),
       ("o1", "VDD", "VDD*STAT", "%s/2+TR+TOV" % T, "%s/2-2*TR-TOV" % T),
       ("o1b", "0", "VDD*(1-STAT)", "%s/2+TR+TOV" % T, "%s/2-2*TR-TOV" % T),
       ("o2", "0", "VDD*(1-STAT)", "%s/2" % T, "%s/2+TOV" % T),
       ("o2b", "VDD", "VDD*STAT", "%s/2" % T, "%s/2+TOV" % T),
       ("o3", "VDD", "VDD*%s" % S3, "%s/2+TR+TOV" % T, "%s/2-2*TR-TOV" % T),
       ("o3b", "0", "VDD*(1-%s)" % S3, "%s/2+TR+TOV" % T, "%s/2-2*TR-TOV" % T),
       ("o4", "0", "VDD*(1-%s)" % S3, "%s/2" % T, "%s/2+TOV" % T),
       ("o4b", "VDD", "VDD*%s" % S3, "%s/2" % T, "%s/2+TOV" % T)]
for k, (nm, v1, v2, td, pw) in enumerate(clk):
    body.append(inst("VK" + nm, "analogLib", "vpulse", (-22 + 2.0 * (k % 6), 2.0 - 3.0 * (k // 6)),
                     [("v1", v1), ("v2", v2), ("td", td), ("tr", "TR"), ("tf", "TR"), ("pw", pw), ("per", T)],
                     {"PLUS": nm, "MINUS": "gnd!"}))
# bench 1: main (PSS/PAC/Pnoise/PSTB, T1/T2, Zin)
body += supplies(1, 0, "lna_chop", {})
body += [inst("VIP1", "analogLib", "vsin", (-2.5, -2), sin("VCM+VOS", "AMP/2", "FSIG", "0", None, None, "0.5"), {"PLUS": "vinp1", "MINUS": "gnd!"}),
         inst("VIN1", "analogLib", "vsin", (-1.5, -2), sin("VCM", "AMP/2", "FSIG", "180", None, None, "0.5", "180"), {"PLUS": "vinn1", "MINUS": "gnd!"})]
# bench 2: T3 50 Hz common mode
body += supplies(2, 9, "lna_chop", {})
body += [inst("VC2", "analogLib", "vsin", (6.5, -2), sin("VCM", "VCMA", "50", "0", None, None, "1"), {"PLUS": "cm2", "MINUS": "gnd!"}),
         inst("VDP2", "analogLib", "vsin", (7.0, -3.5), sin("0", "VDA/2", "10"), {"PLUS": "vinp2", "MINUS": "cm2"}),
         inst("VDN2", "analogLib", "vsin", (8.0, -3.5), sin("0", "VDA/2", "10", "180"), {"PLUS": "vinn2", "MINUS": "cm2"})]
# bench 4: overload step + reset
pul = lambda v2: [("vdc", "VCM"), ("v1", "VCM"), ("v2", v2), ("td", "TSTEP"), ("tr", "1u"), ("tf", "1u"), ("pw", "100")]
body += supplies(4, 18, "lna_chop", {"rst": "rst4", "rstb": "rstb4"})
body += [inst("VP4", "analogLib", "vpulse", (15.5, -2), pul("VCM+VSTEP/2"), {"PLUS": "vinp4", "MINUS": "gnd!"}),
         inst("VN4", "analogLib", "vpulse", (16.5, -2), pul("VCM-VSTEP/2"), {"PLUS": "vinn4", "MINUS": "gnd!"}),
         inst("VRST4", "analogLib", "vpulse", (15.5, -4), [("v1", "0"), ("v2", "VDD*RSTEN"), ("td", "TSTEP+TRD"), ("tr", "TR"),
                                                          ("tf", "TR"), ("pw", "TRW")], {"PLUS": "rst4", "MINUS": "gnd!"}),
         inst("VRSTB4", "analogLib", "vpulse", (16.5, -4), [("v1", "VDD"), ("v2", "VDD*(1-RSTEN)"), ("td", "TSTEP+TRD"), ("tr", "TR"),
                                                           ("tf", "TR"), ("pw", "TRW")], {"PLUS": "rstb4", "MINUS": "gnd!"})]
# bench 5: ripple / offset test copy (VOSI inside the OTA)
body += supplies(5, 27, "lna_chop_os", {})
body += [inst("VIP5", "analogLib", "vdc", (24.5, -2), [("vdc", "VCM")], {"PLUS": "vinp5", "MINUS": "gnd!"}),
         inst("VIN5", "analogLib", "vdc", (25.5, -2), [("vdc", "VCM")], {"PLUS": "vinn5", "MINUS": "gnd!"})]
# bench 6: 6-element pseudo-R variant (same inputs as bench 1)
body += supplies(6, 36, "lna_chop_pr10", {})
pul6 = lambda v2, pm, pp: pul(v2) + [("pacm", pm)] + ([("pacp", pp)] if pp else [])
body += [inst("VP6", "analogLib", "vpulse", (33.5, -2), pul6("VCM+VSTEP6/2", "0.5", None), {"PLUS": "vinp6", "MINUS": "gnd!"}),
         inst("VN6", "analogLib", "vpulse", (34.5, -2), pul6("VCM-VSTEP6/2", "0.5", "180"), {"PLUS": "vinn6", "MINUS": "gnd!"})]
body.append(note((33, -6), "bench 6: lna_chop_pr10 (10-element pseudo-R) - step VSTEP6 at TSTEP, PAC +-0.5"))
body.append(note((-1, -6), "bench 1: lna_chop main (PSS/PAC/Pnoise/PSTB, T1/T2, Zin)"))
body.append(note((8, -6), "bench 2: T3 50 Hz CM"))
body.append(note((17, -6), "bench 4: overload step + reset pulse"))
body.append(note((26, -6), "bench 5: lna_chop_os ripple / offset (VOSI)"))
out += cell("tb_lna_chop", [], body, symbol=False)

open(os.path.join(HERE, "skill", "p3_cells.il"), "w", newline="\n").write("\n".join(out) + "\n")
print("wrote", len(out), "lines")
