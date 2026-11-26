#!/usr/bin/env python3
"""Bake the explosion and render every shot of the MC-130 / MOAB segment, then build the video.
Works on Windows, macOS and Linux; resumable (existing frames and finished bakes are skipped).

    python render_all.py <frames_root> <sim_root> [out.mp4] [--only shot,shot,...] [--res 1280x720] [--spp N] [--bake out:256:400]

--only renders just the named shots and skips the final edit (for running two renders side by side on one card).
--res / --spp / --bake make a quick draft (for example --res 640x360 --spp 6 --bake out:112:400).
Set RENDER_DEVICE=GPU to render with Cycles on the graphics card.  The bakes always run on the CPU.
Needs `pip install bpy numpy pillow` (scipy speeds up the sound) and ffmpeg on the PATH.
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = [("card", 72), ("approach", 96), ("intro", 96), ("release", 180), ("fall", 84), ("strike", 220), ("reach", 204), ("after", 108)]
SIM = {"strike": "out", "reach": "out"}
BAKE = {"out": ("256", "400")}                                      # resolution, frames (no noise pass)

def run(script, *args):
    print("=== %s %s  %s" % (script, " ".join(args[:2]), time.strftime("%H:%M:%S")), flush=True)
    p = subprocess.Popen([sys.executable, os.path.join(HERE, script)] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
    for line in p.stdout:
        if line.startswith(("FRAME", "RENDER_DEVICE", "Traceback", "  File", "BAKE")) or "Error" in line:
            print(line.rstrip(), flush=True)
    return p.wait()

def opt(name, default=None):
    if name in sys.argv:
        k = sys.argv.index(name); v = sys.argv[k + 1]; del sys.argv[k:k + 2]; return v
    return default

def main():
    only = opt("--only"); only = only.split(",") if only else None; res = opt("--res", "1280x720"); spp = opt("--spp"); bake = dict(BAKE)
    for item in (opt("--bake") or "").split(","):
        if item:
            k, r, f = item.split(":"); bake[k] = (r, f)
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    root, sim_root = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(root, "mc130_moab.mp4")
    os.makedirs(root, exist_ok=True); os.makedirs(sim_root, exist_ok=True)
    for name, n in SHOTS:
        if only and name not in only:
            continue
        extra = ["--res", res] + (["--spp", spp] if spp else [])
        if name in SIM:
            sim = os.path.join(sim_root, SIM[name])
            if not os.path.exists(os.path.join(sim, "DONE")):
                run("asim.py", SIM[name], sim, bake[SIM[name]][0], bake[SIM[name]][1], "0")
            extra += ["--sim", sim_root]
        for a in range(0, n, 24):
            b = min(a + 24, n) - 1
            if not all(os.path.exists(os.path.join(root, name, "f%04d.png" % i)) for i in range(a, b + 1)):
                run("ashots.py", name, os.path.join(root, name), "--frames", "%d-%d" % (a, b), *extra)
    if only:
        print("PART DONE %s" % ",".join(only)); return
    if run("apost.py", root, out) == 0:
        print("ALL DONE  %s" % out)

if __name__ == "__main__":
    main()
