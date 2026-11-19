"""Lockheed Martin F-16C Fighting Falcon with two 370-gal tanks, wingtip AIM-120s, one Mk 82 and one Mk 83.

Aircraft frame: nose towards +X, left +Y, up +Z.  Geometry is laid out by fuselage station s (metres aft of the tip
of the pitot boom); x = X0 - s.  Published figures (USAF / aerospaceweb / NASA TP): length 15.03 m, span 9.45 m over
the tip launchers (9.14 m theoretical), wing area 27.87 m2, leading-edge sweep 40 deg, trailing edge unswept, no
dihedral, 4 % thick (NACA 64A204), centre-line root chord 4.97 m, tip chord 1.13 m; stabilator span 5.58 m, 40 deg
sweep, 10 deg anhedral; fin 2.57 m exposed height, 47.5 deg sweep; two ventral fins canted 15 deg.
Mk 82: 2.22 m long, 273 mm diameter.  Mk 83: 3.00 m long, 357 mm diameter.  Both: ogive nose with nose fuze,
conical four-fin tail, olive drab with one yellow band, two lugs 14 in apart.
Everything else is proportioned from photographs (see README).
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "reaper-hellfire")); sys.path.insert(0, HERE)
from qgeo import *
from util import new_mesh, grid_faces

X0 = 7.3
MID = (0.150, 0.165, 0.185, 1); DARK = (0.075, 0.085, 0.100, 1); LIGHT = (0.25, 0.27, 0.29, 1); RADOME = (0.12, 0.13, 0.14, 1); BLACK = (0.012, 0.012, 0.014, 1); STEEL = (0.09, 0.09, 0.10, 1)
OLIVE = (0.075, 0.082, 0.040, 1); YELLOW = (0.70, 0.52, 0.03, 1); WHITE = (0.52, 0.53, 0.54, 1)
SWEEP = math.tan(math.radians(40.0)); C_ROOT = 4.97; C_TIP = 1.13; HALF = 4.57; LE0 = 5.15
STA3 = 3.05; STA4 = 1.80; TIP_Y = 4.80

def P(s, y, z):
    return np.array([X0 - s, y, z])

def shade(V):
    """Two-tone grey: darker on the upper forward and centre fuselage, light underneath, radome grey on the nose."""
    V = np.asarray(V, float); s = X0 - V[:, 0]; y = np.abs(V[:, 1]); z = V[:, 2]
    c = np.tile(np.array(MID), (len(V), 1))
    c[(z > 0.18) & (s > 2.0) & (s < 9.4) & (y < 1.5)] = DARK
    c[z < -0.10] = LIGHT
    c[s < 2.0] = RADOME
    return c

# fuselage stations: s, centre z, half width, height up, depth down, squareness
_FUS = [(0.35, 0.00, 0.012, 0.012, 0.012, 2.0), (0.80, 0.00, 0.15, 0.15, 0.15, 2.0), (1.40, 0.00, 0.31, 0.31, 0.31, 2.0), (2.00, 0.00, 0.43, 0.43, 0.43, 2.1), (2.60, 0.02, 0.51, 0.47, 0.51, 2.2),
        (3.30, 0.02, 0.57, 0.50, 0.56, 2.3), (3.90, 0.02, 0.62, 0.52, 0.56, 2.4), (4.60, 0.02, 0.70, 0.60, 0.56, 2.6), (5.60, 0.02, 0.78, 0.70, 0.58, 2.8), (7.00, 0.02, 0.84, 0.74, 0.62, 2.8),
        (8.50, 0.02, 0.86, 0.76, 0.70, 2.6), (10.0, 0.03, 0.82, 0.74, 0.72, 2.4), (11.5, 0.04, 0.76, 0.70, 0.68, 2.2), (12.8, 0.05, 0.68, 0.65, 0.64, 2.1), (13.9, 0.05, 0.60, 0.59, 0.59, 2.0)]

def _fus_at(s):
    a = np.array(_FUS); return [float(np.interp(s, a[:, 0], a[:, k])) for k in range(1, 6)]

def _fuselage(S):
    ss = 0.35 + 13.55 * np.linspace(0, 1, 76) ** 1.15; m = 36; th = np.linspace(0, 2 * np.pi, m, endpoint=False); rings = []
    for s in ss:
        zc, w, up, dn, e = _fus_at(s); p = 2.0 / e; cs, sn = np.cos(th), np.sin(th)
        rings.append(np.stack([np.full(m, X0 - s), w * np.sign(cs) * np.abs(cs) ** p, zc + np.where(sn > 0, up, dn) * np.sign(sn) * np.abs(sn) ** p], 1))
    V, Q, T = loft(rings); S.add(V, Q, T, shade(V))
    v, f, t = revolve([(0.0, 0.012), (0.36, 0.014)], 6, axis=-EX, origin=P(0, 0, 0)); S.add(v, f, t, STEEL)                 # pitot boom

def _intake(S):
    """Chin intake: an oval duct under the forward fuselage, open at the front, fairing into the belly aft."""
    st = [(3.90, -0.86, 0.50, 0.30), (4.40, -0.87, 0.55, 0.31), (5.60, -0.84, 0.62, 0.30), (7.20, -0.74, 0.66, 0.26), (8.60, -0.62, 0.62, 0.18), (9.60, -0.52, 0.50, 0.08)]
    m = 24; a = np.linspace(0, 2 * np.pi, m, endpoint=False); e = 2.0 / 2.6; cs, sn = np.cos(a), np.sin(a); sx = np.sign(cs) * np.abs(cs) ** e; sz = np.sign(sn) * np.abs(sn) ** e
    V, Q, T = loft([np.stack([np.full(m, X0 - s), w * sx, zc + h * sz], 1) for s, zc, w, h in st], cap0=False); S.add(V, Q, T, np.tile(np.array(LIGHT), (len(V), 1)))
    V, Q, T = loft([np.stack([np.full(m, X0 - s), 0.45 * sx, -0.86 + 0.25 * sz], 1) for s in (3.93, 4.30)], cap0=False); S.add(V, Q, T, BLACK)   # the mouth
    for sy in (1, -1):                                                # the diverter between duct and fuselage
        v, f, t = box(P(5.2, sy * 0.30, -0.55), (2.4, 0.10, 0.10)); S.add(v, f, t, LIGHT)

def _canopy():
    """Frameless bubble canopy, 3.2 m long."""
    G = Shell(); ss = np.linspace(2.55, 5.75, 26); a = np.linspace(-0.12, math.pi + 0.12, 15); rings = []
    for s in ss:
        u = (s - 2.55) / 3.2; w = 0.50 * math.sin(math.pi * min(u * 1.15, 1.0) ** 0.75) ** 0.6 * (1 - 0.35 * max(u - 0.6, 0) / 0.4) + 0.02
        h = 0.56 * math.sin(math.pi * u ** 0.62) ** 0.9 + 0.01; sill = 0.44 + 0.16 * u
        rings.append(np.stack([np.full(len(a), X0 - s), w * np.cos(a), sill + h * np.sin(a)], 1))
    R = np.array(rings); G.add(R.reshape(-1, 3), grid_faces(len(ss), len(a)), None, (0.05, 0.035, 0.015, 1))
    return G

def _spine(S):
    st = [(5.35, 0.62, 0.34, 0.34), (6.2, 0.70, 0.30, 0.20), (7.5, 0.74, 0.24, 0.12), (9.0, 0.74, 0.20, 0.10), (10.8, 0.70, 0.18, 0.10)]
    m = 14; a = np.linspace(0, 2 * np.pi, m, endpoint=False)
    V, Q, T = loft([np.stack([np.full(m, X0 - s), w * np.cos(a), zc + h * np.sin(a)], 1) for s, zc, w, h in st]); S.add(V, Q, T, shade(V))

def wing_le(y):
    ay = abs(y); return LE0 + SWEEP * ay, C_ROOT + (C_TIP - C_ROOT) * ay / HALF

def _wings(S):
    for sg in (1, -1):
        st = []
        for y in np.linspace(0.70, HALF, 8):
            s, c = wing_le(y); st.append((P(s, sg * y, 0.0), c, 0.05 if y < 2 else 0.045, (-1, 0, 0), (0, 0, 1)))
        V, Q, T = surface(st, 16); S.add(V, Q, T, shade(V))
        # leading-edge strake, blending the wing into the forward fuselage, and the shelf that carries the stabilator
        v, f, t = plate([P(3.15, sg * 0.50, 0.02), P(4.3, sg * 0.80, 0.02), P(5.5, sg * 1.02, 0.02), P(6.45, sg * 1.55, 0.02), P(7.4, sg * 1.55, 0.02), P(7.4, sg * 0.5, 0.02)], (0, 0, 1), 0.09); S.add(v, f, t, shade(v))
        v, f, t = plate([P(10.0, sg * 0.55, 0.0), P(10.0, sg * 1.20, 0.0), P(13.5, sg * 1.12, 0.0), P(14.0, sg * 0.95, 0.0), P(14.0, sg * 0.5, 0.0)], (0, 0, 1), 0.14); S.add(v, f, t, shade(v))
        v, f, t = box(P(9.95, sg * 4.66, 0.0), (2.9, 0.09, 0.10)); S.add(v, f, t, MID)                                            # tip launcher

def _tail(S):
    a10 = math.tan(math.radians(10.0))
    for sg in (1, -1):
        d = 1.74; V, Q, T = wing(P(11.95, sg * 1.05, -0.03), 2.45, 0.05, P(11.95 + SWEEP * d, sg * (1.05 + d), -0.03 - a10 * d), 0.58, 0.045, (0, sg * math.sin(math.radians(10)), math.cos(math.radians(10))), n=14, k=4)
        S.add(V, Q, T, shade(V))
        dv = np.array([0, sg * math.sin(math.radians(15)), -math.cos(math.radians(15))]); n_ = np.array([0, math.cos(math.radians(15)), sg * math.sin(math.radians(15))])
        V, Q, T = wing(P(11.6, sg * 0.60, -0.52), 1.25, 0.06, P(11.95, sg * 0.60, -0.52) + dv * 0.70, 0.72, 0.05, n_, n=10, k=3); S.add(V, Q, T, LIGHT)
    V, Q, T = wing(P(10.55, 0, 0.66), 3.35, 0.055, P(10.55 + math.tan(math.radians(47.5)) * 2.57, 0, 0.66 + 2.57), 0.95, 0.045, (0, 1, 0), n=14, k=5); S.add(V, Q, T, MID)
    v, f, t = box(P(12.4, 0, 0.80), (3.0, 0.22, 0.22)); S.add(v, f, t, MID)                                                      # fin root fairing

def _nozzle(S):
    S.add(*revolve([(0.0, 0.60), (0.35, 0.585), (0.75, 0.50), (1.13, 0.37)], 28, axis=-EX, origin=P(13.9, 0, 0.05)), color=(0.06, 0.055, 0.05, 1))
    S.add(*revolve([(1.13, 0.35), (0.55, 0.42), (0.50, 0.0)], 20, axis=-EX, origin=P(13.9, 0, 0.05)), color=BLACK)

def bomb_shell(L, D, fin):
    """Low-drag general-purpose bomb about its centre, nose towards +X: ogive nose with fuze, parallel body, boat-tail,
    conical tail with four fins in an X."""
    S = Shell(); r = D / 2; h = L / 2; nose = 2.3 * D; tail = 0.27 * L
    pr = [(h, 0.0), (h, 0.022), (h - 0.07, 0.030), (h - 0.07, 0.045)]
    pr += [(h - 0.07 - nose * u, 0.045 + (r - 0.045) * math.sin(math.pi / 2 * u) ** 0.85) for u in np.linspace(0, 1, 12)[1:]]
    pr += [(-h + tail + 0.55 * D, r), (-h + tail, r * 0.80), (-h + 0.02, r * 0.42), (-h, 0.0)]
    pr = sorted(pr, key=lambda p: -p[0]); V, Q, T = revolve([(x, rr) for x, rr in pr], 24)
    c = np.tile(np.array(OLIVE), (len(V), 1)); c[V[:, 0] > h - 0.075] = STEEL; S.add(V, Q, T, c)
    xb = h - 0.07 - 0.62 * nose; rb = 0.045 + (r - 0.045) * math.sin(math.pi / 2 * 0.62) ** 0.85
    S.add(*revolve([(xb + 0.035, rb - 0.006), (xb - 0.035, rb + 0.012)], 24), color=YELLOW)                                      # high-explosive band
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2; er = np.array([0, math.cos(a), math.sin(a)]); n_ = np.array([0, -math.sin(a), math.cos(a)])
        q = lambda x, hh: EX * x + er * hh
        S.add(*plate([q(-h + tail * 0.95, r * 0.78), q(-h + tail * 0.55, fin / 2), q(-h, fin / 2), q(-h, r * 0.40)], n_, 0.012), color=OLIVE)
    for sx in (-0.178, 0.178):
        S.add(*box((sx + 0.12 * L, 0, r + 0.018), (0.06, 0.03, 0.045)), color=STEEL)
    return S

MK82 = dict(L=2.22, D=0.273, fin=0.384, name="mk82"); MK83 = dict(L=3.00, D=0.357, fin=0.49, name="mk83")

class Bomb:
    def __init__(self, col, spec, name=None):
        me = bpy.data.meshes.get(spec["name"]) or bomb_shell(spec["L"], spec["D"], spec["fin"]).mesh(spec["name"])
        if not me.materials:
            me.materials.append(bpy.data.materials.get("BombPaint") or paint_mat("BombPaint", rough=0.60))
        self.spec = spec; self.ob = bpy.data.objects.new(name or spec["name"], me); col.objects.link(self.ob); self.ob.rotation_mode = 'QUATERNION'

def store_pos(spec, side):
    """Centre of a bomb hung on station 3 (side +1, left) or 7 (side -1, right)."""
    s, c = wing_le(STA3); return P(s + 0.42 * c + 0.12 * spec["L"], side * STA3, -0.075 - 0.26 - 0.03 - spec["D"] / 2)

def _stores(S):
    for sg in (1, -1):
        s, c = wing_le(STA3)                                                                                                       # weapon pylon, station 3 / 7
        V, Q, T = wing(P(s + 0.10 * c, sg * STA3, -0.06), 1.9, 0.07, P(s + 0.16 * c, sg * STA3, -0.33), 1.6, 0.07, (0, 1, 0), n=10, k=3, tip_round=False); S.add(V, Q, T, LIGHT)
        s, c = wing_le(STA4)                                                                                                       # tank pylon and 370-gal tank, station 4 / 6
        V, Q, T = wing(P(s + 0.20 * c, sg * STA4, -0.08), 2.1, 0.06, P(s + 0.26 * c, sg * STA4, -0.30), 1.8, 0.06, (0, 1, 0), n=10, k=3, tip_round=False); S.add(V, Q, T, LIGHT)
        pr = [(0.0, 0.0)] + [(1.5 * math.sin(a) ** 1.0 * 1.0, 0.335 * (1 - math.cos(a)) ** 0.5 if a < 1.57 else 0.335) for a in np.linspace(0.05, math.pi / 2, 9)] + [(3.6, 0.335), (4.6, 0.20), (5.25, 0.03), (5.26, 0.0)]
        o = P(s - 0.55, sg * STA4, -0.30 - 0.335)
        S.add(*revolve(pr, 24, axis=-EX, origin=o), color=LIGHT)
        for k, a in enumerate((math.pi / 2 + 0.7, math.pi / 2 - 0.7)):                                                             # tank tail fins
            er = np.array([0, math.cos(a), -math.sin(a)]); q = lambda x, hh: o - EX * x + er * hh
            S.add(*plate([q(4.35, 0.22), q(5.1, 0.06), q(5.1, 0.42), q(4.75, 0.42)], np.cross(EX, er), 0.012), color=LIGHT)
        # AIM-120 on the tip launcher
        o = P(8.25, sg * TIP_Y, 0.0)
        S.add(*revolve([(0.0, 0.0), (0.35, 0.075), (0.60, 0.089), (3.60, 0.089), (3.65, 0.06)], 16, axis=-EX, origin=o), color=WHITE)
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2; er = np.array([0, math.cos(a), math.sin(a)]); n_ = np.cross(EX, er); q = lambda x, hh: o - EX * x + er * hh
            S.add(*plate([q(1.55, 0.08), q(2.05, 0.08), q(2.05, 0.26), q(1.90, 0.26)], n_, 0.008), color=WHITE)
            S.add(*plate([q(3.20, 0.08), q(3.62, 0.08), q(3.62, 0.31), q(3.48, 0.31)], n_, 0.008), color=WHITE)

def build(col=None, name="F16"):
    """Returns dict: root, mk82 / mk83 (Bomb objects hung under the wings, parented), p82 / p83 (their rest positions)."""
    col = col or bpy.context.scene.collection
    root = bpy.data.objects.new(name, None); col.objects.link(root); root.rotation_mode = 'QUATERNION'
    S = Shell(); _fuselage(S); _intake(S); _spine(S); _wings(S); _tail(S); _nozzle(S); _stores(S)
    body = new_obj(name + "_Body", S.mesh("f16_body", sharp=math.radians(32)), col, paint_mat("F16Paint", rough=0.48, bump=0.02)); body.parent = root
    can = new_obj(name + "_Canopy", _canopy().mesh("f16_canopy", sharp=3.0), col, glass_mat("F16Canopy", (0.035, 0.028, 0.016), 0.03)); can.parent = root
    b82 = Bomb(col, MK82, name + "_Mk82"); b83 = Bomb(col, MK83, name + "_Mk83"); p82 = store_pos(MK82, 1); p83 = store_pos(MK83, -1)
    for b, p in ((b82, p82), (b83, p83)):
        b.ob.parent = root; b.ob.location = p
    return dict(root=root, body=body, canopy=can, mk82=b82, mk83=b83, p82=p82, p83=p83)
