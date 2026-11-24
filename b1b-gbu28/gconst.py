"""Shared numbers, the bomb's fall and its path through the ground for the B-1B / GBU-28 segment (no bpy imports).

Site coordinates: the bomb meets the flat desert at the origin; +Z is up; the bomb travels in the X-Z plane, and the
section through the bunker is the plane y = 0.  Times: t = seconds after release; tp = seconds after the nose touches
the ground; the fuze fires at tp = FUZE_DELAY.

The bunker is invented, on the pattern described for the Iraqi command bunkers the bomb was built for in 1991 (about
50 ft of soil, a two-foot slab of reinforced concrete, then concrete chambers).  How far the bomb gets through it is
calculated with the Young / Sandia penetration equations (SAND97-2426), layer by layer.
"""
import math
import numpy as np

FPS = 24
G = 9.81
# ---- GBU-28/B and its BLU-113/B warhead (src: FAS / GlobalSecurity; NDIA 2005 BLU-122 briefing; designation-systems; Kopp)
GBU_L = 5.84; GBU_M = 2130.0                          # 19 ft 2 in; about 4,700 lb complete
BLU_L = 3.90; BLU_D = 0.370; BLU_M = 2041.0           # 153.5 in long, 14.56 in across, 4,500 lb
FILL = 286.0                                          # 630 lb of tritonal
CASE = 0.058                                          # the wall is 2.28 in thick (bored-out 8 in howitzer barrel)
SPAN_SHUT = 0.72; SPAN_OPEN = 1.68                    # rear wings folded and open
FUZE_DELAY = 0.060                                    # FMU-143: 60 ms after impact
PUBLISHED = dict(concrete=6.1, earth=30.5, sled=6.7)  # "more than 20 ft of concrete, more than 100 ft of earth"; sled test through 22 ft of slabs
# ---- the release (illustrative): level at Mach 0.9, 9,000 m above a plain that lies 300 m above sea level
TARGET_ELEV = 300.0; H_REL = 9000.0; MACH_REL = 0.90; DIVE_SET = 80.0

def _air(h):
    T = max(288.15 - 0.0065 * h, 216.65); return 1.225 * (T / 288.15) ** 4.256 if h < 11000 else 0.3639 * math.exp(-(h - 11000) / 6341.6), math.sqrt(1.4 * 287.05 * T)

V_REL = MACH_REL * _air(TARGET_ELEV + H_REL)[1]

def _fall(dt=0.005):
    """Point mass with drag; from 6 km down the bomb's wings steer it on to a steep path (at most about 1.5 g)."""
    x = 0.0; z = H_REL; vx = V_REL; vz = -2.0; t = 0.0; out = [(t, x, z, vx, vz)]; A = math.pi * BLU_D ** 2 / 4
    while z > 0.0:
        rho, a = _air(TARGET_ELEV + z); v = math.hypot(vx, vz); M = v / a
        cd = 0.34 + 0.62 * min(max((M - 0.80) / 0.25, 0.0), 1.0) - 0.10 * min(max((M - 1.05) / 0.5, 0.0), 1.0)      # nose kit, wings and collar; the drag rise through Mach 1
        k = 0.5 * rho * cd * A / GBU_M; ax = -k * v * vx; az = -G - k * v * vz
        if z < 6000.0:
            g_now = math.atan2(-vz, vx); err = math.radians(DIVE_SET) - g_now; an = max(min(err * 6.0, 1.5), -1.5) * G
            ax += an * (vz / v); az += -an * (vx / v)
        vx += ax * dt; vz += az * dt; x += vx * dt; z += vz * dt; t += dt; out.append((t, x, z, vx, vz))
    a, b = np.array(out[-2]), np.array(out[-1]); out[-1] = tuple(a + (b - a) * (a[2] / (a[2] - b[2])))           # end exactly on the ground
    return np.array(out)

FALL = _fall()
TOF = float(FALL[-1, 0]); THROW = float(FALL[-1, 1]); V_HIT = float(np.hypot(FALL[-1, 3], FALL[-1, 4])); DIVE = math.degrees(math.atan2(-FALL[-1, 4], FALL[-1, 3]))
MACH_HIT = V_HIT / _air(TARGET_ELEV)[1]
U = np.array([math.cos(math.radians(DIVE)), 0.0, -math.sin(math.radians(DIVE))])     # unit vector along the bomb's path at impact
sinD = math.sin(math.radians(DIVE))

def fall_state(t):
    """Site coordinates: the point of the nose and the velocity t seconds after release (the nose reaches the origin at TOF)."""
    a = FALL; tt = min(max(t, 0.0), TOF); f = lambda k: float(np.interp(tt, a[:, 0], a[:, k]))
    return np.array([f(1) - THROW, 0.0, f(2)]), np.array([f(3), 0.0, f(4)])

def jet_pos(t):
    return np.array([-THROW + V_REL * t, 0.0, H_REL])

# ---- the Young / Sandia penetration equations, SI form (D in metres, V in m/s, mass in kg, area in m2)
NOSE_L = 0.62                                         # the nose is the BLU-109's (src: designation-systems); its length is estimated from photographs
N_NOSE = 0.18 * NOSE_L / BLU_D + 0.56

def young_depth(S, V, N=N_NOSE, m=BLU_M, d=BLU_D):
    k = S * N * (m / (math.pi * d * d / 4)) ** 0.7
    return 0.000018 * k * (V - 30.5) if V >= 61.0 else 0.0008 * k * math.log(1.0 + 2.15e-4 * V * V)

def s_concrete(thick, fc_psi=5000.0, steel_pct=2.0, cure_yr=1.0):
    tc = min(thick / BLU_D, 6.0); return 0.085 * (11.0 - steel_pct) * (cure_yr * tc) ** -0.06 * (5000.0 / fc_psi) ** 0.3

def s_rock(fc_psi, Q):
    return 2.7 * (fc_psi * Q) ** -0.3

# ---- the site (invented): chambers of reinforced concrete under 15 m of soil and a concrete slab, on a flat plain
S_SOIL = 5.2                                          # medium-dense sand and silt
COVER = 15.0; SLAB = 0.60; GAP = 1.0; ROOF = 0.50; ROOM_H = 4.0; FLOOR = 0.50; WALL = 0.50
LAYERS = [("soil", "soil", COVER, S_SOIL), ("slab", "conc", SLAB, s_concrete(SLAB)), ("gap", "soil", GAP, S_SOIL), ("roof", "conc", ROOF, s_concrete(ROOF)),
          ("room", "air", ROOM_H, 0.0), ("floor", "conc", FLOOR, s_concrete(FLOOR)), ("below", "soil", 60.0, S_SOIL)]
Z_SLAB = -COVER; Z_ROOF = -(COVER + SLAB + GAP); Z_CEIL = Z_ROOF - ROOF; Z_FLOOR = Z_CEIL - ROOM_H

def _run():
    """Through the layers: [(name, kind, s0, s1, v0, v1, t0, t1)] with s the distance along the path."""
    out = []; v = V_HIT; s = 0.0; t = 0.0
    for name, kind, th, S in LAYERS:
        path = th / sinD
        if v <= 0:
            break
        if kind == "air":
            v1 = v; dt = path / v; ds = path
        else:
            D = young_depth(S, v)
            if D <= path:
                v1 = 0.0; ds = D; dt = 2.0 * D / v
            else:
                v1 = v * math.sqrt(1.0 - path / D); ds = path; dt = 2.0 * path / (v + v1)
        out.append((name, kind, s, s + ds, v, v1, t, t + dt)); s += ds; t += dt; v = v1
    return out

RUN = _run()
S_END = RUN[-1][3]; T_END = RUN[-1][7]

def pen_state(tp):
    """Distance of the nose along the path below the surface (m) and the speed (m/s), tp seconds after it touches."""
    if tp <= 0:
        return V_HIT * tp, V_HIT
    for name, kind, s0, s1, v0, v1, t0, t1 in RUN:
        if tp < t1:
            u = (tp - t0) / max(t1 - t0, 1e-9); v = v0 + (v1 - v0) * u; return s0 + (v0 + v) / 2 * (tp - t0), v
    return S_END, 0.0

def layer_at(name):
    return [r for r in RUN if r[0] == name][0]

S_BURST, V_BURST = pen_state(FUZE_DELAY)
NOSE_BURST = U * S_BURST; BURST = U * (S_BURST - BLU_L / 2)           # the nose and the middle of the warhead when the fuze fires
DEPTH_BURST = -float(NOSE_BURST[2])
IN_ROOM = Z_FLOOR < BURST[2] < Z_CEIL
# ---- what the same bomb would do in uniform ground at this speed (for the closing table)
TABLE = {"soil": young_depth(S_SOIL, V_HIT), "concrete": young_depth(s_concrete(6.0), V_HIT), "weathered": young_depth(s_rock(4000.0, 0.3), V_HIT), "limestone": young_depth(s_rock(10000.0, 0.7), V_HIT)}
# ---- the bunker's plan along the section (x; the bomb comes down at about x = 0 .. 4)
XC = float((U * (COVER + SLAB + GAP + ROOF + ROOM_H / 2) / sinD)[0])  # where the path crosses the middle of the room
ROOM_A = (XC - 7.0, XC + 7.0); ROOM_B = (XC + 14.0, XC + 26.0); COR_H = 2.6; COR_W = 2.4
STAIR_X = (XC - 16.0, XC - 16.0 - (-Z_FLOOR - 0.0))                    # a 45 degree stair from the corridor's end up to the surface
ENTR_X = STAIR_X[1]; VENTS = (XC + 4.5, XC + 20.0); VENT_R = 0.45

if __name__ == "__main__":
    print("release %.0f m/s  fall %.1f s  throw %.0f m  impact %.0f m/s (Mach %.2f) at %.1f deg" % (V_REL, TOF, THROW, V_HIT, MACH_HIT, DIVE))
    print("N %.3f   S: soil %.2f  slab %.3f  roof %.3f" % (N_NOSE, S_SOIL, s_concrete(SLAB), s_concrete(ROOF)))
    for name, kind, s0, s1, v0, v1, t0, t1 in RUN:
        print("  %-6s %-5s path %6.2f -> %6.2f m   %5.0f -> %5.0f m/s   %5.1f -> %5.1f ms" % (name, kind, s0, s1, v0, v1, t0 * 1e3, t1 * 1e3))
    print("fuze at %.0f ms: nose %.2f m along the path, %.2f m down, at %.0f m/s; warhead centre z %.2f (ceiling %.2f, floor %.2f) in room: %s" % (FUZE_DELAY * 1e3, S_BURST, DEPTH_BURST, V_BURST, BURST[2], Z_CEIL, Z_FLOOR, IN_ROOM))
    print("uniform ground at impact speed:", {k: round(v, 1) for k, v in TABLE.items()}, " XC %.2f  entrance x %.1f" % (XC, ENTR_X))
