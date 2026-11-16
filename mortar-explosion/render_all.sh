#!/usr/bin/env bash
# Render every shot of the 120 mm mortar segment (resumable: existing frames are skipped), then run post.
# usage: ./render_all.sh <frames_root> <sim_root> [out.mp4]      sims are baked into <sim_root>/launch and <sim_root>/impact
set -u
ROOT=${1:?frames root}; SIM=${2:?sim root}; OUT=${3:-$ROOT/mortar120.mp4}
HERE="$(cd "$(dirname "$0")" && pwd)"; PY=${PY:-python3}
mkdir -p "$ROOT"
run() { echo "=== $1 $(date +%T)"; "$PY" "$HERE/mshots.py" "$@" 2>&1 | grep --line-buffered -E "^FRAME|Error|Traceback|  File" ; }
run card   "$ROOT/card"   --res 1280x720
run load   "$ROOT/load"   --res 1280x720
run fall   "$ROOT/fall"   --res 1280x720
run after  "$ROOT/after"  --res 1280x720
while pgrep -f "msim.py" > /dev/null; do sleep 20; done      # a bake started elsewhere: let it finish
[ -f "$SIM/launch/DONE" ] || "$PY" "$HERE/msim.py" launch "$SIM/launch" 128 110 1
run fire   "$ROOT/fire"   --sim "$SIM/launch" --res 1280x720
while pgrep -f "msim.py" > /dev/null; do sleep 20; done
[ -f "$SIM/impact/DONE" ] || "$PY" "$HERE/msim.py" impact "$SIM/impact" 144 200 1
run impact "$ROOT/impact" --sim "$SIM/impact" --res 1280x720
run radius "$ROOT/radius" --sim "$SIM/impact" --res 1280x720
echo "=== post $(date +%T)"
"$PY" "$HERE/mpost.py" "$ROOT" "$OUT" && echo "ALL DONE $(date +%T)" && touch "$ROOT/ALL_DONE"
