"""Finishing for the MC-130 / MOAB segment: upscale to 1080p, title card, captions, the pressure rings on the valley,
a closing table, sound, encode.

  python3 apost.py <frames_root> <out.mp4> [--draft]

The assembly and the fades are the BLU-82 segment's (dpost.py); this file supplies this film's words, drawings and
soundtrack (recorded effects from ../c130-blu82/sfx or $SFX_DIR; without them dpost's synthesized track is used).
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "blackhawk-mk77", "b1b-gbu28", "c130-blu82"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
import dpost as B
from post import W, H, FPS, SR, AMBER, RED, INK, DIM, PANEL, F_TITLE, F_SEMI, F_MED, ease, text, shadowed, lower, callout
from npost import readout, dashed

dim_line = B.dim_line
KMH = lambda v: int(round(v * 3.6, -1))
R = lambda x: int(math.floor(x + 0.5))
SPECS = [("BOMB", "GBU-43/B Massive Ordnance Air Blast"), ("SIZE", "9.2 m long  ·  1.03 m across"), ("WEIGHT", "9,800 kg (21,600 lb)"), ("EXPLOSIVE", "8,500 kg of H6"),
         ("CASE", "thin aluminium"), ("GUIDANCE", "GPS and inertial, four lattice fins"), ("DROPPED BY", "MC-130, pulled out by parachute"), ("FIRST USED", "13 April 2017, Afghanistan")]
WHITE = (244, 244, 240)

def tag(d, a=1.0):
    text(d, (64, 54), "EXPLOSION COMPARISON", F_SEMI(30), INK, a, tracking=4)
    d.rectangle([64, 96, 64 + 54, 100], fill=(*AMBER, int(255 * a)))
    text(d, (130, 84), "13  ·  GBU-43/B MOAB  ·  MC-130 HERCULES", F_MED(26), DIM, a, tracking=2)

def _tw(d, s, f, tracking=0):
    return sum(d.textlength(ch, font=f) + tracking for ch in s) - tracking if s else 0.0

def label(d, px, py, big, small, color, a=1.0, dx=150, dy=-120):
    """A leader from a tracked point to a label on the side dx points to; the elbow is moved so that the words stay inside the picture."""
    if a <= 0:
        return
    w = max(_tw(d, big, F_TITLE(64)), _tw(d, small, F_SEMI(32), 3)); ex, ey = px + dx, py + dy; c = (*color, int(255 * a)); sg = 1 if dx >= 0 else -1
    ex = min(ex, W - 56 - 40 - w) if sg > 0 else max(ex, 56 + 40 + w)
    d.line([(px, py), (ex, ey), (ex + sg * 28, ey)], fill=c, width=3); d.ellipse([px - 7, py - 7, px + 7, py + 7], outline=c, width=3)
    text(d, (ex + sg * 40, ey - 46), big, F_TITLE(64), color, a, anchor="la" if sg > 0 else "ra"); text(d, (ex + sg * 40, ey + 28), small, F_SEMI(32), INK, a, anchor="la" if sg > 0 else "ra", tracking=3)

callout_l = label

def card_frame(img, i, n):
    base = Image.new("RGBA", (W, H), (*PANEL, 255))
    base.paste(img.convert("RGB").resize((W // 2, H), Image.LANCZOS), (0, 0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    grad = Image.linear_gradient("L").rotate(90, expand=True).resize((90, H))
    seam = Image.new("RGBA", (90, H), (*PANEL, 255)); seam.putalpha(grad.point(lambda v: 255 - v))
    base.alpha_composite(seam.transpose(Image.FLIP_LEFT_RIGHT), (W // 2 - 90, 0))
    t = i / FPS; x0 = W // 2 + 96
    text(d, (x0, 110), "EXPLOSION COMPARISON  ·  13", F_SEMI(30), DIM, ease((t - 0.10) / 0.5), tracking=5)
    a = ease((t - 0.20) / 0.5); text(d, (x0 + int((1 - a) * 40), 156), "MOAB", F_TITLE(170), INK, a)
    a = ease((t - 0.35) / 0.5); text(d, (x0 + int((1 - a) * 40), 374), "21,600 LB OF AIR BLAST, DROPPED FROM A CARGO AIRCRAFT", F_TITLE(34), AMBER, a, tracking=1)
    a = ease((t - 0.45) / 0.5); d.rectangle([x0, 448, x0 + int(820 * a), 451], fill=(*AMBER, int(255 * a)))
    y = 478
    for k, (lab, val) in enumerate(SPECS):
        a = ease((t - 0.65 - 0.11 * k) / 0.45); dx = int((1 - a) * 28); hot = lab == "EXPLOSIVE"
        text(d, (x0 + dx, y), lab, F_SEMI(30), RED if hot else DIM, a, tracking=3)
        text(d, (x0 + 250 + dx, y - 4), val, F_MED(35), INK, a)
        y += 55
    a = ease((t - 1.7) / 0.6)
    text(d, (x0, 936), "\"Massive Ordnance Air Blast\": it bursts just above the ground", F_MED(28), INK, a)
    text(d, (x0, 970), "and its blast spreads sideways. It is not a penetrator.", F_MED(28), INK, a)
    text(d, (x0, 1016), "The valley and this drop are invented. Nobody is modelled.", F_MED(26), DIM, a)
    base.alpha_composite(ov)
    return base.convert("RGB")

def poly(d, pts, color, a, width=3, dash=False):
    pts = [p for p in pts]
    if len(pts) < 3:
        return
    c = (*color, int(255 * a)); loop = pts + [pts[0]]
    if dash:
        for k in range(0, len(loop) - 1, 2):
            d.line([loop[k], loop[k + 1]], fill=c, width=width)
    else:
        d.line(loop, fill=c, width=width, joint="curve")

RING_TXT = {"r10": ("10 psi", "HEAVY BUILDINGS BADLY DAMAGED"), "r5": ("5 psi", "MOST BUILDINGS COLLAPSE"), "r2": ("2 psi", "ROOFS AND WALLS BROKEN"), "r1": ("1 psi", "WINDOWS BROKEN")}
RING_COL = {"r10": RED, "r5": RED, "r2": AMBER, "r1": AMBER}

def reach_overlay(d, i, n, m, info):
    an = m["anchors"]; P = lambda q: (q[0] * W, q[1] * H); N = info["NRING"]; tb = m["tb"]; rf = m["front"]; pre, one = info["REACH"]
    rad = {"r10": info["R_10"], "r5": info["R_5"], "r2": info["R_2"], "r1": info["R_1"]}; tf = lambda r: float(np.interp(r, [q[0] for q in info["FRONT"]], [q[1] for q in info["FRONT"]]))
    out = 1 - ease((i - (n - 9)) / 8.0)
    for k in ("r1", "r2", "r5", "r10"):
        a = ease((tb - tf(rad[k])) / 0.12) * out
        if a <= 0:
            continue
        pts = [P(an["%s_%02d" % (k, j)]) for j in range(N)]; poly(d, pts, RING_COL[k], a * 0.9, 3 if k in ("r1", "r2") else 4)
        j0, side = {"r10": (25, -1), "r5": (36, 1), "r2": (1, 1), "r1": (44, 1)}[k]; q = pts[j0]; big, small = RING_TXT[k]; anc = "la" if side > 0 else "ra"      # each ring's label on a different side
        text(d, (q[0] + side * 16, q[1] + 2), "%s  ·  %d m" % (big, R(rad[k])), F_TITLE(40), RING_COL[k], a, anchor=anc); text(d, (q[0] + side * 16, q[1] + 48), small, F_SEMI(22), INK, a, anchor=anc, tracking=2)
    if "f_00" in an and rf > 3.0:                                      # the front itself
        a = (1 - ease((rf - 620.0) / 200.0)) * out; poly(d, [P(an["f_%02d" % j]) for j in range(N)], WHITE, a * 0.85, 3)
    readout(d, "AFTER THE BURST", "%.2f s" % max(tb, 0.0), ease((i - 2) / 6.0), INK, "BLAST FRONT AT %d m" % R(rf) if 0 < rf < 900 else "SEEN FROM ABOVE")
    a1 = ease((i - 3) / 8.0) * (1 - ease((tb - 1.55) / 0.2)); a2 = ease((tb - 1.9) / 0.25) * out
    if a1 > 0:
        lower(d, "HOW FAR DOES THE BLAST REACH?", "Peak pressure, calculated for open ground  ·  white: the blast front  ·  colours: 10, 5, 2 and 1 psi", a1)
    if a2 > 0:
        lower(d, "AND A MILE AWAY?", "About %.1f psi: a bang, perhaps cracked glass  ·  not the \"one-mile blast radius\" of many reports" % info["PSI_MILE"], a2)
    text(d, (W - 64, 60), "SLOWED 1.7 TIMES" if i < pre + one else "REAL TIME x 1.2", F_SEMI(26), DIM, 1.0, anchor="ra", tracking=3)
    text(d, (W - 64, 94), "PRESSURES ARE CALCULATED (KINNEY-GRAHAM), NOT MEASURED", F_SEMI(22), DIM, 1.0, anchor="ra", tracking=2)

def overlay_for(shot, i, n, m, info, hold=None):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    t = m["t"]; an = m.get("anchors", {}); P = lambda q: (q[0] * W, q[1] * H)
    tag(d, ease(i / 8.0) if shot == "approach" else 1.0)
    io = ease((i - 5) / 9.0) * (1 - ease((i - (n - 7)) / 7.0))
    seen = lambda q: 0.04 < q[0] < 0.96 and 0.08 < q[1] < 0.86
    if shot == "approach":
        lower(d, "MC-130 HERCULES", "About 6,100 m (20,000 ft) up, ramp open  ·  the bomb rides on a platform in the hold  ·  the height is not published", io)
        a = ease((m.get("open", 0) - 0.6) / 0.3) * (1 - ease((i - (n - 10)) / 7.0))
        if a > 0 and seen(an["chute"]):
            label(d, *P(an["chute"]), "PARACHUTE", "IT WILL PULL THE LOAD OUT", AMBER, a, dx=-130, dy=-150)
    elif shot == "intro":
        lower(d, "WHAT IT DROPS: GBU-43/B MOAB", "Massive Ordnance Air Blast  ·  9.2 m long, 1.03 m across, 9,800 kg  ·  more than four fifths of it is explosive", io)
        A = lambda k: ease((i - 8 - 8 * k) / 8.0) * (1 - ease((i - (n - 7)) / 6.0)); px = {k: P(q) for k, q in an.items()}
        dim_line(d, (px["tail"][0], px["top"][1] - 112), (px["nose"][0], px["top"][1] - 112), "9.2 m  ·  9,800 kg", A(0))
        for k, (key, big, small, col, ex, ey) in enumerate((("fin", "LATTICE FINS", "FOUR OF THEM STEER IT", AMBER, -90, -70), ("wing", "FIXED WINGS", "", AMBER, 180, 110),
                                                         ("cfill", "8,500 kg OF H6 EXPLOSIVE", "IN A THIN ALUMINIUM CASE", RED, 150, -115), ("cfuze", "FUZE AT THE NOSE", "FIRES JUST ABOVE THE GROUND", RED, 60, 140),
                                                         ("cbox", "GUIDANCE", "GPS, INERTIAL, FIN DRIVES", RED, 60, 140))):
            label(d, *px[key], big, small, col, A(k + 1), dx=ex, dy=ey)
        text(d, (W - 64, 60), "THE INSIDE IS A DIAGRAM, NOT A DRAWING OF THE REAL BOMB", F_SEMI(22), DIM, A(3), anchor="ra", tracking=2)
    elif shot == "release":
        tau = m.get("tau", -1.0); a1 = ease((i - 4) / 8.0) * (1 - ease((tau - 0.25) / 0.25)); a2 = ease((tau - 0.6) / 0.25) * (1 - ease((i - (n - 8)) / 7.0))
        if a1 > 0:
            lower(d, "PULLED OUT BY PARACHUTE", "The parachute drags platform, cradle and bomb back along the floor and off the ramp", a1)
        if a2 > 0:
            lower(d, "THE BOMB LEAVES ITS CRADLE", "Freed at once, it falls without a parachute  ·  its four lattice fins swing out and begin to steer  ·  half speed", a2)
            readout(d, "AFTER RELEASE", "%.2f s" % max(t, 0.0), a2)
        a = ease((m.get("fins", 0) - 0.5) / 0.3) * (1 - ease((i - (n - 10)) / 7.0))
        if a > 0 and seen(an["fins"]):
            callout(d, *P(an["fins"]), "LATTICE FINS", "OUT AND STEERING", AMBER, a, dx=120, dy=-170)
    elif shot == "fall":
        readout(d, "ABOVE THE VALLEY FLOOR", "{:,} m".format(int(round(max(m.get("alt", 0), 0.0), -1))), 1.0, AMBER, "{:,} km/h  ·  {:d}° DOWN".format(KMH(m.get("v", 0)), round(m.get("dive", 0))))
        lower(d, "GUIDED ALL THE WAY DOWN", "Released about %.1f km short, it falls for %d s  ·  GPS and inertial guidance work the fins  ·  speed and path are calculated" % (info["THROW"] / 1000.0, round(info["TAU_HIT"])), io)
        a = ease((i - 22) / 10.0) * (1 - ease((i - (n - 24)) / 10.0))
        if a > 0 and seen(an["cave"]):
            callout(d, *P(an["cave"]), "TARGET", "TUNNEL MOUTHS AT THE FOOT OF THE SLOPE", RED, a, dx=140, dy=-150)
    elif shot == "strike":
        tb = t; pre, one = info["STRIKE"]
        readout(d, "AFTER THE BURST", "%.1f s" % max(tb, 0.0), ease((i - 2) / 6.0), INK, "SLOWED 1.7 TIMES" if i < pre + one else "REAL TIME x 1.8")
        a1 = ease((i - 3) / 8.0) * (1 - ease((tb - 0.9) / 0.2)); a2 = ease((tb - 1.2) / 0.25) * (1 - ease((tb - 4.6) / 0.3)); a3 = ease((tb - 5.0) / 0.3) * (1 - ease((i - (n - 10)) / 8.0))
        if a1 > 0:
            lower(d, "TWO METRES ABOVE THE GROUND", "The fuze fires it about 6 ft up (as reported), so that the blast goes outward and not into a crater", a1)
        if a2 > 0:
            lower(d, "8.5 TONNES OF EXPLOSIVE", "A fireball about %d m across  ·  the blast front crosses the valley faster than sound, lifting dust as it goes" % round(info["FB_D"], -1), a2)
        if a3 > 0:
            lower(d, "THE CLOUD CLIMBS", "Hot gas rises on a stem of dust, as in the film released of the 2017 strike  ·  its size and speed here are staged", a3)
    elif shot == "reach":
        reach_overlay(d, i, n, m, info)
    elif shot == "after":
        a0 = ease((i - 14) / 10.0) * (1 - ease((i - (n - 14)) / 10.0)); pts = [P(an["r5_%02d" % j]) for j in range(info["NRING"])]; poly(d, pts, RED, a0 * 0.8, 3, dash=True)
        q = pts[40]; text(d, (q[0] + 14, q[1] + 6), "5 psi  ·  %d m" % R(info["R_5"]), F_TITLE(36), RED, a0)
        for k, (key, big, small, col, ex, ey) in enumerate((("flat", "FLATTENED", "INSIDE THE 5 psi LINE", RED, -170, 40), ("hurt", "ROOFS GONE, WALLS BREACHED", "2 TO 5 psi", AMBER, -120, 50),
                                                         ("ok", "STILL STANDING", "UNDER 2 psi", INK, 130, 110), ("cave", "TUNNEL MOUTHS", "BURIED UNDER FALLEN ROCK (STAGED)", RED, 190, -120))):
            a = ease((i - 22 - 9 * k) / 9.0) * (1 - ease((i - (n - 14)) / 10.0))
            if a > 0 and key in an and seen(an[key]):
                label(d, *P(an[key]), big, small, col, a, dx=ex, dy=ey)
        lower(d, "A MINUTE LATER", "Hardly a crater: the ground is burnt, not dug out  ·  what still stands follows the calculated pressure", ease((i - 10) / 12.0) * (1 - ease((i - (n - 10)) / 8.0)))
    return ov

def summary_frame(bg, i, n, info):
    frame = bg.copy(); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov); t = i / FPS; tag(d, 1.0)
    text(d, (120, 140), "GBU-43/B MOAB", F_TITLE(80), INK, ease((t - 0.1) / 0.5))
    a = ease((t - 0.4) / 0.5); d.rectangle([120, 248, 120 + int(1680 * a), 251], fill=(*AMBER, int(255 * a)))
    rows = [("WEIGHT", "9,800 kg (21,600 lb)  ·  8,500 kg of it explosive, in a thin aluminium case", DIM),
            ("YIELD", "about 11 tons of TNT  ·  15 built, one used", DIM),
            ("CALCULATED BLAST, OPEN GROUND:", "", AMBER),
            ("    10 psi", "out to about %d m   ·   heavy buildings badly damaged" % R(info["R_10"]), DIM),
            ("    5 psi", "out to about %d m   ·   most buildings collapse" % R(info["R_5"]), DIM),
            ("    2 psi", "out to about %d m   ·   roofs and walls broken" % R(info["R_2"]), DIM),
            ("    1 psi", "out to about %d m   ·   windows broken" % R(info["R_1"]), DIM),
            ("    AT ONE MILE", "about %.1f psi   ·   the \"one-mile blast radius\" is not borne out" % info["PSI_MILE"], RED),
            ("13 APRIL 2017", "Achin, Afghanistan: about twenty compounds destroyed, hardly any crater", DIM)]
    y = 278
    for r, (lab, val, col) in enumerate(rows):
        a = ease((t - 0.7 - 0.22 * r) / 0.45); dx = int((1 - a) * 24)
        text(d, (120 + dx, y + 6), lab, F_SEMI(30), col, a, tracking=3); text(d, (700 + dx, y - 1), val, F_MED(34), INK, a)
        y += 62
    a = ease((t - 3.4) / 0.6)
    text(d, (120, 872), "It is an air-blast bomb, not a penetrator: it can close the mouths of tunnels, but what it did inside the tunnels in 2017", F_MED(30), INK, a)
    text(d, (120, 910), "was never published. The real strike was after dark; this one is shown by day.", F_MED(30), INK, a)
    text(d, (120, 962), "Pressures by the Kinney-Graham fit for an 11-ton TNT burst at the ground, at the air pressure of a valley 1,200 m up: estimates,", F_MED(26), DIM, a)
    text(d, (120, 998), "not measurements, and without the shelter of walls and slopes. What they do to buildings is general published guidance.", F_MED(26), DIM, a)
    frame.alpha_composite(ov)
    return frame

def build_audio(path, starts, metas, lens, total, info):
    """Recorded effects: four propellers, the locks and the rollers, cloth filling, rushing air, a large explosion with a long tail."""
    import gsfx as S
    S.DIR = os.environ.get("SFX_DIR") or os.path.join(HERE, "..", "c130-blu82", "sfx")
    if not all(os.path.exists(os.path.join(S.DIR, n_ + ".wav")) for n_ in B.SFX):
        print("NOTE: recorded effects not found in %s - no soundtrack effects; using the synthesized track" % S.DIR)
        m2 = dict(metas); m2["cutaway"] = metas["reach"]; s2 = dict(starts); s2["cutaway"] = starts["reach"]; l2 = dict(lens); l2["cutaway"] = lens["reach"]; i2 = dict(info); i2["CUT"] = info["REACH"]
        return B.build_audio_synth(path, s2, m2, l2, total, i2)
    gp = B.gp; mx = gp.Mix(total); T = {k: v / FPS for k, v in starts.items()}; L = {k: v / FPS for k, v in lens.items()}; when = B._when(metas, T)
    tick = lambda t, g=0.22: mx.add(t, gp.lp(gp.s_tick(), 3500, 1), g, 0.25)
    S.put(mx, 0.0, S.bed("drone", T["approach"] + 0.4, t0=6.0, fi=0.3, fo=0.5, level=0.07)); S.put(mx, 0.05, S.cut("boom_deep", 0.0, 2.0, speed=1.8, fo=1.0), 0.30)
    for k in range(len(SPECS)):
        tick(0.65 + 0.11 * k)
    for shot, t0, g in (("approach", 1.0, 1.0), ("release", 9.0, 0.9)):                         # four turboprops (the recording is played lower, for a bigger machine)
        S.put(mx, T[shot], S.bed("prop", L[shot] + 0.3, t0=t0, speed=0.72, fi=0.6, fo=0.35, lp=6000, level=0.085), g, -0.1); S.put(mx, T[shot], S.bed("prop", L[shot] + 0.3, t0=t0 + 7.0, speed=0.76, fi=0.6, fo=0.35, lp=6000, level=0.06), g, 0.25)
        if shot == "release":
            S.put(mx, T[shot], S.bed("flap", L[shot] + 0.3, t0=4.0, fi=0.6, fo=0.35, lp=3000, level=0.016), g, 0.35)
    tx = when("approach", lambda m: m.get("stage", 0) >= 1); tf = when("approach", lambda m: m.get("open", 0) > 0.05)
    if tx:
        S.put(mx, tx - 0.03, S.cut("latch", 1.9, 0.9), 0.35, 0.3); S.put(mx, tx + 0.2, S.cut("whoosh", 16.4, 1.6, fi=0.15, fo=0.5), 0.22, 0.3)
    if tf:
        S.put(mx, tf, S.cut("flap", 6.6, 2.4, speed=0.8, fi=0.04, fo=1.0), 0.50, 0.3); S.put(mx, tf + 0.5, S.bed("flap", max(T["approach"] + L["approach"] - tf - 0.2, 0.5), t0=4.0, fi=0.5, fo=0.35, lp=3000, level=0.016), 1.0, 0.35)
    S.put(mx, T["intro"], S.bed("drone", L["intro"], t0=22.0, fi=0.4, fo=0.4, level=0.065)); S.put(mx, T["intro"] + 0.05, S.cut("boom_deep", 0.0, 1.8, speed=1.8, fo=1.0), 0.22)
    for k in range(6):
        tick(T["intro"] + (8 + 8 * k) / FPS)
    t0 = when("release", lambda m: m["t"] >= 0.0); te = when("release", lambda m: m["tau"] >= 0.0); ts = when("release", lambda m: m.get("sep", 0) > 0.5); to = when("release", lambda m: m.get("fins", 0) > 0.05)
    if t0 and te:                                                                                # the locks, the rollers, out into the air
        S.put(mx, t0 - 0.04, S.cut("latch", 5.55, 1.3), 0.75); r = S.cut("roll", 3.0, te - t0 + 0.25, fi=0.15, fo=0.25, lp=5000); r *= np.linspace(0.4, 1.0, len(r))[:, None]; S.put(mx, t0, r, 0.6)
        S.put(mx, te - 0.1, S.cut("whoosh", 16.4, 3.6, fi=0.2, fo=0.8), 0.40, -0.2)
    if ts:
        S.put(mx, ts - 0.03, S.cut("latch", 1.9, 0.9), 0.40, 0.2)
    if to:
        S.put(mx, to, S.cut("latch", 9.1, 1.2), 0.38, 0.1)
    lf = L["fall"]; w = S.bed("wind", lf, t0=34.0, speed=1.5, fi=0.25, fo=0.03, level=0.11) * np.linspace(0.5, 1.25, int(lf * SR))[:, None]; S.put(mx, T["fall"], w)
    S.put(mx, T["fall"] + lf - 2.2, S.cut("whoosh", 32.6, 2.2, fi=0.6, fo=0.02), 0.55)
    tb = when("strike", lambda m: m["t"] >= 0.0); ls = L["strike"]; th = when("strike", lambda m: m.get("front", 0) >= info["CAM_DIST"])
    S.put(mx, T["strike"], S.bed("wind", ls, t0=4.0, fi=0.3, fo=0.5, level=0.035))
    if tb:                                                                                       # seen first; the sound of the front comes when it reaches the camera
        S.put(mx, tb, S.cut("boom_deep", 0.0, 8.0, speed=0.7, fo=3.0, drive=2.5), 0.30); tq = th or tb + 1.5
        S.put(mx, tq, S.cut("boom_real", 0.0, 3.1, speed=0.8, fo=0.8), 1.0); S.put(mx, tq, S.cut("boom_big", 0.0, 7.0, speed=0.8, fo=2.5), 0.85); S.put(mx, tq + 0.3, S.cut("debris", 0.0, 3.0, speed=0.8, fo=1.2), 0.30, 0.1)
        S.put(mx, tq + 0.2, S.bed("quake", max(T["strike"] + ls - tq - 0.2, 1.0), t0=20.0, fi=0.2, fo=2.5, lp=400, level=0.05)); S.put(mx, tq + 0.6, S.cut("treefall", 1.0, 3.0, speed=0.85, fi=0.05, fo=1.0), 0.25, -0.3)
    tc = T["reach"]; lc = L["reach"]; pre, one = info["REACH"]; tb2 = tc + pre / FPS
    S.put(mx, tc, S.bed("drone", lc, t0=30.0, fi=0.5, fo=0.8, level=0.05)); S.put(mx, tc, S.bed("wind", lc, t0=14.0, fi=0.4, fo=0.6, level=0.03))
    S.put(mx, tb2, S.cut("boom_real", 0.0, 5.0, speed=0.6, fo=1.6), 0.8); S.put(mx, tb2, S.cut("boom_big", 0.0, 8.0, speed=0.6, fo=3.0), 0.7); S.put(mx, tb2, S.cut("boom_deep", 0.0, 9.0, speed=0.6, fo=3.0, drive=3.0), 0.40)
    for k, rk in enumerate((info["R_10"], info["R_5"], info["R_2"], info["R_1"])):               # a tick as the front crosses each line
        tk = float(np.interp(rk, [q[0] for q in info["FRONT"]], [q[1] for q in info["FRONT"]])); tick(tb2 + tk * 40.0 / FPS, 0.28)
    S.put(mx, tb2 + 0.8, S.cut("debris", 0.0, 5.0, speed=0.5, fo=2.0), 0.28, 0.1)
    ta = T["after"]; la_ = L["after"] + L["summary"]; S.put(mx, ta, S.bed("wind", la_, t0=6.0, fi=0.5, fo=1.0, level=0.05)); S.put(mx, ta + 1.0, S.cut("debris", 0.0, 3.0, speed=0.7, fi=0.2, fo=1.5), 0.08, 0.4)
    ts_ = T["summary"]; S.put(mx, ts_, S.bed("drone", L["summary"], t0=8.0, fi=0.6, fo=1.2, level=0.06)); S.put(mx, ts_ + 0.1, S.cut("boom_deep", 0.0, 2.0, speed=1.8, fo=1.0), 0.28)
    for r in range(9):
        tick(ts_ + 0.7 + 0.22 * r)
    S.finish(mx, total, path)

B.ORDER = ["card", "approach", "intro", "release", "fall", "strike", "reach", "after", "summary"]; B.N_SUMMARY = 264; B.HOLD = {}; B.SPECS = SPECS
B.tag = tag; B.card_frame = card_frame; B.overlay_for = overlay_for; B.summary_frame = summary_frame; B.build_audio = build_audio
B.GRADE = {"fall": 1.10, "strike": 1.12, "reach": 1.10, "after": 1.16}
B.FADES = {"card": (8, 6), "approach": (8, 5), "intro": (6, 6), "release": (6, 5), "fall": (5, 0), "strike": (0, 8), "reach": (8, 8), "after": (8, 0), "summary": (0, 16)}

if __name__ == "__main__":
    B.main()
