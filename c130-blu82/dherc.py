"""Lockheed C-130B Hercules as flown by the 463rd Tactical Airlift Wing on the "Commando Vault" drops over South
Vietnam in 1970: Southeast Asia camouflage, rear ramp and cargo door open for the drop.

Aircraft frame: nose towards +X, left +Y, up +Z; z = 0 on the centre line of the fuselage's parallel part.  Geometry is
laid out by station s (metres aft of the tip of the nose), x = X0 - s.
From sources (see README): span 132 ft 7 in, length 97 ft 9 in, height 38 ft 3 in, wing area 1,745 sq ft, tailplane
52 ft 8 in, wheel track 14 ft 3 in, four Allison T56 turboprops driving four-blade propellers 13 ft 6 in across, a
cargo compartment about 10 ft wide and 9 ft high that ends in a ramp and an upward-opening door.  The B has no
underwing tanks.  Section shapes and the outlines of nose, nacelles, sponsons and fin are proportioned from
drawings and photographs.  The landing gear is up; there are no panel lines, aerials or crew.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "reaper-hellfire")); sys.path.insert(0, HERE)
from qgeo import *
from util import new_obj, new_mesh, grid_faces, nodemat, simple_mat

FT = 0.3048
X0 = 13.0                                                            # x of the tip of the nose
SPAN = (132.0 + 7.0 / 12.0) * FT; LENGTH = (97.0 + 9.0 / 12.0) * FT; HEIGHT = (38.0 + 3.0 / 12.0) * FT
GREY = (0.42, 0.44, 0.45, 1); CAMO = (0.2, 0.2, 0.15, 0.0)             # under surfaces; alpha 0: the material paints the three-colour pattern there
BLACK = (0.012, 0.012, 0.013, 1); INSIDE = (0.10, 0.115, 0.10, 1); METAL = (0.30, 0.30, 0.31, 1); TYRE = (0.02, 0.02, 0.022, 1)
WHITE = (0.72, 0.72, 0.70, 1); INS_BLUE = (0.015, 0.03, 0.10, 1); INS_RED = (0.36, 0.03, 0.03, 1); PROPC = (0.035, 0.035, 0.038, 1)
# ---- fuselage: s, centre z, half width, height up, depth down, squareness
R_F = 2.16                                                           # the pressure hull is close to a circle 4.3 m across
_FUS = [(0.12, -0.78, 0.10, 0.10, 0.10, 2.0), (0.5, -0.74, 0.50, 0.50, 0.48, 2.0), (1.1, -0.62, 0.95, 0.98, 0.86, 2.1), (2.0, -0.40, 1.45, 1.52, 1.28, 2.2), (3.2, -0.16, 1.88, 1.95, 1.70, 2.3),
        (4.6, -0.03, 2.10, 2.13, 2.00, 2.4), (5.6, 0.0, R_F, R_F, 2.10, 2.5), (17.4, 0.0, R_F, R_F, 2.10, 2.5),
        (19.4, 0.30, 2.10, 1.90, 1.55, 2.5), (21.6, 0.72, 1.86, 1.55, 1.05, 2.4), (24.0, 1.16, 1.42, 1.20, 0.66, 2.3), (26.4, 1.52, 0.92, 0.90, 0.42, 2.2), (28.6, 1.80, 0.42, 0.56, 0.28, 2.0), (29.72, 1.92, 0.10, 0.20, 0.12, 2.0)]
FLOOR_Z = -1.16                                                      # the cargo floor
HOLD_W = 1.56                                                        # half width of the hold (10 ft 3 in across)
RAMP = (18.25, 21.35); DOOR = (21.35, 25.2)                          # the ramp (hinged at its front) and the cargo door behind it (hinged at its rear)
GROUND_Z = -2.10 - 0.58                                              # the ground when it stands on its wheels (for the height check only)
# ---- wing
INC = math.radians(3.0); DIH = math.radians(2.5)
W_LE = 11.9; W_C0 = 16.0 * FT; W_Z = 2.02; YC = 5.6                  # root leading edge station, centre-section chord, chord-line height, half the centre section's span
W_C1 = 2.20; W_T0 = 0.18; W_T1 = 0.12                                 # chord near the tip, thickness ratios (NACA 64A318 to 64A412)
TIP_Y = SPAN / 2 - 0.55
K_LE = 0.30                                                           # the 30 per cent chord line of the outer panel is straight
ENG_Y = (4.93, 10.06)                                                 # engine centre lines
PROP_R = 13.5 * FT / 2; PROP_S = 9.0                                 # propeller radius; station of the propeller planes
TANK_Y = 7.50                                                         # external tanks, between the engines

def P(s, y, z):
    return np.array([X0 - s, y, z])

def fus(s):
    a = np.array(_FUS); return [float(np.interp(s, a[:, 0], a[:, k])) for k in range(1, 6)]

def _ring(s, th, out=0.0):
    zc, w, up, dn, e = fus(s); p = 2.0 / e; cs, sn = np.cos(th), np.sin(th)
    y = (w + out) * np.sign(cs) * np.abs(cs) ** p; z = zc + (np.where(sn > 0, up, dn) + out) * np.sign(sn) * np.abs(sn) ** p
    return y, z

def side_y(s, z, out=0.015):
    """Half width of the skin (plus `out`) at station s and height z."""
    zc, w, up, dn, e = fus(s); h = up if z >= zc else dn; t = min(abs(z - zc) / h, 0.97); return (w + out) * (1.0 - t ** e) ** (1.0 / e)

def top_z(s):
    zc, w, up, dn, e = fus(s); return zc + up

def belly_z(s, y=0.0):
    """Height of the under skin at station s, y from the centre line."""
    zc, w, up, dn, e = fus(s); t = min(abs(y) / w, 0.98); return zc - dn * (1.0 - t ** e) ** (1.0 / e)

CAMO_SIN = -0.42                                                     # the camouflage comes down the sides to here; below it the light grey

def _opening(s):
    """Half width of the rear opening at station s (0 outside it): it narrows with the fuselage towards the tail."""
    if not (RAMP[0] < s < DOOR[1]):
        return 0.0
    zc, w, up, dn, e = fus(s); return min(HOLD_W, w * 0.86)

def _fuselage(S):
    ss = sorted(set(list(np.linspace(0.12, 29.72, 150)) + [RAMP[0] - 0.02, RAMP[0] + 0.02, DOOR[1] - 0.02, DOOR[1] + 0.02]))
    th0 = np.linspace(0, 2 * np.pi, 96, endpoint=False); rings = []; cols = []
    for s in ss:
        y, z = _ring(s, th0); m = len(th0); zc, w, up, dn, e = fus(s)
        c = np.tile(np.array(GREY), (m, 1)); c[np.sin(th0) > CAMO_SIN] = CAMO
        if s < 1.55:                                                   # the black radome
            c[:] = BLACK
        ho = _opening(s)
        if ho > 0:                                                     # the open rear: the belly skin is pushed up to the roof of the hold; ramp and door cover it when shut
            inb = (np.sin(th0) < 0) & (np.abs(y) < ho); z = np.where(inb, min(zc + up - 0.35, FLOOR_Z + 2.74), z); c[inb] = INSIDE
        rings.append(np.stack([np.full(m, X0 - s), y, z], 1)); cols.append(c)
    V, Q, T = loft(rings); n = len(ss) * len(th0); c = np.tile(np.array(GREY), (len(V), 1)); c[:n] = np.concatenate(cols); S.add(V, Q, T, c)
    # main gear fairings along each side, and the nose-wheel doors as a slight keel
    for sg in (1, -1):
        st = [(9.8, 0.02, 0.05), (10.7, 0.52, 0.62), (11.9, 0.66, 0.80), (15.4, 0.66, 0.80), (17.0, 0.50, 0.62), (18.1, 0.02, 0.05)]; rr = []; a = np.linspace(-math.pi / 2, math.pi / 2, 12)
        for s, out, hh in st:
            yb = side_y(s, -1.55, 0.0) - 0.25; rr.append(np.stack([np.full(len(a), X0 - s), sg * (yb + (out + 0.25) * np.cos(a) ** 0.6), -1.50 + hh * np.sin(a)], 1))
        V, Q, T = loft(rr); S.add(V, Q, T, GREY)
    # the wing's root fairing over the top of the fuselage
    rr = []
    for s, h in ((W_LE - 1.6, 0.02), (W_LE - 0.3, 0.30), (W_LE + 1.0, 0.46), (W_LE + 3.6, 0.46), (W_LE + 5.2, 0.24), (W_LE + 6.6, 0.02)):
        a = np.linspace(0, math.pi, 13); rr.append(np.stack([np.full(len(a), X0 - s), 1.65 * np.cos(a), top_z(s) - 0.35 + (h + 0.35) * np.sin(a) ** 0.8], 1))
    V, Q, T = loft(rr); S.add(V, Q, T, CAMO)

def _glass():
    """Flight-deck glazing: the band of windscreen panes round the nose, the lower windows below them and the frames between."""
    S = Shell(); G = (0.025, 0.035, 0.045, 1)
    def band(s0, s1, a0, a1, n=10, out=0.012):
        ss = np.linspace(s0, s1, 4); aa = np.linspace(math.radians(a0), math.radians(a1), n); V = []
        for s in ss:
            y, z = _ring(s, aa, out); V.append(np.stack([np.full(n, X0 - s), y, z], 1))
        S.add(np.concatenate(V), grid_faces(len(ss), n), None, G)
    for k in range(9):                                                 # nine panes of the upper band
        a0 = 22.0 + k * 15.4; band(1.95, 2.95, a0, a0 + 13.2, 5)
    for sg in (0, 1):                                                  # the lower windows either side of the nose
        for k in range(3):
            a0 = (-34.0 + k * 17.0) if sg == 0 else (214.0 - k * 17.0 - 13.0); band(1.55 + 0.12 * k, 2.30 + 0.16 * k, a0, a0 + 13.0, 4)
        band(3.10, 3.75, 24.0 if sg == 0 else 138.0, 42.0 if sg == 0 else 156.0, 4)      # the side windows behind the windscreen
    return S.mesh("herc_glass", sharp=math.radians(50))

# ---- wing geometry
CD = np.array([-math.cos(INC), 0.0, -math.sin(INC)]); UP0 = np.array([-math.sin(INC), 0.0, math.cos(INC)])

def wing_at(y):
    """Leading-edge point, chord, thickness ratio and 'up' vector of the wing at span position y (either side)."""
    ay = abs(y); sg = 1.0 if y >= 0 else -1.0
    if ay <= YC:
        return P(W_LE, y, W_Z), W_C0, W_T0, UP0
    u = (ay - YC) / (TIP_Y - YC); c = W_C0 + (W_C1 - W_C0) * u
    le = P(W_LE + K_LE * (W_C0 - c), y, W_Z + math.tan(DIH) * (ay - YC)); up = UP0 * math.cos(DIH) + np.array([0, -sg * math.sin(DIH), 0])
    return le, c, W_T0 + (W_T1 - W_T0) * u, up / np.linalg.norm(up)

def _yt(b, t):
    b = np.clip(b, 0.0, 1.0); return 5 * t * (0.2969 * np.sqrt(b) - 0.1260 * b - 0.3516 * b ** 2 + 0.2843 * b ** 3 - 0.1036 * b ** 4)

def wing_surf(y, s, upper=True, out=0.0):
    le, c, t, up = wing_at(y); b = (X0 - s - le[0]) / (c * CD[0]); zc = 0.02 * 4 * b * (1 - b); h = float(_yt(b, t))
    return le + c * b * CD + c * (zc + (h if upper else -h)) * up + (out if upper else -out) * up

def _two_tone(V, rings, n):
    m = 2 * n - 2; c = np.tile(np.array(GREY), (len(V), 1)); j = np.arange(rings * m) % m; c[: rings * m][j < n] = CAMO; return c

def _wings(S):
    n = 22
    for sg in (1, -1):
        st = []
        for y in list(np.linspace(0.0, YC, 4)) + list(np.linspace(YC, TIP_Y, 9)[1:]):
            le, c, t, up = wing_at(sg * y); st.append((le, c, t, CD, up))
        le, c, t, up = wing_at(sg * TIP_Y); d = np.array([0.0, sg * math.cos(DIH), math.sin(DIH)])
        for f, k in ((0.25, 0.92), (0.45, 0.72), (0.55, 0.42)):          # the rounded tip
            st.append((le + d * f + (-CD) * (-c * (1 - k) * 0.45), c * k, t * 0.95, CD, up))
        V, Q, T = surface(st, n, camber=0.02); S.add(V, Q, T, _two_tone(V, len(st), n))

def _nacelle(S, yy):
    """One T56 nacelle: slim, slung under the wing, with the air intake under the spinner and the jet pipe under the wing."""
    le, c, t, up = wing_at(yy); zw = le[2]; s_le = X0 - le[0]; zt = zw - 0.42                        # thrust line
    st = [(PROP_S + 0.10, 0.40, 0.40, 0.62), (PROP_S + 0.55, 0.50, 0.48, 0.80), (PROP_S + 1.5, 0.56, 0.52, 0.84), (s_le - 0.1, 0.58, 0.50, 0.82), (s_le + 0.30 * c, 0.52, 0.34, 0.70),
          (s_le + 0.62 * c, 0.36, 0.12, 0.50), (s_le + 0.86 * c, 0.05, 0.04, 0.10)]
    m = 28; a = np.linspace(0, 2 * np.pi, m, endpoint=False); p = 2.0 / 2.4; cs, sn = np.cos(a), np.sin(a); rings = []; cols = []
    for k, (s, w, hu, hd) in enumerate(st):
        zc = zt - math.sin(INC) * max(s - s_le, 0.0) * 0.5 - (0.10 if k == len(st) - 1 else 0.0)
        z = zc + np.where(sn > 0, hu, hd) * np.sign(sn) * np.abs(sn) ** p; rings.append(np.stack([np.full(m, X0 - s), yy + w * np.sign(cs) * np.abs(cs) ** p, z], 1))
        col = np.tile(np.array(GREY), (m, 1)); col[sn > -0.2] = CAMO; cols.append(col)
    V, Q, T = loft(rings); col = np.tile(np.array(GREY), (len(V), 1)); col[: len(st) * m] = np.concatenate(cols); S.add(V, Q, T, col)
    S.add(*box(P(PROP_S + 0.12, yy, zt - 0.47), (0.08, 0.50, 0.26)), color=(0.004, 0.004, 0.004, 1))               # the intake's mouth
    S.add(*revolve([(0.0, 0.17), (0.5, 0.19)], 14, axis=-EX, origin=P(s_le + 0.50 * c, yy, zt - 0.36)), color=(0.05, 0.045, 0.04, 1))     # jet pipe

def _tank(S, yy):
    """A 1,360 US gallon external tank on its pylon under the wing, between the engines."""
    le, c, t, up = wing_at(yy); s0 = X0 - le[0] - 1.9; L_ = 7.3; R_ = 0.56; zt = le[2] - 1.05
    prof = [(0.0, 0.0), (0.25, 0.26), (0.8, 0.46), (1.8, R_), (4.6, R_), (6.0, 0.40), (7.0, 0.16), (L_, 0.0)]
    S.add(*revolve([(-x, r) for x, r in prof][::-1], 20, axis=EX, origin=P(s0, yy, zt)), color=GREY)
    S.add(*box(P(s0 + 3.4, yy, zt + 0.62), (2.6, 0.12, 0.50)), color=GREY)

def _spinner_prop():
    """One propeller in its own frame: hub at the origin, turning about X.  Four broad blades, 13 ft 6 in across."""
    S = Shell(); S.add(*revolve([(0.62, 0.0), (0.56, 0.10), (0.40, 0.24), (0.16, 0.35), (-0.06, 0.40), (-0.12, 0.40)], 24), color=BLACK)
    rr = np.linspace(0.36, PROP_R, 9)
    for k in range(4):
        a = 2 * math.pi * k / 4; er = np.array([0, math.cos(a), math.sin(a)]); et = np.array([0, -math.sin(a), math.cos(a)])
        for r0, r1 in zip(rr[:-1], rr[1:]):
            pts = []
            for r, sgn in ((r0, -1), (r1, -1), (r1, 1), (r0, 1)):
                u = (r - 0.36) / (PROP_R - 0.36); ch = 0.20 + 0.34 * math.sin(math.pi * min(u * 1.05 + 0.12, 1.0)) ** 0.6 * (1.0 if u < 0.95 else 0.85); beta = math.radians(64.0 - 40.0 * u)
                pts.append(er * r + sgn * ch / 2 * (et * math.cos(beta) + EX * math.sin(beta)))
            nrm = np.cross(pts[1] - pts[0], pts[3] - pts[0]); S.add(*plate(pts, nrm, 0.05 * (1.2 - 0.8 * (r0 - 0.3) / PROP_R)), color=PROPC)
    return S.mesh("herc_prop", sharp=math.radians(40))

# ---- tail
T_S = 25.3; T_C0 = 4.0; T_C1 = 1.9; T_SPAN = (52.0 + 8.0 / 12.0) * FT; T_Z = 2.42     # tailplane: root leading edge station, chords, span, height
F_S = 23.0; F_C0 = 6.3; F_C1 = 2.5; F_TOP = HEIGHT + GROUND_Z                        # fin: root leading edge station, root and tip chords, height of its top

def fin_at(z):
    """Leading-edge station and chord of the fin at height z."""
    z0 = 2.25; u = min(max((z - z0) / (F_TOP - z0), 0.0), 1.0); c = F_C0 + (F_C1 - F_C0) * u; return F_S + (F_C0 - c) * 0.97, c                # nearly all the taper is on the leading edge: the rudder's edge stands upright

def _tail(S):
    n = 16
    for sg in (1, -1):
        st = [(P(T_S + 0.30 * (T_C0 - c), sg * y, T_Z), c, 0.11, (-1, 0, 0), (0, 0, 1)) for y, c in ((yy, T_C0 + (T_C1 - T_C0) * yy / (T_SPAN / 2)) for yy in np.linspace(0.0, T_SPAN / 2, 6))]
        V, Q, T = surface(st, n); S.add(V, Q, T, _two_tone(V, len(st), n))
    st = []
    for z in np.linspace(2.0, F_TOP, 9):
        sle, c = fin_at(z); st.append((P(sle, 0.0, z), c, 0.10, (-1, 0, 0), (0, 1, 0)))
    V, Q, T = surface(st, n); S.add(V, Q, T, CAMO)
    pts = [P(F_S - 4.6, 0, top_z(F_S - 4.6) - 0.05), P(F_S + 0.6, 0, 3.55), P(F_S + 1.8, 0, 2.2), P(F_S - 4.0, 0, 2.0)]                      # the dorsal fillet ahead of the fin
    S.add(*plate(pts, EY, 0.12), color=CAMO)

def _disc(S, pt, radii, colors, n=40):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    for k, (r, col) in enumerate(zip(radii, colors)):
        r0 = radii[k + 1] if k + 1 < len(radii) else 0.0; rs = np.linspace(r0, r, 4)
        V = np.array([pt(rr * math.cos(t), rr * math.sin(t)) for t in a for rr in rs]); S.add(V, grid_faces(n, 4, wrap_u=True), None, col)

def _star(S, pt, R_):
    """The national insignia on a surface: blue disc, white star, white bars with a red stripe, blue surround.  pt(u, v) maps metres."""
    _disc(S, pt, [R_ * 1.0], [INS_BLUE], n=36)
    for sg in (1, -1):                                                 # bars: R long, R/2 high, with a red stripe a sixth of the star's diameter
        for (v0, v1, col, o) in ((-R_ * 0.5 - 0.04, R_ * 0.5 + 0.04, INS_BLUE, 0.0005), (-R_ * 0.5, R_ * 0.5, WHITE, 0.001), (-R_ / 6.0, R_ / 6.0, INS_RED, 0.0015)):
            u0, u1 = (R_ * 0.96, R_ * 2.0 + (0.04 if col is INS_BLUE else 0.0)); V = [pt(sg * u0, v0, o), pt(sg * u1, v0, o), pt(sg * u1, v1, o), pt(sg * u0, v1, o)]; S.add(np.array(V), np.array([[0, 1, 2, 3]]), None, col)
    a = [math.pi / 2 + k * 2 * math.pi / 10 for k in range(10)]; rr = [R_ * 0.96 if k % 2 == 0 else R_ * 0.96 * 0.382 for k in range(10)]
    V = [pt(0.0, 0.0, 0.002)] + [pt(r * math.cos(t), r * math.sin(t), 0.002) for r, t in zip(rr, a)]
    S.add(np.array(V), None, np.array([[0, 1 + k, 1 + (k + 1) % 10] for k in range(10)]), WHITE)

def _markings(S):
    for sg in (1, -1):                                                 # fuselage sides, aft of the wing
        s0 = 20.0; z0 = 0.80; R_ = 0.26
        _star(S, lambda u, v, o=0.0: np.array([X0 - s0 - sg * u, sg * (side_y(s0 + sg * u, z0 + v) + o), z0 + v]), R_)
    yc = SPAN / 2 - 4.6                                                # above the left wing and below the right
    le, c, t, up = wing_at(yc); sc_ = X0 - (le + c * 0.45 * CD)[0]; _star(S, lambda u, v, o=0.0: wing_surf(yc + u, sc_ - v, True, 0.012 + o), 0.40)
    le, c, t, up = wing_at(-yc); _star(S, lambda u, v, o=0.0: wing_surf(-yc + u, sc_ + v, False, 0.012 + o), 0.40)

def _text(col, root, pm, txt, size, s_c, z_c, sg, color, on_fin=False):
    """Lettering as a mesh laid on the fuselage side or the fin."""
    import bmesh
    cu = bpy.data.curves.new("txt", 'FONT'); cu.body = txt; cu.size = size; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.space_character = 1.1
    tmp = bpy.data.objects.new("txt_tmp", cu); col.objects.link(tmp); bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get())); bpy.data.objects.remove(tmp, do_unlink=True); bpy.data.curves.remove(cu)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.triangulate(bm, faces=bm.faces[:])
    for _ in range(2):
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    bm.to_mesh(me); bm.free()
    co = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3); out = np.zeros_like(co)
    for i, (u, v, _) in enumerate(co):
        sv = s_c + sg * u; zv = z_c + v
        if on_fin:
            sle, c = fin_at(zv); b = (sv - sle) / c; out[i] = (X0 - sv, sg * (float(_yt(b, 0.10)) * c + 0.012), zv)
        else:
            out[i] = (X0 - sv, sg * side_y(sv, zv), zv)
    me.vertices.foreach_set("co", out.ravel()); me.update()
    at = me.attributes.new("col", 'FLOAT_COLOR', 'POINT'); at.data.foreach_set("color", np.tile(np.array(color, np.float32), len(me.vertices)))
    me.materials.append(pm); o = bpy.data.objects.new("Text", me); col.objects.link(o); o.parent = root; return o

def _ramp():
    """The ramp in its own frame: hinge line along Y at the origin (its front edge, at floor level); shut, it follows the belly."""
    S = Shell(); ss = np.linspace(RAMP[0] + 0.02, RAMP[1] - 0.02, 12); rows_o = []; rows_i = []
    for s in ss:
        ho = _opening(s) - 0.01; ys = np.linspace(-ho, ho, 9); zo = np.array([belly_z(s, y) for y in ys]) - 0.004
        rows_o.append(np.stack([np.full(9, RAMP[0] - s), ys, zo - FLOOR_Z], 1)); zi = FLOOR_Z + (s - RAMP[0]) / (RAMP[1] - RAMP[0]) * (belly_z(RAMP[1]) + 0.10 - FLOOR_Z)
        rows_i.append(np.stack([np.full(9, RAMP[0] - s), ys, np.maximum(zo + 0.08, zi) - FLOOR_Z], 1))
    S.add(np.concatenate(rows_o), grid_faces(len(ss), 9), None, GREY); S.add(np.concatenate(rows_i), grid_faces(len(ss), 9), None, INSIDE)
    return S.mesh("herc_ramp", sharp=3.0)

def _door():
    """The cargo door in its own frame: hinge line along Y at the origin (its rear edge); shut, it follows the belly."""
    S = Shell(); ss = np.linspace(DOOR[0] + 0.02, DOOR[1] - 0.02, 12); rows_o = []; rows_i = []; zh = belly_z(DOOR[1])
    for s in ss:
        ho = _opening(s) - 0.01; ys = np.linspace(-ho, ho, 9); zo = np.array([belly_z(s, y) for y in ys]) - 0.004
        rows_o.append(np.stack([np.full(9, DOOR[1] - s), ys, zo - zh], 1)); rows_i.append(rows_o[-1] + np.array([0, 0, 0.07]))
    S.add(np.concatenate(rows_o), grid_faces(len(ss), 9), None, GREY); S.add(np.concatenate(rows_i), grid_faces(len(ss), 9), None, INSIDE)
    return S.mesh("herc_door", sharp=3.0)

def herc_mat(name="HercPaint"):
    """Matt paint: colours from the 'col' attribute; where its alpha is 0, the Southeast Asia pattern of tan and two greens."""
    m, N, L, Pn = nodemat(name); a = N.new("ShaderNodeAttribute"); a.attribute_name = "col"; tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.085, 0.11, 0.05); L.new(tc.outputs["Object"], mp.inputs["Vector"])
    n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 1.0; n.inputs["Detail"].default_value = 0.5; n.inputs["Distortion"].default_value = 1.1; L.new(mp.outputs[0], n.inputs["Vector"])
    s1 = N.new("ShaderNodeMath"); s1.operation = 'GREATER_THAN'; s1.inputs[1].default_value = 0.56; L.new(n.outputs["Fac"], s1.inputs[0])
    s2 = N.new("ShaderNodeMath"); s2.operation = 'GREATER_THAN'; s2.inputs[1].default_value = 0.44; L.new(n.outputs["Fac"], s2.inputs[0])
    c1 = N.new("ShaderNodeMixRGB"); c1.inputs[1].default_value = (0.040, 0.060, 0.030, 1); c1.inputs[2].default_value = (0.095, 0.115, 0.050, 1); L.new(s2.outputs[0], c1.inputs[0])      # dark green 34079, green 34102
    c2 = N.new("ShaderNodeMixRGB"); c2.inputs[2].default_value = (0.30, 0.215, 0.115, 1); L.new(s1.outputs[0], c2.inputs[0]); L.new(c1.outputs[0], c2.inputs[1])                             # tan 30219
    up = N.new("ShaderNodeMath"); up.operation = 'LESS_THAN'; up.inputs[1].default_value = 0.5; L.new(a.outputs["Alpha"], up.inputs[0])
    mix = N.new("ShaderNodeMixRGB"); L.new(up.outputs[0], mix.inputs[0]); L.new(a.outputs["Color"], mix.inputs[1]); L.new(c2.outputs[0], mix.inputs[2])
    f = N.new("ShaderNodeTexNoise"); f.inputs["Scale"].default_value = 2.0; f.inputs["Detail"].default_value = 5; L.new(tc.outputs["Object"], f.inputs["Vector"])
    w = N.new("ShaderNodeMixRGB"); w.blend_type = 'MULTIPLY'; w.inputs[0].default_value = 0.14; L.new(mix.outputs[0], w.inputs[1]); L.new(f.outputs["Color"], w.inputs[2]); L.new(w.outputs[0], Pn.inputs["Base Color"])
    Pn.inputs["Roughness"].default_value = 0.60
    return m

class Hercules:
    def __init__(self, col=None, name="Herc", serial="969", code="QB", tanks=False):
        col = col or bpy.context.scene.collection; M = bpy.data.materials
        self.root = bpy.data.objects.new(name, None); col.objects.link(self.root); self.root.rotation_mode = 'QUATERNION'
        pm = M.get("HercPaint") or herc_mat()
        S = Shell(); _fuselage(S); _wings(S); _tail(S)
        for sg in (1, -1):
            for yy in ENG_Y:
                _nacelle(S, sg * yy)
            if tanks:                                                  # the later C-130E's external tanks
                _tank(S, sg * TANK_Y)
        _markings(S)
        self.body = new_obj(name + "_Body", S.mesh("herc_body", sharp=math.radians(34)), col, pm); self.body.parent = self.root
        self.glass = new_obj(name + "_Glass", bpy.data.meshes.get("herc_glass") or _glass(), col, M.get("HercGlass") or glass_mat("HercGlass", (0.03, 0.045, 0.055))); self.glass.parent = self.root
        self.texts = []
        for sg in (1, -1):                                             # tail code, "USAF" and the serial on the fin
            self.texts.append(_text(col, self.root, pm, code, 1.10, F_S + 4.4, 5.3, sg, WHITE, on_fin=True))
            self.texts.append(_text(col, self.root, pm, serial, 0.42, F_S + 4.5, 4.45, sg, WHITE, on_fin=True))
        self.props = []
        for sg in (1, -1):
            for k in (0, 1):
                le, c, t, up = wing_at(sg * ENG_Y[k]); o = new_obj(name + "_Prop%+d%d" % (sg, k), bpy.data.meshes.get("herc_prop") or _spinner_prop(), col, pm); o.parent = self.root
                o.location = tuple(P(PROP_S, sg * ENG_Y[k], le[2] - 0.42)); o.rotation_mode = 'XYZ'; self.props.append((o, 0.7 * (2 * k + (sg > 0))))
        self.ramp = new_obj(name + "_Ramp", bpy.data.meshes.get("herc_ramp") or _ramp(), col, pm); self.ramp.parent = self.root; self.ramp.location = (X0 - RAMP[0], 0.0, FLOOR_Z)
        self.door = new_obj(name + "_Door", bpy.data.meshes.get("herc_door") or _door(), col, pm); self.door.parent = self.root; self.door.location = (X0 - DOOR[1], 0.0, belly_z(DOOR[1]))
        self.ramp_shut = math.atan2(belly_z(RAMP[1]) - FLOOR_Z, RAMP[1] - RAMP[0])        # how far the shut ramp slopes up from the floor
        self.set(0.0)

    def set(self, open_=None):
        """open_: 0 shut .. 1 open for an airdrop (the ramp level with the floor, the door swung up into the roof)."""
        if open_ is not None:
            self.ramp.rotation_euler = (0.0, -self.ramp_shut * open_, 0.0)
            self.door.rotation_euler = (0.0, -math.radians(58.0) * open_, 0.0)

    def spin_props(self, sc, t, dt, mb=True, rpm=1020.0):
        """Turn the four propellers (they run at a constant 1,020 rpm); with motion blur, linear keys either side of the frame."""
        F = sc.frame_current; w = rpm / 60.0 * 2 * math.pi
        for o, ph in self.props:
            o.animation_data_clear()
            if mb:
                for k in (-1, 0, 1):
                    o.rotation_euler = (ph + w * (t + k * dt), 0, 0); o.keyframe_insert("rotation_euler", frame=F + k)
                act = o.animation_data.action
                try:
                    fcs = list(act.fcurves)
                except AttributeError:
                    fcs = [fc for layer in act.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]
                for fc in fcs:
                    for kp in fc.keyframe_points:
                        kp.interpolation = 'LINEAR'
            o.rotation_euler = (ph + w * t, 0, 0)
