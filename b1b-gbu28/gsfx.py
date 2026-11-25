"""Recorded sound effects for the soundtracks of segments 09 and 10.

The recordings come from the Epidemic Sound catalogue (reached through Higgsfield) and are licensed, not ours to
redistribute, so they are NOT in the repository.  Put them as 48 kHz stereo WAV files, named as below, in the folder
`sfx/` beside this file (ignored by git) or in $SFX_DIR.  Without them the post scripts fall back to the old
synthesized soundtrack.

  name            catalogue title
  jet             Motors, Turbine, Jet Engine, Runway
  latch           Mechanical, Latch, Metal Latch, Heavy, Lock, Unlock, MKH 50
  whoosh          Swooshes, Whoosh, Wind Whooshes Panned, Whistling 03
  missile         Guns, Artillery, Missile, Fly By, Huge Missile
  wind            Ambience, Desert, Desolation, Canyon, Wind
  impact          Rocks, Impact, Hit Rock into the Earth
  debris          Rocks, Crash & Debris, Heavy, Big Hit, Stone Debris 05
  boom_muffled    Explosions, Real, Boom, Distant Explosion, Low, Muffled 02
  boom_deep       Designed, Boom, Cinematic, Impact, Big, Deep, Low Rumble, Growl, Frightening, Muffled
  hiss            Air, Hiss, Steam, Mist, Smoke, Gas, Release, Long, Close 01
  collapse        Destruction, Collapse, Stone Wall Collapsing, Rumble, Heavy Debris, Cracking, Stones Rolling 01
  quake           Natural Disaster, Earthquake, Rumble, Rocks In Motion 01
  drone           Designed, Drone, Tension, Low
"""
import os, sys, wave, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion"))
import post as gp
from post import SR

DIR = os.environ.get("SFX_DIR") or os.path.join(HERE, "sfx")
NAMES = ("jet", "latch", "whoosh", "missile", "wind", "impact", "debris", "boom_muffled", "boom_deep", "hiss", "collapse", "quake", "drone")
_cache = {}

def available():
    return all(os.path.exists(os.path.join(DIR, n + ".wav")) for n in NAMES)

def load(name):
    if name not in _cache:
        w = wave.open(os.path.join(DIR, name + ".wav")); n = w.getnframes(); ch = w.getnchannels(); assert w.getframerate() == SR and w.getsampwidth() == 2, name
        x = np.frombuffer(w.readframes(n), "<i2").astype(np.float64).reshape(-1, ch) / 32768.0; _cache[name] = x if ch == 2 else np.repeat(x, 2, 1)
    return _cache[name]

def _filt(x, lp=None, hp=None):
    for c in range(2):
        if lp:
            x[:, c] = gp.lp(x[:, c], lp, 2)
        if hp:
            x[:, c] = gp.hp(x[:, c], hp, 1)
    return x

def _fade(x, fi, fo):
    n = len(x); a = min(int(fi * SR), n // 2); b = min(int(fo * SR), n // 2)
    if a > 0:
        x[:a] *= np.linspace(0, 1, a)[:, None] ** 2
    if b > 0:
        x[-b:] *= np.linspace(1, 0, b)[:, None] ** 2
    return x

def cut(name, t0, dur, speed=1.0, fi=0.005, fo=0.15, lp=None, hp=None, norm=True, drive=0.0):
    """`dur` seconds of output taken from t0 in the recording; speed < 1 plays it slower and lower (for slow motion).
    norm scales the piece so that its peak is 1.  drive > 0 saturates it, which adds overtones to a very deep sound so that
    it can still be heard on small loudspeakers."""
    src = load(name); a = int(t0 * SR); n = int(dur * SR); pos = a + np.arange(n) * speed; pos = pos[pos < len(src) - 1]; i = pos.astype(int); f = (pos - i)[:, None]
    x = src[i] * (1 - f) + src[i + 1] * f; x = _filt(x, lp, hp)
    if norm or drive:
        x = x / (np.abs(x).max() + 1e-9)
    if drive:
        x = np.tanh(drive * x) / math.tanh(drive)
    return _fade(x, fi, fo)

def crunch(name, t0, dur, speed=1.0, drive=6.0, hp=170.0, lp=2500.0, fi=0.005, fo=0.6):
    """The audible body of a very deep sound: the piece is saturated hard and only what lies above `hp` is kept, so that an
    explosion recorded as a low rumble also carries on loudspeakers that cannot play the rumble itself."""
    x = cut(name, t0, dur, speed=speed, fi=0.0, fo=0.0, drive=drive); x = _filt(x, lp, hp); x = x / (np.abs(x).max() + 1e-9); return _fade(x, fi, fo)

def bed(name, dur, t0=0.0, speed=1.0, fi=0.4, fo=0.4, lp=None, hp=None, level=0.1):
    """A steady recording laid under `dur` seconds, looped with cross-fades if it is too short; its RMS is set to `level`."""
    src = load(name); need = int(dur * SR * speed) + SR; seg = src[int(t0 * SR): int(t0 * SR) + need]
    while len(seg) < need:                                               # loop with a one-second cross-fade
        xf = SR; more = src[int(t0 * SR): int(t0 * SR) + need]; r = np.linspace(0, 1, xf)[:, None]; seg = np.vstack([seg[:-xf], seg[-xf:] * (1 - r) + more[:xf] * r, more[xf:]])
    pos = np.arange(int(dur * SR)) * speed; i = pos.astype(int); f = (pos - i)[:, None]; x = seg[i] * (1 - f) + seg[i + 1] * f; x = _filt(x, lp, hp)
    x = x * (level / (math.sqrt((x ** 2).mean()) + 1e-9)); return _fade(x, fi, fo)

def put(mx, t, x, gain=1.0, pan=0.0):
    """Add a stereo piece to a gp.Mix at time t (pan -1 .. 1 shifts the balance)."""
    i = int(t * SR)
    if i < 0:
        x = x[-i:]; i = 0
    n = min(len(x), len(mx.b) - i)
    if n > 0:
        mx.b[i:i + n, 0] += x[:n, 0] * gain * min(1.0, 1.0 - pan); mx.b[i:i + n, 1] += x[:n, 1] * gain * min(1.0, 1.0 + pan)

def finish(mx, total, path):
    """Gentle limiter, fade-out, normalise, write 16-bit stereo."""
    x = np.tanh(mx.b[: int(total * SR)] * 1.05); fo = int(0.8 * SR); x[-fo:] *= np.linspace(1, 0, fo)[:, None]; x = x / (np.abs(x).max() + 1e-9) * 0.89
    with wave.open(path, "wb") as w_:
        w_.setnchannels(2); w_.setsampwidth(2); w_.setframerate(SR); w_.writeframes((x * 32767).astype("<i2").tobytes())
