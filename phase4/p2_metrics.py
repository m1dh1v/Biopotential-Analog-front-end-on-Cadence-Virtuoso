"""Shared metric helpers for Phase-2 results."""
import numpy as np

kB, q = 1.380649e-23, 1.602176634e-19
T_NEF, UT_NEF = 300.0, 25.9e-3
FOURKT = 4 * kB * T_NEF


def bw(f, H):
    A = 20 * np.log10(np.abs(H)); i = int(np.argmax(A)); Am = A[i]
    fl = np.exp(np.interp(Am - 3, A[:i + 1], np.log(f[:i + 1])))
    fh = np.exp(np.interp(-(Am - 3), -A[i:], np.log(f[i:])))
    return Am, fl, fh


def integ(f, S, a, b, n=6000):
    x = np.logspace(np.log10(a), np.log10(b), n)
    return np.trapezoid(np.exp(np.interp(np.log(x), np.log(f), np.log(S))), x)


def noise_metrics(fn, out, fac, Hac, Itot):
    """fn/out: noise freq & output noise (V/rtHz); fac/Hac: AC differential transfer."""
    G, fhp, flp = bw(fac, Hac)
    Hn = np.exp(np.interp(np.log(fn), np.log(fac), np.log(np.abs(Hac))))
    vin = out / Hn
    Gl = 10 ** (G / 20)
    vni_band = np.sqrt(integ(fn, vin ** 2, 0.5, 200))
    vni_tot = np.sqrt(integ(fn, out ** 2, fn[0], fn[-1])) / Gl
    BW = flp - fhp
    nef = vni_tot * np.sqrt(2 * Itot / (np.pi * UT_NEF * FOURKT * BW))
    return dict(G=G, fhp=fhp, flp=flp, vin=vin, vni_band=vni_band, vni_tot=vni_tot, BW=BW, NEF=nef, PEF=nef ** 2 * 1.8,
                vin1=np.interp(1, fn, vin), vin1k=np.interp(1e3, fn, vin))
