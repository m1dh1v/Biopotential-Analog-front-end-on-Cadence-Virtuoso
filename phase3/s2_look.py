import psf, numpy as np, sys, os
from p2_metrics import bw, integ
rd = "raw/" + sys.argv[1]
p=psf.read(rd+"/pac1.0.pac"); f=p["freq"]; H=p["vout"]
G,fl,fh=bw(f,H); print("PAC sb0: G=%.2f dB fHP=%.3f fLP=%.1f"%(G,fl,fh))
n=psf.read(rd+"/pn1.pnoise"); fn=n["freq"]; out=np.abs(n["out"]); Hn=np.interp(fn,f,np.abs(H)); vin=out/Hn
for fx in [0.5,1,10,100,1000]:
    i=np.argmin(abs(fn-fx)); print(fx, "in-ref %.3g nV/rtHz"%(vin[i]*1e9))
print("Vni band %.3f uV"%(np.sqrt(integ(fn,vin**2,0.5,200))*1e6))
i1=np.argmin(abs(fn-1)); i2=np.argmin(abs(fn-1000))
for i in (i1,i2):
    tot=out[i]**2; items=sorted(((k,v[i,-1]) for k,v in n.items() if isinstance(v,np.ndarray) and v.ndim==2), key=lambda x:-x[1])
    print("f=%g"%fn[i], [(k, "%.1f%%"%(100*x/tot)) for k,x in items[:10]])
op=psf.read(rd+"/pss1.td.pss")
for k in ["vout","I1.ninv","I1.nnon","I1.I0.g1","I1.I0.f1","I1.I0.s5","c1","o1"]:
    print(k, "%.4f..%.4f"%(op[k].min(),op[k].max()))
