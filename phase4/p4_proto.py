"""Prototype runs: gm-cell DC transfer and biquad AC/noise/THD for variants A/B/C."""
import os, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psf, runsim, lpf
from thd import thd
from p2_metrics import integ


def dc_transfer(var, ib, vcm=0.9, mt=1, c=lpf.DEF, tag=""):
    t = "\n".join([lpf.header(var, {"IB": ib, "VCM": vcm}, c),
                   "VDD (vdd 0) vsource dc=VDD", "IB (nbt 0) isource dc=IB",
                   ] + lpf.stack("MB", "p", "nbt", "nbt", "vdd", "vdd", c["WT"], c["LT"], c["NT"]) + [
                   "VP (inp 0) vsource dc=VCM+VD/2", "VN (inn 0) vsource dc=VCM-VD/2", "VO (out 0) vsource dc=VCM",
                   "X1 (inp inn out vdd 0 nbt) gmc mt=%d" % mt, "save VO:p VDD:p",
                   "sw dc param=VD start=-0.5 stop=0.5 step=2m"])
    rd = runsim.run("dc_%s%s" % (var, tag), t, quiet=True)
    r = psf.read(os.path.join(rd, "sw.dc")); vd = r["VD"] if "VD" in r else r["_x"]; i = r["VO:p"]   # current into VO = out current
    gm = np.gradient(i, vd); g0 = gm[np.argmin(abs(vd))]
    # linear range: |VD| where incremental gm has fallen by 10 % / output current deviates 1 % from linear
    ok = np.abs(gm) >= 0.9 * abs(g0); k0 = np.argmin(abs(vd)); lo = k0; hi = k0
    while lo > 0 and ok[lo - 1]: lo -= 1
    while hi < len(vd) - 1 and ok[hi + 1]: hi += 1
    return dict(gm0=abs(g0), lin10=float(min(-vd[lo], vd[hi])), Isup=abs(float(r["VDD:p"][k0])), vd=vd, i=i, gm=gm)


def biquad(var, ib, c=lpf.DEF, tag="", amp=0.25, fsig=30, tstop=0.4, temp=27):
    t = "\n".join([lpf.header(var, {"IB": ib, "AMP": amp, "FSIG": fsig}, c).replace("temp=27", "temp=%g" % temp),
                   "VDD (vdd 0) vsource dc=VDD", "IB (ib 0) isource dc=IB",
                   "VIN (vin 0) vsource type=sine dc=VCM sinedc=VCM ampl=AMP freq=FSIG mag=1",
                   "X1 (vin vout vdd 0 ib) lpf", "save vout X1.v1 VDD:p VIN:p",
                   "op dc", "ac1 ac start=0.1 stop=100k dec=20", "nz (vout 0) noise start=0.1 stop=100k dec=20",
                   "tr tran stop=%g maxstep=%g errpreset=conservative" % (tstop, 1 / fsig / 400)])
    rd = runsim.run("bq_%s%s" % (var, tag), t, quiet=True)
    ac = psf.read(os.path.join(rd, "ac1.ac")); f = ac["freq"]; H = np.abs(ac["vout"]); A = 20 * np.log10(H)
    g0 = A[0]; fc = float(np.exp(np.interp(-(g0 - 3), -A, np.log(f)))); pk = float(A.max() - g0)
    nz = psf.read(os.path.join(rd, "nz.noise")); fn = nz["freq"]; o = np.abs(nz["out"])
    vn = np.sqrt(integ(fn, o ** 2, 0.1, 3 * fc))
    tr = psf.read(os.path.join(rd, "tr.tran.tran")); tt = tr["time"]; tu = np.arange(0.2, tstop, 1 / fsig / 200)
    vu = np.interp(tu, tt, tr["vout"]); th, h = thd(tu, vu, fsig, 0.2, 0.2 + 6 / fsig)
    op = psf.read(os.path.join(rd, "op.dc"))
    Iin = ac["VIN:p"]; cin = {fx: float(abs(np.interp(fx, f, Iin.imag)) / (2 * np.pi * fx)) for fx in (10.0, 50.0, 150.0, 1000.0)}
    return dict(cin=cin, G0=float(g0), fc=fc, peak=pk, vn=float(vn), thd=float(th), h1=float(h[0]), I=abs(float(np.atleast_1d(op["VDD:p"])[0])),
                vout_dc=float(np.atleast_1d(op["vout"])[0]), v1_dc=float(np.atleast_1d(op["X1.v1"])[0]))


if __name__ == "__main__":
    var = sys.argv[1]; ib = float(sys.argv[2])
    d = dc_transfer(var, ib)
    print("%s DC: gm0=%.3g S at IB=%.3g (tail mt=1), lin(gm -10%%)=+-%.0f mV" % (var, d["gm0"], ib, d["lin10"] * 1e3))
    b = biquad(var, ib)
    print("%s biquad: G0=%.2f dB fc=%.1f Hz peak=%.2f dB  noise(0.1-3fc)=%.1f uV  THD(0.5Vpp,30Hz)=%.3f %%  I=%.2f nA  Vout=%.4f V1=%.4f" % (
        var, b["G0"], b["fc"], b["peak"], b["vn"] * 1e6, b["thd"] * 100, b["I"] * 1e9, b["vout_dc"], b["v1_dc"]))
