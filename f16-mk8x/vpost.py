"""Finishing for the F-16 / Mk 82 / Mk 83 / Mk 84 segment: upscale to 1080p, title card, HUD overlays, one bomb at a
time (introduction with dimensions, impact, radius), a closing table of the three, synthesized sound, encode.

  python3 vpost.py <frames_root> <out.mp4> [--draft]
"""
import os, sys, json, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "blackhawk-mk77"))
import post as gp
from post import W, H, FPS, SR, AMBER, RED, INK, DIM, PANEL, F_TITLE, F_SEMI, F_MED, ease, text, shadowed, lower, callout
from npost import readout, dashed, _mod

KINDS = ("mk82", "mk83", "mk84"); TAG = {"mk82": "82", "mk83": "83", "mk84": "84"}; ORANGE = (255, 122, 40)
COL = {"mk82": AMBER, "mk83": ORANGE, "mk84": RED}
B = {"mk82": dict(name="MK 82", cls="500 lb CLASS", mass=227, fill=87, L="2.22 m", D="273 mm", fin=0.384, rs=16, rb=31, crater="4.6 – 10.7 m wide",
                  diff=("THE SMALLEST OF THE THREE", "38 % OF ITS WEIGHT IS EXPLOSIVE")),
     "mk83": dict(name="MK 83", cls="1,000 lb CLASS", mass=447, fill=202, L="3.00 m", D="357 mm", fin=0.49, rs=21, rb=41, crater="about 6 – 14 m wide",
                  diff=("TWICE THE WEIGHT OF THE MK 82", "2.3 × ITS EXPLOSIVE")),
     "mk84": dict(name="MK 84", cls="2,000 lb CLASS", mass=925, fill=429, L="3.28 m", D="458 mm", fin=0.64, rs=27, rb=53, crater="15 m wide, 11 m deep",
                  diff=("FOUR TIMES THE WEIGHT OF THE MK 82", "4.9 × ITS EXPLOSIVE"))}
ORDER = ["card", "approach", "release", "intro82", "fall", "impact82", "radius82", "intro83", "impact83", "radius83", "intro84", "impact84", "radius84", "after", "summary"]
N_SUMMARY = 168
SPECS = [("AIRCRAFT", "F-16C Fighting Falcon  ·  15.0 m long"), ("MK 82", "500 lb class  ·  87 kg of explosive"), ("MK 83", "1,000 lb class  ·  202 kg of explosive"),
         ("MK 84", "2,000 lb class  ·  429 kg of explosive"), ("RELEASE", "450 kt, level, at 1,500 m"), ("FALL", "17.5 s  ·  3.9 km of forward throw"), ("TARGETS", "Three concrete bunkers, one bomb each")]

def tag(d, a=1.0):
    text(d, (64, 54), "EXPLOSION COMPARISON", F_SEMI(30), INK, a, tracking=4)
    d.rectangle([64, 96, 64 + 54, 100], fill=(*AMBER, int(255 * a)))
    text(d, (130, 84), "07  ·  F-16  ·  MK 82, MK 83 AND MK 84 BOMBS", F_MED(26), DIM, a, tracking=2)

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
    a = ease((t - 0.35) / 0.5); text(d, (x0 + int((1 - a) * 40), 446), "MK 82  ·  MK 83  ·  MK 84", F_TITLE(54), AMBER, a, tracking=2)
    a = ease((t - 0.45) / 0.5); d.rectangle([x0, 528, x0 + int(820 * a), 531], fill=(*AMBER, int(255 * a)))
    y = 562
    for k, (lab, val) in enumerate(SPECS):
        a = ease((t - 0.65 - 0.12 * k) / 0.45); dx = int((1 - a) * 28); hot = lab.startswith("MK")
        text(d, (x0 + dx, y), lab, F_SEMI(31), COL["mk" + lab[3:]] if hot else DIM, a, tracking=3)
        text(d, (x0 + 240 + dx, y - 4), val, F_MED(38), INK, a)
        y += 60
    text(d, (x0, 1000), "One of each is carried for the comparison  ·  not a service load.", F_MED(28), DIM, ease((t - 1.9) / 0.6))
    base.alpha_composite(ov)
    return base.convert("RGB")

def _person(d, x, yfeet, ppm, a):
    """A 1.8 m standing figure for scale, drawn at the same pixels-per-metre as the bomb."""
    c = (*DIM, int(150 * a)); m = lambda v: v * ppm
    d.ellipse([x - m(0.115), yfeet - m(1.80), x + m(0.115), yfeet - m(1.57)], fill=c)
    d.rounded_rectangle([x - m(0.23), yfeet - m(1.52), x + m(0.23), yfeet - m(0.86)], radius=int(m(0.09)), fill=c)
    for sx in (-1, 1):
        xa, xb = sorted([x + sx * m(0.02), x + sx * m(0.20)]); d.rounded_rectangle([xa, yfeet - m(0.90), xb, yfeet], radius=int(m(0.05)), fill=c)             # leg
        xa, xb = sorted([x + sx * m(0.25), x + sx * m(0.34)]); d.rounded_rectangle([xa, yfeet - m(1.50), xb, yfeet - m(0.82)], radius=int(m(0.04)), fill=c)   # arm
    text(d, (x, yfeet - m(1.80) - 44), "1.8 m", F_SEMI(28), DIM, a, anchor="ma", tracking=2)

def intro_overlay(kind, i, n, m):
    """Chapter card for one bomb: name, class, weight, explosive, dimension lines on the picture, what sets it apart."""
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov); tag(d, 1.0)
    b = B[kind]; col = COL[kind]; an = m["anchors"]; u = i / (n - 1); t = i / FPS; k = KINDS.index(kind)
    ppm = (an["m1"][0] - an["m0"][0]) * W; cx = an["top"][0] * W; cy = (an["top"][1] + an["bot"][1]) / 2 * H
    _person(d, 150, an["floor"][1] * H, ppm, ease((t - 0.3) / 0.5))
    ad = ease((u - 0.46) / 0.10)
    if ad > 0:
        x0, x1 = an["tail"][0] * W, an["nose"][0] * W; y = cy + b["fin"] / 2 * ppm + 46; c = (*INK, int(235 * ad))
        d.line([(x0, y), (x1, y)], fill=c, width=3)
        for x in (x0, x1):
            d.line([(x, y - 16), (x, y + 16)], fill=c, width=3)
        text(d, ((x0 + x1) / 2, y + 14), b["L"], F_TITLE(60), INK, ad, anchor="ma")
        yt, yb = an["top"][1] * H, an["bot"][1] * H; xv = x1 + 44; g = (*INK, int(110 * ad))
        dashed(d, [(cx + 0.30 * (x1 - cx) + q * (xv + 12 - cx - 0.30 * (x1 - cx)) / 24, yt) for q in range(25)], g, 2); dashed(d, [(cx + 0.30 * (x1 - cx) + q * (xv + 12 - cx - 0.30 * (x1 - cx)) / 24, yb) for q in range(25)], g, 2)
        d.line([(xv, yt), (xv, yb)], fill=c, width=3)
        for yy in (yt, yb):
            d.line([(xv - 12, yy), (xv + 12, yy)], fill=c, width=3)
        text(d, (xv + 22, (yt + yb) / 2 - 30), b["D"], F_TITLE(48), INK, ad)
    x0 = 1470
    text(d, (x0, 150), "BOMB %d OF 3" % (k + 1), F_SEMI(30), DIM, ease((t - 0.05) / 0.4), tracking=5)
    a = ease((t - 0.12) / 0.45); text(d, (x0 + int((1 - a) * 40), 186), b["name"], F_TITLE(150), col, a)
    a = ease((t - 0.25) / 0.45); text(d, (x0, 372), b["cls"], F_TITLE(50), INK, a, tracking=1)
    a = ease((t - 0.35) / 0.45); d.rectangle([x0, 446, x0 + int(386 * a), 449], fill=(*col, int(255 * a)))
    y = 476
    for j, (lab, val) in enumerate((("WEIGHT", "%d kg" % b["mass"]), ("EXPLOSIVE", "%d kg" % b["fill"]), ("LENGTH", b["L"]), ("DIAMETER", b["D"]))):
        a = ease((t - 0.55 - 0.14 * j) / 0.4); dx = int((1 - a) * 24)
        text(d, (x0 + dx, y + 6), lab, F_SEMI(30), DIM, a, tracking=3); text(d, (x0 + 386 + dx, y - 4), val, F_MED(44), INK, a, anchor="ra")
        y += 62
    a = ease((t - 1.5) / 0.5)
    lower(d, b["diff"][0], b["diff"][1] + ("  ·  tritonal or H-6 in a forged steel case" if kind == "mk82" else "  ·  the same shape, scaled up" if kind == "mk83" else "  ·  the largest of the Mk 80 series"), a)
    return ov

def _leader(d, px, py, tx, ty, col, a):
    d.line([(px, py), (tx - 18, ty)], fill=(*col, int(230 * a)), width=3); d.ellipse([px - 7, py - 7, px + 7, py + 7], outline=(*col, int(255 * a)), width=3)

def overlay_for(shot, i, n, m, info):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    t = m["t"]; td = m.get("td", 0.0); an = m.get("anchors", {})
    tag(d, ease(i / 8.0) if shot == "approach" else 1.0)
    io = ease((i - 5) / 9.0) * (1 - ease((i - (n - 7)) / 7.0)); kind = "mk" + shot[-2:] if shot[-2:] in ("82", "83", "84") else None
    if shot == "approach":
        lower(d, "RUNNING IN", "F-16C  ·  three bombs of the same family, each twice the weight of the one before", io)
        readout(d, "HEIGHT", "1,500 m", ease((i - 10) / 10.0), AMBER, "SPEED  450 kt")
        rows = (("mk82", "UNDER THE LEFT WING", True), ("mk83", "UNDER THE RIGHT WING", False), ("mk84", "ON THE CENTRE LINE", True))
        for j, (k, where, lead) in enumerate(rows):
            a = ease((i - 26 - 12 * j) / 8.0) * (1 - ease((i - (n - 8)) / 7.0)); y = 160 + 118 * j
            if a > 0:
                text(d, (W - 64, y), B[k]["name"], F_TITLE(60), COL[k], a, anchor="ra"); text(d, (W - 64, y + 70), "%s  ·  %s" % (where, B[k]["cls"]), F_SEMI(28), INK, a, anchor="ra", tracking=2)
                if lead and 0.03 < an[k][0] < 0.97:
                    _leader(d, an[k][0] * W, an[k][1] * H, W - 64 - 210, y + 40, COL[k], a * 0.8)
    elif shot == "release":
        if t < 0:
            lower(d, "OVER THE RELEASE POINT", "Level at 1,500 m  ·  3.9 km short of the first bunker", ease((i - 2) / 6.0))
        else:
            R = info["REL"]; cur = [k for k in KINDS if t >= R[k]][-1]
            lower(d, "RELEASE", "One after another, 0.6 s apart  ·  each lands on its own bunker, about 155 m further on", 1 - ease((i - (n - 8)) / 8.0))
            readout(d, "SLOW MOTION", "T + %04d ms" % round(t * 1000), 1.0, INK, "%s AWAY" % B[cur]["name"])
            for k, (dx, dy) in (("mk82", (110, -70)), ("mk83", (-330, 70)), ("mk84", (120, 60))):
                a = ease((t - R[k]) / 0.08) * (1 - ease((t - R[k] - 0.5) / 0.1))
                if a > 0 and 0.03 < an[k][1] < 0.92 and 0.03 < an[k][0] < 0.97:
                    callout(d, an[k][0] * W, an[k][1] * H, B[k]["name"], "%d kg" % B[k]["mass"], COL[k], a, dx=dx, dy=dy)
    elif shot == "fall":
        a = ease((i - 2) / 8.0)
        readout(d, "HEIGHT", "%d m" % round(m.get("alt", 0)), a, AMBER, "%d m/s  ·  IMPACT IN %.1f s" % (round(m.get("v", 0)), max(-td, 0)))
        lower(d, "%d SECONDS LATER" % round(info["TOF"]["mk82"]), "%.1f km down range  ·  all three arrive at about %d m/s and %d°" % (info["FWD"]["mk82"] / 1000.0, round(info["V_HIT"]["mk82"]), round(info["ANGLE"]["mk82"])),
              ease((i - 6) / 10.0) * (1 - ease((i - (n - 8)) / 8.0)))
    elif shot.startswith("impact"):
        readout(d, "SLOW MOTION", "T + %03d ms" % max(0, round(td * 1000)), ease((i - 2) / 6.0), INK, "%s  ·  %d kg OF EXPLOSIVE" % (B[kind]["name"], B[kind]["fill"]))
        a = ease((i - 12) / 10.0) * (1 - ease((i - (n - 12)) / 10.0))
        sub = {"mk82": "Instantaneous fuze on the roof of the first bunker", "mk83": "2.3 × the explosive  ·  the camera stands 1.3 × further back than for the Mk 82",
               "mk84": "4.9 × the explosive  ·  the camera stands 1.7 × further back than for the Mk 82"}[kind]
        lower(d, B[kind]["name"] + " ON A BUNKER", sub, a)
    elif shot.startswith("radius"):
        b = B[kind]; P = lambda q: (q[0] * W, q[1] * H); a0 = ease((td - 0.25) / 0.3); a1 = ease((td - 0.9) / 0.3); ag = ease((td - 1.3) / 0.3)
        text(d, (W - 64, 150), b["name"], F_TITLE(110), COL[kind], 1.0, anchor="ra"); text(d, (W - 64, 278), "%d kg OF EXPLOSIVE" % b["fill"], F_SEMI(32), INK, 1.0, anchor="ra", tracking=3)
        for k in KINDS[:KINDS.index(kind)]:                                    # the smaller bombs already shown, faintly
            pg = [P(q) for q in m.get("path_g_" + k, [])]
            if ag > 0 and len(pg) > 2:
                dashed(d, pg, (*INK, int(150 * ag)), 2, on=2, off=2); q = P(an["g_" + k]); text(d, (q[0], q[1] - 40), "%s  ·  %d m" % (B[k]["name"], B[k]["rb"]), F_SEMI(26), INK, ag * 0.85, anchor="ma", tracking=2)
        ps = [P(q) for q in m.get("path_struct", [])]; pb = [P(q) for q in m.get("path_blast", [])]
        if a0 > 0 and len(ps) > 2:
            d.line([(x, y + 2) for x, y in ps], fill=(0, 0, 0, int(120 * a0)), width=7); d.line(ps, fill=(*RED, int(235 * a0)), width=5)
            callout(d, *P(an["struct"]), "%s%d m" % ("" if kind == "mk82" else "≈ ", b["rs"]), "CONCRETE BUILDINGS DESTROYED", RED, a0, dx=110, dy=140)
        if a1 > 0 and len(pb) > 2:
            dashed(d, pb, (*AMBER, int(235 * a1)), 4)
            callout(d, *P(an["blast"]), "%s%d m" % ("" if kind == "mk82" else "≈ ", b["rb"]), "34 kPa (5 psi) BLAST", AMBER, a1, dx=-400, dy=-70)
        sub = {"mk82": "Published radii for the Mk 82  ·  the next two bombs are shown from exactly this camera",
               "mk83": "2.3 × the explosive, 1.3 × the radius  ·  scaled from the Mk 82 by the cube root of the filling (estimate)",
               "mk84": "4.9 × the explosive, only 1.7 × the radius  ·  blast reach grows with the cube root of the filling (estimate)"}[kind]
        lower(d, "HOW FAR IT REACHES", sub, ease((td - 0.5) / 0.3))
    elif shot == "after":
        lab = {"mk82": "ROOF HOLED  ·  STRUCTURE STANDING", "mk83": "ROOF BROKEN OPEN  ·  WALLS STANDING", "mk84": "ROOF GONE  ·  INTERIOR WRECKED"}
        for k in KINDS:
            x, y, z = an[k]; a = ease((x - 0.16) / 0.10) * ease((0.80 - x) / 0.10) if z > 0 else 0.0
            if a > 0:
                callout(d, x * W, y * H, B[k]["name"], lab[k], COL[k], a, dx=-420, dy=-250)
        lower(d, "HALF A MINUTE LATER", "General-purpose bombs crater, spall and hole  ·  hardened targets need penetrating bombs", ease((i - 10) / 12.0) * (1 - ease((i - (n - 10)) / 8.0)))
    return ov

def summary_frame(bg, i, n):
    """Closing table over the darkened last frame: the three bombs, figure by figure."""
    frame = bg.copy(); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov); t = i / FPS; tag(d, 1.0)
    text(d, (120, 170), "THE THREE COMPARED", F_TITLE(84), INK, ease((t - 0.1) / 0.5))
    xl = 120; xc = [900, 1250, 1600]; y = 300
    for j, k in enumerate(KINDS):
        a = ease((t - 0.3 - 0.12 * j) / 0.4); text(d, (xc[j], y), B[k]["name"], F_TITLE(72), COL[k], a, anchor="ma")
    a = ease((t - 0.5) / 0.5); d.rectangle([xl, y + 100, xl + int(1680 * a), y + 103], fill=(*AMBER, int(255 * a)))
    rows = [("CLASS", [B[k]["cls"].replace(" CLASS", "") for k in KINDS], None), ("WEIGHT", ["%d kg" % B[k]["mass"] for k in KINDS], [B[k]["mass"] / 925.0 for k in KINDS]),
            ("EXPLOSIVE", ["%d kg" % B[k]["fill"] for k in KINDS], [B[k]["fill"] / 429.0 for k in KINDS]), ("LENGTH  ×  DIAMETER", ["%s × %s" % (B[k]["L"], B[k]["D"]) for k in KINDS], None),
            ("CONCRETE BUILDINGS DESTROYED WITHIN", ["16 m", "≈ 21 m", "≈ 27 m"], [B[k]["rs"] / 27.0 for k in KINDS]), ("34 kPa (5 psi) BLAST REACHES", ["31 m", "≈ 41 m", "≈ 53 m"], [B[k]["rb"] / 53.0 for k in KINDS]),
            ("CRATER", [B[k]["crater"] for k in KINDS], None)]
    y += 122
    for r, (lab, vals, bars) in enumerate(rows):
        a = ease((t - 0.8 - 0.22 * r) / 0.45); dx = int((1 - a) * 24)
        text(d, (xl + dx, y + 8), lab, F_SEMI(30), DIM, a, tracking=3)
        for j, v in enumerate(vals):
            text(d, (xc[j] + dx, y), v, F_MED(40 if len(v) < 14 else 32), INK, a, anchor="ma")
            if bars:
                wb = int(130 * bars[j] * a); d.rectangle([xc[j] - 130, y + 52, xc[j] + 130, y + 55], fill=(*DIM, int(60 * a))); d.rectangle([xc[j] - 130, y + 52, xc[j] - 130 + 2 * wb, y + 57], fill=(*COL[KINDS[j]], int(255 * a)))
        y += 74
    a = ease((t - 2.9) / 0.6)
    text(d, (xl, 960), "Five times the explosive does not give five times the reach: blast radius grows with the cube root, here 1.7 times.", F_MED(32), INK, a)
    text(d, (xl, 1004), "Mk 82 radii are published (GICHD); Mk 83 and Mk 84 radii are scaled from them and are estimates. Mk 84 crater: published.", F_MED(26), DIM, a)
    frame.alpha_composite(ov)
    return frame

# ------------------------------------------------------------------ sound
def s_jet(dur, seed=3):
    """A jet close by: broadband roar with a thin compressor whine over it."""
    n = int(dur * SR); t = np.arange(n) / SR
    x = gp.bp(gp.noise(n), 120, 1800) * 1.4 * _mod(n, 2.0, 0.25, seed) + gp.hp(gp.lp(gp.noise(n), 7000, 1), 2500) * 0.25 + gp.lp(gp.noise(n), 100, 2) * 1.6
    return x + 0.05 * np.sin(2 * np.pi * 2900 * t + 3 * np.sin(2 * np.pi * 0.7 * t))

def s_blast(scale):
    """A large bomb at a distance of a few dozen metres: sharp crack, then a long heavy rumble; bigger bombs are lower and longer."""
    n = int((3.5 + scale) * SR); t = np.arange(n) / SR
    crack = gp.noise(n) * np.exp(-t / 0.012) * 3.0
    body = gp.lp(gp.noise(n), 160 / scale, 3) * 9.0 * np.minimum(1.0, t / 0.01) * np.exp(-t / (0.55 * scale))
    tail = gp.bp(gp.noise(n), 60, 500) * 1.6 * np.exp(-t / (1.3 * scale)) * _mod(n, 3.0, 0.4, 17)
    sub = np.sin(2 * np.pi * np.cumsum(np.linspace(55 / scale, 24, n)) / SR) * 1.4 * np.exp(-t / (0.5 * scale))
    return crack + body + tail + sub

SCALE = {"mk82": 1.0, "mk83": 1.32, "mk84": 1.70}; GAIN = {"mk82": 0.72, "mk83": 0.86, "mk84": 1.0}

def build_audio(path, starts, metas, lens, total):
    mx = gp.Mix(total); T = {k: v / FPS for k, v in starts.items()}; L = {k: v / FPS for k, v in lens.items()}
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
    for tt, pan in ((0.0, 0.4), (0.6, -0.4), (1.2, 0.0)):
        tr = when("release", lambda m, tt=tt: m["t"] >= tt)
        if tr:
            mx.add(tr, gp.s_thud(0.6), 0.9, pan); mx.add(tr + 0.02, gp.s_ping(260, 0.35), 0.3, pan)
    for k in KINDS:
        ti = T["intro" + TAG[k]]; mx.add(ti, gp.s_drone(L["intro" + TAG[k]]), 0.45); mx.add(ti + 0.08, gp.s_thud(1.0 * SCALE[k]), 0.5); mx.add(ti - 0.3, gp.s_whoosh(0.5, 200, 1200, 0.8), 0.3)
        for j in range(4):
            mx.add(ti + 0.55 + 0.14 * j, gp.s_tick(), 0.3, 0.4)
        mx.add(ti + L["intro" + TAG[k]] * 0.46, gp.s_ping(520, 0.3), 0.22, -0.2)
        th = when("impact" + TAG[k], lambda m: m["td"] >= 0); g = GAIN[k]
        if th:
            mx.add(th, s_blast(SCALE[k]), g, 0.0); mx.add(th + 0.25, gp.s_debris(3.5, 80, 2.2), 0.55 * g, 0.2); mx.add(th + 0.1, gp.s_ring(3.0), 0.5 * g)
        tb = T["radius" + TAG[k]]; mx.add(tb, s_blast(SCALE[k]), 0.62 * g, 0.0); mx.add(tb + 0.3, gp.s_debris(3.0, 60, 1.8), 0.35 * g, 0.0)
    mx.add(T["fall"], gp.s_whoosh(L["fall"], 300, 2200, 0.8) * 0.9, 0.6); mx.add(T["fall"], gp.s_wind(L["fall"]) * 0.35, 1.0, 0.0)
    ta = T["after"]; mx.add(ta, gp.s_wind(L["after"] + L["summary"]) * 0.14, 1.0, -0.1); mx.add(ta + 0.2, gp.s_debris(L["after"] - 0.5, 14, 0.7), 0.18, 0.2)
    for u0 in (0.20, 0.60):
        mx.add(ta + u0 * L["after"], gp.s_whoosh(0.22 * L["after"], 150, 900, 0.8), 0.3)
    ts = T["summary"]; mx.add(ts, gp.s_drone(L["summary"]), 0.45); mx.add(ts + 0.1, gp.s_thud(1.2), 0.4)
    for r in range(7):
        mx.add(ts + 0.8 + 0.22 * r, gp.s_tick(), 0.3, 0.3)
    x = np.tanh(mx.b[: int(total * SR)] * 1.1)
    fo = int(0.8 * SR); x[-fo:] *= np.linspace(1, 0, fo)[:, None]
    x = x / (np.abs(x).max() + 1e-9) * 0.89
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype("<i2").tobytes())

FADES = {"card": (8, 6), "approach": (6, 0), "release": (0, 5), "fall": (5, 0), "after": (5, 0), "summary": (0, 16)}
for _k in KINDS:
    FADES["intro" + TAG[_k]] = (5, 5); FADES["impact" + TAG[_k]] = (0 if _k == "mk82" else 5, 4); FADES["radius" + TAG[_k]] = (4, 6)

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
    starts = {}; metas = {}; lens = {}; g = 0; last = None
    for shot in ORDER:
        starts[shot] = g; fi, fo = FADES[shot]
        if shot == "summary":
            n = N_SUMMARY; metas[shot] = {}; bg = Image.blend(last.convert("RGB").filter(ImageFilter.GaussianBlur(14)), Image.new("RGB", (W, H), PANEL), 0.80).convert("RGBA")
        else:
            d1, f1, m1 = _load(root, shot); n = len(f1); metas[shot] = m1
        lens[shot] = n
        for k in range(n):
            if shot == "card":
                frame = card_frame(Image.open(os.path.join(d1, f1[k])), k, n).convert("RGBA")
            elif shot == "summary":
                a = ease(k / 14.0); frame = Image.blend(last, summary_frame(bg, k, n), a) if a < 1 else summary_frame(bg, k, n)
            else:
                frame = Image.open(os.path.join(d1, f1[k])).convert("RGB").resize((W, H), Image.LANCZOS).convert("RGBA")
                if shot == "after" and k == n - 1:
                    last = frame.copy()
                shadowed(frame, intro_overlay("mk" + shot[-2:], k, n, m1[str(k)]) if shot.startswith("intro") else overlay_for(shot, k, n, m1[str(k)], info))
            fade = min(1.0, (k + 1) / fi if fi else 1.0, (n - k) / fo if fo else 1.0)
            if fade < 1.0:
                frame = Image.blend(Image.new("RGBA", frame.size, (0, 0, 0, 255)), frame, fade)
            frame.convert("RGB").save(os.path.join(stage, "m%05d.png" % g), compress_level=1); g += 1
        print("staged", shot, n); sys.stdout.flush()
    total = g / FPS
    wav = os.path.join(root, "mix.wav"); build_audio(wav, starts, metas, lens, total)
    vf = "unsharp=5:5:0.55:5:5:0.0,vignette=PI/7,noise=alls=4:allf=t+u,format=yuv420p"
    cmd = ["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", os.path.join(stage, "m%05d.png"), "-i", wav,
           "-vf", vf, "-c:v", "libx264", "-preset", "medium" if draft else "slow", "-crf", "21" if draft else "18",
           "-maxrate", "14M", "-bufsize", "28M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest", out]
    subprocess.check_call(cmd)
    print("wrote", out, "%.2fs" % total, starts)

if __name__ == "__main__":
    main()
