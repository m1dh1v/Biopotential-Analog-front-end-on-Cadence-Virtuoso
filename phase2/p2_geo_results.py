import os, sys, json, numpy as np, psf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p2_metrics import noise_metrics
HERE = os.path.dirname(os.path.abspath(__file__))
rows = []
for cin, cf in [("20p", 200e-15), ("10p", 100e-15)]:
    rd = os.path.join(HERE, "raw", "p2_geo_" + cin)
    for k, L in enumerate([1, 2, 4]):
        op = psf.read(os.path.join(rd, "swL-%03d_op.dc" % k)); g = lambda x: float(np.atleast_1d(op[x])[0])
        ac = psf.read(os.path.join(rd, "swL-%03d_ac1.ac" % k)); nz = psf.read(os.path.join(rd, "swL-%03d_nz.noise" % k))
        Itot = abs(g("VDD1:p"))
        m = noise_metrics(nz["freq"], np.abs(nz["out"]), ac["freq"], ac["vout1"], Itot)
        cgg = abs(g("I1.I0.M1:cgg")); Cin = float(cin[:-1]) * 1e-12
        pen = (Cin + cf + cgg) / Cin
        rows.append(dict(Cin=cin, L=L, WL=500 * L, cgg=cgg, gmid=abs(g("I1.I0.M1:gm") / g("I1.I0.M1:ids")), pen=pen, Itot=Itot,
                         **{k_: v for k_, v in m.items() if k_ != "vin"}))
print("Cin  L   W*L    Cgg(M1)  gm/ID  (Cin+Cf+Cp)/Cin  gain   f_HP    f_LP    in@1Hz  in@1k   Vni(0.5-200)  Vni_tot  NEF   PEF")
for r in rows:
    print("%-4s %du %5d  %6.2fpF  %5.1f   %6.3f        %5.2f  %5.3f  %6.0f  %6.0fn  %5.1fn   %.3f uV      %.3f uV  %.2f  %.2f" % (
        r["Cin"], r["L"], r["WL"], r["cgg"] * 1e12, r["gmid"], r["pen"], r["G"], r["fhp"], r["flp"], r["vin1"] * 1e9,
        r["vin1k"] * 1e9, r["vni_band"] * 1e6, r["vni_tot"] * 1e6, r["NEF"], r["PEF"]))
print("Itot(VDD1) = %.1f nA" % (rows[0]["Itot"] * 1e9))
json.dump(rows, open(os.path.join(HERE, "plots", "geo_table.json"), "w"), indent=1)
