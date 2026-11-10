#!/usr/bin/env python3
"""
char_mosfet.py  -  gm/Id characterization plots + lookup table for gpdk180 devices.

Input : one CSV per channel length, written from the Cadence DC sweep, named
        nmos_L180n.csv, nmos_L500n.csv, nmos_L1u.csv, nmos_L2u.csv   (same for pmos_*)
        Columns (lower/upper case ignored): vgs (or vsg), id, gm, gds, cgs, cgd, vth, vdsat
Output: <outdir>/gmid_<dev>.png      four-panel figure
        <outdir>/lut_<dev>.csv       lookup table used later for sizing
        console summary table        gm/Id -> Id/W, intrinsic gain, fT, Vov at each L

Usage examples
  python char_mosfet.py --dir raw --dev nmos --w 10e-6 --out results
  python char_mosfet.py --dir raw --dev pmos --w 10e-6 --out results
  # size a transistor:  gm = 7 uS, gm/Id = 20, L = 1 um
  python char_mosfet.py --dir raw --dev nmos --w 10e-6 --out results --size 7e-6 20 1e-6

Notes
  * Points with |Id| < --imin (default 1 nA) are dropped: Spectre's current tolerance is
    1 pA, so deep-subthreshold currents are unreliable.
  * cgs and cgd come out negative from Spectre; abs() is taken. fT here uses only
    cgs + cgd (intrinsic + overlap as reported by the model) so treat it as approximate.
  * The model is binned in W and L. If curves show small steps, that is the bin switching.
"""
import argparse
import glob
import os
import re
import sys

import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--dir", required=True, help="folder with <dev>_L*.csv")
ap.add_argument("--dev", required=True, choices=["nmos", "pmos"])
ap.add_argument("--w", type=float, default=10e-6, help="device width used in the sweep [m]")
ap.add_argument("--out", default="results", help="output folder")
ap.add_argument("--imin", type=float, default=1e-9, help="drop points with |Id| below this [A]")
ap.add_argument("--show", action="store_true", help="open the plot window")
ap.add_argument("--size", nargs=3, type=float, metavar=("GM", "GMID", "L"),
                help="size a device: gm [S], gm/Id [1/V], L [m]")
args = ap.parse_args()

import matplotlib
if not args.show:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

SUFFIX = {"n": 1e-9, "u": 1e-6, "m": 1e-3, "p": 1e-12}


def tag_to_len(tag):
    m = re.fullmatch(r"([0-9.]+)([nump])", tag)
    if not m:
        raise ValueError("cannot parse length tag '%s'" % tag)
    return float(m.group(1)) * SUFFIX[m.group(2)]


def load(path):
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    for need in ["id", "gm", "gds", "cgs", "cgd"]:
        if need not in df.columns:
            sys.exit("%s: missing column '%s'. Columns found: %s" % (path, need, list(df.columns)))
    vcol = "vgs" if "vgs" in df.columns else ("vsg" if "vsg" in df.columns else df.columns[0])
    d = pd.DataFrame()
    d["vg"] = df[vcol].astype(float)
    d["id"] = df["id"].astype(float).abs()
    d["gm"] = df["gm"].astype(float).abs()
    d["gds"] = df["gds"].astype(float).abs()
    d["cap"] = df["cgs"].astype(float).abs() + df["cgd"].astype(float).abs()
    d["vth"] = df["vth"].astype(float).abs() if "vth" in df.columns else np.nan
    d["vdsat"] = df["vdsat"].astype(float).abs() if "vdsat" in df.columns else np.nan
    return d


files = sorted(glob.glob(os.path.join(args.dir, "%s_L*.csv" % args.dev)))
if not files:
    sys.exit("no files like %s_L*.csv in %s" % (args.dev, args.dir))

os.makedirs(args.out, exist_ok=True)
curves = {}
lut_rows = []
for f in files:
    tag = re.search(r"_L([0-9.]+[nump])\.csv$", f).group(1)
    L = tag_to_len(tag)
    d = load(f)
    d = d[(d["id"] > args.imin) & (d["gm"] > 0) & (d["gds"] > 0) & (d["cap"] > 0)].reset_index(drop=True)
    d["gmid"] = d["gm"] / d["id"]
    d["idw"] = d["id"] / args.w                      # A per metre of width (numerically = uA per um)
    d["gain"] = d["gm"] / d["gds"]
    d["ft"] = d["gm"] / (2 * np.pi * d["cap"])
    d["vov"] = d["vg"] - d["vth"]
    curves[L] = (tag, d)
    steps = np.abs(np.diff(d["gmid"].values)) / d["gmid"].values[:-1]
    n_jump = int((steps > 0.08).sum())
    print("%s  L=%s: %d points kept, plateau gm/Id = %.1f, Id range %.2e..%.2e A%s"
          % (args.dev, tag, len(d), d["gmid"].max(), d["id"].min(), d["id"].max(),
             ("   <-- %d jumps >8%% (possible bin edge)" % n_jump) if n_jump else ""))
    for _, r in d.iterrows():
        lut_rows.append([L, r["vg"], r["idw"], r["gmid"], r["gain"], r["ft"], r["vov"], r["vdsat"]])

curves = dict(sorted(curves.items()))
lut = pd.DataFrame(lut_rows, columns=["L_m", "vg", "id_per_w_uA_per_um", "gm_over_id", "gm_over_gds",
                                      "ft_Hz", "vov", "vdsat"])
lut_path = os.path.join(args.out, "lut_%s.csv" % args.dev)
lut.to_csv(lut_path, index=False)

# ---------------------------------------------------------------- figure
fig, ax = plt.subplots(2, 2, figsize=(11, 8))
for L, (tag, d) in curves.items():
    lab = "L=%s" % tag
    ax[0, 0].semilogx(d["idw"], d["gmid"], label=lab)                    # Id/W in uA/um (= A/m)
    ax[0, 1].semilogy(d["gmid"], d["gain"], label=lab)
    ax[1, 0].semilogy(d["gmid"], d["ft"], label=lab)
    ax[1, 1].plot(d["vg"], d["gmid"], label=lab)
ax[0, 0].set(xlabel="Id/W  [uA/um]", ylabel="gm/Id  [1/V]", title="%s gm/Id vs current density" % args.dev.upper())
ax[0, 1].set(xlabel="gm/Id  [1/V]", ylabel="gm/gds", title="Intrinsic gain vs gm/Id")
ax[1, 0].set(xlabel="gm/Id  [1/V]", ylabel="fT  [Hz] (approx)", title="fT vs gm/Id")
ax[1, 1].set(xlabel="|Vgs|  [V]", ylabel="gm/Id  [1/V]", title="gm/Id vs Vgs (look for plateau / steps)")
for a in ax.ravel():
    a.grid(True, which="both", alpha=0.3)
    a.legend(fontsize=8)
fig.tight_layout()
png = os.path.join(args.out, "gmid_%s.png" % args.dev)
fig.savefig(png, dpi=150)
print("\nsaved", png, "and", lut_path)
if args.show:
    plt.show()


# ---------------------------------------------------------------- lookup helpers
def at_gmid(d, gmid):
    """Interpolate the curve at a given gm/Id. Returns None if outside the measured range."""
    x = d["gmid"].values
    if gmid < x.min() or gmid > x.max():
        return None
    order = np.argsort(x)
    xs = x[order]
    out = {}
    for key, logy in [("idw", True), ("gain", True), ("ft", True), ("vg", False), ("vov", False), ("vdsat", False)]:
        y = d[key].values[order]
        out[key] = float(np.exp(np.interp(gmid, xs, np.log(y)))) if logy else float(np.interp(gmid, xs, y))
    return out


print("\nSummary (device %s, W=%.1f um in the sweep) - Id/W [uA/um], gm/gds, fT [GHz], Vov [V]" % (args.dev, args.w * 1e6))
for gm_target in (5, 10, 15, 20, 25):
    line = ["gm/Id=%2d:" % gm_target]
    for L, (tag, d) in curves.items():
        r = at_gmid(d, gm_target)
        if r is None:
            line.append("L=%s: n/a" % tag)
        else:
            line.append("L=%s: %.2f uA/um, %4.0f, %.2f GHz, %+.2f V" % (tag, r["idw"], r["gain"], r["ft"] / 1e9, r["vov"]))
    print("  " + " | ".join(line))

if args.size:
    gm, gmid, L = args.size
    match = [k for k in curves if abs(k - L) / L < 0.01]
    if not match:
        sys.exit("L=%.3g m not among measured lengths: %s" % (L, sorted(curves)))
    tag, d = curves[match[0]]
    r = at_gmid(d, gmid)
    if r is None:
        sys.exit("gm/Id=%.1f is outside the measured range for L=%s (%.1f..%.1f)" %
                 (gmid, tag, d["gmid"].min(), d["gmid"].max()))
    Id = gm / gmid
    W = Id / r["idw"]
    print("\nSIZING  gm=%.3g S, gm/Id=%.1f, L=%s" % (gm, gmid, tag))
    print("  Id = %.3g A,  Id/W = %.3g uA/um  ->  W = %.2f um" % (Id, r["idw"], W * 1e6))
    print("  intrinsic gain gm/gds = %.0f (%.1f dB),  fT = %.3g GHz,  Vov = %.3f V,  Vdsat = %.3f V"
          % (r["gain"], 20 * np.log10(r["gain"]), r["ft"] / 1e9, r["vov"], r["vdsat"]))
    print("  (Valid at the VDS used in the sweep; re-check in a DC operating point.)")
