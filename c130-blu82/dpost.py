"""Finishing for the C-130 / BLU-82 segment: the Lancaster segments' finishing (../lancaster-tallboy/lpost.py: upscale,
encode) with this segment's title card, captions, circles, closing table and sound.

  python3 dpost.py <frames_root> <out.mp4> [--draft]
"""
import os, sys, math, wave
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "lancaster-tallboy"))
from PIL import Image, ImageDraw
import lpost as lp
from lpost import W, H, FPS, SR, AMBER, RED, INK, DIM, PANEL, F_TITLE, F_SEMI, F_MED, ease, text, lower, callout, callout_l, dim_line, ring, readout, MK84, gp, _mod

SPECS = [("BOMB", "BLU-82/B  ·  15,000 lb, the \"Daisy Cutter\""), ("SIZE", "11 ft 10 in (3.6 m) long  ·  54 in (1.37 m) across"), ("WEIGHT", "6,800 kg (15,000 lb)"), ("EXPLOSIVE", "5,715 kg (12,600 lb) of slurry"),
         ("FUZE", "on a 3 ft extender: it bursts above the ground"), ("CARRIED BY", "C-130 Hercules, pulled out by parachute"), ("FIRST USED", "23 March 1970  ·  South Vietnam")]
KMH = lambda v: int(round(v * 3.6, -1))

def tag(d, a=1.0):
    text(d, (64, 54), "EXPLOSION COMPARISON", F_SEMI(30), INK, a, tracking=4)
    d.rectangle([64, 96, 64 + 54, 100], fill=(*AMBER, int(255 * a)))
    text(d, (130, 84), "13  ·  BLU-82  ·  C-130 HERCULES", F_MED(26), DIM, a, tracking=2)

def card_frame(img, i, n):
    base = Image.new("RGBA", (W, H), (*PANEL, 255))
    base.paste(img.convert("RGB").resize((W // 2, H), Image.LANCZOS), (0, 0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    grad = Image.linear_gradient("L").rotate(90, expand=True).resize((90, H))
    seam = Image.new("RGBA", (90, H), (*PANEL, 255)); seam.putalpha(grad.point(lambda v: 255 - v))
    base.alpha_composite(seam.transpose(Image.FLIP_LEFT_RIGHT), (W // 2 - 90, 0))
    t = i / FPS; x0 = W // 2 + 96
    text(d, (x0, 130), "EXPLOSION COMPARISON  ·  13", F_SEMI(30), DIM, ease((t - 0.10) / 0.5), tracking=5)
    a = ease((t - 0.20) / 0.5); text(d, (x0 + int((1 - a) * 40), 190), "BLU-82/B", F_TITLE(150), INK, a)
    a = ease((t - 0.35) / 0.5); text(d, (x0 + int((1 - a) * 40), 400), "15,000 LB FROM A C-130 TO CLEAR A LANDING ZONE", F_TITLE(38), AMBER, a, tracking=1)
    a = ease((t - 0.45) / 0.5); d.rectangle([x0, 478, x0 + int(820 * a), 481], fill=(*AMBER, int(255 * a)))
    y = 512
    for k, (lab, val) in enumerate(SPECS):
        a = ease((t - 0.65 - 0.12 * k) / 0.45); dx = int((1 - a) * 28); hot = lab == "EXPLOSIVE"
        text(d, (x0 + dx, y), lab, F_SEMI(31), RED if hot else DIM, a, tracking=3)
        text(d, (x0 + 250 + dx, y - 4), val, F_MED(36), INK, a)
        y += 58
    a = ease((t - 1.7) / 0.6)
    text(d, (x0, 936), "Made to blow a helicopter landing zone out of jungle in one stroke:", F_MED(28), INK, a)
    text(d, (x0, 970), "Operation Commando Vault, South Vietnam, 1970 to 1972.", F_MED(28), INK, a)
    text(d, (x0, 1016), "The place and the drop are invented. The fall is calculated; the clearing is the published size.", F_MED(26), DIM, a)
    base.alpha_composite(ov)
    return base.convert("RGB")

def overlay_for(shot, i, n, m, info):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    t = m["t"]; an = m.get("anchors", {}); P = lambda q: (q[0] * W, q[1] * H)
    tag(d, ease(i / 8.0) if shot == "approach" else 1.0)
    io = ease((i - 5) / 9.0) * (1 - ease((i - (n - 7)) / 7.0))
    seen = lambda q: 0.04 < q[0] < 0.96 and 0.08 < q[1] < 0.86
    vh = round(info["V_HIT"]); rc = round(info["R_CLEAR"]); rs = round(info["R_STRIP"]); rb = round(info["R_BLAST"])
    if shot == "approach":
        lower(d, "LOCKHEED C-130B HERCULES", "6,000 ft above the ground at 150 knots  ·  ramp and door open, the extraction parachute streamed behind", io)
        a = ease((t - info["T_STREAM"][1] - 0.2) / 0.4) * (1 - ease((i - (n - 10)) / 7.0))
        if a > 0 and seen(an["chute"]):
            callout(d, *P(an["chute"]), "EXTRACTION PARACHUTE", "15 ft RING-SLOT  ·  IT WILL PULL THE LOAD OUT", AMBER, a, dx=-560, dy=190)
        a = ease((i - 12) / 10.0) * (1 - ease((i - (n - 10)) / 7.0))
        text(d, (W - 64, 60), "FOUR ALLISON T56 TURBOPROPS  ·  SPAN 132 ft 7 in (40.4 m)", F_SEMI(28), INK, a, anchor="ra", tracking=3)
        text(d, (W - 64, 98), "463rd TACTICAL AIRLIFT WING  ·  AIMED BY GROUND RADAR: THE CREW NEVER SEES THE TARGET", F_SEMI(24), DIM, a, anchor="ra", tracking=2)
    elif shot == "intro":
        lower(d, "BLU-82/B", "A thin steel tank of slurry explosive: all blast, almost no fragments, and no crater", io)
        A = lambda k: ease((i - 8 - 9 * k) / 8.0) * (1 - ease((i - (n - 7)) / 6.0)); px = {k: P(q) for k, q in an.items()}
        dim_line(d, (px["tail"][0], px["top"][1] - 130), (px["nose"][0], px["top"][1] - 130), "11 ft 10 in  ·  3.6 m  ·  6,800 kg", A(0))
        for k, (key, big, small, col, ex_, ey_, left) in enumerate((("case", "5,715 kg OF SLURRY", "IN A 1/4 in STEEL TANK", RED, -110, 240, True), ("ext", "3 ft FUZE EXTENDER", "IT TOUCHES FIRST: THE BURST IS ABOVE GROUND", AMBER, -30, -190, True),
                                                                 ("pack", "PARACHUTE PACK", "24 ft SLOTTED CANOPY", AMBER, -60, -150, True))):
            a = A(k + 1)
            if a > 0:
                (callout_l if left else callout)(d, *px[key], big, small, col, a, dx=ex_, dy=ey_)
        a = A(4)
        text(d, (W - 64, 880), "JEEP, 3.4 m", F_TITLE(48), INK, a, anchor="ra"); text(d, (W - 64, 940), "BEHIND IT, FOR SCALE", F_SEMI(30), INK, a, anchor="ra", tracking=3)
    elif shot == "release":
        a1 = ease((i - 4) / 8.0) * (1 - ease((t + 0.05) / 0.12)); a2 = ease((t - 0.25) / 0.2) * (1 - ease((i - (n - 8)) / 7.0))
        if a1 > 0:
            lower(d, "PULLED OUT BY PARACHUTE", "The locks are released  ·  the extraction parachute drags 20,000 lb down the rollers and off the ramp in %.1f s" % info["T_EXIT"], a1)
        if a2 > 0:
            lower(d, "THE BOMB LEAVES ITS CRADLE", "Its own parachute pulls it off the platform and swings it nose down  ·  cradle and platform fall away", a2)
            readout(d, "AFTER LEAVING THE RAMP", "%.2f s" % max(t, 0.0), a2)
    elif shot == "fall":
        readout(d, "ABOVE THE GROUND", "{:,} m".format(int(round(m.get("alt", 0), -1))), 1.0, AMBER, "{:,} km/h".format(KMH(m.get("v", 0))))
        lower(d, "NOSE DOWN AT {:,} km/h".format(KMH(info["V_HIT"])), "It falls for %d s under a 24 ft parachute and arrives at %d m/s  ·  published: 26 to 27 s and 338 ft/s (103 m/s)" % (round(info["TOF"]), vh), io)
        a = ease((i - 22) / 10.0) * (1 - ease((i - (n - 16)) / 10.0))
        if a > 0 and seen(an["probe"]):
            callout(d, *P(an["probe"]), "FUZE EXTENDER", "3 ft AHEAD OF THE BOMB", AMBER, a, dx=190, dy=-150)
    elif shot == "impact":
        td = t
        readout(d, "SLOW MOTION", "T + {:,} ms".format(max(0, int(round(td * 1000)))), ease((i - 2) / 6.0), INK, "6.8 t BOMB  ·  5,715 kg OF SLURRY")
        a1 = ease((i - 3) / 8.0) * (1 - ease((td + 0.03) / 0.05)); a2 = ease((td - 0.02) / 0.10) * (1 - ease((td - 1.35) / 0.2)); a3 = ease((td - 1.6) / 0.2) * (1 - ease((i - (n - 10)) / 8.0))
        if a1 > 0:
            lower(d, "INTO THE TREES", "It comes down through the canopy  ·  the extender touches the ground and fires the bomb three feet up", a1)
        if a2 > 0:
            lower(d, "5,715 kg OF SLURRY, ABOVE THE GROUND", "No crater: the blast goes outwards along the ground and takes the forest with it", a2)
        if a3 > 0:
            lower(d, "THE CLOUD", "A pale cloud climbs out of the forest: the aluminium in the slurry burns to white smoke", a3)
        a = ease((td - 2.6) / 0.3) * (1 - ease((i - (n - 12)) / 8.0))
        if a > 0 and seen(an["top"]):
            callout(d, *P(an["top"]), "100 m UP", "", AMBER, a, dx=230, dy=-40)
    elif shot == "radius":
        paths = m.get("paths", {}); A = lambda k: ease((i - 24 - 12 * k) / 10.0) * (1 - ease((i - (n - 8)) / 7.0))
        lower(d, "WHAT IT CLEARS", "An area about %d m across is cleared and the foliage burnt off to twice that (published)  ·  the 5 psi circle is scaled from the Mk 82's" % (2 * rc), io)
        for k, (key, col, big, small, dx, dy) in enumerate((("clear", RED, "CLEARED: %d m ACROSS" % (2 * rc), "PUBLISHED: ABOUT 260 ft", 190, -70), ("strip", AMBER, "FOLIAGE BURNT OFF", "TO ABOUT %d m FROM THE BURST" % rs, 50, 150), ("blast", INK, "5 psi BLAST", "TO ABOUT %d m, IN THE OPEN" % rb, 60, -90))):
            a = A(k)
            if key in paths:
                ring(d, paths[key], col, a, 5 if key == "clear" else 4, dash=key != "clear")
            if a > 0 and key in an and seen(an[key]):
                (callout_l if dx < 0 else callout)(d, *P(an[key]), big, small, col, a, dx=dx, dy=dy)
        a = A(3)
        if "rotor" in paths:
            ring(d, paths["rotor"], MK84, a, 4, dash=False)
        if a > 0 and seen(an["rotor"]):
            callout_l(d, *P(an["rotor"]), "A UH-1's ROTOR, 14.6 m", "FOR SCALE", MK84, a, dx=-70, dy=-190)
        text(d, (W - 64, 60), "SLOWED ABOUT 1.4 TIMES", F_SEMI(26), DIM, 1.0, anchor="ra", tracking=3)
    elif shot == "after":
        paths = m.get("paths", {}); a = ease((i - 18) / 10.0) * (1 - ease((i - (n - 14)) / 10.0))
        if a > 0 and seen(an["a"]) and seen(an["b"]):
            dim_line(d, P(an["a"]), P(an["b"]), "ABOUT %d m" % (2 * rc), a, RED, off=-58)
        if "rotor" in paths:
            ring(d, paths["rotor"], MK84, a * ease((i - 34) / 10.0), 4, dash=False)
        lower(d, "A LANDING ZONE", "Bare ground, stumps and trunks thrown outwards, no crater  ·  in 1970 two drops in five left room for one helicopter, as many for two or more", ease((i - 10) / 12.0) * (1 - ease((i - (n - 10)) / 8.0)))
    return ov

def summary_frame(bg, i, n, info):
    frame = bg.copy(); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov); t = i / FPS; tag(d, 1.0); v = round(info["V_HIT"])
    text(d, (120, 140), "BLU-82/B: THE NUMBERS", F_TITLE(80), INK, ease((t - 0.1) / 0.5))
    a = ease((t - 0.4) / 0.5); d.rectangle([120, 248, 120 + int(1680 * a), 251], fill=(*AMBER, int(255 * a)))
    rows = [("THE BOMB", "3.6 m long  ·  1.37 m across  ·  6,800 kg  ·  5,715 kg of slurry explosive", DIM),
            ("RELEASE", "6,000 ft above the ground at 150 knots, pulled out of a C-130B by parachute", DIM),
            ("THE FALL", "%d s from release (published: 26 to 27 s)  ·  %d m/s at the ground (published: 338 ft/s)" % (round(info["TOF"]), v), AMBER),
            ("FUZE", "on a 3 ft extender: the bomb bursts above the ground and leaves no crater", DIM),
            ("CLEARED", "about %d m across (published: 260 ft)  ·  stumps are left standing" % round(2 * info["R_CLEAR"]), RED),
            ("FOLIAGE BURNT", "out to about %d m from the burst (published: twice the usable radius)" % round(info["R_STRIP"]), DIM),
            ("5 psi BLAST", "to about %d m in the open (scaled from the Mk 82's)" % round(info["R_BLAST"]), DIM),
            ("AIMING", "by ground radar  ·  average miss 58 m in 1970", DIM),
            ("SAFE DISTANCE", "friendly troops no nearer than 1,500 m  ·  225 bombs were built", DIM)]
    y = 278
    for r, (lab, val, col) in enumerate(rows):
        a = ease((t - 0.7 - 0.22 * r) / 0.45); dx = int((1 - a) * 24)
        text(d, (120 + dx, y + 6), lab, F_SEMI(30), col, a, tracking=3); text(d, (620 + dx, y - 2), val, F_MED(38), INK, a)
        y += 62
    a = ease((t - 3.4) / 0.6)
    text(d, (120, 872), "It did not always work: of 107 drops counted in 1970, 17 left no usable zone, 44 room for one helicopter,", F_MED(30), INK, a)
    text(d, (120, 910), "36 for two and 10 for three or four.", F_MED(30), INK, a)
    text(d, (120, 962), "The place and the drop are invented. The fall is calculated; the 5 psi radius is scaled from the Mk 82's published one.", F_MED(26), DIM, a)
    text(d, (120, 998), "Sources: Project CHECO report 'Commando Vault' (1970); National Museum of the USAF; Air Force Armament Museum; AFI 11-231.", F_MED(26), DIM, a)
    frame.alpha_composite(ov)
    return frame

# ------------------------------------------------------------------ sound
def s_turboprops(dur, seed=3):
    """Four T56s at a constant 1,020 rpm: the four-blade propellers' 68 Hz note with its harmonics, turbine whine over it."""
    n = int(dur * SR); t = np.arange(n) / SR; x = np.zeros(n)
    for k, f in enumerate((68.0, 68.4, 67.7, 68.9)):
        for h_, g in ((1, 1.0), (2, 0.7), (3, 0.35), (4, 0.2)):
            x += g * np.sin(2 * np.pi * f * h_ * t + k * 1.1 + h_)
    whine = np.sin(2 * np.pi * 2300 * t + 3 * np.sin(2 * np.pi * 0.7 * t)) * 0.05
    return x * 0.10 * _mod(n, 1.2, 0.15, seed) + whine * _mod(n, 0.6, 0.2, seed + 2) + gp.lp(gp.noise(n), 260, 2) * 2.2 * _mod(n, 0.8, 0.25, seed + 1) + gp.bp(gp.noise(n), 400, 2600) * 0.6

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
    la = L["approach"]; ramp = np.minimum(1.0, np.arange(int((la + 0.4) * SR)) / (0.5 * SR)); mx.add(T["approach"], s_turboprops(la + 0.4, 3) * ramp, 0.55, -0.15); mx.add(T["approach"], s_turboprops(la + 0.4, 8) * ramp, 0.55, 0.15)
    ts_ = when("approach", lambda m: m.get("stream", 0) > 0.02)
    if ts_:
        mx.add(ts_, gp.s_whoosh(1.2, 300, 1500, 0.5), 0.4); mx.add(ts_ + 0.9, gp.s_thud(0.7), 0.5)
    mx.add(T["intro"], gp.s_drone(L["intro"]), 0.4); mx.add(T["intro"] + 0.05, gp.s_thud(0.8), 0.4)
    for k in range(5):
        mx.add(T["intro"] + (8 + 9 * k) / FPS, gp.s_tick(), 0.35, 0.3 - 0.12 * k)
    lr = L["release"]; mx.add(T["release"], s_turboprops(lr, 11) * 0.9, 0.5)
    tl_ = when("release", lambda m: m["t"] >= -info["T_EXIT"]); tr = when("release", lambda m: m["t"] >= 0.0); tc_ = when("release", lambda m: m["t"] >= info["T_SEP"])
    if tl_ and tr:
        mx.add(tl_, gp.lp(gp.noise(int((tr - tl_) * SR)), 180, 2) * 5.0 * np.linspace(0.3, 1.0, int((tr - tl_) * SR)), 0.6)       # the platform running down the rollers
    if tr:
        mx.add(tr, gp.s_thud(1.6), 1.0); mx.add(tr + 0.1, gp.s_whoosh(1.4, 250, 1400, 0.3), 0.4)
    if tc_:
        mx.add(tc_ + 0.3, gp.s_whoosh(0.8, 500, 2200, 0.4), 0.45); mx.add(tc_ + 0.9, gp.s_thud(0.9), 0.6)
    lf = L["fall"]; w = gp.s_wind(lf) * 0.6 * np.linspace(0.6, 1.0, int(lf * SR)); mx.add(T["fall"], w, 1.0); mx.add(T["fall"], gp.s_whoosh(lf, 250, 1600, 0.97), 0.5)
    tdet = when("impact", lambda m: m["t"] >= 0.0); mx.add(T["impact"], gp.s_wind(L["impact"]) * 0.12, 1.0)
    if tdet:
        mx.add(tdet, gp.s_boom(2.2, 2.5), 1.0); mx.add(tdet + 0.05, gp.s_boom(1.2, 1.2), 0.7); mx.add(tdet + 0.6, gp.s_debris(8.0, 70, 2.5), 0.55, 0.1); mx.add(tdet + 0.2, gp.s_roll(9.0) if hasattr(gp, "s_roll") else gp.s_wind(9.0), 0.5)
    tr_ = T["radius"]; mx.add(tr_, gp.s_wind(L["radius"]) * 0.10, 1.0); mx.add(tr_ + 0.05, gp.s_boom(1.8, 1.4), 0.85); mx.add(tr_ + 0.8, gp.s_debris(4.0, 50, 1.4), 0.45, -0.1)
    for k in range(4):
        mx.add(tr_ + (24 + 12 * k) / FPS, gp.s_tick(), 0.35, 0.2)
    ta = T["after"]; la_ = L["after"] + L["summary"]; mx.add(ta, gp.s_wind(la_) * 0.16, 1.0, -0.1)
    tsum = T["summary"]; mx.add(tsum, gp.s_drone(L["summary"]), 0.45); mx.add(tsum + 0.1, gp.s_thud(1.2), 0.4)
    for r in range(9):
        mx.add(tsum + 0.7 + 0.22 * r, gp.s_tick(), 0.3, 0.3)
    x = np.tanh(mx.b[: int(total * SR)] * 1.1)
    fo = int(0.8 * SR); x[-fo:] *= np.linspace(1, 0, fo)[:, None]
    x = x / (np.abs(x).max() + 1e-9) * 0.89
    with wave.open(path, "wb") as w_:
        w_.setnchannels(2); w_.setsampwidth(2); w_.setframerate(SR); w_.writeframes((x * 32767).astype("<i2").tobytes())

if __name__ == "__main__":
    lp.main(card_frame, overlay_for, summary_frame, None, build_audio)
