"""Finishing for the B-1B / BLU-109 segment: upscale to 1080p, title card, captions, the depth scale and labels on the
section, a closing table, synthesized sound, encode.

  python3 ppost.py <frames_root> <out.mp4> [--draft]
"""
import os, sys, json, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "blackhawk-mk77"))
import post as gp
from post import W, H, FPS, SR, AMBER, RED, INK, DIM, PANEL, F_TITLE, F_SEMI, F_MED, ease, text, shadowed, lower, callout
from npost import readout, dashed, _mod, s_roar, s_crackle

ORDER = ["card", "approach", "intro", "bay", "fall", "strike", "cutaway", "after", "summary"]
N_SUMMARY = 216
HOLD = {"cutaway": 40}                                               # the first frame of the section is held while its caption is read
SPECS = [("BOMB", "GBU-31(V)3/B  ·  BLU-109 warhead"), ("SIZE", "3.77 m long  ·  368 mm across"), ("WEIGHT", "about 960 kg (2,120 lb)"), ("EXPLOSIVE", "243 kg of tritonal"),
         ("CASE", "forged steel, at least 27 mm thick"), ("GUIDANCE", "GPS and inertial (JDAM tail kit)"), ("DROPPED BY", "B-1B Lancer  ·  up to 24 on board")]

def tag(d, a=1.0):
    text(d, (64, 54), "EXPLOSION COMPARISON", F_SEMI(30), INK, a, tracking=4)
    d.rectangle([64, 96, 64 + 54, 100], fill=(*AMBER, int(255 * a)))
    text(d, (130, 84), "09  ·  BLU-109 PENETRATOR BOMB  ·  B-1B LANCER", F_MED(26), DIM, a, tracking=2)

def card_frame(img, i, n):
    base = Image.new("RGBA", (W, H), (*PANEL, 255))
    base.paste(img.convert("RGB").resize((W // 2, H), Image.LANCZOS), (0, 0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    grad = Image.linear_gradient("L").rotate(90, expand=True).resize((90, H))
    seam = Image.new("RGBA", (90, H), (*PANEL, 255)); seam.putalpha(grad.point(lambda v: 255 - v))
    base.alpha_composite(seam.transpose(Image.FLIP_LEFT_RIGHT), (W // 2 - 90, 0))
    t = i / FPS; x0 = W // 2 + 96
    text(d, (x0, 150), "EXPLOSION COMPARISON  ·  09", F_SEMI(30), DIM, ease((t - 0.10) / 0.5), tracking=5)
    a = ease((t - 0.20) / 0.5); text(d, (x0 + int((1 - a) * 40), 200), "BLU-109", F_TITLE(170), INK, a)
    a = ease((t - 0.35) / 0.5); text(d, (x0 + int((1 - a) * 40), 420), "A 2,000 LB PENETRATOR INTO A MOUNTAIN BUNKER", F_TITLE(40), AMBER, a, tracking=1)
    a = ease((t - 0.45) / 0.5); d.rectangle([x0, 500, x0 + int(820 * a), 503], fill=(*AMBER, int(255 * a)))
    y = 548
    for k, (lab, val) in enumerate(SPECS):
        a = ease((t - 0.65 - 0.12 * k) / 0.45); dx = int((1 - a) * 28); hot = lab == "EXPLOSIVE"
        text(d, (x0 + dx, y), lab, F_SEMI(31), RED if hot else DIM, a, tracking=3)
        text(d, (x0 + 230 + dx, y - 4), val, F_MED(36), INK, a)
        y += 62
    text(d, (x0, 980), "The bunker, the mountain and the strike in this film are invented.", F_MED(28), DIM, ease((t - 1.8) / 0.6))
    text(d, (x0, 1016), "How deep the bomb goes is calculated, not measured. Nobody is modelled.", F_MED(28), DIM, ease((t - 1.8) / 0.6))
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
    pre, pen, one, ms = info["CUT"]; TP = info["TP"]; U = info["U"]; tp = m["tp"]; td = tp - info["FUZE"]; s = m["s"]; v = m["v"]; Z = info["Z"]; sinD = -U[2]
    fi = lambda t_: pre + t_ / ms                                     # frame at which tp = t_
    out = 1 - ease((td - 0.10) / 0.10)                                # the drawing clears once the room has gone
    if hold is not None:
        lower(d, "THE SAME STRIKE, WITH THE GROUND CUT OPEN", "A section along the bomb's path  ·  the bunker: a concrete room under earth and rock, a tunnel to the slope", ease(hold * 6) * (1 - ease((hold - 0.85) / 0.15)))
    # ---- names of the layers
    a = ease((i - 2) / 8.0) * out if hold is None else ease(hold * 4)
    p = PX(8.6, -0.55); text(d, p, "COVER: EARTH AND BROKEN ROCK", F_SEMI(30), INK, a, tracking=2); text(d, (p[0], p[1] + 38), "3.6 m along the bomb's path", F_MED(28), INK, a)
    for k, (zm, big, small) in enumerate((((Z[0] + Z[1]) / 2, "0.9 m", "REINFORCED CONCRETE ROOF"), ((Z[1] + Z[2]) / 2, "3 m", "THE ROOM"), (Z[2] - 0.3, "0.6 m", "CONCRETE FLOOR, ROCK UNDER IT"))):
        a = (ease((i - fi(TP[k + 1]) + 6) / 8.0) if hold is None else 0.0) * out
        if a > 0:
            p0 = PX(9.25, zm); p1 = PX(9.75, zm); d.line([p0, p1], fill=(*INK, int(230 * a)), width=3); note(d, PX(13.45, zm), big, small, a, dy=-44)
    # ---- the depth scale
    if hold is None and tp >= -0.002:
        a = ease((i - pre + 4) / 6.0) * out; depth = max(s, 0.0) * sinD; xr = -11.0; c = (*AMBER, int(235 * a)); p0 = PX(0, 0); p1 = PX(xr - 0.5, 0)
        dashed(d, [(p0[0] + (p1[0] - p0[0]) * q / 60.0, p0[1]) for q in range(61)], c, 3)
        top = PX(xr, 0); bot = PX(xr, -depth); d.line([top, bot], fill=c, width=4)
        for k in range(0, int(depth) + 1):
            q = PX(xr, -k); d.line([(q[0] - 9, q[1]), (q[0] + 9, q[1])], fill=c, width=3)
        nose = PX(U[0] * s, U[2] * s)
        if depth > 0.3:
            dashed(d, [(nose[0] + (bot[0] - nose[0]) * q / 60.0, bot[1]) for q in range(61)], c, 2); d.line([(bot[0] - 14, bot[1]), (bot[0] + 14, bot[1])], fill=c, width=4)
        text(d, (bot[0] - 24, bot[1] - 84), "%.1f m" % depth, F_TITLE(66), AMBER, a, anchor="ra"); text(d, (bot[0] - 24, bot[1] + 12), "BELOW WHERE IT WENT IN", F_SEMI(24), INK, a, anchor="ra", tracking=2)
    # ---- captions, speed and time
    if hold is None:
        io = lambda t0, t1: ease((i - fi(t0)) / 6.0) * (1 - ease((i - fi(t1) + 5) / 5.0))
        if tp < 0:
            lower(d, "IT ARRIVES AT %d m/s" % round(info["V_HIT"]), "%d km/h, %d° down  ·  about 874 kg of steel and explosive behind a solid steel nose" % (round(info["V_HIT"] * 3.6, -1), round(info["DIVE"])), ease((i - 1) / 5.0) * (1 - ease((i - pre + 4) / 4.0)))
        elif tp < TP[1]:
            lower(d, "THROUGH THE COVER", "The tail kit is torn off at the surface  ·  earth and broken rock slow the warhead from %d to about %d m/s" % (round(info["VS"][0]), round(info["VS"][1], -1)), io(0.0, TP[1]))
        elif tp < TP[2]:
            lower(d, "THROUGH THE ROOF", "0.9 m of reinforced concrete takes it down to about %d m/s" % round(info["VS"][2], -1), io(TP[1], TP[2]))
        elif tp < TP[3]:
            lower(d, "ACROSS THE ROOM", "Still in one piece  ·  the fuze in its tail has not fired yet", io(TP[2], TP[3]))
        elif tp < TP[5] + 0.002:
            lower(d, "INTO THE FLOOR", "It stops with its nose about %.1f m into the floor, %.1f m below where it went in" % (info["S"][5] - info["S"][3], info["DEPTH"]), io(TP[3], TP[5] + 0.002))
        elif td < 0:
            lower(d, "THE FUZE WAITS", "Sixty thousandths of a second after the impact it fires the charge", ease((i - fi(TP[5] + 0.002)) / 5.0) * (1 - ease((i - (pre + pen) + 4) / 4.0)))
        elif td < 0.55:
            lower(d, "243 kg OF EXPLOSIVE IN A CLOSED ROOM", "The gas goes down the tunnel and back up the hole, and it lifts the roof and the earth on it", ease((td - 0.004) / 0.03) * (1 - ease((td - 0.50) / 0.05)))
        else:
            lower(d, "THE COVER FALLS IN", "Roof and earth drop into the room  ·  a hollow is left in the slope above", ease((td - 0.55) / 0.08) * (1 - ease((i - (n - 9)) / 8.0)))
        if 0 <= tp and td < 0:
            readout(d, "SPEED", "%d m/s" % round(v), ease((i - pre) / 4.0), AMBER, "T + %.1f ms" % (tp * 1000))
        elif td >= 0:
            readout(d, "AFTER THE IMPACT", "%d ms" % round(tp * 1000), 1.0, INK, "THE CHARGE HAS FIRED")
        slow = "1 SECOND OF FILM = 12 THOUSANDTHS OF A SECOND" if td < 0 else ("SLOWED 10 TIMES" if i < pre + pen + one else "SLOWED 3 TIMES")
        text(d, (W - 64, 60), slow, F_SEMI(26), DIM, 1.0, anchor="ra", tracking=3)
        text(d, (W - 64, 94), "DEPTHS AND SPEEDS ARE CALCULATED (YOUNG / SANDIA EQUATIONS)", F_SEMI(22), DIM, 1.0, anchor="ra", tracking=2)

def overlay_for(shot, i, n, m, info, hold=None):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    t = m["t"]; an = m.get("anchors", {}); P = lambda q: (q[0] * W, q[1] * H)
    tag(d, ease(i / 8.0) if shot == "approach" else 1.0)
    io = ease((i - 5) / 9.0) * (1 - ease((i - (n - 7)) / 7.0))
    seen = lambda q: 0.04 < q[0] < 0.96 and 0.08 < q[1] < 0.86
    if shot == "approach":
        lower(d, "B-1B LANCER", "About 8,200 m up at Mach 0.85  ·  wings swept back to 67.5° for speed  ·  crew of four", io)
        a = ease((i - 24) / 8.0) * (1 - ease((i - (n - 10)) / 7.0))
        if a > 0 and seen(an["wing"]):
            callout(d, *P(an["wing"]), "SWING WING", "24.1 m ACROSS SWEPT, 41.8 m FORWARD", AMBER, a, dx=-120, dy=-190)
        a = ease((i - 40) / 8.0) * (1 - ease((i - (n - 10)) / 7.0))
        if a > 0 and seen(an["nacelle"]):
            callout(d, *P(an["nacelle"]), "FOUR ENGINES", "TWO IN A NACELLE UNDER EACH WING ROOT", AMBER, a, dx=90, dy=170)
    elif shot == "intro":
        lower(d, "WHAT IT DROPS: GBU-31(V)3/B", "A BLU-109 penetrator with a JDAM guidance tail  ·  961 kg  ·  the warhead alone: 2.40 m long, 368 mm across, 874 kg", io)
        A = lambda k: ease((i - 8 - 8 * k) / 8.0) * (1 - ease((i - (n - 7)) / 6.0)); px = {k: P(q) for k, q in an.items()}
        dim_line(d, (px["tail"][0], px["top"][1] - 70), (px["nose"][0], px["top"][1] - 70), "3.77 m WITH THE TAIL KIT", A(0))
        for k, (key, big, small, col, ex, ey) in enumerate((("kit", "JDAM TAIL KIT", "GPS AND INERTIAL GUIDANCE  ·  THREE FINS MOVE", AMBER, -40, 150), ("strake", "STRAKES", "STRAPPED ON, FOR LIFT", AMBER, 160, 70),
                                                         ("cnose", "SOLID STEEL NOSE", "FORGED CASE AT LEAST 27 mm THICK", RED, -233, -123), ("cfill", "243 kg OF EXPLOSIVE", "LESS THAN A THIRD OF THE BOMB'S WEIGHT", RED, -557, -123),
                                                         ("cfuze", "FUZE IN THE TAIL", "FIRES 0.06 s AFTER IMPACT", RED, -300, 95))):
            a = A(k + 1)
            if a > 0:
                callout(d, *px[key], big, small, col, a, dx=ex, dy=ey)
    elif shot == "bay":
        a1 = ease((i - 4) / 8.0) * (1 - ease((t + 0.25) / 0.2)); a2 = ease((t + 0.05) / 0.15) * (1 - ease((i - (n - 8)) / 7.0))
        if a1 > 0:
            lower(d, "THE BAY OPENS", "Three bays  ·  each takes a rotary launcher with eight 2,000 lb bombs", a1)
            if m.get("doors", 0) > 0.9 and seen(an["bay"]):
                callout(d, *P(an["bay"]), "ROTARY LAUNCHER", "EIGHT GBU-31 ON ONE DRUM", AMBER, a1 * ease((t + 1.25) / 0.3), dx=-560, dy=120)
        if a2 > 0:
            lower(d, "ONE BOMB AWAY", "It is pushed off its rack; the launcher turns the next one to the bottom  ·  shown at half speed", a2)
            readout(d, "AFTER RELEASE", "%.2f s" % max(t, 0.0), a2)
    elif shot == "fall":
        readout(d, "ABOVE THE TARGET", "{:,} m".format(int(round(m.get("alt", 0), -1))), 1.0, AMBER, "%d km/h  ·  %d° DOWN" % (round(m.get("v", 0) * 3.6, -1), round(m.get("dive", 0))))
        lower(d, "STEERED ALL THE WAY DOWN", "Released about %.0f km away, it falls for %d s  ·  GPS brings it within about 5 m, on a steep path" % (info["THROW"] / 1000.0, round(info["TOF"])), io)
        a = ease((i - 26) / 10.0) * (1 - ease((i - (n - 22)) / 10.0))
        if a > 0 and seen(an["target"]):
            callout(d, *P(an["target"]), "TARGET", "A BUNKER UNDER THE SLOPE", RED, a, dx=150, dy=-170)
    elif shot == "strike":
        tp = t; td = tp - info["FUZE"]
        readout(d, "SLOW MOTION", "T + %03d ms" % max(0, round(tp * 1000)), ease((i - 2) / 6.0), INK, "874 kg BOMB  ·  243 kg OF EXPLOSIVE")
        a1 = ease((i - 3) / 8.0) * (1 - ease((td - 0.25) / 0.15)); a2 = ease((td - 0.45) / 0.15) * (1 - ease((i - (n - 10)) / 8.0))
        if a1 > 0:
            lower(d, "INTO THE MOUNTAINSIDE", "No flash: the bomb goes in whole and its fuze waits 60 thousandths of a second", a1)
        if a2 > 0:
            lower(d, "THE BURST IS UNDER GROUND", "Dust is forced up through the cover  ·  flame and smoke come out of the tunnel", a2)
        a = ease((td - 0.05) / 0.1) * (1 - ease((td - 1.1) / 0.3))
        if a > 0 and seen(an["mouth"]):
            callout(d, *P(an["mouth"]), "TUNNEL MOUTH", "THE DOORS ARE BLOWN OUT", AMBER, a, dx=170, dy=-150)
    elif shot == "cutaway":
        cut_overlay(d, i, n, m, info, hold)
    elif shot == "after":
        a = ease((i - 16) / 10.0) * (1 - ease((i - (n - 14)) / 10.0))
        if a > 0 and seen(an["hollow"]):
            callout(d, *P(an["hollow"]), "HOLLOW", "THE COVER FELL INTO THE ROOM", RED, a, dx=-470, dy=-150)
        lower(d, "TWENTY SECONDS LATER", "From outside there is little to see: a hollow, a hole, smoke  ·  the room under it is gone", ease((i - 10) / 12.0) * (1 - ease((i - (n - 10)) / 8.0)))
    return ov

def summary_frame(bg, i, n, info):
    frame = bg.copy(); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov); t = i / FPS; tag(d, 1.0); T = info["TABLE"]; v = round(info["V_HIT"])
    text(d, (120, 150), "HOW DEEP DOES A BLU-109 GO?", F_TITLE(80), INK, ease((t - 0.1) / 0.5))
    a = ease((t - 0.4) / 0.5); d.rectangle([120, 258, 120 + int(1680 * a), 261], fill=(*AMBER, int(255 * a)))
    rows = [("IN THIS FILM", "3.6 m of earth, a 0.9 m concrete roof, the room, 0.7 m of floor", RED),
            ("THE SAME BOMB AT %d m/s IN:" % v, "", AMBER),
            ("    COMPACTED EARTH AND ROCK", "about %.0f m" % T["fill"], DIM), ("    REINFORCED CONCRETE", "about %.1f m   ·   published: 1.2 to 2.4 m" % T["concrete"], DIM),
            ("    WEATHERED ROCK", "about %.1f m" % T["weathered"], DIM), ("    SOUND LIMESTONE", "about %.1f m" % T["limestone"], DIM),
            ("THE BOMB", "BLU-109/B  ·  874 kg  ·  243 kg of explosive  ·  27 mm steel case", DIM), ("AS DROPPED", "GBU-31(V)3/B  ·  3.77 m  ·  961 kg  ·  GPS and inertial guidance", DIM),
            ("FUZE", "in the tail  ·  fires 0.060 s after impact", DIM)]
    y = 290
    for r, (lab, val, col) in enumerate(rows):
        a = ease((t - 0.7 - 0.22 * r) / 0.45); dx = int((1 - a) * 24)
        text(d, (120 + dx, y + 6), lab, F_SEMI(30), col, a, tracking=3); text(d, (700 + dx, y - 2), val, F_MED(40), INK, a)
        y += 64
    a = ease((t - 3.4) / 0.6)
    text(d, (120, 900), "A few metres of concrete or a little rock stop it: a bunker under a hillside's earth can be reached, one deep in a", F_MED(30), INK, a)
    text(d, (120, 938), "mountain's rock cannot. Much heavier penetrators were built for those (the 2.1 t GBU-28, the 13.6 t GBU-57).", F_MED(30), INK, a)
    text(d, (120, 990), "Depths are calculated with the Young / Sandia penetration equations for an invented target. They are estimates, not test results.", F_MED(26), DIM, a)
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

def build_audio_synth(path, starts, metas, lens, total, info):
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
    la = L["approach"]; e = s_bomber(la + 0.4, 3); e *= np.minimum(1.0, np.arange(len(e)) / (0.5 * SR)); mx.add(T["approach"], e, 0.55, -0.15); mx.add(T["approach"], s_bomber(la + 0.4, 8) * np.minimum(1.0, np.arange(int((la + 0.4) * SR)) / (0.5 * SR)), 0.55, 0.15)
    mx.add(T["intro"], gp.s_drone(L["intro"]), 0.4); mx.add(T["intro"] + 0.05, gp.s_thud(0.8), 0.4)
    for k in range(6):
        mx.add(T["intro"] + (8 + 8 * k) / FPS, gp.s_tick(), 0.35, 0.3 - 0.1 * k)
    lb = L["bay"]; mx.add(T["bay"], s_bomber(lb, 11) * 0.8, 0.45); td_ = when("bay", lambda m: m.get("doors", 0) > 0.02)
    if td_:
        b = s_buffet(T["bay"] + lb - td_, 5); b *= np.minimum(1.0, np.arange(len(b)) / (1.2 * SR)); mx.add(td_, b, 0.5); mx.add(td_, gp.s_thud(0.7), 0.5, 0.2)
    tr = when("bay", lambda m: m["t"] >= 0.0)
    if tr:
        mx.add(tr, gp.s_thud(1.3), 0.9); mx.add(tr + 0.02, gp.s_ping(700, 0.3), 0.25, -0.2); mx.add(tr + 0.1, gp.s_whoosh(1.2, 300, 1500, 0.3), 0.35)
    tt = when("bay", lambda m: m["t"] >= 0.85)
    if tt:
        mx.add(tt, gp.s_roll(1.3) * 0.5, 0.4); mx.add(tt + 1.3, gp.s_thud(0.6), 0.5)
    lf = L["fall"]; w = gp.s_wind(lf) * 0.55 * np.linspace(0.5, 1.0, int(lf * SR)); mx.add(T["fall"], w, 1.0); mx.add(T["fall"], gp.s_whoosh(lf, 300, 2800, 0.97), 0.7)
    th = when("strike", lambda m: m["t"] >= 0.0); tdet = when("strike", lambda m: m["t"] >= info["FUZE"])
    mx.add(T["strike"], gp.s_wind(L["strike"]) * 0.12, 1.0)
    if th:
        mx.add(T["strike"], gp.s_whoosh(th - T["strike"] + 0.05, 600, 3000, 0.96), 0.6); mx.add(th, gp.s_thud(1.6), 0.9)
    if tdet:
        mx.add(tdet, s_muffled(1.2), 1.0); mx.add(tdet + 0.05, gp.s_boom(0.5, 1.0), 0.35, 0.3); mx.add(tdet + 0.5, gp.s_debris(4.0, 70, 2.0), 0.5, -0.1)
    tc = T["cutaway"]; lc = L["cutaway"]; mx.add(tc, gp.s_drone(lc), 0.35); pre, pen, one, ms = info["CUT"]; hold = HOLD.get("cutaway", 0) / FPS
    for k, tk in enumerate(info["TP"][:5]):
        mx.add(tc + hold + (pre + tk / ms) / FPS, gp.s_thud(1.4 if k in (0, 1, 3) else 0.7), 0.7 if k in (0, 1, 3) else 0.4, 0.1 * (k - 2))
    grind = gp.lp(gp.noise(int((pen / FPS) * SR)), 180, 2) * 3.0; ng = len(grind); grind *= np.interp(np.arange(ng) / SR, [0, 0.2, info["TP"][5] / ms / FPS, info["TP"][5] / ms / FPS + 0.3, pen / FPS], [0, 1, 0.5, 0, 0]); mx.add(tc + hold + pre / FPS, grind, 0.6)
    tb = tc + hold + (pre + pen) / FPS; mx.add(tb, s_muffled(1.3, 2.2), 1.0); mx.add(tb, gp.s_boom(0.9, 2.5), 0.45); mx.add(tb + 1.0, gp.s_debris(6.0, 40, 3.0), 0.5, 0.1)
    ta = T["after"]; la_ = L["after"] + L["summary"]; mx.add(ta, gp.s_wind(la_) * 0.16, 1.0, -0.1); mx.add(ta, s_crackle(L["after"] + 1.0, 8.0, 7), 0.2, 0.1); mx.add(ta + 0.6, gp.s_debris(3.0, 14, 2.0), 0.3, -0.2)
    ts_ = T["summary"]; mx.add(ts_, gp.s_drone(L["summary"]), 0.45); mx.add(ts_ + 0.1, gp.s_thud(1.2), 0.4)
    for r in range(9):
        mx.add(ts_ + 0.7 + 0.22 * r, gp.s_tick(), 0.3, 0.3)
    x = np.tanh(mx.b[: int(total * SR)] * 1.1)
    fo = int(0.8 * SR); x[-fo:] *= np.linspace(1, 0, fo)[:, None]
    x = x / (np.abs(x).max() + 1e-9) * 0.89
    with wave.open(path, "wb") as w_:
        w_.setnchannels(2); w_.setsampwidth(2); w_.setframerate(SR); w_.writeframes((x * 32767).astype("<i2").tobytes())

def build_audio_sfx(path, starts, metas, lens, total, info):
    """The soundtrack from recorded effects (see ../b1b-gbu28/gsfx.py) in place of synthesized noise."""
    sys.path.insert(0, os.path.join(HERE, "..", "b1b-gbu28")); import gsfx as S
    mx = gp.Mix(total); T = {k: v / FPS for k, v in starts.items()}; L = {k: v / FPS for k, v in lens.items()}
    def when(shot, pred):
        m = metas[shot]
        for i in sorted(int(k) for k in m):
            if pred(m[str(i)]):
                return T[shot] + i / FPS
        return None
    tick = lambda t, g=0.22: mx.add(t, gp.lp(gp.s_tick(), 3500, 1), g, 0.25)
    S.put(mx, 0.0, S.bed("drone", T["approach"] + 0.4, t0=6.0, fi=0.3, fo=0.5, level=0.07)); S.put(mx, 0.05, S.cut("boom_deep", 0.0, 2.0, speed=1.8, fo=1.0), 0.30)
    for k in range(len(SPECS)):
        tick(0.65 + 0.12 * k)
    for shot, t0, g in (("approach", 2.0, 1.0), ("bay", 9.0, 0.85)):                                # the aircraft's engines
        S.put(mx, T[shot], S.bed("jet", L[shot] + 0.3, t0=t0, fi=0.6, fo=0.35, lp=7000, level=0.085), g); S.put(mx, T[shot], S.bed("quake", L[shot] + 0.3, t0=20.0, fi=0.6, fo=0.35, lp=160, level=0.03), g)
    S.put(mx, T["intro"], S.bed("drone", L["intro"], t0=22.0, fi=0.4, fo=0.4, level=0.065)); S.put(mx, T["intro"] + 0.05, S.cut("boom_deep", 0.0, 1.8, speed=1.8, fo=1.0), 0.22)
    for k in range(6):
        tick(T["intro"] + (8 + 8 * k) / FPS)
    td_ = when("bay", lambda m: m.get("doors", 0) > 0.02); tr = when("bay", lambda m: m["t"] >= 0.0); tt = when("bay", lambda m: m["t"] >= 0.85)
    if td_:                                                                                      # the bay opens: a latch, then air beating in the open bay
        S.put(mx, td_, S.cut("latch", 1.9, 0.9), 0.45, 0.2); S.put(mx, td_, S.bed("wind", T["bay"] + L["bay"] - td_, t0=30.0, speed=0.7, fi=1.2, fo=0.4, lp=900, level=0.05))
    if tr:
        S.put(mx, tr - 0.04, S.cut("latch", 5.55, 1.3), 0.75); S.put(mx, tr + 0.2, S.cut("whoosh", 16.4, 3.6, fi=0.2, fo=0.8), 0.40, -0.2)
    if tt:
        S.put(mx, tt, S.cut("latch", 9.1, 1.2), 0.40, 0.1)
    lf = L["fall"]; w = S.bed("wind", lf, t0=34.0, speed=1.5, fi=0.25, fo=0.03, level=0.11) * np.linspace(0.45, 1.25, int(lf * SR))[:, None]; S.put(mx, T["fall"], w)
    S.put(mx, T["fall"] + lf - 2.2, S.cut("whoosh", 32.6, 2.2, fi=0.6, fo=0.02), 0.55)
    th = when("strike", lambda m: m["t"] >= 0.0); tdet = when("strike", lambda m: m["t"] >= info["FUZE"])
    S.put(mx, T["strike"], S.bed("wind", L["strike"], t0=4.0, fi=0.3, fo=0.5, level=0.035))
    if th:
        S.put(mx, th - 0.95, S.cut("missile", 0.95, 0.95, fi=0.25, fo=0.01), 0.60); S.put(mx, th, S.cut("impact", 10.0, 1.4), 0.90); S.put(mx, th, S.cut("boom_deep", 0.0, 1.3, speed=2.6, fo=0.5), 0.50)
    if tdet:                                                                                     # the burst under the slope, the tunnel mouth, the cover coming down
        S.put(mx, tdet + 0.02, S.cut("boom_muffled", 6.3, 6.0, fo=1.5, drive=2.5), 0.55); S.put(mx, tdet + 0.02, S.cut("boom_muffled", 6.3, 2.6, speed=2.3, fo=1.2), 0.85)
        S.put(mx, tdet + 0.1, S.cut("debris", 0.0, 2.0, fo=0.6), 0.45, -0.4); S.put(mx, tdet + 0.1, S.cut("hiss", 3.1, 4.5, speed=0.6, fi=0.15, fo=2.0, lp=2000), 0.15, -0.4)
        S.put(mx, tdet + 1.4, S.cut("collapse", 2.2, min(4.5, T["cutaway"] - tdet - 1.5), fi=0.2, fo=1.0), 0.50, 0.2)
    tc = T["cutaway"]; lc = L["cutaway"]; pre, pen, one, ms = info["CUT"][:4]; hold = HOLD.get("cutaway", 0) / FPS; TP = info["TP"]; at = lambda fr: tc + hold + fr / FPS
    S.put(mx, tc, S.bed("drone", lc, t0=30.0, fi=0.5, fo=0.8, level=0.05))
    t_in = at(pre); t_stop = at(pre + TP[5] / ms); tb = at(pre + pen)
    g = S.bed("quake", t_stop - t_in + 0.4, t0=40.0, fi=0.08, fo=0.4, lp=4500, hp=420, level=0.060); n_ = len(g); g *= np.interp(np.arange(n_) / SR, [0, 0.3, t_stop - t_in, t_stop - t_in + 0.4], [1.0, 1.0, 0.5, 0.0])[:, None]; S.put(mx, t_in, g)
    S.put(mx, t_in, S.cut("impact", 10.0, 2.4, speed=0.55), 0.85); S.put(mx, t_in, S.cut("boom_deep", 0.0, 1.8, speed=1.9, fo=0.8), 0.45)
    for k in (1, 3):                                                                             # the roof, the floor
        S.put(mx, at(pre + TP[k] / ms), S.cut("debris", 0.0, 2.6, speed=0.5, fo=0.8), 0.60, 0.1); S.put(mx, at(pre + TP[k] / ms), S.cut("boom_deep", 0.0, 1.5, speed=2.2, fo=0.6), 0.34)
    S.put(mx, tb, S.cut("boom_deep", 0.0, 8.0, speed=0.6, fo=2.0, drive=3.0), 0.45); S.put(mx, tb + 0.04, S.cut("boom_muffled", 6.3, 4.0, speed=1.5, fo=2.0), 0.85)
    S.put(mx, tb, S.cut("boom_deep", 0.0, 2.2, speed=2.0, fo=1.0), 0.55); S.put(mx, tb + 0.1, S.cut("debris", 0.0, 3.0, speed=0.6, fo=1.0), 0.32, 0.2)
    j_col = one + (0.55 * 240.0 - one) / 3.0; tcol = tb + j_col / FPS; dur = max(tc + lc - tcol - 0.1, 0.5)
    S.put(mx, tcol, S.cut("collapse", 2.2, dur, speed=0.75, fi=0.15, fo=1.0), 0.60, 0.1)
    ta = T["after"]; la_ = L["after"] + L["summary"]; S.put(mx, ta, S.bed("wind", la_, t0=6.0, fi=0.5, fo=1.0, level=0.045)); S.put(mx, ta + 0.8, S.cut("collapse", 12.5, 3.0, fi=0.3, fo=1.0), 0.18, -0.2)
    ts_ = T["summary"]; S.put(mx, ts_, S.bed("drone", L["summary"], t0=8.0, fi=0.6, fo=1.2, level=0.06)); S.put(mx, ts_ + 0.1, S.cut("boom_deep", 0.0, 2.0, speed=1.8, fo=1.0), 0.28)
    for r in range(9):
        tick(ts_ + 0.7 + 0.22 * r)
    S.finish(mx, total, path)

def build_audio(path, starts, metas, lens, total, info):
    sys.path.insert(0, os.path.join(HERE, "..", "b1b-gbu28")); import gsfx
    if gsfx.available():
        return build_audio_sfx(path, starts, metas, lens, total, info)
    print("NOTE: recorded effects not found in %s - using the synthesized soundtrack" % gsfx.DIR); return build_audio_synth(path, starts, metas, lens, total, info)

FADES = {"card": (8, 6), "approach": (8, 5), "intro": (6, 6), "bay": (6, 5), "fall": (5, 0), "strike": (0, 8), "cutaway": (10, 8), "after": (6, 0), "summary": (0, 16)}

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
