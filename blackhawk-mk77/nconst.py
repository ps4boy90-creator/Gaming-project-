"""Shared geometry, timing and the canister's fall for the UH-60 / Mk 77 segment (no bpy imports).

One set: the ruined town of segment 04.  The street runs along X between the house fronts at y = +3 and y = -6;
the canister lands in it at the origin, travelling towards +X.  The helicopter flies level along +X.
Time base: t = seconds after release; the canister hits at t = T_HIT.

Fall: a point mass with the drag of a tumbling blunt cylinder (an estimate - the Mk 77 has no fins and tumbles end
over end).  It is an illustration, not a ballistic table.
"""
import math
import numpy as np

FPS = 24
G = 9.81
SIM_DT = 1.0 / 48.0            # one sim frame (scene fps 24 x time scale 0.5)

# ---- helicopter (UH-60L, published figures)
ROTOR_D = 16.36; TAIL_ROTOR_D = 3.35; FUS_LEN = 15.27; HEIGHT = 5.13; FUS_W = 2.36
MAIN_RPS = 258.0 / 60.0; TAIL_RPS = 1214.0 / 60.0
V_HELI = 51.4                  # 100 kt
ALT = 60.0                     # wheels about 200 ft above the street

# ---- Mk 77 Mod 5
B_LEN = 2.06; B_DIA = 0.47; B_MASS = 236.0       # 81.2 in, 18.6 in, 520 lb filled
B_FUEL_L = 284.0                                  # 75 US gal
CDA = 0.42                                        # drag area of the tumbling canister, m2 (estimate)
TUMBLE = 1.25                                     # rev/s once it is tumbling (estimate)

# ---- published fire figures (jet delivery)
FOOT_L = 65.0; FOOT_W = 23.0                      # about 215 x 75 ft ellipse (USMC Basic School handout)
TEMP_LO, TEMP_HI = 800, 1200                      # deg C
# ---- this drop (simulation)
SMEAR_L = 34.0; SMEAR_W = 9.0                     # the street confines it

def _fall(z0, dt=0.002):
    x = 0.0; z = z0; vx = V_HELI; vz = 0.0; t = 0.0; out = [(t, x, z, vx, vz)]
    k = 0.5 * 1.2 * CDA / B_MASS
    while z > B_DIA / 2:
        v = math.hypot(vx, vz); vx += -k * v * vx * dt; vz += (-G - k * v * vz) * dt; x += vx * dt; z += vz * dt; t += dt
        out.append((t, x, z, vx, vz))
    return np.array(out)

REL_Z = ALT + 1.15                                # height of the canister on its pylon
TRAJ = _fall(REL_Z)
T_HIT = float(TRAJ[-1, 0]); FWD = float(TRAJ[-1, 1]); V_IMP = TRAJ[-1, 3:5].copy(); V_HIT = float(np.hypot(*V_IMP)); FALL_ANGLE = math.atan2(-V_IMP[1], V_IMP[0])
PYLON_Y = -2.95                                   # the dropped canister hangs on the right outboard pylon
HELI_Y = -PYLON_Y                                 # so that pylon tracks down the middle of the aim line (y = 0)

def bomb_state(t):
    """Centre of the canister, its velocity and tumble angle (rad, about the pitch axis) at time t >= 0."""
    t = min(max(t, 0.0), T_HIT)
    p = np.array([np.interp(t, TRAJ[:, 0], TRAJ[:, 1]) - FWD, 0.0, np.interp(t, TRAJ[:, 0], TRAJ[:, 2])])
    v = np.array([np.interp(t, TRAJ[:, 0], TRAJ[:, 3]), 0.0, np.interp(t, TRAJ[:, 0], TRAJ[:, 4])])
    ang = 2 * math.pi * TUMBLE * (t - 0.35 * (1 - math.exp(-t / 0.35))) * 1.0
    return p, v, ang

def heli_pos(t):
    """Origin of the helicopter frame (ground point under the rotor mast, lifted to ALT)."""
    return np.array([-FWD + V_HELI * t - STORE_X, HELI_Y, ALT])

STORE_X = 0.15                                    # x of the store centre in the helicopter frame

if __name__ == "__main__":
    print("T_HIT %.2f s  forward throw %.0f m  V_HIT %.0f m/s  angle %.0f deg" % (T_HIT, FWD, V_HIT, math.degrees(FALL_ANGLE)))
