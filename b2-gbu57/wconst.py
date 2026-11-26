"""Shared numbers, the bomb's fall and its path through the ground for the B-2 / GBU-57 segment (no bpy imports).

Site coordinates: the bomb meets the mountainside at the origin; +X is horizontal into the mountain, +Z is up, and
the section through the bunker is the plane y = 0.  Times: t = seconds after release; tp = seconds after the nose
touches the slope; the fuze fires at tp = FUZE_DELAY.

Published (USAF fact sheet and Air & Space Forces Magazine; DOT&E reports; Wikipedia for the fill): 30,000 lb class,
20.5 ft long, 31.5 in across; 4,590 lb of AFX-757 and 752 lb of PBXN-114; a case of high-strength steel; GPS/INS
guidance with lattice fins at the tail; two carried by a B-2.  The Air Force says it is "designed to penetrate up
to 200 feet underground before exploding", and the film shows that: the invented bunker's hall lies 61 m (200 ft)
below the point of impact.  What the 200 ft are made of is not stated; other published figures are 200 ft of
5,000 psi concrete and 130 ft of moderately hard rock (the 2004 proposal), 200 ft of earth or 60 ft of concrete
(Janes).  By the Young / Sandia penetration equations (SAND97-2426) the bomb reaches 61 m only in soft earth, so
that is what the film's mountainside is made of; the equations' results for other ground are shown beside the
published claims in the closing table.  Everything marked "illustrative" is a plausible
choice, not a quoted profile.  The names follow the BLU-109 segment's pconst, whose site and shot code this one
adapts: BLU_* is the penetrator body, GBU_* the whole bomb with its tail.
"""
import math
import numpy as np

FPS = 24
G = 9.81
SDT = 1.0 / 60.0
K = 3.0                                               # how much bigger this bunker and its surroundings are than the BLU-109 film's (used by the site, sim and shot code)
# ---- GBU-57 (src: see above)
GBU_L = 20.5 * 0.3048                                 # 6.25 m overall
BLU_D = 31.5 * 0.0254                                 # 0.80 m
BLU_L = 5.55                                          # the steel body without the tail section (estimated from photographs)
GBU_M = 13608.0                                       # 30,000 lb, the USAF's figure for the class
BLU_M = 12304.0                                       # 27,125 lb, the lower published weight: used for what goes into the ground
FILL = 2082.0 + 341.0                                 # 2,423 kg: AFX-757 and PBXN-114
CASE = 0.060                                          # wall of the body, estimated from the weights (not published)
TAIL_SPAN = 2.05                                      # across the opened lattice fins (estimated from photographs)
WING_SPAN = 1.42                                      # across the short wings on the body (estimated)
PUBLISHED = dict(official=61.0, earth=61.0, concrete=(18.0, 61.0), hard=(2.4, 8.0), rock=40.0)   # metres: see the notes above (8 ft and 26 ft are both quoted for 10,000 psi concrete)
# ---- B-2A (src: USAF fact sheet)
B2_SPAN = 52.4; B2_LEN = 21.0; B2_H = 5.18; B2_SWEEP = 33.0
# ---- the release (illustrative): level, Mach 0.80, 15,240 m (50,000 ft, the B-2's ceiling) above sea level; the target lies at 1,700 m
TARGET_ELEV = 1700.0; H_REL = 13540.0; MACH_REL = 0.80; DIVE_SET = 70.0

def _air(h):
    T = max(288.15 - 0.0065 * h, 216.65); return (1.225 * (T / 288.15) ** 4.256 if h < 11000 else 0.3639 * math.exp(-(h - 11000) / 6341.6)), math.sqrt(1.4 * 287.05 * T)

V_REL = MACH_REL * _air(TARGET_ELEV + H_REL)[1]

def _fall(dt=0.005):
    """Point mass with drag; from 5 km up the lattice fins steer it on to a steep path (at most about 1.2 g)."""
    x = 0.0; z = H_REL; vx = V_REL; vz = -1.5; t = 0.0; out = [(t, x, z, vx, vz)]; A = math.pi * BLU_D ** 2 / 4
    while z > 0.0:
        rho, a = _air(TARGET_ELEV + z); v = math.hypot(vx, vz); M = v / a
        cd = 0.30 + 0.50 * min(max((M - 0.80) / 0.25, 0.0), 1.0) - 0.08 * min(max((M - 1.05) / 0.5, 0.0), 1.0)      # body, wings and lattice fins; the drag rise through Mach 1
        k = 0.5 * rho * cd * A / GBU_M; ax = -k * v * vx; az = -G - k * v * vz
        if z < 5000.0:
            g_now = math.atan2(-vz, vx); err = math.radians(DIVE_SET) - g_now; an = max(min(err * 6.0, 1.2), -1.2) * G
            ax += an * (vz / v); az += -an * (vx / v)
        vx += ax * dt; vz += az * dt; x += vx * dt; z += vz * dt; t += dt; out.append((t, x, z, vx, vz))
    a, b = np.array(out[-2]), np.array(out[-1]); out[-1] = tuple(a + (b - a) * (a[2] / (a[2] - b[2])))
    return np.array(out)

FALL = _fall()
TOF = float(FALL[-1, 0]); THROW = float(FALL[-1, 1]); V_HIT = float(np.hypot(FALL[-1, 3], FALL[-1, 4])); DIVE = math.degrees(math.atan2(-FALL[-1, 4], FALL[-1, 3]))
MACH_HIT = V_HIT / _air(TARGET_ELEV)[1]
U = np.array([math.cos(math.radians(DIVE)), 0.0, -math.sin(math.radians(DIVE))])     # unit vector along the bomb's path at impact

def fall_state(t):
    """Site coordinates: the bomb's nose and its velocity t seconds after release (it arrives at the origin at TOF)."""
    a = FALL; tt = min(max(t, 0.0), TOF); f = lambda k: float(np.interp(tt, a[:, 0], a[:, k]))
    return np.array([f(1) - THROW, 0.0, f(2)]), np.array([f(3), 0.0, f(4)])

def jet_pos(t):
    return np.array([-THROW + V_REL * t, 0.0, H_REL])

# ---- the Young / Sandia penetration equations, SI form (D in metres, V in m/s, mass in kg, area in m2)
NOSE_L = 1.45                                         # length of the ogive (estimated from photographs)
N_NOSE = 0.18 * NOSE_L / BLU_D + 0.56

def young_depth(S, V, N=N_NOSE, m=BLU_M, d=BLU_D):
    k = S * N * (m / (math.pi * d * d / 4)) ** 0.7
    return 0.000018 * k * (V - 30.5) if V >= 61.0 else 0.0008 * k * math.log(1.0 + 2.15e-4 * V * V)

def s_concrete(thick, fc_psi=5000.0, steel_pct=2.0, cure_yr=1.0):
    tc = min(thick / BLU_D, 6.0); return 0.085 * (11.0 - steel_pct) * (cure_yr * tc) ** -0.06 * (5000.0 / fc_psi) ** 0.3

def s_rock(fc_psi, Q):
    return 2.7 * (fc_psi * Q) ** -0.3

# ---- the site (invented): a concrete hall 61 m (200 ft) down inside a 25 degree mountainside of earth
SLOPE = 25.0
S_FILL = 9.0                                          # the earth over the roof: soft soil (S-numbers of 8 to 10 are loose, moist or soft soils); chosen so that the bomb does reach the published depth
S_EARTH = 6.0                                         # ordinary soil, for the comparison with the published "200 ft of earth"
ROOF = 2.50; WALL = 1.50; FLOOR = 1.50                # reinforced concrete, 35 MPa (5,000 psi), about 2 % steel
ROOM_H = 7.0; ROOM_X = (8.0, 38.0); ROOM_Y = 8.0      # inside: 30 m long, 16 m wide (half-width 8 m), 7 m high
COVER = 54.5                                          # metres of earth over the roof, measured straight down from the point of impact
FILL_PATH = COVER / math.sin(math.radians(DIVE))      # the same along the bomb's path
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
V1, T1, _ = _through(V_HIT, S_FILL, FILL_PATH)                    # out of the cover
V2, T2, _ = _through(V1, S_ROOF, ROOF / sinD)                     # out of the roof slab
T3 = (ROOM_H / sinD) / max(V2, 1e-6)                              # across the hall
V3, T4, D_FLOOR = _through(V2, S_FLOOR, FLOOR / sinD)             # into the floor slab
V4, T5, D_ROCK = _through(V3, S_WEATHERED, 50.0)                  # and, if it gets through, into the rock under it
S1 = FILL_PATH; S2 = S1 + ROOF / sinD; S3 = S2 + ROOM_H / sinD; S4 = S3 + D_FLOOR; S_END = S4 + D_ROCK
TP = (0.0, T1, T1 + T2, T1 + T2 + T3, T1 + T2 + T3 + T4, T1 + T2 + T3 + T4 + T5)
FUZE_DELAY = TP[2] + 0.52 * T3                                    # the fuze senses the layers it goes through and fires in the open space under the roof (set here to fire in the middle of the hall, 61 m down)

def pen_state(tp):
    """Distance of the nose along the path below the surface (m) and the speed (m/s), tp seconds after it touches."""
    if tp <= 0:
        return V_HIT * tp, V_HIT
    segs = ((TP[0], TP[1], 0.0, S1, V_HIT, V1), (TP[1], TP[2], S1, S2, V1, V2), (TP[2], TP[3], S2, S3, V2, V2), (TP[3], TP[4], S3, S4, V2, V3), (TP[4], TP[5], S4, S_END, V3, 0.0))
    for ta, tb, sa, sb, va, vb in segs:
        if tp < tb:
            u = (tp - ta) / max(tb - ta, 1e-9); v = va + (vb - va) * u; return sa + (va + v) / 2 * (tp - ta), v
    return S_END, 0.0

S_BURST, V_BURST = pen_state(FUZE_DELAY)
BURST = U * (S_BURST - BLU_L / 2)                                 # centre of the body when the fuze fires
DEPTH_BURST = -float((U * S_BURST)[2])                            # metres below the point of impact, measured straight down
PORTAL_X = Z_FLOOR / math.tan(math.radians(SLOPE))                # where the access tunnel, level with the floor, meets daylight
TUN_W = 6.0; TUN_H = 6.0
# ---- what the same bomb would do in uniform ground at this speed (for the closing table)
TABLE = {"earth": young_depth(S_EARTH, V_HIT), "fill": young_depth(S_FILL, V_HIT), "concrete": young_depth(s_concrete(6 * BLU_D), V_HIT), "hard": young_depth(s_concrete(6 * BLU_D, 10000.0), V_HIT),
         "weathered": young_depth(S_WEATHERED, V_HIT), "limestone": young_depth(S_LIMESTONE, V_HIT)}

if __name__ == "__main__":
    print("release %.0f m/s  fall %.1f s  throw %.0f m  impact %.0f m/s (Mach %.2f) at %.1f deg" % (V_REL, TOF, THROW, V_HIT, MACH_HIT, DIVE))
    print("N %.3f  S roof %.3f  S limestone %.3f  S weathered %.3f" % (N_NOSE, S_ROOF, S_LIMESTONE, S_WEATHERED))
    print("cover: in %.0f out %.0f m/s (%.1f ms)   roof: out %.0f m/s (%.1f ms)   hall %.1f ms   floor slab: out %.0f m/s after %.2f m (%.1f ms)   rock: stops after %.2f m" % (V_HIT, V1, T1 * 1e3, V2, T2 * 1e3, T3 * 1e3, V3, D_FLOOR, T4 * 1e3, D_ROCK))
    print("times ms", [round(t * 1e3, 1) for t in TP], " fuze %.1f ms  path %.2f m (end %.2f)  burst depth %.2f m  burst centre" % (FUZE_DELAY * 1e3, S_BURST, S_END, DEPTH_BURST), BURST.round(2))
    print("z roof top %.2f  ceiling %.2f  floor %.2f  portal x %.1f" % (Z_ROOF_TOP, Z_CEIL, Z_FLOOR, PORTAL_X))
    print("half-space depths at impact speed:", {k: round(v, 2) for k, v in TABLE.items()})
