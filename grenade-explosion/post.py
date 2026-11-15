"""Finishing: upscale to 1080p, title card, HUD overlays, grade, synthesized sound design, encode.

  python3 post.py <frames_root> <out.mp4> [--draft]

<frames_root>/<shot>/f####.png + meta.json come from shots.py. Sound is generated here with numpy
(no samples, no external services), so the whole video is reproducible from this folder.
"""
import os, sys, json, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1920, 1080, 24
SR = 48000
ORDER = ["card", "throw", "follow", "macro", "flash", "blast", "top"]
TRIM_HEAD = {"macro": 8}          # frames dropped from the start of a shot in the edit
FLASH = [(255, 252, 244), (255, 246, 226), (255, 232, 196)]
AMBER = (255, 176, 46); RED = (255, 58, 40); INK = (240, 238, 232); DIM = (168, 170, 172); PANEL = (17, 19, 22)

def font(name, size):
    return ImageFont.truetype(os.path.join(HERE, "assets", name), size)
F_TITLE = lambda s: font("Anton-Regular.ttf", s)
F_SEMI = lambda s: font("BarlowCondensed-SemiBold.ttf", s)
F_MED = lambda s: font("BarlowCondensed-Medium.ttf", s)

def ease(x):
    x = min(1.0, max(0.0, x)); return 1 - (1 - x) ** 3

def text(d, xy, s, f, fill, alpha=1.0, anchor="la", tracking=0):
    col = (*fill[:3], int(255 * alpha))
    if tracking:
        x, y = xy
        if anchor[0] == "r":
            x -= sum(d.textlength(ch, font=f) + tracking for ch in s) - tracking
        elif anchor[0] == "m":
            x -= (sum(d.textlength(ch, font=f) + tracking for ch in s) - tracking) / 2
        for ch in s:
            d.text((x, y), ch, font=f, fill=col, anchor="l" + anchor[1]); x += d.textlength(ch, font=f) + tracking
    else:
        d.text(xy, s, font=f, fill=col, anchor=anchor)

def shadowed(base, overlay, blur=6, strength=0.55):
    """Composite overlay with a soft dark halo so text stays legible over bright footage."""
    a = overlay.split()[3]
    sh = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    sh.putalpha(a.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(min(255, v * 1.6) * strength)))
    base.alpha_composite(sh); base.alpha_composite(overlay)

def tag(d, a=1.0):
    text(d, (64, 54), "EXPLOSION COMPARISON", F_SEMI(30), INK, a, tracking=4)
    d.rectangle([64, 96, 64 + 54, 100], fill=(*AMBER, int(255 * a)))
    text(d, (130, 84), "01  ·  M67 FRAGMENTATION GRENADE", F_MED(26), DIM, a, tracking=2)

# ------------------------------------------------------------------ per-shot overlays
SPECS = [("TYPE", "Fragmentation, time-delay fuze"), ("BODY", "63.5 mm steel sphere  ·  400 g"), ("FILLER", "180 g Composition B"),
         ("FUZE", "M213  ·  4 – 5.5 s delay"), ("KILL RADIUS", "5 m"), ("CASUALTY RADIUS", "15 m"), ("IN SERVICE", "1968 – present")]

def card_frame(img, i, n):
    """img: the turntable render (left half). Returns the composed 1080p card."""
    base = Image.new("RGBA", (W, H), (*PANEL, 255))
    left = img.convert("RGB").resize((W // 2, H), Image.LANCZOS)
    base.paste(left, (0, 0))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    # soft seam between render and panel
    grad = Image.linear_gradient("L").rotate(90, expand=True).resize((90, H))
    seam = Image.new("RGBA", (90, H), (*PANEL, 255)); seam.putalpha(grad.point(lambda v: 255 - v))
    base.alpha_composite(seam.transpose(Image.FLIP_LEFT_RIGHT), (W // 2 - 90, 0))
    t = i / FPS
    x0 = W // 2 + 96
    a = ease((t - 0.10) / 0.5)
    text(d, (x0, 150), "EXPLOSION COMPARISON  ·  01", F_SEMI(30), DIM, a, tracking=5)
    a = ease((t - 0.20) / 0.5); dx = int((1 - a) * 40)
    text(d, (x0 + dx, 196), "M67", F_TITLE(210), INK, a)
    a = ease((t - 0.35) / 0.5); dx = int((1 - a) * 40)
    text(d, (x0 + dx, 446), "FRAGMENTATION HAND GRENADE", F_TITLE(54), AMBER, a, tracking=2)
    a = ease((t - 0.45) / 0.5)
    d.rectangle([x0, 528, x0 + int(700 * a), 531], fill=(*AMBER, int(255 * a)))
    y = 562
    for k, (lab, val) in enumerate(SPECS):
        a = ease((t - 0.65 - 0.12 * k) / 0.45); dx = int((1 - a) * 28)
        hot = lab in ("KILL RADIUS", "CASUALTY RADIUS")
        text(d, (x0 + dx, y), lab, F_SEMI(31), RED if lab == "KILL RADIUS" else (AMBER if hot else DIM), a, tracking=3)
        text(d, (x0 + 300 + dx, y - 4), val, F_SEMI(40) if hot else F_MED(38), INK, a)
        y += 60
    a = ease((t - 1.9) / 0.6)
    text(d, (x0, 1000), "Standard US fragmentation grenade. Average throw: 30 – 35 m.", F_MED(28), DIM, a)
    base.alpha_composite(ov)
    return base.convert("RGB")

def fuze_hud(d, t, t_det, a=1.0):
    """Bottom-right fuze countdown, running from release to detonation."""
    rem = max(0.0, t_det - t)
    x, y = W - 64, H - 150
    text(d, (x, y), "FUZE", F_SEMI(30), DIM, a, anchor="ra", tracking=5)
    text(d, (x, y + 30), "%.2f s" % rem, F_TITLE(74), AMBER if rem > 0.6 else RED, a, anchor="ra")
    frac = 1.0 - rem / t_det
    d.rectangle([x - 300, y + 122, x, y + 126], fill=(255, 255, 255, int(70 * a)))
    d.rectangle([x - 300, y + 122, x - 300 + int(300 * frac), y + 126], fill=(*(AMBER if rem > 0.6 else RED), int(255 * a)))

def lower(d, title, sub, a=1.0, y=H - 150):
    d.rectangle([64, y + 8, 70, y + 96], fill=(*AMBER, int(255 * a)))
    text(d, (88, y), title, F_TITLE(54), INK, a)
    text(d, (88, y + 66), sub, F_MED(32), DIM, a, tracking=1)

def callout(d, px, py, big, small, color, a=1.0, dx=150, dy=-120):
    """Leader line from a tracked point to a label."""
    ex, ey = px + dx, py + dy
    d.line([(px, py), (ex, ey), (ex + 28, ey)], fill=(*color, int(255 * a)), width=3)
    d.ellipse([px - 7, py - 7, px + 7, py + 7], outline=(*color, int(255 * a)), width=3)
    text(d, (ex + 40, ey - 46), big, F_TITLE(64), color, a)
    text(d, (ex + 40, ey + 28), small, F_SEMI(32), INK, a, tracking=3)

def overlay_for(shot, i, n, m, t_det):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    t = m["t"]; td = m["td"]; u = i / max(1, n - 1)
    fin = ease(i / 8.0)
    tag(d, fin if shot == "throw" else 1.0)
    if shot == "throw":
        lower(d, "THE THROW", "Pin out, lever released  ·  about 30 m downrange", ease((i - 6) / 10.0) * (1 - ease((i - (n - 8)) / 8.0)))
        if t >= 0:
            fuze_hud(d, t, t_det, ease(t / 0.15))
    elif shot == "follow":
        fuze_hud(d, t, t_det)
        lower(d, "IN FLIGHT", "400 g  ·  lever gone, delay fuze burning", ease((i - 4) / 10.0) * (1 - ease((i - (n - 30)) / 10.0)))
    elif shot == "macro":
        fuze_hud(d, t, t_det)
    elif shot == "blast":
        a = ease((i - 8) / 8.0)
        text(d, (W - 64, H - 150), "SLOW MOTION", F_SEMI(30), DIM, a, anchor="ra", tracking=5)
        text(d, (W - 64, H - 120), "T + %03d ms" % max(0, round(td * 1000)), F_TITLE(74), INK, a, anchor="ra")
        lower(d, "DETONATION", "180 g Composition B  ·  steel body shatters into fragments", ease((i - 14) / 10.0) * (1 - ease((i - (n - 26)) / 10.0)))
    elif shot == "top":
        an = m["anchors"]
        text(d, (W - 64, 54), "TOP VIEW", F_SEMI(30), INK, 1.0, anchor="ra", tracking=5)
        a5 = ease((i - 16) / 8.0); a15 = ease((i - 62) / 8.0)
        if a5 > 0:
            callout(d, an["kill"][0] * W, an["kill"][1] * H, "5 m", "KILL RADIUS", RED, a5, dx=110, dy=120)
        if a15 > 0:
            callout(d, an["casualty"][0] * W, an["casualty"][1] * H, "15 m", "CASUALTY RADIUS", AMBER, a15, dx=90, dy=-110)
        if td >= 0:
            text(d, (W - 64, H - 120), "T + %03d ms" % round(td * 1000), F_TITLE(74), INK, 1.0, anchor="ra")
            text(d, (W - 64, H - 150), "2.5× SLOW MOTION", F_SEMI(30), DIM, 1.0, anchor="ra", tracking=5)
        else:
            fuze_hud(d, t, t_det)
        lower(d, "BLAST RADIUS", "Fragments can travel up to 230 m", ease((i - 80) / 12.0))
    return ov

# ------------------------------------------------------------------ sound design (all synthesized)
rng = np.random.default_rng(42)
def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))
def noise(n):
    return rng.standard_normal(n)
def onepole_lp(x, fc):
    a = math.exp(-2 * math.pi * fc / SR); y = np.empty_like(x); acc = 0.0
    # vectorised via lfilter-equivalent recursion in chunks (pure numpy cumulative trick is unstable; loop in C via np.frompyfunc is slow)
    from numpy.lib.stride_tricks import sliding_window_view  # noqa: F401
    try:
        from scipy.signal import lfilter
        return lfilter([1 - a], [1, -a], x)
    except Exception:
        for k in range(len(x)):
            acc = (1 - a) * x[k] + a * acc; y[k] = acc
        return y
def lp(x, fc, order=2):
    for _ in range(order):
        x = onepole_lp(x, fc)
    return x
def hp(x, fc, order=1):
    for _ in range(order):
        x = x - onepole_lp(x, fc)
    return x
def bp(x, lo, hi):
    return hp(lp(x, hi), lo)
def sweep(n, f0, f1):
    f = np.geomspace(f0, f1, n); return np.sin(2 * np.pi * np.cumsum(f) / SR)

class Mix:
    def __init__(self, dur):
        self.b = np.zeros((int(dur * SR) + SR, 2))
    def add(self, t, x, gain=1.0, pan=0.0):
        i = int(t * SR)
        if i < 0:
            x = x[-i:]; i = 0
        n = min(len(x), len(self.b) - i)
        if n <= 0:
            return
        l = math.cos((pan + 1) * math.pi / 4); r = math.sin((pan + 1) * math.pi / 4)
        self.b[i:i + n, 0] += x[:n] * gain * l * 1.414; self.b[i:i + n, 1] += x[:n] * gain * r * 1.414

def s_boom(scale=1.0, slow=1.0):
    """Explosion: crack + sub drop + rumble. slow>1 stretches and pitches it down for slow-motion replays."""
    n = int(SR * 3.6 * slow)
    crack = bp(noise(n), 300 / slow, 7000 / slow) * env_exp(n, 0.055 * slow)
    crack[: int(0.002 * SR)] *= np.linspace(0, 1, int(0.002 * SR))
    sub = sweep(n, 95 / slow, 26 / slow) * env_exp(n, 0.55 * slow)
    thump = sweep(n, 180 / slow, 45 / slow) * env_exp(n, 0.12 * slow)
    rumble = lp(noise(n), 140 / slow, 3) * env_exp(n, 0.9 * slow) * 5.0
    tail = bp(noise(n), 200 / slow, 1800 / slow) * env_exp(n, 0.5 * slow) * np.minimum(1, np.arange(n) / (0.05 * SR))
    x = 1.2 * crack + 1.6 * sub + 1.2 * thump + 0.9 * rumble + 0.35 * tail
    return np.tanh(x * 1.6 * scale)
def s_debris(dur, density=40, slow=1.0):
    n = int(dur * SR); x = np.zeros(n)
    for _ in range(int(density * dur)):
        t0 = rng.uniform(0.15, dur) ** 1.0; k = int(t0 * SR); m = int(rng.uniform(0.01, 0.05) * SR * slow)
        if k + m >= n:
            continue
        x[k:k + m] += bp(noise(m), 800 / slow, 6000 / slow) * env_exp(m, 0.008 * slow) * rng.uniform(0.1, 0.6) * math.exp(-t0 / (dur * 0.45))
    return x
def s_whoosh(dur, f0=300, f1=2400, peak=0.5):
    n = int(dur * SR); t = np.linspace(0, 1, n)
    envl = np.exp(-((t - peak) / 0.22) ** 2)
    x = noise(n); fc = np.geomspace(f0, f1, 8)
    out = np.zeros(n); seg = n // 8
    for k in range(8):
        w = np.exp(-((t - (k + 0.5) / 8) / 0.16) ** 2)
        out += bp(x, fc[k] * 0.6, fc[k] * 1.6) * w
    return out * envl
def s_thud(scale=1.0):
    n = int(0.5 * SR)
    return (sweep(n, 140, 48) * env_exp(n, 0.07) * 1.4 + bp(noise(n), 400, 3500) * env_exp(n, 0.02) * 0.8) * scale
def s_ping(f=4200, dur=0.5):
    n = int(dur * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.6 * np.sin(2 * np.pi * f * 1.51 * t) + 0.4 * np.sin(2 * np.pi * f * 2.27 * t)) * env_exp(n, 0.09) * 0.3
def s_tick():
    n = int(0.05 * SR); return bp(noise(n), 2500, 9000) * env_exp(n, 0.006) * 0.5
def s_wind(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    x = lp(noise(n), 420, 2) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t + 1.0) * np.sin(2 * np.pi * 0.047 * t)) * 6
    return x
def s_birds(dur):
    n = int(dur * SR); x = np.zeros(n)
    tt = 0.8
    while tt < dur - 1:
        f0 = rng.uniform(2600, 4200)
        for k in range(rng.integers(2, 5)):
            m = int(0.07 * SR); k0 = int((tt + k * 0.11) * SR)
            if k0 + m < n:
                x[k0:k0 + m] += sweep(m, f0, f0 * rng.uniform(1.15, 1.5)) * np.hanning(m) * 0.25
        tt += rng.uniform(1.6, 4.5)
    return x
def s_roll(dur):
    n = int(dur * SR); t = np.linspace(0, 1, n)
    x = bp(noise(n), 250, 2600) * (0.5 + 0.5 * np.sin(2 * np.pi * 17 * t * dur)) ** 2 * (1 - t) ** 1.5
    return x * 0.8
def s_drone(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * 55 * t) + 0.5 * np.sin(2 * np.pi * 82.5 * t + 0.4) + 0.3 * np.sin(2 * np.pi * 110.3 * t)) * 0.25
    x += lp(noise(n), 300, 2) * 0.6
    return x * np.minimum(1, t / 0.6) * np.minimum(1, (dur - t) / 0.5)
def s_ring(dur=3.5):
    n = int(dur * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 3150 * t) + 0.5 * np.sin(2 * np.pi * 4720 * t)) * np.minimum(1, t / 0.15) * env_exp(n, 1.1) * 0.05

def build_audio(path, starts, metas, t_det, total):
    mx = Mix(total)
    T = {k: v / FPS for k, v in starts.items()}
    def when(shot, pred):
        m = metas[shot]
        for i in sorted(int(k) for k in m):
            if pred(m[str(i)]):
                return T[shot] + i / FPS
        return None
    # ambience across the live shots
    amb_t0 = T["throw"]; amb = s_wind(total - amb_t0) * 0.045 + s_birds(total - amb_t0) * 0.05
    mx.add(amb_t0, amb, 1.0, -0.1)
    # card: drone + spec ticks + intro hit
    mx.add(0.0, s_drone(T["throw"] + 0.2), 0.5)
    mx.add(0.05, s_thud(1.2), 0.5)
    for k in range(len(SPECS)):
        mx.add(0.65 + 0.12 * k, s_tick(), 0.35, 0.3)
    mx.add(T["throw"] - 0.45, s_whoosh(0.6, 200, 1500, 0.8), 0.35)
    # throw: pin, effort whoosh, lever ping
    tp = when("throw", lambda m: m["t"] >= -1.30)
    if tp: mx.add(tp, s_ping(5200, 0.4), 0.5, 0.2)
    tr = when("throw", lambda m: m["t"] >= -0.12)
    if tr:
        mx.add(tr - 0.12, s_whoosh(0.55, 300, 2800, 0.45), 0.9, 0.1)
        mx.add(tr + 0.10, s_ping(3600, 0.6), 0.45, 0.4)
    # follow: air rush, then impacts
    n_follow = len(metas["follow"]) / FPS
    mx.add(T["follow"], s_whoosh(n_follow * 0.9, 250, 900, 0.55) * 0.9, 0.55)
    land = when("follow", lambda m: m["t"] >= metas["_events"][0])
    if land:
        mx.add(land, s_thud(1.0), 1.0); mx.add(land + 0.02, s_debris(0.6, 30), 0.5)
    b2 = when("follow", lambda m: m["t"] >= metas["_events"][1])
    if b2:
        mx.add(b2, s_thud(0.55), 0.8, 0.15); mx.add(b2 + 0.05, s_roll(0.9), 0.5, 0.2)
    # macro: roll in, settle, hiss, BOOM (real time)
    mx.add(T["macro"], s_roll(1.1), 0.55, -0.3)
    det_m = T["flash"]
    if det_m:
        hiss = hp(noise(int(1.0 * SR)), 5000) * np.linspace(0, 1, int(1.0 * SR)) ** 2 * 0.06
        mx.add(det_m - 1.0, hiss, 1.0)
        mx.add(det_m, s_boom(1.0, 1.0), 1.0)
    # blast: slow-motion replay -> stretched, pitched-down boom + debris + ringing
    det_b = when("blast", lambda m: m["td"] >= 0)
    if det_b:
        mx.add(det_b, s_boom(1.0, 2.2), 1.0)
        mx.add(det_b + 0.1, s_debris(3.6, 45, 2.0), 0.55, 0.2)
        mx.add(det_b + 0.05, s_ring(3.6), 1.0)
        mx.add(det_b + 0.02, s_whoosh(1.2, 150, 1200, 0.2), 0.6, -0.4); mx.add(det_b + 0.3, s_whoosh(1.4, 180, 900, 0.3), 0.4, 0.5)
    # top view: UI blips as the rings draw, then a third (distant, wide) boom
    for k, dt_ in enumerate((0.15, 0.55, 0.95)):
        mx.add(T["top"] + dt_, s_ping(1800 + 500 * k, 0.25), 0.25, 0.3)
    det_t = when("top", lambda m: m["td"] >= 0)
    if det_t:
        mx.add(det_t, s_boom(0.9, 1.5), 0.9)
        mx.add(det_t + 0.1, s_debris(3.0, 35, 1.5), 0.4, -0.2)
    x = mx.b[: int(total * SR)]
    x = np.tanh(x * 1.1)
    fo = int(0.6 * SR); x[-fo:] *= np.linspace(1, 0, fo)[:, None]
    x = x / (np.abs(x).max() + 1e-9) * 0.89
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())

# ------------------------------------------------------------------ assemble
def main():
    root = sys.argv[1]; out = sys.argv[2]; draft = "--draft" in sys.argv
    sys.path.insert(0, HERE)
    info = json.load(open(os.path.join(root, "timeline.json")))
    t_det = info["T_DET"]
    stage = os.path.join(root, "_master"); os.makedirs(stage, exist_ok=True)
    for f in os.listdir(stage):
        os.remove(os.path.join(stage, f))
    starts = {}; metas = {"_events": info["events"]}; g = 0
    for shot in ORDER:
        if shot == "flash":
            starts[shot] = g
            for c in FLASH:
                Image.new("RGB", (W, H), c).save(os.path.join(stage, "m%05d.png" % g), compress_level=1); g += 1
            continue
        d = os.path.join(root, shot)
        files = sorted(f for f in os.listdir(d) if f.startswith("f") and f.endswith(".png"))
        files = files[TRIM_HEAD.get(shot, 0):]
        n = len(files); starts[shot] = g
        meta = json.load(open(os.path.join(d, "meta.json"))) if shot != "card" else {}
        idx = [int(f[1:5]) for f in files]
        metas[shot] = {str(k): meta[str(ix)] for k, ix in enumerate(idx)} if shot != "card" else {}
        for k, f in enumerate(files):
            img = Image.open(os.path.join(d, f))
            if shot == "card":
                frame = card_frame(img, k, n).convert("RGBA")
            else:
                frame = img.convert("RGB").resize((W, H), Image.LANCZOS).convert("RGBA")
                shadowed(frame, overlay_for(shot, k, n, metas[shot][str(k)], t_det))
            # transitions: fade in from black at the head, dip between card and action, fade out at the end
            fade = 1.0
            if shot == "card":
                fade = min(1.0, (k + 1) / 8.0, (n - k) / 6.0)
            elif shot == "throw":
                fade = min(1.0, (k + 1) / 6.0)
            elif shot == "top":
                fade = min(1.0, (n - k) / 14.0)
            if fade < 1.0:
                frame = Image.blend(Image.new("RGBA", frame.size, (0, 0, 0, 255)), frame, fade)
            frame.convert("RGB").save(os.path.join(stage, "m%05d.png" % g), compress_level=1)
            g += 1
        print("staged", shot, n); sys.stdout.flush()
    total = g / FPS
    wav = os.path.join(root, "mix.wav")
    build_audio(wav, starts, metas, t_det, total)
    vf = "unsharp=5:5:0.55:5:5:0.0,vignette=PI/7,noise=alls=4:allf=t+u,format=yuv420p"
    cmd = ["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", os.path.join(stage, "m%05d.png"), "-i", wav,
           "-vf", vf, "-c:v", "libx264", "-preset", "medium" if draft else "slow", "-crf", "21" if draft else "18",
           "-maxrate", "14M", "-bufsize", "28M", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest", out]
    subprocess.check_call(cmd)
    print("wrote", out, "%.2fs" % total, starts)

if __name__ == "__main__":
    main()
