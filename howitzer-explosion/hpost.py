"""Finishing for the 155 mm howitzer segment: upscale to 1080p, title card, HUD overlays, synthesized sound, encode.

  python3 hpost.py <frames_root> <out.mp4> [--draft]

Reuses the typography, overlay helpers and sound synths of the M67 segment (../grenade-explosion/post.py).
"""
import os, sys, json, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion"))
import post as gp
from post import W, H, FPS, SR, AMBER, RED, INK, DIM, PANEL, F_TITLE, F_SEMI, F_MED, ease, text, shadowed, lower, callout

ORDER = ["card", "load", "ram", "charge", "fire", "fall", "impact", "radius", "after"]
SPECS = [("TYPE", "Lightweight towed howitzer"), ("WEIGHT", "4,200 kg  ·  titanium carriage"), ("CREW", "8  ·  5 at the minimum"),
         ("SHELL", "M795 HE  ·  46.7 kg  ·  10.8 kg TNT"), ("MUZZLE VELOCITY", "827 m/s at top charge"), ("RANGE", "22.5 km with the M795"), ("LETHAL RADIUS", "50 – 150 m")]

def tag(d, a=1.0):
    text(d, (64, 54), "EXPLOSION COMPARISON", F_SEMI(30), INK, a, tracking=4)
    d.rectangle([64, 96, 64 + 54, 100], fill=(*AMBER, int(255 * a)))
    text(d, (130, 84), "04  ·  M777  ·  155 MM HOWITZER  ·  M795 HE", F_MED(26), DIM, a, tracking=2)

def card_frame(img, i, n):
    base = Image.new("RGBA", (W, H), (*PANEL, 255))
    base.paste(img.convert("RGB").resize((W // 2, H), Image.LANCZOS), (0, 0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    grad = Image.linear_gradient("L").rotate(90, expand=True).resize((90, H))
    seam = Image.new("RGBA", (90, H), (*PANEL, 255)); seam.putalpha(grad.point(lambda v: 255 - v))
    base.alpha_composite(seam.transpose(Image.FLIP_LEFT_RIGHT), (W // 2 - 90, 0))
    t = i / FPS; x0 = W // 2 + 96
    text(d, (x0, 150), "EXPLOSION COMPARISON  ·  04", F_SEMI(30), DIM, ease((t - 0.10) / 0.5), tracking=5)
    a = ease((t - 0.20) / 0.5); text(d, (x0 + int((1 - a) * 40), 196), "M777", F_TITLE(210), INK, a)
    a = ease((t - 0.35) / 0.5); text(d, (x0 + int((1 - a) * 40), 446), "155 MM HOWITZER  ·  M795 HE SHELL", F_TITLE(54), AMBER, a, tracking=2)
    a = ease((t - 0.45) / 0.5); d.rectangle([x0, 528, x0 + int(820 * a), 531], fill=(*AMBER, int(255 * a)))
    y = 562
    for k, (lab, val) in enumerate(SPECS):
        a = ease((t - 0.65 - 0.12 * k) / 0.45); dx = int((1 - a) * 28); hot = lab == "LETHAL RADIUS"
        text(d, (x0 + dx, y), lab, F_SEMI(31), RED if hot else DIM, a, tracking=3)
        text(d, (x0 + 300 + dx, y - 4), val, F_SEMI(40) if hot else F_MED(38), INK, a)
        y += 60
    text(d, (x0, 1000), "Fired here at a war-damaged town 18 km away.", F_MED(28), DIM, ease((t - 1.9) / 0.6))
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
    io = ease((i - 5) / 9.0) * (1 - ease((i - (n - 7)) / 7.0))
    if shot == "load":
        lower(d, "LOADING", "Breech open, tray in  ·  two cannoneers bring up the 46.7 kg shell and slide it onto the tray", io)
        readout(d, "PROJECTILE", "M795 HE", ease((i - 10) / 10.0), AMBER, "46.7 kg  ·  10.8 kg TNT")
    elif shot == "ram":
        lower(d, "RAMMING", "The two cannoneers drive the shell home with the rammer staff", io)
    elif shot == "charge":
        a1 = ease((i - 5) / 9.0) * (1 - ease((i - 44) / 8.0)); a2 = ease((i - 52) / 8.0) * (1 - ease((i - (n - 7)) / 7.0))
        if a1 > 0:
            lower(d, "CHARGE", "Five propellant increments go in behind the shell", a1)
        if a2 > 0:
            lower(d, "READY", "Tray out, breech closed  ·  cannoneer 1 hooks the lanyard", a2)
        readout(d, "PROPELLING CHARGE", "MACS  ×  5", ease((i - 10) / 10.0), AMBER, "TOP CHARGE")
    elif shot == "fire":
        if t < 0:
            a1 = ease((i - 3) / 8.0) * (1 - ease((t + 1.2) / 0.25)); a2 = ease((t + 1.0) / 0.25)
            if a1 > 0:
                lower(d, "LAYING", "The gunner brings the tube up from loading elevation to the firing data", a1)
            if a2 > 0:
                lower(d, "FIRE", "The section chief drops his arm  ·  cannoneer 1 pulls the lanyard", a2)
            readout(d, "ELEVATION", "%d mils" % round(m.get("elev_mils", 0)), ease((i - 3) / 8.0), AMBER, "TARGET  18 km")
        else:
            lower(d, "THE SHOT", "The tube runs back on its recoil system  ·  the muzzle brake throws the blast sideways", 1 - ease((i - (n - 8)) / 8.0))
            readout(d, "SLOW MOTION", "T + %03d ms" % round(t * 1000), 1.0, INK, "LEAVES AT %d m/s" % round(info["V0"]))
    elif shot == "fall":
        a = ease((i - 2) / 8.0)
        readout(d, "ALTITUDE", "%d m" % round(m.get("alt", 0)), a, AMBER, "%d m/s  ·  IMPACT IN %.1f s" % (round(m.get("v", 0)), max(-td, 0)))
        lower(d, "%d SECONDS LATER" % round(info["TOF"]), "18 km down range  ·  about %.0f km high on the way  ·  arriving at about %d° (point-mass estimate)"
              % (info["APEX"] / 1000.0, round(info["FALL_DEG"])), ease((i - 6) / 10.0) * (1 - ease((i - (n - 8)) / 8.0)))
    elif shot == "impact":
        readout(d, "SLOW MOTION", "T + %03d ms" % max(0, round(td * 1000)), ease((i - 2) / 6.0))
        lower(d, "DETONATION", "10.8 kg of TNT in a steel body  ·  the fuze fires on contact", ease((i - 12) / 10.0) * (1 - ease((i - (n - 14)) / 10.0)))
    elif shot == "radius":
        rf = m.get("r_front", 0.0); done = rf >= info["CASUALTY_R"] - 0.01
        for nm, colr, wd in (("casualty", AMBER, 5), ("lethal", RED, 6), ("m67", INK, 3)):          # ground circles projected to the screen
            pts = [(x * W, y * H) for x, y in m.get("circle_" + nm, [])]
            if len(pts) > 2:
                if nm == "lethal" and done:
                    d.polygon(pts, fill=(*RED, 26))
                d.line([(x, y + 2) for x, y in pts], fill=(0, 0, 0, 120), width=wd + 2); d.line(pts, fill=(*colr, 235), width=wd)
        if not done:
            readout(d, "FRAGMENTS REACH", "%d m" % round(rf), 1.0, AMBER, "T + %03d ms" % max(0, round(td * 1000)))
        else:
            a = ease((td - 0.13) / 0.10)
            callout(d, an["lethal"][0] * W, an["lethal"][1] * H, "50 – 150 m", "EXPECTED LETHAL RADIUS  ·  RING AT 50 m", RED, a, dx=-700, dy=-60)
            a2 = ease((td - 0.35) / 0.12)
            if a2 > 0:
                callout(d, an["casualty"][0] * W, an["casualty"][1] * H, "100 – 300 m", "EXPECTED CASUALTY RADIUS  ·  RING AT 100 m", AMBER, a2, dx=-760, dy=-250)
            a3 = ease((td - 0.65) / 0.12)
            if a3 > 0:
                callout(d, an["m67"][0] * W, an["m67"][1] * H, "15 m", "M67 HAND GRENADE, FOR SCALE", INK, a3, dx=-470, dy=150)
        lower(d, "THE REAL REACH", "The rings mark the lower bounds of the published figures  ·  source: Human Rights Watch", ease((td - 0.30) / 0.2))
    elif shot == "after":
        a1 = ease((i - 8) / 8.0) * (1 - ease((i - 40) / 8.0)); a2 = ease((i - 30) / 8.0) * (1 - ease((i - 62) / 8.0))
        if a1 > 0:
            callout(d, an["crater"][0] * W, an["crater"][1] * H, "IMPACT", "CRATER IN THE STREET", RED, a1, dx=90, dy=130)
        if a2 > 0:
            callout(d, an["wall"][0] * W, an["wall"][1] * H, "3 m AWAY", "HOUSE FRONT AND FLOOR SLABS DOWN", AMBER, a2, dx=-620, dy=-150)
        lower(d, "WHAT IT CAN DO", "One 155 mm shell  ·  lethal to 50 m and beyond, casualties to 100 m and beyond", ease((i - 46) / 12.0))
    return ov

# ------------------------------------------------------------------ sound
def s_whistle(dur):
    n = int(dur * SR); t = np.arange(n) / SR; u = t / dur
    f = 1100 - 700 * u ** 1.5; ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * 0.35 + gp.bp(gp.noise(n), 300, 2600) * 0.9 + gp.lp(gp.noise(n), 200, 2) * 1.2
    return x * (0.08 + 0.92 * u ** 2.0)

def build_audio(path, starts, metas, total):
    mx = gp.Mix(total); T = {k: v / FPS for k, v in starts.items()}
    def when(shot, pred):
        m = metas[shot]
        for i in sorted(int(k) for k in m):
            if pred(m[str(i)]):
                return T[shot] + i / FPS
        return None
    amb0 = T["load"]; mx.add(amb0, gp.s_wind(total - amb0) * 0.05, 1.0, -0.1)
    mx.add(0.0, gp.s_drone(T["load"] + 0.2), 0.5); mx.add(0.05, gp.s_thud(1.2), 0.5)
    for k in range(len(SPECS)):
        mx.add(0.65 + 0.12 * k, gp.s_tick(), 0.35, 0.3)
    mx.add(T["load"] - 0.45, gp.s_whoosh(0.6, 200, 1500, 0.8), 0.35)
    def at(shot, tt):
        return when(shot, lambda m: m["t"] >= tt)
    for shot, tt, snd, g, pan in (("load", -16.0, gp.s_thud(0.4), 0.45, -0.2), ("load", -15.2, gp.s_ping(520, 0.3), 0.25, -0.2), ("load", -14.9, gp.s_thud(0.3), 0.3, 0.2),
                                  ("load", -13.6, gp.s_ping(380, 0.35), 0.3, 0.0), ("load", -12.8, gp.s_thud(0.45), 0.5, 0.0),
                                  ("ram", -10.0, gp.s_whoosh(0.6, 300, 1400, 0.5), 0.4, 0.0), ("ram", -9.42, gp.s_thud(0.5), 0.9, 0.0), ("ram", -9.40, gp.s_ping(300, 0.6), 0.45, 0.0),
                                  ("charge", -6.9, gp.s_whoosh(1.0, 500, 900, 0.3), 0.2, 0.1), ("charge", -5.75, gp.s_thud(0.3), 0.4, 0.1), ("charge", -4.85, gp.s_thud(0.3), 0.3, -0.2),
                                  ("charge", -3.98, gp.s_thud(0.5), 0.8, 0.0), ("charge", -3.95, gp.s_ping(440, 0.5), 0.4, 0.0), ("charge", -3.4, gp.s_tick(), 0.6, -0.2),
                                  ("fire", -0.05, gp.s_tick(), 0.9, -0.2)):
        tw = at(shot, tt)
        if tw:
            mx.add(tw, snd, g, pan)
    tf = when("fire", lambda m: m["t"] >= 0)
    if tf:
        mx.add(tf, gp.s_boom(1.0, 3.2), 1.0); mx.add(tf + 0.01, gp.s_boom(0.7, 1.4), 0.7, 0.2); mx.add(tf + 0.04, gp.s_ring(3.0), 0.6)
        mx.add(tf + 0.05, gp.s_whoosh(2.6, 300, 1600, 0.15), 0.6, 0.0); mx.add(tf + 0.5, gp.s_debris(1.8, 12, 1.2), 0.2, -0.2)
    nf = len(metas["fall"]) / FPS
    mx.add(T["fall"], gp.s_whoosh(nf, 300, 1400, 0.5) * 0.8, 0.5); mx.add(T["fall"], s_whistle(nf + 0.35), 0.5, 0.0)
    th = when("impact", lambda m: m["td"] >= 0)
    if th:
        mx.add(th, gp.s_boom(1.0, 3.6), 1.0); mx.add(th + 0.02, gp.s_boom(0.7, 1.5), 0.7, 0.2)
        mx.add(th + 0.2, gp.s_debris(4.4, 90, 2.4), 0.8, 0.2); mx.add(th + 0.05, gp.s_ring(4.2), 0.9)
        mx.add(th + 0.6, gp.s_whoosh(2.6, 120, 700, 0.3), 0.6, 0.2)
    tb = T["radius"]
    mx.add(tb, gp.s_boom(0.9, 2.8), 0.85, 0.0); mx.add(tb + 0.1, gp.s_whoosh(1.2, 600, 2600, 0.25), 0.4, 0.0); mx.add(tb + 0.3, gp.s_debris(2.8, 50, 1.8), 0.35, 0.0)
    for dt_ in (1.3, 1.9, 2.5):
        mx.add(tb + dt_, gp.s_ping(2000, 0.25), 0.22, 0.3)
    mx.add(T["after"] + 0.1, gp.s_debris(2.2, 8, 1.0), 0.2, 0.2)
    for dt_ in (0.4, 1.3, 2.0):
        mx.add(T["after"] + dt_, gp.s_ping(2000, 0.25), 0.2, 0.3)
    x = np.tanh(mx.b[: int(total * SR)] * 1.1)
    fo = int(0.6 * SR); x[-fo:] *= np.linspace(1, 0, fo)[:, None]
    x = x / (np.abs(x).max() + 1e-9) * 0.89
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype("<i2").tobytes())

FADES = {"card": (8, 6), "load": (6, 0), "ram": (0, 0), "charge": (0, 0), "fire": (0, 5), "fall": (5, 0), "impact": (0, 0), "radius": (0, 4), "after": (5, 14)}

def main():
    root = sys.argv[1]; out = sys.argv[2]; draft = "--draft" in sys.argv
    info = {}
    for nm in ("timeline_gun.json", "timeline_town.json"):
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
