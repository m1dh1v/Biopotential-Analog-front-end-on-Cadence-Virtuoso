"""Node-pole identification: AC test current into each internal OTA node (open loop, L/C trick), pole = -3 dB of |Z|."""
import os, sys, re, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psf, runsim, ota_design as od

NODES = ["tail", "f1", "f2", "x1", "p1", "p2"]

def netlist(CL="5p"):
    sub = od.subckt().replace("subckt ota_fc vip vin vout vdd vss nbn nbp vcn vcp",
        "subckt ota_fc vip vin vout vdd vss nbn nbp vcn vcp\n    parameters " + " ".join("i_%s=0" % n for n in NODES))
    sub = sub.replace("ends ota_fc", "\n".join("    IT_%s (vss %s) isource mag=i_%s" % (n, n, n) for n in NODES) + "\nends ota_fc")
    hdr = od.header("LBIG=1e16 " + " ".join("i_%s=0" % n for n in NODES)).replace(od.subckt(), sub)
    L = [hdr, "VIP (vip 0) vsource dc=VCM", "LFB (vout vin) inductor l=LBIG", "CFB (vin 0) capacitor c=LBIG",
         "CLD (vout 0) capacitor c=%s" % CL, "I0 (vip vin vout vdd 0 nbn nbp vcn vcp) ota_fc",
         "save " + " ".join("I0.%s" % n for n in NODES)]
    for k, n in enumerate(NODES):
        if k: L.append("ra%d alter param=i_%s value=0" % (k, NODES[k - 1]))
        L.append("sa%d alter param=i_%s value=1" % (k, n))
        L.append("z_%s ac start=1 stop=1G dec=40" % n)
    return "\n".join(L)

if __name__ == "__main__":
    rd = runsim.run("it_nodes", netlist())
    for n in NODES:
        r = psf.read(os.path.join(rd, "z_%s.ac" % n))
        f = r["freq"]; z = np.abs(r["I0." + n])
        # resistance plateau: max |Z| in 1 Hz..1 kHz region; pole: where |Z| falls to plateau/sqrt2 beyond the max
        i0 = np.argmax(z)
        j = i0 + np.where(z[i0:] < z[i0] / np.sqrt(2))[0][0]
        fp = np.exp(np.interp(np.log(z[i0] / np.sqrt(2)), np.log(z[j:j - 2:-1]), np.log(f[j:j - 2:-1])))
        C = 1 / (2 * np.pi * fp * z[i0])
        print("node %-5s R=%.3g ohm (peak at %.3g Hz)  pole=%.4g Hz  C_eff=%.3g pF" % (n, z[i0], f[i0], fp, C * 1e12))
