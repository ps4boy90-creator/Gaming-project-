#!/usr/bin/env python3
"""
Take a reference video apart into things that can actually be studied.

There is no way to watch a video here, so studying one means decomposing it:
frames become images that can be looked at, and everything else becomes numbers.
The output is deliberately opinionated toward the questions that matter when
matching another game's look -- how dark is it really, what is its palette, how
long are its shots, does the camera hold or move, and is it drawn on a pixel
grid -- rather than a generic dump of metadata.

    python3 tools/study_video.py <video> [--out study/<name>] [--fps 5]

Writes into study/<name>/:
    probe.json      what the file is
    summary.json    every measurement, machine-readable
    REPORT-DATA.md  the same, readable
    sheets/         contact sheets -- the main thing to look at
    frames/         full-resolution frames at each cut, and evenly sampled
    palette.png     the clip's colours, and each shot's
    luminance.png   brightness and motion over time

Needs a full ffmpeg. The one bundled with Playwright in this environment
decodes VP8 and MJPEG only, so `pip install imageio-ffmpeg` supplies one that
handles H.264 and everything else.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

try:
    import numpy as np
except ImportError:
    sys.exit("numpy is required:  pip install numpy")
try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required:  pip install pillow")


def find_ffmpeg():
    """Prefer a full build; the Playwright one cannot decode H.264."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    found = shutil.which('ffmpeg')
    if found:
        return found
    sys.exit("No ffmpeg found. Run:  pip install imageio-ffmpeg")


FFMPEG = find_ffmpeg()
ANALYSIS_WIDTH = 320


def run(args):
    return subprocess.run(args, capture_output=True, text=True)


def probe(path):
    """Read the stream header. ffmpeg prints it to stderr and exits non-zero
    with no output file, which is expected rather than a failure."""
    out = run([FFMPEG, '-hide_banner', '-i', path]).stderr
    info = {'path': path, 'bytes': os.path.getsize(path)}

    m = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.?\d*)', out)
    if m:
        h, mi, s = m.groups()
        info['duration_s'] = round(int(h) * 3600 + int(mi) * 60 + float(s), 3)

    m = re.search(r'Video:\s*([\w0-9]+)[^,]*,\s*([\w()]+)[^,]*,\s*(\d+)x(\d+)', out)
    if m:
        info['codec'] = m.group(1)
        info['pixel_format'] = m.group(2)
        info['width'] = int(m.group(3))
        info['height'] = int(m.group(4))
    m = re.search(r'(\d+\.?\d*)\s*fps', out)
    if m:
        info['fps'] = float(m.group(1))
    m = re.search(r'Audio:\s*([\w0-9]+)', out)
    info['audio'] = m.group(1) if m else None
    m = re.search(r'bitrate:\s*(\d+)\s*kb/s', out)
    if m:
        info['bitrate_kbps'] = int(m.group(1))

    if 'width' not in info:
        sys.exit(f"Could not read a video stream from {path}.\n\n{out[-1500:]}")
    return info


def extract(path, out_dir, fps=None, width=None, timestamps=None, quality_full=False):
    """Pull frames either at a rate or at a list of timestamps."""
    os.makedirs(out_dir, exist_ok=True)
    if timestamps is not None:
        files = []
        for i, t in enumerate(timestamps):
            dst = os.path.join(out_dir, f'{i:04d}_t{t:07.2f}.png')
            args = [FFMPEG, '-y', '-hide_banner', '-loglevel', 'error',
                    '-ss', f'{t:.3f}', '-i', path, '-frames:v', '1']
            if width and not quality_full:
                args += ['-vf', f'scale={width}:-1']
            args += [dst]
            run(args)
            if os.path.exists(dst):
                files.append(dst)
        return files

    args = [FFMPEG, '-y', '-hide_banner', '-loglevel', 'error', '-i', path,
            '-vf', f'fps={fps}' + (f',scale={width}:-1' if width else ''),
            os.path.join(out_dir, '%05d.png')]
    run(args)
    return sorted(os.path.join(out_dir, f) for f in os.listdir(out_dir) if f.endswith('.png'))


def load_gray_and_hist(files):
    """Per-frame luminance, colour histogram and downscaled pixels."""
    lum, hists, smalls = [], [], []
    for f in files:
        im = Image.open(f).convert('RGB')
        a = np.asarray(im, dtype=np.float32)
        g = a[:, :, 0] * 0.299 + a[:, :, 1] * 0.587 + a[:, :, 2] * 0.114
        lum.append(g.mean() / 255.0)
        q = (a // 32).astype(np.int32)             # 8 levels per channel
        idx = q[:, :, 0] * 64 + q[:, :, 1] * 8 + q[:, :, 2]
        h = np.bincount(idx.ravel(), minlength=512).astype(np.float32)
        hists.append(h / max(1.0, h.sum()))
        smalls.append(np.asarray(im.resize((64, 36)), dtype=np.float32))
    return np.array(lum), np.array(hists), np.array(smalls)


def detect_cuts(hists, smalls, sensitivity=1.0):
    """
    Cuts by histogram distance, with an adaptive threshold.

    A fixed threshold either misses cuts in a dark, low-contrast clip or invents
    them in a busy one. Keying off the distribution of the differences means the
    same setting works on a moody walking-sim and on a fast trailer.
    """
    if len(hists) < 3:
        return [], np.zeros(max(0, len(hists) - 1))
    hist_d = np.abs(np.diff(hists, axis=0)).sum(axis=1) / 2.0
    pix_d = np.abs(np.diff(smalls, axis=0)).mean(axis=(1, 2, 3)) / 255.0

    med = float(np.median(hist_d))
    mad = float(np.median(np.abs(hist_d - med))) or 1e-6
    threshold = max(0.22, med + 6.0 * mad / sensitivity)

    cuts = []
    for i, d in enumerate(hist_d):
        # A cut is a big histogram jump *and* a big pixel jump; requiring both
        # rejects lighting changes and fades, which move one but not the other.
        if d > threshold and pix_d[i] > 0.06:
            if not cuts or i - cuts[-1] > 2:
                cuts.append(i)
    return cuts, pix_d


def contact_sheet(files, cols, cell_w, path, labels=None):
    if not files:
        return None
    ims = [Image.open(f).convert('RGB') for f in files]
    cell_h = round(cell_w * ims[0].height / ims[0].width)
    rows = (len(ims) + cols - 1) // cols
    pad = 3
    sheet = Image.new('RGB', (cols * (cell_w + pad) + pad, rows * (cell_h + pad) + pad), (18, 19, 24))
    for i, im in enumerate(ims):
        x = pad + (i % cols) * (cell_w + pad)
        y = pad + (i // cols) * (cell_h + pad)
        sheet.paste(im.resize((cell_w, cell_h), Image.LANCZOS), (x, y))
    sheet.save(path)
    return path


def palette_of(images, colors=16):
    """Adaptive palette over a montage of sampled frames."""
    if not len(images):
        return []
    n = min(len(images), 40)
    picks = images[np.linspace(0, len(images) - 1, n).astype(int)]
    h, w = picks.shape[1], picks.shape[2]
    strip = Image.new('RGB', (w * n, h))
    for i, arr in enumerate(picks):
        strip.paste(Image.fromarray(arr.astype(np.uint8)), (i * w, 0))
    q = strip.quantize(colors=colors, method=Image.MEDIANCUT)
    pal = q.getpalette()[: colors * 3]
    counts = sorted(q.getcolors(), reverse=True)
    return ['#%02x%02x%02x' % tuple(pal[i * 3:i * 3 + 3]) for _, i in counts]


def swatches(colors, path, cell=44):
    if not colors:
        return None
    img = Image.new('RGB', (cell * len(colors), cell), (18, 19, 24))
    for i, hexc in enumerate(colors):
        rgb = tuple(int(hexc[j:j + 2], 16) for j in (1, 3, 5))
        Image.new('RGB', (cell - 2, cell - 2), rgb)
        img.paste(Image.new('RGB', (cell - 2, cell - 2), rgb), (i * cell + 1, 1))
    img.save(path)
    return path


def timeline(lum, motion, path, w=900, h=200):
    """Brightness and motion over the clip, drawn to a fixed, honest scale."""
    img = Image.new('RGB', (w, h), (14, 15, 20))
    px = img.load()
    n = len(lum)
    if n < 2:
        return None
    for gy in range(0, 5):
        y = int(20 + gy * (h - 40) / 4)
        for x in range(0, w):
            px[x, y] = (34, 36, 44)
    for i in range(n - 1):
        x0 = int(i * (w - 1) / (n - 1))
        x1 = int((i + 1) * (w - 1) / (n - 1))
        for x in range(x0, max(x0 + 1, x1)):
            # luminance 0..1 over the full height
            y = int(h - 20 - lum[i] * (h - 40))
            for dy in (-1, 0, 1):
                if 0 <= y + dy < h:
                    px[x, y + dy] = (230, 200, 110)
            if i < len(motion):
                # motion, normalised to its own maximum so shape is readable
                mv = motion[i] / max(1e-6, motion.max())
                ym = int(h - 20 - mv * (h - 40))
                if 0 <= ym < h:
                    px[x, ym] = (110, 170, 230)
    img.save(path)
    return path


def pixel_grid(files):
    """
    Estimate a pixel-art grid, and be honest about how sure it is.

    Two independent measures, because they fail in opposite directions:

    *Alignment* -- edge energy on columns that are multiples of b, against
    everywhere else. Decisive on a clean nearest-neighbour upscale, which is
    what a capture of a pixel-art game looks like. Note the true grid is the
    **coarsest** b that explains the edges, not the best-scoring one: if the
    grid is 4 then every boundary is also a 2-boundary, so 2 always wins on
    score and always would, which makes the maximum useless.

    *Harmonic run-length* -- the distance between colour changes, requiring the
    candidate and its double to both be peaks. This survives soft or
    resampled art where alignment goes flat; it is what recovers 7 from the
    project's own AI-upscaled references, which alignment cannot see at all.

    Both will happily report *content* periodicity -- brick courses, floor tiles
    -- on art that is already at native resolution and has no grid. So this
    returns its method and score, and study_video also writes a 1:1 zoom crop:
    the only reliable check is looking at one.
    """
    if not files:
        return None

    align = {}
    hist_total = np.zeros(41)
    for f in files[:6]:
        a = np.asarray(Image.open(f).convert('RGB'), dtype=np.float32)
        h, w, _ = a.shape
        rows = a[::max(1, h // 120)]
        d = np.abs(np.diff(rows, axis=1)).sum(axis=2).mean(axis=0)
        if d.size >= 60 and d.mean() > 0:
            xs = np.arange(1, d.size + 1)
            for b in range(2, 25):
                on, off = d[(xs % b) == 0], d[(xs % b) != 0]
                if on.size >= 4 and off.size >= 4:
                    align.setdefault(b, []).append(float(on.mean()) / max(1e-6, float(off.mean())))
        runs = []
        for y in range(0, h, max(1, h // 160)):
            dd = np.abs(np.diff(a[y], axis=0)).sum(axis=1)
            idx = np.flatnonzero(dd > 12)
            if len(idx) > 1:
                runs.extend(np.diff(idx).tolist())
        runs = [r for r in runs if 1 <= r <= 40]
        if runs:
            hist_total += np.bincount(runs, minlength=41).astype(float)

    if align:
        med = {b: float(np.median(v)) for b, v in align.items()}
        peak = max(med.values())
        if peak >= 2.5:
            keep = [b for b, r in med.items() if r >= peak * 0.45]
            block = max(keep) if keep else max(med, key=med.get)
            return {'block': block, 'method': 'alignment',
                    'score': round(med[block], 2),
                    'confidence': round(min(1.0, med[block] / 20.0), 3)}

    total = hist_total.sum()
    if total > 0:
        peaks = [b for b in range(3, 21)
                 if hist_total[b] > hist_total[b - 1] and hist_total[b] > hist_total[b + 1]]
        # The double must be a peak too: a real grid echoes at 2b, content
        # periodicity usually does not.
        confirmed = [b for b in peaks if 2 * b <= 20 and 2 * b in peaks]
        if confirmed:
            block = max(confirmed, key=lambda b: hist_total[b])
            share = hist_total[block] / total
            if share >= 0.08:
                return {'block': block, 'method': 'run-length',
                        'score': round(float(share), 3),
                        'confidence': round(min(1.0, float(share) * 3), 3)}
    return None


def zoom_crop(frame_path, out_path, size=96, scale=6):
    """A 1:1 magnified crop. Whether something is pixel art is a question best
    settled by looking at it, not by a heuristic."""
    try:
        im = Image.open(frame_path).convert('RGB')
    except Exception:
        return None
    x = max(0, im.width // 2 - size // 2)
    y = max(0, im.height // 2 - size // 2)
    crop = im.crop((x, y, min(im.width, x + size), min(im.height, y + size)))
    crop.resize((crop.width * scale, crop.height * scale), Image.NEAREST).save(out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('--out', default=None)
    ap.add_argument('--fps', type=float, default=5.0,
                    help='analysis sampling rate (default 5)')
    ap.add_argument('--sensitivity', type=float, default=1.0)
    args = ap.parse_args()

    if not os.path.exists(args.video):
        sys.exit(f'No such file: {args.video}')

    name = os.path.splitext(os.path.basename(args.video))[0]
    out = args.out or os.path.join('study', re.sub(r'[^\w.-]', '_', name))
    os.makedirs(out, exist_ok=True)
    for sub in ('frames', 'sheets'):
        os.makedirs(os.path.join(out, sub), exist_ok=True)

    info = probe(args.video)
    json.dump(info, open(os.path.join(out, 'probe.json'), 'w'), indent=2)
    print(f"{info.get('width')}x{info.get('height')}  {info.get('codec')}  "
          f"{info.get('fps')} fps  {info.get('duration_s')}s  "
          f"audio={info.get('audio')}  {info['bytes'] // 1024}KB")

    tmp = tempfile.mkdtemp(prefix='study_')
    try:
        analysis = extract(args.video, tmp, fps=args.fps, width=ANALYSIS_WIDTH)
        if not analysis:
            sys.exit('ffmpeg produced no frames -- the file may be truncated or unsupported.')
        print(f'  {len(analysis)} analysis frames at {args.fps} fps')

        lum, hists, smalls = load_gray_and_hist(analysis)
        cuts, motion = detect_cuts(hists, smalls, args.sensitivity)
        cut_times = [round((i + 1) / args.fps, 2) for i in cuts]

        shots = []
        marks = [0.0] + cut_times + [info.get('duration_s', len(analysis) / args.fps)]
        for i in range(len(marks) - 1):
            if marks[i + 1] - marks[i] > 0.15:
                shots.append({'start': marks[i], 'end': marks[i + 1],
                              'length': round(marks[i + 1] - marks[i], 2)})

        # Full-resolution frames: one just inside each shot, plus even samples.
        shot_mids = [round(s['start'] + min(0.4, s['length'] / 3), 2) for s in shots]
        extract(args.video, os.path.join(out, 'frames'), timestamps=shot_mids, quality_full=True)
        even = list(np.linspace(0, max(0.0, info.get('duration_s', 1) - 0.1), 12))
        extract(args.video, os.path.join(out, 'frames'), timestamps=[round(t, 2) for t in even],
                quality_full=True)

        # Contact sheets, the thing actually looked at.
        contact_sheet(analysis[::max(1, len(analysis) // 48)], 8, 200,
                      os.path.join(out, 'sheets', 'overview.png'))
        shot_frames = sorted(os.path.join(out, 'frames', f)
                             for f in os.listdir(os.path.join(out, 'frames')))
        contact_sheet(shot_frames[:40], 5, 260, os.path.join(out, 'sheets', 'shots.png'))

        whole = palette_of(smalls, 16)
        swatches(whole, os.path.join(out, 'palette.png'))
        timeline(lum, motion, os.path.join(out, 'luminance.png'))
        grid = pixel_grid(shot_frames)
        if shot_frames:
            zoom_crop(shot_frames[len(shot_frames) // 2], os.path.join(out, 'zoom.png'))

        dark = float((lum < 0.15).mean())
        summary = {
            'probe': info,
            'analysis_fps': args.fps,
            'frames_analysed': len(analysis),
            'cuts': len(cut_times),
            'cut_times': cut_times[:200],
            'shots': len(shots),
            'shot_length_s': {
                'mean': round(float(np.mean([s['length'] for s in shots])), 2) if shots else None,
                'median': round(float(np.median([s['length'] for s in shots])), 2) if shots else None,
                'min': round(min([s['length'] for s in shots]), 2) if shots else None,
                'max': round(max([s['length'] for s in shots]), 2) if shots else None,
            },
            'luminance': {
                'mean': round(float(lum.mean()), 4),
                'median': round(float(np.median(lum)), 4),
                'p05': round(float(np.percentile(lum, 5)), 4),
                'p95': round(float(np.percentile(lum, 95)), 4),
                'fraction_very_dark': round(dark, 3),
            },
            'motion': {
                'mean': round(float(motion.mean()), 4) if len(motion) else None,
                'p95': round(float(np.percentile(motion, 95)), 4) if len(motion) else None,
                'still_fraction': round(float((motion < 0.01).mean()), 3) if len(motion) else None,
            },
            'palette': whole,
            'pixel_grid': grid,
        }
        json.dump(summary, open(os.path.join(out, 'summary.json'), 'w'), indent=2)

        with open(os.path.join(out, 'REPORT-DATA.md'), 'w') as f:
            f.write(f'# Measurements: {name}\n\n')
            f.write(f"**{info.get('width')}x{info.get('height')}** · {info.get('codec')} · "
                    f"{info.get('fps')} fps · {info.get('duration_s')}s\n\n")
            f.write(f"- **{len(shots)} shots**, median {summary['shot_length_s']['median']}s "
                    f"(min {summary['shot_length_s']['min']}, max {summary['shot_length_s']['max']})\n")
            f.write(f"- **Luminance** mean {summary['luminance']['mean']:.3f}, "
                    f"5th pct {summary['luminance']['p05']:.3f}, 95th {summary['luminance']['p95']:.3f}; "
                    f"{dark*100:.0f}% of frames very dark\n")
            if summary['motion']['mean'] is not None:
                f.write(f"- **Motion** mean {summary['motion']['mean']:.4f}, "
                        f"{summary['motion']['still_fraction']*100:.0f}% near-still\n")
            if grid:
                nat = round(info['width'] / grid['block'])
                f.write(f"- **Pixel grid** {grid['block']}px blocks via {grid['method']} "
                        f"(score {grid['score']}, confidence {grid['confidence']:.2f}) "
                        f"-> native ~{nat}x{round(info['height']/grid['block'])}\n")
                f.write('  Check `zoom.png` before trusting this; both measures can report '
                        'content periodicity on art that has no grid.\n')
            else:
                f.write('- **Pixel grid** none detected (not pixel art, or resampled)\n')
            f.write(f"- **Palette** {' '.join(whole[:10])}\n")

        print(f"  {len(shots)} shots · lum {summary['luminance']['mean']:.3f} · "
              f"grid {grid['block'] if grid else 'none'}")
        print(f'  -> {out}/')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
