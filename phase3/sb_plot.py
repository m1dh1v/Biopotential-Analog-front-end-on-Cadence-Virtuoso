import json, numpy as np, matplotlib, os, psf
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from contrib import group_name
p=psf.read("raw/sb30/pac1.0.pac"); H1=np.abs(p["vout1"])[list(p["freq"]).index(1.0)]
rows=[]
for sb in (30,100,300,1000,3000,10000,30000,100000):
    fn="raw/sb%d/pn1.pnoise"%sb
    if not os.path.exists(fn): continue
    n=psf.read(fn); f=list(n["freq"]); i=f.index(1.0); o=np.abs(n["out"])[i]
    ch1=sum(v[i,-1] for k,v in n.items() if isinstance(v,np.ndarray) and v.ndim==2 and k.startswith("I1.") and group_name(k)=="CH1 switches")
    rows.append((sb,float(o/H1),float(ch1/H1**2),float((o**2-ch1)/H1**2)))
r=np.array(rows)
fig,ax=plt.subplots(figsize=(7.5,4.5))
ax.loglog(r[:,0]*5e3,r[:,1]*1e6,"o-",label="total input-referred @ 1 Hz")
ax.loglog(r[:,0]*5e3,np.sqrt(r[:,2])*1e6,"s--",label="CH1 switches")
ax.loglog(r[:,0]*5e3,np.sqrt(r[:,3])*1e6,"^:",label="everything else")
ax.axhline(19.4,color="r",lw=0.8,ls="-.",label="analytic SC kT/C, C_s = 72 fF (19.4 uV/rtHz)")
ax.set_xlabel("folded bandwidth = maxsideband x f_chop [Hz]"); ax.set_ylabel("uV/rtHz @ 1 Hz")
ax.set_title("Pnoise convergence vs maxsideband (lna_chop, f_chop = 5 kHz)"); ax.grid(True,which="both",alpha=0.3); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig("plots/6_pnoise_sideband_convergence.png",dpi=150)
json.dump(rows,open("plots/sideband_convergence.json","w"),indent=1)
for x in rows: print("sb=%6d  %.2f uV/rtHz"%(x[0],x[1]*1e6))
