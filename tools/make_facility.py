#!/usr/bin/env python3
"""
Generate the backdrop layers for the eight Blackridge Station scenes.

Like tools/make_corridor.py, this art is procedural and explicitly a stand-in.
It exists so the facility is playable now: every scene, clue and deduction is
authored against real geometry rather than against coloured blocks. Replace any
folder under assets/backdrops/ with painted art of the same dimensions and the
scene JSON keeps working untouched.

    python3 tools/make_facility.py


The palette is monochrome by construction rather than by conversion. Converting
colour art to grey collides values that differ only in hue -- the pine
silhouettes and the night sky behind them landed on the same grey and the trees
disappeared. For art this file generates there is no reason to accept that:
the greys are chosen with the separation built in.
"""

import math
import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets', 'backdrops')

H = 216

# One palette across the whole building, so eight rooms read as one place.
CONCRETE_LO = (34, 34, 34)
CONCRETE_HI = (58, 58, 58)
FLOOR_LO = (26, 26, 26)
FLOOR_HI = (46, 46, 46)
TRIM = (78, 78, 78)
STEEL = (96, 96, 96)
DARK = (10, 10, 10)
TEAL = (64, 64, 64)
RUST = (72, 72, 72)
WARN = (112, 112, 112)
NIGHT_SKY_TOP = (12, 12, 12)
NIGHT_SKY_LOW = (44, 44, 44)
PINE = (8, 8, 8)

rand = random.Random(714)


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def put(px, w, h, x, y, colour, a=255):
    if 0 <= x < w and 0 <= y < h:
        px[x, y] = (*colour, a)


def rect(px, w, h, x0, y0, x1, y1, colour):
    for y in range(int(y0), int(y1)):
        for x in range(int(x0), int(x1)):
            put(px, w, h, x, y, colour)


def vgrad(px, w, h, x0, y0, x1, y1, top, bottom):
    span = max(1, y1 - y0)
    for y in range(int(y0), int(y1)):
        c = mix(top, bottom, (y - y0) / span)
        for x in range(int(x0), int(x1)):
            put(px, w, h, x, y, c)


def outline(px, w, h, x0, y0, x1, y1, colour):
    for x in range(int(x0), int(x1)):
        put(px, w, h, x, int(y0), colour)
        put(px, w, h, x, int(y1) - 1, colour)
    for y in range(int(y0), int(y1)):
        put(px, w, h, int(x0), y, colour)
        put(px, w, h, int(x1) - 1, y, colour)


# ------------------------------------------------------------------ surfaces

def interior_base(w, floor_y, wall_lo=CONCRETE_LO, wall_hi=CONCRETE_HI):
    """Cinderblock wall over a scuffed floor -- the shell every room starts from."""
    img = Image.new('RGBA', (w, H), (0, 0, 0, 255))
    px = img.load()

    for y in range(floor_y):
        depth = 1 - (y / floor_y) * 0.5
        base = mix(wall_lo, wall_hi, depth)
        for x in range(w):
            # Block courses: 32 wide, 16 tall, offset every other row.
            row = y // 16
            off = (row % 2) * 16
            seam = ((x + off) % 32 == 0) or (y % 16 == 0)
            c = mix(base, DARK, 0.55) if seam else base
            n = rand.random() * 0.08 - 0.04
            put(px, w, H, x, y, tuple(max(0, min(255, int(v * (1 + n)))) for v in c))

    for y in range(floor_y, H):
        t = (y - floor_y) / max(1, H - floor_y)
        base = mix(FLOOR_LO, FLOOR_HI, 0.2 + t * 0.7)
        for x in range(w):
            tile = (x // 24 + y // 12) % 2
            c = mix(base, CONCRETE_HI, 0.06) if tile else base
            if x % 24 == 0 or y % 12 == 0:
                c = mix(c, DARK, 0.3)
            n = rand.random() * 0.06 - 0.03
            put(px, w, H, x, y, tuple(max(0, min(255, int(v * (1 + n)))) for v in c))

    # Skirting
    rect(px, w, H, 0, floor_y - 6, w, floor_y - 2, mix(TRIM, DARK, 0.35))
    rect(px, w, H, 0, floor_y - 2, w, floor_y, DARK)
    return img, px


# --------------------------------------------------------------------- props

def strip_light(px, w, x, y=14, length=54, dead=False):
    body = mix(STEEL, DARK, 0.35)
    rect(px, w, H, x, y, x + length, y + 5, body)
    rect(px, w, H, x, y + 5, x + length, y + 7, (12, 12, 14) if dead else (226, 224, 206))
    rect(px, w, H, x + 4, y - 4, x + 6, y, mix(STEEL, DARK, 0.5))
    rect(px, w, H, x + length - 6, y - 4, x + length - 4, y, mix(STEEL, DARK, 0.5))


def doorway(px, w, x, floor_y, width=34, height=76, lit=False, colour=None):
    top = floor_y - height
    inner = colour or ((26, 34, 46) if lit else (8, 9, 12))
    vgrad(px, w, H, x, top, x + width, floor_y, mix(inner, (0, 0, 0), 0.2), inner)
    outline(px, w, H, x - 3, top - 3, x + width + 3, floor_y, TRIM)
    outline(px, w, H, x - 2, top - 2, x + width + 2, floor_y, mix(TRIM, DARK, 0.4))


def blast_door(px, w, x, floor_y, width=44, height=80, open_gap=0):
    top = floor_y - height
    vgrad(px, w, H, x, top, x + width, floor_y, mix(STEEL, DARK, 0.2), mix(STEEL, DARK, 0.55))
    for i in range(3):
        yy = top + 12 + i * 22
        rect(px, w, H, x + 3, yy, x + width - 3, yy + 3, mix(STEEL, DARK, 0.6))
    outline(px, w, H, x - 4, top - 4, x + width + 4, floor_y, mix(TRIM, RUST, 0.3))
    if open_gap:
        rect(px, w, H, x + width // 2 - open_gap // 2, top + 2,
             x + width // 2 + open_gap // 2, floor_y, (6, 7, 9))


def locker_bank(px, w, x, floor_y, count=4, unit=14, height=64):
    top = floor_y - height
    for i in range(count):
        lx = x + i * unit
        vgrad(px, w, H, lx, top, lx + unit - 1, floor_y, mix(TEAL, CONCRETE_HI, 0.4), mix(TEAL, DARK, 0.4))
        outline(px, w, H, lx, top, lx + unit - 1, floor_y, mix(DARK, TEAL, 0.35))
        rect(px, w, H, lx + unit - 5, top + 26, lx + unit - 3, top + 32, mix(STEEL, DARK, 0.2))
        for v in range(3):
            rect(px, w, H, lx + 3, top + 6 + v * 3, lx + unit - 5, top + 7 + v * 3, mix(DARK, TEAL, 0.5))


def desk(px, w, x, floor_y, width=54, height=26, with_monitor=False):
    top = floor_y - height
    rect(px, w, H, x, top, x + width, top + 4, mix(TRIM, RUST, 0.25))
    rect(px, w, H, x, top + 4, x + width, floor_y, mix(CONCRETE_HI, DARK, 0.45))
    rect(px, w, H, x + 3, top + 4, x + 6, floor_y, mix(DARK, TRIM, 0.2))
    rect(px, w, H, x + width - 6, top + 4, x + width - 3, floor_y, mix(DARK, TRIM, 0.2))
    if with_monitor:
        mw, mh = 22, 17
        mx = x + width // 2 - mw // 2
        my = top - mh
        rect(px, w, H, mx, my, mx + mw, my + mh, mix(STEEL, DARK, 0.45))
        rect(px, w, H, mx + 2, my + 2, mx + mw - 2, my + mh - 3, (16, 26, 24))
        rect(px, w, H, mx + mw // 2 - 3, my + mh, mx + mw // 2 + 3, top, mix(STEEL, DARK, 0.5))


def chair(px, w, x, floor_y, back=True, flip=False):
    seat_y = floor_y - 15
    rect(px, w, H, x, seat_y, x + 18, seat_y + 3, mix(TRIM, DARK, 0.3))
    rect(px, w, H, x + 2, seat_y + 3, x + 5, floor_y, mix(DARK, TRIM, 0.25))
    rect(px, w, H, x + 13, seat_y + 3, x + 16, floor_y, mix(DARK, TRIM, 0.25))
    if back:
        bx = x + (15 if flip else 1)
        rect(px, w, H, bx, seat_y - 18, bx + 3, seat_y, mix(TRIM, DARK, 0.3))
        rect(px, w, H, bx - (10 if flip else 0), seat_y - 20,
             bx + (3 if flip else 13), seat_y - 16, mix(TRIM, DARK, 0.25))


def shelving(px, w, x, floor_y, width=46, height=76, shelves=4):
    top = floor_y - height
    outline(px, w, H, x, top, x + width, floor_y, mix(STEEL, DARK, 0.4))
    for i in range(shelves):
        yy = top + 6 + i * ((height - 8) // shelves)
        rect(px, w, H, x + 1, yy, x + width - 1, yy + 2, mix(STEEL, DARK, 0.45))
        for b in range(rand.randint(2, 5)):
            bx = x + 3 + b * 9 + rand.randint(0, 2)
            bh = rand.randint(6, 11)
            rect(px, w, H, bx, yy - bh, bx + 6, yy, mix(RUST if b % 2 else TEAL, DARK, 0.35))


def pipes(px, w, x0, x1, y=26, runs=3):
    for i in range(runs):
        yy = y + i * 7
        c = mix(STEEL, RUST if i == 1 else DARK, 0.35)
        rect(px, w, H, x0, yy, x1, yy + 4, c)
        rect(px, w, H, x0, yy, x1, yy + 1, mix(c, (255, 255, 255), 0.18))
        for bx in range(x0 + 20, x1, 64):
            rect(px, w, H, bx, yy - 2, bx + 5, yy + 6, mix(c, DARK, 0.4))


def monitor_wall(px, w, x, floor_y, cols=4, rows=2):
    mw, mh = 26, 20
    top = floor_y - 96
    for r in range(rows):
        for c in range(cols):
            mx = x + c * (mw + 3)
            my = top + r * (mh + 3)
            rect(px, w, H, mx, my, mx + mw, my + mh, mix(STEEL, DARK, 0.5))
            on = (r * cols + c) % 3 != 1
            rect(px, w, H, mx + 2, my + 2, mx + mw - 2, my + mh - 2,
                 (18, 30, 28) if on else (9, 10, 12))
            if on:
                for sl in range(my + 3, my + mh - 3, 3):
                    rect(px, w, H, mx + 3, sl, mx + mw - 3, sl + 1, (24, 42, 38))


def lab_bench(px, w, x, floor_y, width=70):
    top = floor_y - 30
    rect(px, w, H, x, top, x + width, top + 4, mix((176, 178, 172), DARK, 0.45))
    rect(px, w, H, x, top + 4, x + width, floor_y, mix(CONCRETE_HI, DARK, 0.5))
    for i in range(3):
        rect(px, w, H, x + 6 + i * 20, top + 8, x + 20 + i * 20, top + 9, mix(DARK, TRIM, 0.3))


def centrifuge(px, w, x, floor_y, spinning=True):
    top = floor_y - 52
    rect(px, w, H, x, top + 16, x + 30, floor_y, mix(STEEL, DARK, 0.35))
    rect(px, w, H, x + 2, top, x + 28, top + 18, mix(STEEL, CONCRETE_HI, 0.3))
    rect(px, w, H, x + 6, top + 4, x + 24, top + 14, (14, 18, 20))
    if spinning:
        rect(px, w, H, x + 24, top + 22, x + 27, top + 25, (150, 60, 40))


def stairs(px, w, x, floor_y, steps=9, rise=9, run=16, down=True):
    for i in range(steps):
        sx = x + i * run
        sy = floor_y + (i * rise if down else -i * rise)
        rect(px, w, H, sx, sy, sx + run, sy + rise, mix(CONCRETE_HI, DARK, 0.4))
        rect(px, w, H, sx, sy, sx + run, sy + 2, mix(TRIM, DARK, 0.2))


def containment_ring(px, w, cx, floor_y, radius=62):
    """The aperture housing. The aperture itself is a light in the scene JSON,
    not paint, so the lighting system can make it breathe."""
    for a in range(0, 360):
        rad = math.radians(a)
        for t in range(0, 9):
            r = radius + t
            x = int(cx + math.cos(rad) * r)
            y = int(floor_y - 10 - math.sin(rad) * r * 0.92)
            if y > floor_y:
                continue
            put(px, w, H, x, y, mix(STEEL, DARK, 0.15 + t * 0.06))
    for a in range(0, 360, 45):
        rad = math.radians(a)
        x = int(cx + math.cos(rad) * (radius + 10))
        y = int(floor_y - 10 - math.sin(rad) * (radius + 10) * 0.92)
        rect(px, w, H, x - 4, y - 4, x + 4, y + 4, mix(STEEL, RUST, 0.35))
    # cable runs to the floor
    for off in (-radius - 6, radius + 4):
        rect(px, w, H, cx + off, floor_y - 22, cx + off + 3, floor_y, mix(DARK, STEEL, 0.4))


# ------------------------------------------------------------------ layers

def fore_beam(w, posts=(), beam_h=13):
    """Foreground occlusion: a ceiling run and any pillars, drawn over the player."""
    img = Image.new('RGBA', (w, H), (0, 0, 0, 0))
    px = img.load()
    vgrad(px, w, H, 0, 0, w, beam_h, (16, 17, 20), (30, 32, 37))
    rect(px, w, H, 0, beam_h, w, beam_h + 1, DARK)
    for x in posts:
        vgrad(px, w, H, x, 0, x + 16, H, (40, 43, 50), (14, 15, 18))
        rect(px, w, H, x, 0, x + 2, H, mix(TRIM, DARK, 0.2))
        rect(px, w, H, x + 14, 0, x + 16, H, DARK)
    return img


# ------------------------------------------------------------------- scenes

def scene_gate(w=1152, floor_y=176):
    """Exterior: the barrier, the empty booth, and a car park that is still full."""
    img = Image.new('RGBA', (w, H), (0, 0, 0, 255))
    px = img.load()
    for y in range(H):
        c = mix(NIGHT_SKY_TOP, NIGHT_SKY_LOW, min(1.0, y / floor_y) ** 1.4)
        for x in range(w):
            put(px, w, H, x, y, c)
    star = random.Random(31)
    for _ in range(240):
        x, y = star.randrange(0, w), star.randrange(0, int(floor_y * 0.65))
        v = star.randint(90, 205)
        put(px, w, H, x, y, (v, v, min(255, v + 22)))

    for i in range(34):
        bx = 14 + i * 34
        hgt = 40 + (i * 17) % 34
        for tier in range(4):
            t = tier / 4
            half = int(22 * (1 - t * 0.8)) + 1
            for y in range(int(floor_y - 12 - hgt * (t + 0.25)), int(floor_y - 12 - hgt * t)):
                for x in range(bx - half, bx + half):
                    put(px, w, H, x, y, PINE)

    # tarmac
    for y in range(floor_y, H):
        t = (y - floor_y) / max(1, H - floor_y)
        for x in range(w):
            c = mix((20, 21, 25), (38, 39, 45), t + rand.random() * 0.12)
            put(px, w, H, x, y, c)
    for x in range(40, w, 96):
        rect(px, w, H, x, floor_y + 22, x + 30, floor_y + 25, mix(WARN, DARK, 0.35))

    # chain-link fence and gate
    for x in range(0, 360, 3):
        for y in range(floor_y - 74, floor_y):
            if (x + y) % 6 < 2:
                put(px, w, H, x, y, mix(STEEL, DARK, 0.45))
    for x in (10, 120, 230, 340):
        rect(px, w, H, x, floor_y - 82, x + 5, floor_y, mix(STEEL, DARK, 0.25))
        rect(px, w, H, x - 1, floor_y - 86, x + 6, floor_y - 82, (120, 40, 34))

    # guard booth, door ajar, light on
    bx = 386
    vgrad(px, w, H, bx, floor_y - 78, bx + 62, floor_y, mix(CONCRETE_HI, DARK, 0.25), mix(CONCRETE_LO, DARK, 0.4))
    rect(px, w, H, bx - 4, floor_y - 84, bx + 66, floor_y - 76, TRIM)
    rect(px, w, H, bx + 8, floor_y - 66, bx + 40, floor_y - 40, (96, 82, 44))
    outline(px, w, H, bx + 8, floor_y - 66, bx + 40, floor_y - 40, TRIM)
    doorway(px, w, bx + 44, floor_y, width=16, height=54, lit=True)

    # raised barrier
    rect(px, w, H, 470, floor_y - 30, 476, floor_y, mix(STEEL, DARK, 0.3))
    for i in range(46):
        x = 476 + int(i * 1.6)
        y = floor_y - 30 - int(i * 1.15)
        rect(px, w, H, x, y, x + 3, y + 4, (170, 60, 46) if (i // 6) % 2 else (206, 206, 196))

    # parked cars, simple silhouettes -- the point is that they are all still here
    for i in range(7):
        cx = 590 + i * 74
        cw, ch = 58, 22
        top = floor_y - ch
        body = mix((150, 150, 142), DARK, 0.55 + (i % 3) * 0.08)
        rect(px, w, H, cx, top + 7, cx + cw, floor_y - 3, body)
        rect(px, w, H, cx + 12, top, cx + cw - 14, top + 8, mix(body, DARK, 0.25))
        rect(px, w, H, cx + 15, top + 2, cx + cw - 17, top + 7, (24, 30, 40))
        rect(px, w, H, cx + 6, floor_y - 5, cx + 14, floor_y, DARK)
        rect(px, w, H, cx + cw - 15, floor_y - 5, cx + cw - 7, floor_y, DARK)
    return img


def scene_lobby(w=768, floor_y=180):
    img, px = interior_base(w, floor_y)
    pipes(px, w, 0, w, y=22, runs=2)
    for x in (60, 250, 470, 660):
        strip_light(px, w, x, dead=(x == 250))
    # coat hooks with coats still on them
    rect(px, w, H, 54, 88, 168, 91, TRIM)
    for i in range(5):
        cx = 60 + i * 22
        rect(px, w, H, cx, 91, cx + 3, 97, mix(STEEL, DARK, 0.3))
        col = [(52, 46, 60), (40, 52, 48), (60, 44, 38), (36, 42, 58), (48, 40, 44)][i]
        vgrad(px, w, H, cx - 7, 95, cx + 11, 143, col, mix(col, DARK, 0.55))
    desk(px, w, 246, floor_y, width=120, height=32)
    rect(px, w, H, 268, floor_y - 38, 300, floor_y - 32, (168, 164, 150))  # open ledger
    rect(px, w, H, 312, floor_y - 40, 328, floor_y - 32, mix(DARK, STEEL, 0.3))  # phone
    # wall clock
    ccx, ccy, r = 452, 74, 17
    for a in range(0, 360):
        rad = math.radians(a)
        for t in range(3):
            put(px, w, H, int(ccx + math.cos(rad) * (r + t)), int(ccy + math.sin(rad) * (r + t)), TRIM)
    for yy in range(ccy - r, ccy + r):
        for xx in range(ccx - r, ccx + r):
            if (xx - ccx) ** 2 + (yy - ccy) ** 2 < r * r:
                put(px, w, H, xx, yy, (198, 196, 182))
    rect(px, w, H, ccx - 1, ccy - 11, ccx + 1, ccy + 1, DARK)      # hour hand, up-ish
    rect(px, w, H, ccx - 12, ccy - 1, ccx + 1, ccy + 1, DARK)      # minute hand
    # turnstile
    rect(px, w, H, 556, floor_y - 40, 566, floor_y, mix(STEEL, DARK, 0.3))
    for a in (0, 120, 240):
        rad = math.radians(a)
        for k in range(26):
            put(px, w, H, int(561 + math.cos(rad) * k), int(floor_y - 34 + math.sin(rad) * k * 0.4), STEEL)
    rect(px, w, H, 596, floor_y - 46, 604, floor_y - 34, mix(STEEL, DARK, 0.2))
    rect(px, w, H, 598, floor_y - 43, 602, floor_y - 40, (170, 50, 40))
    doorway(px, w, 690, floor_y, width=40, height=84, lit=True)
    return img


def scene_office(w=1152, floor_y=178):
    img, px = interior_base(w, floor_y)
    pipes(px, w, 0, w, y=20, runs=2)
    for x in (40, 210, 380, 560, 740, 920, 1080):
        strip_light(px, w, x, dead=(x in (380, 920)))
    doorway(px, w, 20, floor_y, width=36, height=80, lit=True)
    for i in range(5):
        dx = 110 + i * 190
        desk(px, w, dx, floor_y, width=86, height=28, with_monitor=(i % 2 == 0))
        chair(px, w, dx + 92, floor_y, flip=(i % 2 == 1))
    shelving(px, w, 1064, floor_y, width=60, height=92, shelves=5)
    doorway(px, w, 1098, floor_y, width=36, height=80)
    return img


def scene_canteen(w=768, floor_y=180):
    img, px = interior_base(w, floor_y, wall_hi=(50, 50, 46))
    for x in (60, 300, 560):
        strip_light(px, w, x, dead=(x == 300))
    doorway(px, w, 16, floor_y, width=36, height=80, lit=True)
    for i in range(3):
        tx = 130 + i * 190
        rect(px, w, H, tx, floor_y - 26, tx + 96, floor_y - 22, mix((150, 150, 140), DARK, 0.5))
        rect(px, w, H, tx + 44, floor_y - 22, tx + 52, floor_y, mix(STEEL, DARK, 0.4))
        rect(px, w, H, tx + 22, floor_y - 2, tx + 74, floor_y, mix(STEEL, DARK, 0.5))
        for t in range(2):
            trx = tx + 12 + t * 48
            rect(px, w, H, trx, floor_y - 30, trx + 26, floor_y - 26, mix(RUST, DARK, 0.4))
        chair(px, w, tx - 22, floor_y)
        chair(px, w, tx + 100, floor_y, flip=True)
    # vending machine
    vx = 660
    vgrad(px, w, H, vx, floor_y - 88, vx + 52, floor_y, mix(TEAL, CONCRETE_HI, 0.3), mix(TEAL, DARK, 0.55))
    rect(px, w, H, vx + 5, floor_y - 80, vx + 36, floor_y - 26, (16, 22, 24))
    for r in range(4):
        rect(px, w, H, vx + 7, floor_y - 76 + r * 13, vx + 34, floor_y - 74 + r * 13, mix(STEEL, DARK, 0.4))
    rect(px, w, H, vx + 40, floor_y - 70, vx + 48, floor_y - 40, mix(STEEL, DARK, 0.25))
    return img


def scene_lab(w=1152, floor_y=178):
    img, px = interior_base(w, floor_y, wall_hi=(48, 52, 56))
    pipes(px, w, 0, w, y=18, runs=3)
    for x in (50, 240, 430, 640, 850, 1050):
        strip_light(px, w, x, dead=(x == 640))
    doorway(px, w, 18, floor_y, width=36, height=80, lit=True)
    for i in range(3):
        lab_bench(px, w, 120 + i * 210, floor_y, width=140)
    centrifuge(px, w, 190, floor_y)
    centrifuge(px, w, 420, floor_y, spinning=False)
    # dosimeter rack: a grid of badges, all of them dark
    rx = 700
    outline(px, w, H, rx, 96, rx + 96, 150, TRIM)
    for r in range(3):
        for c in range(8):
            bx = rx + 5 + c * 11
            by = 101 + r * 16
            rect(px, w, H, bx, by, bx + 8, by + 12, mix(STEEL, DARK, 0.3))
            rect(px, w, H, bx + 2, by + 3, bx + 6, by + 9, (10, 10, 12))
    # sample fridge
    fx = 840
    vgrad(px, w, H, fx, floor_y - 96, fx + 60, floor_y, mix(STEEL, CONCRETE_HI, 0.4), mix(STEEL, DARK, 0.5))
    rect(px, w, H, fx + 6, floor_y - 88, fx + 54, floor_y - 44, (20, 34, 40))
    rect(px, w, H, fx + 50, floor_y - 70, fx + 56, floor_y - 50, mix(STEEL, DARK, 0.2))
    shelving(px, w, 950, floor_y, width=60, height=90, shelves=5)
    doorway(px, w, 1090, floor_y, width=38, height=82)
    return img


def scene_security(w=768, floor_y=180):
    img, px = interior_base(w, floor_y, wall_lo=(20, 22, 27))
    for x in (60, 420):
        strip_light(px, w, x, dead=True)
    strip_light(px, w, 240)
    doorway(px, w, 18, floor_y, width=36, height=80, lit=True)
    monitor_wall(px, w, 180, floor_y, cols=5, rows=2)
    desk(px, w, 176, floor_y, width=150, height=30)
    chair(px, w, 250, floor_y)
    # filing cabinet
    cx = 560
    vgrad(px, w, H, cx, floor_y - 70, cx + 46, floor_y, mix(TEAL, CONCRETE_HI, 0.35), mix(TEAL, DARK, 0.5))
    for d in range(3):
        yy = floor_y - 66 + d * 22
        outline(px, w, H, cx + 3, yy, cx + 43, yy + 20, mix(DARK, TEAL, 0.4))
        rect(px, w, H, cx + 18, yy + 8, cx + 28, yy + 11, mix(STEEL, DARK, 0.2))
    locker_bank(px, w, 640, floor_y, count=3)
    return img


def scene_stairwell(w=768, floor_y=150):
    img, px = interior_base(w, floor_y, wall_lo=(18, 19, 24), wall_hi=(36, 38, 45))
    strip_light(px, w, 90, dead=True)
    strip_light(px, w, 400)
    doorway(px, w, 20, floor_y, width=36, height=76, lit=True)
    # store room, barricaded from the inside
    sx = 150
    doorway(px, w, sx, floor_y, width=42, height=78, colour=(14, 16, 20))
    for i in range(4):
        yy = floor_y - 66 + i * 17
        rect(px, w, H, sx - 6, yy, sx + 48, yy + 6, mix(RUST, DARK, 0.35))
    # the descent -- 6px rises so the walk climbs them without a jump
    stairs(px, w, 420, floor_y, steps=8, rise=6, run=16)
    for i in range(8):
        rect(px, w, H, 420 + i * 16, floor_y + i * 6 - 28, 423 + i * 16, floor_y + i * 6, mix(STEEL, DARK, 0.35))
    lower = floor_y + 48
    rect(px, w, H, 548, lower, w, H, mix(FLOOR_LO, FLOOR_HI, 0.4))
    # blast door at the bottom, with the keypad beside it
    blast_door(px, w, 610, lower, width=52, height=76)
    rect(px, w, H, 672, lower - 46, 682, lower - 30, mix(STEEL, DARK, 0.2))
    rect(px, w, H, 674, lower - 43, 680, lower - 36, (40, 90, 70))
    return img


def scene_sublevel(w=1152, floor_y=186):
    img, px = interior_base(w, floor_y, wall_lo=(14, 15, 20), wall_hi=(30, 32, 40))
    pipes(px, w, 0, w, y=16, runs=3)
    strip_light(px, w, 60, dead=True)
    strip_light(px, w, 980, dead=True)
    doorway(px, w, 24, floor_y, width=40, height=82)
    for i in range(2):
        rect(px, w, H, 150 + i * 90, floor_y - 54, 190 + i * 90, floor_y, mix(STEEL, DARK, 0.45))
        rect(px, w, H, 154 + i * 90, floor_y - 48, 186 + i * 90, floor_y - 20, (16, 24, 26))
    containment_ring(px, w, 640, floor_y, radius=66)
    # cable runs across the floor toward the ring
    for i in range(5):
        yy = floor_y + 4 + i * 5
        for x in range(300, 980):
            if (x + i * 9) % 40 > 3:
                put(px, w, H, x, yy, mix(DARK, STEEL, 0.25))
    lab_bench(px, w, 880, floor_y, width=110)
    return img


SCENES = {
    'station_gate': (scene_gate, 1152, (), True),
    'station_lobby': (scene_lobby, 768, (), False),
    'office_wing': (scene_office, 1152, (472,), False),
    'canteen': (scene_canteen, 768, (), False),
    'laboratory': (scene_lab, 1152, (600,), False),
    'security_room': (scene_security, 768, (), False),
    'stairwell': (scene_stairwell, 768, (), False),
    'sublevel_3': (scene_sublevel, 1152, (320, 960), False),
}


def save_mono(img, path):
    """
    Save greyscale.

    The palette constants above are already grey, but both generators also
    place inline colours -- warning LEDs, the moon, lit window glass, monitor
    phosphor. Converting on save catches those without hunting each one, and
    keeps the deliberate greys intact: with a neutral tone curve a grey value
    maps to itself, so this only touches the accents.
    """
    from monochrome import to_mono
    to_mono(img, lift=1.0, contrast=1.0, levels=48, dither=0.5).save(path)


def main():
    for name, (fn, w, posts, exterior) in SCENES.items():
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        save_mono(fn(w), os.path.join(d, 'room.png'))
        if not exterior:
            save_mono(fore_beam(w, posts), os.path.join(d, 'fore.png'))
        print(f'  backdrops/{name}/  {w}x{H}')


if __name__ == '__main__':
    main()
