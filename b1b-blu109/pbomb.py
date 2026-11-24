"""GBU-31(V)3/B: the BLU-109/B penetrator bomb with the JDAM tail kit and body strakes, and a cut-open BLU-109.

Bomb frame: centre of the 2.40 m warhead at the origin, nose towards +X, lugs up (+Z).
From sources (USAF Weapons File, ordnance data sheet, USAF JDAM fact sheet): warhead 2.40 m long and 368 mm in
diameter, a forged steel case at least 27 mm thick, about 243 kg of explosive, a fuze in the tail (FMU-143), two lugs
30 inches apart; with the tail kit the bomb is 3.77 m long and 0.635 m across the fins; three of the four fins move.
The nose's exact curve, the solid length of the nose, the strakes' size and the tail kit's taper are estimates from
photographs.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "reaper-hellfire")); sys.path.insert(0, HERE)
from qgeo import *
from util import new_obj, grid_faces
import pconst as C

L = C.BLU_L; R = C.BLU_D / 2; NL = C.NOSE_L; TAIL = C.GBU_L - C.BLU_L
OLIVE = (0.115, 0.125, 0.070, 1); YELLOW = (0.70, 0.52, 0.03, 1); KIT = (0.19, 0.20, 0.21, 1); STEEL = (0.20, 0.20, 0.21, 1); CUT = (0.10, 0.105, 0.115, 1); FILLC = (0.50, 0.30, 0.05, 1); FUZE = (0.55, 0.12, 0.08, 1); DARK = (0.03, 0.03, 0.03, 1)

def r_out(s):
    """Outer radius s metres behind the nose tip: a blunt-tipped ogive, then the straight body."""
    if s >= NL:
        return R
    u = s / NL; return max(R * math.sin(math.pi / 2 * u) ** 0.72, 0.0)

def r_in(s):
    """Radius of the explosive cavity: the nose is solid steel for the first 0.36 m, the tail is closed by a plate."""
    if s < 0.36 or s > L - 0.07:
        return 0.0
    return max(min(r_out(s) - C.CASE, (s - 0.36) * 0.75), 0.0)

def _stations():
    return sorted(set([0.0, 0.006, 0.02, 0.05] + list(np.linspace(0.09, NL, 12)) + list(np.linspace(NL, L, 10))))

def _kit(S):
    """Tail kit: adapter collar, tapering body with the guidance unit, four fins (three move), and the body strakes."""
    x0 = -L / 2
    S.add(*revolve([(x0 + 0.01, R + 0.004), (x0 - 0.10, R + 0.004), (x0 - 0.22, 0.165), (x0 - TAIL + 0.42, 0.150), (x0 - TAIL + 0.05, 0.118), (x0 - TAIL, 0.105), (x0 - TAIL, 0.0)], 32), color=KIT)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2; er = np.array([0, math.cos(a), math.sin(a)]); n = np.cross(EX, er); q = lambda x, h: EX * x + er * h
        S.add(*plate([q(x0 - TAIL + 0.40, 0.14), q(x0 - TAIL + 0.33, C.TAIL_SPAN / 2), q(x0 - TAIL + 0.05, C.TAIL_SPAN / 2), q(x0 - TAIL + 0.03, 0.11)], n, 0.016), color=KIT)
        S.add(*plate([q(0.55, R - 0.004), q(0.42, R + 0.062), q(-0.72, R + 0.062), q(-0.80, R - 0.004)], n, 0.010), color=KIT)                     # strake
    for x in (0.38, -0.66):                                                                                                                  # the two bands that hold the strakes
        S.add(*revolve([(x + 0.035, R + 0.006), (x - 0.035, R + 0.006)], 32), color=STEEL)

def _body():
    S = Shell(); st = _stations()
    V, Q, T = revolve([(L / 2 - s, r_out(s)) for s in st][::-1], 36); S.add(V, Q, T, OLIVE)
    S.add(*revolve([(L / 2 - 0.70 + 0.04, R + 0.0015), (L / 2 - 0.70 - 0.04, R + 0.0015)], 36), color=YELLOW)                                    # high-explosive band
    for x in (0.381, -0.381):                                                                                                                  # lugs, 30 in apart
        S.add(*box((x, 0, R + 0.02), (0.07, 0.035, 0.05)), color=STEEL)
    _kit(S)
    return S.mesh("gbu31", sharp=math.radians(40))

def _cutaway():
    """The warhead alone with the near half cut away along the plane y = 0 (the far half, y > 0, is kept)."""
    S = Shell(); st = _stations(); a = np.linspace(-math.pi / 2, math.pi / 2, 19)
    V = np.array([[L / 2 - s, r_out(s) * math.cos(t), r_out(s) * math.sin(t)] for s in st for t in a]); S.add(V, grid_faces(len(st), len(a)), None, OLIVE)
    for lo, hi, col, dy in ((lambda s: -r_out(s), lambda s: -r_in(s), CUT, 0.0), (lambda s: r_in(s), lambda s: r_out(s), CUT, 0.0), (lambda s: -r_in(s), lambda s: r_in(s), FILLC, 0.002)):
        V = np.array([[L / 2 - s, dy, f(s)] for s in st for f in (lo, hi)]); S.add(V, grid_faces(len(st), 2), None, col)
    S.add(*box((-L / 2 + 0.17, 0.0, 0.0), (0.20, 0.004, 0.076)), color=FUZE)                                                                   # the fuze in its well at the tail
    S.add(*box((-L / 2 + 0.035, 0.0, 0.0), (0.07, 0.006, 2 * R - 0.02)), color=STEEL)                                                           # closure plate
    return S.mesh("blu109_cut", sharp=math.radians(40))

class Bomb:
    def __init__(self, col=None, name="GBU31", cut=False):
        col = col or bpy.context.scene.collection; D = bpy.data.meshes; nm = "blu109_cut" if cut else "gbu31"
        me = D.get(nm) or (_cutaway() if cut else _body())
        if not me.materials:
            me.materials.append(bpy.data.materials.get("BombPaint") or paint_mat("BombPaint", rough=0.55))
        self.ob = bpy.data.objects.new(name, me); col.objects.link(self.ob); self.ob.rotation_mode = 'QUATERNION'
