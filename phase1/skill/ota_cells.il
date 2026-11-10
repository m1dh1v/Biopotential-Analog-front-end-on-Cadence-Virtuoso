; AFE_lib composite unit cells + ota_fc schematic/symbol  (Phase 1)
; nmos_u5 : 5 x gpdk180 nmos 0.4u/20u in series (common gate)  -> 50 nA unit, composite gm/ID ~6
; pmos_u2 : 2 x gpdk180 pmos 1u/20u   in series (common gate)  -> 50 nA unit, composite gm/ID ~6.7

procedure(A_pinat(cv name xy)
  schCreatePin(cv dbOpenCellViewByType("basic" "iopin" "symbol") name "inputOutput" nil xy "R0"))

procedure(A_unit(cell dev W L ns)
  let((cv top bot i y0 sym src lab)
    cv = dbOpenCellViewByType("AFE_lib" cell "schematic" "schematic" "w")
    for(k 0 ns-1
      i = A_inst(cv "gpdk180" dev sprintf(nil "M%d" k) 0:(-0.5*k) "R0" nil)
      A_mos(i W L 1 1)
      ; gate stub to x=-0.25 rail, body stub to x=0.625 rail
      A_w(cv list(0:(-0.5*k) -0.25:(-0.5*k)))
      A_w(cv list(0.25:(-0.5*k) 0.625:(-0.5*k)))
      when(k < ns-1 A_w(cv list(0.25:(-0.1875-0.5*k) 0.25:(-0.3125-0.5*k)))))
    y0 = -0.5*(ns-1)
    A_w(cv list(-0.25:0 -0.25:y0)) A_w(cv list(0.625:0 0.625:y0))
    ; top / bottom terminals: nmos D top S bottom; pmos S top D bottom
    top = if(dev == "nmos" "D" "S") bot = if(dev == "nmos" "S" "D")
    A_w(cv list(0.25:0.1875 0.25:0.5))  A_pinat(cv top 0.25:0.5)
    A_w(cv list(0.25:(y0-0.1875) 0.25:(y0-0.5)))  A_pinat(cv bot 0.25:(y0-0.5))
    A_w(cv list(-0.25:y0 -0.5:y0)) A_pinat(cv "G" -0.5:y0)
    A_w(cv list(0.625:y0 0.875:y0)) A_pinat(cv "B" 0.875:y0)
    schCheck(cv) dbSave(cv)
    ; symbol: copy of the gpdk180 device symbol, parameter labels replaced by a size note
    src = dbOpenCellViewByType("gpdk180" dev "symbol")
    sym = dbCopyCellView(src "AFE_lib" cell "symbol" nil nil t)
    foreach(s setof(x sym~>shapes x~>objType == "label" && rexMatchp("cdsParam" x~>theLabel)) dbDeleteObject(s))
    lab = dbCreateLabel(sym list("annotate" "drawing7") 0.28125:-0.1 sprintf(nil "%gu/(%dx%s)" W ns L)
                        "lowerLeft" "R0" "stick" 0.0625)
    dbSave(sym)
    list(cell cv~>modifiedButNotSaved length(cv~>instances))))

; ---------------------------------------------------------------- ota_fc
; device placement table: name master W L m  x y  D G S B
procedure(A_ota_fc()
  let((cv i x y)
    cv = dbOpenCellViewByType("AFE_lib" "ota_fc" "schematic" "schematic" "w")
    foreach(d list(
        ;  name        lib        cell       W    L     m   x     y     D       G      S      B
        list("MBP"     "AFE_lib" "pmos_u2"  nil  nil   nil -4.0  4.0  "nbp"  "nbp"  "vdd"  "vdd")
        list("M0<0:7>" "AFE_lib" "pmos_u2"  nil  nil   nil -1.0  4.0  "tail" "nbp"  "vdd"  "vdd")
        list("M1"      "gpdk180" "pmos"     50.0 "4u"  10  -2.0  1.75 "f1"   "vip"  "tail" "tail")
        list("M2"      "gpdk180" "pmos"     50.0 "4u"  10   0.0  1.75 "f2"   "vin"  "tail" "tail")
        list("M7"      "gpdk180" "pmos"     0.5  "20u" 2    2.5  4.0  "p1"   "x1"   "vdd"  "vdd")
        list("M8"      "gpdk180" "pmos"     0.5  "20u" 2    4.5  4.0  "p2"   "x1"   "vdd"  "vdd")
        list("M9"      "gpdk180" "pmos"     0.6  "1u"  1    2.5  2.25 "x1"   "vcp"  "p1"   "vdd")
        list("M10"     "gpdk180" "pmos"     0.6  "1u"  1    4.5  2.25 "vout" "vcp"  "p2"   "vdd")
        list("M5"      "gpdk180" "nmos"     0.4  "1u"  1    2.5  0.5  "x1"   "vcn"  "f1"   "vss")
        list("M6"      "gpdk180" "nmos"     0.4  "1u"  1    4.5  0.5  "vout" "vcn"  "f2"   "vss")
        list("M3<0:5>" "AFE_lib" "nmos_u5"  nil  nil   nil  2.5 -1.25 "f1"   "nbn"  "vss"  "vss")
        list("M4<0:5>" "AFE_lib" "nmos_u5"  nil  nil   nil  4.5 -1.25 "f2"   "nbn"  "vss"  "vss")
        list("MBN"     "AFE_lib" "nmos_u5"  nil  nil   nil -4.0 -1.25 "nbn"  "nbn"  "vss"  "vss"))
      x = nth(6 d) y = nth(7 d)
      i = A_inst(cv nth(1 d) nth(2 d) nth(0 d) x:y "R0" nil)
      when(nth(3 d) A_mos(i nth(3 d) nth(4 d) 1 nth(5 d)))
      ; stubs: drain/source vertical, gate left, body right
      if(member(nth(2 d) '("nmos" "nmos_u5")) then
        A_stub(cv i "D" nth(8 d) "u") A_stub(cv i "S" nth(10 d) "d")
      else
        A_stub(cv i "S" nth(10 d) "u") A_stub(cv i "D" nth(8 d) "d"))
      A_stub(cv i "G" nth(9 d) "l")
      A_stub(cv i "B" nth(11 d) "r" 0.375))
    ; pins (left edge), each with a stub + same-name label
    y = 4.5
    foreach(p '("vdd" "vss" "vip" "vin" "vout" "nbp" "nbn" "vcp" "vcn")
      cond((member(p '("vdd" "vss")) A_pinat(cv p -6.5:y))
           ((p == "vout") schCreatePin(cv dbOpenCellViewByType("basic" "opin" "symbol") p "output" nil -6.5:y "R0"))
           (t schCreatePin(cv dbOpenCellViewByType("basic" "ipin" "symbol") p "input" nil -6.5:y "R0")))
      A_w(cv list(-6.5:y -6.0:y))
      schCreateWireLabel(cv nil -6.0:y p "lowerLeft" "R0" "stick" 0.0625 nil)
      y = y - 0.5)
    schCheck(cv) dbSave(cv)
    list(cv~>modifiedButNotSaved sort(dbGetq(cv "nets")~>name nil))))

procedure(A_ota_sym()
  ; auto-generated symbol: inputs left, output right, inout (supplies) top/bottom
  schPinListToSymbol("AFE_lib" "ota_fc" "symbol" schSchemToPinList("AFE_lib" "ota_fc" "schematic")))
