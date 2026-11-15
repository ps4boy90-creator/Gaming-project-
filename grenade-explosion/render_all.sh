#!/usr/bin/env bash
# Render every shot (resumable: existing frames are skipped), then run post.
# usage: ./render_all.sh <frames_root> <sim_cache_dir> [out.mp4]
set -u
ROOT=${1:?frames root}; SIM=${2:?sim cache dir}; OUT=${3:-$ROOT/grenade_m67.mp4}
HERE="$(cd "$(dirname "$0")" && pwd)"; PY=${PY:-python3}
mkdir -p "$ROOT"
[ -f "$SIM/DONE" ] || "$PY" "$HERE/sim_bake.py" "$SIM" 128 180 1
run() { echo "=== $1 $(date +%T)"; "$PY" "$HERE/shots.py" "$@" 2>&1 | grep --line-buffered -E "^FRAME|Error|Traceback|  File" ; }
run blast  "$ROOT/blast"  --sim "$SIM" --res 1280x720
run top    "$ROOT/top"    --sim "$SIM" --res 1280x720
run follow "$ROOT/follow" --res 1280x720
run throw  "$ROOT/throw"  --res 1280x720
run macro  "$ROOT/macro"  --res 1280x720
run card   "$ROOT/card"   --res 1280x720
echo "=== post $(date +%T)"
"$PY" "$HERE/post.py" "$ROOT" "$OUT" && echo "ALL DONE $(date +%T)" && touch "$ROOT/ALL_DONE"
