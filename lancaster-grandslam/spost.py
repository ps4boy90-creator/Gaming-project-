"""Finishing for the Lancaster / Grand Slam segment: the Tallboy segment's finishing (../lancaster-tallboy/lpost.py:
upscale, sound, encode) with this segment's title card, captions and closing table.

  python3 spost.py <frames_root> <out.mp4> [--draft]

The film leaves out most of the fuze's 11 seconds: the frames run on from the bomb going in to the burst half a second
later (as rendered), and a held black frame between them says how long the wait really was.
"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "lancaster-tallboy"))
from PIL import Image, ImageDraw
import lpost as lp
from lpost import W, H, FPS, AMBER, RED, INK, DIM, PANEL, F_TITLE, F_SEMI, F_MED, ease, text, lower, callout, callout_l, dim_line, ring, readout, KMH, MK84

SPECS = [("BOMB", "Grand Slam  ·  22,000 lb, medium capacity"), ("SIZE", "25 ft 5 in (7.7 m) long  ·  46 in (1.17 m) across"), ("WEIGHT", "about 10,160 kg (22,400 lb)"), ("EXPLOSIVE", "4,144 kg (9,135 lb) of Torpex"),
         ("FUZE", "three tail pistols, here set to 11 s"), ("CARRIED BY", "Lancaster B.I (Special), one bomb each"), ("FIRST USED", "14 March 1945  ·  designed by Barnes Wallis")]
T_CUT = 0.36; HOLD = 44                                              # where the wait is cut (seconds after the bomb touches, as rendered); frames the black card is held

def tag(d, a=1.0):
    text(d, (64, 54), "EXPLOSION COMPARISON", F_SEMI(30), INK, a, tracking=4)
    d.rectangle([64, 96, 64 + 54, 100], fill=(*AMBER, int(255 * a)))
    text(d, (130, 84), "12  ·  GRAND SLAM  ·  AVRO LANCASTER", F_MED(26), DIM, a, tracking=2)

def card_frame(img, i, n):
    base = Image.new("RGBA", (W, H), (*PANEL, 255))
    base.paste(img.convert("RGB").resize((W // 2, H), Image.LANCZOS), (0, 0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    grad = Image.linear_gradient("L").rotate(90, expand=True).resize((90, H))
    seam = Image.new("RGBA", (90, H), (*PANEL, 255)); seam.putalpha(grad.point(lambda v: 255 - v))
    base.alpha_composite(seam.transpose(Image.FLIP_LEFT_RIGHT), (W // 2 - 90, 0))
    t = i / FPS; x0 = W // 2 + 96
    text(d, (x0, 130), "EXPLOSION COMPARISON  ·  12", F_SEMI(30), DIM, ease((t - 0.10) / 0.5), tracking=5)
    a = ease((t - 0.20) / 0.5); text(d, (x0 + int((1 - a) * 40), 205), "GRAND SLAM", F_TITLE(132), INK, a)
    a = ease((t - 0.35) / 0.5); text(d, (x0 + int((1 - a) * 40), 400), "A 22,000 LB BOMB FROM 12,000 FT ON A GERMAN DEPOT", F_TITLE(38), AMBER, a, tracking=1)
    a = ease((t - 0.45) / 0.5); d.rectangle([x0, 478, x0 + int(820 * a), 481], fill=(*AMBER, int(255 * a)))
    y = 512
    for k, (lab, val) in enumerate(SPECS):
        a = ease((t - 0.65 - 0.12 * k) / 0.45); dx = int((1 - a) * 28); hot = lab == "EXPLOSIVE"
        text(d, (x0 + dx, y), lab, F_SEMI(31), RED if hot else DIM, a, tracking=3)
        text(d, (x0 + 250 + dx, y - 4), val, F_MED(36), INK, a)
        y += 58
    a = ease((t - 1.7) / 0.6)
    text(d, (x0, 936), "The heaviest bomb of the war: about 40 were dropped in March and April 1945", F_MED(28), INK, a)
    text(d, (x0, 970), "by No. 617 Squadron, Royal Air Force, on viaducts, bridges and U-boat shelters.", F_MED(28), INK, a)
    text(d, (x0, 1016), "The depot and the strike are invented. The depth it reaches is calculated, not measured.", F_MED(26), DIM, a)
    base.alpha_composite(ov)
    return base.convert("RGB")

def seq_of(shot, n, meta, info):
    """The impact shot holds one frame (blacked out by the overlay) where the fuze's wait is left out."""
    if shot != "impact" or info.get("FUZE_CUT", 0) <= 0:
        return None
    kc = next((k for k in range(n) if meta[str(k)]["t"] >= T_CUT), None)
    return None if kc is None else list(range(kc)) + [(kc, h / (HOLD - 1.0)) for h in range(HOLD)] + list(range(kc + 1, n))

def overlay_for(shot, i, n, m, info):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    t = m["t"]; an = m.get("anchors", {}); P = lambda q: (q[0] * W, q[1] * H)
    io = ease((i - 5) / 9.0) * (1 - ease((i - (n - 7)) / 7.0))
    seen = lambda q: 0.04 < q[0] < 0.96 and 0.08 < q[1] < 0.86
    vh = round(info["V_HIT"]); deep = round(info["D_PATH"] * math.sin(math.radians(info["DIVE"]))); dburst = round(info["DEPTH"]); rs = round(info["R_STRUCT"]); rb = round(info["R_BLAST"]); cr = round(2 * info["CRATER_R"])
    wait = round(info["FUZE_REAL"]); cut = info["FUZE_CUT"]
    if shot == "impact":                                             # the cut: a dip to black round T_CUT, held while the card is read
        hold = m.get("hold"); black = 1.0 if hold is not None else max(0.0, 1.0 - abs(t - T_CUT) / 0.07)
        if black > 0:
            d.rectangle([0, 0, W, H], fill=(0, 0, 0, int(255 * black)))
        if hold is not None:
            a = ease(hold / 0.18) * (1 - ease((hold - 0.84) / 0.14))
            text(d, (W / 2, 440), "%d SECONDS LATER" % wait, F_TITLE(120), INK, a, anchor="ma")
            text(d, (W / 2, 590), "THE FUZE WAS SET TO %d SECONDS  ·  THE BOMB LIES ABOUT %d m DOWN, STOPPED" % (wait, deep), F_SEMI(32), DIM, a, anchor="ma", tracking=3)
    tag(d, ease(i / 8.0) if shot == "approach" else 1.0)
    if shot == "approach":
        lower(d, "AVRO LANCASTER B.I (SPECIAL)", "12,000 ft up at 200 mph  ·  no bomb doors: the bomb is too big for them and hangs partly below the belly", io)
        a = ease((i - 40) / 8.0) * (1 - ease((i - (n - 10)) / 7.0))
        if a > 0 and seen(an["bomb"]):
            callout_l(d, *P(an["bomb"]), "GRAND SLAM", "7.7 m LONG  ·  ABOUT 10 t", AMBER, a, dx=-100, dy=220)
        a = ease((i - 12) / 10.0) * (1 - ease((i - (n - 10)) / 7.0))
        text(d, (W - 64, 60), "FOUR MERLIN ENGINES  ·  NOSE AND MID-UPPER TURRETS REMOVED TO SAVE WEIGHT", F_SEMI(28), INK, a, anchor="ra", tracking=3)
        text(d, (W - 64, 98), "CODE YZ OF No. 617 SQUADRON'S B.I (SPECIAL)S, IN THE NIGHT FINISH THE FIRST OF THEM WORE", F_SEMI(24), DIM, a, anchor="ra", tracking=2)
    elif shot == "intro":
        lower(d, "GRAND SLAM", "The Tallboy's design made larger: ten tons of bomb to go deep into the ground and shake a target down from below", io)
        A = lambda k: ease((i - 8 - 9 * k) / 8.0) * (1 - ease((i - (n - 7)) / 6.0)); px = {k: P(q) for k, q in an.items()}
        dim_line(d, (px["tail"][0], px["top"][1] - 150), (px["nose"][0], px["top"][1] - 150), "25 ft 5 in  ·  7.7 m  ·  ABOUT 10,160 kg", A(0))
        for k, (key, big, small, col, ex_, ey_) in enumerate((("case", "CAST STEEL CASE", "4,144 kg OF TORPEX INSIDE", RED, 150, -130), ("fins", "FOUR FINS SET AT 5°", "THEY SPIN THE BOMB: 60 rpm AT IMPACT", AMBER, -60, 230),
                                                           ("joint", "LIGHT-ALLOY TAIL", "ABOUT HALF THE BOMB'S LENGTH", AMBER, -420, -140))):
            a = A(k + 1)
            if a > 0:
                callout(d, *px[key], big, small, col, a, dx=ex_, dy=ey_)
        a = A(4)
        text(d, (W - 64, 880), "3-TON LORRY, 6 m", F_TITLE(48), INK, a, anchor="ra"); text(d, (W - 64, 940), "BEHIND IT, FOR SCALE", F_SEMI(30), INK, a, anchor="ra", tracking=3)
    elif shot == "release":
        a1 = ease((i - 4) / 8.0) * (1 - ease((t + 0.12) / 0.1)); a2 = ease((t - 0.02) / 0.15) * (1 - ease((i - (n - 8)) / 7.0))
        if a1 > 0:
            lower(d, "TEN TONS UNDER THE BELLY", "It hangs in two links that meet beneath it  ·  the aircraft is stripped to lift it: 72,000 lb at take-off", a1)
        if a2 > 0:
            lower(d, "RELEASED", "The links let go  ·  the offset fins begin to turn the bomb as it gathers speed  ·  shown at half speed", a2)
            readout(d, "AFTER RELEASE", "%.2f s" % max(t, 0.0), a2)
    elif shot == "fall":
        readout(d, "ABOVE THE TARGET", "{:,} m".format(int(round(m.get("alt", 0), -1))), 1.0, AMBER, "{:,} km/h  ·  {:d}° DOWN".format(KMH(m.get("v", 0)), round(m.get("dive", 0))))
        lower(d, "TEN TONS AT {:,} km/h".format(KMH(info["V_HIT"])), "It falls for %d s and arrives at %d m/s (Mach %.2f)  ·  published: 1,049 ft/s (320 m/s), release height not stated" % (round(info["TOF"]), vh, info["MACH_HIT"]), io)
        a = ease((i - 30) / 10.0) * (1 - ease((i - (n - 20)) / 10.0))
        if a > 0 and seen(an["target"]):
            callout(d, *P(an["target"]), "AIM POINT", "THE DEPOT'S YARD", RED, a, dx=170, dy=-170)
        if a > 0 and seen(an["barracks"]) and i > 44:
            (callout_l if an["barracks"][0] > 0.24 else callout)(d, *P(an["barracks"]), "BARRACKS", "", AMBER, a * ease((i - 44) / 8.0), dx=-90 if an["barracks"][0] > 0.24 else 40, dy=-90 if an["barracks"][0] > 0.24 else -150)
    elif shot == "impact":
        tp = t; td = tp - info["FUZE"]; late = tp >= T_CUT and m.get("hold") is None
        clock = "T + %.2f s" % (tp + cut) if late else "T + {:,} ms".format(max(0, int(round(tp * 1000))))
        if m.get("hold") is None:
            readout(d, "SLOW MOTION", clock, ease((i - 2) / 6.0), INK, "10 t BOMB  ·  4,144 kg OF TORPEX")
        a1 = ease((i - 3) / 8.0) * (1 - ease((tp - T_CUT + 0.10) / 0.05)) * (m.get("hold") is None); a2 = ease((td - 0.02) / 0.10) * (1 - ease((td - 1.25) / 0.2)); a3 = ease((td - 1.5) / 0.2) * (1 - ease((i - (n - 10)) / 8.0))
        if a1 > 0:
            lower(d, "INTO THE GROUND", "10 t at %d m/s goes about %d m into the earth and stops  ·  the fuze is set to %d seconds" % (vh, deep, wait), a1)
        if a2 > 0:
            lower(d, "THE CHARGE FIRES, %d m DOWN" % dburst, "4,144 kg of Torpex goes off under the yard: not a fireball but the ground itself, thrown into the air", a2)
        if a3 > 0:
            lower(d, "THE YARD COMES DOWN AGAIN", "Thousands of tonnes of earth fall back over the depot  ·  buildings near the burst are shaken down and buried", a3)
        a = ease((td - 0.9) / 0.15) * (1 - ease((td - 2.2) / 0.3))
        if a > 0 and seen(an["top"]):
            callout(d, *P(an["top"]), "%d m UP" % round(info["TOP"]), "", AMBER, a, dx=230, dy=-40)
    elif shot == "radius":
        paths = m.get("paths", {}); A = lambda k: ease((i - 22 - 12 * k) / 10.0) * (1 - ease((i - (n - 8)) / 7.0))
        lower(d, "HOW FAR IT REACHES", "Crater %d m across and brick buildings demolished to %d m are published figures  ·  the 5 psi circle is scaled from the Mk 82's" % (cr, rs), io)
        for k, (key, col, big, small, dx, dy) in enumerate((("crater", RED, "CRATER: %d m ACROSS" % cr, "PUBLISHED: 124 ft", 260, -60), ("struct", AMBER, "BUILDINGS DEMOLISHED", "BRICK, TO ABOUT %d m  ·  PUBLISHED: 150 ft" % rs, 80, 150), ("blast", INK, "5 psi BLAST", "TO ABOUT %d m" % rb, -90, -80))):
            a = A(k)
            if key in paths:
                ring(d, paths[key], col, a, 5 if key == "crater" else 4, dash=key != "crater")
            if a > 0 and key in an and seen(an[key]):
                (callout_l if dx < 0 else callout)(d, *P(an[key]), big, small, col, a, dx=dx, dy=dy)
        a = A(3)
        if "cmp" in paths:
            ring(d, paths["cmp"], MK84, a * 0.9, 3)
        if a > 0 and "cmp" in an and seen(an["cmp"]):
            callout_l(d, *P(an["cmp"]), "TALLBOY: THE SAME DAMAGE", "TO ABOUT %d m, FOR COMPARISON" % round(info["R_CMP"]), MK84, a, dx=-80, dy=-150)
        text(d, (W - 64, 60), "SLOWED ABOUT 1.5 TIMES", F_SEMI(26), DIM, 1.0, anchor="ra", tracking=3)
        text(d, (W - 64, 94), "THE RADII ARE FOR A BURST AT THE SURFACE: ONE THIS DEEP SENDS MORE OF ITS FORCE INTO THE GROUND", F_SEMI(22), DIM, 1.0, anchor="ra", tracking=2)
    elif shot == "after":
        a = ease((i - 18) / 10.0) * (1 - ease((i - (n - 14)) / 10.0))
        if a > 0 and seen(an["a"]) and seen(an["b"]):
            dim_line(d, P(an["a"]), P(an["b"]), "ABOUT %d m" % cr, a, RED, off=-58)
        if a > 0 and seen(an["lorry"]):
            callout_l(d, *P(an["lorry"]), "A LORRY, 6 m LONG", "", INK, a, dx=-110, dy=-150)
        lower(d, "HALF A MINUTE LATER", "A crater about %d m across where the vehicle park was  ·  published for the trial drop of 13 March 1945: 124 ft across, 34 ft deep" % cr, ease((i - 10) / 12.0) * (1 - ease((i - (n - 10)) / 8.0)))
    return ov

def summary_frame(bg, i, n, info):
    frame = bg.copy(); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov); t = i / FPS; tag(d, 1.0); v = round(info["V_HIT"])
    text(d, (120, 140), "GRAND SLAM: THE NUMBERS", F_TITLE(80), INK, ease((t - 0.1) / 0.5))
    a = ease((t - 0.4) / 0.5); d.rectangle([120, 248, 120 + int(1680 * a), 251], fill=(*AMBER, int(255 * a)))
    rows = [("THE BOMB", "25 ft 5 in (7.7 m)  ·  46 in (1.17 m) across  ·  about 10,160 kg  ·  4,144 kg of Torpex", DIM),
            ("RELEASE", "12,000 ft (3,660 m) at 200 mph  ·  falls %d s (reported for the first drop: 35 s)" % round(info["TOF"]), DIM),
            ("AT IMPACT", "%d m/s ({:,} km/h)  ·  published: 1,049 ft/s (320 m/s) and 60 rpm".format(KMH(info["V_HIT"])) % v, AMBER),
            ("INTO THE GROUND", "about %d m in moist clay and loam (calculated), in about a tenth of a second" % round(info["D_PATH"] * math.sin(math.radians(info["DIVE"]))), DIM),
            ("FUZE", "%d s after impact, as on the first drops  ·  the film leaves the wait out" % round(info["FUZE_REAL"]), DIM),
            ("CRATER", "about %d m across  ·  published: 124 ft across, 34 ft deep" % round(2 * info["CRATER_R"]), RED),
            ("BRICK BUILDINGS", "demolished to about %d m (published: 150 ft)  ·  Tallboy: about %d m (120 ft)" % (round(info["R_STRUCT"]), round(info["R_TALLBOY"])), DIM),
            ("5 psi BLAST", "to about %d m (scaled from the Mk 82's), for a burst at the surface" % round(info["R_BLAST"]), DIM),
            ("CARRIED BY", "Lancaster B.I (Special), without bomb doors  ·  No. 617 Squadron, March and April 1945", DIM)]
    y = 278
    for r, (lab, val, col) in enumerate(rows):
        a = ease((t - 0.7 - 0.22 * r) / 0.45); dx = int((1 - a) * 24)
        text(d, (120 + dx, y + 6), lab, F_SEMI(30), col, a, tracking=3); text(d, (620 + dx, y - 2), val, F_MED(38), INK, a)
        y += 62
    a = ease((t - 3.4) / 0.6)
    text(d, (120, 872), "Against concrete: at Farge in March 1945 two went about 2 m into a roof 4.5 m thick and brought part of it down when they", F_MED(30), INK, a)
    text(d, (120, 910), "burst; in the 1946 trials no bomb could go through the 7 m part of the same roof.", F_MED(30), INK, a)
    text(d, (120, 962), "The depot is invented. Fall, impact speed and depth are calculated; the 5 psi radius is scaled from the Mk 82's published one.", F_MED(26), DIM, a)
    text(d, (120, 998), "Sources: US Navy OP 1665; Bomber Command Museum of Canada; R. Owen (617 Squadron); von Kármán, NDRC; Project Ruby report; Young, SAND97-2426.", F_MED(26), DIM, a)
    frame.alpha_composite(ov)
    return frame

if __name__ == "__main__":
    lp.main(card_frame, overlay_for, summary_frame, seq_of)
