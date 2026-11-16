"""Finishing for the RPG-7 segment: upscale to 1080p, title card, HUD overlays, synthesized sound, encode.

  python3 rpost.py <frames_root> <out.mp4> [--draft]

Reuses the typography, overlay helpers and sound synths of the M67 segment (../grenade-explosion/post.py).
"""
import os, sys, json, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion"))
import post as gp
from post import W, H, FPS, SR, AMBER, RED, INK, DIM, PANEL, F_TITLE, F_SEMI, F_MED, ease, text, shadowed, lower, callout

ORDER = ["card", "fire", "follow", "impact", "behind", "after"]
FIRE_LEAD = 30
SPECS = [("TYPE", "Reloadable shoulder launcher"), ("LAUNCHER", "40 mm tube  ·  950 mm  ·  6.3 kg"), ("ROCKET", "PG-7V HEAT  ·  85 mm warhead"),
         ("VELOCITY", "115 m/s  ·  up to ~300 m/s"), ("EFFECTIVE RANGE", "330 m"), ("PENETRATION", "260 mm steel armour"), ("IN SERVICE", "1961 – present")]

def tag(d, a=1.0):
    text(d, (64, 54), "EXPLOSION COMPARISON", F_SEMI(30), INK, a, tracking=4)
    d.rectangle([64, 96, 64 + 54, 100], fill=(*AMBER, int(255 * a)))
    text(d, (130, 84), "02  ·  RPG-7  ·  PG-7V HEAT ROCKET", F_MED(26), DIM, a, tracking=2)

def card_frame(img, i, n):
    base = Image.new("RGBA", (W, H), (*PANEL, 255))
    base.paste(img.convert("RGB").resize((W // 2, H), Image.LANCZOS), (0, 0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    grad = Image.linear_gradient("L").rotate(90, expand=True).resize((90, H))
    seam = Image.new("RGBA", (90, H), (*PANEL, 255)); seam.putalpha(grad.point(lambda v: 255 - v))
    base.alpha_composite(seam.transpose(Image.FLIP_LEFT_RIGHT), (W // 2 - 90, 0))
    t = i / FPS; x0 = W // 2 + 96
    text(d, (x0, 150), "EXPLOSION COMPARISON  ·  02", F_SEMI(30), DIM, ease((t - 0.10) / 0.5), tracking=5)
    a = ease((t - 0.20) / 0.5); text(d, (x0 + int((1 - a) * 40), 196), "RPG-7", F_TITLE(210), INK, a)
    a = ease((t - 0.35) / 0.5); text(d, (x0 + int((1 - a) * 40), 446), "ANTI-TANK ROCKET LAUNCHER", F_TITLE(54), AMBER, a, tracking=2)
    a = ease((t - 0.45) / 0.5); d.rectangle([x0, 528, x0 + int(700 * a), 531], fill=(*AMBER, int(255 * a)))
    y = 562
    for k, (lab, val) in enumerate(SPECS):
        a = ease((t - 0.65 - 0.12 * k) / 0.45); dx = int((1 - a) * 28); hot = lab == "PENETRATION"
        text(d, (x0 + dx, y), lab, F_SEMI(31), RED if hot else DIM, a, tracking=3)
        text(d, (x0 + 300 + dx, y - 4), val, F_SEMI(40) if hot else F_MED(38), INK, a)
        y += 60
    text(d, (x0, 1000), "Fired here at a one-brick-thick (215 mm) wall from 30 m.", F_MED(28), DIM, ease((t - 1.9) / 0.6))
    base.alpha_composite(ov)
    return base.convert("RGB")

def readout(d, label, value, a=1.0, color=INK):
    text(d, (W - 64, H - 150), label, F_SEMI(30), DIM, a, anchor="ra", tracking=5)
    text(d, (W - 64, H - 120), value, F_TITLE(74), color, a, anchor="ra")

def ruler(d, p0, p1, big, small, a):
    """Ground distance ruler from the wall to the farthest brick; if that brick is outside the
    frame the line is cut at the frame edge and ends in an arrow instead of a tick."""
    x0, y0 = p0[0] * W, p0[1] * H; x1, y1 = p1[0] * W, p1[1] * H
    s = 1.0
    for lo, hi, v0, v1 in ((90, W - 90, x0, x1), (150, H - 210, y0, y1)):
        if v1 > hi and v1 != v0: s = min(s, (hi - v0) / (v1 - v0))
        if v1 < lo and v1 != v0: s = min(s, (lo - v0) / (v1 - v0))
    s = max(0.0, s) * ease(a)
    cut = s < 0.999 and a >= 1.0
    ex, ey = x0 + (x1 - x0) * s, y0 + (y1 - y0) * s
    L = math.hypot(ex - x0, ey - y0)
    if L < 4: return
    ux, uy = (ex - x0) / L, (ey - y0) / L; nx, ny = -uy, ux
    col = AMBER + (int(235 * a),); sh = (0, 0, 0, int(150 * a))
    for off, c in ((2, sh), (0, col)):
        k = 0.0
        while k < L:                                   # dashed line
            e = min(L, k + 16)
            d.line([(x0 + ux * k, y0 + uy * k + off), (x0 + ux * e, y0 + uy * e + off)], fill=c, width=3)
            k += 26
        d.line([(x0 - nx * 12, y0 - ny * 12 + off), (x0 + nx * 12, y0 + ny * 12 + off)], fill=c, width=3)
        if cut or a < 1.0:
            d.polygon([(ex + ux * 16, ey + uy * 16 + off), (ex - ux * 6 + nx * 10, ey - uy * 6 + ny * 10 + off),
                       (ex - ux * 6 - nx * 10, ey - uy * 6 - ny * 10 + off)], fill=c)
        else:
            d.line([(ex - nx * 12, ey - ny * 12 + off), (ex + nx * 12, ey + ny * 12 + off)], fill=c, width=3)
    mx, my = x0 + (ex - x0) * 0.5, y0 + (ey - y0) * 0.5
    side = -1 if ny > 0 else 1                         # put the label above the line
    lx, ly = mx + nx * side * 34 - 60, my + ny * side * 34 - 62
    text(d, (lx, ly - 14), big, F_TITLE(64), AMBER, a)
    text(d, (lx + 2, ly + 62), small, F_SEMI(30), INK, a, tracking=3)

def overlay_for(shot, i, n, m, info):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    t = m["t"]; td = m["td"]
    tag(d, ease(i / 8.0) if shot == "fire" else 1.0)
    if shot == "fire":
        lower(d, "THE SHOT", "Launch charge kicks the rocket out at 115 m/s  ·  backblast vents behind", ease((i - 6) / 10.0) * (1 - ease((i - (n - 8)) / 8.0)))
        if t < 0:
            readout(d, "RANGE TO TARGET", "30 m", ease((i - 4) / 8.0), AMBER)
        else:
            readout(d, "SLOW MOTION", "T + %03d ms" % round(t * 1000))
    elif shot == "follow":
        readout(d, "SPEED", "%d m/s" % round(m["v"]), 1.0, AMBER)
        x = W - 64; y = H - 150; frac = 1.0 - m["togo"] / info["DIST"]
        text(d, (x, y - 62), "%.1f m TO TARGET" % m["togo"], F_SEMI(30), INK, 1.0, anchor="ra", tracking=3)
        d.rectangle([x - 300, y - 20, x, y - 16], fill=(255, 255, 255, 70)); d.rectangle([x - 300, y - 20, x - 300 + int(300 * frac), y - 16], fill=(*AMBER, 255))
        a1 = ease((i - 4) / 8.0) * (1 - ease((t - info["T_IGN"] + 0.012) / 0.012)); a2 = ease((t - info["T_IGN"] - 0.004) / 0.012) * (1 - ease((i - (n - 8)) / 8.0))
        if a1 > 0:
            lower(d, "IN FLIGHT", "Four fins spring open  ·  coasting on the launch charge", a1)
        if a2 > 0:
            lower(d, "MOTOR IGNITION", "Rocket motor lights about 10 m out and keeps accelerating", a2)
    elif shot == "impact":
        a = ease((i - 2) / 6.0)
        readout(d, "SLOW MOTION", "T + %03d ms" % max(0, round(td * 1000)), a)
        lower(d, "IMPACT", "Shaped-charge warhead detonates on contact", ease((i - 12) / 10.0) * (1 - ease((i - (n - 22)) / 10.0)))
    elif shot == "behind":
        readout(d, "SLOW MOTION", "T + %03d ms" % max(0, round(td * 1000)))
        lower(d, "THROUGH THE WALL", "Jet and blast burst out of the far side, bricks ahead of them", ease((i - 8) / 10.0) * (1 - ease((i - (n - 10)) / 8.0)))
    elif shot == "after":
        an = m["anchors"]
        a1 = ease((i - 8) / 8.0) * (1 - ease((i - 38) / 8.0)); a2 = ease((i - 60) / 8.0)
        if a1 > 0:
            callout(d, an["hole"][0] * W, an["hole"][1] * H, "BREACHED", "215 MM BRICK  ·  ONE ROCKET", RED, a1, dx=150, dy=-150)
        if a2 > 0:
            ruler(d, an["wall"], an["far"], "%d m" % round(info["reach"]), "DEBRIS THROWN  ·  FARTHEST BRICK", a2)
        lower(d, "WHAT IT CAN DO", "Built to pierce 260 mm of steel armour  ·  brick is no obstacle", ease((i - 44) / 12.0))
    return ov

# ------------------------------------------------------------------ sound
def s_rocket(dur, rise=0.15):
    n = int(dur * SR); t = np.arange(n) / SR
    x = gp.bp(gp.noise(n), 180, 2600) * 1.4 + gp.lp(gp.noise(n), 160, 2) * 3.0
    return x * np.minimum(1, t / rise) * (0.75 + 0.25 * np.sin(2 * np.pi * 31 * t))

def build_audio(path, starts, metas, info, total):
    mx = gp.Mix(total); T = {k: v / FPS for k, v in starts.items()}
    def when(shot, pred):
        m = metas[shot]
        for i in sorted(int(k) for k in m):
            if pred(m[str(i)]):
                return T[shot] + i / FPS
        return None
    amb0 = T["fire"]; mx.add(amb0, gp.s_wind(total - amb0) * 0.045 + gp.s_birds(total - amb0) * 0.045, 1.0, -0.1)
    mx.add(0.0, gp.s_drone(T["fire"] + 0.2), 0.5); mx.add(0.05, gp.s_thud(1.2), 0.5)
    for k in range(len(SPECS)):
        mx.add(0.65 + 0.12 * k, gp.s_tick(), 0.35, 0.3)
    mx.add(T["fire"] - 0.45, gp.s_whoosh(0.6, 200, 1500, 0.8), 0.35)
    # the shot: click, then the launch bang stretched for slow motion, hiss of the backblast
    tf = when("fire", lambda m: m["t"] >= 0)
    if tf:
        mx.add(tf - 0.55, gp.s_ping(2400, 0.2), 0.3, 0.1); mx.add(tf - 0.04, gp.s_tick(), 0.9)
        mx.add(tf, gp.s_boom(0.75, 1.8), 0.9, -0.1)
        mx.add(tf + 0.02, gp.s_whoosh(2.2, 300, 2400, 0.12), 0.8, -0.3); mx.add(tf + 0.3, gp.s_debris(2.0, 18, 1.5), 0.25, -0.4)
    # chase: air rush, then the motor
    nf = len(metas["follow"]) / FPS
    mx.add(T["follow"], gp.s_whoosh(nf, 250, 1100, 0.5) * 0.9, 0.55)
    ti = when("follow", lambda m: m["t"] >= info["T_IGN"])
    if ti:
        mx.add(ti, gp.s_thud(0.8), 0.7, 0.1); mx.add(ti, s_rocket(T["impact"] - ti + 0.25), 0.16, 0.1)
    # impact (slow motion) and the view from behind
    th = when("impact", lambda m: m["td"] >= 0)
    if th:
        mx.add(th, gp.s_boom(1.0, 2.2), 1.0); mx.add(th + 0.1, gp.s_debris(3.6, 55, 2.0), 0.6, 0.2); mx.add(th + 0.05, gp.s_ring(3.6), 1.0)
        mx.add(th + 0.02, gp.s_whoosh(1.2, 150, 1200, 0.2), 0.6, -0.4)
    tb = when("behind", lambda m: m["td"] >= 0)
    if tb:
        mx.add(tb, gp.s_boom(0.95, 2.0), 0.95, 0.1); mx.add(tb + 0.1, gp.s_debris(2.6, 70, 2.0), 0.7, -0.2)
        mx.add(tb + 0.3, gp.s_whoosh(1.4, 180, 900, 0.3), 0.45, 0.4)
    # aftermath: settling debris, UI blips
    mx.add(T["after"] + 0.1, gp.s_debris(2.0, 9, 1.0), 0.22, 0.2)
    for dt_ in (0.4, 2.55):
        mx.add(T["after"] + dt_, gp.s_ping(2000, 0.25), 0.22, 0.3)
    x = np.tanh(mx.b[: int(total * SR)] * 1.1)
    fo = int(0.6 * SR); x[-fo:] *= np.linspace(1, 0, fo)[:, None]
    x = x / (np.abs(x).max() + 1e-9) * 0.89
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype("<i2").tobytes())

def main():
    root = sys.argv[1]; out = sys.argv[2]; draft = "--draft" in sys.argv
    info = json.load(open(os.path.join(root, "timeline.json")))
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
            elif shot == "fire":
                fade = min(1.0, (k + 1) / 6.0)
            elif shot == "after":
                fade = min(1.0, (k + 1) / 5.0, (n - k) / 14.0)
            elif shot == "behind":
                fade = min(1.0, (n - k) / 4.0)
            if fade < 1.0:
                frame = Image.blend(Image.new("RGBA", frame.size, (0, 0, 0, 255)), frame, fade)
            frame.convert("RGB").save(os.path.join(stage, "m%05d.png" % g), compress_level=1); g += 1
        print("staged", shot, n); sys.stdout.flush()
    total = g / FPS
    wav = os.path.join(root, "mix.wav"); build_audio(wav, starts, metas, info, total)
    vf = "unsharp=5:5:0.55:5:5:0.0,vignette=PI/7,noise=alls=4:allf=t+u,format=yuv420p"
    cmd = ["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", os.path.join(stage, "m%05d.png"), "-i", wav,
           "-vf", vf, "-c:v", "libx264", "-preset", "medium" if draft else "slow", "-crf", "21" if draft else "18",
           "-maxrate", "14M", "-bufsize", "28M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest", out]
    subprocess.check_call(cmd)
    print("wrote", out, "%.2fs" % total, starts)

if __name__ == "__main__":
    main()
