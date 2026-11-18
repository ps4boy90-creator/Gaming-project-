"""Re-cut an existing blackhawk_mk77.mp4 without re-rendering everything: put newly rendered frames in place of one or
more shots and rebuild the whole soundtrack.

  python3 nremix.py <old.mp4> <frames_root> <out.mp4> <shot> [<shot> ...]

The other shots are taken from the old video (decoded and encoded once more); the new frames get their overlays and
the same finishing filter as in npost.py.  A full run of render_all.py gives the same result from clean frames.
"""
import os, sys, json, subprocess, tempfile
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import npost as P
import nconst as C

COUNTS = [("card", 72), ("approach", 96), ("release", 112), ("fall", 64), ("impact", 150), ("radius", 96), ("after", 84)]

def main():
    old, root, out, new = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
    starts = {}; g = 0
    for name, n in COUNTS:
        starts[name] = g; g += n
    total = g / P.FPS; cnt = dict(COUNTS)
    info = json.load(open(os.path.join(root, "timeline.json")))
    metas = {name: {str(i): {"t": 0.0, "td": -1.0} for i in range(c)} for name, c in COUNTS}
    metas["card"] = {}
    metas["release"] = {str(i): {"t": (i - 20) / 96.0 if i >= 20 else -1.0, "td": -1.0} for i in range(cnt["release"])}
    metas["impact"] = {str(i): {"t": 0.0, "td": (i - 10) * C.SIM_DT} for i in range(cnt["impact"])}          # ten frames run before the hit
    tmp = tempfile.mkdtemp(prefix="nremix_"); vf = "unsharp=5:5:0.55:5:5:0.0,vignette=PI/7,noise=alls=4:allf=t+u,format=yuv420p"; segs = {}
    for shot in new:
        d = os.path.join(root, shot); meta = json.load(open(os.path.join(d, "meta.json")))
        files = sorted(f for f in os.listdir(d) if f.startswith("f") and f.endswith(".png")); n = len(files)
        assert n == cnt[shot], "expected %d %s frames, found %d" % (cnt[shot], shot, n)
        metas[shot] = {str(k): meta[str(int(f[1:5]))] for k, f in enumerate(files)}; fi, fo = P.FADES[shot]; sd = os.path.join(tmp, shot); os.makedirs(sd)
        for k, f in enumerate(files):
            frame = Image.open(os.path.join(d, f)).convert("RGB").resize((P.W, P.H), Image.LANCZOS).convert("RGBA")
            P.shadowed(frame, P.overlay_for(shot, k, n, metas[shot][str(k)], info))
            fade = min(1.0, (k + 1) / fi if fi else 1.0, (n - k) / fo if fo else 1.0)
            if fade < 1.0:
                frame = Image.blend(Image.new("RGBA", frame.size, (0, 0, 0, 255)), frame, fade)
            frame.convert("RGB").save(os.path.join(sd, "m%05d.png" % k), compress_level=1)
        segs[shot] = os.path.join(tmp, shot + ".mp4")
        subprocess.check_call(["ffmpeg", "-y", "-v", "error", "-framerate", str(P.FPS), "-i", os.path.join(sd, "m%05d.png"), "-vf", vf, "-c:v", "libx264", "-preset", "slow", "-crf", "10", "-pix_fmt", "yuv420p", segs[shot]])
        print("staged", shot, n); sys.stdout.flush()
    wav = os.path.join(tmp, "mix.wav"); P.build_audio(wav, starts, metas, total)
    inputs = ["-i", old]; parts = []; fc = []; k = 0
    for name, c in COUNTS:                                       # walk the cut: old footage or a new segment for each shot
        if name in segs:
            inputs += ["-i", segs[name]]; fc.append("[%d:v]setpts=PTS-STARTPTS[p%d]" % (len(inputs) // 2 - 1, k))
        else:
            fc.append("[0:v]trim=start_frame=%d:end_frame=%d,setpts=PTS-STARTPTS[p%d]" % (starts[name], starts[name] + c, k))
        parts.append("[p%d]" % k); k += 1
    inputs += ["-i", wav]; ai = len(inputs) // 2 - 1
    fc.append("%sconcat=n=%d:v=1:a=0[v]" % ("".join(parts), k))
    subprocess.check_call(["ffmpeg", "-y", "-v", "error"] + inputs + ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "%d:a" % ai, "-r", str(P.FPS),
                           "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-maxrate", "16M", "-bufsize", "32M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest", out])
    print("wrote", out, "%.2fs" % total)

if __name__ == "__main__":
    main()
