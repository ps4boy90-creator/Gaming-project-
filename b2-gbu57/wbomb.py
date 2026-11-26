"""GBU-57 Massive Ordnance Penetrator, and the same body cut open.

Bomb frame: middle of the 5.55 m steel body at the origin, nose towards +X; the tail section with its four lattice
fins reaches GBU_L - BLU_L behind the body.
From sources: 6.25 m long, 0.80 m across, 30,000 lb class with 2,423 kg of explosive, short wings on the body and
lattice ("grid") fins at the tail that are stowed for carriage.  The shape of the nose, the size and place of the
wings, the lattice fins, the tail section and the colour are estimated from published photographs; the inside
(solid nose, wall, the two fills, the fuze well) is a diagram drawn from the published weights, not a drawing of the
real bomb.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "reaper-hellfire")); sys.path.insert(0, HERE)
from mathutils import Quaternion
from qgeo import *
from util import new_obj, grid_faces
import wconst as C

L = C.BLU_L; R = C.BLU_D / 2; NL = C.NOSE_L; TAIL = C.GBU_L - C.BLU_L
BODY = (0.085, 0.095, 0.075, 1); YELLOW = (0.70, 0.52, 0.03, 1); KIT = (0.16, 0.17, 0.18, 1); STEEL = (0.20, 0.20, 0.21, 1); CUT = (0.10, 0.105, 0.115, 1); FILLC = (0.50, 0.30, 0.05, 1); FILL2 = (0.74, 0.60, 0.36, 1); FUZE = (0.55, 0.12, 0.08, 1)
GRID_W = 0.62; GRID_H = (C.TAIL_SPAN - 2 * R) / 2                    # one lattice fin: its width along the body's circumference and how far it stands out

def r_out(s):
    """Outer radius s metres behind the nose tip: an ogive with a slightly blunted point, then the straight body."""
    if s >= NL:
        return R
    u = s / NL; return max(R * math.sin(math.pi / 2 * u) ** 0.80, 0.0)

def r_in(s):
    """Radius of the explosive cavity: the nose is solid steel for the first 1.55 m, the tail is closed by a thick plug."""
    if s < 1.55 or s > L - 0.30:
        return 0.0
    return max(min(R - C.CASE, (s - 1.55) * 0.55), 0.0)

def _stations():
    return sorted(set([0.0, 0.008, 0.03, 0.07] + list(np.linspace(0.12, NL, 14)) + list(np.linspace(NL, L, 14)) + [1.55, 1.62, 1.8, 2.17, L - 0.30]))

def _kit(S):
    """What is stripped off at the surface: the tail section with its four lattice fins, and the short wings on the body."""
    x0 = -L / 2
    S.add(*revolve([(x0 + 0.01, R + 0.006), (x0 - 0.12, R + 0.006), (x0 - TAIL + 0.10, R - 0.05), (x0 - TAIL, R - 0.09), (x0 - TAIL, 0.0)], 36), color=KIT)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2; er = np.array([0, math.cos(a), math.sin(a)]); et = np.cross(EX, er); xc = x0 - TAIL * 0.52
        n = et; q = lambda x, h: EX * x + er * h; hw = C.WING_SPAN / 2                                                                             # short wing on the body
        S.add(*plate([q(0.95, R - 0.004), q(0.55, hw), q(-0.35, hw), q(-0.55, R - 0.004)], n, 0.030), color=KIT)

FIN_X = -L / 2 - TAIL * 0.52                                         # where the lattice fins are hinged

def _fin():
    """One lattice fin in its own frame: hinged at the origin, standing out along +Z, its cells open along X."""
    S = Shell(); S.add(*box((0, 0, 0.0), (0.16, 0.20, 0.12)), color=STEEL); z0 = 0.05; zc = z0 + GRID_H / 2
    for dy in (-GRID_W / 2, GRID_W / 2):                               # the frame
        S.add(*box((0, dy, zc), (0.14, 0.022, GRID_H)), color=KIT)
    for dz in (0.0, GRID_H):
        S.add(*box((0, 0, z0 + dz), (0.14, GRID_W, 0.022)), color=KIT)
    for j in range(1, 5):                                               # the cells: thin walls crossing at right angles
        S.add(*box((0, -GRID_W / 2 + j * GRID_W / 5, zc), (0.13, 0.008, GRID_H)), color=KIT)
    for j in range(1, 6):
        S.add(*box((0, 0, z0 + j * GRID_H / 6), (0.13, GRID_W, 0.008)), color=KIT)
    return S.mesh("mop_fin", sharp=math.radians(40))

def _body(kit=True):
    S = Shell(); st = _stations()
    V, Q, T = revolve([(L / 2 - s, r_out(s)) for s in st][::-1], 40); S.add(V, Q, T, BODY)
    S.add(*revolve([(L / 2 - 1.75 + 0.05, R + 0.002), (L / 2 - 1.75 - 0.05, R + 0.002)], 40), color=YELLOW)                                      # high-explosive band
    for x in (0.60, -0.60):                                                                                                                  # lugs
        S.add(*box((x, 0, R + 0.03), (0.14, 0.07, 0.07)), color=STEEL)
    for x in (1.35, -1.75):                                                                                                                  # bands
        S.add(*revolve([(x + 0.04, R + 0.004), (x - 0.04, R + 0.004)], 40), color=STEEL)
    if kit:
        _kit(S)
    return S.mesh("gbu57" if kit else "mop_body", sharp=math.radians(40))

def _kit_only():
    S = Shell(); _kit(S); return S.mesh("mop_kit", sharp=math.radians(40))

def _cutaway():
    """The body alone with the near half cut away along the plane y = 0 (the far half, y > 0, is kept; it is looked at from -Y)."""
    S = Shell(); st = _stations(); a = np.linspace(-math.pi / 2, math.pi / 2, 21); xs = 1.55 + 0.72 * (L - 0.30 - 1.55)        # the smaller fill sits in the front of the cavity (a guess at the arrangement)
    V = np.array([[L / 2 - s, r_out(s) * math.cos(t), r_out(s) * math.sin(t)] for s in st for t in a]); S.add(V, grid_faces(len(st), len(a)), None, BODY)
    V = np.array([[L / 2 - s, 0.0, f * r_out(s)] for s in st for f in (-1.0, 1.0)]); S.add(V, grid_faces(len(st), 2), None, CUT)                     # the steel
    for s0, s1, col in ((1.55, 2.17, FILL2), (2.17, L - 0.30, FILLC)):
        ss = [s for s in st if s0 <= s <= s1]; V = np.array([[L / 2 - s, -0.003, f * r_in(s)] for s in ss for f in (-1.0, 1.0)]); S.add(V, grid_faces(len(ss), 2), None, col)
    S.add(*box((-L / 2 + 0.52, -0.006, 0.0), (0.44, 0.004, 0.16)), color=FUZE)                                                                  # the fuze in its well at the tail
    return S.mesh("mop_cut", sharp=math.radians(40))

class Bomb:
    def __init__(self, col=None, name="GBU57", cut=False, part="all"):
        """part: "all" = the bomb as dropped; "warhead" = the steel body alone; "kit" = the tail section, lattice fins and wings alone."""
        col = col or bpy.context.scene.collection; D = bpy.data.meshes; nm = "mop_cut" if cut else {"all": "gbu57", "warhead": "mop_body", "kit": "mop_kit"}[part]
        me = D.get(nm) or (_cutaway() if cut else _kit_only() if part == "kit" else _body(part == "all"))
        if not me.materials:
            me.materials.append(bpy.data.materials.get("BombPaint") or paint_mat("BombPaint", rough=0.55))
        self.ob = bpy.data.objects.new(name, me); col.objects.link(self.ob); self.ob.rotation_mode = 'QUATERNION'
        self.fins = []
        if not cut and part in ("all", "kit"):
            fm = D.get("mop_fin") or _fin()
            if not fm.materials:
                fm.materials.append(me.materials[0])
            for k in range(4):
                f = bpy.data.objects.new(name + "_fin%d" % k, fm); col.objects.link(f); f.parent = self.ob; f.rotation_mode = 'QUATERNION'; a = math.pi / 4 + k * math.pi / 2
                f.location = (FIN_X, (R + 0.05) * math.cos(a), (R + 0.05) * math.sin(a)); self.fins.append((f, a))
        self.set_fins(1.0)

    def set_fins(self, open_=1.0):
        """open_: 0 = folded back along the tail (as carried), 1 = standing out."""
        for f, a in self.fins:
            f.rotation_quaternion = Quaternion((1, 0, 0), a - math.pi / 2) @ Quaternion((0, 1, 0), -math.radians(88.0) * (1 - open_))

    def hide(self, v):
        self.ob.hide_render = v
        for f, a in self.fins:
            f.hide_render = v
