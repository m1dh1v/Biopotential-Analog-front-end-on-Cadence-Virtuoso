"""Pnoise maxsideband convergence check (does folded switch kT/C noise grow with more sidebands?)."""
import sys
import p3_sims, runsim
sb = int(sys.argv[1])
L = [p3_sims.hdr("tb_lna_chop", {}), "save vout1",
     "pss1 pss fund=FCH harms=20 tstab=5/FCH errpreset=conservative",
     "pac1 pac values=[0.5 1 2 5 10 20 50 100 200 1000] sweeptype=absolute maxsideband=10",
     "pn1 (vout1 0) pnoise values=[1] sweeptype=absolute maxsideband=%d noisetype=timeaverage" % sb]
runsim.run("sb%d" % sb, "\n".join(L), quiet=True)
print("done", sb)
