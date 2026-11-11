; export a schematic as nx x ny zoomed tiles (readable device labels), plus the full view
procedure(P4_expTiles(cell nx ny w h)
  let((win bb x0 y0 x1 y1 dx dy files f)
    win = geOpen(?lib "AFE_lib" ?cell cell ?view "schematic" ?mode "r")
    hiResizeWindow(win list(0:0 w:h))
    bb = geGetEditCellView(win)~>bBox
    x0 = xCoord(car(bb)) - 0.3  y0 = yCoord(car(bb)) - 0.3  x1 = xCoord(cadr(bb)) + 0.3  y1 = yCoord(cadr(bb)) + 0.3
    dx = (x1 - x0) / nx  dy = (y1 - y0) / ny
    for(i 0 nx-1 for(j 0 ny-1
      hiZoomIn(win list((x0 + i*dx):(y1 - (j+1)*dy) (x0 + (i+1)*dx):(y1 - j*dy)))
      f = sprintf(nil "/home/ISDL_UG_86/Desktop/cmos65/sim/afe/p4png/sch_%s_tile_r%dc%d.png" cell j+1 i+1)
      hiExportImage(?fileName f ?window win ?exportRegion 'visibleArea ?width w ?height h)
      files = cons(f files)))
    hiCloseWindow(win)
    files))
