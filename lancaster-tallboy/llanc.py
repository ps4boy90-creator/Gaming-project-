"""Avro Lancaster B.I / B.III as flown with Tallboys by Nos. 617 and 9 Squadrons in 1944: bulged bomb doors, one
bomb in the bay.

Aircraft frame: nose towards +X, left +Y, up +Z; geometry is laid out by station s (metres aft of the front of the
nose), x = X0 - s.
From sources (see README): span 102 ft (31.09 m), length 69 ft 6 in (21.18 m), wing area 1,297 sq ft, a flat
centre section with outer panels at 7 degrees of dihedral, four Merlins driving three-blade propellers 13 ft across,
the main wheels 23 ft 9 in apart under the inner nacelles, a tailplane 33 ft across with two oval fins at its ends,
a bomb bay 33 ft long; nose, mid-upper and tail turrets; Dark Green and Dark Earth upper surfaces over Night, with
red squadron codes, Type C1 roundels on the fuselage and Type B above the wings.
Section shapes, the outline of nose, canopy, nacelles and fins, the wing's chords and the places of the turrets are
proportioned from drawings and photographs.  The landing gear is up (the tail wheel does not retract); there are no
panel lines, aerials or crew.

With LANC_BOMB=grandslam this is the B.I (Special) of 1945 that carried the 22,000 lb Grand Slam: no bomb doors (the
opening is faired at its ends and the bomb hangs partly below the belly), no nose or mid-upper turret.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "reaper-hellfire")); sys.path.insert(0, HERE)
from qgeo import *
from util import new_obj, new_mesh, grid_faces, nodemat, simple_mat
import lconst as C, lbomb

X0 = 7.6
FT = 0.3048
SPECIAL = C.BOMB == "grandslam"                                      # the B.I (Special)
SPAN = 102.0 * FT; LENGTH = 69.5 * FT
NIGHT = (0.012, 0.012, 0.013, 1); CAMO = (0.09, 0.10, 0.07, 0.0)       # alpha 0: the material paints the disruptive pattern there
INSIDE = (0.10, 0.13, 0.10, 1); METAL = (0.11, 0.105, 0.10, 1); EXH = (0.05, 0.035, 0.03, 1); TYRE = (0.02, 0.02, 0.022, 1); YELLOW = (0.62, 0.45, 0.03, 1)
R_RED = (0.33, 0.035, 0.03, 1); R_BLUE = (0.022, 0.035, 0.11, 1); R_WHITE = (0.60, 0.60, 0.57, 1); R_YEL = (0.62, 0.47, 0.05, 1); CODE = (0.30, 0.045, 0.04, 1)
# ---- fuselage: s, centre z, half width, height up, depth down, squareness
_FUS = [(0.55, -0.20, 0.50, 0.62, 0.62, 2.2), (1.2, -0.12, 0.74, 0.86, 0.90, 2.4), (2.3, -0.04, 0.85, 1.00, 1.14, 2.7), (3.6, 0.0, 0.875, 1.12, 1.26, 3.0), (9.0, 0.0, 0.875, 1.12, 1.26, 3.0),
        (12.4, 0.02, 0.86, 1.06, 1.18, 3.0), (15.0, 0.12, 0.76, 0.94, 0.98, 2.8), (17.8, 0.26, 0.64, 0.80, 0.76, 2.6), (19.8, 0.36, 0.54, 0.70, 0.62, 2.5), (20.75, 0.40, 0.48, 0.62, 0.56, 2.4)]
STORE_S = 8.60                                                       # station of the middle of the bomb's length
BAY = (2.95, 2.95 + 33.0 * FT); BAY_W = 0.80; BULGE = 0.14; BAY_ROOF = -0.22       # the 33 ft bomb bay; how far the bulged doors stand below the normal belly
if SPECIAL:                                                          # no doors: the opening is closed in ahead of and behind the bomb
    BAY = (STORE_S - C.TB_L / 2 - 0.40, STORE_S + C.TB_L / 2 + 0.22); BULGE = 0.0
STORE = None                                                         # filled in below (aircraft frame)
# ---- wing
INC = math.radians(4.0); DIH = math.radians(7.0)
W_LE = 5.60; W_C0 = 16.0 * FT; W_Z = 0.20; YC = 14.0 * FT             # root leading edge station, centre-section chord, chord-line height, half the centre section's span
W_C1 = 2.81; W_T0 = 0.18; W_T1 = 0.11                                 # chord at the wing-tip joint (9 ft 2 9/16 in), thickness ratios (NACA 23018 to 23012)
ENG_Y = (23.75 * FT / 2, 7.55)                                        # inner engines over the main wheels (track 23 ft 9 in), outer engines
PROP_R = 13.0 * FT / 2
PROP_S = (3.20, 3.52)                                                 # propeller planes, inner and outer

def P(s, y, z):
    return np.array([X0 - s, y, z])

def fus(s):
    a = np.array(_FUS); return [float(np.interp(s, a[:, 0], a[:, k])) for k in range(1, 6)]

def _bulge(s):
    u = (s - BAY[0]) / (BAY[1] - BAY[0])
    return BULGE * (min(max(u / 0.10, 0.0), 1.0) * min(max((1.0 - u) / 0.14, 0.0), 1.0)) ** 0.8 if 0.0 < u < 1.0 else 0.0

def _ring(s, th, out=0.0):
    zc, w, up, dn, e = fus(s); p = 2.0 / e; cs, sn = np.cos(th), np.sin(th); dn = dn + _bulge(s)
    y = (w + out) * np.sign(cs) * np.abs(cs) ** p; z = zc + (np.where(sn > 0, up, dn) + out) * np.sign(sn) * np.abs(sn) ** p
    return y, z

def fus_pt(s, ang, out=0.0):
    y, z = _ring(s, np.array([ang]), out); return np.array([X0 - s, float(y[0]), float(z[0])])

def _bay_angle(s):
    """The angle (below the horizontal) at which the belly skin is BAY_W from the centre line."""
    zc, w, up, dn, e = fus(s); return math.acos(min((BAY_W / w) ** (e / 2.0), 1.0))

CAMO_SIN = 0.50                                                      # the upper camouflage comes this far down the sides

def _fuselage(S):
    ss = sorted(set(list(np.linspace(0.55, 20.75, 96)) + [BAY[0] - 0.015, BAY[0] + 0.015, BAY[1] - 0.015, BAY[1] + 0.015]))
    a0 = _bay_angle(6.0); base = [t for t in np.linspace(0, 2 * np.pi, 72, endpoint=False) if not any(abs((t - c + math.pi) % (2 * math.pi) - math.pi) < 0.07 for c in (2 * math.pi - a0, math.pi + a0))]
    rings = []; cols = []; e = 0.004
    for s in ss:
        ab = _bay_angle(min(max(s, 3.6), 12.0)); th = np.array(sorted(base + [2 * math.pi - ab - e, 2 * math.pi - ab + e, math.pi + ab - e, math.pi + ab + e])); y, z = _ring(s, th); m = len(th)
        zc, w, up, dn, e_ = fus(s); c = np.tile(np.array(NIGHT), (m, 1)); c[np.sin(th) > CAMO_SIN] = CAMO
        if BAY[0] < s < BAY[1]:                                        # the open bay is a recess pushed up into the belly; the doors cover it when shut
            inb = (np.sin(th) < 0) & (np.abs(y) < BAY_W - 1e-4); z = np.where(inb, zc + BAY_ROOF, z); c[inb] = INSIDE
        rings.append(np.stack([np.full(m, X0 - s), y, z], 1)); cols.append(c)
    V, Q, T = loft(rings); n = len(ss) * len(rings[0]); c = np.tile(np.array(NIGHT), (len(V), 1)); c[:n] = np.concatenate(cols); S.add(V, Q, T, c)
    # frames of the canopy, the astrodome's ring and the turret rings (the glass itself is a separate object)
    for s in (2.52, 3.05, 3.65, 4.25, 4.85):
        V, Q, T = loft([_canopy_ring(s + d, 0.014) for d in (-0.022, 0.022)], cap0=False, cap1=False); S.add(V, Q, T, CAMO)
    for sg in (-1, 0, 1):
        pts = [_canopy_pt(s, sg * 0.62, 0.014) for s in np.linspace(2.52, 5.6, 14)]
        for a, b in zip(pts[:-1], pts[1:]):
            d = b - a; L_ = np.linalg.norm(d); ex = d / L_; ey = np.array([0, 1.0, 0]); ez = np.cross(ex, ey); S.add(*box((a + b) / 2, (L_, 0.04, 0.02), rot=np.stack([ex, ey, ez], 1)), color=CAMO)
    if SPECIAL:                                                        # the nose turret's place is faired over; there is no mid-upper turret
        S.add(*ellipsoid(P(0.66, 0, -0.20 + 0.40), (0.50, 0.44, 0.42), 20, 10), color=CAMO)
    else:
        S.add(*revolve([(0.0, 0.50), (0.16, 0.47)], 28, axis=EZ, origin=P(MID_S, 0, _top(MID_S) - 0.06)), color=CAMO)                 # fairing round the mid-upper turret
    for sg in (1, -1):                                                 # nose guns (FN5: two .303s), tail guns (FN20: four), mid-upper (FN50: two, trained aft)
        if not SPECIAL:
            S.add(*revolve([(0.0, 0.016), (0.62, 0.013)], 8, axis=EX, origin=P(0.50, sg * 0.10, -0.20 + 0.36)), color=METAL)
            S.add(*revolve([(0.0, 0.016), (0.60, 0.013)], 8, axis=-EX + 0.25 * EZ, origin=P(MID_S + 0.25, sg * 0.10, _top(MID_S) + 0.24)), color=METAL)
        for dz in (-0.07, 0.11):
            S.add(*revolve([(0.0, 0.016), (0.66, 0.013)], 8, axis=-EX, origin=P(21.02, sg * 0.14, 0.40 + dz)), color=METAL)
    zt = fus(19.3)[0] - fus(19.3)[3]                                   # the fixed tail wheel
    S.add(*box(P(19.3, 0, zt - 0.20), (0.10, 0.08, 0.50)), color=METAL); S.add(*revolve([(-0.07, 0.0), (-0.07, 0.17), (-0.03, 0.21), (0.03, 0.21), (0.07, 0.17), (0.07, 0.0)], 18, axis=EY, origin=P(19.42, 0, zt - 0.46), side=EX), color=TYRE)

def _top(s):
    zc, w, up, dn, e = fus(s); return zc + up

MID_S = 12.55                                                        # the mid-upper turret

def _canopy_h(s):
    """Height of the cockpit canopy above the fuselage top: a long greenhouse, highest over the pilot."""
    return 0.62 * (min(max((s - 2.25) / 0.85, 0.0), 1.0) ** 0.6) * (min(max((5.95 - s) / 1.9, 0.0), 1.0) ** 0.8)

def _canopy_ring(s, out=0.0):
    zc, w, up, dn, e = fus(s); hw = min(0.70, w - 0.10) + out; h = _canopy_h(s) + out; z0 = zc + up - 0.34; a = np.linspace(0, math.pi, 19); p = 2.0 / 2.6
    y = hw * np.sign(np.cos(a)) * np.abs(np.cos(a)) ** p; z = z0 + (h + 0.34) * np.abs(np.sin(a)) ** p
    low = np.stack([np.full(3, X0 - s), np.linspace(-hw, hw, 5)[1:4], np.full(3, z0)], 1)
    return np.vstack([np.stack([np.full(len(a), X0 - s), y, z], 1), low])

def _canopy_pt(s, f, out=0.0):
    r = _canopy_ring(s, out); a = np.linspace(0, math.pi, 19); k = int(round((1 - f) / 2 * 18)); return r[k]

def _glass():
    S = Shell(); G = (0.03, 0.04, 0.05, 1)
    V, Q, T = loft([_canopy_ring(s) for s in np.linspace(2.30, 5.9, 26)]); S.add(V, Q, T, G)
    if not SPECIAL:
        S.add(*ellipsoid(P(0.66, 0, -0.20 + 0.40), (0.50, 0.44, 0.42), 20, 10), color=G)                # nose turret
        S.add(*ellipsoid(P(MID_S, 0, _top(MID_S) + 0.10), (0.44, 0.42, 0.40), 20, 10), color=G)         # mid-upper turret
    S.add(*ellipsoid(P(0.62, 0, -0.20 - 0.34), (0.62, 0.47, 0.50), 20, 10), color=G)                    # the bomb aimer's blister
    S.add(*ellipsoid(P(6.75, 0, _top(6.75) - 0.02), (0.30, 0.30, 0.24), 16, 8), color=G)                # astrodome
    S.add(*ellipsoid(P(20.82, 0, 0.42), (0.42, 0.44, 0.52), 20, 10), color=G)                           # tail turret
    return S.mesh("lanc_glass", sharp=math.radians(50))

# ---- wing geometry
CD = np.array([-math.cos(INC), 0.0, -math.sin(INC)]); UP0 = np.array([-math.sin(INC), 0.0, math.cos(INC)])
TIP_Y = SPAN / 2 - 1.25                                               # the wing-tip joint; a rounded tip finishes the span
K_LE = 0.35                                                           # the 35 per cent chord line of the outer panel is straight

def wing_at(y):
    """Leading-edge point, chord, thickness ratio and the 'up' vector of the wing at span position y (either side)."""
    ay = abs(y); sg = 1.0 if y >= 0 else -1.0
    if ay <= YC:
        return P(W_LE, y, W_Z), W_C0, W_T0, UP0
    u = (ay - YC) / (TIP_Y - YC); c = W_C0 + (W_C1 - W_C0) * u
    le = P(W_LE + K_LE * (W_C0 - c), y, W_Z + math.tan(DIH) * (ay - YC)); up = UP0 * math.cos(DIH) + np.array([0, -sg * math.sin(DIH), 0])
    return le, c, W_T0 + (W_T1 - W_T0) * u, up / np.linalg.norm(up)

def _yt(b, t):
    b = np.clip(b, 0.0, 1.0); return 5 * t * (0.2969 * np.sqrt(b) - 0.1260 * b - 0.3516 * b ** 2 + 0.2843 * b ** 3 - 0.1036 * b ** 4)

def wing_surf(y, s, upper=True, out=0.0):
    """Point on the wing's upper or lower skin at span y and fuselage station s, pushed out along the panel's normal."""
    le, c, t, up = wing_at(y); b = (X0 - s - le[0]) / (c * CD[0]); zc = 0.02 * 4 * b * (1 - b); h = float(_yt(b, t))
    return le + c * b * CD + c * (zc + (h if upper else -h)) * up + (out if upper else -out) * up

def _two_tone(V, rings, n, extra=2):
    """Colours for a lifting surface made by qgeo.surface: the upper side camouflaged, the under side Night."""
    m = 2 * n - 2; c = np.tile(np.array(NIGHT), (len(V), 1)); j = np.arange(rings * m) % m; c[: rings * m][j < n] = CAMO; return c

def _wings(S):
    n = 22
    for sg in (1, -1):
        st = []
        for y in list(np.linspace(0.0, YC, 4)) + list(np.linspace(YC, TIP_Y, 9)[1:]):
            le, c, t, up = wing_at(sg * y); st.append((le, c, t, CD, up))
        le, c, t, up = wing_at(sg * TIP_Y); d = np.array([0.0, sg * math.cos(DIH), math.sin(DIH)])
        for f, k in ((0.50, 0.93), (0.90, 0.76), (1.14, 0.50), (1.25, 0.22)):          # the rounded tip
            st.append((le + d * f + (-CD) * (-c * (1 - k) * 0.42), c * k, t * 0.95, CD, up))
        V, Q, T = surface(st, n, camber=0.02); S.add(V, Q, T, _two_tone(V, len(st), n))

def _nacelle(S, yy, inner):
    """One engine nacelle: Merlin power plant with its chin radiator, running back under the wing (the inner ones hold the wheels)."""
    le, c, t, up = wing_at(yy); zw = le[2]; s_le = X0 - le[0]; sp = PROP_S[0 if inner else 1]; zt = zw - 0.34          # thrust line
    end = s_le + (1.08 if inner else 0.74) * c
    st = [(sp + 0.16, 0.36, 0.38, 0.40), (sp + 0.55, 0.43, 0.44, 0.78), (sp + 1.5, 0.48, 0.48, 0.86), (s_le + 0.3, 0.50, 0.50, 0.88 if inner else 0.80), (s_le + 0.45 * c, 0.50, 0.40, 0.86 if inner else 0.66),
          (s_le + 0.80 * c if inner else s_le + 0.60 * c, 0.40, 0.22, 0.62 if inner else 0.40), (end, 0.03, 0.03, 0.05)]
    m = 28; a = np.linspace(0, 2 * np.pi, m, endpoint=False); p = 2.0 / 2.5; cs, sn = np.cos(a), np.sin(a); rings = []; cols = []
    for k, (s, w, hu, hd) in enumerate(st):
        zc = zt + (0.0 if k < len(st) - 1 else -0.12) - math.sin(INC) * max(s - s_le, 0.0) * 0.6
        z = zc + np.where(sn > 0, hu, hd) * np.sign(sn) * np.abs(sn) ** p; rings.append(np.stack([np.full(m, X0 - s), yy + w * np.sign(cs) * np.abs(cs) ** p, z], 1))
        col = np.tile(np.array(NIGHT), (m, 1)); col[sn > 0.25] = CAMO; cols.append(col)
    V, Q, T = loft(rings); col = np.tile(np.array(NIGHT), (len(V), 1)); col[: len(st) * m] = np.concatenate(cols); S.add(V, Q, T, col)
    S.add(*box(P(sp + 0.52, yy, zt - 0.50), (0.06, 0.52, 0.40)), color=(0.004, 0.004, 0.004, 1))                         # the radiator's mouth
    for sg in (1, -1):                                                 # exhaust shrouds along each side of the cowling
        S.add(*box(P(sp + 1.25, yy + sg * 0.475, zt + 0.10), (1.25, 0.05, 0.10)), color=EXH)

def _spinner_prop():
    """One propeller in its own frame: hub at the origin, turning about X.  Three blades, 13 ft across, with yellow tips."""
    S = Shell(); S.add(*revolve([(0.46, 0.0), (0.42, 0.07), (0.30, 0.20), (0.12, 0.31), (-0.10, 0.37), (-0.16, 0.37)], 24), color=NIGHT)
    rr = np.linspace(0.30, PROP_R, 9)
    for k in range(3):
        a = 2 * math.pi * k / 3; er = np.array([0, math.cos(a), math.sin(a)]); et = np.array([0, -math.sin(a), math.cos(a)])
        for r0, r1 in zip(rr[:-1], rr[1:]):
            pts = []
            for r, sgn in ((r0, -1), (r1, -1), (r1, 1), (r0, 1)):
                u = (r - 0.30) / (PROP_R - 0.30); ch = (0.10 + 0.24 * math.sin(math.pi * min(u * 1.25 + 0.1, 1.0)) ** 0.8 * (1.0 if u < 0.92 else 0.75)) * (1.3 if SPECIAL else 1.0)   # the Specials had broad "paddle" blades; beta = math.radians(62.0 - 40.0 * u)
                pts.append(er * r + sgn * ch / 2 * (et * math.cos(beta) + EX * math.sin(beta)))
            nrm = np.cross(pts[1] - pts[0], pts[3] - pts[0]); S.add(*plate(pts, nrm, 0.035 * (1.2 - 0.8 * (r0 - 0.3) / PROP_R)), color=YELLOW if r0 > PROP_R - 0.12 * 2 else NIGHT)
    return S.mesh("lanc_prop", sharp=math.radians(40))

# ---- tail
T_S = 17.85; T_C0 = 2.45; T_C1 = 1.75; T_SPAN = 33.0 * FT; T_Z = 0.72       # tailplane: root leading edge station, chords, span, height
FIN_H = (1.42, 2.22); FIN_C = 2.55                                    # the fins reach this far below and above the tailplane; their greatest chord

def _fin_at(z):
    """Leading-edge station and chord of a fin at height z above the tailplane: a tall oval, fuller towards the front."""
    u = min(max((z + FIN_H[0]) / (FIN_H[0] + FIN_H[1]), 0.0), 1.0); k = max(1.0 - (2 * u - 1) ** 2, 0.0) ** 0.5; c = max(FIN_C * k, 0.02)
    return T_S + 0.42 + FIN_C * 0.5 - 0.54 * c, c

def _tail(S):
    n = 16
    for sg in (1, -1):
        st = [(P(T_S + 0.25 * (T_C0 - c), sg * y, T_Z), c, 0.11, (-1, 0, 0), (0, 0, 1)) for y, c in ((yy, T_C0 + (T_C1 - T_C0) * yy / (T_SPAN / 2)) for yy in np.linspace(0.0, T_SPAN / 2, 5))]
        V, Q, T = surface(st, n); S.add(V, Q, T, _two_tone(V, len(st), n))
        st = []
        for z in -FIN_H[0] + (FIN_H[0] + FIN_H[1]) * (1 - np.cos(np.pi * np.linspace(0.05, 0.95, 17))) / 2:
            sle, c = _fin_at(z); st.append((P(sle, sg * T_SPAN / 2, T_Z + z), c, 0.085, (-1, 0, 0), (0, sg, 0)))
        V, Q, T = surface(st, n); S.add(V, Q, T, NIGHT)

def _disc(S, pt, radii, colors, n=40):
    """Concentric rings of colour on a surface: pt(u, v) maps a point of the unit plane (metres) on to the skin."""
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    for k, (r, col) in enumerate(zip(radii, colors)):
        r0 = radii[k + 1] if k + 1 < len(radii) else 0.0; rs = np.linspace(r0, r, 4)
        V = np.array([pt(rr * math.cos(t), rr * math.sin(t)) for t in a for rr in rs]); S.add(V, grid_faces(n, 4, wrap_u=True), None, col)

ROUNDEL_S = 13.9                                                      # the fuselage roundel

def _markings(S, code="KC", letter="A"):
    IN = 0.0254
    for sg in (1, -1):
        zc, w, up, dn, e = fus(ROUNDEL_S); zr = zc - 0.08
        _disc(S, lambda u, v: np.array([X0 - ROUNDEL_S - u, sg * (w + 0.012), zr + v]), [27 * IN, 24 * IN, 12 * IN, 9 * IN], [R_YEL, R_BLUE, R_WHITE, R_RED])       # Type C1, 54 in
        yc = SPAN / 2 - 2.75; le, c, t, up_ = wing_at(sg * yc); sc_ = X0 - (le + c * 0.46 * CD)[0]
        _disc(S, lambda u, v: wing_surf(sg * yc + v, sc_ + u, True, 0.010), [1.20, 0.48], [R_BLUE, R_RED], n=48)                                                          # Type B, above the wings only
        sle, c = _fin_at(0.75); sf = sle + 0.33 * c                     # fin flash, 24 in by 36 in: red leading
        for side in (1, -1):
            for k, col in enumerate((R_RED, R_WHITE, R_BLUE)):
                x0, x1 = [(0.0, 11 * IN), (11 * IN, 13 * IN), (13 * IN, 24 * IN)][k]
                V = []
                for sx in (sf + x0, sf + x1):
                    for z in (0.75 - 18 * IN, 0.75 + 18 * IN):
                        l2, c2 = _fin_at(z); b = (sx - l2) / c2; V.append([X0 - sx, sg * T_SPAN / 2 + side * (float(_yt(b, 0.085)) * c2 + 0.008), T_Z + z])
                S.add(np.array(V), np.array([[0, 1, 3, 2]]), None, col)

def _codes(col, root, pm, code="KC", letter="A"):
    """Squadron code and aircraft letter in dull red, 4 ft high, as text turned into meshes on the flat of the fuselage sides."""
    obs = []
    for sg in (1, -1):
        for txt, ds in ((code, -2.25 if sg > 0 else 2.25), (letter, 1.65 if sg > 0 else -1.65)):
            cu = bpy.data.curves.new("code", 'FONT'); cu.body = txt; cu.size = 1.45; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.space_character = 1.05
            tmp = bpy.data.objects.new("code_tmp", cu); col.objects.link(tmp); bpy.context.view_layer.update()
            me = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get())); bpy.data.objects.remove(tmp, do_unlink=True); bpy.data.curves.remove(cu)
            at = me.attributes.new("col", 'FLOAT_COLOR', 'POINT'); at.data.foreach_set("color", np.tile(np.array(CODE, np.float32), len(me.vertices)))
            me.materials.append(pm); o = bpy.data.objects.new("Code", me); col.objects.link(o); o.parent = root
            s = ROUNDEL_S + ds; zc, w, up, dn, e = fus(s); o.location = (X0 - s, sg * (w + 0.012), zc - 0.08); o.rotation_euler = (math.pi / 2, 0, math.pi if sg > 0 else 0.0); obs.append(o)
    return obs

def _door(sg):
    """One bomb door in its own frame: hinge along X at the origin; shut, it follows the bulged belly to the centre line."""
    S = Shell(); ss = np.linspace(BAY[0] + 0.02, BAY[1] - 0.02, 30); rows_o = []; rows_i = []
    for s in ss:
        ab = _bay_angle(min(max(s, 3.6), 12.0)); th = np.linspace(2 * math.pi - ab, 1.5 * math.pi, 9) if sg > 0 else np.linspace(math.pi + ab, 1.5 * math.pi, 9)
        y, z = _ring(s, th, 0.004); hz = fus(6.0)[0] - (fus(6.0)[4]) * math.sin(_bay_angle(6.0)) ** (2.0 / 3.0)
        rows_o.append(np.stack([np.full(9, X0 - s) - (X0 - (BAY[0] + BAY[1]) / 2), y - sg * BAY_W, z - HINGE_Z], 1)); rows_i.append(rows_o[-1] + np.array([0, 0, 0.04]))
    S.add(np.concatenate(rows_o), grid_faces(len(ss), 9), None, NIGHT); S.add(np.concatenate(rows_i), grid_faces(len(ss), 9), None, INSIDE)
    return S.mesh("lanc_door%+d" % sg, sharp=3.0)

def _hinge_z():
    zc, w, up, dn, e = fus(6.0); a = _bay_angle(6.0); return zc - (dn + _bulge(6.0)) * math.sin(a) ** (2.0 / e)

HINGE_Z = _hinge_z()
STORE = P(STORE_S, 0.0, BAY_ROOF - (0.14 if SPECIAL else 0.035) - C.TB_D / 2)   # the middle of the bomb's length, aircraft frame

LINK_X = (2.0 * C.K_L, 0.8 * C.K_L)                                                 # the two suspension links, in the bomb's frame (round the steel case)

def _link(sg, x):
    """Half of one suspension link in its own frame: hinged at the top of the bomb, hanging round one side to meet its twin beneath."""
    S = Shell(); rr = lbomb.r_out(lbomb.X0 - x) + 0.02; ph = np.linspace(math.pi / 2, -math.pi / 2, 13)
    for a, b in zip(ph[:-1], ph[1:]):
        pa = np.array([0.0, sg * rr * math.cos(a), rr * math.sin(a) - rr]); pb = np.array([0.0, sg * rr * math.cos(b), rr * math.sin(b) - rr]); d = pb - pa; L_ = np.linalg.norm(d); ey = d / L_; ez = np.cross(EX, ey)
        S.add(*box((pa + pb) / 2, (0.07, L_ * 1.05, 0.014), rot=np.stack([EX, ey, ez], 1)), color=METAL)
    return S.mesh("lanc_link%+d_%d" % (sg, int(x * 10)), sharp=math.radians(40))

def lanc_mat(name="LancPaint"):
    """Matt wartime paint: colours from the 'col' attribute; where its alpha is 0, the Dark Green / Dark Earth pattern."""
    m, N, L, Pn = nodemat(name); a = N.new("ShaderNodeAttribute"); a.attribute_name = "col"; tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.115, 0.16, 0.05); L.new(tc.outputs["Object"], mp.inputs["Vector"])
    n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 1.0; n.inputs["Detail"].default_value = 0.6; n.inputs["Distortion"].default_value = 0.9; L.new(mp.outputs[0], n.inputs["Vector"])
    st = N.new("ShaderNodeMath"); st.operation = 'GREATER_THAN'; st.inputs[1].default_value = 0.5; L.new(n.outputs["Fac"], st.inputs[0])
    cm = N.new("ShaderNodeMixRGB"); cm.inputs[1].default_value = (0.150, 0.110, 0.070, 1); cm.inputs[2].default_value = (0.052, 0.068, 0.040, 1); L.new(st.outputs[0], cm.inputs[0])      # Dark Earth, Dark Green
    up = N.new("ShaderNodeMath"); up.operation = 'LESS_THAN'; up.inputs[1].default_value = 0.5; L.new(a.outputs["Alpha"], up.inputs[0])
    mix = N.new("ShaderNodeMixRGB"); L.new(up.outputs[0], mix.inputs[0]); L.new(a.outputs["Color"], mix.inputs[1]); L.new(cm.outputs[0], mix.inputs[2])
    f = N.new("ShaderNodeTexNoise"); f.inputs["Scale"].default_value = 2.5; f.inputs["Detail"].default_value = 5; L.new(tc.outputs["Object"], f.inputs["Vector"])
    w = N.new("ShaderNodeMixRGB"); w.blend_type = 'MULTIPLY'; w.inputs[0].default_value = 0.14; L.new(mix.outputs[0], w.inputs[1]); L.new(f.outputs["Color"], w.inputs[2]); L.new(w.outputs[0], Pn.inputs["Base Color"])
    Pn.inputs["Roughness"].default_value = 0.62
    return m

class Lancaster:
    def __init__(self, col=None, name="Lanc", store=False, code="YZ" if SPECIAL else "KC", letter="C" if SPECIAL else "A"):
        col = col or bpy.context.scene.collection; M = bpy.data.materials
        self.root = bpy.data.objects.new(name, None); col.objects.link(self.root); self.root.rotation_mode = 'QUATERNION'
        pm = M.get("LancPaint") or lanc_mat()
        S = Shell(); _fuselage(S); _wings(S); _tail(S)
        for sg in (1, -1):
            _nacelle(S, sg * ENG_Y[0], True); _nacelle(S, sg * ENG_Y[1], False)
        _markings(S, code, letter)
        self.body = new_obj(name + "_Body", S.mesh("lanc_body", sharp=math.radians(34)), col, pm); self.body.parent = self.root
        self.glass = new_obj(name + "_Glass", bpy.data.meshes.get("lanc_glass") or _glass(), col, M.get("LancGlass") or glass_mat("LancGlass", (0.03, 0.045, 0.055))); self.glass.parent = self.root
        self.codes = _codes(col, self.root, pm, code, letter)
        self.props = []
        for sg in (1, -1):
            for k in (0, 1):
                le, c, t, up = wing_at(sg * ENG_Y[k]); o = new_obj(name + "_Prop%+d%d" % (sg, k), bpy.data.meshes.get("lanc_prop") or _spinner_prop(), col, pm); o.parent = self.root
                o.location = tuple(P(PROP_S[k], sg * ENG_Y[k], le[2] - 0.34)); o.rotation_mode = 'XYZ'; self.props.append((o, 0.9 * (2 * k + (sg > 0))))
        self.doors = []
        for sg in (() if SPECIAL else (1, -1)):
            d = new_obj(name + "_Door%+d" % sg, bpy.data.meshes.get("lanc_door%+d" % sg) or _door(sg), col, pm); d.parent = self.root
            d.location = (X0 - (BAY[0] + BAY[1]) / 2, sg * BAY_W, HINGE_Z); self.doors.append((d, sg))
        self.store = None
        if store:
            self.store = lbomb.Bomb(col, name + "_Store"); self.store.root.parent = self.root; self.store.root.location = tuple(STORE)
        self.links = []
        if store:                                                      # twin suspension links, each closed beneath the bomb by a release clip
            for x in LINK_X:
                for sg in (1, -1):
                    o = new_obj(name + "_Link%+d" % sg, _link(sg, x), col, pm); o.parent = self.root; rr = lbomb.r_out(lbomb.X0 - x) + 0.02
                    o.location = (STORE[0] + x, 0.0, STORE[2] + rr); self.links.append((o, sg))
        self.set(0.0, 0.0)

    def set(self, doors=None, links=None):
        """doors: 0 shut .. 1 open (they swing down and outwards to hang beside the bay); links: 0 closed round the bomb .. 1 let go."""
        if doors is not None:
            for d, sg in self.doors:
                d.rotation_euler = (-sg * math.radians(96.0) * doors, 0, 0)
        if links is not None:
            for o, sg in self.links:
                o.rotation_euler = (sg * math.radians(38.0) * links, 0, 0)

    def spin_props(self, sc, t, dt, mb=True, rpm=1300.0):
        """Turn the four propellers; with motion blur, linear keys one frame either side so that they smear into discs."""
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
