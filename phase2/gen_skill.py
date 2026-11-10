"""Generate SKILL for Phase-2 cells in AFE_lib from the same description used by lna_design.py."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lna_design as ld

HERE = os.path.dirname(os.path.abspath(__file__))
WPR, LPR = "0.4u", "4u"


def mos_inst(name, c, d, g, s, b, m, xy):
    """-> SKILL lines for one (possibly composite) device."""
    if c["ns"] > 1:  # composite: use the AFE_lib unit cell, m -> iterated instance
        cell = "nmos_u5" if c["type"] == "n" else "pmos_u2"
        iname = name if m == 1 else "%s<0:%d>" % (name, m - 1)
        return [inst(iname, "AFE_lib", cell, xy, [], {"D": d, "G": g, "S": s, "B": b})]
    L = c["L"] if isinstance(c["L"], str) else "%gu" % c["L"]
    return [inst(name, "gpdk180", "nmos" if c["type"] == "n" else "pmos", xy,
                 [("mos", c["W"], L, m)], {"D": d, "G": g, "S": s, "B": b})]


def inst(name, lib, cell, xy, params, conns):
    ps = []
    for p in params:
        if p[0] == "mos":
            ps.append('A_mos(i %s "%s" 1 %d)' % (repr(float(p[1])), p[2], p[3]))
        else:
            ps.append('dbReplaceProp(i "%s" "string" "%s")' % (p[0], p[1]))
    if cell == "vdc" and not any(p[0] == "acm" for p in params):
        ps.append('dbDeletePropByName(i "acm")')
    cs = " ".join('list("%s" "%s")' % kv for kv in conns.items())
    return ('i = A_inst(cv "%s" "%s" "%s" %g:%g "R0" nil) %s A_conn(cv i list(%s))'
            % (lib, cell, name, xy[0], xy[1], " ".join(ps), cs))


def cell(name, pins, body):
    L = ["procedure(P2_%s()" % name, " let((cv i y)",
         '  cv = dbOpenCellViewByType("AFE_lib" "%s" "schematic" "schematic" "w")' % name]
    y = 1.0
    for p, d in pins:
        master = {"input": "ipin", "output": "opin", "inputOutput": "iopin"}[d]
        L.append('  schCreatePin(cv dbOpenCellViewByType("basic" "%s" "symbol") "%s" "%s" nil -3.5:%g "R0")' % (master, p, d, y))
        L.append('  A_w(cv list(-3.5:%g -3.0:%g)) schCreateWireLabel(cv nil -3.0:%g "%s" "lowerLeft" "R0" "stick" 0.0625 nil)' % (y, y, y, p))
        y -= 0.5
    L += ["  " + b for b in body]
    L += ["  schCheck(cv) dbSave(cv)",
          '  when(ddGetObj("AFE_lib" "%s" "symbol") ddDeleteObj(ddGetObj("AFE_lib" "%s" "symbol")))' % (name, name),
          '  schPinListToSymbol("AFE_lib" "%s" "symbol" schSchemToPinList("AFE_lib" "%s" "schematic"))' % (name, name),
          '  list(cv~>modifiedButNotSaved length(cv~>instances))))', ""]
    return L


def grid(k, cols=6, dx=2.5, dy=2.0):
    return (dx * (k % cols), -dy * (k // cols))


out = [open(os.path.join(HERE, "skill", "p2_util.il")).read()]
# ---- pseudo_r
out += cell("pseudo_r", [("a", "input"), ("b", "output")], [
    inst("MPA", "gpdk180", "pmos", (0, 0), [("mos", 0.4, LPR, 1)], {"D": "mid", "G": "mid", "S": "a", "B": "a"}),
    inst("MPB", "gpdk180", "pmos", (2.5, 0), [("mos", 0.4, LPR, 1)], {"D": "mid", "G": "mid", "S": "b", "B": "b"})])
# ---- bias_gen
body = []
for k, (n, a) in enumerate(ld.BIAS.items()):
    body += mos_inst(n, *a, xy=grid(k, cols=5))
out += cell("bias_gen", [("vdd", "inputOutput"), ("vss", "inputOutput"), ("iref", "input"), ("nbn", "output"),
                         ("nbp", "output"), ("vcp", "output")], [b.replace('"vcn"', '"iref"') for b in body])
# ---- ota_fc_lna
body = []
for k, (n, a) in enumerate(ld.CORE.items()):
    body += mos_inst(n, *a, xy=grid(k))
body.append(inst("XB", "AFE_lib", "bias_gen", (0, -7), [],
                 {"vdd": "vdd", "vss": "vss", "iref": "iref", "nbn": "nbn", "nbp": "nbp", "vcp": "vcp"}))
out += cell("ota_fc_lna", [("vdd", "inputOutput"), ("vss", "inputOutput"), ("vip", "input"), ("vin", "input"),
                           ("iref", "input"), ("vout", "output")], body)
# ---- lna_cci
body = [inst("CIN1", "gpdk180", "mimcap", (0, 0), [("w", "WCIN"), ("l", "LCIN1")], {"PLUS": "vinp", "MINUS": "ninv"}),
        inst("CIN2", "gpdk180", "mimcap", (0, -2), [("w", "WCIN"), ("l", "WCIN")], {"PLUS": "vinn", "MINUS": "nnon"}),
        inst("CF1", "gpdk180", "mimcap", (2.5, 0), [("w", "WCF"), ("l", "WCF")], {"PLUS": "vfb", "MINUS": "ninv"}),
        inst("CF2", "gpdk180", "mimcap", (2.5, -2), [("w", "WCF"), ("l", "WCF")], {"PLUS": "nnon", "MINUS": "vref"}),
        inst("IPRB", "analogLib", "iprobe", (5, 0), [], {"PLUS": "vout", "MINUS": "vfb"}),
        inst("I0", "AFE_lib", "ota_fc_lna", (7.5, -1), [],
             {"vip": "nnon", "vin": "ninv", "vout": "vout", "vdd": "vdd", "vss": "vss", "iref": "iref"})]
for side, a, b, y in [("PR1", "vfb", "ninv", 2.0), ("PR2", "nnon", "vref", -4.0)]:
    nodes = [a] + ["%s_m%d" % (side.lower(), k) for k in range(1, ld.NPR)] + [b]
    for k in range(ld.NPR):
        body.append(inst("%s_%d" % (side, k), "AFE_lib", "pseudo_r", (2.0 * k, y), [], {"a": nodes[k], "b": nodes[k + 1]}))
out += cell("lna_cci", [("vdd", "inputOutput"), ("vss", "inputOutput"), ("vinp", "input"), ("vinn", "input"),
                        ("vref", "input"), ("iref", "input"), ("vout", "output")], body)
# ---- tb_pseudo_r
out += cell("tb_pseudo_r", [], [
    inst("X0", "AFE_lib", "pseudo_r", (0, 0), [], {"a": "a", "b": "b"}),
    inst("VA", "analogLib", "vdc", (-2, 0), [("vdc", "0.9+DV")], {"PLUS": "a", "MINUS": "gnd!"}),
    inst("VB", "analogLib", "vdc", (3, 0), [("vdc", "0.9")], {"PLUS": "b", "MINUS": "gnd!"}),
    'A_inst(cv "analogLib" "gnd" "GND0" 0:-2 "R0" nil) A_w(cv list(0:-2 0:-1.75)) schCreateWireLabel(cv nil 0:-1.75 "gnd!" "lowerLeft" "R0" "stick" 0.0625 nil)'])


# ---- tb_lna : 4 benches
def lna(k, x0, extra):
    b = str(k)
    L = [inst("I%s" % b, "AFE_lib", "lna_cci", (x0, 0), [],
              {"vinp": "vinp" + b, "vinn": "vinn" + b, "vref": "vref", "vout": "vout" + b, "vdd": "vdd" + b,
               "vss": "gnd!", "iref": "iref" + b}),
         inst("VDD" + b, "analogLib", "vdc", (x0 + 3, 2), [("vdc", "VDD")] + ([("acm", "1")] if k == 3 else []),
              {"PLUS": "vdd" + b, "MINUS": "gnd!"}),
         inst("IREF" + b, "analogLib", "idc", (x0 + 4, 2), [("idc", "IREF")], {"PLUS": "vdd" + b, "MINUS": "iref" + b}),
         inst("CL" + b, "analogLib", "cap", (x0 + 3, -2), [("c", "CL")], {"PLUS": "vout" + b, "MINUS": "gnd!"})]
    return L + extra


sin = lambda vdc, va, f, ph="0", acm=None, acp=None: (
    [("vdc", vdc), ("vo", vdc), ("va", va), ("freq", f), ("sinephase", ph)] +
    ([("acm", acm)] if acm else []) + ([("acp", acp)] if acp else []))
body = ['A_inst(cv "analogLib" "gnd" "GND0" -3:-5 "R0" nil) A_w(cv list(-3:-5 -3:-4.75)) '
        'schCreateWireLabel(cv nil -3:-4.75 "gnd!" "lowerLeft" "R0" "stick" 0.0625 nil)',
        inst("VREF", "analogLib", "vdc", (-3, 0), [("vdc", "VREF")], {"PLUS": "vref", "MINUS": "gnd!"})]
body += lna(1, 0, [
    inst("VIP1", "analogLib", "vsin", (-1.5, -2), sin("VCM+VOS", "AMP/2", "FSIG", "0", "0.5"), {"PLUS": "vinp1", "MINUS": "gnd!"}),
    inst("VIN1", "analogLib", "vsin", (-0.5, -2), sin("VCM", "AMP/2", "FSIG", "180", "0.5", "180"), {"PLUS": "vinn1", "MINUS": "gnd!"})])
body += lna(2, 8, [
    inst("VC2", "analogLib", "vsin", (6.0, -2), sin("VCM", "VCMA", "50", "0", "1"), {"PLUS": "cm2", "MINUS": "gnd!"}),
    inst("VDP2", "analogLib", "vsin", (6.5, -3.5), sin("0", "VDA/2", "10"), {"PLUS": "vinp2", "MINUS": "cm2"}),
    inst("VDN2", "analogLib", "vsin", (7.5, -3.5), sin("0", "VDA/2", "10", "180"), {"PLUS": "vinn2", "MINUS": "cm2"})])
body += lna(3, 16, [
    inst("VIP3", "analogLib", "vdc", (14.5, -2), [("vdc", "VCM")], {"PLUS": "vinp3", "MINUS": "gnd!"}),
    inst("VIN3", "analogLib", "vdc", (15.5, -2), [("vdc", "VCM")], {"PLUS": "vinn3", "MINUS": "gnd!"})])
pul = lambda v2: [("vdc", "VCM"), ("v1", "VCM"), ("v2", v2), ("td", "0.1"), ("tr", "1u"), ("tf", "1u"), ("pw", "100"), ("per", "200")]
body += lna(4, 24, [
    inst("VP4", "analogLib", "vpulse", (22.5, -2), pul("VCM+VSTEP/2"), {"PLUS": "vinp4", "MINUS": "gnd!"}),
    inst("VN4", "analogLib", "vpulse", (23.5, -2), pul("VCM-VSTEP/2"), {"PLUS": "vinn4", "MINUS": "gnd!"})])
tb = cell("tb_lna", [], body)
tb = [l for l in tb if "schPinListToSymbol" not in l and 'ddDeleteObj(ddGetObj("AFE_lib" "tb_lna" "symbol")' not in l]
tbp = [l for l in out if True]
out += tb
open(os.path.join(HERE, "skill", "p2_cells.il"), "w", newline="\n").write("\n".join(out) + "\n")
print("wrote", len(out), "lines")
