#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LIB="${SKY130_LIB:-$SCRIPT_DIR/sky.lib}"
YS="${YOSYS:-yosys}"
R="$ROOT/rtl"
SYN="$ROOT/tmp/syn"
NET="$SCRIPT_DIR/netlists"
mkdir -p "$SYN" "$NET"
cd "$ROOT"
run() {
  local NAME=$1 TOP=$2 SRCS=$3 CH=$4 DEF=$5
  timeout 3500 "$YS" -p "read_verilog $DEF -I$R $SRCS; hierarchy -check -top $TOP $CH; synth -top $TOP -flatten -noabc; dfflibmap -liberty $LIB; abc -liberty $LIB -script +strash;amap;stime; stat -liberty $LIB; write_blif $NET/${NAME}.blif" > "$SYN/${NAME}.log" 2>&1
  echo "RC=$? ${NAME} $(grep -a 'Chip area' "$SYN/${NAME}.log" | tail -1) $(grep -a 'Delay' "$SYN/${NAME}.log" | tail -1 | grep -o 'Delay = [0-9.]*')" >> "$SYN/batch2_result.txt"
}
BASE="$R/rns_mod_add.v $R/rns_mod_mul.v $R/eiu_rns_mac_channel.v"
> "$SYN/batch2_result.txt"
run array8_4096 eiu_rns_mac_array "$BASE $R/eiu_rns_mac_array.v" "-chparam NCH 8" "-DRNS_W4096"
run mrc_1024 rns_mrc_converter "$BASE $R/rns_mrc_converter.v $R/eiu_rns_moduli_1024.vh" "" ""
echo B2A_DONE >> "$SYN/batch2_result.txt"
