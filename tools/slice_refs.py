#!/usr/bin/env python3
"""
Derive game-ready assets from the reference art in art/refs/.

The references are large upscales (2688x1520) of lower-resolution pixel art.
This script recovers usable, correctly-scaled assets from them and writes
everything under assets/. It is safe to re-run: it always regenerates from
art/refs/ and overwrites its own output.

    python3 tools/slice_refs.py

Add new reference art by appending an entry to one of the tables below rather
than by hand-cropping in an image editor, so the pipeline stays reproducible.
"""

import json
import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required:  pip install pillow")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from monochrome import to_mono  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, "art", "refs")
OUT = os.path.join(ROOT, "assets")

# The game renders at this native resolution and integer-scales to the window.
# 384x216 is the true pixel grid of the painted references (they are 7x upscales)
# and multiplies cleanly to 1920x1080 at 5x.
SCREEN_W, SCREEN_H = 384, 216

# How tall the protagonist stands, in native pixels. The bedroom reference is
# painted as a close interior, so the character reads large; tune here and
# re-run rather than scaling at draw time.
PLAYER_H = 88
PORTRAIT_H = 56

# The reference for this project is Midnight Scenes, whose early episodes are
# monochrome. Set False to derive the colour assets instead; the scene files and
# the engine are unchanged either way, so the two can be compared directly.
MONO = True


def ref(name):
    return Image.open(os.path.join(REFS, name)).convert("RGBA")


def ensure(*parts):
    d = os.path.join(OUT, *parts)
    os.makedirs(d, exist_ok=True)
    return d


def fit(img, w=None, h=None):
    """Resize preserving aspect. LANCZOS keeps the shading of the source art
    coherent when reducing by a large, non-integer factor; a nearest-neighbour
    reduction here would alias the dithering into noise."""
    if w is None:
        w = max(1, round(img.width * h / img.height))
    if h is None:
        h = max(1, round(img.height * w / img.width))
    return img.resize((w, h), Image.LANCZOS)


def crisp(img, colors=48, levels=24):
    """
    Snap to a limited palette so the reduced art reads as pixel art again
    instead of as a soft photograph.

    In monochrome this hands over to tools/monochrome.py, which does its own
    quantisation on a grey ramp. Converting *after* a colour quantisation would
    be worse: the adaptive palette spends its entries separating hues that are
    about to be discarded, leaving fewer distinct values where they matter.
    """
    if MONO:
        out = to_mono(img, levels=levels)
        out.putalpha(img.convert("RGBA").getchannel("A"))
        return out
    rgb = img.convert("RGB").quantize(colors=colors, method=Image.MEDIANCUT,
                                      dither=Image.NONE).convert("RGB")
    out = rgb.convert("RGBA")
    out.putalpha(img.getchannel("A"))
    return out


def cut_bg(img, tol=34, feather_edges=True):
    """Knock out the flat plate the sheets are laid out on. The plate is
    textured rather than a single flat value, so match within a tolerance and
    only from the outside in, which protects same-toned pixels inside the
    subject (the lab coat's shadows sit close to the grey)."""
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    # Plate colour sampled from the corners of the crop.
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    bg = tuple(sum(c[i] for c in corners) // 4 for i in range(3))

    def near(p):
        return abs(p[0] - bg[0]) + abs(p[1] - bg[1]) + abs(p[2] - bg[2]) <= tol

    # Flood from the border so enclosed pixels of a similar tone survive.
    seen = bytearray(w * h)
    stack = [(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)] \
        + [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)]
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= w or y >= h:
            continue
        i = y * w + x
        if seen[i]:
            continue
        if not near(px[x, y]):
            continue
        seen[i] = 1
        px[x, y] = (0, 0, 0, 0)
        stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return img


def trim(img):
    box = img.getbbox()
    return img.crop(box) if box else img


# ---------------------------------------------------------------- backdrops

def build_backdrops():
    d = ensure("backdrops", "cabin_bedroom")
    room = crisp(fit(ref("cabin_bedroom_night.png"), w=SCREEN_W), colors=64)
    room = room.crop((0, 0, SCREEN_W, min(SCREEN_H, room.height)))
    if room.height < SCREEN_H:  # pad from the floor colour if the aspect is short
        pad = Image.new("RGBA", (SCREEN_W, SCREEN_H), room.getpixel((2, room.height - 2)))
        pad.paste(room, (0, 0))
        room = pad
    room.save(os.path.join(d, "room.png"))
    print(f"  backdrops/cabin_bedroom/room.png  {room.width}x{room.height}")


# ------------------------------------------------------------------- stills

# Cutscenes render on their own surface at twice the gameplay resolution, so
# their stills are derived at that size rather than at the game's. This is where
# the detail in the 2688x1520 references actually gets used.
STILL_W, STILL_H = SCREEN_W * 2, SCREEN_H * 2


def build_stills():
    d = ensure("stills")

    def still_from(name, out, focus=None):
        """Derive one still. `focus` is a crop box in source pixels, for
        framing a shot tighter than the whole reference."""
        img = ref(name)
        if focus:
            img = img.crop(focus)
        img = crisp(fit(img, w=STILL_W), colors=64, levels=40)
        if img.height > STILL_H:
            top = (img.height - STILL_H) // 2
            img = img.crop((0, top, STILL_W, top + STILL_H))
        elif img.height < STILL_H:
            pad = Image.new("RGBA", (STILL_W, STILL_H), (0, 0, 0, 255))
            pad.paste(img, (0, (STILL_H - img.height) // 2))
            img = pad
        img.convert("RGB").save(os.path.join(d, out))
        print(f"  stills/{out}  {img.width}x{img.height}")

    still_from("facility_exterior_night.png", "facility_exterior_night.png")
    # The room he is about to leave, framed on the bed and the window.
    still_from("cabin_bedroom_night.png", "cabin_prologue.png")


# ------------------------------------------------------------------ sprites

# Boxes measured from the reference by projection analysis, not by eye.
BODIES = {
    "front": (155, 116, 587, 1378),
    "side":  (667, 122, 902, 1380),
    "back":  (925, 123, 1342, 1378),
}

PORTRAITS = {
    "neutral":  (1757, 614, 2019, 929),
    "stern":    (2037, 614, 2301, 929),
    "worried":  (2317, 614, 2582, 929),
    "resolute": (1893, 959, 2160, 1275),
    "smile":    (2176, 959, 2438, 1275),
}


def build_scientist():
    sheet = ref("scientist_turnaround.png")
    d = ensure("sprites", "scientist")
    frames = {}
    for name, box in BODIES.items():
        img = trim(cut_bg(sheet.crop(box)))
        img = crisp(fit(img, h=PLAYER_H), colors=40)
        frames[name] = img

    # Pack the three views into one sheet so the loader exercises the same
    # atlas path that hand-authored walk cycles will use.
    pad = 1
    w = sum(f.width for f in frames.values()) + pad * (len(frames) + 1)
    h = max(f.height for f in frames.values()) + pad * 2
    atlas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    rects, x = {}, pad
    for name, f in frames.items():
        atlas.paste(f, (x, pad + (h - pad * 2 - f.height)))
        rects[name] = {"x": x, "y": pad + (h - pad * 2 - f.height),
                       "w": f.width, "h": f.height}
        x += f.width + pad
    atlas.save(os.path.join(d, "scientist.png"))

    # A stand-in idle/walk built from the side view. Real hand-drawn sheets
    # replace this by dropping in a new png + json with the same clip names.
    json.dump({
        "image": "sprites/scientist/scientist.png",
        "origin": "bottom-center",
        "frames": rects,
        "clips": {
            "idle":   {"frames": ["side"], "fps": 1, "loop": True},
            "walk":   {"frames": ["side"], "fps": 10, "loop": True,
                       "bob": [0, -1, 0, 1], "lean": 1},
            "idle_front": {"frames": ["front"], "fps": 1, "loop": True},
            "idle_back":  {"frames": ["back"], "fps": 1, "loop": True}
        },
        "placeholder": True,
        "note": "Derived from the turnaround reference; no true walk frames exist yet. "
                "The 'bob' and 'lean' fields let the renderer fake motion until real "
                "frames land. Replace this file and scientist.png together."
    }, open(os.path.join(d, "scientist.json"), "w"), indent=2)
    print(f"  sprites/scientist/scientist.png  {atlas.width}x{atlas.height}  "
          f"({', '.join(rects)})")

    d2 = ensure("portraits", "scientist")
    for name, box in PORTRAITS.items():
        img = trim(cut_bg(sheet.crop(box)))
        img = crisp(fit(img, h=PORTRAIT_H), colors=32)
        img.save(os.path.join(d2, f"{name}.png"))
    print(f"  portraits/scientist/  {len(PORTRAITS)} expressions at {PORTRAIT_H}px")


# -------------------------------------------------------------------- props

CAR_VIEWS = {
    "side":     ((745, 164, 1809, 516), 212),
    "front":    ((108, 164, 620, 516), 132),
    "rear":     ((104, 584, 626, 1034), 132),
    "top":      ((750, 584, 1782, 1034), 264),
    "front_3q": ((77, 1062, 911, 1410), 216),
    "rear_3q":  ((1054, 1062, 1838, 1410), 216),
}


def build_car():
    sheet = ref("car_veridian_2400.png")
    d = ensure("props", "car_veridian")
    for name, (box, width) in CAR_VIEWS.items():
        img = trim(cut_bg(sheet.crop(box)))
        img = crisp(fit(img, w=width), colors=40)
        img.save(os.path.join(d, f"{name}.png"))
    print(f"  props/car_veridian/  {len(CAR_VIEWS)} views")


# ------------------------------------------------------------------ palette

def build_palette():
    """Pull the dominant colours of each reference so new art can be kept in
    family. Written for humans to read, not consumed by the engine."""
    out = {"_note": "Dominant colours per reference, for keeping new art in family.",
           "screen": {"w": SCREEN_W, "h": SCREEN_H}}
    for f in sorted(os.listdir(REFS)):
        if not f.endswith(".png"):
            continue
        im = Image.open(os.path.join(REFS, f)).convert("RGB")
        im.thumbnail((256, 256))
        q = im.quantize(colors=12, method=Image.MEDIANCUT)
        pal = q.getpalette()[: 12 * 3]
        counts = sorted(q.getcolors(), reverse=True)
        out[f[:-4]] = ["#%02x%02x%02x" % tuple(pal[i * 3:i * 3 + 3]) for _, i in counts]
    json.dump(out, open(os.path.join(OUT, "palette.json"), "w"), indent=2)
    print("  palette.json")


def main():
    print("Deriving assets from art/refs/ ...")
    build_backdrops()
    build_stills()
    build_scientist()
    build_car()
    build_palette()
    print("Done.")


if __name__ == "__main__":
    main()
