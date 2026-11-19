"""Finishing for the F-16 / Mk 82 / Mk 83 segment: upscale to 1080p, title card, HUD overlays, the side-by-side
comparison of the two bursts, synthesized sound, encode.

  python3 vpost.py <frames_root> <out.mp4> [--draft]
"""
import os, sys, json, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "blackhawk-mk77"))
import post as gp
from post import W, H, FPS, SR, AMBER, RED, INK, DIM, PANEL, F_TITLE, F_SEMI, F_MED, ease, text, shadowed, lower, callout
from npost import readout, dashed, _mod

ORDER = ["card", "approach", "release", "fall", "impact82", "impact83", "radius", "after"]
SPECS = [("AIRCRAFT", "F-16C Fighting Falcon  ·  15.0 m long"), ("WING", "9.45 m span  ·  40° sweep"), ("MK 82", "500 lb class  ·  2.22 m  ·  87 kg filling"),
         ("MK 83", "1,000 lb class  ·  3.00 m  ·  202 kg filling"), ("RELEASE", "450 kt, level, at 1,500 m"), ("FALL", "17.5 s  ·  3.9 km of forward throw"), ("ON BUNKERS", "Holes and scars, not destruction")]

def tag(d, a=1.0):
    text(d, (64, 54), "EXPLOSION COMPARISON", F_SEMI(30), INK, a, tracking=4)
    d.rectangle([64, 96, 64 + 54, 100], fill=(*AMBER, int(255 * a)))
    text(d, (130, 84), "07  ·  F-16  ·  MK 82 AND MK 83 BOMBS", F_MED(26), DIM, a, tracking=2)

def card_frame(img, i, n):
    base = Image.new("RGBA", (W, H), (*PANEL, 255))
    base.paste(img.convert("RGB").resize((W // 2, H), Image.LANCZOS), (0, 0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    grad = Image.linear_gradient("L").rotate(90, expand=True).resize((90, H))
    seam = Image.new("RGBA", (90, H), (*PANEL, 255)); seam.putalpha(grad.point(lambda v: 255 - v))
    base.alpha_composite(seam.transpose(Image.FLIP_LEFT_RIGHT), (W // 2 - 90, 0))
    t = i / FPS; x0 = W // 2 + 96
    text(d, (x0, 150), "EXPLOSION COMPARISON  ·  07", F_SEMI(30), DIM, ease((t - 0.10) / 0.5), tracking=5)
    a = ease((t - 0.20) / 0.5); text(d, (x0 + int((1 - a) * 40), 196), "F-16", F_TITLE(210), INK, a)
    a = ease((t - 0.35) / 0.5); text(d, (x0 + int((1 - a) * 40), 446), "MK 82 AND MK 83 BOMBS", F_TITLE(54), AMBER, a, tracking=2)
    a = ease((t - 0.45) / 0.5); d.rectangle([x0, 528, x0 + int(820 * a), 531], fill=(*AMBER, int(255 * a)))
    y = 562
    for k, (lab, val) in enumerate(SPECS):
        a = ease((t - 0.65 - 0.12 * k) / 0.45); dx = int((1 - a) * 28); hot = lab == "ON BUNKERS"
        text(d, (x0 + dx, y), lab, F_SEMI(31), RED if hot else DIM, a, tracking=3)
        text(d, (x0 + 300 + dx, y - 4), val, F_SEMI(40) if hot else F_MED(38), INK, a)
        y += 60
    text(d, (x0, 1000), "The Mk 83 is cleared for the F-16 but rarely carried by US Air Force jets.", F_MED(28), DIM, ease((t - 1.9) / 0.6))
    base.alpha_composite(ov)
    return base.convert("RGB")

def overlay_for(shot, i, n, m, info):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    t = m["t"]; td = m["td"]; an = m.get("anchors", {})
    tag(d, ease(i / 8.0) if shot == "approach" else 1.0)
    io = ease((i - 5) / 9.0) * (1 - ease((i - (n - 7)) / 7.0))
    if shot == "approach":
        lower(d, "RUNNING IN", "F-16C  ·  a Mk 82 under the left wing, a Mk 83 under the right, fuel tanks inboard", io)
        readout(d, "HEIGHT", "1,500 m", ease((i - 10) / 10.0), AMBER, "SPEED  450 kt")
        a1 = ease((i - 30) / 8.0) * (1 - ease((i - (n - 8)) / 7.0)); a2 = ease((i - 44) / 8.0) * (1 - ease((i - (n - 8)) / 7.0))
        if a1 > 0:
            callout(d, an["mk82"][0] * W, an["mk82"][1] * H, "MK 82", "500 lb CLASS  ·  87 kg OF EXPLOSIVE", AMBER, a1, dx=-520, dy=210)
        if a2 > 0:
            text(d, (W - 64, 150), "MK 83", F_TITLE(64), RED, a2, anchor="ra"); text(d, (W - 64, 226), "UNDER THE FAR WING  ·  1,000 lb CLASS  ·  202 kg OF EXPLOSIVE", F_SEMI(28), INK, a2, anchor="ra", tracking=2)
    elif shot == "release":
        if t < 0:
            lower(d, "OVER THE RELEASE POINT", "Level at 1,500 m  ·  3.9 km short of the first bunker", ease((i - 2) / 6.0))
        else:
            lower(d, "RELEASE", "The Mk 82 goes first  ·  the Mk 83 follows 0.6 s later, to land 153 m further on", 1 - ease((i - (n - 8)) / 8.0))
            readout(d, "SLOW MOTION", "T + %03d ms" % round(t * 1000), 1.0, INK, "MK 82 AWAY" if t < info["T83"] else "MK 83 AWAY")
            a1 = ease(t / 0.08) * (1 - ease((t - 0.55) / 0.1)); a2 = ease((t - info["T83"]) / 0.08) * (1 - ease((i - (n - 8)) / 7.0))
            if a1 > 0 and 0.03 < an["mk82"][1] < 0.97:
                callout(d, an["mk82"][0] * W, an["mk82"][1] * H, "MK 82", "227 kg", AMBER, a1, dx=110, dy=-90)
            if a2 > 0 and 0.03 < an["mk83"][1] < 0.97:
                callout(d, an["mk83"][0] * W, an["mk83"][1] * H, "MK 83", "447 kg", RED, a2, dx=-330, dy=90)
    elif shot == "fall":
        a = ease((i - 2) / 8.0)
        readout(d, "HEIGHT", "%d m" % round(m.get("alt", 0)), a, AMBER, "%d m/s  ·  IMPACT IN %.1f s" % (round(m.get("v", 0)), max(-td, 0)))
        lower(d, "%d SECONDS LATER" % round(info["TOF"]["mk82"]), "%.1f km down range  ·  arriving at about %d m/s and %d°" % (info["FWD"]["mk82"] / 1000.0, round(info["V_HIT"]["mk82"]), round(info["ANGLE"]["mk82"])),
              ease((i - 6) / 10.0) * (1 - ease((i - (n - 8)) / 8.0)))
    elif shot in ("impact82", "impact83"):
        readout(d, "SLOW MOTION", "T + %03d ms" % max(0, round(td * 1000)), ease((i - 2) / 6.0))
        a = ease((i - 12) / 10.0) * (1 - ease((i - (n - 12)) / 10.0))
        if shot == "impact82":
            lower(d, "MK 82", "87 kg of explosive  ·  instantaneous fuze on the roof of the first bunker", a)
        else:
            lower(d, "MK 83", "202 kg of explosive  ·  the second bunker, 0.6 s later", a)
    elif shot == "after":
        a1 = ease((i - 8) / 8.0) * (1 - ease((i - 50) / 8.0))
        if a1 > 0:
            callout(d, an["mk82"][0] * W, an["mk82"][1] * H, "MK 82", "ROOF HOLED  ·  STRUCTURE STANDING", AMBER, a1, dx=-120, dy=-250)
            callout(d, an["mk83"][0] * W, an["mk83"][1] * H, "MK 83", "ROOF BROKEN OPEN  ·  WALLS STANDING", RED, a1, dx=-560, dy=-330)
        lower(d, "WHAT THEY DO TO A BUNKER", "General-purpose bombs crater, spall and hole  ·  hardened targets need penetrating bombs", ease((i - 40) / 12.0))
    return ov

def compare_frame(im82, im83, i, n, m82, m83, info):
    """Left half the Mk 82, right half the Mk 83, same camera and scale, with the radii drawn on the ground."""
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 255)); hw = W // 2
    for k, (im, x0) in enumerate(((im82, 0), (im83, hw))):
        frame.paste(im.convert("RGB").resize((hw, H), Image.LANCZOS), (x0, 0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov); tag(d, 1.0)
    d.rectangle([hw - 2, 0, hw + 1, H], fill=(*PANEL, 255))
    td = m82["td"]; a0 = ease((td - 0.25) / 0.3); a1 = ease((td - 0.9) / 0.3)
    for kind, m, x0, name, fill in (("mk82", m82, 0, "MK 82", 87), ("mk83", m83, hw, "MK 83", 202)):
        P = lambda q: (x0 + q[0] * hw, q[1] * H)
        text(d, (x0 + hw - 48, 150), name, F_TITLE(96), INK, 1.0, anchor="ra"); text(d, (x0 + hw - 48, 262), "%d kg OF EXPLOSIVE" % fill, F_SEMI(30), DIM, 1.0, anchor="ra", tracking=3)
        ps = [P(q) for q in m.get("path_struct", [])]; pb = [P(q) for q in m.get("path_blast", [])]
        if a0 > 0 and len(ps) > 2:
            d.line([(x, y + 2) for x, y in ps], fill=(0, 0, 0, int(120 * a0)), width=7); d.line(ps, fill=(*RED, int(235 * a0)), width=5)
            callout(d, *P(m["anchors"]["struct"]), "%d m" % round(info["R_STRUCT"][kind]), "STRUCTURES DESTROYED", RED, a0, dx=-300, dy=200)
        if a1 > 0 and len(pb) > 2:
            dashed(d, pb, (*AMBER, int(235 * a1)), 4)
            callout(d, *P(m["anchors"]["blast"]), "%d m" % round(info["R_BLAST"][kind]), "34 kPa BLAST", AMBER, a1, dx=-10, dy=-250)
    lower(d, "SIDE BY SIDE", "Same camera, same scale  ·  Mk 82 radii published, Mk 83 scaled by the cube root of the filling", ease((td - 0.5) / 0.3))
    shadowed(frame, ov)
    return frame

# ------------------------------------------------------------------ sound
def s_jet(dur, seed=3):
    """A jet close by: broadband roar with a thin compressor whine over it."""
    n = int(dur * SR); t = np.arange(n) / SR
    x = gp.bp(gp.noise(n), 120, 1800) * 1.4 * _mod(n, 2.0, 0.25, seed) + gp.hp(gp.lp(gp.noise(n), 7000, 1), 2500) * 0.25 + gp.lp(gp.noise(n), 100, 2) * 1.6
    return x + 0.05 * np.sin(2 * np.pi * 2900 * t + 3 * np.sin(2 * np.pi * 0.7 * t))

def s_blast(scale):
    """A large bomb at a distance of a few dozen metres: sharp crack, then a long heavy rumble."""
    n = int((3.5 + scale) * SR); t = np.arange(n) / SR
    crack = gp.noise(n) * np.exp(-t / 0.012) * 3.0
    body = gp.lp(gp.noise(n), 160 / scale, 3) * 9.0 * np.minimum(1.0, t / 0.01) * np.exp(-t / (0.55 * scale))
    tail = gp.bp(gp.noise(n), 60, 500) * 1.6 * np.exp(-t / (1.3 * scale)) * _mod(n, 3.0, 0.4, 17)
    sub = np.sin(2 * np.pi * np.cumsum(np.linspace(55 / scale, 24, n)) / SR) * 1.4 * np.exp(-t / (0.5 * scale))
    return crack + body + tail + sub

def build_audio(path, starts, metas, total):
    mx = gp.Mix(total); T = {k: v / FPS for k, v in starts.items()}; L = {k: len(metas[k]) / FPS for k in metas}
    def when(shot, pred):
        m = metas[shot]
        for i in sorted(int(k) for k in m):
            if pred(m[str(i)]):
                return T[shot] + i / FPS
        return None
    mx.add(0.0, gp.s_drone(T["approach"] + 0.2), 0.5); mx.add(0.05, gp.s_thud(1.2), 0.5)
    for k in range(len(SPECS)):
        mx.add(0.65 + 0.12 * k, gp.s_tick(), 0.35, 0.3)
    mx.add(T["approach"] - 0.45, gp.s_whoosh(0.6, 200, 1500, 0.8), 0.35)
    la = L["approach"] + L["release"]; mx.add(T["approach"], s_jet(la, 3), 0.42, -0.2); mx.add(T["approach"], s_jet(la, 5), 0.42, 0.2)
    for tt, pan in ((0.0, 0.4), (0.6, -0.4)):
        tr = when("release", lambda m, tt=tt: m["t"] >= tt)
        if tr:
            mx.add(tr, gp.s_thud(0.6), 0.9, pan); mx.add(tr + 0.02, gp.s_ping(260, 0.35), 0.3, pan)
    mx.add(T["fall"], gp.s_whoosh(L["fall"], 300, 2200, 0.8) * 0.9, 0.6); mx.add(T["fall"], gp.s_wind(L["fall"]) * 0.35, 1.0, 0.0)
    for shot, sc_, g in (("impact82", 1.0, 0.85), ("impact83", 1.32, 1.0)):
        th = when(shot, lambda m: m["td"] >= 0)
        if th:
            mx.add(th, s_blast(sc_), g, 0.0); mx.add(th + 0.25, gp.s_debris(3.5, 80, 2.2), 0.55 * g, 0.2); mx.add(th + 0.1, gp.s_ring(3.0), 0.5 * g)
    tb = T["radius"]; mx.add(tb, s_blast(1.0), 0.55, -0.6); mx.add(tb + 0.02, s_blast(1.32), 0.65, 0.6); mx.add(tb + 0.3, gp.s_debris(3.0, 60, 1.8), 0.35, 0.0)
    ta = T["after"]; mx.add(ta, gp.s_wind(L["after"]) * 0.14, 1.0, -0.1); mx.add(ta + 0.2, gp.s_debris(L["after"] - 0.5, 14, 0.7), 0.18, 0.2)
    x = np.tanh(mx.b[: int(total * SR)] * 1.1)
    fo = int(0.6 * SR); x[-fo:] *= np.linspace(1, 0, fo)[:, None]
    x = x / (np.abs(x).max() + 1e-9) * 0.89
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype("<i2").tobytes())

FADES = {"card": (8, 6), "approach": (6, 0), "release": (0, 4), "fall": (4, 0), "impact82": (0, 4), "impact83": (4, 5), "radius": (5, 5), "after": (5, 14)}

def _load(root, shot):
    d = os.path.join(root, shot); files = sorted(f for f in os.listdir(d) if f.startswith("f") and f.endswith(".png"))
    meta = json.load(open(os.path.join(d, "meta.json"))) if shot != "card" else {}
    return d, files, ({str(k): meta[str(int(f[1:5]))] for k, f in enumerate(files)} if shot != "card" else {})

def main():
    root = sys.argv[1]; out = sys.argv[2]; draft = "--draft" in sys.argv
    info = json.load(open(os.path.join(root, "timeline.json")))
    stage = os.path.join(root, "_master"); os.makedirs(stage, exist_ok=True)
    for f in os.listdir(stage):
        os.remove(os.path.join(stage, f))
    starts = {}; metas = {}; g = 0
    for shot in ORDER:
        starts[shot] = g; fi, fo = FADES[shot]
        if shot == "radius":
            d1, f1, m1 = _load(root, "radius82"); d2, f2, m2 = _load(root, "radius83"); n = min(len(f1), len(f2)); metas[shot] = {str(k): m1[str(k)] for k in range(n)}
        else:
            d1, f1, m1 = _load(root, shot); n = len(f1); metas[shot] = m1
        for k in range(n):
            if shot == "card":
                frame = card_frame(Image.open(os.path.join(d1, f1[k])), k, n).convert("RGBA")
            elif shot == "radius":
                frame = compare_frame(Image.open(os.path.join(d1, f1[k])), Image.open(os.path.join(d2, f2[k])), k, n, m1[str(k)], m2[str(k)], info)
            else:
                frame = Image.open(os.path.join(d1, f1[k])).convert("RGB").resize((W, H), Image.LANCZOS).convert("RGBA")
                shadowed(frame, overlay_for(shot, k, n, m1[str(k)], info))
            fade = min(1.0, (k + 1) / fi if fi else 1.0, (n - k) / fo if fo else 1.0)
            if fade < 1.0:
                frame = Image.blend(Image.new("RGBA", frame.size, (0, 0, 0, 255)), frame, fade)
            frame.convert("RGB").save(os.path.join(stage, "m%05d.png" % g), compress_level=1); g += 1
        print("staged", shot, n); sys.stdout.flush()
    total = g / FPS
    wav = os.path.join(root, "mix.wav"); build_audio(wav, starts, metas, total)
    vf = "unsharp=5:5:0.55:5:5:0.0,vignette=PI/7,noise=alls=4:allf=t+u,format=yuv420p"
    cmd = ["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", os.path.join(stage, "m%05d.png"), "-i", wav,
           "-vf", vf, "-c:v", "libx264", "-preset", "medium" if draft else "slow", "-crf", "21" if draft else "18",
           "-maxrate", "14M", "-bufsize", "28M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest", out]
    subprocess.check_call(cmd)
    print("wrote", out, "%.2fs" % total, starts)

if __name__ == "__main__":
    main()
