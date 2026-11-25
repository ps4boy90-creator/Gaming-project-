"""Finishing for the Lancaster / Tallboy segment: upscale to 1080p, title card, captions, the radius circles, a
closing table, synthesized sound, encode.

  python3 lpost.py <frames_root> <out.mp4> [--draft]
"""
import os, sys, json, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "blackhawk-mk77"))
import post as gp
from post import W, H, FPS, SR, AMBER, RED, INK, DIM, PANEL, F_TITLE, F_SEMI, F_MED, ease, text, shadowed, lower, callout
from npost import readout, dashed, _mod

ORDER = ["card", "approach", "intro", "release", "fall", "impact", "radius", "after", "summary"]
N_SUMMARY = 228
SPECS = [("BOMB", "Tallboy  ·  12,000 lb, medium capacity"), ("SIZE", "21 ft (6.4 m) long  ·  38 in (0.97 m) across"), ("WEIGHT", "about 5,440 kg (12,000 lb)"), ("EXPLOSIVE", "2,360 kg (5,200 lb) of Torpex"),
         ("FUZE", "three tail pistols, here set to 0.5 s"), ("CARRIED BY", "Avro Lancaster, one bomb each"), ("FIRST USED", "June 1944  ·  designed by Barnes Wallis")]
KMH = lambda v: int(round(v * 3.6, -1))
MK84 = (120, 170, 215)

def tag(d, a=1.0):
    text(d, (64, 54), "EXPLOSION COMPARISON", F_SEMI(30), INK, a, tracking=4)
    d.rectangle([64, 96, 64 + 54, 100], fill=(*AMBER, int(255 * a)))
    text(d, (130, 84), "11  ·  TALLBOY  ·  AVRO LANCASTER", F_MED(26), DIM, a, tracking=2)

def card_frame(img, i, n):
    base = Image.new("RGBA", (W, H), (*PANEL, 255))
    base.paste(img.convert("RGB").resize((W // 2, H), Image.LANCZOS), (0, 0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    grad = Image.linear_gradient("L").rotate(90, expand=True).resize((90, H))
    seam = Image.new("RGBA", (90, H), (*PANEL, 255)); seam.putalpha(grad.point(lambda v: 255 - v))
    base.alpha_composite(seam.transpose(Image.FLIP_LEFT_RIGHT), (W // 2 - 90, 0))
    t = i / FPS; x0 = W // 2 + 96
    text(d, (x0, 130), "EXPLOSION COMPARISON  ·  11", F_SEMI(30), DIM, ease((t - 0.10) / 0.5), tracking=5)
    a = ease((t - 0.20) / 0.5); text(d, (x0 + int((1 - a) * 40), 180), "TALLBOY", F_TITLE(170), INK, a)
    a = ease((t - 0.35) / 0.5); text(d, (x0 + int((1 - a) * 40), 400), "A 12,000 LB BOMB FROM 18,000 FT ON A GERMAN DEPOT", F_TITLE(38), AMBER, a, tracking=1)
    a = ease((t - 0.45) / 0.5); d.rectangle([x0, 478, x0 + int(820 * a), 481], fill=(*AMBER, int(255 * a)))
    y = 512
    for k, (lab, val) in enumerate(SPECS):
        a = ease((t - 0.65 - 0.12 * k) / 0.45); dx = int((1 - a) * 28); hot = lab == "EXPLOSIVE"
        text(d, (x0 + dx, y), lab, F_SEMI(31), RED if hot else DIM, a, tracking=3)
        text(d, (x0 + 250 + dx, y - 4), val, F_MED(36), INK, a)
        y += 58
    a = ease((t - 1.7) / 0.6)
    text(d, (x0, 936), "Dropped in 1944 and 1945 by Nos. 617 and 9 Squadrons, Royal Air Force,", F_MED(28), INK, a)
    text(d, (x0, 970), "on targets that ordinary bombs could not break.", F_MED(28), INK, a)
    text(d, (x0, 1016), "The depot and the strike are invented. Depth and radii are calculated, not measured.", F_MED(26), DIM, a)
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

def ring(d, pts, color, a, width=4, dash=True):
    if a <= 0:
        return
    P = [(x * W, y * H) for x, y in pts]; c = (*color, int(235 * a))
    if dash:
        dashed(d, P, c, width)
    else:
        d.line(P, fill=c, width=width)

def overlay_for(shot, i, n, m, info):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    t = m["t"]; an = m.get("anchors", {}); P = lambda q: (q[0] * W, q[1] * H)
    tag(d, ease(i / 8.0) if shot == "approach" else 1.0)
    io = ease((i - 5) / 9.0) * (1 - ease((i - (n - 7)) / 7.0))
    seen = lambda q: 0.04 < q[0] < 0.96 and 0.08 < q[1] < 0.86
    vh = round(info["V_HIT"]); deep = round(info["D_PATH"] * math.sin(math.radians(info["DIVE"]))); dburst = round(info["DEPTH"]); rs = round(info["R_STRUCT"]); rb = round(info["R_BLAST"]); cr = round(2 * info["CRATER_R"])
    if shot == "approach":
        lower(d, "AVRO LANCASTER", "18,000 ft up at 200 mph  ·  on the run-up the bulged bomb doors open on a single 12,000 lb bomb", io)
        a = ease((i - 62) / 8.0) * (1 - ease((i - (n - 10)) / 7.0))
        if a > 0 and seen(an["bomb"]):
            callout(d, *P(an["bomb"]), "TALLBOY", "6.4 m LONG  ·  ABOUT 5.4 t", AMBER, a, dx=-160, dy=220)
        a = ease((i - 12) / 10.0) * (1 - ease((i - (n - 10)) / 7.0))
        text(d, (W - 64, 60), "FOUR MERLIN ENGINES  ·  SPAN 102 ft (31.1 m)", F_SEMI(28), INK, a, anchor="ra", tracking=3)
        text(d, (W - 64, 98), "MARKINGS OF No. 617 SQUADRON; THE AIRCRAFT LETTER IS NOT A PARTICULAR MACHINE", F_SEMI(24), DIM, a, anchor="ra", tracking=2)
    elif shot == "intro":
        lower(d, "TALLBOY", "A streamlined steel case built to reach the ground at nearly the speed of sound and go deep into it before it bursts", io)
        A = lambda k: ease((i - 8 - 9 * k) / 8.0) * (1 - ease((i - (n - 7)) / 6.0)); px = {k: P(q) for k, q in an.items()}
        dim_line(d, (px["tail"][0], px["top"][1] - 70), (px["nose"][0], px["top"][1] - 70), "21 ft  ·  6.4 m  ·  ABOUT 5,440 kg", A(0))
        for k, (key, big, small, col, ex_, ey_) in enumerate((("case", "CAST STEEL CASE", "2,360 kg OF TORPEX INSIDE", RED, 150, 235), ("fins", "FOUR FINS SET AT 5°", "THEY SPIN THE BOMB: 300 rpm AT IMPACT", AMBER, -60, 230),
                                                           ("joint", "LIGHT-ALLOY TAIL", "ABOUT HALF THE BOMB'S LENGTH", AMBER, -200, -215), ("lorry", "3-TON LORRY, 6 m", "FOR SCALE", INK, -330, 60))):
            a = A(k + 1)
            if a > 0:
                callout(d, *px[key], big, small, col, a, dx=ex_, dy=ey_)
    elif shot == "release":
        a1 = ease((i - 4) / 8.0) * (1 - ease((t + 0.12) / 0.1)); a2 = ease((t - 0.02) / 0.15) * (1 - ease((i - (n - 8)) / 7.0))
        if a1 > 0:
            lower(d, "ONE BOMB FILLS THE BAY", "It hangs in two links that meet beneath it  ·  the bay is 33 ft long, the bomb 21 ft", a1)
        if a2 > 0:
            lower(d, "RELEASED", "The links let go  ·  the offset fins begin to turn the bomb as it gathers speed  ·  shown at half speed", a2)
            readout(d, "AFTER RELEASE", "%.2f s" % max(t, 0.0), a2)
    elif shot == "fall":
        readout(d, "ABOVE THE TARGET", "{:,} m".format(int(round(m.get("alt", 0), -1))), 1.0, AMBER, "{:,} km/h  ·  {:d}° DOWN".format(KMH(m.get("v", 0)), round(m.get("dive", 0))))
        lower(d, "NEARLY THE SPEED OF SOUND", "It falls for %d s and arrives at %d m/s ({:,} km/h, Mach %.2f)  ·  published: 1,097 ft/s (334 m/s)".format(KMH(info["V_HIT"])) % (round(info["TOF"]), vh, info["MACH_HIT"]), io)
        a = ease((i - 30) / 10.0) * (1 - ease((i - (n - 20)) / 10.0))
        if a > 0 and seen(an["target"]):
            callout(d, *P(an["target"]), "AIM POINT", "THE DEPOT'S YARD", RED, a, dx=170, dy=-170)
        if a > 0 and seen(an["barracks"]) and i > 44:
            callout(d, *P(an["barracks"]), "BARRACKS", "", AMBER, a * ease((i - 44) / 8.0), dx=-330, dy=-90)
    elif shot == "impact":
        tp = t; td = tp - info["FUZE"]
        readout(d, "SLOW MOTION", "T + {:,} ms".format(max(0, int(round(tp * 1000)))), ease((i - 2) / 6.0), INK, "5.4 t BOMB  ·  2,360 kg OF TORPEX")
        a1 = ease((i - 3) / 8.0) * (1 - ease((td + 0.06) / 0.06)); a2 = ease((td - 0.02) / 0.10) * (1 - ease((td - 1.25) / 0.2)); a3 = ease((td - 1.5) / 0.2) * (1 - ease((i - (n - 10)) / 8.0))
        if a1 > 0:
            lower(d, "INTO THE GROUND", "5.4 t at %d m/s goes about %d m into the earth and stops  ·  the fuze is still counting" % (vh, deep), a1)
        if a2 > 0:
            lower(d, "HALF A SECOND LATER, %d m DOWN" % dburst, "2,360 kg of Torpex fires under the yard: not a fireball but the ground itself, thrown into the air", a2)
        if a3 > 0:
            lower(d, "THE YARD COMES DOWN AGAIN", "Thousands of tonnes of earth fall back over the depot  ·  buildings near the burst are shaken down and buried", a3)
        a = ease((td - 0.9) / 0.15) * (1 - ease((td - 2.2) / 0.3))
        if a > 0 and seen(an["top"]):
            callout(d, *P(an["top"]), "100 m UP", "", AMBER, a, dx=230, dy=-40)
    elif shot == "radius":
        paths = m.get("paths", {}); A = lambda k: ease((i - 22 - 12 * k) / 10.0) * (1 - ease((i - (n - 8)) / 7.0))
        lower(d, "HOW FAR IT REACHES", "Crater about %d m across (published)  ·  the two outer circles are scaled from the Mk 82's, for a burst at the surface" % cr, io)
        for k, (key, col, big, small, dx, dy) in enumerate((("crater", RED, "CRATER: %d m ACROSS" % cr, "PUBLISHED: 100 ft", 260, -60), ("struct", AMBER, "BUILDINGS DESTROYED", "TO ABOUT %d m" % rs, 250, 110), ("blast", INK, "5 psi BLAST", "TO ABOUT %d m" % rb, -330, 130))):
            a = A(k)
            if key in paths:
                ring(d, paths[key], col, a, 5 if key == "crater" else 4, dash=key != "crater")
            if a > 0 and key in an and seen(an[key]):
                callout(d, *P(an[key]), big, small, col, a, dx=dx, dy=dy)
        a = A(3)
        if "mk84" in paths:
            ring(d, paths["mk84"], MK84, a * 0.9, 3)
        if a > 0 and seen(an["mk84"]):
            callout(d, *P(an["mk84"]), "Mk 84 (2,000 lb): 5 psi", "TO ABOUT %d m, FOR COMPARISON" % round(info["R_MK84"]), MK84, a, dx=-470, dy=-150)
        text(d, (W - 64, 60), "SLOWED ABOUT 1.5 TIMES", F_SEMI(26), DIM, 1.0, anchor="ra", tracking=3)
        text(d, (W - 64, 94), "A BURST THIS DEEP SENDS LESS OF ITS FORCE INTO THE AIR AND MORE INTO THE GROUND", F_SEMI(22), DIM, 1.0, anchor="ra", tracking=2)
    elif shot == "after":
        a = ease((i - 18) / 10.0) * (1 - ease((i - (n - 14)) / 10.0))
        if a > 0 and seen(an["a"]) and seen(an["b"]):
            dim_line(d, P(an["a"]), P(an["b"]), "ABOUT %d m" % cr, a, RED, off=-58)
        if a > 0 and seen(an["lorry"]):
            callout(d, *P(an["lorry"]), "A LORRY, 6 m LONG", "", INK, a, dx=120, dy=-150)
        lower(d, "HALF A MINUTE LATER", "A crater about %d m across where the vehicle park was  ·  published for the Tallboy: 100 ft across, 80 ft deep" % cr, ease((i - 10) / 12.0) * (1 - ease((i - (n - 10)) / 8.0)))
    return ov

def summary_frame(bg, i, n, info):
    frame = bg.copy(); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov); t = i / FPS; tag(d, 1.0); v = round(info["V_HIT"])
    text(d, (120, 140), "TALLBOY: THE NUMBERS", F_TITLE(80), INK, ease((t - 0.1) / 0.5))
    a = ease((t - 0.4) / 0.5); d.rectangle([120, 248, 120 + int(1680 * a), 251], fill=(*AMBER, int(255 * a)))
    rows = [("THE BOMB", "21 ft (6.4 m)  ·  38 in (0.97 m) across  ·  about 5,440 kg  ·  2,360 kg of Torpex", DIM),
            ("RELEASE", "18,000 ft (5,490 m) at 200 mph  ·  falls %d s (published: 37 s)" % round(info["TOF"]), DIM),
            ("AT IMPACT", "%d m/s ({:,} km/h)  ·  published: 1,097 ft/s (334 m/s), 300 rpm".format(KMH(info["V_HIT"])) % v, AMBER),
            ("INTO THE GROUND", "about %d m in moist clay and loam (calculated), in under a tenth of a second" % round(info["D_PATH"] * math.sin(math.radians(info["DIVE"]))), DIM),
            ("FUZE", "0.5 s after impact  ·  delays of 0.5 s and 11 s are recorded for Tallboys", DIM),
            ("CRATER", "about %d m across  ·  published: 100 ft across, 80 ft deep" % round(2 * info["CRATER_R"]), RED),
            ("BUILDINGS DESTROYED", "to about %d m  ·  Mk 84 (2,000 lb): about 27 m" % round(info["R_STRUCT"]), DIM),
            ("5 psi BLAST", "to about %d m  ·  Mk 84: about %d m  ·  both for a burst at the surface" % (round(info["R_BLAST"]), round(info["R_MK84"])), DIM),
            ("CARRIED BY", "Avro Lancaster with bulged bomb doors  ·  Nos. 617 and 9 Squadrons, 1944–45", DIM)]
    y = 278
    for r, (lab, val, col) in enumerate(rows):
        a = ease((t - 0.7 - 0.22 * r) / 0.45); dx = int((1 - a) * 24)
        text(d, (120 + dx, y + 6), lab, F_SEMI(30), col, a, tracking=3); text(d, (620 + dx, y - 2), val, F_MED(38), INK, a)
        y += 62
    a = ease((t - 3.4) / 0.6)
    text(d, (120, 872), "Against concrete it did less than its legend says: in the 1946 trials at Farge a Tallboy went 5 ft 7 in (1.7 m) into", F_MED(30), INK, a)
    text(d, (120, 910), "reinforced concrete, and at Brest in 1944 no hit went through the U-boat bunker's roof before it burst.", F_MED(30), INK, a)
    text(d, (120, 962), "The depot is invented. Fall, impact speed and depth are calculated; the two outer radii are scaled from the Mk 82's published ones.", F_MED(26), DIM, a)
    text(d, (120, 998), "Sources: US Navy OP 1665; Bomber Command Museum of Canada; US Strategic Bombing Survey; Project Ruby report; Young, SAND97-2426.", F_MED(26), DIM, a)
    frame.alpha_composite(ov)
    return frame

# ------------------------------------------------------------------ sound
def s_merlins(dur, seed=3):
    """Four Merlins and their propellers heard from alongside: a beating drone on the blade-passing note, a rush of air over it."""
    n = int(dur * SR); t = np.arange(n) / SR; x = np.zeros(n)
    for k, f in enumerate((65.0, 65.9, 64.3, 66.6)):                     # 1,300 rpm, three blades; the four are never quite in step
        for h_, g in ((1, 1.0), (2, 0.55), (3, 0.3), (4, 0.16)):
            x += g * np.sin(2 * np.pi * f * h_ * t + k * 1.3 + h_)
    return x * 0.11 * _mod(n, 1.5, 0.2, seed) + gp.lp(gp.noise(n), 220, 2) * 2.6 * _mod(n, 0.8, 0.25, seed + 1) + gp.bp(gp.noise(n), 300, 2400) * 0.7 * _mod(n, 2.0, 0.3, seed + 2)

def s_buffet(dur, seed=5):
    """Air beating in the open bay."""
    n = int(dur * SR); return gp.lp(gp.noise(n), 90, 2) * 6.0 * np.clip(_mod(n, 9.0, 0.8, seed), 0.2, None) + gp.bp(gp.noise(n), 200, 900) * 0.8 * _mod(n, 5.0, 0.5, seed + 1)

def s_buried(scale, slow=1.0):
    """A big charge going off under ground: no crack, a heavy heave and a long rumble."""
    n = int((5.0 + scale) * slow * SR); t = np.arange(n) / SR / slow
    body = gp.lp(gp.noise(n), 75 / slow, 3) * 13.0 * np.minimum(1.0, t / 0.03) * np.exp(-t / (0.9 * scale))
    sub = np.sin(2 * np.pi * np.cumsum(np.linspace(44 / slow, 18 / slow, n)) / SR) * 2.4 * np.exp(-t / (0.8 * scale))
    tail = gp.bp(gp.noise(n), 40, 320) * 1.8 * np.exp(-t / (1.8 * scale)) * _mod(n, 3.0, 0.4, 17)
    return body + sub + tail

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
    la = L["approach"]; ramp = np.minimum(1.0, np.arange(int((la + 0.4) * SR)) / (0.5 * SR)); mx.add(T["approach"], s_merlins(la + 0.4, 3) * ramp, 0.55, -0.15); mx.add(T["approach"], s_merlins(la + 0.4, 8) * ramp, 0.55, 0.15)
    td_ = when("approach", lambda m: m.get("doors", 0) > 0.02)
    if td_:
        mx.add(td_, gp.s_whoosh(2.0, 200, 900, 0.5), 0.35); mx.add(td_ + 1.9, gp.s_thud(0.8), 0.5)
    mx.add(T["intro"], gp.s_drone(L["intro"]), 0.4); mx.add(T["intro"] + 0.05, gp.s_thud(0.8), 0.4)
    for k in range(5):
        mx.add(T["intro"] + (8 + 9 * k) / FPS, gp.s_tick(), 0.35, 0.3 - 0.12 * k)
    lr = L["release"]; mx.add(T["release"], s_merlins(lr, 11) * 0.9, 0.5); mx.add(T["release"], s_buffet(lr, 5) * 0.4, 0.4)
    tr = when("release", lambda m: m["t"] >= 0.0)
    if tr:
        mx.add(tr, gp.s_thud(1.6), 1.0); mx.add(tr + 0.02, gp.s_ping(600, 0.3), 0.25, -0.2); mx.add(tr + 0.1, gp.s_whoosh(1.6, 250, 1400, 0.3), 0.4)
    lf = L["fall"]; w = gp.s_wind(lf) * 0.6 * np.linspace(0.5, 1.0, int(lf * SR)); mx.add(T["fall"], w, 1.0); mx.add(T["fall"], gp.s_whoosh(lf, 300, 3200, 0.97), 0.75)
    th = when("impact", lambda m: m["t"] >= 0.0); tdet = when("impact", lambda m: m["t"] >= info["FUZE"])
    mx.add(T["impact"], gp.s_wind(L["impact"]) * 0.12, 1.0)
    if th:
        mx.add(T["impact"], gp.s_whoosh(th - T["impact"] + 0.05, 600, 3200, 0.96), 0.7); mx.add(th, gp.s_thud(2.4), 1.0); mx.add(th + 0.02, gp.s_boom(0.35, 1.0), 0.3)
    if tdet:
        mx.add(tdet, s_buried(1.8, 1.6), 1.0); mx.add(tdet + 0.12, gp.s_boom(1.2, 2.5), 0.7); mx.add(tdet + 1.2, gp.s_debris(7.0, 60, 2.5), 0.55, 0.1)
    tr_ = T["radius"]; mx.add(tr_, gp.s_wind(L["radius"]) * 0.10, 1.0); mx.add(tr_ + 0.25, s_buried(1.6, 1.3), 0.85); mx.add(tr_ + 0.35, gp.s_boom(1.0, 1.6), 0.5); mx.add(tr_ + 1.4, gp.s_debris(4.0, 50, 1.5), 0.45, -0.1)
    for k in range(4):
        mx.add(tr_ + (22 + 12 * k) / FPS, gp.s_tick(), 0.35, 0.2)
    ta = T["after"]; la_ = L["after"] + L["summary"]; mx.add(ta, gp.s_wind(la_) * 0.16, 1.0, -0.1); mx.add(ta + 0.3, gp.s_debris(3.0, 8, 1.0), 0.2, 0.2)
    ts_ = T["summary"]; mx.add(ts_, gp.s_drone(L["summary"]), 0.45); mx.add(ts_ + 0.1, gp.s_thud(1.2), 0.4)
    for r in range(9):
        mx.add(ts_ + 0.7 + 0.22 * r, gp.s_tick(), 0.3, 0.3)
    x = np.tanh(mx.b[: int(total * SR)] * 1.1)
    fo = int(0.8 * SR); x[-fo:] *= np.linspace(1, 0, fo)[:, None]
    x = x / (np.abs(x).max() + 1e-9) * 0.89
    with wave.open(path, "wb") as w_:
        w_.setnchannels(2); w_.setsampwidth(2); w_.setframerate(SR); w_.writeframes((x * 32767).astype("<i2").tobytes())

FADES = {"card": (8, 6), "approach": (8, 5), "intro": (6, 6), "release": (6, 5), "fall": (5, 0), "impact": (0, 8), "radius": (6, 6), "after": (6, 0), "summary": (0, 16)}

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
            n = N_SUMMARY; metas[shot] = {}; bg = Image.blend(last.convert("RGB").filter(ImageFilter.GaussianBlur(14)), Image.new("RGB", (W, H), PANEL), 0.84).convert("RGBA"); seq = list(range(n))
        else:
            d1, f1, m1 = _load(root, shot); n = len(f1); metas[shot] = m1; seq = list(range(n))
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
                shadowed(frame, overlay_for(shot, k, n, m1[str(k)], info))
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
