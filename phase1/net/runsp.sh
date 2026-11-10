#!/bin/bash
# usage: runsp.sh <netlist.scs> <rawdir>   (runs in ~/Desktop/cmos65/sim/afe)
export LM_LICENSE_FILE=5280@14.139.1.126 CDS_LIC_FILE=5280@14.139.1.126
export CDS_AUTO_64BIT=ALL MMSIMHOME=/cad/SPECTRE211
export PATH=/cad/SPECTRE211/bin:/cad/IC618/tools/bin:$PATH
cd ~/Desktop/cmos65/sim/afe
spectre -64 +escchars -format psfascii -raw "$2" "$1" +log "$2.log" > /dev/null 2>&1
echo "exit=$?"; grep -E "completes with|ERROR|Error" "$2.log" | head -20
