import subprocess, time, sys, os
jobs = [["main"], ["tran", "5000", "1.0"], ["tran", "10000", "0.3"], ["tran", "20000", "0.3"], ["offset"], ["thd"],
        ["pss", "s3_W500_L1", '{"WINF":50e-6,"LIN":1e-6}'], ["pss", "s3_W500_L2", '{"WINF":50e-6,"LIN":2e-6}'],
        ["pss", "s3_W500_L4", '{"WINF":50e-6,"LIN":4e-6}'], ["pss", "s3_W20_L1", '{"WINF":2e-6,"LIN":1e-6}'],
        ["pss", "s3_W40_L1", '{"WINF":4e-6,"LIN":1e-6}'], ["pss", "s3_W100_L1", '{"WINF":10e-6,"LIN":1e-6}'],
        ["pss", "fch_10k", '{"FCH":10e3}'], ["pss", "fch_20k", '{"FCH":20e3}'], ["pss", "ch3off", '{"CH3EN":0}'],
        ["psso", "rip_5k", '{"VOSI":0.5e-3,"FCH":5e3}'], ["psso", "rip_10k", '{"VOSI":0.5e-3,"FCH":10e3}'],
        ["psso", "rip_20k", '{"VOSI":0.5e-3,"FCH":20e3}'], ["psso", "off_nom", '{}'], ["psso", "off_mm", '{"WS1A":0.88e-6}']]
sel = sys.argv[1:]
ps = []
for j in jobs:
    nm = "_".join(j[:2])
    if sel and nm not in sel:
        continue
    ps.append((nm, subprocess.Popen([sys.executable, "p3_sims.py"] + j, stdout=open("raw/logs/%s.log" % nm, "w"), stderr=subprocess.STDOUT)))
    time.sleep(2)
for nm, p in ps:
    p.wait(); print(nm, "rc", p.returncode, flush=True)
