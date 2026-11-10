"""gm/ID sizing for the folded-cascode OTA from the W=10u lookup data (gpdk180, |VDS|=0.9 V)."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psf

HERE = os.path.dirname(os.path.abspath(__file__))
W0 = 10e-6
lut = {"nmos": {}, "pmos": {}}
for folder, Ls in [("gmid_char", [0.18e-6, 0.5e-6, 1e-6, 2e-6, 4e-6]), ("gmid_long", [8e-6, 12e-6, 20e-6])]:
    for k, L in enumerate(Ls):
        r = psf.read(os.path.join(HERE, "raw", folder, "swL-%03d_dcsw.dc" % k))
        for d, m in [("nmos", "M0"), ("pmos", "M1")]:
            i = np.abs(r[m + ":ids"]); ok = i > 1e-12
            lut[d][L] = dict(vgs=r["VGS"][ok], idw=i[ok] / W0, gmid=np.abs(r[m + ":gm"][ok]) / i[ok],
                             vdsat=np.abs(r[m + ":vdsat"][ok]), vth=np.abs(r[m + ":vth"][ok]),
                             gain=np.abs(r[m + ":gm"][ok] / r[m + ":gds"][ok]))


def at_gmid(d, L, g):
    D = lut[d][L]; x = D["gmid"]
    o = np.argsort(x)
    f = lambda k, lg: (np.exp(np.interp(g, x[o], np.log(D[k][o]))) if lg else np.interp(g, x[o], D[k][o]))
    return dict(idw=f("idw", True), vgs=f("vgs", False), vdsat=f("vdsat", False), gain=f("gain", True))


def at_idw(d, L, idw):
    D = lut[d][L]; lx = np.log(D["idw"])
    f = lambda k: np.interp(np.log(idw), lx, D[k])
    return dict(gmid=f("gmid"), vgs=f("vgs"), vdsat=f("vdsat"), gain=np.exp(np.interp(np.log(idw), lx, np.log(D["gain"]))))


if __name__ == "__main__":
    print("== Required W for target gm/ID (W from ID / (ID/W at that gm/ID)) ==")
    for name, d, ID, L, g in [
        ("input pair  M1,M2", "pmos", 200e-9, 4e-6, 25),
        ("NMOS sink   M3,M4", "nmos", 300e-9, 4e-6, 7),
        ("NMOS sink   M3,M4", "nmos", 300e-9, 20e-6, 7),
        ("NMOS sink   M3,M4", "nmos", 300e-9, 20e-6, 6),
        ("NMOS casc   M5,M6", "nmos", 100e-9, 1e-6, 17),
        ("PMOS load   M7,M8", "pmos", 100e-9, 4e-6, 7),
        ("PMOS load   M7,M8", "pmos", 100e-9, 20e-6, 7),
        ("PMOS load   M7,M8", "pmos", 100e-9, 20e-6, 6),
        ("PMOS casc   M9,M10", "pmos", 100e-9, 1e-6, 17),
        ("PMOS tail   M0", "pmos", 400e-9, 20e-6, 7),
    ]:
        r = at_gmid(d, L, g)
        print("%-18s ID=%5.0fn L=%4.1fu gm/ID=%4.1f -> ID/W=%.3g A/m  W=%.3f um  |VGS|=%.3f  Vdsat=%.3f  gm/gds=%.0f"
              % (name, ID * 1e9, L * 1e6, g, r["idw"], ID / r["idw"] * 1e6, r["vgs"], r["vdsat"], r["gain"]))
