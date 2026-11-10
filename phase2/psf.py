"""Minimal PSF-ASCII reader for Spectre swept/non-swept results (dc, ac, noise, stb, op)."""
import re
import numpy as np

_num = re.compile(r'^[-+0-9.eEinfa]+$')


def _tok(s):
    # tokens: quoted strings, parens, numbers
    return re.findall(r'"[^"]*"|\(|\)|[^\s()]+', s)


def read(path):
    txt = open(path).read()
    i = txt.find("\nVALUE\n")
    if i < 0:
        raise ValueError("no VALUE section in " + path)
    has_sweep = "\nSWEEP\n" in txt[:i]
    sweepname = None
    if has_sweep:
        sw = txt[txt.find("\nSWEEP\n") + 7:txt.find("\nTRACE\n") if "\nTRACE\n" in txt else i]
        sweepname = _tok(sw)[0].strip('"')
    body = txt[i + 7:]
    end = body.rfind("END")
    body = body[:end]
    toks = _tok(body)
    data = {}
    k = 0
    n = len(toks)
    while k < n:
        name = toks[k].strip('"'); k += 1
        if k < n and toks[k].startswith('"') and not _num.match(toks[k].strip('"')):
            # type name for non-swept op files:  "name" "type" value
            k += 1
        if toks[k] == "(":
            j = toks.index(")", k)
            nums = [float(x) for x in toks[k + 1:j]]
            k = j + 1
            # 2 numbers = complex (re im); more = struct (e.g. per-device noise fields)
            val = complex(nums[0], nums[1]) if len(nums) == 2 else tuple(nums)
        else:
            t = toks[k].strip('"'); k += 1
            try:
                val = float(t)
            except ValueError:
                val = t
        if k < n and toks[k] == "PROP":
            k = toks.index(")", k) + 1
        data.setdefault(name, []).append(val)
    out = {}
    for key, v in data.items():
        try:
            out[key] = np.array(v)
        except Exception:
            out[key] = v
    if sweepname and sweepname in out:
        out["_x"] = out[sweepname]
    return out
