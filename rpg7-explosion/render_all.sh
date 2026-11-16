#!/usr/bin/env bash
# Render every shot of the RPG-7 segment (resumable: existing frames are skipped), then run post.
# usage: ./render_all.sh <frames_root> <sim_root> [out.mp4]      sims are baked into <sim_root>/launch and <sim_root>/impact
set -u
ROOT=${1:?frames root}; SIM=${2:?sim root}; OUT=${3:-$ROOT/rpg7.mp4}
HERE="$(cd "$(dirname "$0")" && pwd)"; PY=${PY:-python3}
mkdir -p "$ROOT"
[ -f "$SIM/launch/DONE" ] || "$PY" "$HERE/rsim.py" launch "$SIM/launch" 160 100 1
run() { echo "=== $1 $(date +%T)"; "$PY" "$HERE/rshots.py" "$@" 2>&1 | grep --line-buffered -E "^FRAME|Error|Traceback|  File" ; }
run card   "$ROOT/card"   --res 1280x720
run follow "$ROOT/follow" --res 1280x720
run after  "$ROOT/after"  --res 1280x720
run fire   "$ROOT/fire"   --sim "$SIM/launch" --res 1280x720
[ -f "$SIM/impact/DONE" ] || "$PY" "$HERE/rsim.py" impact "$SIM/impact" 144 130 1
run impact "$ROOT/impact" --sim "$SIM/impact" --res 1280x720
run behind "$ROOT/behind" --sim "$SIM/impact" --res 1280x720
echo "=== post $(date +%T)"
"$PY" "$HERE/rpost.py" "$ROOT" "$OUT" && echo "ALL DONE $(date +%T)" && touch "$ROOT/ALL_DONE"
