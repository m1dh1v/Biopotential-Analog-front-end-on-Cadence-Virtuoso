"""Read Spectre op.info (oppoint=rawfile) into {instance: {param: value}} for bsim3v3 devices."""
import re, numpy as np
import psf
def read(path):
    txt = open(path).read()
    t0 = txt.index('"bsim3v3" STRUCT('); t1 = txt.index(' STRUCT(', t0 + 20)
    fields = re.findall(r'^"(\w+)" (?:FLOAT|INT|STRING|BYTE)', txt[t0:t1], re.M)
    raw = psf.read(path); out = {}
    for k, v in raw.items():
        a = np.atleast_1d(v)
        if a.ndim == 2: a = a[0]
        if len(a) == len(fields):
            out[k] = dict(zip(fields, a))
    return out
