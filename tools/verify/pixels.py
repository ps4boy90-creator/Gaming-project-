#!/usr/bin/env python3
"""Pixel-level checks that are easier to state in numpy than in a browser.

Two jobs, both called by tools/verify/cutscenes.cjs:

    compare BASELINE_DIR CANDIDATE_DIR   gameplay frames must be identical
    stills  DIR                          every cutscene still is grey and legible

`compare` is the one that matters. The claim being defended is that raising
the cutscenes changed nothing about how gameplay looks, and the only honest
way to say that is pixel-for-pixel against frames captured before the work
began. Both sides are captured with grain and the broadcast effects off and
the lighting clock frozen -- otherwise every frame differs from every other
frame and the comparison proves nothing.

Output is one `PASS`/`FAIL` line per check so the node harness can just relay
it, and the exit code is the number of failures.
"""
import sys
import pathlib
import numpy as np
from PIL import Image

fails = []


def check(name, ok, extra=''):
    print(f"{'PASS' if ok else 'FAIL'}  {name}{'  ' + extra if extra else ''}")
    if not ok:
        fails.append(name)


def load(p):
    return np.asarray(Image.open(p).convert('RGB'), dtype=np.int16)


def compare(base_dir, cand_dir):
    base = sorted(pathlib.Path(base_dir).glob('*.png'))
    check('baseline exists', len(base) > 0, f'{len(base)} frames')
    for b in base:
        c = pathlib.Path(cand_dir) / b.name
        if not c.exists():
            check(f'{b.stem}: captured', False, 'no candidate frame')
            continue
        a, d = load(b), load(c)
        if a.shape != d.shape:
            check(f'{b.stem}: identical to baseline', False, f'{a.shape} vs {d.shape}')
            continue
        diff = np.abs(a - d)
        n = int((diff.max(axis=2) > 0).sum())
        worst = int(diff.max())
        check(f'{b.stem}: identical to baseline', n == 0,
              'exact' if n == 0 else f'{n} px differ, worst channel delta {worst}')


def stills(d):
    for p in sorted(pathlib.Path(d).glob('*.png')):
        rgb = load(p)
        img = Image.open(p)
        w, h = img.size
        check(f'{p.stem}: cutscene resolution', (w, h) == (768, 432), f'{w}x{h}')

        spread = int(np.abs(rgb.max(axis=2) - rgb.min(axis=2)).max())
        check(f'{p.stem}: monochrome', spread == 0, f'max channel spread {spread}')

        g = rgb[:, :, 0].astype(np.float64)
        mean, std = g.mean(), g.std()
        # The same bounds the scene art is held to: dark enough to be night,
        # far enough from the floor that the picture is not a black rectangle.
        check(f'{p.stem}: exposure', 14 <= mean <= 120, f'mean {mean:.1f}')
        check(f'{p.stem}: contrast', std >= 18, f'std {std:.1f}')

        levels = len(np.unique(g.astype(np.uint8)))
        # The point of the higher-resolution surface is tonal detail; a still
        # that resolves to a handful of greys has none, whatever its size.
        check(f'{p.stem}: tonal range', levels >= 24, f'{levels} greys')

        # The two rails are not the same failure and do not deserve the same
        # bound. Night sky sitting at true black is the picture working; blown
        # highlights are the tone curve having thrown detail away, which is
        # exactly what a monochrome conversion does when it goes wrong.
        black = float((g <= 1).mean())
        white = float((g >= 254).mean())
        check(f'{p.stem}: shadows hold', black < 0.30, f'{black * 100:.1f}% at black')
        check(f'{p.stem}: highlights hold', white < 0.02, f'{white * 100:.2f}% at white')


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'compare':
        compare(sys.argv[2], sys.argv[3])
    elif mode == 'stills':
        stills(sys.argv[2])
    else:
        raise SystemExit(f'unknown mode {mode}')
    print(f'\n{len(fails)} failed' if fails else '\nall passed')
    sys.exit(len(fails))
