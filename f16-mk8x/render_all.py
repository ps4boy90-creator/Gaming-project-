#!/usr/bin/env python3
"""Bake the three explosions and render every shot of the F-16 / Mk 82 / Mk 83 / Mk 84 segment, then build the video.
Works on Windows, macOS and Linux; resumable (existing frames and finished bakes are skipped).

    python render_all.py <frames_root> <sim_root> [out.mp4] [--only shot,shot,...]

--only renders just the named shots and skips the final edit (for running two renders side by side on one card).

Set RENDER_DEVICE=GPU to render with Cycles on the graphics card.  The bakes always run on the CPU.
Needs `pip install bpy numpy pillow` (scipy speeds up the sound) and ffmpeg on the PATH.
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = [("card", 72), ("approach", 96), ("release", 144), ("intro82", 108), ("fall", 64), ("impact82", 120), ("radius82", 96), ("intro83", 108), ("impact83", 120), ("radius83", 96),
         ("intro84", 108), ("impact84", 120), ("radius84", 96), ("after", 192)]
SIM = {s + t: "mk" + t for s in ("impact", "radius") for t in ("82", "83", "84")}
BAKE = {"mk82": ("112", "170"), "mk83": ("124", "170"), "mk84": ("132", "170")}

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
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(root, "f16_mk82_mk83_mk84.mp4")
    os.makedirs(root, exist_ok=True); os.makedirs(sim_root, exist_ok=True)
    for name, n in SHOTS:
        if only and name not in only:
            continue
        extra = ["--res", "1280x720"]
        if name in SIM:
            kind = SIM[name]; sim = os.path.join(sim_root, kind)
            if not os.path.exists(os.path.join(sim, "DONE")):
                run("vsim.py", kind, sim, BAKE[kind][0], BAKE[kind][1], "1")
            extra += ["--sim", sim_root]
        for a in range(0, n, 24):
            b = min(a + 24, n) - 1
            if not all(os.path.exists(os.path.join(root, name, "f%04d.png" % i)) for i in range(a, b + 1)):
                run("vshots.py", name, os.path.join(root, name), "--frames", "%d-%d" % (a, b), *extra)
    if only:
        print("PART DONE %s" % ",".join(only)); return
    if run("vpost.py", root, out) == 0:
        print("ALL DONE  %s" % out)

if __name__ == "__main__":
    main()
