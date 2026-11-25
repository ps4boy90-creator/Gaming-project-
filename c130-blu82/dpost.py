"""Finishing for the C-130 / BLU-82 segment: upscale to 1080p, title card, captions, the drawing on the section, the
ring on the clearing, a closing table, sound, encode.

  python3 dpost.py <frames_root> <out.mp4> [--draft]

Sound: recorded effects (see SFX below; licensed from the Epidemic Sound catalogue, not in the repository) from the
folder sfx/ beside this file or $SFX_DIR; without them a plain synthesized track is used.
"""
import os, sys, json, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "blackhawk-mk77", "b1b-gbu28"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
import post as gp
from post import W, H, FPS, SR, AMBER, RED, INK, DIM, PANEL, F_TITLE, F_SEMI, F_MED, ease, text, shadowed, lower, callout
from npost import readout, dashed, _mod

ORDER = ["card", "approach", "intro", "release", "fall", "strike", "cutaway", "after", "summary"]
N_SUMMARY = 240
HOLD = {"cutaway": 48}                                               # the first frame of the section is held while its caption is read
SPECS = [("BOMB", "BLU-82/B  ·  \"Daisy Cutter\""), ("SIZE", "3.60 m long  ·  1.37 m across"), ("WEIGHT", "6,800 kg (15,000 lb)"), ("EXPLOSIVE", "5,700 kg of slurry explosive"),
         ("CASE", "a steel tank, 6 mm wall"), ("FUZE", "on a 0.97 m extender"), ("DROPPED BY", "C-130 Hercules, by parachute"), ("FIRST USED", "23 March 1970, Vietnam")]
# name -> title in the catalogue
SFX = {"prop": "Aircraft, Prop, Twin Propeller, Small, Idle", "jungle": "Birds, Tropical, Rainforest, Daytime, Ambience, Baratang Island", "boom_big": "Explosions, Designed, Huge Burst, Long Tail",
       "boom_real": "Explosions, Real, Medium, Long Tail 01", "treefall": "Wood, Break, Tree Crack, Fall 01", "flap": "Cloth, Flap, Flag, Strong Wind, Storm", "roll": "Metal, Movement, Metal Shelf, Steady Constant Rolling, Fast",
       "drone": "Designed, Drone, Tension, Low", "boom_deep": "Designed, Boom, Cinematic, Impact, Big, Deep, Low Rumble, Growl, Frightening, Muffled", "wind": "Ambience, Desert, Desolation, Canyon, Wind",
       "whoosh": "Swooshes, Whoosh, Wind Whooshes Panned, Whistling 03", "latch": "Mechanical, Latch, Metal Latch, Heavy, Lock, Unlock, MKH 50", "debris": "Rocks, Crash & Debris, Heavy, Big Hit, Stone Debris 05", "quake": "Natural Disaster, Earthquake, Rumble, Rocks In Motion 01"}
KMH = lambda v: int(round(v * 3.6, -1))

def tag(d, a=1.0):
    text(d, (64, 54), "EXPLOSION COMPARISON", F_SEMI(30), INK, a, tracking=4)
    d.rectangle([64, 96, 64 + 54, 100], fill=(*AMBER, int(255 * a)))
    text(d, (130, 84), "11  ·  BLU-82 \"DAISY CUTTER\"  ·  C-130 HERCULES", F_MED(26), DIM, a, tracking=2)

def card_frame(img, i, n):
    base = Image.new("RGBA", (W, H), (*PANEL, 255))
    base.paste(img.convert("RGB").resize((W // 2, H), Image.LANCZOS), (0, 0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    grad = Image.linear_gradient("L").rotate(90, expand=True).resize((90, H))
    seam = Image.new("RGBA", (90, H), (*PANEL, 255)); seam.putalpha(grad.point(lambda v: 255 - v))
    base.alpha_composite(seam.transpose(Image.FLIP_LEFT_RIGHT), (W // 2 - 90, 0))
    t = i / FPS; x0 = W // 2 + 96
    text(d, (x0, 110), "EXPLOSION COMPARISON  ·  11", F_SEMI(30), DIM, ease((t - 0.10) / 0.5), tracking=5)
    a = ease((t - 0.20) / 0.5); text(d, (x0 + int((1 - a) * 40), 156), "BLU-82", F_TITLE(170), INK, a)
    a = ease((t - 0.35) / 0.5); text(d, (x0 + int((1 - a) * 40), 374), "15,000 LB TO CLEAR A LANDING ZONE IN THE JUNGLE", F_TITLE(37), AMBER, a, tracking=1)
    a = ease((t - 0.45) / 0.5); d.rectangle([x0, 448, x0 + int(820 * a), 451], fill=(*AMBER, int(255 * a)))
    y = 478
    for k, (lab, val) in enumerate(SPECS):
        a = ease((t - 0.65 - 0.11 * k) / 0.45); dx = int((1 - a) * 28); hot = lab == "EXPLOSIVE"
        text(d, (x0 + dx, y), lab, F_SEMI(30), RED if hot else DIM, a, tracking=3)
        text(d, (x0 + 250 + dx, y - 4), val, F_MED(35), INK, a)
        y += 55
    a = ease((t - 1.7) / 0.6)
    text(d, (x0, 936), "Built to blast a clearing for helicopters out of dense forest,", F_MED(28), INK, a)
    text(d, (x0, 970), "without leaving a crater they could not land in.", F_MED(28), INK, a)
    text(d, (x0, 1016), "The forest and this drop are invented. Sizes and results are published figures.", F_MED(26), DIM, a)
    base.alpha_composite(ov)
    return base.convert("RGB")

def dim_line(d, p0, p1, label, a, color=INK, off=-46, tick=14, size=34):
    """A dimension line between two screen points with end ticks and a centred label."""
    if a <= 0:
        return
    c = (*color, int(235 * a)); d.line([p0, p1], fill=c, width=3)
    vx, vy = p1[0] - p0[0], p1[1] - p0[1]; L_ = math.hypot(vx, vy) + 1e-6; nx, ny = -vy / L_ * tick, vx / L_ * tick
    for p in (p0, p1):
        d.line([(p[0] - nx, p[1] - ny), (p[0] + nx, p[1] + ny)], fill=c, width=3)
    text(d, ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 + off), label, F_SEMI(size), color, a, anchor="ma", tracking=2)

def cut_overlay(d, i, n, m, info, hold):
    """The section: the height of the fuze, then the blast front, the circle in which nothing is left standing, the time."""
    an = m["anchors"]; o, ex, ez = an["o"], an["ex"], an["ez"]
    PX = lambda x, z: ((o[0] + x * (ex[0] - o[0]) + z * (ez[0] - o[0])) * W, (o[1] + x * (ex[1] - o[1]) + z * (ez[1] - o[1])) * H)
    pre, one = info["CUT"]; tb = m["tb"]; R = info["R_LZ"]; fr = np.array(info["FRONT"]); P = lambda q: (q[0] * W, q[1] * H)
    if hold is not None:
        a = ease(hold * 6) * (1 - ease((hold - 0.88) / 0.12))
        lower(d, "THE SAME BURST, SEEN FROM THE SIDE", "The forest cut along a line through the centre  ·  trees up to 45 m tall, the bomb to the same scale", a)
        a = ease((hold - 0.2) * 5) * (1 - ease((hold - 0.88) / 0.12))
        if a > 0:
            callout(d, *P(an["bomb"]), "BLU-82", "3.6 m LONG, UNDER ITS PARACHUTE", AMBER, a, dx=170, dy=-60)
        return
    slow = "1 SECOND OF FILM = A TENTH OF A SECOND" if i < pre + one else "1 SECOND OF FILM = A FIFTH OF A SECOND"
    text(d, (W - 64, 60), slow, F_SEMI(26), DIM, 1.0, anchor="ra", tracking=3)
    if tb < 0:
        a = ease((i - 1) / 5.0) * (1 - ease((i - pre + 5) / 5.0))
        lower(d, "THE FUZE TOUCHES FIRST", "It stands 0.97 m ahead of the tank, so the charge goes off above the ground and the blast spreads sideways", a)
        readout(d, "FUZE ABOVE THE GROUND", "%.1f m" % m["tipz"], a, AMBER, "FALLING AT %d m/s" % round(m["v"]))
        if a > 0:
            callout(d, *P(an["tip"]), "NOSE FUZE", "ON A 0.97 m EXTENDER", AMBER, a, dx=190, dy=40)
        return
    text(d, (W - 64, 94), "THE TIMING OF THE BLAST AND THE TREES IS A RECONSTRUCTION", F_SEMI(22), DIM, 1.0, anchor="ra", tracking=2)
    readout(d, "AFTER THE BURST", "{:,} ms".format(int(round(tb * 1000))), 1.0, INK, "5.7 t OF EXPLOSIVE")
    rf = float(np.interp(tb, fr[:, 1], fr[:, 0])); a = ease(tb / 0.01) * (1 - ease((rf - 150.0) / 40.0))
    if a > 0 and rf > 3:                                              # the blast front
        c = (*INK, int(150 * a))
        for sg in (-1, 1):
            p0 = PX(sg * rf, 0.0); p1 = PX(sg * rf, 46.0); dashed(d, [(p0[0], p0[1] + (p1[1] - p0[1]) * q / 30.0) for q in range(31)], c, 3)
        q = PX(rf, 48.5); text(d, (q[0], q[1] - 30), "BLAST FRONT", F_SEMI(24), INK, a * (1 - ease((rf - 120.0) / 20.0)), anchor="ma", tracking=2)
    a = ease((tb - 0.30) / 0.12) * (1 - ease((i - (n - 8)) / 7.0))
    if a > 0:
        p0 = PX(-R, 0.0); p1 = PX(R, 0.0); y = p0[1] + 46; dim_line(d, (p0[0], y), (p1[0], y), "79 m (260 ft): NOTHING LEFT STANDING", a, AMBER, off=14)
    if tb < 0.34:
        lower(d, "THE BLAST GOES OUT SIDEWAYS", "About 1,000 lb per square inch near the centre (published)  ·  the trees nearest the burst are broken up altogether", ease(tb / 0.02) * (1 - ease((tb - 0.29) / 0.05)))
    else:
        lower(d, "TRUNKS SNAP AND GO DOWN POINTING OUTWARDS", "Round the clearing the trees are stripped and left leaning  ·  the dust is drawn thin here so that the trees can be seen", ease((tb - 0.34) / 0.06) * (1 - ease((i - (n - 9)) / 8.0)))

def overlay_for(shot, i, n, m, info, hold=None):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    t = m["t"]; an = m.get("anchors", {}); P = lambda q: (q[0] * W, q[1] * H)
    tag(d, ease(i / 8.0) if shot == "approach" else 1.0)
    io = ease((i - 5) / 9.0) * (1 - ease((i - (n - 7)) / 7.0))
    seen = lambda q: 0.04 < q[0] < 0.96 and 0.08 < q[1] < 0.86
    if shot == "approach":
        lower(d, "C-130 HERCULES", "1,830 m (6,000 ft) above the forest at about %d km/h  ·  ramp down, the extraction parachute already out" % KMH(info["V_AC"]), io)
        a = ease((i - 30) / 8.0) * (1 - ease((i - (n - 10)) / 7.0))
        if a > 0 and seen(an["chute"]):
            callout(d, *P(an["chute"]), "EXTRACTION PARACHUTE", "4.6 m (15 ft)  ·  TIED TO THE LOAD INSIDE", AMBER, a, dx=-420, dy=150)
        a = ease((i - 12) / 10.0) * (1 - ease((i - (n - 10)) / 7.0))
        text(d, (W - 64, 60), "\"COMMANDO VAULT\": C-130 CREWS DROPPED THESE BOMBS IN VIETNAM FROM 1970", F_SEMI(26), INK, a, anchor="ra", tracking=2)
        text(d, (W - 64, 96), "A RADAR CONTROLLER ON THE GROUND COUNTED THE CREW DOWN TO THE RELEASE", F_SEMI(24), DIM, a, anchor="ra", tracking=2)
    elif shot == "intro":
        lower(d, "BLU-82/B", "A thin steel tank holding 5.7 tonnes of slurry explosive: more than four fifths of the bomb's weight is explosive", io)
        A = lambda k: ease((i - 8 - 9 * k) / 8.0) * (1 - ease((i - (n - 7)) / 6.0)); px = {k: P(q) for k, q in an.items()}
        dim_line(d, (px["tail"][0], px["top"][1] - 50), (px["nose"][0], px["top"][1] - 50), "3.60 m  ·  6,800 kg", A(0))
        dim_line(d, (px["nose"][0], px["bot"][1] + 34), (px["tip"][0], px["bot"][1] + 34), "0.97 m", A(1), AMBER, off=14, size=30)
        for k, (key, big, small, col, ex_, ey_) in enumerate((("ext", "FUZE EXTENDER", "THE FUZE AT ITS TIP TOUCHES FIRST", AMBER, 70, -150), ("pack", "STABILISING PARACHUTE", "PACKED ON THE REAR END", AMBER, -450, 70),
                                                           ("cwall", "WALL 6 mm THICK", "A TANK, NOT A FORGED CASE", RED, 470, 10), ("cfill", "5,700 kg OF EXPLOSIVE", "A SLURRY, POURED IN", RED, -760, -30), ("cboost", "BOOSTER", "", AMBER, 300, 100))):
            a = A(k + 1)
            if a > 0:
                callout(d, *px[key], big, small, col, a, dx=ex_, dy=ey_)
    elif shot == "release":
        tau = m["tau"]; a1 = ease((i - 4) / 8.0) * (1 - ease((tau + 0.15) / 0.15)); a2 = ease((tau - 0.05) / 0.2) * (1 - ease((i - (n - 8)) / 7.0))
        if a1 > 0:
            lower(d, "RELEASE", "The loadmaster frees the locks  ·  the parachute pulls bomb, cradle and platform out along the rollers", a1)
            readout(d, "AFTER RELEASE", "%.1f s" % max(t, 0.0), a1)
        if a2 > 0:
            lower(d, "THE BOMB LEAVES ITS CRADLE", "Blades on static lines cut the webbing as the load clears the ramp  ·  its own parachute opens  ·  shown at half speed", a2)
            readout(d, "AFTER RELEASE", "%.1f s" % max(t, 0.0), a2)
        a = ease((tau - 1.0) / 0.2) * (1 - ease((i - (n - 8)) / 7.0))
        if a > 0 and seen(an["plat"]):
            callout(d, *P(an["plat"]), "PLATFORM AND CRADLE", "FALL AWAY ON THE EXTRACTION PARACHUTE", INK, a, dx=-620, dy=-200)
        a = ease((m["open"] - 0.6) / 0.3) * (1 - ease((i - (n - 8)) / 7.0))
        if a > 0 and seen(an["stab"]):
            callout(d, *P(an["stab"]), "STABILISING PARACHUTE", "KEEPS THE BOMB NOSE-DOWN", AMBER, a, dx=-110, dy=190)
    elif shot == "fall":
        readout(d, "ABOVE THE GROUND", "{:,} m".format(int(round(m.get("alt", 0)))), 1.0, AMBER, "{:,} km/h  ·  {:d}° DOWN".format(KMH(m.get("v", 0)), round(m.get("dive", 0))))
        lower(d, "26 SECONDS TO FALL 1,830 m", "The parachute holds it to about %d km/h and nearly upright  ·  the aircraft is well clear by the time it bursts" % KMH(info["V_HIT"]), io)
        a = ease((i - 26) / 10.0) * (1 - ease((i - (n - 22)) / 10.0))
        if a > 0 and seen(an["tip"]):
            callout(d, *P(an["tip"]), "FUZE ON A 0.97 m EXTENDER", "", AMBER, a, dx=-470, dy=120)
    elif shot == "strike":
        tb = t; pre, one = info["STRIKE"]
        readout(d, "AFTER THE BURST" if tb >= 0 else "SLOW MOTION", "%.1f s" % max(tb, 0.0), ease((i - 2) / 6.0), INK, "5.7 t OF EXPLOSIVE")
        if i < pre + one:
            text(d, (W - 64, 60), "SLOWED 1.7 TIMES", F_SEMI(26), DIM, 1.0, anchor="ra", tracking=3)
        a1 = ease((i - 3) / 8.0) * (1 - ease((tb - 1.1) / 0.3)); a2 = ease((tb - 1.5) / 0.3) * (1 - ease((i - (n - 10)) / 8.0))
        if a1 > 0:
            lower(d, "IT BURSTS JUST ABOVE THE GROUND", "The fuze on the extender touches first  ·  the blast spreads out through the trees instead of digging a crater", a1)
        if a2 > 0:
            lower(d, "A CIRCLE OF FOREST IS GONE", "About 1,000 lb per square inch near the centre (published)  ·  crews felt the shock in the aircraft, 1,800 m up", a2)
        a = ease((i - 4) / 6.0) * (1 - ease((tb + 0.08) / 0.06))
        if a > 0 and seen(an["bomb"]):
            callout(d, *P(an["bomb"]), "BLU-82", "", AMBER, a, dx=150, dy=-120)
    elif shot == "cutaway":
        cut_overlay(d, i, n, m, info, hold)
    elif shot == "after":
        a = ease((i - 14) / 10.0) * (1 - ease((i - (n - 12)) / 10.0))
        if a > 0:
            pts = [P(an["r%02d" % k]) for k in range(48)]; pts.append(pts[0]); c = (*AMBER, int(230 * a))
            for k in range(0, 48, 2):
                d.line([pts[k], pts[k + 1]], fill=c, width=4)
            e0, e1 = P(an["r24"]), P(an["r00"]); d.line([e0, e1], fill=c, width=3); mid = ((e0[0] + e1[0]) / 2, (e0[1] + e1[1]) / 2)
            text(d, (mid[0], mid[1] - 64), "79 m", F_TITLE(60), AMBER, a, anchor="ma"); text(d, (mid[0], mid[1] + 10), "260 ft", F_SEMI(30), INK, a, anchor="ma", tracking=2)
        lower(d, "A MINUTE LATER: A LANDING ZONE", "Room for one to three UH-1 helicopters  ·  almost no crater: a dish a hand deep under the burst  ·  hardly any debris piled at the edge", ease((i - 8) / 12.0) * (1 - ease((i - (n - 10)) / 8.0)))
    return ov

def summary_frame(bg, i, n, info):
    frame = bg.copy(); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov); t = i / FPS; tag(d, 1.0)
    text(d, (120, 140), "WHAT A BLU-82 DOES", F_TITLE(80), INK, ease((t - 0.1) / 0.5))
    a = ease((t - 0.4) / 0.5); d.rectangle([120, 248, 120 + int(1680 * a), 251], fill=(*AMBER, int(255 * a)))
    rows = [("THE BOMB", "6,800 kg, of which 5,700 kg is slurry explosive, in a steel tank 6 mm thick", DIM),
            ("THE DROP", "pulled out of a C-130 by parachute at 1,830 m or more  ·  26 s to fall", DIM),
            ("THE BURST", "above the ground: the fuze stands 0.97 m ahead of the tank", AMBER),
            ("THE CLEARING", "about 79 m (260 ft) across: room for one to three UH-1 helicopters", RED),
            ("THE CRATER", "almost none: a dish 6 to 9 m across and 15 to 30 cm deep (1969 test)", DIM),
            ("THE TREES", "cleared trees up to 1.2 m thick and 45 m tall", DIM),
            ("BUILT", "225, from 1970, to follow the 10,000 lb M121", DIM),
            ("USED", "Vietnam from March 1970  ·  the Gulf, 1991  ·  Afghanistan, 2001  ·  last one dropped in 2008", DIM),
            ("IT IS NOT", "a fuel-air bomb: the explosive carries its own oxidiser", DIM)]
    y = 278
    for r, (lab, val, col) in enumerate(rows):
        a = ease((t - 0.7 - 0.22 * r) / 0.45); dx = int((1 - a) * 24)
        text(d, (120 + dx, y + 6), lab, F_SEMI(30), col, a, tracking=3); text(d, (470 + dx, y - 2), val, F_MED(38), INK, a)
        y += 62
    a = ease((t - 3.4) / 0.6)
    text(d, (120, 872), "\"Daisy cutter\" was first the name of the fuze extender, on any bomb. In Vietnam it became this bomb's name.", F_MED(30), INK, a)
    text(d, (120, 924), "Weights, sizes, the height of the drop, the fall time and the size of the clearing are published figures (USAF museums, Air & Space Forces Magazine).", F_MED(26), DIM, a)
    text(d, (120, 960), "The forest, the speed of the blast and the way the trees go down are a reconstruction. Parachute sizes and the release speed are estimates.", F_MED(26), DIM, a)
    frame.alpha_composite(ov)
    return frame

# ------------------------------------------------------------------ sound
def _when(metas, T):
    def when(shot, pred):
        m = metas[shot]
        for i in sorted(int(k) for k in m):
            if pred(m[str(i)]):
                return T[shot] + i / FPS
        return None
    return when

def build_audio_synth(path, starts, metas, lens, total, info):
    mx = gp.Mix(total); T = {k: v / FPS for k, v in starts.items()}; L = {k: v / FPS for k, v in lens.items()}; when = _when(metas, T)
    def turboprop(dur, seed):
        n = int(dur * SR); t = np.arange(n) / SR; return gp.lp(gp.noise(n), 160, 3) * 4.0 * _mod(n, 0.8, 0.25, seed) + 0.10 * np.sin(2 * np.pi * 68 * t) + 0.06 * np.sin(2 * np.pi * 136 * t) + gp.bp(gp.noise(n), 300, 1500) * 0.6
    mx.add(0.0, gp.s_drone(T["approach"] + 0.2), 0.5); mx.add(0.05, gp.s_thud(1.2), 0.5)
    for shot in ("approach", "release"):
        mx.add(T[shot], turboprop(L[shot], 3), 0.5, -0.15); mx.add(T[shot], turboprop(L[shot], 8), 0.5, 0.15)
    mx.add(T["intro"], gp.s_drone(L["intro"]), 0.4)
    tr = when("release", lambda m: m["tau"] >= 0.0)
    if tr:
        mx.add(tr, gp.s_whoosh(1.6, 250, 1400, 0.3), 0.5)
    mx.add(T["fall"], gp.s_wind(L["fall"]) * 0.6, 1.0); mx.add(T["fall"], gp.s_whoosh(L["fall"], 300, 2400, 0.97), 0.5)
    tb = when("strike", lambda m: m["t"] >= 0.0)
    if tb:
        mx.add(tb, gp.s_boom(2.5, 1.6), 1.0); mx.add(tb + 0.4, gp.s_debris(5.0, 40, 2.0), 0.5)
    tc = T["cutaway"] + (HOLD.get("cutaway", 0) + info["CUT"][0]) / FPS; mx.add(T["cutaway"], gp.s_drone(L["cutaway"]), 0.35); mx.add(tc, gp.s_boom(2.5, 3.0), 1.0); mx.add(tc + 0.6, gp.s_debris(6.0, 40, 3.0), 0.5)
    mx.add(T["after"], gp.s_wind(L["after"] + L["summary"]) * 0.16, 1.0); mx.add(T["summary"], gp.s_drone(L["summary"]), 0.45)
    x = np.tanh(mx.b[: int(total * SR)] * 1.1); fo = int(0.8 * SR); x[-fo:] *= np.linspace(1, 0, fo)[:, None]; x = x / (np.abs(x).max() + 1e-9) * 0.89
    with wave.open(path, "wb") as w_:
        w_.setnchannels(2); w_.setsampwidth(2); w_.setframerate(SR); w_.writeframes((x * 32767).astype("<i2").tobytes())

def build_audio_sfx(path, starts, metas, lens, total, info, S):
    """Recorded effects: four propellers, the rollers and the locks, cloth filling, rushing air, the forest before the
    burst, a large explosion with a long tail, trees breaking, and a low tonal bed under the title and the tables."""
    mx = gp.Mix(total); T = {k: v / FPS for k, v in starts.items()}; L = {k: v / FPS for k, v in lens.items()}; when = _when(metas, T)
    tick = lambda t, g=0.22: mx.add(t, gp.lp(gp.s_tick(), 3500, 1), g, 0.25)
    # ---- title card
    S.put(mx, 0.0, S.bed("drone", T["approach"] + 0.4, t0=6.0, fi=0.3, fo=0.5, level=0.07)); S.put(mx, 0.05, S.cut("boom_deep", 0.0, 2.0, speed=1.8, fo=1.0), 0.30)
    for k in range(len(SPECS)):
        tick(0.65 + 0.11 * k)
    # ---- the aircraft: four turboprops (the recording is played lower, for a bigger machine), wind past the open ramp
    for shot, t0, g in (("approach", 1.0, 1.0), ("release", 9.0, 0.9)):
        S.put(mx, T[shot], S.bed("prop", L[shot] + 0.3, t0=t0, speed=0.72, fi=0.6, fo=0.35, lp=6000, level=0.085), g, -0.1); S.put(mx, T[shot], S.bed("prop", L[shot] + 0.3, t0=t0 + 7.0, speed=0.76, fi=0.6, fo=0.35, lp=6000, level=0.06), g, 0.25)
        S.put(mx, T[shot], S.bed("flap", L[shot] + 0.3, t0=4.0, fi=0.6, fo=0.35, lp=3000, level=0.016), g, 0.35)
    # ---- the bomb, whole and cut open
    S.put(mx, T["intro"], S.bed("drone", L["intro"], t0=22.0, fi=0.4, fo=0.4, level=0.065)); S.put(mx, T["intro"] + 0.05, S.cut("boom_deep", 0.0, 1.8, speed=1.8, fo=1.0), 0.22)
    for k in range(6):
        tick(T["intro"] + (8 + 9 * k) / FPS)
    # ---- release: the locks, the rollers, out into the air, the webbing cut, the second parachute
    t0 = when("release", lambda m: m["t"] >= 0.0); te = when("release", lambda m: m["tau"] >= 0.0); ts = when("release", lambda m: m.get("sep", 0) > 0.5); to = when("release", lambda m: m.get("open", 0) > 0.05)
    if t0 and te:
        S.put(mx, t0 - 0.04, S.cut("latch", 5.55, 1.3), 0.75); r = S.cut("roll", 3.0, te - t0 + 0.25, fi=0.15, fo=0.25, lp=5000); r *= np.linspace(0.4, 1.0, len(r))[:, None]; S.put(mx, t0, r, 0.55)
        S.put(mx, te - 0.1, S.cut("whoosh", 16.4, 3.6, fi=0.2, fo=0.8), 0.40, -0.2)
    if ts:
        S.put(mx, ts - 0.03, S.cut("latch", 1.9, 0.9), 0.40, 0.2)
    if to:
        S.put(mx, to, S.cut("flap", 6.6, 2.6, speed=0.8, fi=0.05, fo=1.0), 0.55, 0.15)
    # ---- the fall: air rushing past, the parachute working
    lf = L["fall"]; w = S.bed("wind", lf, t0=34.0, speed=1.4, fi=0.25, fo=0.03, level=0.10) * np.linspace(0.5, 1.2, int(lf * SR))[:, None]; S.put(mx, T["fall"], w)
    S.put(mx, T["fall"], S.bed("flap", lf, t0=12.0, fi=0.3, fo=0.03, level=0.03), 1.0, 0.1); S.put(mx, T["fall"] + lf - 2.2, S.cut("whoosh", 32.6, 2.2, fi=0.6, fo=0.02), 0.5)
    # ---- the burst from the air
    tb = when("strike", lambda m: m["t"] >= 0.0); ls = L["strike"]
    if tb:
        S.put(mx, T["strike"], S.bed("jungle", tb - T["strike"] + 0.05, t0=20.0, fi=0.2, fo=0.02, level=0.05)); S.put(mx, T["strike"], S.bed("wind", ls, t0=4.0, fi=0.3, fo=0.5, level=0.03))
        S.put(mx, tb, S.cut("boom_real", 0.0, 3.1, speed=0.8, fo=0.8), 1.0); S.put(mx, tb, S.cut("boom_big", 0.0, 7.0, speed=0.8, fo=2.5), 0.85); S.put(mx, tb, S.cut("boom_deep", 0.0, 8.0, speed=0.7, fo=3.0, drive=2.5), 0.40)
        for k, (dt_, pan, t0_) in enumerate(((0.35, -0.4, 1.0), (0.7, 0.4, 4.3), (1.2, 0.0, 1.6), (1.9, -0.2, 4.6))):
            S.put(mx, tb + dt_, S.cut("treefall", t0_, 3.0, speed=0.85, fi=0.05, fo=1.0), 0.50, pan)
        S.put(mx, tb + 0.3, S.cut("debris", 0.0, 3.0, speed=0.8, fo=1.2), 0.30, 0.1); S.put(mx, tb + 0.2, S.bed("quake", max(T["strike"] + ls - tb - 0.2, 1.0), t0=20.0, fi=0.2, fo=2.5, lp=400, level=0.05))
    # ---- the section
    tc = T["cutaway"]; lc = L["cutaway"]; hold = HOLD.get("cutaway", 0) / FPS; pre, one = info["CUT"]; tb2 = tc + hold + pre / FPS
    S.put(mx, tc, S.bed("drone", lc, t0=30.0, fi=0.5, fo=0.8, level=0.05)); S.put(mx, tc, S.bed("jungle", tb2 - tc, t0=60.0, fi=0.5, fo=0.05, level=0.03))
    S.put(mx, tb2 - 2.0, S.cut("whoosh", 32.6, 2.0, speed=0.5, fi=0.8, fo=0.02), 0.40)
    S.put(mx, tb2, S.cut("boom_real", 0.0, 6.0, speed=0.45, fo=2.0), 1.0); S.put(mx, tb2, S.cut("boom_big", 0.0, 9.0, speed=0.5, fo=3.0), 0.8); S.put(mx, tb2, S.cut("boom_deep", 0.0, 9.0, speed=0.6, fo=3.0, drive=3.0), 0.40)
    for k, (dt_, pan, t0_) in enumerate(((1.0, -0.5, 1.0), (2.0, 0.5, 4.3), (3.2, -0.2, 1.6), (4.6, 0.3, 4.6), (6.0, 0.0, 1.0))):
        S.put(mx, tb2 + dt_, S.cut("treefall", t0_, 5.0, speed=0.5, fi=0.05, fo=1.5), 0.55, pan)
    S.put(mx, tb2 + 0.6, S.cut("debris", 0.0, 6.0, speed=0.45, fo=2.0), 0.30, 0.1)
    # ---- afterwards: the forest is silent; wind, and wood settling
    ta = T["after"]; la_ = L["after"] + L["summary"]; S.put(mx, ta, S.bed("wind", la_, t0=6.0, fi=0.5, fo=1.0, level=0.045)); S.put(mx, ta + 1.0, S.cut("treefall", 1.0, 3.0, speed=0.9, fi=0.2, fo=1.5), 0.10, 0.4)
    # ---- closing table
    ts_ = T["summary"]; S.put(mx, ts_, S.bed("drone", L["summary"], t0=8.0, fi=0.6, fo=1.2, level=0.06)); S.put(mx, ts_ + 0.1, S.cut("boom_deep", 0.0, 2.0, speed=1.8, fo=1.0), 0.28)
    for r in range(9):
        tick(ts_ + 0.7 + 0.22 * r)
    S.finish(mx, total, path)

def build_audio(path, starts, metas, lens, total, info):
    import gsfx as S
    S.DIR = os.environ.get("SFX_DIR") or os.path.join(HERE, "sfx")
    if all(os.path.exists(os.path.join(S.DIR, n + ".wav")) for n in SFX):
        return build_audio_sfx(path, starts, metas, lens, total, info, S)
    print("NOTE: recorded effects not found in %s - using the synthesized soundtrack" % S.DIR); return build_audio_synth(path, starts, metas, lens, total, info)

GRADE = {"fall": 1.22, "strike": 1.28, "after": 1.30, "cutaway": 1.10}        # under the high sun the forest renders dark: lift those shots a little
_LUT = {}

def grade(img, shot):
    g = GRADE.get(shot)
    if not g:
        return img
    if shot not in _LUT:
        x = np.arange(256) / 255.0; y = np.clip(x ** (1 / g ** 0.6) * (1 + 0.12 * (g - 1)), 0, 1); _LUT[shot] = [int(round(v * 255)) for v in y] * 3
    return img.point(_LUT[shot])

FADES = {"card": (8, 6), "approach": (8, 5), "intro": (6, 6), "release": (6, 5), "fall": (5, 0), "strike": (0, 8), "cutaway": (10, 8), "after": (8, 0), "summary": (0, 16)}

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
                frame = grade(Image.open(os.path.join(d1, f1[k])).convert("RGB"), shot).resize((W, H), Image.LANCZOS).convert("RGBA")
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
