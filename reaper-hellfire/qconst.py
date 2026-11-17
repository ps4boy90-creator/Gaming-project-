"""Shared geometry, timing and the missile fly-out for the MQ-9 / Hellfire segment (no bpy imports).

Two sets:
  * the air set    - the Reaper sits at the origin of its own frame, flying along +X at U m/s, ALT above the desert;
  * the target set - the pickup stands at the origin, long axis along Y; the missile arrives travelling towards +X.
Time base: t = seconds after the rocket motor ignites; the missile strikes at t = T_HIT.

Fly-out: the missile follows a smooth prescribed path from the launch point (leaving level, along the aircraft's
heading) to the target (arriving a few degrees steeper than the line of sight).  Along that path its speed comes
from a point-mass model: a boost that reaches about Mach 1.3 at burn-out (the published top speed), then drag and
gravity.  It is an illustration, not a guidance simulation.
"""
import math
import numpy as np

FPS = 24
MASTER_DT = 1.0 / 120.0
G = 9.81

# ---- engagement (see README for sources)
ALT = 6096.0                 # 20,000 ft above the ground
RANGE = 4600.0               # ground distance at launch  -> slant range about 7.6 km (4.7 miles)
U = 87.0                     # Reaper cruise, 169 kt
SLANT = math.hypot(ALT, RANGE)
LOS = math.atan2(ALT, RANGE)
DIVE = LOS + math.radians(5.0)

# ---- AGM-114R
M_LEN = 1.63; M_DIA = 0.178; M_SPAN = 0.33
M_MASS0 = 49.0; M_MASS1 = 40.5          # launch / burnt-out (the motor holds roughly 8.5 kg of propellant - estimate)
T_BURN = 2.9
A_THRUST = 132.0                         # m/s2 while the motor burns (about 13 g; chosen to reach ~Mach 1.3 at burn-out)
WARHEAD = 9.0                            # kg (20 lb multi-purpose warhead)

# ---- published effect radii (Chamayou, "A Theory of the Drone"; repeated by the BBC)
KILL_R = 15.0
WOUND_R = 20.0
M67_R = 15.0; H155_R = 50.0

# ---- target
HIT = np.array([0.0, 0.0, 1.30])         # where the missile meets the pickup (rear of the cab)
TRUCK_V = 14.0                           # m/s on the track (50 km/h)
BRAKE = 3.2                              # s

def _hermite(u, p0, m0, p1, m1):
    u = np.asarray(u)[..., None]
    return (2 * u ** 3 - 3 * u ** 2 + 1) * p0 + (u ** 3 - 2 * u ** 2 + u) * m0 + (-2 * u ** 3 + 3 * u ** 2) * p1 + (u ** 3 - u ** 2) * m1

_P0 = np.array([-RANGE, 0.0, ALT]); _M0 = np.array([5200.0, 0.0, 0.0]); _M1 = 6500.0 * np.array([math.cos(DIVE), 0.0, -math.sin(DIVE)])
_UU = np.linspace(0, 1, 6001)
PATH = _hermite(_UU, _P0, _M0, HIT, _M1)                      # (n, 3)
_SEG = np.linalg.norm(np.diff(PATH, axis=0), axis=1)
PATH_S = np.concatenate([[0.0], np.cumsum(_SEG)]); PATH_LEN = float(PATH_S[-1])
_TAN = np.gradient(PATH, PATH_S, axis=0); _TAN /= np.linalg.norm(_TAN, axis=1, keepdims=True)

def path_at(s):
    """Position and unit tangent at arc length s (clamped)."""
    s = float(np.clip(s, 0.0, PATH_LEN))
    p = np.array([np.interp(s, PATH_S, PATH[:, k]) for k in range(3)]); d = np.array([np.interp(s, PATH_S, _TAN[:, k]) for k in range(3)])
    return p, d / np.linalg.norm(d)

def _cd(mach):
    return float(np.interp(mach, [0.0, 0.8, 0.95, 1.05, 1.3, 2.0], [0.30, 0.31, 0.42, 0.56, 0.52, 0.44]))

def _fly(dt=0.002):
    A = math.pi * M_DIA ** 2 / 4; s = 0.0; v = U; t = 0.0; out = [(t, s, v)]
    while s < PATH_LEN:
        p, d = path_at(s); z = p[2]
        rho = 1.225 * math.exp(-max(z, 0) / 8500.0); c = 340.3 - 0.0040 * min(max(z, 0), 11000)
        m = M_MASS0 + (M_MASS1 - M_MASS0) * min(t / T_BURN, 1.0)
        a = (A_THRUST if t < T_BURN else 0.0) - 0.5 * rho * v * v * A * _cd(v / c) / m - G * d[2]
        v += a * dt; s += v * dt; t += dt; out.append((t, s, v))
    a_ = np.array(out); f = (PATH_LEN - a_[-2, 1]) / (a_[-1, 1] - a_[-2, 1]); a_[-1] = a_[-2] + (a_[-1] - a_[-2]) * f
    return a_

FLY = _fly()
T_HIT = float(FLY[-1, 0]); V_HIT = float(FLY[-1, 2]); V_MAX = float(FLY[:, 2].max())
T_STOP = T_HIT - 8.0                     # the pickup comes to rest

def s_of(t):
    return float(np.interp(t, FLY[:, 0], FLY[:, 1]))
def v_of(t):
    return float(np.interp(t, FLY[:, 0], FLY[:, 2]))

def missile_state(t):
    """Target set: position of the missile's nose, unit direction and speed at time t (0 <= t <= T_HIT)."""
    p, d = path_at(s_of(t)); return p, d, v_of(t)

def missile_rel(t):
    """Air set: displacement of the missile from its place on the rail, in the aircraft's (moving) frame, and its direction."""
    if t <= 0:
        return np.zeros(3), np.array([1.0, 0, 0])
    p, d = path_at(s_of(t)); return p - _P0 - np.array([U * t, 0, 0]), d

def smoke_rel(tau, t):
    """Air set: where the exhaust released at time tau sits at time t (it stays put in the air; the aircraft flies on)."""
    p, d = path_at(s_of(tau)); return p - _P0 - np.array([U * t, 0, 0]) - d * M_LEN * 0.0

def truck_y(t):
    """Target set: the pickup drives up the track (along +Y) and stops at the origin at T_STOP."""
    if t >= T_STOP:
        return 0.0
    r = T_STOP - t
    if r <= BRAKE:
        return -0.5 * (TRUCK_V / BRAKE) * r * r
    return -(0.5 * TRUCK_V * BRAKE + TRUCK_V * (r - BRAKE))

def aircraft_pos(t):
    """Target set: where the Reaper is at time t (it keeps flying level along +X)."""
    return _P0 + np.array([U * t, 0, 0])

if __name__ == "__main__":
    print("slant %.0f m  LOS %.1f deg  dive %.1f deg  path %.0f m" % (SLANT, math.degrees(LOS), math.degrees(DIVE), PATH_LEN))
    print("T_HIT %.2f s  V_MAX %.0f m/s  V_HIT %.0f m/s  v(burnout) %.0f" % (T_HIT, V_MAX, V_HIT, v_of(T_BURN)))
    for t in (0.1, 0.3, 0.5, 1.0, 2.0):
        r, d = missile_rel(t); print("t=%.1f rel=(%.2f, %.2f, %.2f) dive=%.2f deg" % (t, r[0], r[1], r[2], -math.degrees(math.asin(d[2]))))
    for td in (-3, -1, -0.1):
        p, d, v = missile_state(T_HIT + td); print("td=%.1f pos=(%.0f, %.0f) v=%.0f" % (td, p[0], p[2], v))
