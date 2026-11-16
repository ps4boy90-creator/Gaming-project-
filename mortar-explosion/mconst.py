"""Shared geometry and timing for the 120 mm mortar segment (no bpy imports, so sim and render agree).

Two sets share one terrain but are shown as two places 2 km apart:
  * the mortar pit  - mortar baseplate centre at (MX, 0), firing along +X;
  * the target      - the round lands at the world origin, next to the ruins, travelling along +X.
Time base: t = seconds after the round strikes the firing pin; it lands at t = T_HIT.

The trajectory is plain drag-free ballistics for the chosen elevation and range.  It is an illustration of
a low-charge shot, not a firing-table solution.
"""
import math
import numpy as np

FPS = 24
MASTER_DT = 1.0 / 120.0            # one sim ("master") frame, both sims
G = 9.81

# ---- weapon (FM 23-90, ch. 7): M298 cannon 69 in, elevation 0710-1510 mils
TUBE_LEN = 1.753                   # ball centre of the base cap -> muzzle face
ELEV = math.radians(1100 * 360.0 / 6400.0)       # 1100 mils = 61.875 deg
ZB = 0.035                         # height of the base-cap ball centre above the ground
MX = -30.0                         # mortar position (pit set)
PIT_X = MX + 1.15                  # env.build() "throw_x": puts the sandbag front wall 2.2 m ahead of the baseplate
BORE = np.array([math.cos(ELEV), 0.0, math.sin(ELEV)])
BALL = np.array([MX, 0.0, ZB])
MUZZLE = BALL + BORE * TUBE_LEN

# ---- round: M934A1 HE, 27.99 in long, 31.2 lb (manufacturer data sheet)
ROUND_LEN = 0.711
SEAT = 0.262                       # bore-x of the round's tail when it rests on the firing pin
HANG = TUBE_LEN - 0.36             # tail position when the round is "hung": tail cone inside, body in the hands
SLIDE_ACC = 0.80 * G * math.sin(ELEV)
T_SLIDE = math.sqrt(2 * (HANG - SEAT) / SLIDE_ACC)
T_RELEASE = -T_SLIDE               # the round is let go at T_RELEASE and strikes the pin at t = 0

# ---- trajectory
RANGE = 2000.0
V0 = math.sqrt(RANGE * G / math.sin(2 * ELEV))
TOF = 2 * V0 * math.sin(ELEV) / G
APEX = (V0 * math.sin(ELEV)) ** 2 / (2 * G)
TUBE_RUN = TUBE_LEN - SEAT         # tail travel until it clears the muzzle
T_EXIT = 2 * TUBE_RUN / V0
T_HIT = TOF
IMPACT = np.array([0.0, 0.0, 0.0])
V_IMP = V0 * np.array([math.cos(ELEV), 0.0, -math.sin(ELEV)])

# ---- effect (FM 23-90 table 7-1: bursting radius 75 m; M67 grenade for comparison: 15 m casualty radius)
BURST_R = 75.0
M67_R = 15.0

def tail_s(t):
    """Bore-x of the round's tail while it is in or just leaving the tube."""
    if t <= T_RELEASE:
        return HANG
    if t < 0:
        return HANG - 0.5 * SLIDE_ACC * (t - T_RELEASE) ** 2
    if t < T_EXIT:
        return SEAT + 0.5 * (V0 / T_EXIT) * t * t
    return TUBE_LEN + V0 * (t - T_EXIT)

def launch_pos(t):
    """World position of the round's tail on the way out (pit set); ballistic once clear of the muzzle."""
    if t < T_EXIT:
        return BALL + BORE * tail_s(t)
    tau = t - T_EXIT
    return MUZZLE + BORE * V0 * tau + np.array([0, 0, -0.5 * G * tau * tau])

def launch_vel(t):
    if t < 0:
        return BORE * 1e-6
    if t < T_EXIT:
        return BORE * (V0 * t / T_EXIT)
    return BORE * V0 + np.array([0, 0, -G * (t - T_EXIT)])

def fall_pos(td):
    """World position of the round's nose td seconds relative to impact (target set, td <= 0)."""
    return IMPACT + V_IMP * td + np.array([0, 0, -0.5 * G * td * td])

def fall_vel(td):
    return V_IMP + np.array([0, 0, -G * td])

if __name__ == "__main__":
    print("ELEV %.2f deg  V0 %.1f m/s  TOF %.1f s  APEX %.0f m  T_SLIDE %.3f  T_EXIT %.4f" % (math.degrees(ELEV), V0, TOF, APEX, T_SLIDE, T_EXIT))
    print("MUZZLE", MUZZLE)
