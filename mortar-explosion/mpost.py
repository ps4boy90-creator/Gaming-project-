"""Finishing for the 120 mm mortar segment: upscale to 1080p, title card, HUD overlays, synthesized sound, encode.

  python3 mpost.py <frames_root> <out.mp4> [--draft]

Reuses the typography, overlay helpers and sound synths of the M67 segment (../grenade-explosion/post.py).
"""
import os, sys, json, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion"))
import post as gp
from post import W, H, FPS, SR, AMBER, RED, INK, DIM, PANEL, F_TITLE, F_SEMI, F_MED, ease, text, shadowed, lower, callout

ORDER = ["card", "load", "fire", "fall", "impact", "radius", "after"]
SPECS = [("TYPE", "Smooth-bore, muzzle-loaded mortar"), ("CANNON", "M298  ·  120 mm  ·  1.75 m  ·  50 kg"), ("IN ACTION", "145 kg with bipod and baseplate"),
         ("ROUND", "M934A1 HE  ·  14.2 kg  ·  Comp B"), ("RANGE", "200 – 7,200 m"), ("RATE OF FIRE", "16 rds/min  ·  4 sustained"), ("BURSTING RADIUS", "75 m")]

def tag(d, a=1.0):
    text(d, (64, 54), "EXPLOSION COMPARISON", F_SEMI(30), INK, a, tracking=4)
    d.rectangle([64, 96, 64 + 54, 100], fill=(*AMBER, int(255 * a)))
    text(d, (130, 84), "03  ·  M120  ·  120 MM MORTAR  ·  M934A1 HE", F_MED(26), DIM, a, tracking=2)

def card_frame(img, i, n):
    base = Image.new("RGBA", (W, H), (*PANEL, 255))
    base.paste(img.convert("RGB").resize((W // 2, H), Image.LANCZOS), (0, 0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    grad = Image.linear_gradient("L").rotate(90, expand=True).resize((90, H))
    seam = Image.new("RGBA", (90, H), (*PANEL, 255)); seam.putalpha(grad.point(lambda v: 255 - v))
    base.alpha_composite(seam.transpose(Image.FLIP_LEFT_RIGHT), (W // 2 - 90, 0))
    t = i / FPS; x0 = W // 2 + 96
    text(d, (x0, 150), "EXPLOSION COMPARISON  ·  03", F_SEMI(30), DIM, ease((t - 0.10) / 0.5), tracking=5)
    a = ease((t - 0.20) / 0.5); text(d, (x0 + int((1 - a) * 40), 196), "M120", F_TITLE(210), INK, a)
    a = ease((t - 0.35) / 0.5); text(d, (x0 + int((1 - a) * 40), 446), "120 MM MORTAR SYSTEM  ·  US ARMY", F_TITLE(54), AMBER, a, tracking=2)
    a = ease((t - 0.45) / 0.5); d.rectangle([x0, 528, x0 + int(820 * a), 531], fill=(*AMBER, int(255 * a)))
    y = 562
    for k, (lab, val) in enumerate(SPECS):
        a = ease((t - 0.65 - 0.12 * k) / 0.45); dx = int((1 - a) * 28); hot = lab == "BURSTING RADIUS"
        text(d, (x0 + dx, y), lab, F_SEMI(31), RED if hot else DIM, a, tracking=3)
        text(d, (x0 + 300 + dx, y - 4), val, F_SEMI(40) if hot else F_MED(38), INK, a)
        y += 60
    text(d, (x0, 1000), "Fired here at a group of ruined buildings 2,000 m away.", F_MED(28), DIM, ease((t - 1.9) / 0.6))
    base.alpha_composite(ov)
    return base.convert("RGB")

def readout(d, label, value, a=1.0, color=INK, sub=None):
    text(d, (W - 64, H - 150), label, F_SEMI(30), DIM, a, anchor="ra", tracking=5)
    text(d, (W - 64, H - 120), value, F_TITLE(74), color, a, anchor="ra")
    if sub:
        text(d, (W - 64, H - 196), sub, F_SEMI(30), INK, a, anchor="ra", tracking=3)

def overlay_for(shot, i, n, m, info):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    t = m["t"]; td = m["td"]; an = m.get("anchors", {})
    tag(d, ease(i / 8.0) if shot == "load" else 1.0)
    if shot == "load":
        a1 = ease((i - 6) / 10.0) * (1 - ease((i - 52) / 8.0)); a2 = ease((i - 60) / 8.0)
        if a1 > 0:
            lower(d, "LOADING", "The assistant gunner lifts the 14 kg round to the muzzle, tail first", a1)
        if a2 > 0:
            lower(d, "“HANGING”", "Tail in the tube, both hands on the body  ·  waiting for the command to fire", a2)
        readout(d, "ELEVATION", "1100 mils", ease((i - 10) / 10.0), AMBER, "62° ABOVE THE HORIZON")
    elif shot == "fire":
        if t < 0:
            lower(d, "FIRE", "Released, the round slides down the tube onto the fixed firing pin", ease(i / 6.0))
            readout(d, "RANGE TO TARGET", "2,000 m", ease((i - 2) / 6.0), AMBER)
        else:
            lower(d, "THE SHOT", "The propelling charge throws the round up the 1.75 m tube", 1 - ease((i - (n - 8)) / 8.0))
            readout(d, "SLOW MOTION", "T + %03d ms" % round(t * 1000), 1.0, INK, "LEAVES AT ~%d m/s" % round(info["V0"]))
    elif shot == "fall":
        a = ease((i - 2) / 8.0)
        readout(d, "ALTITUDE", "%d m" % round(m.get("alt", 0)), a, AMBER, "%d m/s  ·  IMPACT IN %.1f s" % (round(m.get("v", 0)), max(-td, 0)))
        lower(d, "PLUNGING FIRE", "Up to %d m, then down at 62°  ·  about %d s in the air (drag-free estimate)" % (round(info["APEX"]), round(info["TOF"])),
              ease((i - 6) / 10.0) * (1 - ease((i - (n - 8)) / 8.0)))
    elif shot == "impact":
        readout(d, "SLOW MOTION", "T + %03d ms" % max(0, round(td * 1000)), ease((i - 2) / 6.0))
        lower(d, "DETONATION", "Fuze fires on contact  ·  the steel body bursts into fragments", ease((i - 14) / 10.0) * (1 - ease((i - (n - 14)) / 10.0)))
    elif shot == "radius":
        rf = m.get("r_front", 0.0); done = rf >= info["BURST_R"] - 0.01
        if not done:
            readout(d, "FRAGMENTS REACH", "%d m" % round(rf), 1.0, AMBER, "T + %03d ms" % max(0, round(td * 1000)))
        else:
            a = ease((td - 0.10) / 0.10)
            callout(d, an["edge"][0] * W, an["edge"][1] * H, "75 m", "BURSTING RADIUS  ·  FM 23-90", RED, a, dx=-560, dy=-190)
            a2 = ease((td - 0.50) / 0.15)
            if a2 > 0:
                callout(d, an["m67"][0] * W, an["m67"][1] * H, "15 m", "M67 HAND GRENADE, FOR SCALE", AMBER, a2, dx=-520, dy=110)
            readout(d, "DANGER AREA", "17,700 m²", a, INK, "ABOUT 2½ FOOTBALL PITCHES")
        lower(d, "THE REAL REACH", "The cloud is a few metres wide  ·  steel fragments carry the effect to 75 m", ease((td - 0.30) / 0.2))
    elif shot == "after":
        a1 = ease((i - 8) / 8.0) * (1 - ease((i - 40) / 8.0)); a2 = ease((i - 30) / 8.0) * (1 - ease((i - 62) / 8.0))
        if a1 > 0:
            callout(d, an["crater"][0] * W, an["crater"][1] * H, "IMPACT", "SHALLOW CRATER  ·  SOIL THROWN IN RAYS", RED, a1, dx=70, dy=130)
        if a2 > 0:
            callout(d, an["wall"][0] * W, an["wall"][1] * H, "2.7 m AWAY", "FREE-STANDING WALL KNOCKED DOWN", AMBER, a2, dx=-560, dy=-170)
        lower(d, "WHAT IT CAN DO", "One 120 mm HE round  ·  fragments dangerous out to 75 m", ease((i - 46) / 12.0))
    return ov

# ------------------------------------------------------------------ sound
def s_whistle(dur):
    """Incoming round: a falling whine that gets louder."""
    n = int(dur * SR); t = np.arange(n) / SR; u = t / dur
    f = 1500 - 850 * u ** 1.5; ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * 0.5 + np.sin(ph * 1.5 + 0.3) * 0.18 + gp.bp(gp.noise(n), 500, 3500) * 0.6
    return x * (0.08 + 0.92 * u ** 2.2)

def build_audio(path, starts, metas, total):
    mx = gp.Mix(total); T = {k: v / FPS for k, v in starts.items()}
    def when(shot, pred):
        m = metas[shot]
        for i in sorted(int(k) for k in m):
            if pred(m[str(i)]):
                return T[shot] + i / FPS
        return None
    amb0 = T["load"]; mx.add(amb0, gp.s_wind(total - amb0) * 0.045 + gp.s_birds(total - amb0) * 0.045, 1.0, -0.1)
    mx.add(0.0, gp.s_drone(T["load"] + 0.2), 0.5); mx.add(0.05, gp.s_thud(1.2), 0.5)
    for k in range(len(SPECS)):
        mx.add(0.65 + 0.12 * k, gp.s_tick(), 0.35, 0.3)
    mx.add(T["load"] - 0.45, gp.s_whoosh(0.6, 200, 1500, 0.8), 0.35)
    # loading: the tail touches the muzzle, the round settles into the tube
    tm = when("load", lambda m: m["t"] >= -3.3)
    if tm:
        mx.add(tm, gp.s_tick(), 0.5, 0.1); mx.add(tm + 0.85, gp.s_thud(0.35), 0.35, 0.1); mx.add(tm + 1.0, gp.s_ping(1500, 0.3), 0.18, 0.2)
    # release -> slide -> shot (the bang is stretched because the picture is in slow motion)
    tr = when("fire", lambda m: m["t"] >= metas["fire"]["0"]["t"] + 0.2)
    tf = when("fire", lambda m: m["t"] >= 0)
    if tf:
        mx.add(tf - 0.55, gp.s_whoosh(0.5, 900, 300, 0.6), 0.30, 0.0); mx.add(tf - 0.03, gp.s_tick(), 0.9)
        mx.add(tf, gp.s_boom(1.0, 2.4), 1.0); mx.add(tf + 0.04, gp.s_ring(2.6), 0.5)
        mx.add(tf + 0.05, gp.s_whoosh(2.4, 400, 1800, 0.15), 0.5, 0.0); mx.add(tf + 0.4, gp.s_debris(1.6, 10, 1.2), 0.2, -0.2)
    # the fall: wind rush and the whistle, cut off by the burst
    nf = len(metas["fall"]) / FPS
    mx.add(T["fall"], gp.s_whoosh(nf, 300, 1400, 0.5) * 0.8, 0.5); mx.add(T["fall"], s_whistle(nf + 0.4), 0.42, 0.0)
    th = when("impact", lambda m: m["td"] >= 0)
    if th:
        mx.add(th, gp.s_boom(1.0, 3.0), 1.0); mx.add(th + 0.02, gp.s_boom(0.6, 1.2), 0.6, 0.2)
        mx.add(th + 0.15, gp.s_debris(4.2, 60, 2.2), 0.6, 0.2); mx.add(th + 0.05, gp.s_ring(4.0), 0.9)
        mx.add(th + 0.05, gp.s_whoosh(1.6, 150, 1000, 0.2), 0.55, -0.3)
    tb = T["radius"]
    mx.add(tb, gp.s_boom(0.9, 2.4), 0.8, 0.0); mx.add(tb + 0.1, gp.s_whoosh(1.2, 600, 2600, 0.25), 0.4, 0.0); mx.add(tb + 0.3, gp.s_debris(2.6, 40, 1.6), 0.3, 0.0)
    for dt_ in (1.25, 1.9):
        mx.add(tb + dt_, gp.s_ping(2000, 0.25), 0.22, 0.3)
    mx.add(T["after"] + 0.1, gp.s_debris(2.0, 8, 1.0), 0.2, 0.2)
    for dt_ in (0.4, 1.3, 2.0):
        mx.add(T["after"] + dt_, gp.s_ping(2000, 0.25), 0.2, 0.3)
    x = np.tanh(mx.b[: int(total * SR)] * 1.1)
    fo = int(0.6 * SR); x[-fo:] *= np.linspace(1, 0, fo)[:, None]
    x = x / (np.abs(x).max() + 1e-9) * 0.89
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype("<i2").tobytes())

def main():
    root = sys.argv[1]; out = sys.argv[2]; draft = "--draft" in sys.argv
    info = {}
    for nm in ("timeline_pit.json", "timeline_target.json"):
        info.update(json.load(open(os.path.join(root, nm))))
    stage = os.path.join(root, "_master"); os.makedirs(stage, exist_ok=True)
    for f in os.listdir(stage):
        os.remove(os.path.join(stage, f))
    starts = {}; metas = {}; g = 0
    for shot in ORDER:
        d = os.path.join(root, shot)
        files = sorted(f for f in os.listdir(d) if f.startswith("f") and f.endswith(".png"))
        n = len(files); starts[shot] = g
        meta = json.load(open(os.path.join(d, "meta.json"))) if shot != "card" else {}
        metas[shot] = {str(k): meta[str(int(f[1:5]))] for k, f in enumerate(files)} if shot != "card" else {}
        for k, f in enumerate(files):
            img = Image.open(os.path.join(d, f))
            if shot == "card":
                frame = card_frame(img, k, n).convert("RGBA")
            else:
                frame = img.convert("RGB").resize((W, H), Image.LANCZOS).convert("RGBA")
                shadowed(frame, overlay_for(shot, k, n, metas[shot][str(k)], info))
            fade = 1.0
            if shot == "card":
                fade = min(1.0, (k + 1) / 8.0, (n - k) / 6.0)
            elif shot == "load":
                fade = min(1.0, (k + 1) / 6.0)
            elif shot == "fall":
                fade = min(1.0, (k + 1) / 5.0)
            elif shot == "fire":
                fade = min(1.0, (n - k) / 5.0)
            elif shot == "after":
                fade = min(1.0, (k + 1) / 5.0, (n - k) / 14.0)
            elif shot == "radius":
                fade = min(1.0, (n - k) / 4.0)
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
