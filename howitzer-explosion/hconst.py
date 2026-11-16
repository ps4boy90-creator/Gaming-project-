"""Shared geometry, timing and ballistics for the 155 mm howitzer segment (no bpy imports).

Two sets, shown as two places about 18 km apart:
  * the gun position - M777 with the ground under its trunnions at the origin, firing along +X;
  * the town         - the shell lands at the origin of that set, travelling along +X.
Time base: t = seconds after the propelling charge fires; the shell lands at t = T_HIT.

Ballistics: a point-mass trajectory with a standard-shaped drag curve.  The drag level is scaled once so
that the model reproduces the published maximum range of the M795 (22.5 km) at the published top-charge
muzzle velocity (827 m/s); the shot shown is then a low-angle solution of that same model for RANGE.
It is an estimate, not a firing-table solution.
"""
import math
import numpy as np

FPS = 24
MASTER_DT = 1.0 / 120.0
G = 9.81

# ---- gun (M777A2): trunnions about 0.8 m ahead of the breech face, 1.05 m above the ground
TRUN = np.array([0.0, 0.0, 1.05])        # trunnion axis
S_BREECH = -0.80                          # bore coordinate (m from the trunnion) of the rear face of the breech ring
S_CHAMBER = -0.65                         # rear of the powder chamber
S_SEAT = 0.23                             # base of the rammed projectile
S_TUBE = 4.80                             # end of the tube proper
S_MUZZLE = 5.25                           # front of the muzzle brake
RECOIL_LEN = 1.25

# ---- projectile M795 (manufacturer brochure) and charge
SHELL_LEN = 0.843                         # 33.2 in with fuze
SHELL_MASS = 46.7                         # 103 lb
CAL = 0.155
V0 = 827.0                                # top charge
MAX_RANGE = 22500.0
RANGE = 18000.0
MACS_LEN = 0.154; MACS_N = 5              # five M232A1 increments

# ---- published effect radii (Human Rights Watch / UN reporting; Article 36 for the M795 "kill radius")
LETHAL_R = 50.0                           # lower bound of the 50-150 m expected lethal radius
CASUALTY_R = 100.0                        # lower bound of the 100-300 m expected casualty radius
M120_R = 75.0; M67_R = 15.0

def _cd(mach):
    return np.interp(mach, [0.0, 0.8, 0.95, 1.05, 1.2, 1.6, 2.0, 2.6], [0.145, 0.150, 0.250, 0.370, 0.345, 0.300, 0.270, 0.240])

def _fly(elev, k, dt=0.02):
    """Integrate until the shell is back at launch height. Returns arrays t, x, z, vx, vz."""
    A = math.pi * CAL * CAL / 4
    x = 0.0; z = 0.0; vx = V0 * math.cos(elev); vz = V0 * math.sin(elev); t = 0.0
    out = [(t, x, z, vx, vz)]
    def acc(z_, vx_, vz_):
        v = math.hypot(vx_, vz_); rho = 1.225 * math.exp(-max(z_, 0) / 8500.0); c = 340.3 - 0.0040 * min(max(z_, 0), 11000)
        f = 0.5 * rho * v * A * k * float(_cd(v / c)) / SHELL_MASS
        return -f * vx_, -f * vz_ - G
    while True:
        ax, az = acc(z, vx, vz)
        xm = x + vx * dt / 2; zm = z + vz * dt / 2; vxm = vx + ax * dt / 2; vzm = vz + az * dt / 2
        ax2, az2 = acc(zm, vxm, vzm)
        x += vxm * dt; z += vzm * dt; vx += ax2 * dt; vz += az2 * dt; t += dt
        out.append((t, x, z, vx, vz))
        if z <= 0 and vz < 0:
            break
    a = np.array(out)
    f = a[-2, 2] / (a[-2, 2] - a[-1, 2]); a[-1] = a[-2] + (a[-1] - a[-2]) * f       # land exactly on z = 0
    return a

def _range(elev, k):
    return _fly(elev, k, 0.05)[-1, 1]

def _solve():
    lo, hi = 0.3, 3.0                                             # drag scale: match the published maximum range
    for _ in range(40):
        k = (lo + hi) / 2
        r = max(_range(math.radians(e), k) for e in (40, 43, 46, 49, 52))
        lo, hi = (k, hi) if r > MAX_RANGE else (lo, k)
    k = (lo + hi) / 2
    lo, hi = math.radians(3), math.radians(40)                    # low-angle solution for RANGE
    for _ in range(50):
        e = (lo + hi) / 2
        lo, hi = (e, hi) if _range(e, k) < RANGE else (lo, e)
    return k, (lo + hi) / 2

DRAG_K, ELEV = _solve()
TRAJ = _fly(ELEV, DRAG_K, 0.01)
TOF = float(TRAJ[-1, 0]); APEX = float(TRAJ[:, 2].max())
V_IMP = TRAJ[-1, 3:5].copy(); V_HIT = float(np.hypot(*V_IMP)); FALL_ANGLE = math.atan2(-V_IMP[1], V_IMP[0])
T_HIT = TOF
BORE = np.array([math.cos(ELEV), 0.0, math.sin(ELEV)])
MUZZLE = TRUN + BORE * S_MUZZLE
T_EXIT = 2 * (S_TUBE - S_SEAT) / V0
IMPACT = np.zeros(3)

def recoil(t):
    """Rearward travel of the recoiling parts (m): out in ~0.12 s, back in battery in ~1.5 s."""
    if t <= 0:
        return 0.0
    out = 1 - math.exp(-t / 0.035)
    back = 1.0 if t < 0.16 else 0.5 * (1 + math.cos(math.pi * min((t - 0.16) / 1.35, 1.0)))
    return RECOIL_LEN * out * back

def base_s(t):
    """Bore coordinate of the projectile base while it is still in the tube."""
    return S_SEAT + 0.5 * (V0 / T_EXIT) * t * t if t > 0 else S_SEAT

def launch_pos(t):
    """World position of the projectile base after firing (gun set)."""
    if t < T_EXIT:
        return TRUN + BORE * base_s(t)
    tau = t - T_EXIT
    return TRUN + BORE * S_TUBE + BORE * V0 * tau + np.array([0, 0, -0.5 * G * tau * tau])

def fall_state(td):
    """Position of the nose and velocity td seconds relative to impact (town set, td <= 0)."""
    t = TOF + td
    x = np.interp(t, TRAJ[:, 0], TRAJ[:, 1]) - RANGE; z = np.interp(t, TRAJ[:, 0], TRAJ[:, 2])
    vx = np.interp(t, TRAJ[:, 0], TRAJ[:, 3]); vz = np.interp(t, TRAJ[:, 0], TRAJ[:, 4])
    return np.array([x, 0.0, z]), np.array([vx, 0.0, vz])

if __name__ == "__main__":
    print("drag scale %.3f  ELEV %.2f deg (%.0f mils)  TOF %.1f s  APEX %.0f m  V_HIT %.0f m/s  fall angle %.1f deg  T_EXIT %.4f"
          % (DRAG_K, math.degrees(ELEV), math.degrees(ELEV) * 6400 / 360, TOF, APEX, V_HIT, math.degrees(FALL_ANGLE), T_EXIT))
    print("MUZZLE", MUZZLE, "range check", TRAJ[-1, 1])
