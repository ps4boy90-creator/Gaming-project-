"""Shared geometry and timing for the RPG-7 segment (no bpy imports, so sim and render agree).

World frame: the brick wall's front face is the plane x = 0, the wall runs along Y; the shooter
stands at x = SHOOT_X and fires along +X.  Time base: t = seconds after the trigger.
"""
import math
import numpy as np

FPS = 24
MASTER_DT = 1.0 / 240.0          # one sim ("master") frame, both sims

# ---- wall / target
WALL_T = 0.215                   # one-brick-thick wall (two stretcher wythes)
WALL_W = 5.4
WALL_H = 2.4
ZI = 1.30                        # impact height
IMPACT = np.array([0.0, 0.0, ZI])

# ---- launcher (local +X = bore, origin = muzzle face)
TUBE_LEN = 0.950
SEAT = 0.437                     # launcher-x of the rocket's nose tip when loaded
SHOULDER_X = -0.62               # where the tube rests on the shoulder
SHOOT_X = -30.0
SHOULDER = np.array([SHOOT_X, 0.0, 1.47])            # point on the bore axis above the shoulder
AIM = (IMPACT - SHOULDER) / np.linalg.norm(IMPACT - SHOULDER)
MUZZLE = SHOULDER + AIM * (-SHOULDER_X)
BREECH = SHOULDER + AIM * (-TUBE_LEN - SHOULDER_X)
NOSE0 = MUZZLE + AIM * SEAT
DIST = float((0.0 - NOSE0[0]) / AIM[0])              # nose travel to the wall face

# ---- rocket kinematics: booster in the tube -> coast -> sustainer
V_MUZZLE = 115.0
TUBE_RUN = 0.50
T_EXIT = 2 * TUBE_RUN / V_MUZZLE
S_IGN = 11.0                     # sustainer lights about 10 m from the muzzle
T_IGN = T_EXIT + (S_IGN - TUBE_RUN) / V_MUZZLE
ACC = 360.0                      # m/s^2 on the way to ~295 m/s
_tau = (-V_MUZZLE + math.sqrt(V_MUZZLE ** 2 + 2 * ACC * (DIST - S_IGN))) / ACC
T_HIT = T_IGN + _tau
V_HIT = V_MUZZLE + ACC * _tau
SPIN = 2 * math.pi * 7.0         # slow roll from the canted fins / tail turbine (rad/s)

def travel(t):
    """Nose travel along the bore (m) at time t; keeps going 'virtually' after the hit."""
    if t <= 0:
        return 0.0
    if t < T_EXIT:
        return 0.5 * (V_MUZZLE / T_EXIT) * t * t
    if t < T_IGN:
        return TUBE_RUN + V_MUZZLE * (t - T_EXIT)
    tau = t - T_IGN
    return S_IGN + V_MUZZLE * tau + 0.5 * ACC * tau * tau

def speed(t):
    if t <= 0:
        return 0.0
    if t < T_EXIT:
        return V_MUZZLE * t / T_EXIT
    if t < T_IGN:
        return V_MUZZLE
    return V_MUZZLE + ACC * (t - T_IGN)

def nose(t):
    return NOSE0 + AIM * travel(t)

if __name__ == "__main__":
    print("DIST %.2f  T_EXIT %.4f  T_IGN %.4f  T_HIT %.4f  V_HIT %.1f" % (DIST, T_EXIT, T_IGN, T_HIT, V_HIT))
    print("MUZZLE", MUZZLE, "BREECH", BREECH, "NOSE0", NOSE0)
