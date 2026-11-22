"""Los Angeles-class attack submarine, Flight II (the first boats with twelve vertical launch tubes in the bow).

Submarine frame: tip of the bow at the origin, the hull runs back along -X, axis on the X axis, up +Z.
From sources (US Navy fact file; Naval Encyclopedia): 109.7 m long, 10.06 m beam, one shaft, a sail with fairwater
planes, twelve Tomahawk tubes between the sonar sphere and the pressure hull, arranged as two inner rows of four and
two outer rows of two.  The hull lines, the sail's size and place, the control surfaces and the propeller are
proportioned from photographs and are approximate (the real propeller's shape is not public; a plain seven-bladed
one stands in for it).
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "reaper-hellfire")); sys.path.insert(0, HERE)
from qgeo import *
from util import new_obj
import tconst as C

LEN = C.SUB_LEN; R = C.SUB_R
HULL = (0.016, 0.017, 0.019, 1); DECK = (0.024, 0.025, 0.027, 1); HATCH = (0.036, 0.037, 0.040, 1); HOLE = (0.004, 0.004, 0.005, 1); BRONZE = (0.20, 0.13, 0.06, 1)
BOW = 10.5; STERN0 = 74.0; STERN1 = 106.5
SAIL_D = 27.0; SAIL_L = 8.8; SAIL_H = 5.0; SAIL_W = 2.0
TUBES = [(d, sg * 0.65) for d in (9.6, 10.9, 12.2, 13.5) for sg in (1, -1)] + [(d, sg * 1.95) for d in (10.9, 12.2) for sg in (1, -1)]     # a tight cluster, as in photographs
FIRE = (C.HATCH_X, C.HATCH_Y); HATCH_R = 0.50

def r_hull(d):
    if d < BOW:
        return R * (1.0 - ((BOW - d) / BOW) ** 2.2) ** (1.0 / 2.2)
    if d < STERN0:
        return R
    if d < STERN1:
        return 0.55 + (R - 0.55) * (1.0 - ((d - STERN0) / (STERN1 - STERN0)) ** 1.55)
    return max(0.55 * (1.0 - (d - STERN1) / (LEN - STERN1)) ** 0.6, 0.0)

def _top(d, y):
    """Point on the upper hull at distance d from the bow and offset y, with its outward normal."""
    r = r_hull(d); z = math.sqrt(max(r * r - y * y, 1e-6)); return np.array([-d, y, z]), np.array([0.0, y, z]) / r

def _hull():
    S = Shell(); ds = sorted(set([0.0, 0.03, 0.12, 0.3] + list(np.linspace(0.6, BOW, 16)) + list(np.arange(BOW, STERN0, 2.0)) + list(np.linspace(STERN0, STERN1, 22)) + list(np.linspace(STERN1, LEN, 6))))
    V, Q, T = revolve([(-d, r_hull(d)) for d in ds], 56); c = np.tile(np.array(HULL), (len(V), 1)); c[(V[:, 2] > 4.55) & (V[:, 0] < -8.0) & (V[:, 0] > -80.0)] = DECK      # flat-topped casing walkway tone
    S.add(V, Q, T, c)
    st = [(np.array([-SAIL_D, 0.0, z]), SAIL_L, SAIL_W / SAIL_L, (-1, 0, 0), (0, 1, 0)) for z in (R - 0.9, R + SAIL_H * 0.6, R + SAIL_H - 0.12, R + SAIL_H)]                    # sail
    st[-1] = (np.array([-SAIL_D - 0.10, 0.0, R + SAIL_H]), SAIL_L - 0.2, (SAIL_W - 0.25) / SAIL_L, (-1, 0, 0), (0, 1, 0))
    V, Q, T = surface(st, 26); S.add(V, Q, T, HULL)
    for sg in (1, -1):                                                                                                         # fairwater planes
        V, Q, T = wing((-SAIL_D - 2.3, sg * 0.55, R + 2.9), 2.7, 0.14, (-SAIL_D - 2.9, sg * 3.95, R + 2.9), 1.7, 0.12, (0, 0, 1), n=14, k=4); S.add(V, Q, T, HULL)
        V, Q, T = wing((-96.5, sg * 1.6, 0.0), 4.0, 0.13, (-98.2, sg * 4.95, 0.0), 2.2, 0.11, (0, 0, 1), n=14, k=4); S.add(V, Q, T, HULL)                                      # stern planes
        V, Q, T = wing((-96.5, 0.0, sg * 1.6), 4.0, 0.13, (-98.2, 0.0, sg * 4.95), 2.2, 0.11, (0, 1, 0), n=14, k=4); S.add(V, Q, T, HULL)                                      # rudders
    S.add(*box((-58.0, -R * math.cos(math.radians(38)) - 0.12, R * math.sin(math.radians(38)) + 0.12), (62.0, 0.42, 0.42), rot=None), color=HULL)                             # towed-array fairing down the starboard side
    for d, y in TUBES:                                                                                                          # launch-tube hatches
        p, n = _top(d, y); fire = (abs(d - FIRE[0]) < 1e-6 and abs(y - FIRE[1]) < 1e-6)
        S.add(*revolve([(-0.01, HATCH_R + 0.06), (0.022, HATCH_R + 0.06), (0.022, HATCH_R + 0.01)], 28, axis=n, origin=p), color=HATCH)                                       # coaming ring
        if fire:
            S.add(*revolve([(-0.05, HATCH_R), (-0.6, HATCH_R), (-0.6, 0.0)], 28, axis=n, origin=p + n * 0.02), color=HOLE)                                                    # open tube mouth
        else:
            S.add(*revolve([(0.0, HATCH_R), (0.03, HATCH_R), (0.045, HATCH_R * 0.7), (0.05, 0.0)], 28, axis=n, origin=p), color=HATCH)
    return S.mesh("sub_hull", sharp=math.radians(34))

def _door():
    """The firing tube's hatch in its own frame: hinge on the X axis at the origin, the lid lying towards +Y when shut."""
    S = Shell(); S.add(*revolve([(0.0, HATCH_R), (0.03, HATCH_R), (0.045, HATCH_R * 0.7), (0.05, 0.0)], 28, axis=EZ, origin=(0, HATCH_R + 0.05, 0)), color=HATCH)
    S.add(*box((0, 0.03, 0.02), (0.5, 0.10, 0.06)), color=HATCH)
    return S.mesh("sub_door", sharp=math.radians(34))

def _prop():
    S = Shell(); S.add(*revolve([(0.0, 0.50), (-0.9, 0.42), (-1.6, 0.0)], 20), color=BRONZE)
    for k in range(7):
        a = 2 * math.pi * k / 7; er = np.array([0, math.cos(a), math.sin(a)]); et = np.array([0, -math.sin(a), math.cos(a)]); pitch = math.radians(38)
        cd = -EX * math.cos(pitch) + et * math.sin(pitch); up = np.cross(er, cd)
        st = [(-EX * 0.25 + er * rr + cd * (-0.5 * ch) + et * (0.55 * (rr / 2.3) ** 2), ch, 0.06, cd, up) for rr, ch in ((0.40, 0.55), (0.9, 0.95), (1.5, 1.10), (2.0, 0.85), (2.3, 0.30))]   # skewed back towards the tip
        S.add(*surface(st, 10), color=BRONZE)
    return S.mesh("sub_prop", sharp=math.radians(40))

class Submarine:
    def __init__(self, col=None, name="Sub"):
        col = col or bpy.context.scene.collection
        self.root = bpy.data.objects.new(name, None); col.objects.link(self.root); self.root.rotation_mode = 'QUATERNION'
        pm = bpy.data.materials.get("SubPaint") or paint_mat("SubPaint", rough=0.50, bump=0.25)
        self.hull = new_obj(name + "_Hull", _hull(), col, pm); self.hull.parent = self.root
        self.prop = new_obj(name + "_Prop", _prop(), col, bpy.data.materials.get("SubProp") or paint_mat("SubProp", rough=0.35, metal=0.9)); self.prop.parent = self.root; self.prop.location = (-LEN + 1.75, 0, 0)
        p, n = _top(*FIRE); self.hatch_pos = p; self.hatch_n = n
        # The lid is hinged on its outboard edge.  Its own frame: hinge on X, lid towards +Y, top +Z.
        self.side = 1.0 if FIRE[1] > 0 else -1.0; t = np.array([0.0, n[2], -n[1]]); self.door_roll = math.atan2(-n[1], n[2])
        self.door = new_obj(name + "_Door", _door(), col, pm); self.door.parent = self.root; self.door.rotation_mode = 'ZXY'     # turn about Z first, then swing about the hinge
        self.door.location = tuple(p + n * 0.03 + self.side * t * (HATCH_R + 0.05))
        self.set(0.0, 0.0)

    def set(self, door=0.0, prop_angle=0.0):
        """door: 0 shut .. 1 open (swung up about 100 degrees on its outboard hinge)."""
        self.door.rotation_euler = (self.door_roll - self.side * math.radians(100.0) * door, 0.0, math.pi if self.side > 0 else 0.0)
        self.prop.rotation_euler = (prop_angle, 0, 0)
