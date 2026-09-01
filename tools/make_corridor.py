#!/usr/bin/env python3
"""
Generate the backdrop layers for the `cabin_landing` and `cabin_drive` scenes.

Unlike everything in art/refs/, this art is procedural. It exists so the engine
ships with a second, *wider than the screen* scene -- which is what proves
camera scrolling, parallax layering and scene-to-scene travel. They are deliberately
plain: replace the folders under assets/backdrops/ with painted art when you
have it and the scene JSON keeps working unchanged.

    python3 tools/make_corridor.py


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
OUT = os.path.join(ROOT, 'assets', 'backdrops', 'cabin_landing')

W, H = 768, 216
FLOOR_Y = 168

# Sampled from the bedroom reference so the two scenes sit in the same world.
WALL_DARK = (30, 30, 30)
WALL_MID = (52, 52, 52)
WALL_LIT = (72, 72, 72)
FLOOR_DARK = (22, 22, 22)
FLOOR_MID = (42, 42, 42)
TRIM = (80, 80, 80)
NIGHT = (38, 38, 38)

rand = random.Random(4242)


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def build_wall():
    img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    px = img.load()

    for y in range(H):
        for x in range(W):
            if y < FLOOR_Y:
                # Horizontal log courses, darker toward the ceiling.
                course = (y // 11) % 2
                depth = 1 - (y / FLOOR_Y) * 0.55
                base = mix(WALL_DARK, WALL_MID, depth)
                if course:
                    base = mix(base, WALL_LIT, 0.16)
                # Seam line between courses.
                if y % 11 == 0:
                    base = mix(base, WALL_DARK, 0.7)
                grain = rand.random() * 0.07 - 0.035
                px[x, y] = (
                    max(0, min(255, int(base[0] * (1 + grain)))),
                    max(0, min(255, int(base[1] * (1 + grain)))),
                    max(0, min(255, int(base[2] * (1 + grain)))),
                    255,
                )
            else:
                # Floorboards receding toward the wall.
                run = (y - FLOOR_Y) / (H - FLOOR_Y)
                base = mix(FLOOR_DARK, FLOOR_MID, 0.25 + run * 0.6)
                if (x + (y // 3) * 7) % 46 < 1:
                    base = mix(base, FLOOR_DARK, 0.8)
                if y % 9 == 0:
                    base = mix(base, FLOOR_DARK, 0.35)
                grain = rand.random() * 0.06 - 0.03
                px[x, y] = (
                    max(0, min(255, int(base[0] * (1 + grain)))),
                    max(0, min(255, int(base[1] * (1 + grain)))),
                    max(0, min(255, int(base[2] * (1 + grain)))),
                    255,
                )

    # Skirting board along the floor line.
    for y in range(FLOOR_Y - 7, FLOOR_Y):
        for x in range(W):
            t = (y - (FLOOR_Y - 7)) / 7
            px[x, y] = (*mix(TRIM, WALL_DARK, t * 0.8), 255)

    # A window at the far end, and the moonlight it lets in.
    win = (300, 46, 372, 128)
    for y in range(win[1], win[3]):
        for x in range(win[0], win[2]):
            t = (y - win[1]) / (win[3] - win[1])
            px[x, y] = (*mix(NIGHT, (34, 44, 88), 1 - t * 0.7), 255)
    for y in range(win[1], win[3]):
        for x in range(win[0], win[2]):
            if (x - win[0]) % 36 < 2 or (y - win[1]) % 40 < 2:
                px[x, y] = (*TRIM, 255)
    for y in range(win[1] - 4, win[3] + 4):
        for x in range(win[0] - 4, win[2] + 4):
            edge = not (win[0] <= x < win[2] and win[1] <= y < win[3])
            if edge and 0 <= x < W and 0 <= y < H:
                px[x, y] = (*TRIM, 255)

    # Doorway at the right end -- the way out to the car.
    door = (688, 62, 744, FLOOR_Y)
    for y in range(door[1], door[3]):
        for x in range(door[0], door[2]):
            px[x, y] = (*mix((16, 12, 9), (30, 22, 15), (y - door[1]) / (door[3] - door[1])), 255)
    for y in range(door[1] - 5, door[3]):
        for x in range(door[0] - 5, door[2] + 5):
            edge = not (door[0] <= x < door[2] and door[1] <= y < door[3])
            if edge and 0 <= x < W and 0 <= y < H:
                px[x, y] = (*TRIM, 255)

    # Bedroom doorway at the left, so travelling back has somewhere to be.
    back = (48, 70, 96, FLOOR_Y)
    for y in range(back[1], back[3]):
        for x in range(back[0], back[2]):
            px[x, y] = (*mix((20, 14, 10), (34, 25, 17), (y - back[1]) / (back[3] - back[1])), 255)
    for y in range(back[1] - 5, back[3]):
        for x in range(back[0] - 5, back[2] + 5):
            edge = not (back[0] <= x < back[2] and back[1] <= y < back[3])
            if edge and 0 <= x < W and 0 <= y < H:
                px[x, y] = (*TRIM, 255)

    return img


def build_far():
    """A narrow, repeating haze layer that drifts slowly behind the wall."""
    img = Image.new('RGBA', (128, H), (0, 0, 0, 0))
    px = img.load()
    for y in range(H):
        for x in range(128):
            v = 0.5 + 0.5 * math.sin(x * 0.05 + y * 0.02)
            a = int(26 * v * (1 - y / H))
            px[x, y] = (18, 24, 46, a)
    return img


def build_fore():
    """A ceiling beam and a post that pass in front of the character."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    px = img.load()
    for y in range(0, 16):
        for x in range(W):
            px[x, y] = (*mix((18, 13, 10), (30, 22, 15), y / 16), 255)
    post = (404, 0, 424, H)
    for y in range(post[1], post[3]):
        for x in range(post[0], post[2]):
            t = abs((x - post[0]) / (post[2] - post[0]) - 0.5) * 2
            px[x, y] = (*mix((40, 29, 20), (14, 10, 7), t), 255)
    return img


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


def build_corridor():
    os.makedirs(OUT, exist_ok=True)
    save_mono(build_far(), os.path.join(OUT, 'far.png'))
    save_mono(build_wall(), os.path.join(OUT, 'wall.png'))
    save_mono(build_fore(), os.path.join(OUT, 'fore.png'))
    print(f'  backdrops/cabin_landing/  far.png wall.png fore.png  ({W}x{H})')


# --------------------------------------------------------------- exterior

SKY_TOP = (12, 12, 12)
SKY_LOW = (44, 44, 44)
PINE = (8, 8, 8)
PINE_FAR = (18, 18, 18)
GRAVEL = (38, 38, 38)
CABIN = (34, 34, 34)
EX_GROUND_Y = 172


def _pine(px, x0, base_y, height, width, colour, w_limit, h_limit):
    """One silhouetted conifer, drawn as stacked tapering bands."""
    tiers = max(3, height // 14)
    for tier in range(tiers):
        t = tier / tiers
        half = int(width * (1 - t * 0.82) / 2) + 1
        top = int(base_y - height * (t + 1 / tiers))
        bottom = int(base_y - height * t) + 2
        for y in range(top, bottom):
            if not (0 <= y < h_limit):
                continue
            span = int(half * (1 - (y - top) / max(1, bottom - top) * 0.25))
            for x in range(x0 - span, x0 + span):
                if 0 <= x < w_limit:
                    px[x, y] = (*colour, 255)
    for y in range(base_y - 4, base_y):
        for x in range(x0 - 1, x0 + 2):
            if 0 <= x < w_limit and 0 <= y < h_limit:
                px[x, y] = (*colour, 255)


def build_exterior_sky():
    img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    px = img.load()
    for y in range(H):
        t = min(1.0, y / EX_GROUND_Y)
        base = mix(SKY_TOP, SKY_LOW, t ** 1.4)
        for x in range(W):
            px[x, y] = (*base, 255)

    star = random.Random(77)
    for _ in range(190):
        x = star.randrange(0, W)
        y = star.randrange(0, int(EX_GROUND_Y * 0.72))
        v = star.randint(90, 210)
        px[x, y] = (v, v, min(255, v + 24), 255)

    # Moon, matching the one in the bedroom window.
    mx, my, mr = 610, 44, 11
    for y in range(my - mr - 6, my + mr + 6):
        for x in range(mx - mr - 6, mx + mr + 6):
            if not (0 <= x < W and 0 <= y < H):
                continue
            d = math.hypot(x - mx, y - my)
            if d <= mr:
                px[x, y] = (226, 228, 214, 255)
            elif d <= mr + 6:
                glow = 1 - (d - mr) / 6
                px[x, y] = (*mix(px[x, y][:3], (150, 165, 200), glow * 0.5), 255)

    for i in range(26):
        _pine(px, 20 + i * 30 + (i % 3) * 7, EX_GROUND_Y - 14,
              46 + (i * 13) % 34, 26, PINE_FAR, W, H)
    return img


def build_exterior_ground():
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    px = img.load()

    for i in range(15):
        _pine(px, 30 + i * 54 + (i % 4) * 9, EX_GROUND_Y + 2,
              74 + (i * 23) % 46, 40, PINE, W, H)

    for y in range(EX_GROUND_Y, H):
        t = (y - EX_GROUND_Y) / (H - EX_GROUND_Y)
        base = mix((18, 20, 24), GRAVEL, t)
        for x in range(W):
            n = rand.random()
            c = mix(base, (46, 46, 52), n * 0.35)
            px[x, y] = (*c, 255)

    # The cabin wall the player steps out of, with a lit doorway.
    for y in range(30, EX_GROUND_Y):
        for x in range(0, 150):
            t = (y - 30) / (EX_GROUND_Y - 30)
            edge = 1 - min(1, (150 - x) / 40)
            px[x, y] = (*mix(CABIN, (14, 10, 8), t * 0.5 + edge * 0.3), 255)
    # Roof edge: a lit lip over a dark eave, rather than a flat bright bar.
    for y in range(26, 32):
        for x in range(0, 168):
            lip = 1 - (y - 26) / 6
            px[x, y] = (*mix((28, 21, 15), TRIM, lip * 0.55), 255)
    for y in range(32, 40):
        for x in range(0, 160):
            shade = (y - 32) / 8
            px[x, y] = (*mix((12, 9, 7), CABIN, shade), 255)
    door = (54, 74, 104, EX_GROUND_Y)
    for y in range(door[1], door[3]):
        for x in range(door[0], door[2]):
            px[x, y] = (*mix((92, 68, 38), (40, 30, 18), (y - door[1]) / (door[3] - door[1])), 255)
    for y in range(door[1] - 4, door[3]):
        for x in range(door[0] - 4, door[2] + 4):
            if not (door[0] <= x < door[2] and door[1] <= y < door[3]):
                if 0 <= x < W and 0 <= y < H:
                    px[x, y] = (*TRIM, 255)
    return img


def build_exterior():
    os.makedirs(os.path.join(ROOT, 'assets', 'backdrops', 'cabin_drive'), exist_ok=True)
    out = os.path.join(ROOT, 'assets', 'backdrops', 'cabin_drive')
    save_mono(build_exterior_sky(), os.path.join(out, 'sky.png'))
    save_mono(build_exterior_ground(), os.path.join(out, 'ground.png'))
    print(f'  backdrops/cabin_drive/  sky.png ground.png  ({W}x{H})')


def main():
    build_corridor()
    build_exterior()


if __name__ == '__main__':
    main()
