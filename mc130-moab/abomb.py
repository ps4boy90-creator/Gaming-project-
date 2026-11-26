"""GBU-43/B MOAB with its lattice fins, and the cradle and airdrop platform it rides on.

Bomb frame: the middle of the 9.19 m length at the origin, nose towards +X, wings in the X-Y plane.
Published: overall length and diameter; a thin aluminium case; fixed wings and four lattice fins that fold.
Estimated from photographs of the Air Force Armament Museum's example and of the 2003 prototype: the rod and the cone
of the nose, the narrower tail section and its eight-sided housing, the outline and place of the two wings, the
raceways along the body, the size and the cells of the fins, the cradle of aluminium beams, the platform.  The colour
is the museum example's (green, yellow nose); the 2003 test bomb was orange.  The inside (cut-open view) is a diagram.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "reaper-hellfire")); sys.path.insert(0, HERE)
from mathutils import Quaternion
from qgeo import *
from util import new_obj, grid_faces, nodemat
import aconst as C

L = C.GBU_L; R = C.GBU_D / 2; PL = C.PROBE_L; NL = C.NOSE_L; SA = C.AFT_S; RA = C.AFT_D / 2
S_TAPER = SA + 0.32; S_BOX = 8.36; R_BOX = 0.47; S_HINGE = 8.50; R_HINGE = 0.47
FIN_L = 1.06; FIN_W = 0.76; FIN_T = 0.11
WING_S = (3.45, 6.50); WING_TIP_S = (5.25, 6.42); WING_OUT = 0.52
GREEN = (0.020, 0.185, 0.050, 1); GREEN2 = (0.016, 0.150, 0.042, 1); YELLOW = (0.72, 0.52, 0.03, 1); STEEL = (0.22, 0.22, 0.23, 1); ALU = (0.52, 0.53, 0.54, 1); ALU2 = (0.40, 0.41, 0.42, 1); DARK = (0.03, 0.03, 0.03, 1)
WEB = (0.55, 0.50, 0.36, 1); CUTC = (0.62, 0.63, 0.64, 1); FILLC = (0.21, 0.155, 0.095, 1); BOOST = (0.62, 0.22, 0.10, 1); FUZEC = (0.60, 0.44, 0.14, 1); BOXC = (0.12, 0.20, 0.34, 1)

def r_out(s):
    """Outer radius s metres behind the tip of the rod at the nose."""
    if s < PL:
        return 0.036
    if s < PL + NL:
        u = (s - PL) / NL; return 0.10 + (R - 0.10) * (1 - (1 - u) ** 1.25) ** 0.9
    if s < SA:
        return R
    if s < S_TAPER:
        u = (s - SA) / (S_TAPER - SA); return R + (RA - R) * u
    return RA

def _st():
    return sorted(set([0.0, 0.02, PL - 0.001, PL] + list(PL + np.linspace(0.0, NL, 16)) + [SA, S_TAPER, S_BOX]))

def _body():
    S = Shell(); st = _st(); x = lambda s: L / 2 - s
    S.add(*revolve([(x(0.0), 0.0)] + [(x(s), r_out(s)) for s in st] + [(x(S_BOX), 0.0)], 48), color=GREEN)
    S.add(*revolve([(x(0.0) + 0.001, 0.0), (x(0.0), 0.030), (x(0.06), 0.052), (x(0.16), 0.052), (x(0.19), 0.040)], 16), color=STEEL)       # the head of the rod
    c0 = PL + 0.02; c1 = PL + 0.56                                    # the yellow front of the cone
    S.add(*revolve([(x(s), r_out(s) + 0.002) for s in np.linspace(c0, c1, 8)], 48), color=YELLOW)
    for s in (PL + NL, 3.35, 5.0, SA):                                # the joints between the sections
        S.add(*revolve([(x(s) + 0.035, R + 0.005), (x(s) - 0.035, R + 0.005)], 48), color=GREEN2)
    a8 = np.linspace(0, 2 * np.pi, 8, endpoint=False) + math.pi / 8   # the eight-sided housing of the tail: guidance and the fins' drives
    rings = [np.stack([np.full(8, x(s)), r * np.cos(a8), r * np.sin(a8)], 1) for s, r in ((S_BOX, RA * 0.9), (S_BOX + 0.05, R_BOX / math.cos(math.pi / 8)), (L - 0.06, R_BOX / math.cos(math.pi / 8)), (L, R_BOX * 0.86 / math.cos(math.pi / 8)))]
    S.add(*loft(rings), color=GREEN)
    S.add(*revolve([(x(L) - 0.012, 0.0), (x(L) - 0.012, 0.07), (x(L) + 0.01, 0.07)], 16), color=ALU)
    for sg in (1, -1):                                                # the two fixed wings: flat plates, swept at the front
        pts = [(x(WING_S[0]), sg * (R - 0.03), 0.0), (x(WING_TIP_S[0]), sg * (R + WING_OUT), 0.0), (x(WING_TIP_S[1]), sg * (R + WING_OUT), 0.0), (x(WING_S[1]), sg * (R - 0.03), 0.0)]
        S.add(*plate(pts if sg > 0 else pts[::-1], EZ, 0.045), color=GREEN)
        for az in (math.radians(38), math.radians(-38)):               # raceways along the body, above and below each wing
            c, s_ = math.cos(az), math.sin(az); S.add(*box((x((PL + NL + 0.25 + SA) / 2), sg * (R + 0.012) * c, (R + 0.012) * s_), (SA - PL - NL - 0.35, 0.03, 0.11), rot=[[1, 0, 0], [0, c, -sg * s_], [0, sg * s_, c]]), color=GREEN2)
    for k in range(4):                                                # the hinge blocks of the fins
        a = math.pi / 4 + k * math.pi / 2; S.add(*box((x(S_HINGE), (R_HINGE - 0.02) * math.cos(a), (R_HINGE - 0.02) * math.sin(a)), (0.20, 0.16, 0.16)), color=ALU2)
    return S.mesh("moab_body", sharp=math.radians(38))

def _fin():
    """One lattice fin in its own frame: hinged at the origin, standing out along +Z, its cells open along X."""
    S = Shell(); z0 = 0.06; zc = z0 + FIN_L / 2
    S.add(*box((0, 0, 0.02), (0.14, 0.26, 0.10)), color=ALU2)
    for dy in (-FIN_W / 2, FIN_W / 2):
        S.add(*box((0, dy, zc), (FIN_T, 0.020, FIN_L)), color=ALU)
    for dz in (0.0, FIN_L):
        S.add(*box((0, 0, z0 + dz), (FIN_T, FIN_W, 0.020)), color=ALU)
    for j in range(1, 7):
        S.add(*box((0, -FIN_W / 2 + j * FIN_W / 7, zc), (FIN_T - 0.01, 0.007, FIN_L)), color=ALU)
    for j in range(1, 10):
        S.add(*box((0, 0, z0 + j * FIN_L / 10), (FIN_T - 0.01, FIN_W, 0.007)), color=ALU)
    return S.mesh("moab_fin", sharp=math.radians(40))

def _cutaway():
    """The far half of the body (y > 0, seen from -Y) with the cut face on the plane y = 0: the thin case, the filling, the fuze behind the nose, the guidance in the tail."""
    S = Shell(); st = [s for s in _st() if s >= PL]; a = np.linspace(-math.pi / 2, math.pi / 2, 25); x = lambda s: L / 2 - s
    V = np.array([[x(s), r_out(s) * math.cos(t), r_out(s) * math.sin(t)] for s in st for t in a]); S.add(V, grid_faces(len(st), len(a)), None, GREEN)
    V = np.array([[x(s), 0.0, f * r_out(s)] for s in st for f in (-1.0, 1.0)]); S.add(V, grid_faces(len(st), 2), None, CUTC)                         # the aluminium, seen edge on
    w = 0.028                                                          # drawn 28 mm thick so that it can be seen at all
    st2 = sorted([s for s in st if PL + 0.30 <= s <= SA - 0.05] + [SA - 0.06]); V = np.array([[x(s), -0.003, f * (r_out(s) - w)] for s in st2 for f in (-1.0, 1.0)]); S.add(V, grid_faces(len(st2), 2), None, FILLC)
    S.add(*box((x(PL + 0.95), -0.006, 0.0), (0.80, 0.004, 0.24)), color=BOOST)                                                                       # booster behind the fuze
    S.add(*box((x(PL + 0.38), -0.006, 0.0), (0.34, 0.004, 0.12)), color=FUZEC)                                                                       # fuze
    S.add(*box((x((SA + 0.25 + S_BOX) / 2), -0.006, 0.0), (S_BOX - SA - 0.45, 0.004, 2 * RA - 0.16)), color=(0.20, 0.21, 0.22, 1))                 # the tail section: empty but for wiring
    S.add(*box((x((S_BOX + L) / 2), 0.0, 0.0), (L - S_BOX, 0.004, 2 * R_BOX)), color=CUTC); S.add(*box((x((S_BOX + L) / 2), -0.004, 0.0), (L - S_BOX - 0.10, 0.004, 2 * R_BOX - 0.10)), color=BOXC)      # guidance and fin drives
    S.add(*revolve([(x(0.0), 0.0), (x(0.0), 0.030), (x(0.06), 0.052), (x(0.16), 0.052), (x(0.19), 0.036), (x(PL), 0.036)], 16), color=STEEL)
    return S.mesh("moab_cut", sharp=math.radians(38))

CR_X = (L / 2 - 1.95, L / 2 - 8.05)                                    # the cradle's ends, along the bomb
PLAT_XC = -0.25

def _cradle():
    """Platform and cradle in the bomb's frame (the cargo floor is AXIS_H below the axis)."""
    S = Shell(); zf = -C.AXIS_H; zp = zf + C.PLAT_H; xc = PLAT_XC; x0, x1 = CR_X; n = 9; xs = np.linspace(x0, x1, n)
    S.add(*box((xc, 0, zf + C.PLAT_H / 2), (C.PLAT_L, C.PLAT_W, C.PLAT_H)), color=ALU)
    for sg in (1, -1):
        S.add(*box((xc, sg * (C.PLAT_W / 2 - 0.04), zp + 0.035), (C.PLAT_L, 0.08, 0.07)), color=ALU2)                 # the platform's side rails
        yt = sg * R * math.sin(math.radians(38)); zt = -R * math.cos(math.radians(38)) - 0.05; yb = sg * 0.86; zb = zp + 0.05
        S.add(*box(((x0 + x1) / 2, yt, zt), (x0 - x1 + 0.3, 0.12, 0.10)), color=ALU); S.add(*box(((x0 + x1) / 2, yb, zb), (x0 - x1 + 0.5, 0.14, 0.10)), color=ALU)     # top and bottom beams
        for k in range(n - 1):                                         # struts in a zigzag between them
            a = np.array([xs[k], yt, zt]) if k % 2 == 0 else np.array([xs[k], yb, zb]); b = np.array([xs[k + 1], yb, zb]) if k % 2 == 0 else np.array([xs[k + 1], yt, zt]); d = b - a; ln = np.linalg.norm(d); ex = d / ln
            ey = np.cross(EZ, ex); ey /= np.linalg.norm(ey); ez = np.cross(ex, ey); S.add(*box((a + b) / 2, (ln, 0.09, 0.09), rot=np.stack([ex, ey, ez], 1)), color=ALU)
    for x in xs[::2]:                                                  # cross members
        S.add(*box((x, 0, zp + 0.05), (0.10, 1.80, 0.09)), color=ALU2); S.add(*box((x, 0, -R - 0.09), (0.10, 2 * R * math.sin(math.radians(38)) + 0.1, 0.08)), color=ALU2)
    for x in (x0 - 0.5, (x0 + x1) / 2 + 0.6, x1 + 1.1):                # webbing over the body, down to the platform
        t = np.linspace(-math.radians(112), math.radians(112), 28); ring = [(R + 0.012) * np.array([0, math.sin(q), math.cos(q)]) for q in t]
        ring = [np.array([0, -(C.PLAT_W / 2 - 0.12), zp + 0.05])] + ring + [np.array([0, C.PLAT_W / 2 - 0.12, zp + 0.05])]
        for p, q in zip(ring[:-1], ring[1:]):
            d = q - p; nrm = np.cross(d, EX); nrm /= np.linalg.norm(nrm); S.add(*plate([p + EX * (x - 0.05), q + EX * (x - 0.05), q + EX * (x + 0.05), p + EX * (x + 0.05)], nrm, 0.006), color=WEB)
    return S.mesh("moab_cradle", sharp=math.radians(35))

class Bomb:
    """ob (quaternion) carries the body (or the cut-open half) and the four fins."""
    def __init__(self, col=None, name="MOAB", cut=False):
        col = col or bpy.context.scene.collection; D = bpy.data.meshes; M = bpy.data.materials
        pm = M.get("MoabPaint") or paint_mat("MoabPaint", rough=0.42, bump=0.04)
        self.ob = bpy.data.objects.new(name, None); col.objects.link(self.ob); self.ob.rotation_mode = 'QUATERNION'; self.parts = []
        nm, make = ("moab_cut", _cutaway) if cut else ("moab_body", _body); me = D.get(nm) or make()
        if not me.materials:
            me.materials.append(pm)
        o = bpy.data.objects.new(name + "_" + nm, me); col.objects.link(o); o.parent = self.ob; self.parts.append(o)
        fm = D.get("moab_fin") or _fin()
        if not fm.materials:
            fm.materials.append(M.get("MoabFin") or paint_mat("MoabFin", rough=0.38, metal=0.7, bump=0.03))
        self.fins = []
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2
            if cut and math.cos(a) < 0:                                 # the near pair would hide the cut face
                continue
            f = bpy.data.objects.new(name + "_Fin%d" % k, fm); col.objects.link(f); f.parent = self.ob; f.rotation_mode = 'QUATERNION'
            f.location = (L / 2 - S_HINGE, R_HINGE * math.cos(a), R_HINGE * math.sin(a)); self.fins.append((f, a)); self.parts.append(f)
        self.set_fins(1.0)
    def set_fins(self, open_=1.0, steer=0.0):
        """open_: 0 = folded forward along the tail section (as carried), 1 = standing out; steer: a small turn of each fin about its own length."""
        for f, a in self.fins:
            f.rotation_quaternion = Quaternion((1, 0, 0), a - math.pi / 2) @ Quaternion((0, 1, 0), math.radians(87.0) * (1 - open_)) @ Quaternion((0, 0, 1), steer * math.cos(2 * a))
    def hide(self, v):
        for o in self.parts:
            o.hide_render = v

class Cradle:
    """Platform and cradle; the same frame as the bomb they carry."""
    def __init__(self, col=None, name="Cradle"):
        col = col or bpy.context.scene.collection; M = bpy.data.materials; pm = M.get("CradlePaint") or paint_mat("CradlePaint", rough=0.45, metal=0.6, bump=0.2)
        me = bpy.data.meshes.get("moab_cradle") or _cradle()
        if not me.materials:
            me.materials.append(pm)
        self.ob = bpy.data.objects.new(name, me); col.objects.link(self.ob); self.ob.rotation_mode = 'QUATERNION'
