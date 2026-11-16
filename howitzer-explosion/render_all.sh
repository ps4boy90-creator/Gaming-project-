#!/usr/bin/env bash
# Render every shot of the 155 mm howitzer segment (resumable: existing frames are skipped), then run post.
# usage: ./render_all.sh <frames_root> <sim_root> [out.mp4]      sims are baked into <sim_root>/launch and <sim_root>/impact
# Long gun-position shots are rendered in chunks of 24 frames, each in a fresh process.
set -u
ROOT=${1:?frames root}; SIM=${2:?sim root}; OUT=${3:-$ROOT/howitzer155.mp4}
HERE="$(cd "$(dirname "$0")" && pwd)"; PY=${PY:-python3}
mkdir -p "$ROOT"
run() { echo "=== $1 $(date +%T)"; "$PY" "$HERE/hshots.py" "$@" 2>&1 | grep --line-buffered -E "^FRAME|Error|Traceback|  File" ; }
chunks() { shot=$1; n=$2; shift 2; a=0; while [ $a -lt $n ]; do b=$((a + 23)); run "$shot" "$ROOT/$shot" --res 1280x720 --frames "$a-$b" "$@"; a=$((b + 1)); done; }
run card "$ROOT/card" --res 1280x720
chunks load 90
chunks ram 52
chunks charge 90
run fall  "$ROOT/fall"  --res 1280x720
run after "$ROOT/after" --res 1280x720
while pgrep -f "hsim.py" > /dev/null; do sleep 20; done      # a bake started elsewhere: let it finish
[ -f "$SIM/launch/DONE" ] || "$PY" "$HERE/hsim.py" launch "$SIM/launch" 144 110 1
chunks fire 112 --sim "$SIM/launch"
while pgrep -f "hsim.py" > /dev/null; do sleep 20; done
[ -f "$SIM/impact/DONE" ] || "$PY" "$HERE/hsim.py" impact "$SIM/impact" 144 200 1
run impact "$ROOT/impact" --sim "$SIM/impact" --res 1280x720
run radius "$ROOT/radius" --sim "$SIM/impact" --res 1280x720
echo "=== post $(date +%T)"
"$PY" "$HERE/hpost.py" "$ROOT" "$OUT" && echo "ALL DONE $(date +%T)" && touch "$ROOT/ALL_DONE"
