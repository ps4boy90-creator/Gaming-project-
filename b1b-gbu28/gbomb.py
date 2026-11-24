"""GBU-28/B: the BLU-113/B penetrator with its Paveway III guidance unit and folding-wing tail, and a cut-open BLU-113.

Bomb frame: middle of the 3.90 m warhead at the origin, nose towards +X.
From sources (FAS / GlobalSecurity, the 2005 BLU-122 briefing, designation-systems.net, Kopp): 5.84 m long overall, the
warhead 3.90 m long and 370 mm across with a wall 58 mm thick (the first ones were bored-out 8-inch howitzer barrels),
286 kg of explosive, the nose cone and fuze of the BLU-109; a Paveway III guidance unit (WGU-36/B) on the nose and the
BSG-92/B airfoil group at the tail, whose four wings open from 0.72 m to 1.68 m across.
The lengths of the guidance unit and the tail, the canards' size and the inside of the warhead are estimated from
photographs.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "reaper-hellfire")); sys.path.insert(0, HERE)
from qgeo import *
from util import new_obj, grid_faces
import gconst as C

L = C.BLU_L; R = C.BLU_D / 2; NL = C.NOSE_L; FRONT = 0.95; TAIL = C.GBU_L - L - FRONT       # the guidance unit reaches 0.95 m ahead of the steel nose
OLIVE = (0.105, 0.115, 0.065, 1); YELLOW = (0.70, 0.52, 0.03, 1); KIT = (0.125, 0.135, 0.085, 1); STEEL = (0.20, 0.20, 0.21, 1); GLASS = (0.012, 0.012, 0.016, 1)
CUT = (0.10, 0.105, 0.115, 1); FILLC = (0.50, 0.30, 0.05, 1); FUZE = (0.55, 0.12, 0.08, 1)

def r_out(s):
    """Outer radius s metres behind the steel nose tip."""
    if s >= NL:
        return R
    return max(R * math.sin(math.pi / 2 * s / NL) ** 0.72, 0.0)

def r_in(s):
    """Radius of the explosive cavity: a bore 254 mm across; the nose is solid for 0.55 m, the tail is closed by a plug."""
    if s < 0.55 or s > L - 0.10:
        return 0.0
    return max(min(R - C.CASE, (s - 0.55) * 0.8), 0.0)

def _stations():
    return sorted(set([0.0, 0.006, 0.02, 0.05] + list(np.linspace(0.09, NL, 12)) + list(np.linspace(NL, L, 12)) + [0.55, 0.60, 0.70, L - 0.10]))

def _warhead():
    S = Shell(); st = _stations()
    S.add(*revolve([(L / 2 - s, r_out(s)) for s in st][::-1], 36), color=OLIVE)
    S.add(*revolve([(L / 2 - 0.95 + 0.04, R + 0.0015), (L / 2 - 0.95 - 0.04, R + 0.0015)], 36), color=YELLOW)                                    # high-explosive band
    for x in (0.381, -0.381):                                                                                                                # lugs, 30 in apart
        S.add(*box((x, 0, R + 0.02), (0.07, 0.035, 0.05)), color=STEEL)
    return S.mesh("blu113", sharp=math.radians(40))

def _front():
    """Guidance unit: an adapter collar over the nose, the control section with four canards, the seeker on its gimbal ring."""
    S = Shell(); x0 = L / 2
    S.add(*revolve([(x0 - 0.62, R + 0.006), (x0 - 0.30, R + 0.006), (x0 - 0.02, 0.150), (x0 + 0.52, 0.135), (x0 + 0.60, 0.105), (x0 + 0.66, 0.105), (x0 + 0.70, 0.125), (x0 + 0.86, 0.125), (x0 + 0.86, 0.0)], 28), color=KIT)
    S.add(*ellipsoid((x0 + 0.86, 0, 0), (0.09, 0.118, 0.118), 20, 10), color=GLASS)                                                             # seeker dome
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2; er = np.array([0, math.cos(a), math.sin(a)]); n = np.cross(EX, er); q = lambda x, h: EX * x + er * h
        S.add(*plate([q(x0 + 0.42, 0.13), q(x0 + 0.36, 0.40), q(x0 + 0.20, 0.40), (q(x0 + 0.10, 0.13))], n, 0.014), color=KIT)                   # canards
    return S.mesh("gbu28_front", sharp=math.radians(40))

def _tail():
    S = Shell(); x0 = -L / 2
    S.add(*revolve([(x0 + 0.02, R + 0.005), (x0 - 0.22, R + 0.005), (x0 - 0.70, 0.150), (x0 - TAIL + 0.04, 0.120), (x0 - TAIL, 0.100), (x0 - TAIL, 0.0)], 28), color=KIT)
    return S.mesh("gbu28_tail", sharp=math.radians(40))

def _wing():
    """One rear wing in its own frame: root along X at the origin, the blade reaching 1 m towards +Z (scaled to the span wanted)."""
    S = Shell(); S.add(*plate([(0.0, 0, 0), (-0.10, 0, 1.0), (-0.52, 0, 1.0), (-0.78, 0, 0)], EY, 0.016), color=KIT)
    return S.mesh("gbu28_wing", sharp=math.radians(40))

def _cutaway():
    """The warhead alone with the near half cut away along the plane y = 0 (the far half, y > 0, is kept)."""
    S = Shell(); st = _stations(); a = np.linspace(-math.pi / 2, math.pi / 2, 19)
    V = np.array([[L / 2 - s, r_out(s) * math.cos(t), r_out(s) * math.sin(t)] for s in st for t in a]); S.add(V, grid_faces(len(st), len(a)), None, OLIVE)
    for lo, hi, col, dy in ((lambda s: -r_out(s), lambda s: -r_in(s), CUT, 0.0), (lambda s: r_in(s), lambda s: r_out(s), CUT, 0.0), (lambda s: -r_in(s), lambda s: r_in(s), FILLC, 0.002)):
        V = np.array([[L / 2 - s, dy, f(s)] for s in st for f in (lo, hi)]); S.add(V, grid_faces(len(st), 2), None, col)
    S.add(*box((-L / 2 + 0.24, 0.0, 0.0), (0.22, 0.004, 0.076)), color=FUZE)                                                                    # the fuze in its well at the tail
    return S.mesh("blu113_cut", sharp=math.radians(40))

class Bomb:
    """The complete bomb, with parts that can be shown separately.  root (quaternion) carries warhead, front, tail and four wings."""
    def __init__(self, col=None, name="GBU28", cut=False, parts=("warhead", "front", "tail")):
        col = col or bpy.context.scene.collection; D = bpy.data.meshes; M = bpy.data.materials
        pm = M.get("BombPaint") or paint_mat("BombPaint", rough=0.55)
        def ob(nm, mesh_name, make):
            me = D.get(mesh_name) or make()
            if not me.materials:
                me.materials.append(pm)
            o = bpy.data.objects.new(name + "_" + nm, me); col.objects.link(o); o.parent = self.root; return o
        self.root = bpy.data.objects.new(name, None); col.objects.link(self.root); self.root.rotation_mode = 'QUATERNION'
        self.ob = self.root; self.warhead = self.front = self.tail = None; self.wings = []
        if cut:
            self.warhead = ob("cut", "blu113_cut", _cutaway); return
        if "warhead" in parts:
            self.warhead = ob("warhead", "blu113", _warhead)
        if "front" in parts:
            self.front = ob("front", "gbu28_front", _front)
        if "tail" in parts:
            self.tail = ob("tail", "gbu28_tail", _tail)
            for k in range(4):
                w = ob("wing%d" % k, "gbu28_wing", _wing); w.location = (-L / 2 - 0.16, 0, 0); w.rotation_euler = (math.pi / 4 + k * math.pi / 2 - math.pi / 2, 0, 0); self.wings.append(w)
        self.set(0.0)

    def set(self, open_=0.0):
        """open_: 0 = wings folded (0.72 m across), 1 = open (1.68 m)."""
        h = (C.SPAN_SHUT + (C.SPAN_OPEN - C.SPAN_SHUT) * open_) / 2
        for w in self.wings:
            w.scale = (1.0, 1.0, h)

    def hide(self, warhead=None, front=None, tail=None):
        for o, v in ((self.warhead, warhead), (self.front, front), (self.tail, tail)):
            if o is not None and v is not None:
                o.hide_render = v
        if tail is not None:
            for w in self.wings:
                w.hide_render = tail
