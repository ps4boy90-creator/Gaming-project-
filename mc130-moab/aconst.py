"""Shared numbers, the bomb's fall and the blast for the MC-130 / GBU-43/B MOAB segment (no bpy imports).

Site coordinates: the point on the valley floor under the burst is the origin; +Z is up; the aircraft flies towards +X,
along the valley, and the bomb falls in the X-Z plane.  Times: t = seconds after the load is released in the aircraft;
tb = seconds after the burst.

Published (Air Force Armament Museum; Air & Space Forces Magazine; af.mil; the Air Force's 2003 legal review of the
weapon; Wikipedia for the exact length): 21,600 lb; 30 ft 1.75 in long, 40.5 in across, 5 ft wide with the fins folded
and 10 ft with them out; 18,700 lb of H6 in a thin aluminium case (the BLU-120/B warhead); GPS and inertial guidance
(KMU-593/B) working four lattice fins, with fixed wings along the body; carried on a cradle on an airdrop platform in
an MC-130 or C-130, pulled out by a drogue parachute, freed from the cradle at once and then falling without a
parachute; guided over about 3 nautical miles.  Yield: about 11 tons of TNT.  Reported, not official: it bursts about
6 ft above the ground.  Used once, at 7.32 pm on 13 April 2017, on a tunnel complex in Achin district, Nangarhar,
Afghanistan; satellite pictures afterwards showed about twenty compounds and the trees round them destroyed and
hardly any crater.

Not published, and chosen here: the release height and speed, the sizes of platform and parachute, the bomb's drag.
The blast figures are calculated (Kinney and Graham's fit for a TNT charge, doubled charge for a burst at the
ground, scaled to the air pressure at the valley's height); they are for open, level ground.
"""
import math
import numpy as np

FPS = 24
G = 9.81
FT = 0.3048; IN = 0.0254; LB = 0.45359237; PSI = 6.894757         # kPa per psi
# ---- the bomb
GBU_L = (30 * 12 + 1.75) * IN           # 9.19 m overall
GBU_D = 40.5 * IN                       # 1.03 m
GBU_M = 21600 * LB                      # 9,798 kg
FILL = 18700 * LB                       # 8,482 kg of H6
CASE_M = 2900 * LB                      # 1,315 kg of aluminium case (Wikipedia)
SPAN_FOLD = 5 * FT; SPAN_OPEN = 10 * FT
YIELD_KG = 11000.0                      # "11 tons of TNT"
HOB = 6 * FT                            # 1.8 m: the height of the burst as reported
N_BUILT = 15
# ---- shape (estimated from photographs of the museum's example; the frame of abomb: middle of the length at 0, nose towards +X)
PROBE_L = 0.42                          # the rod at the nose
NOSE_L = 1.30                           # the cone behind it
AFT_S = 6.55                            # metres behind the tip where the body narrows to the tail section
AFT_D = 0.74
WALL = 0.012                            # skin, from the case's weight (not published)
# ---- how it rides in the aircraft (estimates)
PLAT_L = 24 * FT; PLAT_W = 108 * IN; PLAT_H = 0.10                # a 24 ft airdrop platform
PLAT_M = 1100.0                         # platform and cradle
AXIS_H = PLAT_H + 0.50 + GBU_D / 2      # height of the bomb's axis above the cargo floor
EXTR_D = 28 * FT                        # extraction parachute (a usual size for heavy platforms; the one used is not published)
# ---- the drop (illustrative)
ELEV = 1200.0                           # the valley floor above sea level
H_REL = 20000 * FT - ELEV               # released at 20,000 ft above sea level: 4,900 m above the valley
V_AC = 95.0                             # true air speed (about 140 knots indicated at that height)

def _air(h):
    T = 288.15 - 0.0065 * h; return 1.225 * (T / 288.15) ** 4.256

def _p0(h):
    return 101.325 * (1 - 2.25577e-5 * h) ** 5.25588

# ---- inside the aircraft: the frame of the C-130 model (nose towards +X, z = 0 on the cargo floor, x = X0 - metres aft of the nose)
X0 = 13.0
LOAD_S = 13.3                           # station of the middle of the bomb when it is locked in place
RAMP_S = (19.0, 22.1)                   # hinge and end of the ramp, which is level for the drop
CDA_EXTR = 0.55 * math.pi * (EXTR_D / 2) ** 2
A_SLIDE = 0.5 * _air(ELEV + H_REL) * V_AC ** 2 * CDA_EXTR / (GBU_M + PLAT_M)      # the parachute's pull
T_EXIT = math.sqrt(2 * (RAMP_S[1] - LOAD_S) / A_SLIDE)                           # the middle of the load passes the end of the ramp
V_EXIT = A_SLIDE * T_EXIT
T_SEP = 0.55                            # after the exit: the bomb is freed from the cradle
T_FINS = (0.9, 1.6)                     # the lattice fins swing out
T_EXTR = (-6.0, -5.55, -4.6, -4.0)      # the parachute: let go of its rack, clear of the ramp, line run out, canopy full
CDA_BOMB = 0.95                         # drag area of the bomb with wings and lattice fins, m2 (estimate)

def slide_x(t):
    """Aircraft-frame x of the middle of the bomb while the load runs out along the floor."""
    tt = min(max(t, 0.0), T_EXIT); return X0 - LOAD_S - 0.5 * A_SLIDE * tt * tt

def _fall(plat=False, dt=0.004):
    """Point mass with drag from the end of the ramp.  Rows (tau, x, z, vx, vz), x measured from the exit point."""
    x = 0.0; z = H_REL + AXIS_H; vx = V_AC - V_EXIT; vz = 0.0; tau = 0.0; out = [(tau, x, z, vx, vz)]
    while z > 0.0 and tau < 120.0:
        if tau < T_SEP:
            m = GBU_M + PLAT_M; cda = CDA_EXTR + 2.0
        elif plat:
            m = PLAT_M; cda = CDA_EXTR + 4.0
        else:
            m = GBU_M; cda = CDA_BOMB
        v = math.hypot(vx, vz); k = 0.5 * _air(ELEV + z) * cda / m
        vx += -k * v * vx * dt; vz += (-G - k * v * vz) * dt; x += vx * dt; z += vz * dt; tau += dt; out.append((tau, x, z, vx, vz))
    return np.array(out)

FALL = _fall(); PLAT = _fall(plat=True)
_g = np.arctan2(-FALL[:, 4], FALL[:, 3]); _tip = FALL[:, 2] - GBU_L / 2 * np.sin(_g)       # height of the tip of the nose
_i = int(np.argmax(_tip <= HOB)); _a, _b = FALL[_i - 1], FALL[_i]; _f = (_tip[_i - 1] - HOB) / (_tip[_i - 1] - _tip[_i]); FALL = np.vstack([FALL[:_i], _a + (_b - _a) * _f])
TAU_HIT = float(FALL[-1, 0]); THROW = float(FALL[-1, 1]); V_HIT = float(np.hypot(FALL[-1, 3], FALL[-1, 4])); DIVE = math.degrees(math.atan2(-FALL[-1, 4], FALL[-1, 3]))
T_BURST = T_EXIT + TAU_HIT                                           # seconds after release
Z_BURST = float(FALL[-1, 2])                                         # the middle of the bomb above the ground at the burst
X_EXIT = -THROW                                                       # site x of the end of the ramp when the load leaves it

def ac_pos(t):
    """Site coordinates of the aircraft frame's origin (on the cargo floor) t seconds after release."""
    return np.array([X_EXIT - (X0 - RAMP_S[1]) + V_AC * (t - T_EXIT), 0.0, H_REL])

def _interp(arr, tau):
    tt = min(max(tau, 0.0), float(arr[-1, 0])); f = lambda k: float(np.interp(tt, arr[:, 0], arr[:, k])); return np.array([X_EXIT + f(1), 0.0, f(2)]), np.array([f(3), 0.0, f(4)])

def bomb_state(t):
    """Site coordinates of the middle of the bomb, its velocity and its pitch (radians nose-down) t seconds after release."""
    if t <= T_EXIT:
        p = ac_pos(t) + np.array([slide_x(t), 0.0, AXIS_H]); return p, np.array([V_AC - A_SLIDE * max(t, 0.0), 0.0, 0.0]), 0.0
    tau = t - T_EXIT; p, v = _interp(FALL, tau); gam = math.atan2(-v[2], v[0])
    u = min(max((tau - T_SEP) / 3.5, 0.0), 1.0); u = u * u * (3 - 2 * u)                                                # it noses over into its path once it is free
    wob = math.radians(5.0) * math.exp(-tau / 2.5) * math.sin(2 * math.pi * 0.45 * tau) * min(tau / 0.8, 1.0)
    return p, v, gam * u + wob

def plat_state(t):
    """The platform with the cradle and the parachute, once the bomb has left it."""
    tau = t - T_EXIT; p, v = _interp(PLAT, tau); p[2] -= AXIS_H; return p, v

def fins_open(t):
    tau = t - T_EXIT; u = min(max((tau - T_FINS[0]) / (T_FINS[1] - T_FINS[0]), 0.0), 1.0); return u * u * (3 - 2 * u)

# ---- the blast (calculated; see the note at the top)
P0 = _p0(ELEV)                          # kPa
C0 = 340.3 * math.sqrt((288.15 - 0.0065 * ELEV) / 288.15)
W_EFF = 1.8 * YIELD_KG                  # a burst at the ground: the ground throws most of the lower half back

def overp(r):
    """Peak overpressure in kPa at r metres over open, level ground."""
    z = np.maximum(np.asarray(r, float), 1.0) * (P0 / 101.325) ** (1 / 3) / W_EFF ** (1 / 3)
    return P0 * 808.0 * (1 + (z / 4.5) ** 2) / (np.sqrt(1 + (z / 0.048) ** 2) * np.sqrt(1 + (z / 0.32) ** 2) * np.sqrt(1 + (z / 1.35) ** 2))

def psi(r):
    return overp(r) / PSI

def r_of_psi(p):
    lo, hi = 1.0, 20000.0
    for _ in range(60):
        mid = math.sqrt(lo * hi)
        if psi(mid) > p:
            lo = mid
        else:
            hi = mid
    return math.sqrt(lo * hi)

_R = np.concatenate([np.linspace(0.0, 60.0, 241), np.linspace(60.5, 3000.0, 5880)]); _U = C0 * np.sqrt(1 + 6.0 / 7.0 * overp(np.maximum(_R, 6.0)) / P0)      # speed of the front
_T = np.concatenate([[0.0], np.cumsum(np.diff(_R) / ((_U[1:] + _U[:-1]) / 2))])

def t_front(r):
    """Seconds after the burst at which the blast front reaches r metres."""
    return np.interp(np.asarray(r, float), _R, _T)

def r_front(tb):
    return float(np.interp(max(tb, 0.0), _T, _R))

R_10 = r_of_psi(10.0); R_5 = r_of_psi(5.0); R_2 = r_of_psi(2.0); R_1 = r_of_psi(1.0)
MILE = 1609.344; PSI_MILE = float(psi(MILE))
FB_D = 3.5 * FILL ** (1.0 / 3.0)        # fireball: the usual rule of thumb for a charge of this weight (not a measurement of this bomb)
CLOUD_10S = 300.0                       # the cloud's top ten seconds after the burst, for the staging
# what the pressures mean (general published guidance for blast on buildings; not specific to this bomb):
#   10 psi  heavy concrete buildings badly damaged     5 psi  most ordinary buildings collapse
#    2 psi  roofs and walls of houses badly damaged    1 psi  windows broken, light damage

if __name__ == "__main__":
    print("A_SLIDE %.2f m/s2  T_EXIT %.2f s  V_EXIT %.1f m/s" % (A_SLIDE, T_EXIT, V_EXIT))
    print("TAU_HIT %.2f s  THROW %.0f m  V_HIT %.1f m/s (Mach %.2f)  DIVE %.1f deg  Z_BURST %.2f  T_BURST %.2f" % (TAU_HIT, THROW, V_HIT, V_HIT / C0, DIVE, Z_BURST, T_BURST))
    for tau in (0.3, 0.8, 1.5, 3, 6, 12, 25):
        p, v, th = bomb_state(T_EXIT + tau); pp = plat_state(T_EXIT + tau)[0]; print(tau, np.round(p - ac_pos(T_EXIT + tau), 1), np.round(v, 1), round(math.degrees(th), 1), "plat-bomb", np.round(pp - p, 1))
    print("P0 %.1f kPa  c %.0f m/s  fireball %.0f m" % (P0, C0, FB_D))
    print("radius for 10 / 5 / 2 / 1 psi: %.0f / %.0f / %.0f / %.0f m;  at one mile %.2f psi" % (R_10, R_5, R_2, R_1, PSI_MILE))
    print("psi at", {r: round(float(psi(r)), 2) for r in (30, 50, 100, 150, 200, 300, 500, 1000)})
    print("front at", {r: round(float(t_front(r)), 3) for r in (30, 50, 100, 150, 300, 600, 1000)})
