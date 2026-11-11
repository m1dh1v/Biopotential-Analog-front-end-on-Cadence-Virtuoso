"""Group pnoise/noise per-device contributions; in-band integrals of input-referred contributions."""
import re, numpy as np
from p2_metrics import integ


def group_name(k):
    b = k.replace("I1.I0.", "").replace("I1.", "")
    b = b.replace("\<", "<").replace("\>", ">")
    b = re.sub(r"<\d+>", "", b)
    if b.startswith("PR"):
        return "pseudo-R chains"
    if b.startswith("RS"):
        return "reset switches"
    b = b.split(".")[0] if not b.startswith("XB") else "bias_gen_v2"
    b = re.sub(r"_\d+$", "", b)
    m = re.match(r"^(CH\d)", b)
    if m:
        return m.group(1) + " switches"
    return b


def groups(n, fn):
    G = {}
    for k, v in n.items():
        if isinstance(v, np.ndarray) and v.ndim == 2 and k.startswith("I1."):
            b = group_name(k)
            g = G.setdefault(b, dict(fl=np.zeros(len(fn)), th=np.zeros(len(fn)), tot=np.zeros(len(fn))))
            g["tot"] += v[:, -1]
            if v.shape[1] >= 5 and not b.startswith("pseudo"):
                g["fl"] += v[:, 3]; g["th"] += v[:, 0] + v[:, 1] + v[:, 2]
            else:
                g["th"] += v[:, -1]
    return G


def table(n, fn, out, H2, fx_list=(1.0, 1e3), top=8):
    G = groups(n, fn); res = {}
    for fx in fx_list:
        i = int(np.argmin(abs(fn - fx))); tot = out[i] ** 2; items = []
        for b, g in G.items():
            if b.startswith("pseudo") or b.endswith("switches"):
                items.append((b, g["tot"][i]))
            else:
                items.append((b + " flicker", g["fl"][i])); items.append((b + " thermal", g["th"][i]))
        items.sort(key=lambda x: -x[1])
        res[fx] = [(nm, float(np.sqrt(x / H2[i])), 100 * x / tot) for nm, x in items[:top]]
    band = {b: integ(fn, g["tot"] / H2, 0.5, 200) for b, g in G.items()}
    bandfl = {b: integ(fn, np.maximum(g["fl"], 1e-60) / H2, 0.5, 200) for b, g in G.items()}
    totb = sum(band.values())
    return res, band, bandfl, totb
