"""Finishing for the B-2 / GBU-57 segment: upscale to 1080p, title card, captions, the depth scale and labels on the
section, a closing table, sound, encode.

  python3 wpost.py <frames_root> <out.mp4> [--draft]

The assembly, the fades and the soundtrack are the BLU-109 segment's (ppost.py: recorded effects from
../b1b-gbu28/sfx, or a synthesized track without them); this file supplies this film's words and drawings.
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "blackhawk-mk77", "b1b-gbu28", "b1b-blu109"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
import ppost as B
from post import W, H, FPS, AMBER, RED, INK, DIM, PANEL, F_TITLE, F_SEMI, F_MED, ease, text, shadowed, lower, callout
from npost import readout, dashed

dim_line = B.dim_line; note = B.note
KMH = lambda v: int(round(v * 3.6, -1))
SPECS = [("BOMB", "GBU-57 Massive Ordnance Penetrator"), ("SIZE", "6.2 m long  ·  0.80 m across"), ("WEIGHT", "30,000 lb class (about 13,600 kg)"), ("EXPLOSIVE", "about 2,400 kg"),
         ("CASE", "high-strength steel alloy"), ("GUIDANCE", "GPS and inertial, lattice tail fins"), ("DROPPED BY", "B-2 Spirit  ·  two on board")]

def tag(d, a=1.0):
    text(d, (64, 54), "EXPLOSION COMPARISON", F_SEMI(30), INK, a, tracking=4)
    d.rectangle([64, 96, 64 + 54, 100], fill=(*AMBER, int(255 * a)))
    text(d, (130, 84), "12  ·  GBU-57 MASSIVE ORDNANCE PENETRATOR  ·  B-2 SPIRIT", F_MED(26), DIM, a, tracking=2)

def card_frame(img, i, n):
    base = Image.new("RGBA", (W, H), (*PANEL, 255))
    base.paste(img.convert("RGB").resize((W // 2, H), Image.LANCZOS), (0, 0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    grad = Image.linear_gradient("L").rotate(90, expand=True).resize((90, H))
    seam = Image.new("RGBA", (90, H), (*PANEL, 255)); seam.putalpha(grad.point(lambda v: 255 - v))
    base.alpha_composite(seam.transpose(Image.FLIP_LEFT_RIGHT), (W // 2 - 90, 0))
    t = i / FPS; x0 = W // 2 + 96
    text(d, (x0, 150), "EXPLOSION COMPARISON  ·  12", F_SEMI(30), DIM, ease((t - 0.10) / 0.5), tracking=5)
    a = ease((t - 0.20) / 0.5); text(d, (x0 + int((1 - a) * 40), 200), "GBU-57", F_TITLE(170), INK, a)
    a = ease((t - 0.35) / 0.5); text(d, (x0 + int((1 - a) * 40), 420), "A 30,000 LB PENETRATOR INTO A MOUNTAIN BUNKER", F_TITLE(39), AMBER, a, tracking=1)
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

def cut_overlay(d, i, n, m, info, hold):
    """The section: a depth scale that follows the nose, the layers named as the bomb reaches them, speed and time."""
    an = m["anchors"]; o, ex, ez = an["o"], an["ex"], an["ez"]
    PX = lambda x, z: ((o[0] + x * (ex[0] - o[0]) + z * (ez[0] - o[0])) * W, (o[1] + x * (ex[1] - o[1]) + z * (ez[1] - o[1])) * H)
    pre, pen, one, ms = info["CUT"]; TP = info["TP"]; U = info["U"]; tp = m["tp"]; fz = info["FUZE"]; td = tp - fz; s = min(m["s"], info["S_BURST"]); v = m["v"]; Z = info["Z"]; sinD = -U[2]; VS = info["VS"]; X1 = info["ROOM_X"][1]
    fi = lambda t_: pre + t_ / ms                                     # frame at which tp = t_
    out = 1 - ease((td - 0.10) / 0.10)                                # the drawing clears once the hall has gone
    cover = -Z[0]
    if hold is not None:
        lower(d, "THE SAME STRIKE, WITH THE GROUND CUT OPEN", "A section along the bomb's path  ·  the bunker: a concrete hall under %d m of earth and rock, a tunnel out to the slope  ·  invented" % round(cover), ease(hold * 6) * (1 - ease((hold - 0.85) / 0.15)))
    # ---- names of the layers
    a = ease((i - 2) / 8.0) * out if hold is None else ease(hold * 4)
    p = PX(X1 + 1.0, Z[0] / 2 + 3.2); text(d, p, "COVER: EARTH AND BROKEN ROCK", F_SEMI(30), INK, a, tracking=2); text(d, (p[0], p[1] + 38), "%d m of it along the bomb's path" % round(info["S"][1]), F_MED(28), INK, a)
    for k, (zm, big, small) in enumerate((((Z[0] + Z[1]) / 2, "2.5 m", "REINFORCED CONCRETE ROOF"), ((Z[1] + Z[2]) / 2, "7 m", "THE HALL"))):
        a = (ease((i - fi(TP[k + 1]) + 6) / 8.0) if hold is None else 0.0) * out
        if a > 0:
            p0 = PX(X1 + 2.2, zm); p1 = PX(X1 + 3.6, zm); d.line([p0, p1], fill=(*INK, int(230 * a)), width=3); note(d, PX(X1 + 17.2, zm), big, small, a, dy=-44)
    # ---- the depth scale
    if hold is None and tp >= -0.002:
        a = ease((i - pre + 4) / 6.0) * out; depth = max(s, 0.0) * sinD; xr = -9.0; c = (*AMBER, int(235 * a)); p0 = PX(0, 0); p1 = PX(xr - 1.5, 0)
        dashed(d, [(p0[0] + (p1[0] - p0[0]) * q / 60.0, p0[1]) for q in range(61)], c, 3)
        top = PX(xr, 0); bot = PX(xr, -depth); d.line([top, bot], fill=c, width=4)
        for k in range(0, int(depth) + 1, 5):
            q = PX(xr, -k); d.line([(q[0] - 10, q[1]), (q[0] + 10, q[1])], fill=c, width=3)
        nose = PX(U[0] * s, U[2] * s)
        if depth > 0.5:
            dashed(d, [(nose[0] + (bot[0] - nose[0]) * q / 60.0, bot[1]) for q in range(61)], c, 2); d.line([(bot[0] - 14, bot[1]), (bot[0] + 14, bot[1])], fill=c, width=4)
        text(d, (bot[0] - 24, bot[1] - 84), "%.1f m" % depth, F_TITLE(66), AMBER, a, anchor="ra"); text(d, (bot[0] - 24, bot[1] + 12), "BELOW WHERE IT WENT IN", F_SEMI(24), INK, a, anchor="ra", tracking=2)
    # ---- captions, speed and time
    if hold is None:
        io = lambda t0, t1: ease((i - fi(t0)) / 6.0) * (1 - ease((i - fi(t1) + 5) / 5.0))
        if tp < 0:
            lower(d, "IT ARRIVES AT %d m/s" % round(info["V_HIT"]), "{:,} km/h, faster than sound, {:d}° down  ·  more than 12 tonnes, most of it steel".format(KMH(info["V_HIT"]), round(info["DIVE"])), ease((i - 1) / 5.0) * (1 - ease((i - pre + 4) / 4.0)))
        elif tp < TP[1]:
            lower(d, "THROUGH %d m OF COVER" % round(cover), "The tail and its lattice fins are torn off at the surface  ·  earth and broken rock slow the body from %d to about %d m/s" % (round(VS[0]), round(VS[1], -1)), io(0.0, TP[1]))
        elif tp < TP[2]:
            lower(d, "THROUGH THE ROOF", "2.5 m of reinforced concrete take it down to about %d m/s" % round(VS[2], -1), io(TP[1], TP[2]))
        elif td < 0:
            lower(d, "INTO THE HALL", "Its fuze has counted the layers and fires in the open space, %d thousandths of a second after the impact" % round(fz * 1000), ease((i - fi(TP[2])) / 5.0) * (1 - ease((i - (pre + pen) + 4) / 4.0)))
        elif td < 0.85:
            lower(d, "2.4 TONNES OF EXPLOSIVE IN A CLOSED HALL", "The gas goes down the tunnel and back up the bomb's hole, and it lifts the roof and the %d m of earth on it" % round(cover), ease((td - 0.004) / 0.03) * (1 - ease((td - 0.80) / 0.05)))
        else:
            lower(d, "THE ROOF COMES DOWN", "Roof and cover drop into the hall  ·  a hollow is left in the slope above", ease((td - 0.85) / 0.08) * (1 - ease((i - (n - 9)) / 8.0)))
        if 0 <= tp and td < 0:
            readout(d, "SPEED", "%d m/s" % round(v), ease((i - pre) / 4.0), AMBER, "T + %.1f ms" % (tp * 1000))
        elif td >= 0:
            readout(d, "AFTER THE IMPACT", "{:,} ms".format(int(round(tp * 1000))), 1.0, INK, "THE CHARGE HAS FIRED")
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
        lower(d, "B-2 SPIRIT", "About 12,200 m (40,000 ft) up at Mach 0.8  ·  a flying wing with no tail  ·  crew of two", io)
        a = ease((i - 24) / 8.0) * (1 - ease((i - (n - 10)) / 7.0))
        if a > 0 and seen(an["wing"]):
            callout(d, *P(an["wing"]), "FLYING WING", "52.4 m ACROSS, 21 m LONG", AMBER, a, dx=-120, dy=-190)
        a = ease((i - 40) / 8.0) * (1 - ease((i - (n - 10)) / 7.0))
        if a > 0 and seen(an["intake"]):
            callout(d, *P(an["intake"]), "FOUR ENGINES", "BURIED IN THE WING", AMBER, a, dx=120, dy=190)
    elif shot == "intro":
        lower(d, "WHAT IT DROPS: GBU-57", "The Massive Ordnance Penetrator  ·  6.2 m long, 0.80 m across, 30,000 lb class  ·  only the B-2 carries it, two at a time", io)
        A = lambda k: ease((i - 8 - 8 * k) / 8.0) * (1 - ease((i - (n - 7)) / 6.0)); px = {k: P(q) for k, q in an.items()}
        dim_line(d, (px["tail"][0], px["top"][1] - 96), (px["nose"][0], px["top"][1] - 96), "6.2 m  ·  ABOUT 13,600 kg", A(0))
        for k, (key, big, small, col, ex, ey) in enumerate((("kit", "LATTICE FINS", "THEY STEER IT", AMBER, -430, -40), ("strake", "SHORT WINGS", "", AMBER, 330, 70),
                                                         ("cnose", "SOLID STEEL NOSE", "CASE OF HIGH-STRENGTH STEEL", RED, 110, 95), ("cfill", "ABOUT 2,400 kg OF EXPLOSIVE", "LESS THAN A FIFTH OF THE BOMB'S WEIGHT", RED, -560, 95),
                                                         ("cfuze", "FUZE IN THE TAIL", "FIRES IN THE OPEN SPACE IT BREAKS INTO", RED, -440, -150))):
            a = A(k + 1)
            if a > 0:
                callout(d, *px[key], big, small, col, a, dx=ex, dy=ey)
        text(d, (W - 64, 60), "THE INSIDE IS A DIAGRAM DRAWN FROM THE PUBLISHED WEIGHTS, NOT A DRAWING OF THE REAL BOMB", F_SEMI(22), DIM, A(3), anchor="ra", tracking=2)
    elif shot == "bay":
        a1 = ease((i - 4) / 8.0) * (1 - ease((t + 0.25) / 0.2)); a2 = ease((t + 0.05) / 0.15) * (1 - ease((i - (n - 8)) / 7.0))
        if a1 > 0:
            lower(d, "THE BAYS OPEN", "Two bays side by side  ·  one GBU-57 fills each of them", a1)
            if m.get("doors", 0) > 0.9 and seen(an["bay"]):
                callout(d, *P(an["bay"]), "GBU-57", "ITS LATTICE FINS FOLDED BACK", AMBER, a1 * ease((t + 1.25) / 0.3), dx=-560, dy=120)
        if a2 > 0:
            lower(d, "ONE BOMB AWAY", "Clear of the bay, its lattice fins swing out and begin to steer  ·  shown at half speed", a2)
            readout(d, "AFTER RELEASE", "%.2f s" % max(t, 0.0), a2)
    elif shot == "fall":
        readout(d, "ABOVE THE TARGET", "{:,} m".format(int(round(m.get("alt", 0), -1))), 1.0, AMBER, "{:,} km/h  ·  {:d}° DOWN".format(KMH(m.get("v", 0)), round(m.get("dive", 0))))
        lower(d, "FASTER THAN SOUND", "Released about %d km away, it falls for %d s and arrives at Mach %.1f  ·  GPS and inertial guidance hold it on a steep path" % (round(info["THROW"] / 1000.0), round(info["TOF"]), info["MACH_HIT"]), io)
        a = ease((i - 26) / 10.0) * (1 - ease((i - (n - 22)) / 10.0))
        if a > 0 and seen(an["target"]):
            callout(d, *P(an["target"]), "TARGET", "A BUNKER UNDER THE SLOPE", RED, a, dx=150, dy=-170)
    elif shot == "strike":
        tp = t; td = tp - info["FUZE"]
        readout(d, "SLOW MOTION", "T + {:,} ms".format(max(0, int(round(tp * 1000)))), ease((i - 2) / 6.0), INK, "13.6 t BOMB  ·  2.4 t OF EXPLOSIVE")
        a1 = ease((i - 3) / 8.0) * (1 - ease((td - 0.25) / 0.15)); a2 = ease((td - 0.45) / 0.15) * (1 - ease((i - (n - 10)) / 8.0))
        if a1 > 0:
            lower(d, "INTO THE MOUNTAINSIDE", "No flash at the surface: the bomb goes in whole and bursts %d m down" % round(info["DEPTH"]), a1)
        if a2 > 0:
            lower(d, "THE BURST IS UNDER GROUND", "Dust is forced up through the cover  ·  flame and smoke come out of the tunnel and the air shafts", a2)
        a = ease((td - 0.12) / 0.1) * (1 - ease((td - 1.3) / 0.3))
        if a > 0 and seen(an["mouth"]):
            callout(d, *P(an["mouth"]), "TUNNEL MOUTH", "THE DOORS ARE BLOWN OUT", AMBER, a, dx=170, dy=-150)
    elif shot == "cutaway":
        cut_overlay(d, i, n, m, info, hold)
    elif shot == "after":
        a = ease((i - 16) / 10.0) * (1 - ease((i - (n - 14)) / 10.0))
        if a > 0 and seen(an["hollow"]):
            callout(d, *P(an["hollow"]), "HOLLOW", "THE COVER FELL INTO THE HALL", RED, a, dx=-470, dy=-150)
        lower(d, "TWENTY SECONDS LATER", "From outside: a hollow in the slope, a hole, smoke  ·  the hall under it is gone", ease((i - 10) / 12.0) * (1 - ease((i - (n - 10)) / 8.0)))
    return ov

def summary_frame(bg, i, n, info):
    frame = bg.copy(); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov); t = i / FPS; tag(d, 1.0); T = info["TABLE"]; v = round(info["V_HIT"]); PB = info["PUBLISHED"]
    text(d, (120, 140), "HOW DEEP DOES A GBU-57 GO?", F_TITLE(80), INK, ease((t - 0.1) / 0.5))
    a = ease((t - 0.4) / 0.5); d.rectangle([120, 248, 120 + int(1680 * a), 251], fill=(*AMBER, int(255 * a)))
    rows = [("IN THIS FILM", "%d m of earth and rock, a 2.5 m concrete roof; it bursts in the hall, %d m down" % (round(-info["Z"][0]), round(info["DEPTH"])), RED),
            ("THE SAME BOMB AT %d m/s IN:" % v, "", AMBER),
            ("    ORDINARY SOIL", "about %.0f m   ·   published: about %.0f m (200 ft)" % (T["earth"], PB["earth"]), DIM),
            ("    REINFORCED CONCRETE", "about %.1f m   ·   published claims: up to %.0f m (60 ft)" % (T["concrete"], PB["concrete"]), DIM),
            ("    VERY STRONG CONCRETE", "about %.1f m   ·   published: %.1f m (8 ft)" % (T["hard"], PB["hard"]), DIM),
            ("    WEATHERED ROCK", "about %.1f m" % T["weathered"], DIM), ("    SOUND LIMESTONE", "about %.1f m" % T["limestone"], DIM),
            ("THE BOMB", "GBU-57  ·  6.2 m  ·  30,000 lb class  ·  about 2,400 kg of explosive", DIM),
            ("FIRST USED", "22 June 2025  ·  14 dropped by seven B-2s, 12 of them on Fordow", DIM)]
    y = 278
    for r, (lab, val, col) in enumerate(rows):
        a = ease((t - 0.7 - 0.22 * r) / 0.45); dx = int((1 - a) * 24)
        text(d, (120 + dx, y + 6), lab, F_SEMI(30), col, a, tracking=3); text(d, (700 + dx, y - 2), val, F_MED(38), INK, a)
        y += 62
    a = ease((t - 3.4) / 0.6)
    text(d, (120, 872), "One bomb does not reach a hall under tens of metres of rock. At Fordow six were dropped down each of two", F_MED(30), INK, a)
    text(d, (120, 910), "ventilation shafts, one after another, each going in where the last had opened the way.", F_MED(30), INK, a)
    text(d, (120, 962), "Depths are calculated with the Young / Sandia penetration equations for an invented target. They are estimates, not test results;", F_MED(26), DIM, a)
    text(d, (120, 998), "the public figures for this bomb disagree with each other and the real ones are not published.", F_MED(26), DIM, a)
    frame.alpha_composite(ov)
    return frame

B.SPECS = SPECS; B.tag = tag; B.card_frame = card_frame; B.cut_overlay = cut_overlay; B.overlay_for = overlay_for; B.summary_frame = summary_frame; B.N_SUMMARY = 240; B.HOLD = {"cutaway": 44}

if __name__ == "__main__":
    B.main()
