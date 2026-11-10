"""Unity-gain buffer stb (iprobe in loop) for CL = 1,2,5 pF + pz analysis of open loop (netlist level)."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psf, runsim, ota_design as od


def netlist():
    return "\n".join([
        od.header("LBIG=1e16"),
        "VIP (vip 0) vsource dc=VCM",
        "IPRB (vout vin) iprobe",
        "CLD (vout 0) capacitor c=CL",
        "I0 (vip vin vout vdd 0 nbn nbp vcn vcp) ota_fc",
        "swc sweep param=CL values=[1p 2p 5p] {",
        "  stb1 stb start=1m stop=100M dec=40 probe=IPRB",
        "}",
        # open-loop pz at CL=5p (separate open-loop copy with L/C trick)
        "VIP2 (vip2 0) vsource dc=VCM mag=1",
        "LFB2 (vout2 vin2) inductor l=LBIG",
        "CFB2 (vin2 0) capacitor c=LBIG",
        "CLD2 (vout2 0) capacitor c=5p",
        "I2 (vip2 vin2 vout2 vdd 0 nbn nbp vcn vcp) ota_fc",
        "pz1 (vout2 0) pz iprobe=VIP2 fmax=1G",
    ])


def margins(rd):
    out = []
    for k, cl in enumerate([1, 2, 5]):
        r = psf.read(os.path.join(rd, "swc-%03d_stb1.stb" % k))
        f = r["freq"]; lg = r["loopGain"]
        A = 20 * np.log10(np.abs(lg)); ph = np.unwrap(np.angle(lg)) * 180 / np.pi
        k0 = np.where(A < 0)[0][0]
        fu = np.exp(np.interp(0, [A[k0], A[k0 - 1]], [np.log(f[k0]), np.log(f[k0 - 1])]))
        pm = np.interp(np.log(fu), np.log(f), ph)
        pm = pm % 360 if pm > 0 else pm % 360  # phase of loop gain relative to -180
        pm = (np.interp(np.log(fu), np.log(f), ph) - ph[0]) + 180  # PM = 180 - phase lag
        # gain margin: where phase lag reaches 180
        lag = ph[0] - ph
        j = np.where(lag >= 180)[0]
        gm_ = -np.interp(180, lag[j[0] - 1:j[0] + 1], A[j[0] - 1:j[0] + 1]) if len(j) else np.inf
        out.append((cl, A[0], fu, pm, gm_))
        mf = os.path.join(rd, "swc-%03d_stb1.margin.stb" % k)
        if os.path.exists(mf):
            m = psf.read(mf)
            out[-1] += (float(np.atleast_1d(m.get("phaseMargin", [np.nan]))[0]),
                        float(np.atleast_1d(m.get("gainMargin", [np.nan]))[0]))
    return out


def pz(rd):
    import glob
    fs = glob.glob(os.path.join(rd, "pz1.pz*"))
    res = {}
    for f in fs:
        txt = open(f).read()
        res[os.path.basename(f)] = txt
    return res


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "it_stb"
    rd = os.path.join(runsim.HERE, "raw", name) if os.environ.get("REUSE") else runsim.run(name, netlist())
    for row in margins(rd):
        print("CL=%dp  T0=%.1f dB  fu=%.4g Hz  PM(calc)=%.1f deg  GM(calc)=%.1f dB" % row[:5] +
              ("   spectre: PM=%.1f GM=%.1f" % row[5:] if len(row) > 5 else ""))
    print(sorted(os.listdir(rd)))
