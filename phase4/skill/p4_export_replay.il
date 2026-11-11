load("/home/ISDL_UG_86/Desktop/cmos65/sim/afe/p4_export.il")
foreach(c '(("gm_cell" 2 1) ("lpf_gmc" 2 1) ("tb_lpf" 3 1) ("tb_chain" 2 1) ("pmos_t5" 1 1))
  printf("EXPORT %L\n" errset(P4_expTiles(car(c) cadr(c) caddr(c) 2400 1600) t)))
exit()
