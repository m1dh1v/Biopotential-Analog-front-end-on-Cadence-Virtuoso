; Phase-2 helpers (needs sim/afe/afe_util.il loaded: A_w A_set A_inst A_mos A_pin A_stub)
; connect every terminal of instance i with a stub + net label.
; MOS (gpdk nmos/pmos, nmos_u5/pmos_u2): fixed directions (D/S vertical, G left, B right).
; other symbols: stub leaves through the nearest edge of the master's pin bBox.
procedure(A_conn(cv i conns)
  let((cn isn bb x0 y0 x1 y1 p px py dl dr dd du dir m pins)
    cn = i~>master~>cellName
    isn = member(cn '("nmos" "nmos_u5"))
    if(member(cn '("nmos" "pmos" "nmos_u5" "pmos_u2")) then
      foreach(c conns
        dir = case(car(c) ("G" "l") ("B" "r") ("D" if(isn "u" "d")) ("S" if(isn "d" "u")))
        A_stub(cv i car(c) cadr(c) dir if(car(c) == "B" 0.375 0.25)))
    else
      pins = foreach(mapcar tm i~>master~>terminals A_pin(i tm~>name))
      x0 = apply('min mapcar('xCoord pins)) x1 = apply('max mapcar('xCoord pins))
      y0 = apply('min mapcar('yCoord pins)) y1 = apply('max mapcar('yCoord pins))
      foreach(c conns
        p = A_pin(i car(c)) px = xCoord(p) py = yCoord(p)
        dl = px - x0 dr = x1 - px dd = py - y0 du = y1 - py
        m = min(dl dr dd du)
        dir = cond(((x1 - x0) < 0.01 if(du <= dd "u" "d"))
                   ((y1 - y0) < 0.01 if(dl <= dr "l" "r"))
                   ((m == dl) "l") ((m == dr) "r") ((m == du) "u") (t "d"))
        A_stub(cv i car(c) cadr(c) dir 0.25)))))
