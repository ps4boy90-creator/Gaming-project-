"""Finishing for the UH-60 Black Hawk / Mk 77 fire bomb segment: upscale to 1080p, title card, HUD overlays,
synthesized sound, encode.

  python3 npost.py <frames_root> <out.mp4> [--draft]

Reuses the typography, overlay helpers and sound synths of the M67 segment (../grenade-explosion/post.py).
"""
import os, sys, json, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion"))
import post as gp
from post import W, H, FPS, SR, AMBER, RED, INK, DIM, PANEL, F_TITLE, F_SEMI, F_MED, ease, text, shadowed, lower, callout

ORDER = ["card", "approach", "release", "fall", "impact", "radius", "after"]
SPECS = [("BOMB", "Mk 77 Mod 5  ·  236 kg filled"), ("SIZE", "2.06 m long  ·  0.47 m across  ·  no fins"), ("FILL", "284 litres of fuel gel"), ("FIRE", "800 – 1,200 °C"),
         ("HELICOPTER", "UH-60L Black Hawk  ·  16.4 m rotor"), ("IN SERVICE", "Dropped by F/A-18 and AV-8B jets"), ("FIRE FOOTPRINT", "about 65 × 23 m from a jet")]

def tag(d, a=1.0):
    text(d, (64, 54), "EXPLOSION COMPARISON", F_SEMI(30), INK, a, tracking=4)
    d.rectangle([64, 96, 64 + 54, 100], fill=(*AMBER, int(255 * a)))
    text(d, (130, 84), "06  ·  UH-60 BLACK HAWK  ·  MK 77 FIRE BOMB", F_MED(26), DIM, a, tracking=2)

def card_frame(img, i, n):
    base = Image.new("RGBA", (W, H), (*PANEL, 255))
    base.paste(img.convert("RGB").resize((W // 2, H), Image.LANCZOS), (0, 0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    grad = Image.linear_gradient("L").rotate(90, expand=True).resize((90, H))
    seam = Image.new("RGBA", (90, H), (*PANEL, 255)); seam.putalpha(grad.point(lambda v: 255 - v))
    base.alpha_composite(seam.transpose(Image.FLIP_LEFT_RIGHT), (W // 2 - 90, 0))
    t = i / FPS; x0 = W // 2 + 96
    text(d, (x0, 150), "EXPLOSION COMPARISON  ·  06", F_SEMI(30), DIM, ease((t - 0.10) / 0.5), tracking=5)
    a = ease((t - 0.20) / 0.5); text(d, (x0 + int((1 - a) * 40), 196), "MK 77", F_TITLE(210), INK, a)
    a = ease((t - 0.35) / 0.5); text(d, (x0 + int((1 - a) * 40), 446), "FIRE BOMB  ·  UH-60 BLACK HAWK", F_TITLE(54), AMBER, a, tracking=2)
    a = ease((t - 0.45) / 0.5); d.rectangle([x0, 528, x0 + int(820 * a), 531], fill=(*AMBER, int(255 * a)))
    y = 562
    for k, (lab, val) in enumerate(SPECS):
        a = ease((t - 0.65 - 0.12 * k) / 0.45); dx = int((1 - a) * 28); hot = lab == "FIRE FOOTPRINT"
        text(d, (x0 + dx, y), lab, F_SEMI(31), RED if hot else DIM, a, tracking=3)
        text(d, (x0 + 300 + dx, y - 4), val, F_SEMI(40) if hot else F_MED(38), INK, a)
        y += 60
    text(d, (x0, 1000), "A Black Hawk carrying it is hypothetical  ·  dropped here on a ruined town.", F_MED(28), DIM, ease((t - 1.9) / 0.6))
    base.alpha_composite(ov)
    return base.convert("RGB")

def readout(d, label, value, a=1.0, color=INK, sub=None):
    text(d, (W - 64, H - 150), label, F_SEMI(30), DIM, a, anchor="ra", tracking=5)
    text(d, (W - 64, H - 120), value, F_TITLE(74), color, a, anchor="ra")
    if sub:
        text(d, (W - 64, H - 196), sub, F_SEMI(30), INK, a, anchor="ra", tracking=3)

def dashed(d, pts, fill, width, on=3, off=2):
    for k in range(0, len(pts) - 1, on + off):
        seg = pts[k:k + on + 1]
        if len(seg) > 1:
            d.line(seg, fill=fill, width=width)

def overlay_for(shot, i, n, m, info):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    t = m["t"]; td = m["td"]; an = m.get("anchors", {})
    tag(d, ease(i / 8.0) if shot == "approach" else 1.0)
    io = ease((i - 5) / 9.0) * (1 - ease((i - (n - 7)) / 7.0))
    if shot == "approach":
        lower(d, "RUNNING IN", "UH-60L Black Hawk  ·  four Mk 77 fire bombs on its stub wings  ·  a hypothetical load", io)
        readout(d, "HEIGHT", "200 ft", ease((i - 10) / 10.0), AMBER, "SPEED  100 kt")
        a2 = ease((i - 40) / 8.0) * (1 - ease((i - (n - 8)) / 7.0))
        if a2 > 0:
            callout(d, an["store"][0] * W, an["store"][1] * H, "MK 77 MOD 5", "ALUMINIUM CANISTER  ·  284 L OF FUEL GEL", RED, a2, dx=-640, dy=190)
    elif shot == "release":
        if t < 0:
            lower(d, "OVER THE AIM POINT", "The rack on the right outboard pylon lets go", ease((i - 3) / 8.0))
        else:
            lower(d, "RELEASE", "No fins  ·  the canister starts to tumble as soon as it is free", 1 - ease((i - (n - 8)) / 8.0))
            readout(d, "SLOW MOTION", "T + %03d ms" % round(t * 1000), 1.0, INK, "FALLEN  %.1f m" % m.get("drop", 0))
    elif shot == "fall":
        a = ease((i - 2) / 8.0)
        readout(d, "HEIGHT", "%d m" % round(m.get("alt", 0)), a, AMBER, "%d m/s  ·  IMPACT IN %.1f s" % (round(m.get("v", 0)), max(-td, 0)))
        lower(d, "TUMBLING DOWN", "Thrown %d m forward from 200 ft  ·  arriving at about %d m/s and %d°" % (round(info["FWD"]), round(info["V_HIT"]), round(info["FALL_DEG"])),
              ease((i - 6) / 10.0) * (1 - ease((i - (n - 8)) / 8.0)))
    elif shot == "impact":
        readout(d, "TIME", "T + %.1f s" % max(td, 0.0), ease((i - 2) / 6.0), INK, "HALF SPEED" if m.get("sim", 0) <= 70 else "REAL TIME")
        a1 = ease((i - 14) / 10.0) * (1 - ease((i - 70) / 10.0)); a2 = ease((i - 84) / 10.0) * (1 - ease((i - (n - 12)) / 10.0))
        if a1 > 0:
            lower(d, "IGNITION", "The canister bursts  ·  its igniters light the fuel as it is thrown down the street", a1)
        if a2 > 0:
            lower(d, "THE FIRE", "800 – 1,200 °C  ·  the gel sticks to ground and walls and goes on burning", a2)
    elif shot == "radius":
        ps = [(x * W, y * H) for x, y in m.get("path_sim", [])]; pp = [(x * W, y * H) for x, y in m.get("path_pub", [])]
        a1 = ease((td - 0.9) / 0.4); a2 = ease((td - 2.2) / 0.4)
        if a1 > 0 and len(ps) > 2:
            d.line([(x, y + 2) for x, y in ps], fill=(0, 0, 0, int(120 * a1)), width=8); d.line(ps, fill=(*RED, int(235 * a1)), width=6)
            callout(d, an["sim"][0] * W, an["sim"][1] * H, "%d × %d m" % (info["SMEAR_L"], info["SMEAR_W"]), "THIS DROP  ·  HELD IN BY THE STREET", RED, a1, dx=150, dy=-230)
        if a2 > 0 and len(pp) > 2:
            dashed(d, pp, (*INK, int(225 * a2)), 4)
            callout(d, an["pub"][0] * W, an["pub"][1] * H, "%d × %d m" % (info["FOOT_L"], info["FOOT_W"]), "PUBLISHED FOOTPRINT, DROPPED FROM A JET", INK, a2, dx=-700, dy=150)
        readout(d, "TIME", "T + %.1f s" % max(td, 0.0), 1.0, AMBER, "REAL TIME")
        lower(d, "THE BURNING AREA", "A slow helicopter throws the fuel a shorter way than a jet does", ease((td - 0.6) / 0.4))
    elif shot == "after":
        a1 = ease((i - 8) / 8.0) * (1 - ease((i - 46) / 8.0))
        if a1 > 0:
            callout(d, an["street"][0] * W, an["street"][1] * H, "BURNT OUT", "FUEL GEL STILL BURNING ON THE GROUND", RED, a1, dx=-640, dy=-260)
        lower(d, "WHAT IT DOES", "One 236 kg fire bomb  ·  a street 34 m long alight, burning on for minutes", ease((i - 46) / 12.0))
    return ov

# ------------------------------------------------------------------ sound
def s_rotor(dur):
    """Four-bladed main rotor: blade-passing thump at 17 Hz over turbine whine."""
    n = int(dur * SR); t = np.arange(n) / SR; bp_ = 17.2
    thump = np.maximum(0, np.sin(2 * np.pi * bp_ * t)) ** 6
    x = gp.lp(gp.noise(n), 260, 2) * (0.25 + 1.6 * thump) + 0.25 * np.sin(2 * np.pi * 2 * bp_ * t) * thump + gp.bp(gp.noise(n), 2500, 5200) * 0.10
    return x

def s_fire(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    x = gp.lp(gp.noise(n), 420, 2) * 1.3 + gp.bp(gp.noise(n), 600, 2600) * 0.35
    return x * (0.75 + 0.25 * np.sin(2 * np.pi * 0.9 * t + 1.0) * np.sin(2 * np.pi * 2.3 * t))

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
    mx.add(T["approach"], s_rotor(L["approach"] + L["release"]) * 0.9, 0.6, 0.0); mx.add(T["approach"], gp.s_wind(L["approach"] + L["release"]) * 0.10, 1.0, 0.1)
    tr = when("release", lambda m: m["t"] >= 0)
    if tr:
        mx.add(tr, gp.s_thud(0.5), 0.8, 0.2); mx.add(tr + 0.02, gp.s_ping(300, 0.4), 0.3, 0.2)
    mx.add(T["fall"], gp.s_whoosh(L["fall"], 200, 1500, 0.7) * 0.9, 0.6); mx.add(T["fall"], gp.s_wind(L["fall"]) * 0.30, 1.0, 0.0); mx.add(T["fall"], s_rotor(L["fall"]) * 0.25, 0.4, -0.3)
    th = when("impact", lambda m: m["td"] >= 0)
    if th:
        e = T["after"] - th
        mx.add(th, gp.s_boom(0.8, 2.6), 0.8); mx.add(th + 0.05, gp.s_whoosh(3.0, 100, 900, 0.25), 0.9, 0.0); mx.add(th + 0.15, s_fire(e) * np.minimum(1.0, np.arange(int(e * SR)) / (0.8 * SR)), 0.8, 0.0)
        mx.add(th + 0.3, gp.s_debris(e - 0.4, 30, 0.8), 0.25, 0.1)
    ta = T["after"]; mx.add(ta, s_fire(L["after"]) * 0.45, 0.6, 0.1); mx.add(ta, gp.s_wind(L["after"]) * 0.10, 1.0, -0.1); mx.add(ta + 0.1, gp.s_debris(L["after"] - 0.3, 26, 0.6), 0.25, 0.1)
    x = np.tanh(mx.b[: int(total * SR)] * 1.1)
    fo = int(0.6 * SR); x[-fo:] *= np.linspace(1, 0, fo)[:, None]
    x = x / (np.abs(x).max() + 1e-9) * 0.89
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype("<i2").tobytes())

FADES = {"card": (8, 6), "approach": (6, 0), "release": (0, 4), "fall": (4, 0), "impact": (0, 5), "radius": (5, 5), "after": (5, 14)}

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
        fi, fo = FADES[shot]
        for k, f in enumerate(files):
            img = Image.open(os.path.join(d, f))
            if shot == "card":
                frame = card_frame(img, k, n).convert("RGBA")
            else:
                frame = img.convert("RGB").resize((W, H), Image.LANCZOS).convert("RGBA")
                shadowed(frame, overlay_for(shot, k, n, metas[shot][str(k)], info))
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
