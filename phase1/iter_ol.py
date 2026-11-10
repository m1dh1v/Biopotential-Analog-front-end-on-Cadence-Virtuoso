"""Iteration bench (netlist level): DC op of every device, open-loop AC (L/C trick), input-referred noise."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psf, runsim, ota_design as od

Ut = 1.380649e-23 * 300.15 / 1.602176634e-19


def devlist():
    """all physical instance names inside ota_fc (segments expanded)"""
    out = []
    for n, (c, d, g, s, b, m) in od.DEV.items():
        out += [n] if c["ns"] == 1 else ["%s_%d" % (n, k) for k in range(c["ns"])]
    return out


PARAMS = ["ids", "gm", "gds", "vgs", "vds", "vth", "vdsat", "region"]


def netlist(CL="5p", extra=""):
    saves = " ".join("I0.%s:%s" % (d, p) for d in devlist() for p in PARAMS)
    return "\n".join([
        od.header("LBIG=1e16"),
        "VIP (vip 0) vsource dc=VCM mag=1",
        "LFB (vout vin) inductor l=LBIG",
        "CFB (vin 0) capacitor c=LBIG",
        "CLD (vout 0) capacitor c=%s" % CL,
        "I0 (vip vin vout vdd 0 nbn nbp vcn vcp) ota_fc",
        "save vout vin vip I0.tail I0.f1 I0.f2 I0.x1 I0.p1 I0.p2 nbn nbp VDD:p " + saves,
        "op dc",
        "ac1 ac start=1m stop=100M dec=20",
        "nz (vout 0) noise start=0.1 stop=100k dec=40 iprobe=VIP",
        extra,
    ])


def report_op(r):
    print("%-6s %9s %7s %7s %7s %7s %7s %6s %s" % ("dev", "ID[nA]", "gm/ID", "|VGS|", "|VDS|", "Vdsat", "margin", "gm/gds", "region"))
    for d in devlist():
        g = lambda p: float(np.atleast_1d(r["I0.%s:%s" % (d, p)])[0])
        idd = abs(g("ids"))
        print("%-6s %9.2f %7.2f %7.3f %7.3f %7.3f %7.3f %6.0f %d" % (
            d, idd * 1e9, abs(g("gm")) / idd, abs(g("vgs")), abs(g("vds")), abs(g("vdsat")),
            abs(g("vds")) - abs(g("vdsat")), abs(g("gm")) / abs(g("gds")), int(g("region"))))


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "it_ol"
    rd = os.path.join(runsim.HERE, "raw", name) if os.environ.get("REUSE") else runsim.run(name, netlist())
    op = psf.read(os.path.join(rd, "op.dc"))
    print("nodes: " + "  ".join("%s=%.3f" % (k, float(np.atleast_1d(op[k])[0])) for k in
                               ["vout", "vin", "I0.tail", "I0.f1", "I0.f2", "I0.x1", "I0.p1", "I0.p2", "nbn", "nbp"]))
    print("I(VDD) = %.1f nA" % (abs(float(np.atleast_1d(op["VDD:p"])[0])) * 1e9))
    report_op(op)
    ac = psf.read(os.path.join(rd, "ac1.ac"))
    f = ac["freq"]; H = ac["vout"]
    A = 20 * np.log10(np.abs(H)); ph = np.unwrap(np.angle(H)) * 180 / np.pi
    k = np.where(A < 0)[0][0]
    fu = np.exp(np.interp(0, [A[k], A[k - 1]], [np.log(f[k]), np.log(f[k - 1])]))
    f3 = np.exp(np.interp(A[0] - 3, A[::-1], np.log(f[::-1])))
    print("A0 = %.1f dB  f-3dB = %.3g Hz  UGF = %.4g Hz  phase@UGF = %.1f deg (PM~%.1f)" % (
        A[0], f3, fu, np.interp(np.log(fu), np.log(f), ph), 180 + np.interp(np.log(fu), np.log(f), ph)))
    nz = psf.read(os.path.join(rd, "nz.noise"))
    fn = nz["freq"]; vin = np.abs(nz["in"])
    band = lambda a, b: np.sqrt(np.trapezoid(np.interp(np.logspace(np.log10(a), np.log10(b), 2000), fn, vin ** 2),
                                         np.logspace(np.log10(a), np.log10(b), 2000)))
    print("Vni(0.5-200) = %.3f uVrms   Vni(300-5k) = %.3f uVrms   in@1Hz=%.0f nV/rtHz in@1k=%.1f in@10k=%.1f" % (
        band(0.5, 200) * 1e6, band(300, 5e3) * 1e6, np.interp(1, fn, vin) * 1e9, np.interp(1e3, fn, vin) * 1e9,
        np.interp(1e4, fn, vin) * 1e9))
    # top contributors at 1 Hz and 1 kHz (input referred, per composite device)
    g2 = np.abs(nz["gain"]) ** 2 if "gain" in nz else None
    for fx in (1.0, 1e3):
        i = np.argmin(abs(fn - fx))
        contrib = {}
        for key, v in nz.items():
            if key.startswith("I0.") and isinstance(v, np.ndarray) and v.ndim == 2:
                base = key[3:].split("_")[0]
                contrib[base] = contrib.get(base, 0) + v[i, -1]
        tot = sum(contrib.values())
        top = sorted(contrib.items(), key=lambda x: -x[1])[:6]
        print("  @%g Hz: " % fx + ", ".join("%s %.0f%%" % (n, 100 * x / tot) for n, x in top))
