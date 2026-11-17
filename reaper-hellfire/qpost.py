"""Finishing for the MQ-9 Reaper / Hellfire segment: upscale to 1080p, title card, HUD overlays, the sensor-ball
picture, synthesized sound, encode.

  python3 qpost.py <frames_root> <out.mp4> [--draft]

Reuses the typography, overlay helpers and sound synths of the M67 segment (../grenade-explosion/post.py).
"""
import os, sys, json, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion"))
import post as gp
from post import W, H, FPS, SR, AMBER, RED, INK, DIM, PANEL, F_TITLE, F_SEMI, F_MED, ease, text, shadowed, lower, callout

ORDER = ["card", "cruise", "launch", "target", "fly", "impact", "radius", "after"]
SPECS = [("AIRCRAFT", "MQ-9A Reaper  ·  flown by remote crew"), ("WINGSPAN", "20.1 m  ·  11 m long"), ("ENGINE", "900 shp turboprop, pusher propeller"),
         ("MISSILE", "AGM-114R Hellfire II  ·  49 kg"), ("GUIDANCE", "Homes on a laser spot"), ("SPEED", "Mach 1.3  ·  reach about 8 km"), ("KILL RADIUS", "15 m  ·  wounding to 20 m")]
GREEN = (120, 255, 150)

def tag(d, a=1.0):
    text(d, (64, 54), "EXPLOSION COMPARISON", F_SEMI(30), INK, a, tracking=4)
    d.rectangle([64, 96, 64 + 54, 100], fill=(*AMBER, int(255 * a)))
    text(d, (130, 84), "05  ·  MQ-9 REAPER  ·  AGM-114 HELLFIRE", F_MED(26), DIM, a, tracking=2)

def card_frame(img, i, n):
    base = Image.new("RGBA", (W, H), (*PANEL, 255))
    base.paste(img.convert("RGB").resize((W // 2, H), Image.LANCZOS), (0, 0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    grad = Image.linear_gradient("L").rotate(90, expand=True).resize((90, H))
    seam = Image.new("RGBA", (90, H), (*PANEL, 255)); seam.putalpha(grad.point(lambda v: 255 - v))
    base.alpha_composite(seam.transpose(Image.FLIP_LEFT_RIGHT), (W // 2 - 90, 0))
    t = i / FPS; x0 = W // 2 + 96
    text(d, (x0, 150), "EXPLOSION COMPARISON  ·  05", F_SEMI(30), DIM, ease((t - 0.10) / 0.5), tracking=5)
    a = ease((t - 0.20) / 0.5); text(d, (x0 + int((1 - a) * 40), 196), "MQ-9", F_TITLE(210), INK, a)
    a = ease((t - 0.35) / 0.5); text(d, (x0 + int((1 - a) * 40), 446), "REAPER  ·  AGM-114 HELLFIRE MISSILE", F_TITLE(54), AMBER, a, tracking=2)
    a = ease((t - 0.45) / 0.5); d.rectangle([x0, 528, x0 + int(820 * a), 531], fill=(*AMBER, int(255 * a)))
    y = 562
    for k, (lab, val) in enumerate(SPECS):
        a = ease((t - 0.65 - 0.12 * k) / 0.45); dx = int((1 - a) * 28); hot = lab == "KILL RADIUS"
        text(d, (x0 + dx, y), lab, F_SEMI(31), RED if hot else DIM, a, tracking=3)
        text(d, (x0 + 300 + dx, y - 4), val, F_SEMI(40) if hot else F_MED(38), INK, a)
        y += 60
    text(d, (x0, 1000), "Fired here from 20,000 ft at an armed pickup 7.6 km away.", F_MED(28), DIM, ease((t - 1.9) / 0.6))
    base.alpha_composite(ov)
    return base.convert("RGB")

def readout(d, label, value, a=1.0, color=INK, sub=None):
    text(d, (W - 64, H - 150), label, F_SEMI(30), DIM, a, anchor="ra", tracking=5)
    text(d, (W - 64, H - 120), value, F_TITLE(74), color, a, anchor="ra")
    if sub:
        text(d, (W - 64, H - 196), sub, F_SEMI(30), INK, a, anchor="ra", tracking=3)

# ------------------------------------------------------------------ the sensor picture
_rng = np.random.default_rng(3)
def sensor_look(img, i):
    """Turn the rendered view into a monochrome infra-red style picture (white-hot), a little soft and noisy."""
    a = np.asarray(img.convert("RGB").resize((W, H), Image.LANCZOS), np.float32) / 255.0
    lum = a[..., 0] * 0.45 + a[..., 1] * 0.45 + a[..., 2] * 0.10
    g = np.clip(0.46 + (lum - np.median(lum)) * 1.9, 0.03, 0.97)          # the sand sits mid-grey; the vehicle goes white, its shadow black
    g += _rng.normal(0, 0.022, g.shape).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W]; r2 = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
    g *= 1.0 - 0.28 * np.clip(r2 - 0.25, 0, 1.5)
    g *= 1.0 - 0.035 * ((yy + i) % 3 == 0)
    out = np.clip(np.stack([g * 0.97, g * 1.0, g * 0.98], -1), 0, 1)
    return Image.fromarray((out * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.1))

def sensor_overlay(d, i, m, info):
    cx, cy = W // 2, H // 2; g = (*GREEN, 235); k = (0, 0, 0, 150)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):                       # open cross-hair
        for col, w, o in ((k, 6, 0), (g, 3, 0)):
            d.line([cx + dx * 34, cy + dy * 34, cx + dx * 150, cy + dy * 150], fill=col, width=w)
    d.rectangle([cx - 3, cy - 3, cx + 3, cy + 3], fill=g)
    for sx in (-1, 1):
        for sy in (-1, 1):                                                  # track gate
            x, y = cx + sx * 250, cy + sy * 160
            d.line([x, y, x - sx * 46, y], fill=g, width=3); d.line([x, y, x, y - sy * 46], fill=g, width=3)
    f = F_SEMI(30)
    text(d, (64, 150), "IR  ·  WHITE HOT", f, GREEN, 0.95, tracking=3)
    text(d, (64, 190), "TRACK  ·  VEHICLE", f, GREEN, 0.95, tracking=3)
    if (i // 6) % 2 == 0:
        text(d, (64, 230), "LASER  ·  DESIGNATING", f, (255, 120, 90), 0.95, tracking=3)
    text(d, (W - 64, 150), "SLANT RANGE  %.1f km" % (m.get("slant", 0) / 1000.0), f, GREEN, 0.95, anchor="ra", tracking=3)
    text(d, (W - 64, 190), "ALTITUDE  20,000 ft", f, GREEN, 0.95, anchor="ra", tracking=3)
    text(d, (W - 64, 230), "TARGET  %d km/h" % round(abs(m.get("speed", 0)) * 3.6), f, GREEN, 0.95, anchor="ra", tracking=3)

def overlay_for(shot, i, n, m, info):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    t = m["t"]; td = m["td"]; an = m.get("anchors", {})
    tag(d, ease(i / 8.0) if shot == "cruise" else 1.0)
    io = ease((i - 5) / 9.0) * (1 - ease((i - (n - 7)) / 7.0))
    if shot == "cruise":
        lower(d, "ON STATION", "MQ-9A Reaper  ·  two Hellfire missiles under each wing, a 500 lb laser-guided bomb inboard", io)
        readout(d, "ALTITUDE", "20,000 ft", ease((i - 10) / 10.0), AMBER, "CRUISE  %d kt" % round(info["U"] / 0.5144))
        a1 = ease((i - 16) / 8.0) * (1 - ease((i - 44) / 7.0)); a2 = ease((i - 54) / 8.0) * (1 - ease((i - (n - 8)) / 7.0))
        if a1 > 0:
            callout(d, an["turret"][0] * W, an["turret"][1] * H, "SENSOR BALL", "CAMERAS AND THE LASER DESIGNATOR", AMBER, a1, dx=-520, dy=150)
        if a2 > 0:
            callout(d, an["missile"][0] * W, an["missile"][1] * H, "AGM-114 HELLFIRE", "1.63 m  ·  49 kg  ·  9 kg WARHEAD", RED, a2, dx=-640, dy=170)
    elif shot == "launch":
        if t < 0:
            lower(d, "CLEARED TO FIRE", "The sensor operator holds the laser on the pickup  ·  the pilot releases the missile", ease((i - 3) / 8.0))
            readout(d, "SLANT RANGE", "%.1f km" % (info["SLANT"] / 1000.0), ease((i - 3) / 8.0), AMBER, "TARGET  ARMED PICKUP")
        else:
            lower(d, "MISSILE AWAY", "The motor burns for about three seconds and drives the missile to Mach 1.3", 1 - ease((i - (n - 8)) / 8.0))
            readout(d, "SLOW MOTION", "T + %03d ms" % round(t * 1000), 1.0, INK, "%d m/s" % round(m.get("v", 0)))
    elif shot == "target":
        sensor_overlay(d, i, m, info)
        lower(d, "THE SENSOR OPERATOR'S VIEW", "The laser stays on the pickup  ·  the missile steers for the reflected spot", io)
        readout(d, "TIME TO IMPACT", "%.1f s" % max(m.get("tti", 0), 0), 1.0, AMBER, "MISSILE IN FLIGHT")
    elif shot == "fly":
        a = ease((i - 2) / 8.0)
        readout(d, "ALTITUDE", "%d m" % round(m.get("alt", 0)), a, AMBER, "%d m/s  ·  IMPACT IN %.1f s" % (round(m.get("v", 0)), max(-td, 0)))
        lower(d, "%d SECONDS AFTER LAUNCH" % round(info["T_HIT"] - 3), "%.1f km from the rail  ·  motor long burnt out  ·  arriving at about %d°"
              % (info["SLANT"] / 1000.0, round(info["DIVE_DEG"])), ease((i - 6) / 10.0) * (1 - ease((i - (n - 8)) / 8.0)))
    elif shot == "impact":
        readout(d, "SLOW MOTION", "T + %03d ms" % max(0, round(td * 1000)), ease((i - 2) / 6.0))
        lower(d, "DETONATION", "9 kg multi-purpose warhead  ·  the fuel and the ammunition go up with it", ease((i - 14) / 10.0) * (1 - ease((i - (n - 14)) / 10.0)))
    elif shot == "radius":
        rf = m.get("r_front", 0.0); done = rf >= info["WOUND_R"] - 0.01
        for nm, colr, wd in (("wound", AMBER, 5), ("kill", RED, 6)):
            pts = [(x * W, y * H) for x, y in m.get("circle_" + nm, [])]
            if len(pts) > 2:
                if nm == "kill" and done:
                    d.polygon(pts, fill=(*RED, 26))
                d.line([(x, y + 2) for x, y in pts], fill=(0, 0, 0, 120), width=wd + 2); d.line(pts, fill=(*colr, 235), width=wd)
        if not done:
            readout(d, "FRAGMENTS REACH", "%d m" % round(rf), 1.0, AMBER, "T + %03d ms" % max(0, round(td * 1000)))
        else:
            a = ease((td - 0.08) / 0.10)
            callout(d, an["kill"][0] * W, an["kill"][1] * H, "15 m", "KILL RADIUS", RED, a, dx=260, dy=150)
            a2 = ease((td - 0.30) / 0.12)
            if a2 > 0:
                callout(d, an["wound"][0] * W, an["wound"][1] * H, "20 m", "WOUNDING RADIUS", AMBER, a2, dx=-330, dy=-210)
        lower(d, "THE REAL REACH", "Published kill and wounding radii of a Hellfire warhead  ·  sources in the README", ease((td - 0.30) / 0.2))
    elif shot == "after":
        a1 = ease((i - 8) / 8.0) * (1 - ease((i - 44) / 8.0)); a2 = ease((i - 32) / 8.0) * (1 - ease((i - 64) / 8.0))
        if a1 > 0:
            callout(d, an["wreck"][0] * W, an["wreck"][1] * H, "DIRECT HIT", "PUBLISHED ACCURACY: UNDER 1 m", RED, a1, dx=-640, dy=-190)
        if a2 > 0 and "door" in an:
            callout(d, an["door"][0] * W, an["door"][1] * H, "THROWN CLEAR", "DOORS, WHEELS, THE GUN", AMBER, a2, dx=110, dy=-150)
        lower(d, "WHAT IT CAN DO", "One 49 kg missile from 7.6 km away  ·  lethal to 15 m, wounding to 20 m", ease((i - 46) / 12.0))
    return ov

# ------------------------------------------------------------------ sound
def s_prop(dur):
    """Turboprop drone: low blade-passing hum with slow beating."""
    n = int(dur * SR); t = np.arange(n) / SR
    x = 0.5 * np.sin(2 * np.pi * 79.5 * t) + 0.3 * np.sin(2 * np.pi * 159 * t + 0.4) + 0.18 * np.sin(2 * np.pi * 238.5 * t) + 0.25 * np.sin(2 * np.pi * 53 * t)
    x *= 0.8 + 0.2 * np.sin(2 * np.pi * 0.7 * t)
    return x * 0.5 + gp.lp(gp.noise(n), 900, 2) * 0.5

def s_rocket(dur):
    n = int(dur * SR); t = np.arange(n) / SR; u = t / dur
    x = gp.bp(gp.noise(n), 180, 3200) * 1.0 + gp.lp(gp.noise(n), 160, 2) * 1.4
    return x * np.minimum(1.0, t / 0.02) * (1.0 - 0.75 * u) ** 1.5

def build_audio(path, starts, metas, total):
    mx = gp.Mix(total); T = {k: v / FPS for k, v in starts.items()}; L = {k: len(metas[k]) / FPS for k in metas}
    def when(shot, pred):
        m = metas[shot]
        for i in sorted(int(k) for k in m):
            if pred(m[str(i)]):
                return T[shot] + i / FPS
        return None
    mx.add(0.0, gp.s_drone(T["cruise"] + 0.2), 0.5); mx.add(0.05, gp.s_thud(1.2), 0.5)
    for k in range(len(SPECS)):
        mx.add(0.65 + 0.12 * k, gp.s_tick(), 0.35, 0.3)
    mx.add(T["cruise"] - 0.45, gp.s_whoosh(0.6, 200, 1500, 0.8), 0.35)
    mx.add(T["cruise"], s_prop(L["cruise"] + L["launch"]) * 0.9, 0.55, 0.0); mx.add(T["cruise"], gp.s_wind(L["cruise"] + L["launch"]) * 0.12, 1.0, 0.1)
    tf = when("launch", lambda m: m["t"] >= 0)
    if tf:
        mx.add(tf - 0.3, gp.s_tick(), 0.7, -0.2); mx.add(tf, gp.s_boom(0.5, 0.9), 0.55, 0.2); mx.add(tf, s_rocket(3.2), 0.9, 0.2); mx.add(tf + 0.05, gp.s_whoosh(2.4, 500, 2600, 0.2), 0.5, 0.3)
    ts = T["target"]; mx.add(ts, gp.s_wind(L["target"]) * 0.03, 1.0, 0.0); mx.add(ts, gp.lp(gp.noise(int(L["target"] * SR)), 2500, 2) * 0.05, 0.6, 0.0)
    for k in range(int(L["target"] / 0.5)):
        mx.add(ts + 0.25 + 0.5 * k, gp.s_ping(1250, 0.12), 0.22, 0.0)
    nf = L["fly"]; mx.add(T["fly"], gp.s_whoosh(nf, 300, 1800, 0.5) * 0.9, 0.6); mx.add(T["fly"], gp.s_wind(nf) * 0.35, 1.0, 0.0)
    th = when("impact", lambda m: m["td"] >= 0)
    if th:
        mx.add(th, gp.s_boom(1.0, 3.0), 1.0); mx.add(th + 0.02, gp.s_boom(0.7, 1.3), 0.7, 0.2)
        mx.add(th + 0.2, gp.s_debris(4.0, 70, 2.2), 0.7, 0.2); mx.add(th + 0.05, gp.s_ring(3.6), 0.8)
        mx.add(th + 0.5, gp.s_whoosh(2.8, 120, 700, 0.3), 0.6, 0.2)
    tb = T["radius"]
    mx.add(tb, gp.s_boom(0.9, 2.6), 0.85, 0.0); mx.add(tb + 0.1, gp.s_whoosh(1.2, 600, 2600, 0.25), 0.4, 0.0); mx.add(tb + 0.3, gp.s_debris(2.8, 40, 1.8), 0.35, 0.0)
    for dt_ in (1.6, 2.4):
        mx.add(tb + dt_, gp.s_ping(2000, 0.25), 0.22, 0.3)
    ta = T["after"]; mx.add(ta, gp.s_wind(L["after"]) * 0.10, 1.0, -0.1); mx.add(ta, gp.bp(gp.noise(int(L["after"] * SR)), 90, 900) * 0.10, 0.9, 0.1)
    mx.add(ta + 0.1, gp.s_debris(L["after"] - 0.3, 26, 0.6), 0.22, 0.1)
    for dt_ in (0.5, 1.6):
        mx.add(ta + dt_, gp.s_ping(2000, 0.25), 0.2, 0.3)
    x = np.tanh(mx.b[: int(total * SR)] * 1.1)
    fo = int(0.6 * SR); x[-fo:] *= np.linspace(1, 0, fo)[:, None]
    x = x / (np.abs(x).max() + 1e-9) * 0.89
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype("<i2").tobytes())

FADES = {"card": (8, 6), "cruise": (6, 0), "launch": (0, 4), "target": (3, 3), "fly": (4, 0), "impact": (0, 0), "radius": (0, 4), "after": (5, 14)}

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
                frame = (sensor_look(img, k) if shot == "target" else img.convert("RGB").resize((W, H), Image.LANCZOS)).convert("RGBA")
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
