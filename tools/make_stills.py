#!/usr/bin/env python3
"""
Build the two cutscene stills that cannot be cropped out of the references.

Three of the five beats come straight from art/refs/ -- the bedroom, the
facility exterior, and the facility again for the epilogue. Two do not:

  the drive     The Veridian exists only as an orthographic spec sheet on a
                flat plate. It has to be cut out and put somewhere.
  the aperture  There is no reference for it at all. It is drawn here, at the
                cutscene resolution rather than the gameplay one, reusing the
                containment ring idea from make_facility.py with the detail
                that four times the pixels allows.

Monochrome by construction, in the same grey palette as the generated
backdrops, so a cut from a still to a room does not change materially.

    python3 tools/make_stills.py
"""

import math
import os
import random
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from monochrome import to_mono  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, 'art', 'refs')
OUT = os.path.join(ROOT, 'assets', 'stills')

W, H = 768, 432

SKY_TOP = (10, 10, 10)
SKY_LOW = (46, 46, 46)
PINE = (6, 6, 6)
ROAD = (30, 30, 30)
ROAD_EDGE = (54, 54, 54)
DARK = (8, 8, 8)
STEEL = (96, 96, 96)
CONCRETE = (40, 40, 40)

rand = random.Random(614)


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def put(px, x, y, c, w=W, h=H):
    if 0 <= x < w and 0 <= y < h:
        px[x, y] = (*c, 255)


def rect(px, x0, y0, x1, y1, c):
    for y in range(int(y0), int(y1)):
        for x in range(int(x0), int(x1)):
            put(px, x, y, c)


def pine(px, cx, base, height, width, colour):
    tiers = max(4, height // 16)
    for tier in range(tiers):
        t = tier / tiers
        half = int(width * (1 - t * 0.82) / 2) + 1
        top = int(base - height * (t + 1 / tiers))
        bottom = int(base - height * t) + 2
        for y in range(top, bottom):
            span = int(half * (1 - (y - top) / max(1, bottom - top) * 0.25))
            for x in range(cx - span, cx + span):
                put(px, x, y, colour)


# ------------------------------------------------------------------- the drive

def build_drive():
    """
    The Veridian on the mountain road at night.

    The car is lifted from its reference at full resolution and set into a
    procedural night, rather than being redrawn -- it is the one piece of
    vehicle art in the project and it should be the one on screen.
    """
    img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    px = img.load()
    horizon = int(H * 0.56)

    for y in range(H):
        if y < horizon:
            c = mix(SKY_TOP, SKY_LOW, (y / horizon) ** 1.5)
        else:
            t = (y - horizon) / max(1, H - horizon)
            c = mix((18, 18, 18), ROAD, t)
        for x in range(W):
            put(px, x, y, c)

    star = random.Random(9)
    for _ in range(150):
        x, y = star.randrange(0, W), star.randrange(0, int(horizon * 0.7))
        v = star.randint(70, 190)
        put(px, x, y, (v, v, v))

    # Ridge line, then trees crowding the road on both sides.
    for i in range(30):
        pine(px, 12 + i * 27 + (i % 3) * 6, horizon + 4,
             48 + (i * 19) % 40, 30, mix(PINE, SKY_LOW, 0.18))
    for i in range(14):
        pine(px, -10 + i * 22, H - 40, 150 + (i * 31) % 90, 66, PINE)
    for i in range(14):
        pine(px, W + 10 - i * 22, H - 40, 150 + (i * 23) % 90, 66, PINE)

    # The road: a wedge running back to the vanishing point.
    vx = W // 2
    for y in range(horizon, H):
        t = (y - horizon) / max(1, H - horizon)
        half = int(18 + t * t * 300)
        c = mix((22, 22, 22), ROAD, t)
        for x in range(vx - half, vx + half):
            put(px, x, y, c)
        for x in (vx - half, vx - half + 1, vx + half - 2, vx + half - 1):
            put(px, x, y, mix(c, ROAD_EDGE, 0.7))

    # Centre line, foreshortened.
    y = horizon + 6
    while y < H:
        t = (y - horizon) / max(1, H - horizon)
        seg = max(2, int(3 + t * 26))
        wide = max(1, int(1 + t * 6))
        for yy in range(y, min(H, y + seg)):
            tt = (yy - horizon) / max(1, H - horizon)
            for x in range(vx - wide, vx + wide):
                put(px, x, yy, mix((70, 70, 70), (110, 110, 110), tt))
        y += seg + max(3, int(4 + t * 34))

    img = to_mono(img, lift=1.0, contrast=1.0, levels=40, dither=0.5)

    # The car, cut from the spec sheet at full resolution.
    sheet = Image.open(os.path.join(REFS, 'car_veridian_2400.png')).convert('RGBA')
    car = sheet.crop((745, 164, 1809, 516))
    car = cut_plate(car)
    car = to_mono(car, lift=0.96, contrast=1.10, levels=44, dither=0.6)
    target_w = 430
    car = car.resize((target_w, max(1, round(car.height * target_w / car.width))), Image.LANCZOS)

    cx = (W - car.width) // 2 + 26
    cy = H - car.height - 44
    shadow = Image.new('RGBA', (car.width, 16), (0, 0, 0, 0))
    sp = shadow.load()
    for y in range(16):
        for x in range(car.width):
            edge = min(x, car.width - x) / (car.width * 0.5)
            a = int(150 * (1 - y / 16) * min(1.0, edge * 2))
            sp[x, y] = (0, 0, 0, a)
    img.alpha_composite(shadow, (cx, cy + car.height - 8))
    img.alpha_composite(car, (cx, cy))

    # Headlights. A car photographed at night with its lights off is a car in a
    # car park; the beam is what says it is moving, and it is the only thing
    # lighting the road it is on.
    px = img.load()
    lamp_x = cx + 16
    lamp_y = cy + int(car.height * 0.60)
    for x in range(0, lamp_x):
        run = (lamp_x - x) / float(max(1, lamp_x))
        # The beam drops as it runs ahead, so it lands on the road rather than
        # hanging in the air in front of the car.
        centre = lamp_y + run * lamp_x * 0.30
        spread = 5 + run * 62
        for y in range(int(centre - spread * 0.5), int(centre + spread)):
            if y < 0 or y >= H:
                continue
            across = abs(y - centre) / max(1.0, spread)
            g = (1 - run * 0.85) ** 1.6 * (1 - across) ** 2 * 0.70
            # Dither the beam rather than laying down a smooth wedge: a clean
            # gradient would be the one soft-edged thing in the frame.
            if g > 0.02 and (x * 2 + y * 3) % 6 > int(g * 5):
                put(px, x, y, mix(px[x, y][:3], (230, 230, 230), g))
    for i in range(3):
        rect(px, lamp_x - 5 - i * 3, lamp_y - 6 + i * 3, lamp_x + 2, lamp_y + 3 + i * 2,
             (240 - i * 30,) * 3)
    return img


def cut_plate(img, tol=34):
    """Flood the flat plate the reference sheets are laid out on, from the
    border inwards so tones inside the subject survive."""
    img = img.convert('RGBA')
    px = img.load()
    w, h = img.size
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    bg = tuple(sum(c[i] for c in corners) // 4 for i in range(3))

    def near(p):
        return abs(p[0] - bg[0]) + abs(p[1] - bg[1]) + abs(p[2] - bg[2]) <= tol

    seen = bytearray(w * h)
    stack = [(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)] \
        + [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)]
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= w or y >= h:
            continue
        i = y * w + x
        if seen[i] or not near(px[x, y]):
            continue
        seen[i] = 1
        px[x, y] = (0, 0, 0, 0)
        stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return img


# ---------------------------------------------------------------- the aperture

def build_aperture(occupied=True):
    """
    The containment chamber on Sublevel 3 -- the one image the whole game is
    pointed at.

    Two things had to be got right. The opening reads as a hole rather than a
    dome only if it is *dark* inside with a hard bright rim, the light spilling
    outward: an opening is defined by its edge, not its middle. And it only has
    any scale if there is a room around it -- racks, rails, cable, a man. A
    bright arch floating in an empty grey field is a shape, not a place.

    So the light does the work of describing the room. Everything in here takes
    a rim on the side facing the ring and throws a shadow directly away from it,
    which is what makes a flat side elevation read as depth.

    `occupied` puts Hale at the threshold for the reveal. The epilogue is the
    same chamber without him, and that absence is the entire shot -- so the two
    images are identical in every other particular, down to the light.
    """
    img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    px = img.load()

    floor_y = 336
    cx = 396                       # a little right of centre, so he has room
    rx, ry = 116, 150              # the opening: tall, standing on its plinth
    cy = floor_y - 14              # sunk into the plinth rather than sat on it

    def lit(x, y, amount, colour=(214, 214, 214)):
        """Add light to a pixel, in place."""
        if 0 <= x < W and 0 <= y < H and amount > 0:
            put(px, x, y, mix(px[x, y][:3], colour, min(1.0, amount)))

    def shade(x, y, amount):
        if 0 <= x < W and 0 <= y < H and amount > 0:
            put(px, x, y, mix(px[x, y][:3], (4, 4, 4), min(1.0, amount)))

    # ---------------------------------------------------------------- the room
    for y in range(H):
        if y < floor_y:
            c = mix((26, 26, 26), (11, 11, 11), (1 - y / floor_y) ** 1.4)
        else:
            c = mix((21, 21, 21), (33, 33, 33), (y - floor_y) / max(1, H - floor_y))
        for x in range(W):
            n = rand.random() * 0.12 - 0.06
            put(px, x, y, tuple(max(0, min(255, int(v * (1 + n)))) for v in c))

    # Block courses on the back wall, offset row to row.
    for y in range(0, floor_y, 24):
        for x in range(W):
            put(px, x, y, mix(CONCRETE, DARK, 0.72))
    for y in range(0, floor_y):
        off = 30 if (y // 24) % 2 else 0
        for x in range(0, W, 60):
            put(px, (x + off) % W, y, mix(CONCRETE, DARK, 0.68))

    # Ceiling: a service gantry with dead lamps and hanging conduit.
    rect(px, 0, 0, W, 26, mix(DARK, STEEL, 0.10))
    rect(px, 0, 26, W, 32, mix(STEEL, DARK, 0.62))
    rect(px, 0, 26, W, 28, mix(STEEL, (255, 255, 255), 0.06))
    for x in range(0, W, 96):
        rect(px, x + 30, 32, x + 34, 44, mix(DARK, STEEL, 0.35))
        rect(px, x + 16, 44, x + 48, 50, mix(STEEL, DARK, 0.55))
    for x in range(0, W, 7):
        y = 34 + int(6 * math.sin(x / 26.0)) + (4 if (x // 7) % 3 else 0)
        put(px, x, y, mix(DARK, STEEL, 0.30))
        put(px, x, y + 1, DARK)

    # Floor plates, with the seams running to the sides.
    for i in range(9):
        yy = floor_y + 4 + i * 11
        for x in range(W):
            if (x + i * 17) % 96 > 6:
                put(px, x, yy, mix(DARK, STEEL, 0.22))
    for i in range(1, 9):
        yy = floor_y + i * 11
        spread = int((yy - floor_y) * 2.4)
        for x in range(0, W, 96):
            xx = cx + int((x - cx) * (1 + spread / 260.0))
            for k in range(2):
                put(px, xx + k, yy, mix(DARK, STEEL, 0.18))

    # ------------------------------------------------------------ the fittings
    props = []          # (x0, x1, top) -- everything that casts a shadow

    def cabinet(x0, top, w, h, dials=True):
        rect(px, x0, top, x0 + w, floor_y, mix(DARK, STEEL, 0.16))
        rect(px, x0, top, x0 + w, top + 3, mix(STEEL, DARK, 0.42))
        for i in range(6):
            yy = top + 10 + i * ((h - 18) // 6)
            rect(px, x0 + 4, yy, x0 + w - 4, yy + 2, mix(DARK, STEEL, 0.28))
        if dials:
            for i in range(3):
                dx = x0 + 8 + i * 12
                dy = top + h - 26
                rect(px, dx, dy, dx + 7, dy + 7, mix(STEEL, DARK, 0.35))
                put(px, dx + 3, dy + 3, (150, 150, 150))
        props.append((x0, x0 + w, top))

    cabinet(52, floor_y - 132, 40, 132)
    cabinet(96, floor_y - 146, 44, 146)
    cabinet(144, floor_y - 120, 38, 120, dials=False)

    # A bench, with the paperwork somebody left on it.
    rect(px, 588, floor_y - 62, 684, floor_y - 56, mix(DARK, STEEL, 0.30))
    for x in (594, 674):
        rect(px, x, floor_y - 56, x + 5, floor_y, mix(DARK, STEEL, 0.20))
    for i in range(5):
        x = 600 + i * 16
        rect(px, x, floor_y - 68, x + 14, floor_y - 62, mix(STEEL, (255, 255, 255), 0.18))
    props.append((588, 684, floor_y - 68))

    # Gas cylinders, chained to the wall.
    for i, x in enumerate((704, 726, 748)):
        h = 74 + (i % 2) * 8
        rect(px, x, floor_y - h, x + 16, floor_y, mix(DARK, STEEL, 0.22))
        rect(px, x + 2, floor_y - h - 5, x + 14, floor_y - h, mix(STEEL, DARK, 0.40))
        props.append((x, x + 16, floor_y - h - 5))

    # The plinth the ring stands on, and the hazard band in front of it.
    plinth_x0, plinth_x1 = cx - 196, cx + 196
    rect(px, plinth_x0, floor_y - 16, plinth_x1, floor_y + 4, mix(DARK, STEEL, 0.20))
    rect(px, plinth_x0, floor_y - 16, plinth_x1, floor_y - 13, mix(STEEL, DARK, 0.34))
    for x in range(plinth_x0, plinth_x1, 12):
        rect(px, x, floor_y + 26, x + 6, floor_y + 32, mix(STEEL, DARK, 0.30))

    # Stanchions and chain, the last thing anybody did before it opened.
    for x in (cx - 240, cx - 150, cx + 150, cx + 240):
        rect(px, x, floor_y - 44, x + 5, floor_y + 2, mix(DARK, STEEL, 0.30))
        rect(px, x - 2, floor_y - 48, x + 7, floor_y - 44, mix(STEEL, DARK, 0.36))
        props.append((x, x + 5, floor_y - 48))
    for span in ((cx - 240, cx - 150), (cx + 150, cx + 240)):
        for x in range(span[0], span[1], 5):
            t = (x - span[0]) / max(1, span[1] - span[0])
            y = int(floor_y - 40 + 9 * math.sin(math.pi * t))
            put(px, x, y, mix(DARK, STEEL, 0.34))
            put(px, x + 1, y, mix(DARK, STEEL, 0.22))

    # Cable runs, from the base of the ring out to the racks.
    for i, (y0, amp) in enumerate(((floor_y - 6, 7), (floor_y + 6, 11), (floor_y + 16, 15))):
        for x in range(96, cx - 150):
            t = (x - 96) / float(cx - 246)
            y = int(y0 + amp * math.sin(t * 5.0 + i))
            put(px, x, y, mix(DARK, STEEL, 0.26))
            put(px, x, y + 1, DARK)

    # ------------------------------------------------------- the light it makes
    # A hard-edged pool on the floor and a wash up the back wall, both centred
    # on the opening. This is the only light source in the room.
    for y in range(H):
        for x in range(W):
            d = math.hypot((x - cx) / (rx * 3.1), (y - cy) / (ry * 2.5))
            if d < 1.0:
                g = (1.0 - d) ** 2.4
                floor_bonus = 1.35 if y > floor_y else 1.0
                lit(x, y, g * 0.62 * floor_bonus)

    # Shadows: every object throws one directly away from the ring, along the
    # floor, lengthening with distance the way a single low source behaves.
    for x0, x1, top in props:
        mid = (x0 + x1) / 2
        direction = -1 if mid < cx else 1
        height = floor_y - top
        length = int(60 + height * 1.1)
        for k in range(length):
            t = k / float(length)
            xx0 = int(x0 + direction * k * 0.55)
            xx1 = int(x1 + direction * k * 0.55)
            yy = floor_y + int(k * 0.30)
            if yy >= H:
                break
            a = 0.52 * (1 - t) ** 0.8
            for x in range(min(xx0, xx1), max(xx0, xx1)):
                # Break the trailing edge up rather than ending it on a line:
                # a hard-edged shadow at this size reads as a painted ramp.
                if t > 0.55 and (x + yy * 3) % 7 < int((t - 0.55) * 14):
                    continue
                shade(x, yy, a)

    # Rim light: the edge of every upright facing the ring catches it.
    for x0, x1, top in props:
        edge = x1 - 1 if (x0 + x1) / 2 < cx else x0
        for y in range(top, floor_y):
            f = 1 - (abs(edge - cx) / float(W))
            lit(edge, y, 0.55 * f)
            lit(edge + (-1 if edge == x0 else 1), y, 0.18 * f)

    # ------------------------------------------------------------- the opening
    # Armature first: a segmented steel ring, bolted, on two angled struts.
    for a in range(0, 181):
        rad = math.radians(a)
        gap = (a % 24) < 3           # segment joints
        for t in range(0, 15):
            x = int(cx + math.cos(rad) * (rx + 16 + t))
            y = int(cy - math.sin(rad) * (ry + 16 + t))
            if y > floor_y:
                continue
            v = 0.10 + t * 0.045
            put(px, x, y, mix(STEEL, DARK, 0.62 if gap else v))
    for a in range(12, 180, 24):
        rad = math.radians(a)
        x = int(cx + math.cos(rad) * (rx + 24))
        y = int(cy - math.sin(rad) * (ry + 24))
        rect(px, x - 6, y - 6, x + 6, y + 6, mix(STEEL, DARK, 0.30))
        rect(px, x - 3, y - 3, x + 3, y + 3, mix(STEEL, (255, 255, 255), 0.22))
    for sign in (-1, 1):
        for k in range(64):
            x = int(cx + sign * (rx + 30 + k * 0.55))
            y = int(floor_y - 16 - k * 1.5)
            rect(px, x, y, x + 6, y + 4, mix(DARK, STEEL, 0.26))

    # Then the aperture itself, drawn over the armature's inner edge.
    for y in range(cy - ry - 18, floor_y + 4):
        for x in range(cx - rx - 18, cx + rx + 18):
            d = math.hypot((x - cx) / rx, (y - cy) / ry)
            if d <= 0.955:
                # Not flat black: standing waves, crowding towards the rim.
                band = 0.5 + 0.5 * math.sin(d * 30.0 - 1.1)
                v = 5 + 20 * band * (d ** 2.4)
                put(px, x, y, (int(v), int(v), int(v)))
            elif d <= 1.03:
                put(px, x, y, (242, 242, 242))
            elif d <= 1.20:
                g = (1.20 - d) / 0.17
                lit(x, y, g * g * 0.9, (236, 236, 236))

    # Where it meets the floor the light pools hardest.
    for x in range(cx - rx - 30, cx + rx + 30):
        for y in range(floor_y - 4, floor_y + 26):
            t = 1 - abs(x - cx) / float(rx + 30)
            k = 1 - (y - floor_y + 4) / 30.0
            lit(x, y, max(0.0, t) * max(0.0, k) * 0.85)

    # The floor is polished enough to hold a reflection: the ring again,
    # squashed, broken up by the plate seams. It doubles the apparent size of
    # the opening without making the light any brighter.
    for y in range(floor_y + 6, H):
        k = (y - floor_y - 6) / float(H - floor_y - 6)
        sy = cy + (floor_y - cy) * 2 + int((y - floor_y) * 2.6)
        for x in range(cx - rx - 24, cx + rx + 24):
            d = math.hypot((x - cx) / rx, (sy - cy) / ry)
            if 0.97 <= d <= 1.26 and (y + x // 3) % 5 != 0:
                lit(x, y, (1.26 - d) * 2.4 * (1 - k) ** 1.6 * 0.55)

    # Hale at the threshold, standing in the spill so he reads as a cut-out.
    # He is the scale of the thing: about two thirds of the opening's height.
    figure_x = cx - rx - 44
    if occupied:
        for k in range(150):
            t = k / 150.0
            yy = floor_y + int(k * 0.22)
            half = int(9 + k * 0.10)
            for x in range(figure_x - half - k // 2, figure_x + half - k // 2):
                shade(x, yy, 0.80 * (1 - t) ** 0.6)

    img = to_mono(img, lift=1.0, contrast=1.06, levels=44, dither=0.6)

    if occupied:
        # The actual player sprite, not an approximation: the same figure the
        # player has been walking around, at the scale of the room.
        img = paste_figure(img, figure_x, floor_y + 2, height=104)
    else:
        # She left her badge where he is standing in the other frame. In the
        # epilogue it is the only thing at the threshold.
        img = img.copy()
        p2 = img.load()
        for y in range(floor_y - 3, floor_y + 1):
            for x in range(figure_x - 7, figure_x + 7):
                if 0 <= x < W and 0 <= y < H:
                    p2[x, y] = (196, 196, 196, 255)
        for x in range(figure_x - 7, figure_x + 9):
            if 0 <= x < W:
                p2[x, floor_y + 1] = (8, 8, 8, 255)
                p2[x, floor_y + 2] = (18, 18, 18, 255)
    return img


def paste_figure(img, x, base_y, height=120):
    """Silhouette the player's own sprite at the threshold."""
    import json
    d = os.path.join(ROOT, 'assets', 'sprites', 'scientist')
    try:
        spec = json.load(open(os.path.join(d, 'scientist.json')))
        atlas = Image.open(os.path.join(ROOT, 'assets', spec['image'])).convert('RGBA')
    except (OSError, ValueError, KeyError):
        return img
    f = spec['frames'].get('side') or next(iter(spec['frames'].values()))
    sprite = atlas.crop((f['x'], f['y'], f['x'] + f['w'], f['y'] + f['h']))
    sprite = sprite.resize((max(1, round(sprite.width * height / sprite.height)), height),
                           Image.LANCZOS)
    # Backlit by the opening, so he is nearly black with a rim of light.
    sp = sprite.load()
    for yy in range(sprite.height):
        for xx in range(sprite.width):
            r, g, b, a = sp[xx, yy]
            if a < 40:
                continue
            edge = xx > sprite.width * 0.62
            v = 26 if edge else 12
            sp[xx, yy] = (v, v, v, a)
    img.alpha_composite(sprite, (x - sprite.width // 2, base_y - sprite.height))
    return img


def build_car_part():
    """
    The Veridian on its own, with the plate removed and nothing behind it.

    The drive is animated at runtime -- parallax forest, a moving road, a
    headlight beam -- so the car cannot be baked into a still. It is cut here
    once, converted here once, and drawn by src/game/cutscene_fx.js.
    """
    sheet = Image.open(os.path.join(REFS, 'car_veridian_2400.png')).convert('RGBA')
    car = cut_plate(sheet.crop((745, 164, 1809, 516)))
    car = to_mono(car, lift=0.96, contrast=1.10, levels=44, dither=0.6)
    width = 512
    return car.resize((width, max(1, round(car.height * width / car.width))), Image.LANCZOS)


def main():
    os.makedirs(OUT, exist_ok=True)
    parts = os.path.join(OUT, 'parts')
    os.makedirs(parts, exist_ok=True)
    car = build_car_part()
    car.save(os.path.join(parts, 'car_side.png'))
    print(f'  stills/parts/car_side.png  {car.width}x{car.height}')
    for name, img in [('drive_night', build_drive()),
                      ('aperture_reveal', build_aperture(True)),
                      ('aperture_empty', build_aperture(False))]:
        path = os.path.join(OUT, f'{name}.png')
        img.convert('RGB').save(path)
        print(f'  stills/{name}.png  {img.width}x{img.height}')


if __name__ == '__main__':
    main()
