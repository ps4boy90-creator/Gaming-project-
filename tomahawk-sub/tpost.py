"""Finishing for the submarine-launched Tomahawk segment: upscale to 1080p, title card, captions and read-outs, a
closing table of the missile's figures, synthesized sound, encode.

  python3 tpost.py <frames_root> <out.mp4> [--draft]
"""
import os, sys, json, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "blackhawk-mk77"))
import post as gp
from post import W, H, FPS, SR, AMBER, RED, INK, DIM, PANEL, F_TITLE, F_SEMI, F_MED, ease, text, shadowed, lower, callout
from npost import readout, dashed, _mod, s_roar, s_crackle

ORDER = ["card", "depth", "hatch", "eject", "broach", "wings", "boost", "landfall", "cruise", "terminal", "impact", "radius", "after", "summary"]
N_SUMMARY = 192
SPECS = [("MISSILE", "UGM-109E Tomahawk Block IV"), ("SIZE", "5.56 m long  ·  0.52 m wide  ·  2.67 m span"), ("WEIGHT", "1,315 kg  ·  1,588 kg with its booster"), ("SPEED", "about 880 km/h, 30–50 m above the ground"),
         ("RANGE", "about 1,600 km"), ("WARHEAD", "310 kg  ·  about 120 kg of explosive"), ("LAUNCHED FROM", "a Los Angeles-class submarine")]
TABLE = [("LENGTH", "5.56 m  ·  6.25 m with the booster"), ("DIAMETER  ·  WINGSPAN", "0.52 m  ·  2.67 m"), ("WEIGHT", "1,315 kg  ·  1,588 kg with the booster"), ("BOOSTER", "solid rocket, about 26.7 kN for 12 s"),
         ("CRUISE", "turbofan  ·  about 880 km/h  ·  30–50 m above the ground"), ("RANGE", "about 1,600 km"), ("GUIDANCE", "inertial, GPS, terrain and scene matching  ·  about 10 m"),
         ("WARHEAD", "WDU-36/B  ·  310 kg with about 120 kg of PBXN-107"), ("BLAST (ESTIMATE)", "concrete buildings ≈ 18 m  ·  5 psi ≈ 35 m")]

def tag(d, a=1.0):
    text(d, (64, 54), "EXPLOSION COMPARISON", F_SEMI(30), INK, a, tracking=4)
    d.rectangle([64, 96, 64 + 54, 100], fill=(*AMBER, int(255 * a)))
    text(d, (130, 84), "08  ·  TOMAHAWK CRUISE MISSILE  ·  SUBMARINE LAUNCH", F_MED(26), DIM, a, tracking=2)

def card_frame(img, i, n):
    base = Image.new("RGBA", (W, H), (*PANEL, 255))
    base.paste(img.convert("RGB").resize((W // 2, H), Image.LANCZOS), (0, 0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    grad = Image.linear_gradient("L").rotate(90, expand=True).resize((90, H))
    seam = Image.new("RGBA", (90, H), (*PANEL, 255)); seam.putalpha(grad.point(lambda v: 255 - v))
    base.alpha_composite(seam.transpose(Image.FLIP_LEFT_RIGHT), (W // 2 - 90, 0))
    t = i / FPS; x0 = W // 2 + 96
    text(d, (x0, 150), "EXPLOSION COMPARISON  ·  08", F_SEMI(30), DIM, ease((t - 0.10) / 0.5), tracking=5)
    a = ease((t - 0.20) / 0.5); text(d, (x0 + int((1 - a) * 40), 200), "TOMAHAWK", F_TITLE(170), INK, a)
    a = ease((t - 0.35) / 0.5); text(d, (x0 + int((1 - a) * 40), 420), "FROM A SUBMARINE TO A FACTORY IN THE DESERT", F_TITLE(40), AMBER, a, tracking=1)
    a = ease((t - 0.45) / 0.5); d.rectangle([x0, 500, x0 + int(820 * a), 503], fill=(*AMBER, int(255 * a)))
    y = 538
    for k, (lab, val) in enumerate(SPECS):
        a = ease((t - 0.65 - 0.12 * k) / 0.45); dx = int((1 - a) * 28); hot = lab == "WARHEAD"
        text(d, (x0 + dx, y), lab, F_SEMI(31), RED if hot else DIM, a, tracking=3)
        text(d, (x0 + 280 + dx, y - 4), val, F_MED(36), INK, a)
        y += 60
    text(d, (x0, 980), "Afghanistan has no coast. These missiles reach it from the Arabian Sea,", F_MED(28), DIM, ease((t - 1.9) / 0.6))
    text(d, (x0, 1016), "as they did in October 2001. The target and the place in this film are invented.", F_MED(28), DIM, ease((t - 1.9) / 0.6))
    base.alpha_composite(ov)
    return base.convert("RGB")

def overlay_for(shot, i, n, m, info):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    t = m["t"]; an = m.get("anchors", {}); P = lambda q: (q[0] * W, q[1] * H)
    tag(d, ease(i / 8.0) if shot == "depth" else 1.0)
    io = ease((i - 5) / 9.0) * (1 - ease((i - (n - 7)) / 7.0))
    if shot == "depth":
        lower(d, "ARABIAN SEA", "A Los Angeles-class attack submarine  ·  110 m long  ·  twelve Tomahawk tubes in the bow", io)
        a = ease((i - 30) / 8.0) * (1 - ease((i - (n - 8)) / 7.0))
        if a > 0 and 0.05 < an["tubes"][0] < 0.95:
            callout(d, *P(an["tubes"]), "LAUNCH TUBES", "TWELVE, UPRIGHT, AHEAD OF THE SAIL", AMBER, a, dx=60, dy=-170)
    elif shot == "hatch":
        lower(d, "A TUBE DOOR OPENS", "Each tube holds one missile sealed in a capsule  ·  the submarine stays under water and keeps moving", io)
    elif shot == "eject":
        readout(d, "SLOW MOTION", "T + %04d ms" % max(0, round(t * 1000)), ease((i - 2) / 6.0))
        a1 = ease((i - 4) / 8.0) * (1 - ease((t - info["T_IGN"] + 0.03) / 0.06)); a2 = ease((t - info["T_IGN"] - 0.04) / 0.08) * (1 - ease((i - (n - 8)) / 7.0))
        if a1 > 0:
            lower(d, "THROWN OUT BY GAS", "A gas generator in the capsule fires and pushes the missile up out of the tube", a1)
        if a2 > 0:
            lower(d, "THE BOOSTER LIGHTS UNDER WATER", "Clear of the submarine, the rocket motor ignites and steers the missile to the surface", a2)
    elif shot == "broach":
        readout(d, "HEIGHT", "%d m" % max(0, round(m.get("alt", 0))), ease((t - info["T_BROACH"]) / 0.2), AMBER, "%d km/h" % round(m.get("v", 0) * 3.6))
        a1 = ease((i - 3) / 8.0) * (1 - ease((t - info["T_SHROUD"] + 0.15) / 0.15)); a2 = ease((t - info["T_SHROUD"]) / 0.15) * (1 - ease((i - (n - 8)) / 7.0))
        if a1 > 0:
            lower(d, "OUT OF THE SEA", "The rocket motor gives about 26.7 kN of thrust for about 12 seconds", a1)
        if a2 > 0:
            lower(d, "COVERS OFF, FINS OUT", "The shrouds round the tail are thrown off and three fins swing out in a quarter of a second", a2)
    elif shot == "wings":
        readout(d, "HEIGHT", "%d m" % round(m.get("alt", 0)), 1.0, AMBER, "%d km/h" % round(m.get("v", 0) * 3.6))
        lower(d, "WINGS OUT", "Once it is fast enough the inlet cover drops away and the wings swing out of their slots  ·  2.67 m across", io)
    elif shot == "boost":
        readout(d, "HEIGHT", "%d m" % round(m.get("alt", 0)), 1.0, AMBER, "%d km/h" % round(m.get("v", 0) * 3.6))
        a1 = ease((i - 3) / 8.0) * (1 - ease((t - info["T_JETT"] + 0.2) / 0.2)); a2 = ease((t - info["T_JETT"]) / 0.2) * (1 - ease((i - (n - 8)) / 7.0))
        if a1 > 0:
            lower(d, "BURN-OUT", "About 14 seconds after launch the rocket motor is spent", a1)
        if a2 > 0:
            lower(d, "BOOSTER DROPPED  ·  JET ENGINE STARTS", "A small turbofan of about 3 kN thrust carries it the rest of the way", a2)
            if 0.04 < an["booster"][0] < 0.96 and 0.04 < an["booster"][1] < 0.9 and t < info["T_JETT"] + 1.6:
                callout(d, *P(an["booster"]), "ROCKET MOTOR", "FALLS INTO THE SEA", AMBER, a2 * (1 - ease((t - info["T_JETT"] - 1.3) / 0.3)), dx=-60, dy=150)
    elif shot == "landfall":
        readout(d, "COAST", "%.1f km" % max(m.get("coast", 0) / 1000.0, 0.0), 1.0, AMBER, "880 km/h  ·  30 m UP")
        lower(d, "TOWARDS THE COAST", "About {:,} km to fly, some {:d} minutes  ·  the way to Afghanistan lies across Pakistan".format(int(round(info["ROUTE_KM"], -2)), int(round(info["FLIGHT_MIN"], -1))), io)
    elif shot == "cruise":
        readout(d, "ABOVE THE GROUND", "%d m" % round(m.get("agl", 0)), 1.0, AMBER, "%d km/h" % round(m.get("v", 0) * 3.6))
        lower(d, "FOLLOWING THE GROUND", "A radar altimeter, stored terrain maps and GPS keep it low  ·  30 to 50 m over level country, more over ridges", io)
    elif shot == "terminal":
        readout(d, "HEIGHT", "%d m" % round(m.get("alt", 0)), 1.0, AMBER, "DIVE  %d°" % max(0, round(m.get("dive", 0))))
        lower(d, "THE DIVE", "After a climb it tips over on to the target  ·  GPS and scene matching bring it within about 10 m", io)
        a = ease((i - 30) / 10.0) * (1 - ease((i - (n - 30)) / 10.0))
        if a > 0 and 0.05 < an["target"][0] < 0.95 and 0.08 < an["target"][1] < 0.85:
            callout(d, *P(an["target"]), "TARGET", "A FACTORY HALL, 24 m BY 12 m", RED, a, dx=140, dy=-150)
    elif shot == "impact":
        readout(d, "SLOW MOTION", "T + %03d ms" % max(0, round(t * 1000)), ease((i - 2) / 6.0), INK, "310 kg WARHEAD  ·  ≈ 120 kg OF EXPLOSIVE")
        lower(d, "THROUGH THE ROOF", "The fuze waits until the warhead is inside  ·  roof and walls are blown outwards", ease((i - 16) / 10.0) * (1 - ease((i - (n - 12)) / 10.0)))
    elif shot == "radius":
        a0 = ease((t - 0.25) / 0.3); a1 = ease((t - 0.9) / 0.3)
        text(d, (W - 64, 150), "TOMAHAWK", F_TITLE(100), RED, 1.0, anchor="ra"); text(d, (W - 64, 268), "≈ 120 kg OF EXPLOSIVE", F_SEMI(32), INK, 1.0, anchor="ra", tracking=3)
        ps = [P(q) for q in m.get("path_struct", [])]; pb = [P(q) for q in m.get("path_blast", [])]
        if a0 > 0 and len(ps) > 2:
            d.line([(x, y + 2) for x, y in ps], fill=(0, 0, 0, int(120 * a0)), width=7); d.line(ps, fill=(*RED, int(235 * a0)), width=5)
            callout(d, *P(an["struct"]), "≈ %d m" % round(info["R_STRUCT"]), "CONCRETE BUILDINGS DESTROYED", RED, a0, dx=110, dy=140)
        if a1 > 0 and len(pb) > 2:
            dashed(d, pb, (*AMBER, int(235 * a1)), 4)
            callout(d, *P(an["blast"]), "≈ %d m" % round(info["R_BLAST"]), "34 kPa (5 psi) BLAST", AMBER, a1, dx=-400, dy=-70)
        lower(d, "HOW FAR IT REACHES", "A little more than a 500 lb Mk 82 bomb (16 m and 31 m)  ·  scaled from it by the cube root of the filling (estimate)", ease((t - 0.5) / 0.3))
    elif shot == "after":
        a = ease((i - 14) / 10.0) * (1 - ease((i - (n - 14)) / 10.0))
        if a > 0:
            callout(d, *P(an["hall"]), "THE HALL", "ROOF AND WALLS GONE  ·  FRAME THROWN DOWN", RED, a, dx=-560, dy=-300)
        lower(d, "HALF A MINUTE LATER", "One missile on one light building  ·  the yard wall, the chimney and the office still stand", ease((i - 10) / 12.0) * (1 - ease((i - (n - 10)) / 8.0)))
    return ov

def summary_frame(bg, i, n, info):
    frame = bg.copy(); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov); t = i / FPS; tag(d, 1.0)
    text(d, (120, 160), "THE TOMAHAWK IN NUMBERS", F_TITLE(80), INK, ease((t - 0.1) / 0.5))
    a = ease((t - 0.4) / 0.5); d.rectangle([120, 270, 120 + int(1680 * a), 273], fill=(*AMBER, int(255 * a)))
    y = 300
    for r, (lab, val) in enumerate(TABLE):
        a = ease((t - 0.7 - 0.20 * r) / 0.45); dx = int((1 - a) * 24)
        text(d, (120 + dx, y + 6), lab, F_SEMI(30), RED if lab.startswith(("WARHEAD", "BLAST")) else DIM, a, tracking=3); text(d, (620 + dx, y - 2), val, F_MED(40), INK, a)
        y += 66
    a = ease((t - 3.0) / 0.6)
    text(d, (120, 920), "In this film: about {:,} km from the Arabian Sea in about {:d} minutes. On 7 October 2001 American and British".format(int(round(info["ROUTE_KM"], -2)), int(round(info["FLIGHT_MIN"], -1))), F_MED(30), INK, a)
    text(d, (120, 958), "ships and submarines fired about fifty Tomahawks at targets in Afghanistan this way.", F_MED(30), INK, a)
    text(d, (120, 1006), "Blast radii are scaled from published Mk 82 figures and are estimates. Launch depth, climb and dive profile are illustrative.", F_MED(26), DIM, a)
    frame.alpha_composite(ov)
    return frame

# ------------------------------------------------------------------ sound
def s_under(dur, seed=5):
    """Under water: a deep, slow rumble with a faint hum of machinery."""
    n = int(dur * SR); t = np.arange(n) / SR
    return gp.lp(gp.noise(n), 90, 3) * 5.0 * _mod(n, 0.6, 0.35, seed) + 0.10 * np.sin(2 * np.pi * 58 * t) + 0.05 * np.sin(2 * np.pi * 116.5 * t) + gp.bp(gp.noise(n), 300, 900) * 0.10 * _mod(n, 1.5, 0.5, seed + 1)

def s_bubbles(dur, rate=60.0, seed=3):
    """Gas rushing out under water: a muffled roar with many small rising 'bloops'."""
    r = np.random.default_rng(seed); n = int(dur * SR); x = gp.lp(gp.noise(n), 420, 2) * 3.0 * np.minimum(1.0, np.arange(n) / (0.05 * SR)) * np.exp(-np.arange(n) / (0.6 * dur * SR))
    for _ in range(int(rate * dur)):
        i0 = int(r.uniform(0, max(dur - 0.12, 0.01)) * SR); m = int(r.uniform(0.03, 0.10) * SR); tt = np.arange(m) / SR; f0 = r.uniform(180, 700)
        x[i0:i0 + m] += np.sin(2 * np.pi * (f0 + f0 * 1.2 * tt / (m / SR)) * tt) * np.hanning(m) * r.uniform(0.15, 0.5)
    return x

def s_rocket(dur, seed=2, muffled=False):
    """Solid rocket motor close by: a hard, crackling roar."""
    n = int(dur * SR); x = gp.lp(gp.noise(n), 220, 2) * 4.5 * _mod(n, 9.0, 0.45, seed) + gp.bp(gp.noise(n), 300, 3200) * 1.3 * _mod(n, 28.0, 0.7, seed + 1) + gp.hp(gp.noise(n), 3500) * 0.22 * _mod(n, 40.0, 0.8, seed + 2)
    return gp.lp(x, 500, 2) * 1.6 if muffled else x

def s_jet(dur, seed=3):
    """A small turbofan passing close: thin whine over a rush of air."""
    n = int(dur * SR); t = np.arange(n) / SR
    return gp.bp(gp.noise(n), 400, 3200) * 0.9 * _mod(n, 2.0, 0.25, seed) + gp.lp(gp.noise(n), 160, 2) * 1.4 + 0.07 * np.sin(2 * np.pi * 3400 * t + 2 * np.sin(2 * np.pi * 0.9 * t)) + 0.04 * np.sin(2 * np.pi * 5100 * t)

def s_splash():
    n = int(2.4 * SR); t = np.arange(n) / SR
    return gp.hp(gp.lp(gp.noise(n), 6000, 1), 500) * 2.2 * np.minimum(1.0, t / 0.03) * np.exp(-t / 0.55) + gp.lp(gp.noise(n), 200, 2) * 3.0 * np.exp(-t / 0.25)

def s_blast(scale):
    n = int((3.5 + scale) * SR); t = np.arange(n) / SR
    crack = gp.noise(n) * np.exp(-t / 0.012) * 3.0
    body = gp.lp(gp.noise(n), 160 / scale, 3) * 9.0 * np.minimum(1.0, t / 0.01) * np.exp(-t / (0.55 * scale))
    tail = gp.bp(gp.noise(n), 60, 500) * 1.6 * np.exp(-t / (1.3 * scale)) * _mod(n, 3.0, 0.4, 17)
    sub = np.sin(2 * np.pi * np.cumsum(np.linspace(55 / scale, 24, n)) / SR) * 1.4 * np.exp(-t / (0.5 * scale))
    return crack + body + tail + sub

def build_audio(path, starts, metas, lens, total, info):
    mx = gp.Mix(total); T = {k: v / FPS for k, v in starts.items()}; L = {k: v / FPS for k, v in lens.items()}
    def when(shot, pred):
        m = metas[shot]
        for i in sorted(int(k) for k in m):
            if pred(m[str(i)]):
                return T[shot] + i / FPS
        return None
    mx.add(0.0, gp.s_drone(T["depth"] + 0.2), 0.5); mx.add(0.05, gp.s_thud(1.2), 0.5)
    for k in range(len(SPECS)):
        mx.add(0.65 + 0.12 * k, gp.s_tick(), 0.35, 0.3)
    lu = L["depth"] + L["hatch"] + L["eject"]; mx.add(T["depth"], s_under(lu, 5), 0.55, -0.15); mx.add(T["depth"], s_under(lu, 9), 0.55, 0.15)
    mx.add(T["hatch"] + 0.25, gp.s_thud(0.8), 0.5, 0.1); mx.add(T["hatch"] + 1.9, gp.s_thud(1.1), 0.6, 0.1)
    te = when("eject", lambda m: m["t"] >= 0.0); ti = when("eject", lambda m: m["t"] >= info["T_IGN"])
    if te:
        mx.add(te, gp.s_thud(1.6), 0.9); mx.add(te, s_bubbles(T["broach"] - te, 70, 3), 0.55)
    if ti:
        mx.add(ti, s_rocket(T["broach"] - ti, 2, muffled=True), 0.5)
    tb = when("broach", lambda m: m["t"] >= info["T_BROACH"])
    mx.add(T["broach"], gp.s_wind(L["broach"]) * 0.12, 1.0, 0.0)
    if tb:
        mx.add(tb, s_splash(), 0.8); lr = T["wings"] - tb; r = s_rocket(lr, 4); n_ = len(r); r *= np.minimum(1.0, np.arange(n_) / (0.04 * SR)) * (0.55 + 0.45 * np.exp(-np.arange(n_) / (2.5 * SR)))   # it climbs away
        mx.add(tb, r, 0.75, 0.0)
    ts = when("broach", lambda m: m["t"] >= info["T_SHROUD"])
    if ts:
        mx.add(ts, gp.s_thud(0.5), 0.5, 0.2); mx.add(ts + 0.02, gp.s_ping(900, 0.25), 0.2, -0.2)
    mx.add(T["wings"], s_rocket(L["wings"], 6), 0.55); tw = when("wings", lambda m: m["t"] >= info["T_WINGS"])
    if tw:
        mx.add(tw, gp.s_thud(0.6), 0.6, 0.2); mx.add(tw + 0.5, gp.s_thud(0.45), 0.5, -0.2)
    tbo = when("boost", lambda m: m["t"] >= info["T_BURNOUT"] - 0.2); tj = when("boost", lambda m: m["t"] >= info["T_JETT"]); tg = when("boost", lambda m: m["t"] >= info["T_ENGINE"])
    if tbo:
        r = s_rocket(tbo - T["boost"] + 0.5, 8); n_ = len(r); r *= np.minimum(1.0, (n_ - np.arange(n_)) / (0.45 * SR)); mx.add(T["boost"], r, 0.55)
    mx.add(T["boost"], gp.s_wind(L["boost"]) * 0.30, 1.0, 0.0)
    if tj:
        mx.add(tj, gp.s_thud(0.9), 0.7)
    if tg:
        j = s_jet(T["boost"] + L["boost"] - tg, 3); j *= np.minimum(1.0, np.arange(len(j)) / (0.8 * SR)); mx.add(tg, j, 0.5)
    lc = L["landfall"] + L["cruise"]; mx.add(T["landfall"], s_jet(lc, 5), 0.50, -0.2); mx.add(T["landfall"], s_jet(lc, 7), 0.50, 0.2); mx.add(T["landfall"], gp.s_wind(lc) * 0.4, 1.0)
    mx.add(T["cruise"] - 0.3, gp.s_whoosh(0.7, 200, 1600, 0.8), 0.3)
    mx.add(T["terminal"], s_jet(L["terminal"], 9), 0.4); w = gp.s_whoosh(L["terminal"], 250, 2600, 0.95) * 1.0; mx.add(T["terminal"], w, 0.7)
    th = when("impact", lambda m: m["t"] >= 0)
    if th:
        mx.add(T["impact"], gp.s_whoosh(th - T["impact"] + 0.05, 600, 3000, 0.95), 0.6); mx.add(th, s_blast(1.11), 1.0, 0.0); mx.add(th + 0.25, gp.s_debris(4.0, 90, 2.2), 0.6, 0.2); mx.add(th + 0.1, gp.s_ring(3.0), 0.5)
    mx.add(T["radius"], s_blast(1.11), 0.62, 0.0); mx.add(T["radius"] + 0.3, gp.s_debris(3.0, 60, 1.8), 0.35, 0.0)
    ta = T["after"]; la = L["after"] + L["summary"]; mx.add(ta, gp.s_wind(la) * 0.14, 1.0, -0.1); mx.add(ta, s_roar(L["after"] + 1.0, 3) * 0.5, 0.35, 0.1); mx.add(ta, s_crackle(L["after"] + 1.0, 22.0, 7), 0.30, -0.1)
    ts_ = T["summary"]; mx.add(ts_, gp.s_drone(L["summary"]), 0.45); mx.add(ts_ + 0.1, gp.s_thud(1.2), 0.4)
    for r in range(len(TABLE)):
        mx.add(ts_ + 0.7 + 0.20 * r, gp.s_tick(), 0.3, 0.3)
    x = np.tanh(mx.b[: int(total * SR)] * 1.1)
    fo = int(0.8 * SR); x[-fo:] *= np.linspace(1, 0, fo)[:, None]
    x = x / (np.abs(x).max() + 1e-9) * 0.89
    with wave.open(path, "wb") as w_:
        w_.setnchannels(2); w_.setsampwidth(2); w_.setframerate(SR); w_.writeframes((x * 32767).astype("<i2").tobytes())

FADES = {"card": (8, 6), "depth": (8, 5), "hatch": (5, 4), "eject": (4, 3), "broach": (3, 5), "wings": (5, 4), "boost": (4, 8), "landfall": (8, 4), "cruise": (4, 6), "terminal": (6, 0), "impact": (0, 5), "radius": (4, 6), "after": (6, 0), "summary": (0, 16)}

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
            n = N_SUMMARY; metas[shot] = {}; bg = Image.blend(last.convert("RGB").filter(ImageFilter.GaussianBlur(14)), Image.new("RGB", (W, H), PANEL), 0.82).convert("RGBA")
        else:
            d1, f1, m1 = _load(root, shot); n = len(f1); metas[shot] = m1
        lens[shot] = n
        for k in range(n):
            if shot == "card":
                frame = card_frame(Image.open(os.path.join(d1, f1[k])), k, n).convert("RGBA")
            elif shot == "summary":
                a = ease(k / 14.0); frame = Image.blend(last, summary_frame(bg, k, n, info), a) if a < 1 else summary_frame(bg, k, n, info)
            else:
                frame = Image.open(os.path.join(d1, f1[k])).convert("RGB").resize((W, H), Image.LANCZOS).convert("RGBA")
                if shot == "after" and k == n - 1:
                    last = frame.copy()
                shadowed(frame, overlay_for(shot, k, n, m1[str(k)], info))
            fade = min(1.0, (k + 1) / fi if fi else 1.0, (n - k) / fo if fo else 1.0)
            if fade < 1.0:
                frame = Image.blend(Image.new("RGBA", frame.size, (0, 0, 0, 255)), frame, fade)
            frame.convert("RGB").save(os.path.join(stage, "m%05d.png" % g), compress_level=1); g += 1
        print("staged", shot, n); sys.stdout.flush()
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
