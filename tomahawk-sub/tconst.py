"""Shared numbers, timing and flight paths for the submarine-launched Tomahawk segment (no bpy imports).

Three places, each with its own coordinates and clock:
  sea     origin where the missile breaks the surface, z = 0 sea level, the submarine and the missile head +X;
          t = seconds after first motion in the launch tube
  land    low-level cruise over desert hills along +X; tc = seconds into the shot
  target  the factory hall stands at the origin; the missile arrives from -X; td = seconds after detonation

Published figures are marked (src); everything else is an illustration chosen to be physically plausible.
"""
import math
import numpy as np

FPS = 24
G = 9.81
# ---- UGM-109E Tomahawk Block IV (src: US Navy fact file, NAVAIR, TACTOM manual SW820-AP-MMI-010)
LEN = 5.56; LEN_B = 6.25; DIA = 0.52; SPAN = 2.67
MASS = 1315.0; MASS_B = 1588.0
V_CRUISE = 880.0 / 3.6                 # about 550 mph
ALT_CRUISE = (30.0, 50.0)              # metres above ground
BOOST_THRUST = 26700.0; BOOST_BURN = 12.0
WARHEAD = 310.0; FILL = 120.0          # WDU-36/B: about 310 kg with about 120 kg of PBXN-107
RANGE_KM = 1600.0
# ---- effects: Mk 82 radii published (GICHD / Ordtech: 87 kg filling); scaled by the cube root of the filling (estimates)
K = (FILL / 87.0) ** (1.0 / 3.0)
R_STRUCT = 16.0 * K; R_BLAST = 31.0 * K
# ---- Los Angeles class, Flight II (src: US Navy fact file)
SUB_LEN = 109.73; SUB_R = 5.03
SUB_AXIS_Z = -16.0                     # depth of the hull axis: illustrative (launch depth is not published)
SUB_SPEED = 2.6                        # about 5 kt
HATCH_X = 12.2; HATCH_Y = 0.65         # the tube that fires, in the submarine's frame (bow at 0, +X aft)
HATCH_Z = SUB_AXIS_Z + math.sqrt(SUB_R ** 2 - HATCH_Y ** 2)
# ---- the strike (illustrative): flown from the Arabian Sea, as in October 2001
ROUTE_KM = 1200.0
FLIGHT_MIN = ROUTE_KM / (V_CRUISE * 3.6) * 60.0
# ---- launch events, seconds after first motion (order from the TACTOM manual; times illustrative except the ~14 s boost)
T_IGN = 0.62                           # booster lights under water, once clear of the tube
T_WINGS = 7.0                          # inlet cover off, wings out (after the speed check)
T_BURNOUT = T_IGN + BOOST_BURN
T_JETT = T_BURNOUT + 0.7               # booster dropped
T_ENGINE = T_JETT + 0.9                # turbofan running
FIN_TIME = 0.25                        # fins swing 134 degrees in about a quarter of a second (src)

def _gamma(t):
    """Flight-path angle programme (degrees above the horizon) for the boost and the descent to cruise height."""
    pts = [(0.0, 90.0), (2.4, 90.0), (4.5, 72.0), (7.0, 48.0), (10.0, 27.0), (12.6, 14.0), (15.0, 4.0), (18.0, -6.0), (24.0, -9.0), (30.0, -7.0), (36.0, -1.5), (40.0, 0.0), (400.0, 0.0)]
    a = np.array(pts); return float(np.interp(t, a[:, 0], a[:, 1]))

def _launch(dt=0.002, t_end=44.0):
    """Kinematic launch: gas ejection, drag and buoyancy under water, booster thrust along the programmed path."""
    z0 = HATCH_Z - 0.45 - LEN / 2                 # body centre with the nose just under the hatch
    x = 0.0; z = z0; v = 0.0; t = 0.0; out = []; t_broach = None; t_clear = None
    while t <= t_end:
        g = math.radians(_gamma(t)); out.append((t, x, z, v, math.degrees(g)))
        nose = z + LEN / 2 * math.sin(g); tail = z - (LEN / 2 + 0.69) * math.sin(g)
        if z - z0 < 3.2 and t < 0.6:
            a = 52.0                                                               # gas generator in the capsule
        else:
            wet = tail < 0.0
            thrust = BOOST_THRUST * (1.0 if t < T_BURNOUT - 0.4 else max(0.0, (T_BURNOUT - t) / 0.4)) if t >= T_IGN else 0.0
            if t >= T_ENGINE:
                thrust += 3100.0 * min(1.0, (t - T_ENGINE) / 2.0)                  # F415 turbofan, about 700 lbf
            m = (MASS_B if t < T_JETT else MASS) - (150.0 * min(max((t - T_IGN) / BOOST_BURN, 0.0), 1.0) if t < T_JETT else 0.0)
            if wet:
                a = (thrust - 0.5 * 1025.0 * 0.25 * 0.212 * v * v - 2800.0 * math.sin(g)) / (m + 110.0)
            else:
                cda = 0.075 if t < T_WINGS else 0.11
                a = (thrust - 0.5 * 1.15 * cda * v * v) / m - G * math.sin(g)
                if t > 36.0:
                    a += 0.25 * (V_CRUISE - v)                                      # settle at cruise speed
        v = max(v + a * dt, 0.0); x += v * math.cos(g) * dt; z += v * math.sin(g) * dt; t += dt
        if t_broach is None and nose >= 0.0:
            t_broach = t
        if t_clear is None and tail >= 0.0:
            t_clear = t
    return np.array(out), t_broach, t_clear

LAUNCH, T_BROACH, T_CLEAR = _launch()
T_SHROUD = T_CLEAR + 0.35              # wing-slot plugs and shrouds off, fins out, just after it clears the water
APEX = float(LAUNCH[:, 2].max()); T_APEX = float(LAUNCH[int(LAUNCH[:, 2].argmax()), 0])
V_BURNOUT = float(np.interp(T_BURNOUT, LAUNCH[:, 0], LAUNCH[:, 3]))

def launch_state(t):
    """Sea set: centre of the missile body, its velocity and its speed.  Before first motion it rides in the tube."""
    a = LAUNCH; tt = min(max(t, 0.0), a[-1, 0]); x = np.interp(tt, a[:, 0], a[:, 1]); z = np.interp(tt, a[:, 0], a[:, 2]); v = np.interp(tt, a[:, 0], a[:, 3]); g = math.radians(np.interp(tt, a[:, 0], a[:, 4]))
    drift = SUB_SPEED * min(t, T_BROACH + 1.0) if t > 0 else SUB_SPEED * t        # it leaves with the submarine's own way on
    return np.array([x + drift - SUB_SPEED * T_BROACH, 0.0, z]), np.array([max(v, 0.01) * math.cos(g), 0.0, max(v, 0.01) * math.sin(g)]), float(v)

def sub_bow_x(t):
    """Sea set: x of the submarine's bow; the firing hatch is under the origin at the moment of broach."""
    return SUB_SPEED * (t - T_BROACH) + HATCH_X

# ---- terminal dive (target set).  Flown at cruise speed with turns of about 3 g; a 60 degree commanded dive was shown in a Navy test.
DIVE = 55.0; TURN_R = 2000.0; FAC = dict(lx=24.0, ly=12.0, h=6.5, ridge=1.6)
BURST_Z = 2.0                          # the fuze delay lets the warhead go through the sheet roof before it fires

def _terminal(ds=1.0):
    apex = 900.0; pts = [(0.0, 0.0, BURST_Z)]; g = math.radians(-DIVE); x = 0.0; z = BURST_Z; s = 0.0
    while z < apex - TURN_R * (1 - math.cos(math.radians(DIVE))) :              # straight part of the dive, walking back from the target
        x -= math.cos(g) * ds; z -= math.sin(g) * ds; s += ds; pts.append((-s, x, z))
    while g < 0:                                                                 # the push-over, back to level at the apex
        g = min(g + ds / TURN_R, 0.0); x -= math.cos(g) * ds; z -= math.sin(g) * ds; s += ds; pts.append((-s, x, z))
    for _ in range(1500):
        x -= ds; s += ds; pts.append((-s, x, z))
    a = np.array(pts[::-1]); a[:, 0] /= V_CRUISE; return a

TERM = _terminal()

def term_state(td):
    """Target set: body centre and velocity, td seconds after detonation (negative before)."""
    a = TERM; tt = min(max(td, a[0, 0]), 0.0); x = np.interp(tt, a[:, 0], a[:, 1]); z = np.interp(tt, a[:, 0], a[:, 2]); e = 0.01
    x2 = np.interp(min(tt + e, 0.0), a[:, 0], a[:, 1]); z2 = np.interp(min(tt + e, 0.0), a[:, 0], a[:, 2]); x1 = np.interp(tt - e, a[:, 0], a[:, 1]); z1 = np.interp(tt - e, a[:, 0], a[:, 2])
    d = np.array([x2 - x1, 0.0, z2 - z1]); d = d / (np.linalg.norm(d) + 1e-9)
    return np.array([x, 0.0, z]), d * V_CRUISE

T_ROOF = -( (FAC["h"] + 0.8 - BURST_Z) / math.sin(math.radians(DIVE)) ) / V_CRUISE    # when the nose meets the roof

if __name__ == "__main__":
    print("broach %.2f s  clear %.2f s  shroud %.2f  burnout %.2f (v %.0f m/s)  apex %.0f m at %.1f s" % (T_BROACH, T_CLEAR, T_SHROUD, T_BURNOUT, V_BURNOUT, APEX, T_APEX))
    for t in (0.3, 0.6, T_BROACH, 2, 4, 7, 10, 12.6, 14, 16, 20, 30, 40):
        p, v, s = launch_state(t); print("t %5.2f  x %7.1f  z %7.1f  v %6.1f  gamma %5.1f" % (t, p[0], p[2], s, _gamma(t)))
    print("hatch z %.2f  K %.3f  R_STRUCT %.1f  R_BLAST %.1f  flight %.0f min" % (HATCH_Z, K, R_STRUCT, R_BLAST, FLIGHT_MIN))
    print("terminal: starts %.1f s before, apex %.0f m, x0 %.0f m; roof at td %.3f" % (-TERM[0, 0], TERM[:, 2].max(), TERM[0, 1], T_ROOF))
