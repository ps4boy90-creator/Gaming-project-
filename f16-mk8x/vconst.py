"""Shared geometry, timing and bomb ballistics for the F-16 / Mk 82 / Mk 83 / Mk 84 segment (no bpy imports).

The jet flies level along +X and releases the three bombs in turn.  Time base: t = seconds after the Mk 82 leaves
its rack.  Target frame: bunker A (hit by the Mk 82) stands at the origin; the other two further along the run.
Ballistics: point mass with a small constant drag area (low-drag bombs); an illustration, not a bombing table.
"""
import math
import numpy as np

FPS = 24
G = 9.81
SIM_DT = 1.0 / 60.0            # one sim frame (scene fps 24 x time scale 0.4)
V_JET = 231.5                  # 450 kt
ALT = 1500.0                   # release height above the desert, m (about 4,900 ft)
ORDER = ("mk82", "mk83", "mk84")
REL = {"mk82": 0.0, "mk83": 0.6, "mk84": 1.2}      # release times
STA_Y = 3.05                   # stations 3 / 7

SPEC = {"mk82": dict(L=2.22, D=0.273, mass=227.0, fill=87.0, cda=0.0075, side=1, label="MK 82", lb=500),
        "mk83": dict(L=3.00, D=0.357, mass=447.0, fill=202.0, cda=0.0125, side=-1, label="MK 83", lb=1000),
        "mk84": dict(L=3.28, D=0.458, mass=925.0, fill=429.0, cda=0.0200, side=0, label="MK 84", lb=2000)}
# ---- effects: Mk 82 radii published (GICHD / Ordtech); the others scaled by the cube root of the filling (estimates)
_K = {k: (v["fill"] / 87.0) ** (1.0 / 3.0) for k, v in SPEC.items()}
R_STRUCT = {k: 16.0 * _K[k] for k in SPEC}          # reinforced-concrete buildings destroyed within
R_BLAST = {k: 31.0 * _K[k] for k in SPEC}           # 34 kPa (5 psi) reaches
CRATER = {"mk82": "4.6 – 10.7 m", "mk83": "about 6 – 14 m (est.)", "mk84": "15 m wide, 11 m deep"}     # GICHD; estimate; Wikipedia "Mark 84 bomb"
BUNK = dict(lx=9.0, ly=7.0, h=3.0, wall=0.6, roof=0.8)                    # the bunkers: reinforced-concrete boxes, earth banked on three sides

def _fall(cda, mass, dt=0.002):
    k = 0.5 * 1.1 * cda / mass; x = 0.0; z = ALT; vx = V_JET; vz = -2.0; t = 0.0; out = [(t, x, z, vx, vz)]
    while z > BUNK["h"]:
        v = math.hypot(vx, vz); vx += -k * v * vx * dt; vz += (-G - k * v * vz) * dt; x += vx * dt; z += vz * dt; t += dt; out.append((t, x, z, vx, vz))
    return np.array(out)

TRAJ = {k: _fall(v["cda"], v["mass"]) for k, v in SPEC.items()}
TOF = {k: float(a[-1, 0]) for k, a in TRAJ.items()}; FWD = {k: float(a[-1, 1]) for k, a in TRAJ.items()}
T_HIT = {k: REL[k] + TOF[k] for k in SPEC}
V_HIT = {k: float(np.hypot(a[-1, 3], a[-1, 4])) for k, a in TRAJ.items()}; ANGLE = {k: math.degrees(math.atan2(-a[-1, 4], a[-1, 3])) for k, a in TRAJ.items()}
BUNKER = {k: np.array([V_JET * REL[k] + FWD[k] - FWD["mk82"], SPEC[k]["side"] * STA_Y, 0.0]) for k in SPEC}
SEP = float(BUNKER["mk83"][0] - BUNKER["mk82"][0])

def jet_pos(t):
    """Target frame: the aircraft reference point (it keeps flying level)."""
    return np.array([-FWD["mk82"] + V_JET * t, 0.0, ALT])

def bomb_state(which, t):
    """Target frame: centre of the bomb and its velocity, t seconds after the Mk 82's release."""
    t0 = REL[which]; a = TRAJ[which]; tt = min(max(t - t0, 0.0), TOF[which])
    x = -FWD["mk82"] + V_JET * t0 + np.interp(tt, a[:, 0], a[:, 1]); z = np.interp(tt, a[:, 0], a[:, 2])
    return np.array([x, SPEC[which]["side"] * STA_Y, z]), np.array([np.interp(tt, a[:, 0], a[:, 3]), 0.0, np.interp(tt, a[:, 0], a[:, 4])])

if __name__ == "__main__":
    for k in ORDER:
        print(k, "TOF %.2f s  throw %.0f m  V_HIT %.0f m/s  angle %.1f deg  T_HIT %.2f  bunker x %.0f  R_STRUCT %.0f  R_BLAST %.0f" % (TOF[k], FWD[k], V_HIT[k], ANGLE[k], T_HIT[k], BUNKER[k][0], R_STRUCT[k], R_BLAST[k]))
