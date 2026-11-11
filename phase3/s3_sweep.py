"""Chopped-LNA PSS/PAC/Pnoise metric extraction (Step 3 input-pair sweep, f_chop sweep, ...)."""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psf, runsim, lna3, s2_proto
from p2_metrics import bw, integ, UT_NEF, FOURKT

PSS = "pss1 pss fund=FCH harms=20 tstab=5/FCH errpreset=conservative"
PAC = "pac1 pac start=0.1 stop=100k dec=20 sweeptype=absolute maxsideband=10"
PN = "pn1 (vout 0) pnoise start=0.1 stop=100k dec=20 sweeptype=absolute maxsideband=30 noisetype=timeaverage"


def run(name, over=None, cfg=None, kw=None, extra=(), static_op=True):
    c = dict(lna3.CFG); c.update(cfg or {})
    k = dict(kw or {}); k["c"] = c
    ex = [PSS, PAC, PN, "save I1.I0.M1:cgg I1.I0.M1:gm I1.I0.M1:ids"] + list(extra)
    rd = runsim.run(name, s2_proto.bench(dict({"AMP": 0}, **(over or {})), kw=k, extra=ex))
    if static_op:
        runsim.run(name + "_op", s2_proto.bench(dict({"AMP": 0}, **(over or {})), kw=k, static=True,
                                                extra=["save I1.I0.M1:cgg I1.I0.M1:gm I1.I0.M1:ids I1.I0.M1:cgs", "op dc"]), quiet=True)
    return rd


def metrics(name, fch=10e3):
    rd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw", name)
    p = psf.read(rd + "/pac1.0.pac"); f = p["freq"]; H = p["vout"]
    G, fhp, flp = bw(f, H)
    n = psf.read(rd + "/pn1.pnoise"); fn = n["freq"]; out = np.abs(n["out"])
    Hn = np.exp(np.interp(np.log(fn), np.log(f), np.log(np.abs(H)))); vin = out / Hn
    t = psf.read(rd + "/pss1.td.pss")
    I = abs(t["VDD:p"]).mean()
    Gl = 10 ** (G / 20)
    vni_band = np.sqrt(integ(fn, vin ** 2, 0.5, 200))
    vni_tot = np.sqrt(integ(fn, out ** 2, 0.1, 1e5)) / Gl
    BW = flp - fhp
    nef = vni_tot * np.sqrt(2 * I / (np.pi * UT_NEF * FOURKT * BW))
    nef_x = vni_tot * np.sqrt(2 * (I - 25e-9) / (np.pi * UT_NEF * FOURKT * BW))
    r = dict(G=G, fhp=fhp, flp=flp, vni_band=vni_band, vni_tot=vni_tot, I=I, NEF=nef, NEF_x=nef_x, PEF=nef ** 2 * 1.8,
             vin1=float(np.interp(1, fn, vin)), vin1k=float(np.interp(1e3, fn, vin)), vout_dc=float(t["vout"].mean()))
    try:
        op = psf.read(os.path.join(os.path.dirname(rd), name + "_op", "op.dc"))
        r["Cp"] = float(np.atleast_1d(op["I1.I0.M1:cgg"])[0])
        r["gmid"] = float(abs(np.atleast_1d(op["I1.I0.M1:gm"])[0] / np.atleast_1d(op["I1.I0.M1:ids"])[0]))
        Ctot = 20e-12 + 0.2e-12 + r["Cp"]; r["penalty"] = Ctot / 20e-12
    except Exception as e:
        print("no op", e)
    # white-floor and 1/f corner of the input-referred PSD
    fl = np.median(vin[(fn > 300) & (fn < 1000)])
    lo = np.where(vin > np.sqrt(2) * fl)[0]
    lo = lo[fn[lo] < 300]
    r["floor"] = float(fl); r["corner"] = float(fn[lo[-1]]) if len(lo) else float("nan")
    return r, fn, vin, out


def show(name, r):
    print("%-14s G=%.2f dB fHP=%.3f fLP=%.0f Vni_band=%.3f uV Vni_tot=%.3f uV I=%.1f nA NEF=%.2f (exIREF %.2f) PEF=%.1f"
          " floor=%.0f nV corner=%.3g Hz Cp=%.3g pF pen=%.3f vout=%.3f" % (
              name, r["G"], r["fhp"], r["flp"], r["vni_band"] * 1e6, r["vni_tot"] * 1e6, r["I"] * 1e9, r["NEF"], r["NEF_x"], r["PEF"],
              r["floor"] * 1e9, r["corner"], r.get("Cp", 0) * 1e12, r.get("penalty", 0), r["vout_dc"]))


if __name__ == "__main__":
    pts = json.loads(sys.argv[1])   # list of [name, over, cfg]
    res = {}
    for name, over, cfg in pts:
        run(name, over, cfg)
        r, *_ = metrics(name)
        show(name, r); res[name] = r
    json.dump(res, open(os.path.join("plots", sys.argv[2]), "w"), indent=1)
