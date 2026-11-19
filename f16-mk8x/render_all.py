#!/usr/bin/env python3
"""Bake the two explosions and render every shot of the F-16 / Mk 82 / Mk 83 segment, then build the video.
Works on Windows, macOS and Linux; resumable (existing frames and finished bakes are skipped).

    python render_all.py <frames_root> <sim_root> [out.mp4]

Set RENDER_DEVICE=GPU to render with Cycles on the graphics card.  The bakes always run on the CPU.
Needs `pip install bpy numpy pillow` (scipy speeds up the sound) and ffmpeg on the PATH.
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = [("card", 72), ("approach", 96), ("release", 130), ("fall", 64), ("impact82", 120), ("impact83", 120), ("radius82", 96), ("radius83", 96), ("after", 72)]
RES = {"radius82": "640x720", "radius83": "640x720"}          # the two halves of the side-by-side comparison
SIM = {"impact82": "mk82", "radius82": "mk82", "impact83": "mk83", "radius83": "mk83"}
BAKE = {"mk82": ("112", "170"), "mk83": ("124", "170")}

def run(script, *args):
    print("=== %s %s  %s" % (script, " ".join(args[:1]), time.strftime("%H:%M:%S")), flush=True)
    p = subprocess.Popen([sys.executable, os.path.join(HERE, script)] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
    for line in p.stdout:
        if line.startswith(("FRAME", "RENDER_DEVICE", "Traceback", "  File", "BAKE")) or "Error" in line:
            print(line.rstrip(), flush=True)
    return p.wait()

def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    root, sim_root = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(root, "f16_mk82_mk83.mp4")
    os.makedirs(root, exist_ok=True); os.makedirs(sim_root, exist_ok=True)
    for name, n in SHOTS:
        extra = ["--res", RES.get(name, "1280x720")]
        if name in SIM:
            kind = SIM[name]; sim = os.path.join(sim_root, kind)
            if not os.path.exists(os.path.join(sim, "DONE")):
                run("vsim.py", kind, sim, BAKE[kind][0], BAKE[kind][1], "1")
            extra += ["--sim", sim_root]
        for a in range(0, n, 24):
            b = min(a + 24, n) - 1
            if not all(os.path.exists(os.path.join(root, name, "f%04d.png" % i)) for i in range(a, b + 1)):
                run("vshots.py", name, os.path.join(root, name), "--frames", "%d-%d" % (a, b), *extra)
    if run("vpost.py", root, out) == 0:
        print("ALL DONE  %s" % out)

if __name__ == "__main__":
    main()
