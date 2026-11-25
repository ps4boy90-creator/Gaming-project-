"""GBU-28/B: the BLU-113/B penetrator with its Paveway III guidance unit and folding-wing tail, and a cut-open BLU-113.

Bomb frame: middle of the 3.90 m warhead at the origin, nose towards +X.
From sources (FAS / GlobalSecurity, the 2005 BLU-122 briefing, designation-systems.net, Kopp): 5.84 m long overall, the
warhead 3.90 m long and 370 mm across with a wall 58 mm thick (the first ones were bored-out 8-inch howitzer barrels),
286 kg of explosive, the nose cone and fuze of the BLU-109; a Paveway III guidance unit (WGU-36/B) on the nose and the
BSG-92/B airfoil group at the tail, whose four wings open from 0.72 m to 1.68 m across.
The guidance unit (a slim seeker housing, a control section with four large swept canards, a collar over the steel
nose), the boxy tail fins with their spring-out panels, the lug strip and the cable conduit are proportioned from a
profile photograph of the bomb; the inside of the warhead is an estimate.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "reaper-hellfire")); sys.path.insert(0, HERE)
from qgeo import *
from util import new_obj, grid_faces
import gconst as C

L = C.BLU_L; R = C.BLU_D / 2; NL = C.NOSE_L; FRONT = 0.95; TAIL = C.GBU_L - L - FRONT       # the guidance unit reaches 0.95 m ahead of the steel nose
OLIVE = (0.095, 0.105, 0.062, 1); YELLOW = (0.70, 0.52, 0.03, 1); KIT = (0.150, 0.158, 0.150, 1); SEEKER = (0.20, 0.085, 0.055, 1); STEEL = (0.20, 0.20, 0.21, 1); GLASS = (0.012, 0.012, 0.016, 1)
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
    S.add(*box((0.0, 0, R + 0.012), (1.05, 0.11, 0.024)), color=OLIVE)                                                                       # the strip that carries the lugs
    for x in (0.381, -0.381):                                                                                                                # lugs, 30 in apart
        S.add(*box((x, 0, R + 0.045), (0.075, 0.04, 0.05)), color=STEEL)
    a = math.radians(38.0); er = np.array([0, math.sin(a), math.cos(a)])                                                                     # cable conduit from the tail to the guidance unit
    S.add(*box(er * (R + 0.012) + EX * 0.25, (L - 0.9, 0.05, 0.026), rot=np.array([[1, 0, 0], [0, math.cos(a), math.sin(a)], [0, -math.sin(a), math.cos(a)]])), color=OLIVE)
    return S.mesh("blu113", sharp=math.radians(40))

CAN_SPAN = 0.80                                                      # across the canard tips (from the profile photograph)

def _front():
    """Guidance unit, after the Paveway III of the photographs: a collar over the steel nose, a slim control section with four
    large swept canards, a slimmer seeker housing and its dome."""
    S = Shell(); x0 = L / 2
    S.add(*revolve([(x0 - s, max(r_out(s) + 0.008, 0.105)) for s in (0.66, 0.62, 0.52, 0.42, 0.32, 0.22, 0.14, 0.08, 0.04)], 28), color=OLIVE)                # collar, in the body's colour
    S.add(*revolve([(x0 - 0.05, 0.1055), (x0 + 0.52, 0.1055), (x0 + 0.56, 0.086), (x0 + 0.86, 0.086)], 28), color=KIT)                             # control section
    S.add(*revolve([(x0 + 0.57, 0.0875), (x0 + 0.855, 0.0875)], 28), color=SEEKER)                                                              # seeker housing
    S.add(*ellipsoid((x0 + 0.86, 0, 0), (0.09, 0.086, 0.086), 20, 10), color=GLASS)                                                             # dome
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2; er = np.array([0, math.cos(a), math.sin(a)]); n = np.cross(EX, er); q = lambda x, h: EX * x + er * h; h = CAN_SPAN / 2
        S.add(*plate([q(x0 + 0.50, 0.09), q(x0 + 0.12, h), q(x0 - 0.04, h), q(x0 - 0.18, 0.10)], n, 0.016), color=KIT)                           # canards: swept, root 0.68 m
    return S.mesh("gbu28_front", sharp=math.radians(40))

def _tail():
    S = Shell(); x0 = -L / 2
    S.add(*revolve([(x0 + 0.03, R + 0.006), (x0 - 0.16, R + 0.006), (x0 - 0.20, R - 0.004), (x0 - TAIL + 0.10, 0.150), (x0 - TAIL, 0.132), (x0 - TAIL, 0.0)], 28), color=KIT)
    return S.mesh("gbu28_tail", sharp=math.radians(40))

FIN_H = C.SPAN_SHUT / 2                                              # the fixed part of each tail fin reaches the folded span

def _fin():
    """The fixed part of one tail fin in its own frame: root along X at the origin, the blade towards +Z."""
    S = Shell(); S.add(*plate([(0.0, 0, 0), (-0.10, 0, FIN_H), (-0.62, 0, FIN_H), (-0.85, 0, 0)], EY, 0.020), color=KIT)
    return S.mesh("gbu28_fin", sharp=math.radians(40))

def _wing():
    """The panel that springs out of a fin after release, in the same frame, 1 m tall (scaled to the half span wanted)."""
    S = Shell(); S.add(*plate([(-0.14, 0, 0), (-0.17, 0, 1.0), (-0.56, 0, 1.0), (-0.60, 0, 0)], EY, 0.010), color=KIT)
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
        self.ob = self.root; self.warhead = self.front = self.tail = None; self.wings = []; self.fins = []
        if cut:
            self.warhead = ob("cut", "blu113_cut", _cutaway); return
        if "warhead" in parts:
            self.warhead = ob("warhead", "blu113", _warhead)
        if "front" in parts:
            self.front = ob("front", "gbu28_front", _front)
        if "tail" in parts:
            self.tail = ob("tail", "gbu28_tail", _tail)
            self.fins = []
            for k in range(4):
                rot = (math.pi / 4 + k * math.pi / 2 - math.pi / 2, 0, 0)
                f = ob("fin%d" % k, "gbu28_fin", _fin); f.location = (-L / 2 - 0.10, 0, 0); f.rotation_euler = rot; self.fins.append(f)
                w = ob("wing%d" % k, "gbu28_wing", _wing); w.location = (-L / 2 - 0.10, 0, 0); w.rotation_euler = rot; self.wings.append(w)
        self.set(0.0)

    def set(self, open_=0.0):
        """open_: 0 = wings folded (0.72 m across), 1 = open (1.68 m)."""
        h = (C.SPAN_SHUT + (C.SPAN_OPEN - C.SPAN_SHUT) * open_) / 2
        for w in self.wings:
            w.scale = (1.0, 1.0, h - 0.004 if open_ < 1e-3 else h)        # folded, the panel lies inside the fixed fin

    def hide(self, warhead=None, front=None, tail=None):
        for o, v in ((self.warhead, warhead), (self.front, front), (self.tail, tail)):
            if o is not None and v is not None:
                o.hide_render = v
        if tail is not None:
            for w in self.wings + getattr(self, "fins", []):
                w.hide_render = tail
