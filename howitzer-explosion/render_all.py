#!/usr/bin/env python3
"""Bake the two smoke simulations and render every shot of the 155 mm howitzer segment, then build the video.
Works on Windows, macOS and Linux; resumable (existing frames and finished bakes are skipped).

    python render_all.py <frames_root> <sim_root> [out.mp4]

Set RENDER_DEVICE=GPU to render with Cycles on the graphics card (OptiX/CUDA on NVIDIA, HIP on AMD, Metal on Apple, oneAPI on Intel).
The bakes always run on the CPU. Needs `pip install bpy numpy pillow` and ffmpeg on the PATH.
Long gun-position shots are rendered in chunks of 24 frames, each in a fresh process.
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))

def run(script, *args):
    print("=== %s %s  %s" % (script, " ".join(args[:1]), time.strftime("%H:%M:%S")), flush=True)
    p = subprocess.Popen([sys.executable, os.path.join(HERE, script)] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
    for line in p.stdout:
        if line.startswith(("FRAME", "RENDER_DEVICE", "Traceback", "  File")) or "Error" in line:
            print(line.rstrip(), flush=True)
    return p.wait()

def shot(root, name, n=None, sim=None, chunk=None):
    extra = ["--res", "1280x720"] + (["--sim", sim] if sim else [])
    if chunk is None:
        run("hshots.py", name, os.path.join(root, name), *extra)
    else:
        for a in range(0, n, chunk):
            run("hshots.py", name, os.path.join(root, name), "--frames", "%d-%d" % (a, a + chunk - 1), *extra)

def bake(sim_root, kind, frames):
    d = os.path.join(sim_root, kind)
    if not os.path.exists(os.path.join(d, "DONE")):
        run("hsim.py", kind, d, "144", str(frames), "1")
    return d

def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    root, sim_root = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(root, "howitzer155.mp4")
    os.makedirs(root, exist_ok=True); os.makedirs(sim_root, exist_ok=True)
    shot(root, "card")
    shot(root, "load", 90, chunk=24); shot(root, "ram", 52, chunk=24); shot(root, "charge", 90, chunk=24)
    shot(root, "fall"); shot(root, "after")
    shot(root, "fire", 112, sim=bake(sim_root, "launch", 110), chunk=24)
    imp = bake(sim_root, "impact", 200)
    shot(root, "impact", sim=imp); shot(root, "radius", sim=imp)
    if run("hpost.py", root, out) == 0:
        print("ALL DONE  %s" % out)

if __name__ == "__main__":
    main()
