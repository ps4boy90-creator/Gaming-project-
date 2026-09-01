#!/usr/bin/env python3
"""
Convert the game's art to monochrome without flattening it.

The reference for this project is Midnight Scenes, whose early episodes are
black and white. The naive way to get there -- desaturating -- is exactly wrong
for these scenes: it maps hue to nothing, so two colours that differ in hue but
match in luminance become the same grey. The bedroom's warm lamp and its cold
moonlight sit at almost the same luminance, and a straight desaturation turns
the room from two light sources into one flat wash.

So three deliberate steps:

1. **Weighted mix, not luma.** Blue is weighted well below the standard 0.114
   and red slightly above 0.299. Cold light therefore darkens and warm light
   holds, which widens the gap between the two rather than closing it. On the
   bedroom's two key colours this roughly doubles the separation a straight
   luma conversion leaves.

2. **A tone curve.** Weighting down the blue costs overall brightness in scenes
   that are mostly blue -- which is all of them, at night -- so a lift plus an
   S-curve puts the midtones and the contrast back.

3. **A quantised ramp with an ordered dither.** Continuous greys band visibly
   across the painted falloff in these rooms. Snapping to a ~20 step ramp with
   a 4x4 Bayer dither keeps the gradients smooth, and dithered grey is the
   period texture we want anyway.

Used by slice_refs.py, make_facility.py and make_corridor.py so the three
generators cannot drift apart.
"""

import numpy as np
from PIL import Image

# Deliberately not the luma coefficients. Blue is pushed down and red up so
# that warm and cold light separate by brightness once hue is gone.
WEIGHTS = (0.34, 0.60, 0.06)

# 4x4 ordered dither. The same matrix the very first plan for this project
# proposed for its 1-bit renderer, put to its proper use here.
BAYER4 = np.array([
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
], dtype=np.float32) / 16.0


def mix(rgb, weights=WEIGHTS):
    """Weighted channel mix to a single float plane, 0..255."""
    w = np.asarray(weights, dtype=np.float32)
    w = w / w.sum()
    return (rgb[:, :, 0] * w[0] + rgb[:, :, 1] * w[1] + rgb[:, :, 2] * w[2])


GAMMA = 2.2


def tone(grey, lift=0.92, contrast=1.15, pivot=None):
    """
    Restore what the weighting cost, without crushing the picture.

    The contrast curve pivots on the image's own median, not on mid-grey. These
    are night scenes: their content sits in the bottom tenth of the range, and
    an S-curve about 0.5 pushes almost every pixel toward black -- measured, it
    took the bedroom from a mean of 18/255 to 8/255 and destroyed it. Pivoting
    on the median adds local contrast while leaving the overall level alone.
    """
    x = np.clip(grey / 255.0, 0.0, 1.0)
    x = np.power(x, lift)
    p = float(np.median(x)) if pivot is None else pivot
    x = np.clip((x - p) * contrast + p, 0.0, 1.0)
    return x * 255.0


def quantise(grey, levels=24, dither=1.0):
    """
    Snap to a grey ramp, spreading the error with an ordered dither.

    Quantising in perceptual space rather than linearly, because a linear ramp
    spends most of its steps on highlights these scenes never reach -- on the
    bedroom a 20 step linear ramp resolved to eight actual greys. Encoding to
    roughly gamma 2.2 first puts the steps where the picture is.
    """
    if levels <= 1:
        return grey
    h, w = grey.shape
    enc = np.power(np.clip(grey, 0, 255) / 255.0, 1.0 / GAMMA)
    step = 1.0 / (levels - 1)
    if dither > 0:
        tile = np.tile(BAYER4, (h // 4 + 1, w // 4 + 1))[:h, :w]
        enc = enc + (tile - 0.5) * step * dither
    enc = np.round(np.clip(enc, 0, 1) / step) * step
    return np.power(np.clip(enc, 0, 1), GAMMA) * 255.0


def to_mono(img, weights=WEIGHTS, lift=0.92, contrast=1.15,
            levels=24, dither=1.0):
    """
    Convert a PIL image to monochrome, preserving alpha.

    Returns a new RGBA image whose three colour channels are equal.
    """
    rgba = img.convert('RGBA')
    a = np.asarray(rgba, dtype=np.float32)
    grey = mix(a[:, :, :3], weights)
    grey = tone(grey, lift=lift, contrast=contrast)
    grey = quantise(grey, levels=levels, dither=dither)
    g = grey.astype(np.uint8)
    out = np.dstack([g, g, g, a[:, :, 3].astype(np.uint8)])
    return Image.fromarray(out, 'RGBA')


def grey_of(hex_colour, weights=WEIGHTS):
    """Where a single colour lands on the ramp, 0..255, before any tone curve.

    The tone curve pivots on an image's median and so is meaningless for one
    swatch; this is the raw mix, which is what matters for comparing two lights
    against each other."""
    h = hex_colour.lstrip('#')
    rgb = np.array([[[int(h[i:i + 2], 16) for i in (0, 2, 4)]]], dtype=np.float32)
    return float(mix(rgb, weights)[0, 0])


def separation(hex_a, hex_b, weights=WEIGHTS):
    """
    How far apart two colours land on the grey ramp, 0..255.

    Used by the tests to prove the warm and cold lights in a scene do not
    collapse into the same grey -- the specific failure this module exists to
    avoid, and one an average-contrast measurement would never catch.
    """
    return abs(grey_of(hex_a, weights) - grey_of(hex_b, weights))


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        sys.exit('usage: monochrome.py <in.png> <out.png>')
    to_mono(Image.open(sys.argv[1])).save(sys.argv[2])
    print(f'{sys.argv[1]} -> {sys.argv[2]}')
