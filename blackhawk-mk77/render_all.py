#!/usr/bin/env python3
"""Bake the explosion and render every shot of the UH-60 Black Hawk / Mk 77 segment, then build the video.
Works on Windows, macOS and Linux; resumable (existing frames and a finished bake are skipped).

    python render_all.py <frames_root> <sim_root> [out.mp4]

Set RENDER_DEVICE=GPU to render with Cycles on the graphics card (OptiX/CUDA on NVIDIA, HIP on AMD, Metal on Apple, oneAPI on Intel).
The bake always runs on the CPU. Needs `pip install bpy numpy pillow` and ffmpeg on the PATH.
Each shot is rendered in chunks of 24 frames, each in a fresh process.
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = [("card", 72), ("approach", 96), ("release", 112), ("fall", 64), ("impact", 150), ("radius", 96), ("after", 84)]

def run(script, *args):
    print("=== %s %s  %s" % (script, " ".join(args[:1]), time.strftime("%H:%M:%S")), flush=True)
    p = subprocess.Popen([sys.executable, os.path.join(HERE, script)] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
    for line in p.stdout:
        if line.startswith(("FRAME", "RENDER_DEVICE", "Traceback", "  File", "BAKE")) or "Error" in line:
            print(line.rstrip(), flush=True)
    return p.wait()

def shot(root, name, n, sim=None, chunk=24):
    extra = ["--res", "1280x720"] + (["--sim", sim] if sim else [])
    for a in range(0, n, chunk):
        b = min(a + chunk, n) - 1
        if all(os.path.exists(os.path.join(root, name, "f%04d.png" % i)) for i in range(a, b + 1)):
            continue
        run("nshots.py", name, os.path.join(root, name), "--frames", "%d-%d" % (a, b), *extra)

def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    root, sim_root = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(root, "blackhawk_mk77.mp4")
    os.makedirs(root, exist_ok=True); os.makedirs(sim_root, exist_ok=True)
    sim = os.path.join(sim_root, "impact")
    for name, n in SHOTS:
        if name in ("impact", "radius"):
            if not os.path.exists(os.path.join(sim, "DONE")):
                run("nsim.py", "impact", sim, "176", "232", "1")
            shot(root, name, n, sim=sim)
        else:
            shot(root, name, n)
    if run("npost.py", root, out) == 0:
        print("ALL DONE  %s" % out)

if __name__ == "__main__":
    main()
