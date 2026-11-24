"""Shared numbers, the bomb's fall and its path through the ground for the B-1B / BLU-109 segment (no bpy imports).

Site coordinates: the bomb meets the mountainside at the origin; +X is horizontal into the mountain, +Z is up, and
the section through the bunker is the plane y = 0.  Times: t = seconds after release; tp = seconds after the nose
touches the slope; the fuze fires at tp = FUZE_DELAY.

How deep the bomb goes is not a published figure for this target (the target is invented), so it is calculated with
the Young / Sandia penetration equations (SAND97-2426), which reproduce the published 1.2 to 2.4 m of reinforced
concrete for this bomb.  Everything marked "illustrative" is a plausible choice, not a quoted profile.
"""
import math
import numpy as np

FPS = 24
G = 9.81
SDT = 1.0 / 60.0
# ---- BLU-109/B (src: USAF Weapons File; ordnance data sheet; Jane's via Hansson 2011)
BLU_L = 2.40; BLU_D = 0.368; BLU_M = 874.0            # 14.5 in, about 1,927 lb
FILL = 243.0                                          # 535 lb of tritonal (PBXN-109 in the BLU-109A/B)
CASE = 0.027                                          # the steel case is at least 1.06 in thick
PEN_CONCRETE = (1.2, 2.4)                             # published: 1.2-1.8 m (ordnance data), 1.8-2.4 m (Jane's)
FUZE_DELAY = 0.060                                    # FMU-143: single 0.060 s delay after impact
# ---- GBU-31(V)3/B: the BLU-109 with the JDAM tail kit and strakes (src: USAF fact sheet)
GBU_L = 3.774; GBU_M = 961.4; TAIL_SPAN = 0.635
# ---- B-1B (src: USAF fact sheet; T.O. 1B-1B-1 description)
B1_LEN = 44.5; B1_SPAN_FWD = 41.8; B1_SPAN_AFT = 24.1; B1_H = 10.4; SWEEP_FWD = 15.0; SWEEP_AFT = 67.5
# ---- the release (illustrative): level, Mach 0.85, 6,000 m above the target, which lies 2,200 m above sea level
TARGET_ELEV = 2200.0; H_REL = 6000.0; MACH_REL = 0.85

def _air(h):
    T = 288.15 - 0.0065 * h; return 1.225 * (T / 288.15) ** 4.256, math.sqrt(1.4 * 287.05 * T)

V_REL = MACH_REL * _air(TARGET_ELEV + H_REL)[1]

def _fall(dt=0.005):
    """Point mass with drag; in the last part of the fall the tail kit steepens the path (JDAM can be set for a steep impact)."""
    x = 0.0; z = H_REL; vx = V_REL; vz = -1.5; t = 0.0; out = [(t, x, z, vx, vz)]; A = math.pi * BLU_D ** 2 / 4
    while z > 0.0:
        rho, a = _air(TARGET_ELEV + z); v = math.hypot(vx, vz); M = v / a
        cd = 0.34 + 0.62 * min(max((M - 0.78) / 0.22, 0.0), 1.0)                     # strakes and tail kit; drag rises steeply towards Mach 1
        k = 0.5 * rho * cd * A / GBU_M; ax = -k * v * vx; az = -G - k * v * vz
        if z < 3200.0:                                                               # steer down: a turn of at most about 1 g towards a 66 degree path
            g_now = math.atan2(-vz, vx); err = math.radians(66.0) - g_now; an = max(min(err * 6.0, 1.0), -1.0) * G
            ax += an * (vz / v); az += -an * (vx / v)                                # normal to the path, towards the ground
        vx += ax * dt; vz += az * dt; x += vx * dt; z += vz * dt; t += dt; out.append((t, x, z, vx, vz))
    a, b = np.array(out[-2]), np.array(out[-1]); out[-1] = tuple(a + (b - a) * (a[2] / (a[2] - b[2])))           # end exactly on the ground, not a step below it
    return np.array(out)

FALL = _fall()
TOF = float(FALL[-1, 0]); THROW = float(FALL[-1, 1]); V_HIT = float(np.hypot(FALL[-1, 3], FALL[-1, 4])); DIVE = math.degrees(math.atan2(-FALL[-1, 4], FALL[-1, 3]))
U = np.array([math.cos(math.radians(DIVE)), 0.0, -math.sin(math.radians(DIVE))])     # unit vector along the bomb's path at impact

def fall_state(t):
    """Site coordinates: centre of the bomb and its velocity t seconds after release (it arrives at the origin at TOF)."""
    a = FALL; tt = min(max(t, 0.0), TOF); f = lambda k: float(np.interp(tt, a[:, 0], a[:, k]))
    return np.array([f(1) - THROW, 0.0, f(2)]), np.array([f(3), 0.0, f(4)])

def jet_pos(t):
    return np.array([-THROW + V_REL * t, 0.0, H_REL])

# ---- the Young / Sandia penetration equations, SI form (D in metres, V in m/s, mass in kg, area in m2)
NOSE_L = 0.62
N_NOSE = 0.18 * NOSE_L / BLU_D + 0.56                 # tangent-ogive nose performance coefficient

def young_depth(S, V, N=N_NOSE, m=BLU_M, d=BLU_D):
    k = S * N * (m / (math.pi * d * d / 4)) ** 0.7
    return 0.000018 * k * (V - 30.5) if V >= 61.0 else 0.0008 * k * math.log(1.0 + 2.15e-4 * V * V)

def s_concrete(thick, fc_psi=5000.0, steel_pct=2.0, cure_yr=1.0):
    tc = min(thick / BLU_D, 6.0); return 0.085 * (11.0 - steel_pct) * (cure_yr * tc) ** -0.06 * (5000.0 / fc_psi) ** 0.3

def s_rock(fc_psi, Q):
    return 2.7 * (fc_psi * Q) ** -0.3

# ---- the site (invented): a cut-and-cover bunker let into a 25 degree mountainside
SLOPE = 25.0                                          # the slope rises towards +X
S_FILL = 3.0                                          # compacted earth and broken rock over the roof: the "dense, dry, cemented sand" class
ROOF = 0.90; WALL = 0.60; FLOOR = 0.60                # reinforced concrete, 35 MPa (5,000 psi), about 2 % steel
ROOM_H = 3.0; ROOM_X = (-1.5, 8.5); ROOM_Y = 3.0      # inside: 10 m long, 6 m wide (half-width 3 m), 3 m high
FILL_PATH = 3.6                                       # metres of fill along the bomb's path before the roof
S_ROOF = s_concrete(ROOF); S_FLOOR = s_concrete(FLOOR)
S_LIMESTONE = s_rock(10000.0, 0.7)                    # sound limestone, 69 MPa, few joints
S_WEATHERED = s_rock(4000.0, 0.3)                     # weak, weathered, jointed rock

def _through(V, S, path):
    """Speed on leaving a layer `path` metres thick along the trajectory, and the time taken (constant deceleration)."""
    D = young_depth(S, V)
    if D <= path:
        return 0.0, 2.0 * D / max(V, 1e-6), D
    vex = V * math.sqrt(1.0 - path / D); return vex, 2.0 * path / (V + vex), path

sinD = math.sin(math.radians(DIVE))
Z_ROOF_TOP = -FILL_PATH * sinD; Z_CEIL = Z_ROOF_TOP - ROOF; Z_FLOOR = Z_CEIL - ROOM_H
V1, T1, _ = _through(V_HIT, S_FILL, FILL_PATH)                    # out of the fill
V2, T2, _ = _through(V1, S_ROOF, ROOF / sinD)                     # out of the roof slab
T3 = (ROOM_H / sinD) / max(V2, 1e-6)                              # across the room
V3, T4, D_FLOOR = _through(V2, S_FLOOR, FLOOR / sinD)             # into the floor slab
V4, T5, D_ROCK = _through(V3, S_WEATHERED, 50.0)                  # and, if it gets through, into the rock under it
S1 = FILL_PATH; S2 = S1 + ROOF / sinD; S3 = S2 + ROOM_H / sinD; S4 = S3 + D_FLOOR; S_END = S4 + D_ROCK
TP = (0.0, T1, T1 + T2, T1 + T2 + T3, T1 + T2 + T3 + T4, T1 + T2 + T3 + T4 + T5)

def pen_state(tp):
    """Distance of the nose along the path below the surface (m) and the speed (m/s), tp seconds after it touches."""
    if tp <= 0:
        return V_HIT * tp, V_HIT
    segs = ((TP[0], TP[1], 0.0, S1, V_HIT, V1), (TP[1], TP[2], S1, S2, V1, V2), (TP[2], TP[3], S2, S3, V2, V2), (TP[3], TP[4], S3, S4, V2, V3), (TP[4], TP[5], S4, S_END, V3, 0.0))
    for ta, tb, sa, sb, va, vb in segs:
        if tp < tb:
            u = (tp - ta) / max(tb - ta, 1e-9); v = va + (vb - va) * u; return sa + (va + v) / 2 * (tp - ta), v
    return S_END, 0.0

S_BURST, _vb = pen_state(FUZE_DELAY)
BURST = U * (S_BURST - BLU_L / 2)                                 # centre of the bomb when the fuze fires
DEPTH_BURST = -float((U * S_BURST)[2])                            # metres below the point of impact, measured straight down
PORTAL_X = Z_FLOOR / math.tan(math.radians(SLOPE))                # where the access tunnel, level with the floor, meets daylight
TUN_W = 2.2; TUN_H = 2.4
# ---- what the same bomb would do in uniform ground at this speed (for the closing table)
TABLE = {"fill": young_depth(S_FILL, V_HIT), "concrete": young_depth(s_concrete(2.4), V_HIT), "weathered": young_depth(S_WEATHERED, V_HIT), "limestone": young_depth(S_LIMESTONE, V_HIT)}

if __name__ == "__main__":
    print("release %.0f m/s  fall %.1f s  throw %.0f m  impact %.0f m/s at %.1f deg" % (V_REL, TOF, THROW, V_HIT, DIVE))
    print("N %.3f  S roof %.3f  S limestone %.3f  S weathered %.3f" % (N_NOSE, S_ROOF, S_LIMESTONE, S_WEATHERED))
    print("fill: in %.0f out %.0f m/s (%.1f ms)   roof: out %.0f m/s (%.1f ms)   room %.1f ms   floor slab: out %.0f m/s after %.2f m (%.1f ms)   rock: stops after %.2f m" % (V_HIT, V1, T1 * 1e3, V2, T2 * 1e3, T3 * 1e3, V3, D_FLOOR, T4 * 1e3, D_ROCK))
    print("times ms", [round(t * 1e3, 1) for t in TP], " path at 60 ms %.2f m (end %.2f)  burst depth %.2f m  burst centre" % (S_BURST, S_END, DEPTH_BURST), BURST.round(2))
    print("z roof top %.2f  ceiling %.2f  floor %.2f  portal x %.1f" % (Z_ROOF_TOP, Z_CEIL, Z_FLOOR, PORTAL_X))
    print("half-space depths at impact speed:", {k: round(v, 2) for k, v in TABLE.items()})
