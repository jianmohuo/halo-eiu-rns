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
run() {  # name top srcs chparams
  local NAME=$1 TOP=$2 SRCS=$3 CH=$4
  timeout 1800 "$YS" -p "read_verilog -I$R $SRCS; hierarchy -check -top $TOP $CH; synth -top $TOP -flatten -noabc; dfflibmap -liberty $LIB; abc -liberty $LIB -script +strash;amap;stime; stat -liberty $LIB; write_blif $NET/${NAME}.blif" > "$SYN/${NAME}.log" 2>&1
  echo "RC=$? ${NAME} $(grep -a 'Chip area' "$SYN/${NAME}.log" | tail -1)" >> "$SYN/batch_result.txt"
}
BASE="$R/rns_mod_add.v $R/rns_mod_mul.v $R/eiu_rns_mac_channel.v"
> "$SYN/batch_result.txt"
run ch32c0 eiu_rns_mac_channel "$BASE" "-chparam B 32 -chparam C 0"
run ch31c1 eiu_rns_mac_channel "$BASE" "-chparam B 31 -chparam C 1"
run ch33c3 eiu_rns_mac_channel "$BASE" "-chparam B 33 -chparam C 3"
run ch30c5 eiu_rns_mac_channel "$BASE" "-chparam B 30 -chparam C 5"
run naive1024 eiu_mac_naive "$R/eiu_mac_naive.v" "-chparam W 1024"
run naive4096 eiu_mac_naive "$R/eiu_mac_naive.v" "-chparam W 4096"
run array8_1024 eiu_rns_mac_array "$BASE $R/eiu_rns_mac_array.v" "-chparam NCH 8"
echo BATCH1DONE >> "$SYN/batch_result.txt"
