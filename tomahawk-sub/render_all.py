#!/usr/bin/env python3
"""Bake the explosion and render every shot of the submarine-launched Tomahawk segment, then build the video.
Works on Windows, macOS and Linux; resumable (existing frames and a finished bake are skipped).

    python render_all.py <frames_root> <sim_root> [out.mp4] [--only shot,shot,...]

--only renders just the named shots and skips the final edit (for running two renders side by side on one card).
Set RENDER_DEVICE=GPU to render with Cycles on the graphics card.  The bake always runs on the CPU.
Needs `pip install bpy numpy pillow` (scipy speeds up the sound) and ffmpeg on the PATH.
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = [("card", 72), ("depth", 84), ("hatch", 60), ("eject", 108), ("broach", 144), ("wings", 60), ("boost", 120), ("landfall", 72), ("cruise", 144), ("terminal", 132), ("impact", 132), ("radius", 96), ("after", 120)]
SIM = ("impact", "radius")
BAKE = ("128", "190")

def run(script, *args):
    print("=== %s %s  %s" % (script, " ".join(args[:1]), time.strftime("%H:%M:%S")), flush=True)
    p = subprocess.Popen([sys.executable, os.path.join(HERE, script)] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
    for line in p.stdout:
        if line.startswith(("FRAME", "RENDER_DEVICE", "Traceback", "  File", "BAKE")) or "Error" in line:
            print(line.rstrip(), flush=True)
    return p.wait()

def main():
    only = None
    if "--only" in sys.argv:
        k = sys.argv.index("--only"); only = sys.argv[k + 1].split(","); del sys.argv[k:k + 2]
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    root, sim_root = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(root, "tomahawk_submarine.mp4")
    os.makedirs(root, exist_ok=True); os.makedirs(sim_root, exist_ok=True); sim = os.path.join(sim_root, "hit")
    for name, n in SHOTS:
        if only and name not in only:
            continue
        extra = ["--res", "1280x720"]
        if name in SIM:
            if not os.path.exists(os.path.join(sim, "DONE")):
                run("tsim.py", sim, BAKE[0], BAKE[1], "1")
            extra += ["--sim", sim]
        for a in range(0, n, 24):
            b = min(a + 24, n) - 1
            if not all(os.path.exists(os.path.join(root, name, "f%04d.png" % i)) for i in range(a, b + 1)):
                run("tshots.py", name, os.path.join(root, name), "--frames", "%d-%d" % (a, b), *extra)
    if only:
        print("PART DONE %s" % ",".join(only)); return
    if run("tpost.py", root, out) == 0:
        print("ALL DONE  %s" % out)

if __name__ == "__main__":
    main()
