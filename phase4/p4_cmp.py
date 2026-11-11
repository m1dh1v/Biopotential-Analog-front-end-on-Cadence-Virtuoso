import sys, json, numpy as np, psf, os
import p4_proto, lpf
from p2_metrics import integ
def contrib(name, fc):
    nz = psf.read("raw/%s/nz.noise" % name); fn = nz["freq"]; o2 = np.abs(nz["out"]) ** 2
    tot = integ(fn, o2, 0.1, 3 * fc); fl = th = 0; per = {}
    for k, v in nz.items():
        if isinstance(v, np.ndarray) and v.ndim == 2 and v.shape[1] >= 5:
            f_ = integ(fn, np.maximum(v[:, 3], 1e-60), 0.1, 3 * fc); t_ = integ(fn, np.maximum(v[:, 0] + v[:, 1] + v[:, 2], 1e-60), 0.1, 3 * fc)
            fl += f_; th += t_; key = k.split(".")[1] if "." in k else k; per[k] = f_ + t_
    top = sorted(per.items(), key=lambda x: -x[1])[:6]
    return tot, fl, th, top
var, ib, tag = sys.argv[1], float(sys.argv[2]), sys.argv[3]
c = dict(lpf.DEF); c.update(json.loads(sys.argv[4]) if len(sys.argv) > 4 else {})
d = p4_proto.dc_transfer(var, ib, c=c, tag=tag); b = p4_proto.biquad(var, ib, c=c, tag=tag)
tot, fl, th, top = contrib("bq_%s%s" % (var, tag), b["fc"])
print("Cin(10/50/150/1k Hz) = %s pF" % ["%.3f" % (v * 1e12) for v in b["cin"].values()])
print("%s%s IB=%.3gn: gm0(mt=1)=%.3g nS lin=+-%.0f mV | fc=%.1f peak=%.2f THD=%.3f%% I=%.2f nA | noise %.1f uV (flicker %.1f, thermal %.1f) top: %s" % (
    var, tag, ib * 1e9, d["gm0"] * 1e9, d["lin10"] * 1e3, b["fc"], b["peak"], b["thd"] * 100, b["I"] * 1e9, np.sqrt(tot) * 1e6, np.sqrt(fl) * 1e6, np.sqrt(th) * 1e6,
    ", ".join("%s %.0f%%" % (k, 100 * v / tot) for k, v in top)))
