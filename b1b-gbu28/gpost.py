"""Finishing for the B-1B / GBU-28 segment: upscale to 1080p, title card, captions, the depth scale and labels on the
section, a closing table, synthesized sound, encode.

  python3 gpost.py <frames_root> <out.mp4> [--draft]
"""
import os, sys, json, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "blackhawk-mk77"))
import post as gp
from post import W, H, FPS, SR, AMBER, RED, INK, DIM, PANEL, F_TITLE, F_SEMI, F_MED, ease, text, shadowed, lower, callout
from npost import readout, dashed, _mod, s_roar, s_crackle

ORDER = ["card", "approach", "intro", "release", "fall", "strike", "cutaway", "after", "summary"]
N_SUMMARY = 228
HOLD = {"cutaway": 56}                                               # the first frame of the section is held while its caption is read
SPECS = [("BOMB", "GBU-28/B  ·  BLU-113 warhead"), ("SIZE", "5.84 m long  ·  370 mm across"), ("WEIGHT", "about 2,130 kg (4,700 lb)"), ("EXPLOSIVE", "286 kg of tritonal"),
         ("CASE", "steel 58 mm thick"), ("GUIDANCE", "laser (Paveway III), later with GPS"), ("FIRST USED", "27 February 1991, from an F-111F")]
KMH = lambda v: int(round(v * 3.6, -1))

def tag(d, a=1.0):
    text(d, (64, 54), "EXPLOSION COMPARISON", F_SEMI(30), INK, a, tracking=4)
    d.rectangle([64, 96, 64 + 54, 100], fill=(*AMBER, int(255 * a)))
    text(d, (130, 84), "10  ·  GBU-28 BUNKER BUSTER  ·  B-1B LANCER", F_MED(26), DIM, a, tracking=2)

def card_frame(img, i, n):
    base = Image.new("RGBA", (W, H), (*PANEL, 255))
    base.paste(img.convert("RGB").resize((W // 2, H), Image.LANCZOS), (0, 0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    grad = Image.linear_gradient("L").rotate(90, expand=True).resize((90, H))
    seam = Image.new("RGBA", (90, H), (*PANEL, 255)); seam.putalpha(grad.point(lambda v: 255 - v))
    base.alpha_composite(seam.transpose(Image.FLIP_LEFT_RIGHT), (W // 2 - 90, 0))
    t = i / FPS; x0 = W // 2 + 96
    text(d, (x0, 130), "EXPLOSION COMPARISON  ·  10", F_SEMI(30), DIM, ease((t - 0.10) / 0.5), tracking=5)
    a = ease((t - 0.20) / 0.5); text(d, (x0 + int((1 - a) * 40), 180), "GBU-28", F_TITLE(170), INK, a)
    a = ease((t - 0.35) / 0.5); text(d, (x0 + int((1 - a) * 40), 400), "A 5,000 LB BUNKER BUSTER, 20 m UNDER THE DESERT", F_TITLE(38), AMBER, a, tracking=1)
    a = ease((t - 0.45) / 0.5); d.rectangle([x0, 478, x0 + int(820 * a), 481], fill=(*AMBER, int(255 * a)))
    y = 512
    for k, (lab, val) in enumerate(SPECS):
        a = ease((t - 0.65 - 0.12 * k) / 0.45); dx = int((1 - a) * 28); hot = lab == "EXPLOSIVE"
        text(d, (x0 + dx, y), lab, F_SEMI(31), RED if hot else DIM, a, tracking=3)
        text(d, (x0 + 250 + dx, y - 4), val, F_MED(36), INK, a)
        y += 58
    a = ease((t - 1.7) / 0.6)
    text(d, (x0, 936), "In service this bomb is dropped by the F-15E and the B-2. The B-1B", F_MED(28), INK, a)
    text(d, (x0, 970), "of this film has flown its successor, the GBU-72, on a pylon like the one shown.", F_MED(28), INK, a)
    text(d, (x0, 1016), "The bunker and the strike are invented. Depths are calculated, not measured.", F_MED(26), DIM, a)
    base.alpha_composite(ov)
    return base.convert("RGB")

def dim_line(d, p0, p1, label, a, color=INK, off=-46, tick=14):
    """A dimension line between two screen points with end ticks and a centred label."""
    if a <= 0:
        return
    c = (*color, int(235 * a)); d.line([p0, p1], fill=c, width=3)
    vx, vy = p1[0] - p0[0], p1[1] - p0[1]; L_ = math.hypot(vx, vy) + 1e-6; nx, ny = -vy / L_ * tick, vx / L_ * tick
    for p in (p0, p1):
        d.line([(p[0] - nx, p[1] - ny), (p[0] + nx, p[1] + ny)], fill=c, width=3)
    text(d, ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 + off), label, F_SEMI(34), color, a, anchor="ma", tracking=2)

def note(d, p, big, small, a, color=INK, dx=0, dy=0, anchor="la"):
    if a > 0:
        text(d, (p[0] + dx, p[1] + dy), big, F_TITLE(42), color, a, anchor=anchor); text(d, (p[0] + dx, p[1] + dy + 50), small, F_SEMI(25), INK, a, anchor=anchor, tracking=2)


def cut_overlay(d, i, n, m, info, hold):
    """The section: a depth scale that follows the nose, the layers named as the bomb reaches them, speed and time."""
    an = m["anchors"]; o, ex, ez = an["o"], an["ex"], an["ez"]
    PX = lambda x, z: ((o[0] + x * (ex[0] - o[0]) + z * (ez[0] - o[0])) * W, (o[1] + x * (ex[1] - o[1]) + z * (ez[1] - o[1])) * H)
    pre, pen, one, ms, k1, ms2 = info["CUT"]; RUN = {r[0]: r for r in info["RUN"]}; U = info["U"]; tp = m["tp"]; td = tp - info["FUZE"]; s = min(m["s"], info["S_BURST"]); v = m["v"]; Z = info["Z"]; sinD = -U[2]
    A0, A1 = info["ROOM_A"]; B0, B1 = info["ROOM_B"]; V0, V1 = info["VENTS"]; fi = lambda t_: pre + (t_ / ms if t_ <= k1 * ms else k1 + (t_ - k1 * ms) / ms2)
    out = 1 - ease((td - 0.03) / 0.06)                                # the drawing clears as the view pulls back
    lab = lambda x, z, big, small, a, col=INK: (text(d, PX(x, z), big, F_SEMI(30), col, a, tracking=2), text(d, (PX(x, z)[0], PX(x, z)[1] + 36), small, F_MED(27), INK, a)) if a > 0 else None
    if hold is not None:
        lower(d, "THE SAME STRIKE, WITH THE GROUND CUT OPEN", "Chambers of reinforced concrete under a concrete slab and 15 m of soil  ·  the bunker is invented, on the pattern of those of 1991", ease(hold * 6) * (1 - ease((hold - 0.88) / 0.12)))
        a = ease((hold - 0.15) * 5) * (1 - ease((hold - 0.88) / 0.12))
        lab(A1 - 1.0, Z["ceil"] - 0.45, "TARGET CHAMBER", "", a, AMBER); lab(B1 - 3.2, Z["ceil"] - 0.45, "SECOND CHAMBER", "", a)
        lab((V0 + V1) / 2 + 4.2, -4.0, "AIR SHAFTS", "", a); lab(info["S0"] - 3.0, -6.2, "STAIR TO THE ENTRANCE", "", a)
    a0 = (ease((i - 2) / 8.0) if hold is None else ease((hold - 0.15) * 5)) * out
    lab(A1 + 2.9, -7.6, "SOIL: 15 m", "sand and silt", a0)
    if hold is None:
        a = ease((i - fi(RUN["slab"][6]) + 14) / 8.0) * out; lab(A1 + 2.9, Z["slab"] + 1.25, "CONCRETE SLAB: 0.6 m", "", a)
        a = ease((i - fi(RUN["roof"][6]) + 12) / 8.0) * out; lab(A1 - 0.4, Z["roof"] + 0.98, "ROOF: 0.5 m", "", a)
        # ---- the depth scale
        if tp >= -0.002:
            a = ease((i - pre + 4) / 6.0) * out; depth = max(s, 0.0) * sinD; xr = -8.2; c = (*AMBER, int(235 * a)); p0 = PX(0, 0); p1 = PX(xr - 0.6, 0)
            dashed(d, [(p0[0] + (p1[0] - p0[0]) * q / 40.0, p0[1]) for q in range(41)], c, 3)
            top = PX(xr, 0); bot = PX(xr, -depth); d.line([top, bot], fill=c, width=4)
            for k in range(0, int(depth) + 1, 5):
                q = PX(xr, -k); d.line([(q[0] - 10, q[1]), (q[0] + 10, q[1])], fill=c, width=3)
            nose = PX(U[0] * s, U[2] * s)
            if depth > 0.5:
                dashed(d, [(nose[0] + (bot[0] - nose[0]) * q / 40.0, bot[1]) for q in range(41)], c, 2); d.line([(bot[0] - 14, bot[1]), (bot[0] + 14, bot[1])], fill=c, width=4)
            text(d, (bot[0] + 26, bot[1] - 84), "%.1f m" % depth, F_TITLE(66), AMBER, a); text(d, (bot[0] + 26, bot[1] + 12), "BELOW THE SURFACE", F_SEMI(24), INK, a, tracking=2)
        # ---- captions, speed and time
        io = lambda t0, t1: ease((i - fi(t0)) / 6.0) * (1 - ease((i - fi(t1) + 5) / 5.0)); t_slab = RUN["slab"][6]; t_room = RUN["room"][6]
        if tp < 0:
            lower(d, "IT ARRIVES AT %d m/s" % round(info["V_HIT"]), "{:,} km/h, faster than sound  ·  two tonnes of steel round 286 kg of explosive".format(KMH(info["V_HIT"])), ease((i - 1) / 5.0) * (1 - ease((i - pre + 4) / 4.0)))
        elif tp < t_slab:
            lower(d, "THROUGH 15 m OF SOIL", "Guidance unit and tail are torn off at the surface  ·  the soil slows the warhead from %d to about %d m/s" % (round(info["V_HIT"]), round(RUN["soil"][5], -1)), io(0.0, t_slab))
        elif tp < t_room:
            lower(d, "THROUGH THE SLAB AND THE ROOF", "0.6 m and 0.5 m of reinforced concrete take it down to about %d m/s" % (5 * round(RUN["roof"][5] / 5)), io(t_slab, t_room))
        elif td < 0:
            lower(d, "INTO THE CHAMBER", "The fuze counts 60 thousandths of a second from the impact  ·  it fires here, about %d m down" % round(info["DEPTH"]), ease((i - fi(t_room)) / 5.0) * (1 - ease((i - (pre + pen) + 4) / 4.0)))
        elif td < 0.62:
            lower(d, "286 kg OF EXPLOSIVE IN A CLOSED CHAMBER", "The gas takes every way out: along the corridors, up the stair, up the air shafts, back up the bomb's own hole", ease((td - 0.004) / 0.03) * (1 - ease((td - 0.57) / 0.05)))
        else:
            lower(d, "THE CHAMBER IS GONE; THE SURFACE HARDLY MOVES", "Roof and slab come down into it  ·  17 m above there is a hole in the ground, and smoke", ease((td - 0.62) / 0.08) * (1 - ease((i - (n - 9)) / 8.0)))
        if 0 <= tp and td < 0:
            readout(d, "SPEED", "%d m/s" % round(v), ease((i - pre) / 4.0), AMBER, "T + %.1f ms" % (tp * 1000))
        elif td >= 0:
            readout(d, "AFTER THE IMPACT", "{:,} ms".format(int(round(tp * 1000))), 1.0, INK, "THE CHARGE HAS FIRED")
        slow = ("1 SECOND OF FILM = 12 THOUSANDTHS OF A SECOND" if i <= pre + k1 else "1 SECOND OF FILM = 5 THOUSANDTHS OF A SECOND") if td < 0 else ("SLOWED 10 TIMES" if i < pre + pen + one else "SLOWED 3 TIMES")
        text(d, (W - 64, 60), slow, F_SEMI(26), DIM, 1.0, anchor="ra", tracking=3)
        text(d, (W - 64, 94), "DEPTHS AND SPEEDS ARE CALCULATED (YOUNG / SANDIA EQUATIONS)", F_SEMI(22), DIM, 1.0, anchor="ra", tracking=2)

def overlay_for(shot, i, n, m, info, hold=None):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    t = m["t"]; an = m.get("anchors", {}); P = lambda q: (q[0] * W, q[1] * H)
    tag(d, ease(i / 8.0) if shot == "approach" else 1.0)
    io = ease((i - 5) / 9.0) * (1 - ease((i - (n - 7)) / 7.0))
    seen = lambda q: 0.04 < q[0] < 0.96 and 0.08 < q[1] < 0.86
    if shot == "approach":
        lower(d, "B-1B LANCER", "About 9,300 m up at Mach 0.9  ·  the bomb hangs on a pylon under the forward fuselage", io)
        a = ease((i - 30) / 8.0) * (1 - ease((i - (n - 10)) / 7.0))
        if a > 0 and seen(an["bomb"]):
            callout(d, *P(an["bomb"]), "GBU-28", "5.84 m LONG  ·  ABOUT 2.1 t", AMBER, a, dx=-150, dy=230)
        a = ease((i - 12) / 10.0) * (1 - ease((i - (n - 10)) / 7.0))
        text(d, (W - 64, 60), "THE GBU-28 IS AN F-15E AND B-2 WEAPON", F_SEMI(28), INK, a, anchor="ra", tracking=3)
        text(d, (W - 64, 98), "THE B-1B HAS FLOWN ITS SUCCESSOR, THE GBU-72, ON A PYLON LIKE THIS", F_SEMI(24), DIM, a, anchor="ra", tracking=2)
    elif shot == "intro":
        lower(d, "GBU-28/B", "A 3.9 m steel penetrator, a laser guidance unit on its nose, folding wings at its tail  ·  the fuze in the tail fires 0.06 s after impact", io)
        A = lambda k: ease((i - 8 - 9 * k) / 8.0) * (1 - ease((i - (n - 7)) / 6.0)); px = {k: P(q) for k, q in an.items()}
        dim_line(d, (px["tail"][0], px["top"][1] - 62), (px["nose"][0], px["top"][1] - 62), "5.84 m  ·  ABOUT 2,130 kg", A(0))
        for k, (key, big, small, col, ex_, ey_) in enumerate((("seeker", "LASER GUIDANCE UNIT", "PAVEWAY III SEEKER AND CANARDS", AMBER, -470, 125), ("wings", "FOLDING WINGS", "0.72 m SHUT  ·  1.68 m OPEN", AMBER, 60, 80),
                                                           ("cwall", "WALL 58 mm THICK", "FIRST MADE FROM 8-INCH GUN BARRELS", RED, 120, 150), ("cfill", "286 kg OF EXPLOSIVE", "A SEVENTH OF THE WARHEAD'S WEIGHT", RED, -330, 135))):
            a = A(k + 1)
            if a > 0:
                callout(d, *px[key], big, small, col, a, dx=ex_, dy=ey_)
    elif shot == "release":
        a1 = ease((i - 4) / 8.0) * (1 - ease((t + 0.12) / 0.1)); a2 = ease((t - 0.02) / 0.15) * (1 - ease((i - (n - 8)) / 7.0))
        if a1 > 0:
            lower(d, "ON AN OUTSIDE PYLON", "At 5.84 m the bomb is longer than one of the B-1B's 4.6 m weapons bays", a1)
        if a2 > 0:
            lower(d, "RELEASED", "The tail wings spring open, from 0.72 m to 1.68 m across  ·  shown at half speed", a2)
            readout(d, "AFTER RELEASE", "%.2f s" % max(t, 0.0), a2)
    elif shot == "fall":
        readout(d, "ABOVE THE TARGET", "{:,} m".format(int(round(m.get("alt", 0), -1))), 1.0, AMBER, "{:,} km/h  ·  {:d}° DOWN".format(KMH(m.get("v", 0)), round(m.get("dive", 0))))
        lower(d, "FASTER THAN SOUND", "Released about %d km away, it falls for %d s and arrives at Mach %.1f, steered nearly straight down" % (round(info["THROW"] / 1000.0), round(info["TOF"]), info["MACH_HIT"]), io)
        a = ease((i - 30) / 10.0) * (1 - ease((i - (n - 20)) / 10.0))
        if a > 0 and seen(an["target"]):
            callout(d, *P(an["target"]), "AIM POINT", "OVER A CHAMBER 17 m DOWN", RED, a, dx=160, dy=-170)
        if a > 0 and seen(an["hut"]) and i > 44:
            callout(d, *P(an["hut"]), "ENTRANCE", "", AMBER, a * ease((i - 44) / 8.0), dx=-330, dy=120)
    elif shot == "strike":
        tp = t; td = tp - info["FUZE"]
        readout(d, "SLOW MOTION", "T + {:,} ms".format(max(0, int(round(tp * 1000)))), ease((i - 2) / 6.0), INK, "2.1 t BOMB  ·  286 kg OF EXPLOSIVE")
        a1 = ease((i - 3) / 8.0) * (1 - ease((td - 0.30) / 0.12)); a2 = ease((td - 0.45) / 0.15) * (1 - ease((i - (n - 10)) / 8.0))
        if a1 > 0:
            lower(d, "INTO THE GROUND", "Two tonnes at %d m/s: a spurt of soil and a hole  ·  the burst is 20 m down and cannot be seen" % round(info["V_HIT"]), a1)
        if a2 > 0:
            lower(d, "THEN SMOKE FROM THE AIR SHAFTS", "In 1991 that was the only sign from the air: smoke out of the bunker seconds after the hit", a2)
        a = ease((td - 0.12) / 0.1) * (1 - ease((td - 1.0) / 0.3))
        if a > 0 and seen(an["vent"]):
            callout(d, *P(an["vent"]), "AIR SHAFTS", "", AMBER, a, dx=-250, dy=-210)
        a = ease((td - 0.35) / 0.1) * (1 - ease((td - 1.4) / 0.3))
        if a > 0 and seen(an["hut"]):
            callout(d, *P(an["hut"]), "ENTRANCE", "THE DOOR IS BLOWN OUT", AMBER, a, dx=-520, dy=-230)
    elif shot == "cutaway":
        cut_overlay(d, i, n, m, info, hold)
    elif shot == "after":
        a = ease((i - 16) / 10.0) * (1 - ease((i - (n - 14)) / 10.0))
        if a > 0 and seen(an["hit"]):
            callout(d, *P(an["hit"]), "THE HOLE", "HALF A METRE ACROSS", RED, a, dx=110, dy=170)
        lower(d, "TWENTY SECONDS LATER", "On the surface: a hole, and smoke from the shafts and the entrance  ·  the chamber it came from is 17 m below", ease((i - 10) / 12.0) * (1 - ease((i - (n - 10)) / 8.0)))
    return ov

def summary_frame(bg, i, n, info):
    frame = bg.copy(); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov); t = i / FPS; tag(d, 1.0); T = info["TABLE"]; v = round(info["V_HIT"])
    text(d, (120, 140), "HOW DEEP DOES A GBU-28 GO?", F_TITLE(80), INK, ease((t - 0.1) / 0.5))
    a = ease((t - 0.4) / 0.5); d.rectangle([120, 248, 120 + int(1680 * a), 251], fill=(*AMBER, int(255 * a)))
    rows = [("IN THIS FILM", "15 m of soil, a 0.6 m slab, a 0.5 m roof; it bursts in the chamber, %d m down" % round(info["DEPTH"]), RED),
            ("THE SAME BOMB AT %d m/s IN:" % v, "", AMBER),
            ("    SOIL (SAND AND SILT)", "about %.0f m   ·   published: more than 30 m" % T["soil"], DIM), ("    REINFORCED CONCRETE", "about %.1f m   ·   published: more than 6 m" % T["concrete"], DIM),
            ("    WEATHERED ROCK", "about %.1f m" % T["weathered"], DIM), ("    SOUND LIMESTONE", "about %.1f m" % T["limestone"], DIM),
            ("THE BOMB", "GBU-28/B  ·  5.84 m  ·  about 2,130 kg  ·  286 kg of explosive  ·  58 mm steel wall", DIM),
            ("CARRIED BY", "F-15E and B-2, first the F-111F  ·  not the B-1B (it has flown the GBU-72)", DIM),
            ("FIRST USED", "27 February 1991  ·  built in under four weeks", DIM)]
    y = 278
    for r, (lab, val, col) in enumerate(rows):
        a = ease((t - 0.7 - 0.22 * r) / 0.45); dx = int((1 - a) * 24)
        text(d, (120 + dx, y + 6), lab, F_SEMI(30), col, a, tracking=3); text(d, (700 + dx, y - 2), val, F_MED(38), INK, a)
        y += 62
    a = ease((t - 3.4) / 0.6)
    text(d, (120, 872), "For concrete the calculation gives less than the published figure: in the 1991 sled test the warhead went through", F_MED(30), INK, a)
    text(d, (120, 910), "6.7 m of stacked concrete slabs and kept going. For soil the two agree.", F_MED(30), INK, a)
    text(d, (120, 962), "Depths are calculated with the Young / Sandia penetration equations for an invented target. They are estimates, not test results.", F_MED(26), DIM, a)
    text(d, (120, 998), "Release, fall and impact speed are a plausible profile; the bunker follows published descriptions of those of 1991.", F_MED(26), DIM, a)
    frame.alpha_composite(ov)
    return frame

# ------------------------------------------------------------------ sound
def s_bomber(dur, seed=3):
    """Four big turbofans heard from alongside: a deep roar under a rush of air."""
    n = int(dur * SR); t = np.arange(n) / SR
    return gp.lp(gp.noise(n), 140, 3) * 5.0 * _mod(n, 0.8, 0.25, seed) + gp.bp(gp.noise(n), 250, 1800) * 1.0 * _mod(n, 2.0, 0.3, seed + 1) + 0.06 * np.sin(2 * np.pi * 96 * t) + 0.04 * np.sin(2 * np.pi * 144.5 * t)

def s_buffet(dur, seed=5):
    """Air beating in an open bay."""
    n = int(dur * SR); return gp.lp(gp.noise(n), 90, 2) * 6.0 * np.clip(_mod(n, 9.0, 0.8, seed), 0.2, None) + gp.bp(gp.noise(n), 200, 900) * 0.8 * _mod(n, 5.0, 0.5, seed + 1)

def s_muffled(scale, slow=1.0):
    """A charge going off under ground: no crack, a heavy thump and a long rumble."""
    n = int((4.0 + scale) * slow * SR); t = np.arange(n) / SR / slow
    body = gp.lp(gp.noise(n), 70 / slow, 3) * 12.0 * np.minimum(1.0, t / 0.02) * np.exp(-t / (0.7 * scale))
    sub = np.sin(2 * np.pi * np.cumsum(np.linspace(46 / slow, 20 / slow, n)) / SR) * 2.2 * np.exp(-t / (0.6 * scale))
    tail = gp.bp(gp.noise(n), 40, 260) * 1.5 * np.exp(-t / (1.5 * scale)) * _mod(n, 3.0, 0.4, 17)
    return body + sub + tail

def s_hiss(dur, seed=4):
    """Gas and smoke driven out of a shaft: a hard rush that dies away."""
    n = int(dur * SR); t = np.arange(n) / SR
    return (gp.bp(gp.noise(n), 500, 5000) * 1.4 + gp.lp(gp.noise(n), 200, 2) * 2.0) * np.minimum(1.0, t / 0.05) * (0.25 + 0.75 * np.exp(-t / (0.35 * dur))) * _mod(n, 6.0, 0.4, seed)

def build_audio(path, starts, metas, lens, total, info):
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
    la = L["approach"]; ramp = np.minimum(1.0, np.arange(int((la + 0.4) * SR)) / (0.5 * SR)); mx.add(T["approach"], s_bomber(la + 0.4, 3) * ramp, 0.55, -0.15); mx.add(T["approach"], s_bomber(la + 0.4, 8) * ramp, 0.55, 0.15)
    mx.add(T["intro"], gp.s_drone(L["intro"]), 0.4); mx.add(T["intro"] + 0.05, gp.s_thud(0.8), 0.4)
    for k in range(5):
        mx.add(T["intro"] + (8 + 9 * k) / FPS, gp.s_tick(), 0.35, 0.3 - 0.12 * k)
    lr = L["release"]; mx.add(T["release"], s_bomber(lr, 11) * 0.9, 0.5); mx.add(T["release"], s_buffet(lr, 5) * 0.4, 0.4)
    tr = when("release", lambda m: m["t"] >= 0.0)
    if tr:
        mx.add(tr, gp.s_thud(1.6), 1.0); mx.add(tr + 0.02, gp.s_ping(600, 0.3), 0.25, -0.2); mx.add(tr + 0.1, gp.s_whoosh(1.6, 250, 1400, 0.3), 0.4)
    tw = when("release", lambda m: m.get("open", 0) > 0.05)
    if tw:
        mx.add(tw, gp.s_thud(0.7), 0.6, 0.2)
    lf = L["fall"]; w = gp.s_wind(lf) * 0.6 * np.linspace(0.5, 1.0, int(lf * SR)); mx.add(T["fall"], w, 1.0); mx.add(T["fall"], gp.s_whoosh(lf, 300, 3200, 0.97), 0.75)
    th = when("strike", lambda m: m["t"] >= 0.0); tdet = when("strike", lambda m: m["t"] >= info["FUZE"]); tv = when("strike", lambda m: m["t"] >= info["FUZE"] + 0.12); te = when("strike", lambda m: m["t"] >= info["FUZE"] + info["T_DOOR"])
    mx.add(T["strike"], gp.s_wind(L["strike"]) * 0.12, 1.0)
    if th:
        mx.add(T["strike"], gp.s_whoosh(th - T["strike"] + 0.05, 600, 3200, 0.96), 0.7); mx.add(th, gp.s_thud(2.2), 1.0); mx.add(th + 0.02, gp.s_boom(0.35, 1.0), 0.3); mx.add(th + 0.3, gp.s_debris(2.5, 40, 1.5), 0.3)
    if tdet:
        mx.add(tdet, s_muffled(1.5) * 0.7, 0.9)
    if tv:
        mx.add(tv, s_hiss(4.0, 4), 0.55, 0.3); mx.add(tv + 0.15, s_hiss(4.0, 9), 0.45, 0.5)
    if te:
        mx.add(te, gp.s_boom(0.5, 1.0), 0.4, -0.5); mx.add(te, s_hiss(4.0, 13), 0.5, -0.5)
    tc = T["cutaway"]; lc = L["cutaway"]; mx.add(tc, gp.s_drone(lc), 0.35); pre, pen, one, ms, k1, ms2 = info["CUT"]; hold = HOLD.get("cutaway", 0) / FPS; RUN = {r[0]: r for r in info["RUN"]}
    fi = lambda t_: t_ / ms if t_ <= k1 * ms else k1 + (t_ - k1 * ms) / ms2
    for name, g_ in (("soil", 1.6), ("slab", 1.4), ("roof", 1.4)):
        mx.add(tc + hold + (pre + fi(RUN[name][6])) / FPS, gp.s_thud(g_), 0.8, 0.0)
    ng = int((pen / FPS) * SR); grind = gp.lp(gp.noise(ng), 180, 2) * 3.0; t_room = fi(RUN["room"][6]) / FPS
    grind *= np.interp(np.arange(ng) / SR, [0, 0.2, t_room, t_room + 0.25, pen / FPS], [0, 1, 0.6, 0, 0]); mx.add(tc + hold + pre / FPS, grind, 0.6)
    tb = tc + hold + (pre + pen) / FPS; mx.add(tb, s_muffled(1.4, 2.2), 1.0); mx.add(tb, gp.s_boom(0.9, 2.5), 0.5); mx.add(tb + 0.4, s_hiss(5.0, 21) * 0.6, 0.4, -0.3); mx.add(tb + 1.5, gp.s_debris(6.0, 40, 3.0), 0.5, 0.1)
    ta = T["after"]; la_ = L["after"] + L["summary"]; mx.add(ta, gp.s_wind(la_) * 0.16, 1.0, -0.1); mx.add(ta, s_hiss(L["after"] + 1.0, 31) * 0.25, 0.3, 0.2)
    ts_ = T["summary"]; mx.add(ts_, gp.s_drone(L["summary"]), 0.45); mx.add(ts_ + 0.1, gp.s_thud(1.2), 0.4)
    for r in range(9):
        mx.add(ts_ + 0.7 + 0.22 * r, gp.s_tick(), 0.3, 0.3)
    x = np.tanh(mx.b[: int(total * SR)] * 1.1)
    fo = int(0.8 * SR); x[-fo:] *= np.linspace(1, 0, fo)[:, None]
    x = x / (np.abs(x).max() + 1e-9) * 0.89
    with wave.open(path, "wb") as w_:
        w_.setnchannels(2); w_.setsampwidth(2); w_.setframerate(SR); w_.writeframes((x * 32767).astype("<i2").tobytes())

FADES = {"card": (8, 6), "approach": (8, 5), "intro": (6, 6), "release": (6, 5), "fall": (5, 0), "strike": (0, 8), "cutaway": (10, 8), "after": (6, 0), "summary": (0, 16)}

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
        starts[shot] = g; fi, fo = FADES[shot]; hold = HOLD.get(shot, 0)
        if shot == "summary":
            n = N_SUMMARY; metas[shot] = {}; bg = Image.blend(last.convert("RGB").filter(ImageFilter.GaussianBlur(14)), Image.new("RGB", (W, H), PANEL), 0.84).convert("RGBA"); seq = list(range(n))
        else:
            d1, f1, m1 = _load(root, shot); n = len(f1); metas[shot] = m1; seq = [0] * hold + list(range(n))
        lens[shot] = len(seq)
        for j, k in enumerate(seq):
            if shot == "card":
                frame = card_frame(Image.open(os.path.join(d1, f1[k])), k, n).convert("RGBA")
            elif shot == "summary":
                a = ease(k / 14.0); frame = Image.blend(last, summary_frame(bg, k, n, info), a) if a < 1 else summary_frame(bg, k, n, info)
            else:
                frame = Image.open(os.path.join(d1, f1[k])).convert("RGB").resize((W, H), Image.LANCZOS).convert("RGBA")
                if shot == "after" and k == n - 1:
                    last = frame.copy()
                shadowed(frame, overlay_for(shot, k, n, m1[str(k)], info, hold=(j / hold) if j < hold else None))
            fade = min(1.0, (j + 1) / fi if fi else 1.0, (len(seq) - j) / fo if fo else 1.0)
            if fade < 1.0:
                frame = Image.blend(Image.new("RGBA", frame.size, (0, 0, 0, 255)), frame, fade)
            frame.convert("RGB").save(os.path.join(stage, "m%05d.png" % g), compress_level=1); g += 1
        print("staged", shot, len(seq)); sys.stdout.flush()
    total = g / FPS
    wav = os.path.join(root, "mix.wav"); build_audio(wav, starts, metas, lens, total, info)
    vf = "unsharp=5:5:0.55:5:5:0.0,vignette=PI/7,noise=alls=4:allf=t+u,format=yuv420p"
    cmd = ["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", os.path.join(stage, "m%05d.png"), "-i", wav,
           "-vf", vf, "-c:v", "libx264", "-preset", "medium" if draft else "slow", "-crf", "21" if draft else "18",
           "-maxrate", "14M", "-bufsize", "28M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest", out]
    subprocess.check_call(cmd)
    print("wrote", out, "%.2fs" % total, starts)

if __name__ == "__main__":
    main()
