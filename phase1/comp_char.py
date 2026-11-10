"""Characterize composite (series-stacked) unit devices at 50 nA: gm/ID (composite) and effective Vdsat."""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psf, runsim, ota_design as od

units = {"NU5": dict(type="n", W=0.4, L=20, ns=5), "NU10": dict(type="n", W=0.4, L=20, ns=10),
         "PU2": dict(type="p", W=1.0, L=20, ns=2), "PU4": dict(type="p", W=1.0, L=20, ns=4)}
def run(tag, c):
    n = c["type"] == "n"
    lines = [od.header().split("subckt ota_fc")[0]]
    lines += od.mos_line("X", c, "d", "g", "0" if n else "vdd", "0" if n else "vdd", 1)
    lines += ["VD (d 0) vsource dc=%s" % ("VDS" if n else "1.8-VDS"), "VG (g 0) vsource dc=%s" % ("VG" if n else "1.8-VG"),
              "VDD (vdd 0) vsource dc=1.8", "parameters VDS=0.9 VG=0.5", "save VD:p",
              "sg dc param=VG start=0.3 stop=1.2 step=1m",
              "alt alter param=VG value=VGX", "sd dc param=VDS start=0 stop=0.9 step=2m"]
    return lines
for tag, c in units.items():
    # pass 1: VG sweep at VDS=0.9 -> find VG for 50nA and composite gm/ID
    base = run(tag, c)
    txt = "\n".join(base[:-2]).replace("parameters VDS=0.9 VG=0.5", "parameters VDS=0.9 VG=0.5")
    rd = runsim.run("cc_" + tag, txt, quiet=True)
    r = psf.read(os.path.join(rd, "sg.dc")); vg = r["VG"]; i = np.abs(r["VD:p"])
    vg50 = np.interp(np.log(50e-9), np.log(i), vg)
    gmid = np.interp(vg50, vg, np.gradient(np.log(i), vg))
    txt2 = "\n".join(base[:-3] + ["sd dc param=VDS start=0 stop=0.9 step=2m"]).replace("VG=0.5", "VG=%.5f" % vg50)
    rd = runsim.run("cc2_" + tag, txt2, quiet=True)
    r = psf.read(os.path.join(rd, "sd.dc")); vd = r["VDS"]; i2 = np.abs(r["VD:p"])
    vds95 = np.interp(0.95 * i2[-1], i2, vd)
    gds = np.gradient(i2, vd)[-1]
    print("%-5s %s W=%gu L=%dx%gu (Leff=%gu)  |VGS|(50nA)=%.3f  composite gm/ID=%.2f  Vdsat_eff(95%%)=%.3f V  gm/gds=%.0f"
          % (tag, c["type"], c["W"], c["ns"], c["L"], c["ns"] * c["L"], vg50, gmid, vds95, gmid * 50e-9 / gds))
