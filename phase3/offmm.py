import sys
import p3_sims, runsim
v = sys.argv[1]
an = {"a": "pss1 pss fund=FCH harms=50 tstab=10/FCH errpreset=moderate",
      "b": "pss1 pss fund=FCH harms=50 tstab=40/FCH errpreset=conservative steadyratio=0.01 maxstep=0.5u"}[v]
runsim.run("off_mm" + v, "\n".join([p3_sims.hdr("tb_lna_chop", {"WS1A": 0.88e-6}), p3_sims.SAVE, an]))
