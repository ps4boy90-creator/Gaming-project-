"""Finishing for the B-2 / GBU-57 segment: upscale to 1080p, title card, captions, the depth scale and labels on the
section, a closing table, sound, encode.

  python3 wpost.py <frames_root> <out.mp4> [--draft]

The assembly and the fades are the BLU-109 segment's (ppost.py); this file supplies this film's words, drawings and
soundtrack (recorded effects from ../b1b-gbu28/sfx; without them ppost's synthesized track is used).
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "blackhawk-mk77", "b1b-gbu28", "b1b-blu109"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
import ppost as B
from post import W, H, FPS, SR, AMBER, RED, INK, DIM, PANEL, F_TITLE, F_SEMI, F_MED, ease, text, shadowed, lower, callout
from npost import readout, dashed

dim_line = B.dim_line; note = B.note
KMH = lambda v: int(round(v * 3.6, -1))
R = lambda x: int(math.floor(x + 0.5))

def callout_l(d, px, py, big, small, color, a=1.0, dx=-150, dy=-120):
    """callout() with the label on the left of the elbow, so that the leader does not run under the words."""
    ex, ey = px + dx, py + dy; c = (*color, int(255 * a))
    d.line([(px, py), (ex, ey), (ex - 28, ey)], fill=c, width=3); d.ellipse([px - 7, py - 7, px + 7, py + 7], outline=c, width=3)
    text(d, (ex - 40, ey - 46), big, F_TITLE(64), color, a, anchor="ra"); text(d, (ex - 40, ey + 28), small, F_SEMI(32), INK, a, anchor="ra", tracking=3)
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
    text(d, (x0, 980), "The bunker, the mountain and the strike are invented. Nobody is modelled.", F_MED(28), DIM, ease((t - 1.8) / 0.6))
    text(d, (x0, 1016), "The depth, 61 m (200 ft), is the U.S. Air Force's figure for this bomb.", F_MED(28), DIM, ease((t - 1.8) / 0.6))
    base.alpha_composite(ov)
    return base.convert("RGB")

def vdim(d, p0, p1, big, small, a, color=AMBER, side=1):
    """An upright dimension line with end ticks and its label beside the middle."""
    if a <= 0:
        return
    c = (*color, int(235 * a)); d.line([p0, p1], fill=c, width=4)
    for p in (p0, p1):
        d.line([(p[0] - 14, p[1]), (p[0] + 14, p[1])], fill=c, width=4)
    ym = (p0[1] + p1[1]) / 2; anc = "la" if side > 0 else "ra"
    text(d, (p0[0] + side * 26, ym - 62), big, F_TITLE(76), color, a, anchor=anc); text(d, (p0[0] + side * 26, ym + 22), small, F_SEMI(30), INK, a, anchor=anc, tracking=2)

def cut_overlay(d, i, n, m, info, hold):
    """The section: the 61 m named on the whole view, a depth gauge that goes down with the nose, the layers, speed and time."""
    an = m["anchors"]; o, ex, ez = an["o"], an["ex"], an["ez"]
    PX = lambda x, z: ((o[0] + x * (ex[0] - o[0]) + z * (ez[0] - o[0])) * W, (o[1] + x * (ex[1] - o[1]) + z * (ez[1] - o[1])) * H)
    pre, pen, one, ms = info["CUT"]; n1, ms2, t1 = info["CUT2"]; TP = info["TP"]; U = info["U"]; tp = m["tp"]; fz = info["FUZE"]; td = tp - fz; s = min(m["s"], info["S_BURST"]); v = m["v"]; Z = info["Z"]; sinD = -U[2]; VS = info["VS"]
    X0, X1 = info["ROOM_X"]; XF = info["XF"]; DEP = info["DEPTH"]; FT = lambda x: int(round(x / 0.3048)); cover = R(info["COVER"]); j = i - pre - pen
    for k in range(24):                                                # a darker foot to the picture, so that the captions read over pale earth
        d.rectangle([0, H - 216 + 9 * k, W, H - 216 + 9 * k + 9], fill=(0, 0, 0, int(105 * ease((k + 1) / 14.0))))
    fi = lambda t_: pre + (t_ / ms if t_ <= t1 else n1 + (t_ - t1) / ms2)              # frame at which tp = t_
    wide0 = (1 - ease((i - 6) / 10.0)) if hold is None else ease(hold * 4)             # the whole section at the start ...
    wide1 = ease((j - one - 34) / 14.0) * (1 - ease((i - (n - 10)) / 8.0)) if hold is None else 0.0     # ... and again once the camera is back out
    # ---- the whole section: what is where, and how deep
    for a, full in ((wide0, True), (wide1, False)):
        if a <= 0:
            continue
        xd = -17.0; p0 = PX(xd, 0.0); p1 = PX(xd, -DEP); c = (*AMBER, int(235 * a))
        dashed(d, [(PX(0, 0)[0] + (p0[0] - PX(0, 0)[0]) * q / 30.0, p0[1]) for q in range(31)], c, 3); q1 = PX(X0 - 1.5, -DEP); dashed(d, [(q1[0] + (p1[0] - q1[0]) * q / 30.0, p1[1]) for q in range(31)], c, 3)
        vdim(d, p0, p1, "%d m" % round(DEP), "%d FEET DOWN" % (round(FT(DEP), -1)), a)
        if full:
            q = PX(-2.0, 2.5); note(d, (q[0] + 60, q[1] - 124), "THE BOMB GOES IN HERE", "%d m/s  ·  %d° DOWN" % (round(info["V_HIT"]), round(info["DIVE"])), a); d.line([(q[0] + 50, q[1] - 40), q], fill=(*INK, int(230 * a)), width=3)
            q = PX(X1 + 31.0, -24.0); note(d, q, "EARTH", "%d m OF IT OVER THE HALL" % cover, a)
            q = PX(X1 + 1.5, Z[0] + 13.0); note(d, q, "THE HALL", "REINFORCED CONCRETE  ·  30 x 16 x 7 m", a); d.line([PX(X1 - 6.0, Z[0] + 4.6), PX(X1 - 6.0, Z[0] + 0.4)], fill=(*INK, int(230 * a)), width=3)
            q = PX((XF + X0) / 2 + 14.0, Z[2] + 19.0); note(d, q, "TUNNEL", "%d m OUT TO THE SLOPE" % round(X0 - XF, -1), a); d.line([PX((XF + X0) / 2 + 8.0, Z[2] + 10.8), PX((XF + X0) / 2 + 8.0, Z[2] + 7.4)], fill=(*INK, int(230 * a)), width=3)
    if hold is not None:
        lower(d, "THE SAME STRIKE, WITH THE GROUND CUT OPEN", "A concrete hall %d m (%d ft) under the slope: the depth the U.S. Air Force gives for this bomb  ·  an invented site" % (round(DEP), round(FT(DEP), -1)), ease(hold * 6) * (1 - ease((hold - 0.88) / 0.12)))
        return
    out = 1 - ease((td - 0.06) / 0.08)                                # the drawing clears when the hall has gone
    # ---- names of the roof and the hall, as the nose reaches them
    for k, (zm, big, small) in enumerate((((Z[0] + Z[1]) / 2, "2.5 m", "CONCRETE ROOF"), ((Z[1] + Z[2]) / 2, "7 m", "THE HALL"))):
        a = ease((i - fi(TP[k + 1]) + 10) / 8.0) * out
        if a > 0:
            p0 = PX(X1 + 2.2, zm); p1 = PX(X1 + 4.2, zm); d.line([p0, p1], fill=(*INK, int(230 * a)), width=3); note(d, (p1[0] - 14, p1[1]), big, small, a, dy=-44, anchor="ra")
    # ---- the depth gauge: it goes down beside the nose
    if tp >= -0.002 and out > 0:
        a = ease((i - pre + 2) / 8.0) * out; depth = max(s, 0.0) * sinD; xr = U[0] * max(s, 0.0) - 15.0; c = (*AMBER, int(235 * a)); c2 = (*AMBER, int(150 * a))
        top = PX(xr, 0); bot = PX(xr, -depth); d.line([top, bot], fill=c, width=4); d.line([(top[0] - 16, top[1]), (top[0] + 16, top[1])], fill=c, width=4)
        for k in range(5, int(depth) + 1, 5):
            q = PX(xr, -k); w_ = 14 if k % 10 == 0 else 8; d.line([(q[0] - w_, q[1]), (q[0] + w_, q[1])], fill=c, width=3)
            if k % 10 == 0 and depth - k > 3.0 and q[1] > 150:
                text(d, (q[0] + 26, q[1] - 17), "%d m" % k, F_SEMI(28), AMBER, a * 0.8)
        nose = PX(U[0] * s, U[2] * s)
        if depth > 0.5:
            dashed(d, [(nose[0] + (bot[0] - nose[0]) * q / 60.0, bot[1]) for q in range(61)], c, 2); d.line([(bot[0] - 16, bot[1]), (bot[0] + 16, bot[1])], fill=c, width=4)
        text(d, (bot[0] + 30, bot[1] - 88), "%.1f m" % depth, F_TITLE(70), AMBER, a); text(d, (bot[0] + 30, bot[1] - 6), "%d FEET DOWN" % FT(depth), F_SEMI(32), INK, a, tracking=2)
    # ---- captions, speed and time
    io = lambda t0, t1_: ease((i - fi(t0)) / 6.0) * (1 - ease((i - fi(t1_) + 5) / 5.0)); half = 0.5 * TP[1]
    if tp < 0:
        lower(d, "IT ARRIVES AT %d m/s" % round(info["V_HIT"]), "{:,} km/h, faster than sound, {:d}° down  ·  more than 12 tonnes, most of it steel".format(KMH(info["V_HIT"]), round(info["DIVE"])), ease((i - 14) / 6.0) * (1 - ease((i - pre + 4) / 4.0)))
    elif tp < half:
        lower(d, "INTO THE EARTH", "The tail and its lattice fins are torn off at the surface  ·  the steel body goes on alone", io(0.0, half))
    elif tp < TP[1]:
        lower(d, "STILL GOING", "Soft earth slows it only gradually: from %d m/s at the surface to about %d m/s at the roof, %d m down" % (round(VS[0]), round(VS[1], -1), cover), io(half, TP[1]))
    elif tp < TP[2]:
        lower(d, "THROUGH THE ROOF", "2.5 m of reinforced concrete take it down to about %d m/s" % round(VS[2], -1), io(TP[1], TP[2]))
    elif td < 0:
        lower(d, "INTO THE HALL, %d m DOWN" % round(DEP), "Its fuze has counted the layers and fires in the open space, %d thousandths of a second after the impact" % round(fz * 1000), ease((i - fi(TP[2])) / 5.0) * (1 - ease((i - (pre + pen) + 4) / 4.0)))
    elif td < 0.50:
        lower(d, "2.4 TONNES OF EXPLOSIVE IN A CLOSED HALL", "The gas has two ways out: %d m of tunnel, and the hole the bomb made" % round(X0 - XF, -1), ease((td - 0.004) / 0.03) * (1 - ease((td - 0.45) / 0.05)))
    else:
        lower(d, "THE ROOF COMES DOWN", "The broken roof and the earth on it fall into the hall  ·  %d m higher, the surface does not break" % cover, ease((td - 0.50) / 0.08) * (1 - ease((i - (n - 9)) / 8.0)))
    if 0 <= tp and td < 0:
        readout(d, "SPEED", "%d m/s" % round(v), ease((i - pre) / 4.0), AMBER, "T + %.1f ms" % (tp * 1000))
    elif td >= 0:
        readout(d, "AFTER THE IMPACT", "{:,} ms".format(int(round(tp * 1000))), 1.0, INK, "THE CHARGE HAS FIRED")
    slow = ("1 SECOND OF FILM = %d THOUSANDTHS OF A SECOND" % round(FPS * 1000 * (ms if tp < t1 else ms2))) if td < 0 else ("SLOWED 10 TIMES" if i < pre + pen + one else "SLOWED 3 TIMES")
    text(d, (W - 64, 60), slow, F_SEMI(26), DIM, 1.0, anchor="ra", tracking=3)
    text(d, (W - 64, 94), "200 ft IS THE AIR FORCE'S FIGURE  ·  SPEEDS ARE CALCULATED (YOUNG / SANDIA EQUATIONS)", F_SEMI(22), DIM, 1.0, anchor="ra", tracking=2)

def overlay_for(shot, i, n, m, info, hold=None):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    t = m["t"]; an = m.get("anchors", {}); P = lambda q: (q[0] * W, q[1] * H)
    tag(d, ease(i / 8.0) if shot == "approach" else 1.0)
    io = ease((i - 5) / 9.0) * (1 - ease((i - (n - 7)) / 7.0))
    seen = lambda q: 0.04 < q[0] < 0.96 and 0.08 < q[1] < 0.86
    if shot == "approach":
        lower(d, "B-2 SPIRIT", "About 15,200 m (50,000 ft) up at Mach 0.8  ·  a flying wing with no tail  ·  crew of two", io)
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
            callout(d, *P(an["target"]), "TARGET", "A HALL %d m UNDER THE SLOPE" % round(info["DEPTH"]), RED, a, dx=150, dy=-170)
    elif shot == "strike":
        tp = t; td = tp - info["FUZE"]; dep = round(info["DEPTH"]); ft = int(round(info["DEPTH"] / 0.3048, -1))
        readout(d, "SLOW MOTION", "T + {:,} ms".format(max(0, int(round(tp * 1000)))), ease((i - 2) / 6.0), INK, "13.6 t BOMB  ·  2.4 t OF EXPLOSIVE")
        a1 = ease((i - 3) / 8.0) * (1 - ease((td - 0.20) / 0.12)); a2 = ease((td - 0.36) / 0.12) * (1 - ease((i - (n - 10)) / 8.0))
        if a1 > 0:
            lower(d, "INTO THE MOUNTAINSIDE", "No flash at the surface: the bomb goes in whole and bursts %d m (%d ft) down" % (dep, ft), a1)
        if a2 > 0:
            lower(d, "THE BURST IS %d m UNDER GROUND" % dep, "The slope does not break  ·  flame out of the tunnel, smoke out of the bomb's hole and the air shafts", a2)
        a = ease((tp - 0.02) / 0.08) * (1 - ease((td - 0.20) / 0.12))
        if a > 0 and seen(an["hit"]):
            callout(d, *P(an["hit"]), "IT GOES IN HERE", "A SPURT OF EARTH, NO FLAME", AMBER, a, dx=150, dy=-190)
        a = ease((td - info["T_DOOR"] - 0.03) / 0.1) * (1 - ease((td - 1.6) / 0.3))
        if a > 0 and seen(an["mouth"]):
            callout_l(d, *P(an["mouth"]), "TUNNEL MOUTH", "THE DOORS ARE BLOWN OUT", AMBER, a, dx=-150, dy=-190)
    elif shot == "cutaway":
        cut_overlay(d, i, n, m, info, hold)
    elif shot == "after":
        dep = round(info["DEPTH"]); ft = int(round(info["DEPTH"] / 0.3048, -1)); a = ease((i - 16) / 10.0) * (1 - ease((i - (n - 14)) / 10.0))
        if a > 0 and seen(an["hole"]):
            callout(d, *P(an["hole"]), "THE HOLE", "ABOUT A METRE ACROSS  ·  THE HALL IS %d m UNDER IT" % dep, RED, a, dx=170, dy=-120)
        lower(d, "TWENTY SECONDS LATER", "From outside: a hole, earth thrown round it, smoke  ·  everything else happened %d m (%d ft) down" % (dep, ft), ease((i - 10) / 12.0) * (1 - ease((i - (n - 10)) / 8.0)))
    return ov

def summary_frame(bg, i, n, info):
    frame = bg.copy(); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov); t = i / FPS; tag(d, 1.0); T = info["TABLE"]; v = round(info["V_HIT"]); PB = info["PUBLISHED"]; dep = round(info["DEPTH"])
    text(d, (120, 140), "HOW DEEP DOES A GBU-57 GO?", F_TITLE(80), INK, ease((t - 0.1) / 0.5))
    a = ease((t - 0.4) / 0.5); d.rectangle([120, 248, 120 + int(1680 * a), 251], fill=(*AMBER, int(255 * a)))
    rows = [("THE U.S. AIR FORCE SAYS", "\u201cup to 200 feet underground before exploding\u201d (61 m)  ·  in what ground, it does not say", RED),
            ("IN THIS FILM", "%d m of soft earth and a 2.5 m concrete roof  ·  it bursts in the hall, %d m down" % (R(info["COVER"]), dep), AMBER),
            ("CALCULATED AT %d m/s IN:" % v, "", AMBER),
            ("    SOFT EARTH", "about %.0f m" % T["fill"], DIM),
            ("    ORDINARY SOIL", "about %.0f m   ·   published: %.0f m (200 ft) of earth" % (T["earth"], PB["earth"]), DIM),
            ("    REINFORCED CONCRETE", "about %.0f m   ·   published: %.0f m (60 ft); a 2004 proposal said %.0f m" % (T["concrete"], PB["concrete"][0], PB["concrete"][1]), DIM),
            ("    WEATHERED ROCK", "about %.0f m   ·   the 2004 proposal: %.0f m (130 ft) of moderately hard rock" % (T["weathered"], PB["rock"]), DIM),
            ("    SOUND LIMESTONE", "about %.0f m" % T["limestone"], DIM),
            ("FIRST USED", "22 June 2025  ·  14 dropped by seven B-2s, 12 of them on Fordow", DIM)]
    y = 278
    for r, (lab, val, col) in enumerate(rows):
        a = ease((t - 0.7 - 0.22 * r) / 0.45); dx = int((1 - a) * 24)
        text(d, (120 + dx, y + 6), lab, F_SEMI(30), col, a, tracking=3); text(d, (700 + dx, y - 1), val, F_MED(34), INK, a)
        y += 62
    a = ease((t - 3.4) / 0.6)
    text(d, (120, 872), "By the open penetration equations this bomb reaches 61 m only in earth, so this film's mountainside is earth. Under hard rock", F_MED(30), INK, a)
    text(d, (120, 910), "it would stop far short: at Fordow six were dropped down each of two ventilation shafts, one after another.", F_MED(30), INK, a)
    text(d, (120, 962), "The table is calculated with the Young / Sandia penetration equations: estimates, not test results. The published figures for this", F_MED(26), DIM, a)
    text(d, (120, 998), "bomb disagree with each other, and the real ones are not public.", F_MED(26), DIM, a)
    frame.alpha_composite(ov)
    return frame

def build_audio(path, starts, metas, lens, total, info):
    """The soundtrack from recorded effects.  Outside, the burst is a thud from deep in the ground and then the blast at the tunnel mouth."""
    import gsfx as S
    if not S.available():
        print("NOTE: recorded effects not found in %s - using the synthesized soundtrack" % S.DIR); return B.build_audio_synth(path, starts, metas, lens, total, info)
    gp = B.gp; mx = gp.Mix(total); T = {k: v / FPS for k, v in starts.items()}; L = {k: v / FPS for k, v in lens.items()}
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
    th = when("strike", lambda m: m["t"] >= 0.0); tdet = when("strike", lambda m: m["t"] >= info["FUZE"]); tmouth = when("strike", lambda m: m["t"] >= info["FUZE"] + info["T_DOOR"])
    S.put(mx, T["strike"], S.bed("wind", L["strike"], t0=4.0, fi=0.3, fo=0.5, level=0.035))
    if th:
        S.put(mx, th - 0.95, S.cut("missile", 0.95, 0.95, fi=0.25, fo=0.01), 0.60); S.put(mx, th, S.cut("impact", 10.0, 1.4), 0.90); S.put(mx, th, S.cut("boom_deep", 0.0, 1.3, speed=2.6, fo=0.5), 0.50)
        S.put(mx, th + 0.1, S.cut("debris", 0.0, 2.0, fo=0.6), 0.40, -0.2)
    if tdet:                                                                                     # the burst far under the slope: felt more than heard
        S.put(mx, tdet + 0.02, S.cut("boom_muffled", 6.3, 6.0, speed=0.8, fo=1.5, drive=2.5, lp=300), 0.60); S.put(mx, tdet + 0.02, S.bed("quake", 3.0, t0=40.0, fi=0.05, fo=2.2, lp=140, level=0.10))
    if tmouth:                                                                                   # the blast reaches the tunnel mouth
        S.put(mx, tmouth, S.cut("boom_muffled", 6.3, 2.6, speed=2.3, fo=1.2), 0.85, -0.3); S.put(mx, tmouth, S.cut("boom_deep", 0.0, 2.4, speed=1.6, fo=1.2), 0.50, -0.3)
        S.put(mx, tmouth + 0.1, S.cut("hiss", 3.1, 4.5, speed=0.6, fi=0.15, fo=2.0, lp=2000), 0.17, -0.4); S.put(mx, tmouth + 0.25, S.cut("debris", 0.0, 2.0, fo=0.6), 0.35, -0.4)
    tc = T["cutaway"]; lc = L["cutaway"]; pre, pen, one, ms = info["CUT"][:4]; n1, ms2, t1 = info["CUT2"]; hold = B.HOLD.get("cutaway", 0) / FPS; TP = info["TP"]; at = lambda fr: tc + hold + fr / FPS
    fi_ = lambda t_: pre + (t_ / ms if t_ <= t1 else n1 + (t_ - t1) / ms2)
    S.put(mx, tc, S.bed("drone", lc, t0=30.0, fi=0.5, fo=0.8, level=0.05))
    t_in = at(pre); tb = at(pre + pen); dur = tb - t_in                                           # the body grinding down through the earth
    g = S.bed("quake", dur + 0.3, t0=40.0, fi=0.08, fo=0.3, lp=4500, hp=420, level=0.060); n_ = len(g); g *= np.interp(np.arange(n_) / SR, [0, 0.3, dur, dur + 0.3], [1.0, 1.0, 0.55, 0.0])[:, None]; S.put(mx, t_in, g)
    S.put(mx, t_in, S.cut("impact", 10.0, 2.4, speed=0.55), 0.85); S.put(mx, t_in, S.cut("boom_deep", 0.0, 1.8, speed=1.9, fo=0.8), 0.45)
    S.put(mx, at(fi_(TP[1])), S.cut("debris", 0.0, 2.6, speed=0.5, fo=0.8), 0.60, 0.1); S.put(mx, at(fi_(TP[1])), S.cut("boom_deep", 0.0, 1.5, speed=2.2, fo=0.6), 0.36)       # the roof
    S.put(mx, tb, S.cut("boom_deep", 0.0, 8.0, speed=0.6, fo=2.0, drive=3.0), 0.45); S.put(mx, tb + 0.04, S.cut("boom_muffled", 6.3, 4.0, speed=1.5, fo=2.0), 0.85)
    S.put(mx, tb, S.cut("boom_deep", 0.0, 2.2, speed=2.0, fo=1.0), 0.55); S.put(mx, tb + 0.1, S.cut("debris", 0.0, 3.0, speed=0.6, fo=1.0), 0.32, 0.2)
    j_col = one + (0.50 * 240.0 - one) / 3.0; tcol = tb + j_col / FPS; dur = max(tc + lc - tcol - 0.1, 0.5)
    S.put(mx, tcol, S.cut("collapse", 2.2, dur, speed=0.75, fi=0.15, fo=1.0), 0.60, 0.1)
    ta = T["after"]; la_ = L["after"] + L["summary"]; S.put(mx, ta, S.bed("wind", la_, t0=6.0, fi=0.5, fo=1.0, level=0.045))
    ts_ = T["summary"]; S.put(mx, ts_, S.bed("drone", L["summary"], t0=8.0, fi=0.6, fo=1.2, level=0.06)); S.put(mx, ts_ + 0.1, S.cut("boom_deep", 0.0, 2.0, speed=1.8, fo=1.0), 0.28)
    for r in range(9):
        tick(ts_ + 0.7 + 0.22 * r)
    S.finish(mx, total, path)

B.SPECS = SPECS; B.tag = tag; B.card_frame = card_frame; B.cut_overlay = cut_overlay; B.overlay_for = overlay_for; B.summary_frame = summary_frame; B.build_audio = build_audio; B.N_SUMMARY = 264; B.HOLD = {"cutaway": 66}

if __name__ == "__main__":
    B.main()
