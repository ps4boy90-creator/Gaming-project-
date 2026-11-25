"""Shared numbers and the bomb's fall for the C-130 / BLU-82 segment (no bpy imports).

Site coordinates: the point on the jungle floor under the burst is the origin; +Z is up; the aircraft flies towards +X
and the bomb falls in the X-Z plane.  Times: t = seconds after the loadmaster releases the load in the aircraft;
tb = seconds after the burst.

Published figures used here (National Museum of the USAF; Air Force Armament Museum; Air & Space Forces Magazine,
"Herculean Bombers"; AFI 11-231): 15,000 lb bomb, 141.6 in long and 54 in across, a tank of 1/4-inch steel holding
12,600 lb of slurry explosive; a nose fuze on a 38-inch extender so that it bursts just above the ground; delivered
by cargo extraction from a C-130 at 6,000 ft above the ground or more; 26 seconds to fall 6,000 ft under a
stabilising parachute; a clearing about 260 ft across; almost no crater.
"""
import math
import numpy as np

FPS = 24
G = 9.81
FT = 0.3048; IN = 0.0254; LB = 0.45359237
# ---- the bomb
BLU_L = 141.6 * IN                      # 3.60 m, the body
BLU_D = 54.0 * IN                       # 1.37 m (the museum's figure; other lists give 56 in)
BLU_M = 15000 * LB                      # 6,804 kg
FILL = 12600 * LB                       # 5,715 kg of slurry explosive
WALL = 0.25 * IN                        # 6.35 mm steel plate
EXT_L = 38.0 * IN                       # 0.965 m from the nose of the tank to the tip of the fuze
NOSE_L = 1.05                           # length of the conical nose (estimated from photographs)
N_BUILT = 225
# ---- how it rides in the aircraft (sizes of the platform, cradle and parachutes are estimates, see README)
PLAT_L = 3.66; PLAT_W = 108 * IN; PLAT_H = 0.10      # airdrop platform, 12 ft by 108 in
PLAT_M = 450.0                          # platform, cradle and rigging
AXIS_H = PLAT_H + 0.16 + BLU_D / 2      # height of the bomb's axis above the cargo floor
EXTR_D = 15 * FT                        # 15 ft extraction parachute (published)
STAB_D = 4.4                            # stabilising parachute: sized here so that the fall takes the published 26 s
# ---- the result (published)
LZ_D = 260 * FT                         # 79 m clearing
PSI_GZ = 1000.0                         # overpressure near the centre, lb per square inch
DIP_D = (20 * FT, 30 * FT); DIP_H = (6 * IN, 12 * IN)   # the dish left in the ground at the 1969 test
TREE_H = 150 * FT; TREE_D = 4 * FT      # "trees as large as 4 feet in diameter and 150 feet tall"
# ---- the drop (illustrative within the published limits)
ELEV = 600.0                            # the jungle floor above sea level
H_REL = 6000 * FT                       # 1,829 m above the ground
V_AC = 77.0                             # true air speed, about 140 knots indicated at that height (a usual heavy-drop speed)
FALL_TIME = 26.0                        # from leaving the ramp to the burst (published)

def _air(h):
    T = 288.15 - 0.0065 * h; return 1.225 * (T / 288.15) ** 4.256

# ---- inside the aircraft: frame with the nose towards +X, z = 0 on the cargo floor, x = X0 - (metres aft of the nose)
X0 = 13.0
LOAD_S = 13.2                           # station of the middle of the bomb when it is locked in place
RAMP_S = (19.0, 22.1)                   # hinge and end of the ramp, which is level for the drop
CDA_EXTR = 0.55 * math.pi * (EXTR_D / 2) ** 2
A_SLIDE = 0.5 * _air(ELEV + H_REL) * V_AC ** 2 * CDA_EXTR / (BLU_M + PLAT_M)      # the extraction parachute's pull
T_EXIT = math.sqrt(2 * (RAMP_S[1] - LOAD_S) / A_SLIDE)                           # the middle of the load passes the end of the ramp
V_EXIT = A_SLIDE * T_EXIT
T_SEP = 0.8                             # after the exit: the webbing is cut and the bomb leaves cradle and platform
T_STAB = (0.9, 1.7)                     # the stabilising parachute fills

def slide_x(t):
    """Aircraft-frame x of the middle of the bomb while the load runs out along the floor."""
    tt = min(max(t, 0.0), T_EXIT); return X0 - LOAD_S - 0.5 * A_SLIDE * tt * tt

def _fall(cda_stab, dt=0.004, mass_b=BLU_M, plat=False):
    """Point mass with drag from the end of the ramp.  Returns rows (tau, x, z, vx, vz), x measured from the exit point."""
    x = 0.0; z = H_REL + AXIS_H; vx = V_AC - V_EXIT; vz = 0.0; tau = 0.0; out = [(tau, x, z, vx, vz)]; A_b = math.pi * BLU_D ** 2 / 4
    while z > 0.0 and tau < 80.0:
        if tau < T_SEP:
            m = BLU_M + PLAT_M; cda = CDA_EXTR + 2.0
        elif plat:
            m = PLAT_M; cda = CDA_EXTR + 3.0
        else:
            u = min(max((tau - T_STAB[0]) / (T_STAB[1] - T_STAB[0]), 0.0), 1.0); m = mass_b; cda = 0.85 * A_b + cda_stab * u * u * (3 - 2 * u)
        v = math.hypot(vx, vz); k = 0.5 * _air(ELEV + z) * cda / m
        vx += -k * v * vx * dt; vz += (-G - k * v * vz) * dt; x += vx * dt; z += vz * dt; tau += dt; out.append((tau, x, z, vx, vz))
    return np.array(out)

def _tune():
    lo, hi = 2.0, 60.0                                                # drag area of the stabilising parachute, m2
    for _ in range(40):
        mid = (lo + hi) / 2
        if _fall(mid)[-1, 0] < FALL_TIME:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2

CDA_STAB = _tune()
FALL = _fall(CDA_STAB); PLAT = _fall(0.0, plat=True)
STAB_D = 2 * math.sqrt(CDA_STAB / (0.62 * math.pi))                  # what that drag area means for a ribbon canopy (Cd about 0.6)
HOB = EXT_L + BLU_L / 2                                              # middle of the bomb above the ground when the fuze touches (it arrives nearly upright)
_i = int(np.argmax(FALL[:, 2] <= HOB)); _a, _b = FALL[_i - 1], FALL[_i]; _row = _a + (_b - _a) * ((_a[2] - HOB) / (_a[2] - _b[2])); FALL = np.vstack([FALL[:_i], _row])
TAU_HIT = float(FALL[-1, 0]); THROW = float(FALL[-1, 1]); V_HIT = float(np.hypot(FALL[-1, 3], FALL[-1, 4])); DIVE = math.degrees(math.atan2(-FALL[-1, 4], FALL[-1, 3]))
T_BURST = T_EXIT + TAU_HIT                                           # seconds after release
X_EXIT = -THROW                                                       # site x of the end of the ramp at the moment the load leaves it

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
    u = min(max((tau - 0.25) / 2.6, 0.0), 1.0); u = u * u * (3 - 2 * u)
    wob = math.radians(11.0) * math.exp(-tau / 2.2) * math.sin(2 * math.pi * 0.55 * tau) * min(tau / 0.5, 1.0)       # it swings under the parachute before it steadies
    return p, v, gam * u + wob

def plat_state(t):
    """The platform with the cradle and the extraction parachute, once the bomb has left it."""
    tau = t - T_EXIT; p, v = _interp(PLAT, tau); p[2] -= AXIS_H; return p, v

def stab_open(t):
    tau = t - T_EXIT; u = min(max((tau - T_STAB[0]) / (T_STAB[1] - T_STAB[0]), 0.0), 1.0); return u * u * (3 - 2 * u)

# ---- the blast on the jungle (staging; only the published end state is fixed: the size of the clearing)
R_LZ = LZ_D / 2                         # 39.6 m: inside this nothing is left standing
R_BARE = 16.0                           # nearest the burst the trees are broken up altogether (estimate)
R_LEAN = 75.0                           # out to here trees are stripped and left leaning (estimate)
R_SHAKE = 260.0                         # the canopy is shaken out to here (estimate)

def t_front(r):
    """Seconds after the burst at which the blast front reaches r metres (staged: fast near the burst, slowing to the speed of sound)."""
    r = np.asarray(r, float); return r / 345.0 * (1.0 - 0.80 * np.exp(-r / 45.0))

if __name__ == "__main__":
    print("A_SLIDE %.2f m/s2  T_EXIT %.2f s  V_EXIT %.1f m/s" % (A_SLIDE, T_EXIT, V_EXIT))
    print("CDA_STAB %.1f m2  STAB_D %.2f m  TAU_HIT %.2f s  THROW %.0f m  V_HIT %.1f m/s  DIVE %.1f deg  HOB %.2f" % (CDA_STAB, STAB_D, TAU_HIT, THROW, V_HIT, DIVE, HOB))
    for tau in (0.5, 1, 2, 4, 8, 15, 25):
        p, v, th = bomb_state(T_EXIT + tau); print(tau, np.round(p, 1), np.round(v, 1), round(math.degrees(th), 1))
    print("plat", [np.round(plat_state(T_EXIT + tau)[0] - bomb_state(T_EXIT + tau)[0], 1) for tau in (1, 2, 4)])
    print("front", [round(float(t_front(r)), 3) for r in (10, 20, 40, 75, 150, 260)])
