import sys
import p3_sims, runsim
nm, ws = sys.argv[1], float(sys.argv[2])
o = dict(WS1A=ws, VOSI=0, AMP=0, VOS=0, VCMA=0, VDA=0, VSTEP=0, RSTEN=0)
runsim.run(nm, "\n".join([p3_sims.hdr("tb_lna_chop", o), "save vout1 I1.ninv I1.nnon",
                          "tr tran stop=4 maxstep=10u strobeperiod=20u errpreset=moderate"]))
