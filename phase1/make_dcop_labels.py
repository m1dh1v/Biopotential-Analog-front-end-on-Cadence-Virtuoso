"""Build SKILL that annotates AFE_lib/ota_fc_dcop with DC-op data from raw/final/op.dc (bench I1)."""
import json, os, numpy as np, psf
HERE = os.path.dirname(os.path.abspath(__file__))
op = psf.read(os.path.join(HERE, "raw", "final", "op.dc"))
g = lambda k: float(np.atleast_1d(op[k])[0])
REG = {0: "off", 1: "triode", 2: "sat", 3: "subth(sat)", 4: "bkdn"}
lab = {}
for d in ["M1", "M2", "M5", "M6", "M7", "M8", "M9", "M10"]:
    p = lambda n: g("I1.%s:%s" % (d, n))
    i = abs(p("ids")); r = int(p("region"))
    lab[d] = ["ID=%.0fn  gm/ID=%.1f" % (i * 1e9, abs(p("gm")) / i), REG[r], "Vds-Vdsat=%.2f V" % (abs(p("vds")) - abs(p("vdsat")))]
nodes = {k: g(k) for k in ["I1.tail", "I1.f1", "I1.f2", "nbn1", "nbp1"]}
# composite stacks: unit characterization (comp_char.py): nmos_u5 gm/ID 5.98 Vdsat_eff 0.242; pmos_u2 6.74 / 0.215
comp = {"MBP": ("p", 1, 1.8 - nodes["nbp1"]), "M0<0:7>": ("p", 8, 1.8 - nodes["I1.tail"]),
        "MBN": ("n", 1, nodes["nbn1"]), "M3<0:5>": ("n", 6, nodes["I1.f1"]), "M4<0:5>": ("n", 6, nodes["I1.f2"])}
U = {"n": (5.98, 0.242), "p": (6.74, 0.215)}
for d, (t, m, vds) in comp.items():
    seg = {"MBP": "MBP.M1", "M0<0:7>": "M0\<0\>.M1", "MBN": "MBN.M0", "M3<0:5>": "M3\<0\>.M0", "M4<0:5>": "M4\<0\>.M0"}[d]
    iu = abs(g("I1.%s:ids" % seg))
    lab[d] = ["ID=%.0fn (%dx%.0fn)" % (iu * m * 1e9, m, iu * 1e9), "gm/ID~%.1f  stack sat" % U[t][0], "Vds-Vdsat,eff=%.2f V" % (vds - U[t][1])]
lines = ['procedure(A_dcop()', ' let((cv src i txt)',
         '  src = dbOpenCellViewByType("AFE_lib" "ota_fc" "schematic")',
         '  cv = dbCopyCellView(src "AFE_lib" "ota_fc_dcop" "schematic" nil nil t)']
for d, txt in lab.items():
    lines.append('  i = dbFindAnyInstByName(cv "%s")' % d)
    for k, t in enumerate(txt):
        lines.append('  dbCreateLabel(cv list("annotate" "drawing") xCoord(i~>xy)+0.3:yCoord(i~>xy)-0.62-%.2f "%s" "lowerLeft" "R0" "stick" 0.06)' % (0.1 * k, t))
lines.append('  dbCreateLabel(cv list("annotate" "drawing") -6.5:5.3 "DC operating point (Spectre, tb_ota bench I1, VCM=0.9 V, VDD=1.8 V, 27C):  I(VDD)=%.1f nA  tail=%.3f  f1=%.3f  f2=%.3f  x1=%.3f  p1=%.3f  p2=%.3f  vout=%.3f V" "lowerLeft" "R0" "stick" 0.07)'
             % (abs(g("VDD1:p")) * 1e9, g("I1.tail"), g("I1.f1"), g("I1.f2"), g("I1.x1"), g("I1.p1"), g("I1.p2"), g("vout1")))
lines += ['  schCheck(cv) dbSave(cv) length(cv~>shapes)))']
open(os.path.join(HERE, "skill", "dcop.il"), "w", newline="\n").write("\n".join(lines) + "\n")
print("\n".join(lines))
