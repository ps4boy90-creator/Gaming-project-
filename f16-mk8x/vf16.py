"""Lockheed Martin F-16C Fighting Falcon with two 370-gal tanks, wingtip AIM-120s, AIM-9s, and one each of the
Mk 82, Mk 83 and Mk 84 bombs.

Aircraft frame: nose towards +X, left +Y, up +Z.  Geometry is laid out by fuselage station s (metres aft of the tip
of the pitot boom); x = X0 - s.  Published figures (USAF / aerospaceweb / NASA TP): length 15.03 m, span 9.45 m over
the tip launchers (9.14 m theoretical), wing area 27.87 m2, leading-edge sweep 40 deg, trailing edge unswept, no
dihedral, 4 % thick (NACA 64A204), centre-line root chord 4.97 m, tip chord 1.13 m, exposed root at 1.37 m;
stabilator span 5.58 m, 40 deg sweep, 10 deg anhedral; fin 2.57 m exposed height, 47.5 deg sweep; two ventral fins
canted 15 deg.  Mk 82: 2.22 m x 273 mm.  Mk 83: 3.00 m x 357 mm.  Mk 84: 3.28 m x 458 mm.  All three: ogive nose with
nose fuze, conical four-fin tail, olive drab with one yellow band, two lugs.
The blended wing-body (the long strakes running forward to the cockpit and the shoulder they form with the fuselage),
canopy, intake, fin fairing and stores are proportioned from photographs (see README).
"""
import bpy, math, os, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "reaper-hellfire")); sys.path.insert(0, HERE)
from qgeo import *
from util import new_mesh, grid_faces, nodemat

X0 = 7.3
MID = (0.150, 0.165, 0.185, 1); DARK = (0.070, 0.080, 0.096, 1); LIGHT = (0.25, 0.27, 0.29, 1); RADOME = (0.115, 0.125, 0.135, 1); BLACK = (0.012, 0.012, 0.014, 1); STEEL = (0.09, 0.09, 0.10, 1)
OLIVE = (0.075, 0.082, 0.040, 1); YELLOW = (0.70, 0.52, 0.03, 1); WHITE = (0.52, 0.53, 0.54, 1); FORM = (0.42, 0.50, 0.26, 1)
SWEEP = math.tan(math.radians(40.0)); C_ROOT = 4.97; C_TIP = 1.13; HALF = 4.57; LE0 = 5.15; TE = LE0 + C_ROOT
STA2 = 3.99; STA3 = 3.05; STA4 = 1.80; TIP_Y = 4.80

def P(s, y, z):
    return np.array([X0 - s, y, z])

def shade(V):
    """Three greys: darker on the upper forward and centre fuselage, mid grey on wings and tail, light underneath."""
    V = np.asarray(V, float); s = X0 - V[:, 0]; y = np.abs(V[:, 1]); z = V[:, 2]
    c = np.tile(np.array(MID), (len(V), 1))
    c[(z > 0.10) & (s > 2.0) & (s < 9.6) & (y < 1.45)] = DARK
    c[z < -0.06] = LIGHT
    c[s < 2.0] = RADOME
    return c

# central fuselage: s, centre z, half width, height up, depth down, squareness
_FUS = [(0.35, -0.06, 0.012, 0.012, 0.012, 2.0), (0.90, -0.05, 0.17, 0.17, 0.17, 2.0), (1.50, -0.03, 0.325, 0.325, 0.33, 2.0), (2.00, 0.00, 0.42, 0.42, 0.44, 2.1), (2.70, 0.02, 0.50, 0.46, 0.52, 2.2),
        (3.40, 0.02, 0.55, 0.48, 0.58, 2.3), (3.90, 0.02, 0.60, 0.50, 0.60, 2.4), (4.70, 0.02, 0.68, 0.58, 0.60, 2.6), (5.80, 0.02, 0.76, 0.68, 0.60, 2.8), (7.00, 0.02, 0.80, 0.72, 0.62, 2.8),
        (8.50, 0.02, 0.80, 0.74, 0.68, 2.6), (10.0, 0.03, 0.76, 0.72, 0.70, 2.4), (11.5, 0.04, 0.72, 0.69, 0.67, 2.2), (12.8, 0.05, 0.66, 0.64, 0.63, 2.1), (13.9, 0.05, 0.60, 0.59, 0.59, 2.0)]

def _fus_at(s):
    a = np.array(_FUS); return [float(np.interp(s, a[:, 0], a[:, k])) for k in range(1, 6)]

def _fuselage(S):
    ss = 0.35 + 13.55 * np.linspace(0, 1, 84) ** 1.15; m = 40; th = np.linspace(0, 2 * np.pi, m, endpoint=False); rings = []
    for s in ss:
        zc, w, up, dn, e = _fus_at(s); p = 2.0 / e; cs, sn = np.cos(th), np.sin(th)
        rings.append(np.stack([np.full(m, X0 - s), w * np.sign(cs) * np.abs(cs) ** p, zc + np.where(sn > 0, up, dn) * np.sign(sn) * np.abs(sn) ** p], 1))
    V, Q, T = loft(rings); S.add(V, Q, T, shade(V))
    v, f, t = revolve([(0.0, 0.012), (0.36, 0.014)], 6, axis=-EX, origin=P(0, 0, -0.06)); S.add(v, f, t, STEEL)                # pitot boom
    v, f, t = ellipsoid(P(3.55, 0.585, 0.30), (0.32, 0.025, 0.045)); S.add(v, f, t, BLACK)                                    # gun port, left side
    for sg in (1, -1):                                                                                                         # formation-light strips
        v, f, t = box(P(2.75, sg * 0.512, 0.10), (0.42, 0.012, 0.05)); S.add(v, f, t, FORM)
        v, f, t = box(P(11.9, sg * 0.722, 0.22), (0.45, 0.012, 0.05)); S.add(v, f, t, FORM)

_STRAKE_Y = [0.30, 0.50, 0.75, 0.95, 1.15, 1.37, 1.60]; _STRAKE_S = [2.90, 3.25, 4.20, 5.20, 5.95, 6.30, LE0 + SWEEP * 1.60]; _STRAKE_T = [0.36, 0.34, 0.30, 0.25, 0.21, 0.19, 0.175]

def _blend(S):
    """The blended wing-body: the leading-edge strake that runs forward to the cockpit and the thick shoulder it forms."""
    for sg in (1, -1):
        st = []
        for y in np.linspace(0.30, 1.60, 12):
            s = float(np.interp(y, _STRAKE_Y, _STRAKE_S)); c = TE + 0.03 - s; t = float(np.interp(y, _STRAKE_Y, _STRAKE_T))
            st.append((P(s, sg * y, 0.03), c, t / c, (-1, 0, 0), (0, 0, 1)))
        V, Q, T = surface(st, 22); S.add(V, Q, T, shade(V))
        # the shelf beside the engine that carries the stabilator and the speed brakes
        v, f, t = plate([P(10.0, sg * 0.55, 0.0), P(10.0, sg * 1.25, 0.0), P(13.6, sg * 1.12, 0.0), P(14.25, sg * 0.92, 0.0), P(14.25, sg * 0.5, 0.0)], (0, 0, 1), 0.16); S.add(v, f, t, shade(v))

def _intake(S):
    """Chin intake: an oval duct under the forward fuselage, held off it by a boundary-layer diverter, fairing into the belly aft."""
    st = [(3.90, -0.95, 0.50, 0.30), (4.40, -0.95, 0.55, 0.31), (5.60, -0.90, 0.62, 0.30), (7.20, -0.76, 0.66, 0.26), (8.60, -0.63, 0.62, 0.18), (9.60, -0.52, 0.50, 0.08)]
    m = 28; a = np.linspace(0, 2 * np.pi, m, endpoint=False); e = 2.0 / 2.6; cs, sn = np.cos(a), np.sin(a); sx = np.sign(cs) * np.abs(cs) ** e; sz = np.sign(sn) * np.abs(sn) ** e
    V, Q, T = loft([np.stack([np.full(m, X0 - s), w * sx, zc + h * sz], 1) for s, zc, w, h in st], cap0=False); S.add(V, Q, T, np.tile(np.array(LIGHT), (len(V), 1)))
    V, Q, T = loft([np.stack([np.full(m, X0 - s), 0.455 * sx, -0.95 + 0.255 * sz], 1) for s in (3.92, 4.35)], cap0=False); S.add(V, Q, T, BLACK)   # the mouth
    v, f, t = box(P(4.02, 0, -0.615), (0.75, 0.80, 0.022)); S.add(v, f, t, LIGHT)                                              # splitter plate
    v, f, t = box(P(4.9, 0, -0.60), (1.9, 0.26, 0.10)); S.add(v, f, t, LIGHT)                                                  # diverter

def _canopy_rings(scale=1.0, s0=2.55, s1=5.75, n=30):
    a = np.linspace(-0.10, math.pi + 0.10, 17); rings = []
    for s in np.linspace(s0, s1, n):
        u = (s - 2.55) / 3.2; w = (0.50 * math.sin(math.pi * min(u * 1.2, 1.0) ** 0.72) ** 0.55 * (1 - 0.42 * max(u - 0.55, 0) / 0.45) + 0.02) * scale
        h = (0.62 * math.sin(math.pi * min(u, 1.0) ** 0.55) ** 0.85 + 0.01) * scale; sill = 0.43 + 0.17 * u
        rings.append(np.stack([np.full(len(a), X0 - s), w * np.cos(a), sill + h * np.sin(a)], 1))
    return np.array(rings), len(a)

def canopy_mat():
    """Thin gold-tinted transparency with a glossy reflection."""
    m = bpy.data.materials.new("F16Canopy"); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; L = nt.links; N.clear()
    out = N.new("ShaderNodeOutputMaterial"); tr = N.new("ShaderNodeBsdfTransparent"); tr.inputs["Color"].default_value = (0.78, 0.66, 0.46, 1)
    gl = N.new("ShaderNodeBsdfGlossy"); gl.inputs["Roughness"].default_value = 0.02; gl.inputs["Color"].default_value = (1.0, 0.92, 0.75, 1)
    lw = N.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.22; mix = N.new("ShaderNodeMixShader")
    L.new(lw.outputs["Fresnel"], mix.inputs["Fac"]); L.new(tr.outputs[0], mix.inputs[1]); L.new(gl.outputs[0], mix.inputs[2]); L.new(mix.outputs[0], out.inputs["Surface"])
    return m

def _cockpit(S):
    """What shows through the canopy: coaming, ejection seat, pilot, and the canopy's fixed rear frame."""
    for c, sz, colr in ((P(3.05, 0, 0.56), (0.55, 0.62, 0.20), BLACK), (P(4.15, 0, 0.62), (0.16, 0.36, 0.74), (0.05, 0.05, 0.05, 1)), (P(3.95, 0, 0.36), (0.9, 0.60, 0.20), BLACK),
                        (P(3.86, 0, 0.60), (0.26, 0.40, 0.50), (0.10, 0.11, 0.07, 1))):
        S.add(*box(c, sz), color=colr)
    S.add(*ellipsoid(P(3.80, 0, 0.925), (0.130, 0.120, 0.125)), color=(0.20, 0.21, 0.22, 1))                                   # helmet
    S.add(*ellipsoid(P(3.71, 0, 0.905), (0.06, 0.10, 0.07)), color=BLACK)                                                     # visor
    R, na = _canopy_rings(1.012, 4.58, 4.70, 2); S.add(R.reshape(-1, 3), grid_faces(2, na), None, DARK)                       # frame hoop
    R, na = _canopy_rings(1.008, 2.52, 2.62, 2); S.add(R.reshape(-1, 3), grid_faces(2, na), None, DARK)

def _spine(S):
    st = [(5.30, 0.60, 0.36, 0.36), (6.2, 0.70, 0.30, 0.20), (7.5, 0.74, 0.24, 0.12), (9.0, 0.74, 0.20, 0.10), (10.6, 0.72, 0.18, 0.10)]
    m = 14; a = np.linspace(0, 2 * np.pi, m, endpoint=False)
    V, Q, T = loft([np.stack([np.full(m, X0 - s), w * np.cos(a), zc + h * np.sin(a)], 1) for s, zc, w, h in st]); S.add(V, Q, T, shade(V))

def wing_le(y):
    ay = abs(y); return LE0 + SWEEP * ay, C_ROOT + (C_TIP - C_ROOT) * ay / HALF

def _wings(S):
    for sg in (1, -1):
        st = []
        for y in np.linspace(1.50, HALF, 8):
            s, c = wing_le(y); st.append((P(s, sg * y, 0.03 * max(0.0, (2.2 - y) / 0.7)), c, 0.048 if y < 2.2 else 0.042, (-1, 0, 0), (0, 0, 1)))
        V, Q, T = surface(st, 18); S.add(V, Q, T, shade(V))
        v, f, t = box(P(9.95, sg * 4.66, 0.0), (2.9, 0.09, 0.10)); S.add(v, f, t, MID)                                           # tip launcher
        v, f, t = box(P(9.0, sg * 4.60, 0.062), (0.5, 0.05, 0.012)); S.add(v, f, t, FORM)

def _yt(t, b):
    return 5 * t * (0.2969 * math.sqrt(b) - 0.1260 * b - 0.3516 * b ** 2 + 0.2843 * b ** 3 - 0.1036 * b ** 4)

def _seams(S):
    """Hinge lines of the leading-edge flaps, the flaperons and the rudder, as thin dark strips lying on the skin."""
    ink = (0.045, 0.05, 0.06, 1); w = 0.014
    def wp(y, fr, top):
        s, c = wing_le(y); return P(s + fr * c, y, 0.03 * max(0.0, (2.2 - abs(y)) / 0.7) + top * (c * _yt(0.042, fr) + 0.004))
    for sg in (1, -1):
        for top in (1, -1):
            for fr, ya, yb in ((0.13, 1.75, 4.50), (0.78, 1.60, 3.72)):
                a, b = wp(sg * ya, fr, top), wp(sg * yb, fr, top); S.add(*plate([a + EX * w, b + EX * w, b - EX * w, a - EX * w], (0, 0, 1), 0.004), color=ink)
            a, b = wp(sg * 3.72, 0.78, top), wp(sg * 3.72, 0.995, top); S.add(*plate([a + EY * w, b + EY * w, b - EY * w, a - EY * w], (0, 0, 1), 0.004), color=ink)
        k = math.tan(math.radians(47.5)); pts = []
        for z in (1.25, 3.05):
            u = (z - 0.98) / 2.30; c = 2.95 + (0.92 - 2.95) * u; pts.append(P(10.95 + k * (z - 0.98) + 0.70 * c, sg * (c * _yt(0.05, 0.70) + 0.004), z))
        S.add(*plate([pts[0] + EX * w, pts[1] + EX * w, pts[1] - EX * w, pts[0] - EX * w], (0, 1, 0), 0.004), color=ink)

def _tail(S):
    a10 = math.tan(math.radians(10.0))
    for sg in (1, -1):
        d = 1.74; V, Q, T = wing(P(11.95, sg * 1.05, -0.03), 2.45, 0.05, P(11.95 + SWEEP * d, sg * (1.05 + d), -0.03 - a10 * d), 0.58, 0.045, (0, sg * math.sin(math.radians(10)), math.cos(math.radians(10))), n=14, k=4)
        S.add(V, Q, T, shade(V))
        dv = np.array([0, sg * math.sin(math.radians(15)), -math.cos(math.radians(15))]); n_ = np.array([0, math.cos(math.radians(15)), sg * math.sin(math.radians(15))])
        V, Q, T = wing(P(11.6, sg * 0.60, -0.52), 1.25, 0.06, P(11.95, sg * 0.60, -0.52) + dv * 0.70, 0.72, 0.05, n_, n=10, k=3); S.add(V, Q, T, LIGHT)
    z0 = 0.98; V, Q, T = wing(P(10.95, 0, z0), 2.95, 0.055, P(10.95 + math.tan(math.radians(47.5)) * 2.30, 0, z0 + 2.30), 0.92, 0.045, (0, 1, 0), n=14, k=5); S.add(V, Q, T, MID)
    st = [(9.7, 0.74, 0.07, 0.02), (10.6, 0.82, 0.13, 0.12), (11.6, 0.86, 0.16, 0.16), (13.4, 0.86, 0.15, 0.16), (14.6, 0.84, 0.11, 0.13), (14.85, 0.84, 0.05, 0.06)]         # fin root fairing
    m = 14; a = np.linspace(0, 2 * np.pi, m, endpoint=False)
    V, Q, T = loft([np.stack([np.full(m, X0 - s), w * np.cos(a), zc + h * np.sin(a)], 1) for s, zc, w, h in st]); S.add(V, Q, T, MID)
    S.add(*ellipsoid(P(14.35, 0, z0 + 2.30), (0.42, 0.045, 0.06)), color=MID)                                                 # fin tip fairing
    S.add(*box(P(13.55, 0, 2.0), (0.06, 0.075, 0.5)), color=FORM)

def _nozzle():
    S = Shell()
    S.add(*revolve([(0.0, 0.60), (0.30, 0.59), (0.72, 0.52), (1.13, 0.40)], 20, axis=-EX, origin=P(13.9, 0, 0.05)), color=(0.085, 0.075, 0.068, 1))
    S.add(*revolve([(1.13, 0.385), (0.60, 0.44), (0.30, 0.30), (0.28, 0.0)], 20, axis=-EX, origin=P(13.9, 0, 0.05)), color=BLACK)
    return S

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
    for sx in (-0.178, 0.178) if D < 0.4 else (-0.381, 0.381):                       # 14-in lugs; 30-in on the 2,000 lb bomb
        S.add(*box((sx + 0.10 * L, 0, r + 0.018), (0.06, 0.03, 0.045)), color=STEEL)
    return S

MK82 = dict(L=2.22, D=0.273, fin=0.384, name="mk82"); MK83 = dict(L=3.00, D=0.357, fin=0.49, name="mk83"); MK84 = dict(L=3.28, D=0.458, fin=0.64, name="mk84")
BOMBS = {"mk82": MK82, "mk83": MK83, "mk84": MK84}

class Bomb:
    def __init__(self, col, spec, name=None):
        me = bpy.data.meshes.get(spec["name"]) or bomb_shell(spec["L"], spec["D"], spec["fin"]).mesh(spec["name"])
        if not me.materials:
            me.materials.append(bpy.data.materials.get("BombPaint") or paint_mat("BombPaint", rough=0.60))
        self.spec = spec; self.ob = bpy.data.objects.new(name or spec["name"], me); col.objects.link(self.ob); self.ob.rotation_mode = 'QUATERNION'

def store_pos(kind):
    """Centre of each bomb on its station: Mk 82 on station 3 (left), Mk 83 on station 7 (right), Mk 84 on the centre line."""
    spec = BOMBS[kind]
    if kind == "mk84":
        return P(8.05, 0.0, -1.03 - 0.17 - 0.03 - spec["D"] / 2)
    s, c = wing_le(STA3); return P(s + 0.42 * c + 0.12 * spec["L"], (1 if kind == "mk82" else -1) * STA3, -0.075 - 0.26 - 0.03 - spec["D"] / 2)

def _missile(S, o, L, r, fins, colr=WHITE):
    S.add(*revolve([(0.0, 0.0), (0.30 * L / 3.65, r * 0.85), (0.55 * L / 3.65, r), (L - 0.05, r), (L, r * 0.7)], 14, axis=-EX, origin=o), color=colr)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2; er = np.array([0, math.cos(a), math.sin(a)]); n_ = np.cross(EX, er); q = lambda x, hh: o - EX * x + er * hh
        for x0, x1, span in fins:
            S.add(*plate([q(x0, r * 0.9), q(x1, r * 0.9), q(x1, span), q(x0 + 0.6 * (x1 - x0), span)], n_, 0.008), color=colr)

def _stores(S):
    for sg in (1, -1):
        s, c = wing_le(STA3)                                                                                                       # weapon pylon, station 3 / 7
        V, Q, T = wing(P(s + 0.10 * c, sg * STA3, -0.04), 1.9, 0.07, P(s + 0.16 * c, sg * STA3, -0.33), 1.6, 0.07, (0, 1, 0), n=10, k=3, tip_round=False); S.add(V, Q, T, LIGHT)
        s, c = wing_le(STA4)                                                                                                       # tank pylon and 370-gal tank, station 4 / 6
        V, Q, T = wing(P(s + 0.20 * c, sg * STA4, -0.05), 2.1, 0.06, P(s + 0.26 * c, sg * STA4, -0.30), 1.8, 0.06, (0, 1, 0), n=10, k=3, tip_round=False); S.add(V, Q, T, LIGHT)
        pr = [(0.0, 0.0)] + [(1.5 * math.sin(a), 0.335 * (1 - math.cos(a)) ** 0.5 if a < 1.57 else 0.335) for a in np.linspace(0.05, math.pi / 2, 9)] + [(3.6, 0.335), (4.6, 0.20), (5.25, 0.03), (5.26, 0.0)]
        o = P(s - 0.55, sg * STA4, -0.30 - 0.335)
        S.add(*revolve(pr, 24, axis=-EX, origin=o), color=LIGHT)
        for a in (math.pi / 2 + 0.7, math.pi / 2 - 0.7):                                                                           # tank tail fins
            er = np.array([0, math.cos(a), -math.sin(a)]); q = lambda x, hh: o - EX * x + er * hh
            S.add(*plate([q(4.35, 0.22), q(5.1, 0.06), q(5.1, 0.42), q(4.75, 0.42)], np.cross(EX, er), 0.012), color=LIGHT)
        _missile(S, P(8.25, sg * TIP_Y, 0.0), 3.65, 0.089, ((1.55, 2.05, 0.26), (3.20, 3.62, 0.31)))                               # AIM-120 on the tip launcher
        s, c = wing_le(STA2)                                                                                                       # station 2 / 8: launcher rail and AIM-9
        V, Q, T = wing(P(s + 0.15 * c, sg * STA2, -0.03), 0.9, 0.08, P(s + 0.18 * c, sg * STA2, -0.16), 0.8, 0.08, (0, 1, 0), n=8, k=2, tip_round=False); S.add(V, Q, T, LIGHT)
        S.add(*box(P(s + 0.55 * c, sg * STA2, -0.19), (2.4, 0.07, 0.07)), color=LIGHT)
        _missile(S, P(s - 0.35, sg * STA2, -0.29), 2.87, 0.0635, ((0.45, 0.62, 0.19), (2.35, 2.85, 0.31)), colr=(0.42, 0.43, 0.44, 1))
    V, Q, T = wing(P(7.15, 0, -1.00), 1.9, 0.07, P(7.2, 0, -1.20), 1.7, 0.07, (0, 1, 0), n=10, k=2, tip_round=False); S.add(V, Q, T, LIGHT)   # centre-line pylon

# ----------------------------------------------------------------------------- markings
def _marking_images():
    """Low-visibility national insignia and fin lettering, drawn once to PNG files."""
    from PIL import Image, ImageDraw, ImageFont
    d = os.path.join(tempfile.gettempdir(), "f16_markings"); os.makedirs(d, exist_ok=True); g = (40, 46, 56, 235)
    p1 = os.path.join(d, "insignia.png")
    if not os.path.exists(p1):
        im = Image.new("RGBA", (720, 360), (0, 0, 0, 0)); dr = ImageDraw.Draw(im); cx, cy, r = 360, 180, 150
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=g, width=16)
        pts = [(cx + (r * 0.96 if k % 2 == 0 else r * 0.37) * math.sin(math.pi * k / 5), cy - (r * 0.96 if k % 2 == 0 else r * 0.37) * math.cos(math.pi * k / 5)) for k in range(10)]
        dr.polygon(pts, fill=g)
        for x0, x1 in ((20, cx - r + 6), (cx + r - 6, 700)):
            dr.rectangle([x0, cy - 62, x1, cy + 62], outline=g, width=16); dr.line([x0, cy, x1, cy], fill=g, width=14)
        im.save(p1)
    p2 = os.path.join(d, "fin.png")
    if not os.path.exists(p2):
        im = Image.new("RGBA", (800, 400), (0, 0, 0, 0)); dr = ImageDraw.Draw(im); fp = os.path.join(HERE, "..", "grenade-explosion", "assets", "BarlowCondensed-SemiBold.ttf")
        dr.text((40, 30), "AF", font=ImageFont.truetype(fp, 120), fill=g); dr.text((40, 150), "00", font=ImageFont.truetype(fp, 120), fill=g); dr.text((250, 60), "016", font=ImageFont.truetype(fp, 300), fill=g)
        im.save(p2)
    return p1, p2

def _decal(col, root, name, path, corners):
    """A flat marking: corners are four points (lower-left, lower-right, upper-right, upper-left of the picture)."""
    m = bpy.data.materials.get("Decal_" + os.path.basename(path))
    if m is None:
        m, N, L, Pn = nodemat("Decal_" + os.path.basename(path)); tex = N.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(path)
        L.new(tex.outputs["Color"], Pn.inputs["Base Color"]); L.new(tex.outputs["Alpha"], Pn.inputs["Alpha"]); Pn.inputs["Roughness"].default_value = 0.55
    me = new_mesh(name, np.array(corners, float), [np.array([[0, 1, 2, 3]])], uvs=np.array([[0, 0], [1, 0], [1, 1], [0, 1]], float), smooth=False)
    ob = new_obj(name, me, col, m); ob.parent = root; ob.visible_shadow = False
    return ob

def _markings(col, root):
    p1, p2 = _marking_images()
    # upper left wing and lower right wing; bars spanwise, top of the star towards the leading edge
    _decal(col, root, "Mark_WingTop", p1, [P(9.30, 2.55, 0.070), P(9.30, 3.55, 0.070), P(8.80, 3.55, 0.070), P(8.80, 2.55, 0.070)])
    _decal(col, root, "Mark_WingBottom", p1, [P(9.20, -2.80, -0.070), P(9.20, -2.20, -0.070), P(8.90, -2.20, -0.070), P(8.90, -2.80, -0.070)])
    for sg in (1, -1):
        y = sg * 0.80; a, b = (11.55, 10.75) if sg > 0 else (10.75, 11.55)
        _decal(col, root, "Mark_Fus%d" % sg, p1, [P(a, y, 0.05), P(b, y, 0.05), P(b, y, 0.45), P(a, y, 0.45)])
        yf = sg * 0.078; a, b = (12.25, 13.05) if sg > 0 else (13.05, 12.25)
        _decal(col, root, "Mark_Fin%d" % sg, p2, [P(a, yf, 1.45), P(b, yf, 1.45), P(b, yf, 1.85), P(a, yf, 1.85)])

def build(col=None, name="F16"):
    """Returns dict: root, bombs {kind: Bomb hung on its station, parented}, pos {kind: its rest position}."""
    col = col or bpy.context.scene.collection
    root = bpy.data.objects.new(name, None); col.objects.link(root); root.rotation_mode = 'QUATERNION'
    S = Shell(); _fuselage(S); _blend(S); _intake(S); _cockpit(S); _spine(S); _wings(S); _seams(S); _tail(S); _stores(S)
    body = new_obj(name + "_Body", S.mesh("f16_body", sharp=math.radians(32)), col, paint_mat("F16Paint", rough=0.48, bump=0.02)); body.parent = root
    noz = new_obj(name + "_Nozzle", _nozzle().mesh("f16_nozzle", sharp=0.05), col, paint_mat("F16Nozzle", rough=0.42, metal=0.8)); noz.parent = root
    G = Shell(); R, na = _canopy_rings(); G.add(R.reshape(-1, 3), grid_faces(len(R), na), None, (1, 1, 1, 1))
    can = new_obj(name + "_Canopy", G.mesh("f16_canopy", sharp=3.0), col, bpy.data.materials.get("F16Canopy") or canopy_mat()); can.parent = root; can.visible_shadow = False
    try:
        _markings(col, root)
    except Exception as e:                                              # markings are decoration: never let them stop a render
        print("markings skipped:", e)
    bombs = {}; pos = {}
    for k in ("mk82", "mk83", "mk84"):
        b = Bomb(col, BOMBS[k], name + "_" + k); p = store_pos(k); b.ob.parent = root; b.ob.location = p; bombs[k] = b; pos[k] = p
    return dict(root=root, body=body, canopy=can, bombs=bombs, pos=pos)
