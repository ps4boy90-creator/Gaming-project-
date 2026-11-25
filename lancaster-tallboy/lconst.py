"""Shared numbers, the bomb's fall, how deep it goes into the ground and the size of what follows, for the
Lancaster / Tallboy segment (no bpy imports).

Site coordinates: the bomb meets the ground at the origin; +Z is up; the bomb travels in the X-Z plane.
Times: t = seconds after release; tp = seconds after the nose touches the ground; the charge fires at tp = FUZE_DELAY.

The target is an invented German army depot of 1944 on open ground.  How deep the bomb goes before its fuze fires
is calculated with the Young / Sandia penetration equations (SAND97-2426); the crater's width is the published one.
"""
import math
import numpy as np

FPS = 24
G = 9.81
FT = 0.3048; LB = 0.45359237; MPH = 0.44704
# ---- Tallboy: Bomb, H.E., M.C., 12,000 lb (sources: see README)
TB_L = 21.0 * FT                                       # 21 ft overall (6.40 m)
TB_D = 38.0 * 0.0254                                   # 38 in across the body (0.965 m)
TB_M = 12000.0 * LB                                    # about 12,000 lb (5,443 kg)
FILL = 5200.0 * LB                                     # 5,200 lb of Torpex D1 (2,359 kg)
CASE_L = 10.0 * FT                                     # the steel case: some 10 ft (3.05 m); the rest is the light-alloy tail
TAIL_L = TB_L - CASE_L
FIN_CANT = 5.0                                         # the four fins are set at 5 degrees so that the bomb spins as it falls
FUZE_DELAY = 0.5                                       # three No. 58 tail pistols; delays of 0.5 s and 11 s are recorded for Tallboys (USSBS, Brest)
SPIN_RPM = 300.0                                       # published spin at impact (OP 1665)
PUBLISHED = dict(v_fps=1097.0, tof=37.0, ruby_m=1.70)   # OP 1665: 1,097 ft/s from 18,000 ft at 200 mph; 37 s of fall (BCMC); Project Ruby: 5 ft 7 in into concrete
# ---- the release: a Lancaster level 18,000 ft above the target at 200 mph (the case given in OP 1665)
H_REL = 18000.0 * FT; TARGET_ELEV = 60.0

def _air(h):
    T = max(288.15 - 0.0065 * h, 216.65); return 1.225 * (T / 288.15) ** 4.256 if h < 11000 else 0.3639 * math.exp(-(h - 11000) / 6341.6), math.sqrt(1.4 * 287.05 * T)

V_REL = 200.0 * MPH

def cd(M):
    """Drag coefficient on the body's frontal area: a very clean shape, with the usual rise towards Mach 1 (estimated)."""
    return 0.10 + 0.24 * min(max((M - 0.82) / 0.20, 0.0), 1.0) ** 1.5

def _fall(dt=0.005):
    """Point mass with drag, no steering: the Tallboy was unguided.  Rows: t, x, z, vx, vz."""
    x = 0.0; z = H_REL; vx = V_REL; vz = 0.0; t = 0.0; out = [(t, x, z, vx, vz)]; A = math.pi * TB_D ** 2 / 4
    while z > 0.0:
        rho, a = _air(TARGET_ELEV + z); v = math.hypot(vx, vz); k = 0.5 * rho * cd(v / a) * A / TB_M
        vx += -k * v * vx * dt; vz += (-G - k * v * vz) * dt; x += vx * dt; z += vz * dt; t += dt; out.append((t, x, z, vx, vz))
    a, b = np.array(out[-2]), np.array(out[-1]); out[-1] = tuple(a + (b - a) * (a[2] / (a[2] - b[2])))           # end exactly on the ground
    return np.array(out)

FALL = _fall()
TOF = float(FALL[-1, 0]); THROW = float(FALL[-1, 1]); V_HIT = float(np.hypot(FALL[-1, 3], FALL[-1, 4])); DIVE = math.degrees(math.atan2(-FALL[-1, 4], FALL[-1, 3]))
MACH_HIT = V_HIT / _air(TARGET_ELEV)[1]
U = np.array([math.cos(math.radians(DIVE)), 0.0, -math.sin(math.radians(DIVE))])     # unit vector along the bomb's path at impact
sinD = math.sin(math.radians(DIVE))
# The spin: the offset fins turn the bomb faster as it gathers speed; the published figure is 300 rpm at impact.
def _spin(dt=0.01, tau=1.2):
    """Angle turned (rad) against time: the rate follows the bomb's speed with a lag of a few seconds, to SPIN_RPM at impact."""
    w = 0.0; a = 0.0; out = [(0.0, 0.0, 0.0)]; t = 0.0; w_hit = SPIN_RPM * 2 * math.pi / 60.0
    while t < TOF:
        v = float(np.hypot(np.interp(t, FALL[:, 0], FALL[:, 3]), np.interp(t, FALL[:, 0], FALL[:, 4]))); w += (w_hit * v / V_HIT - w) * dt / tau; a += w * dt; t += dt; out.append((t, a, w))
    return np.array(out)

SPIN = _spin(); RPM_HIT = float(SPIN[-1, 2]) * 60.0 / (2 * math.pi)

def spin_angle(t):
    return float(np.interp(min(max(t, 0.0), TOF), SPIN[:, 0], SPIN[:, 1]))

def fall_state(t):
    """Site coordinates: the point of the nose and the velocity t seconds after release (the nose reaches the origin at TOF)."""
    a = FALL; tt = min(max(t, 0.0), TOF); f = lambda k: float(np.interp(tt, a[:, 0], a[:, k]))
    return np.array([f(1) - THROW, 0.0, f(2)]), np.array([f(3), 0.0, f(4)])

def jet_pos(t):
    return np.array([-THROW + V_REL * t, 0.0, H_REL])

# ---- the Young / Sandia penetration equations, SI form (D in metres, V in m/s, mass in kg, area in m2)
NOSE_L = 1.45                                          # length of the ogival nose (from drawings; estimated)
N_NOSE = 0.18 * NOSE_L / TB_D + 0.56

def young_depth(S, V, N=N_NOSE, m=TB_M, d=TB_D):
    k = S * N * (m / (math.pi * d * d / 4)) ** 0.7
    return 0.000018 * k * (V - 30.5) if V >= 61.0 else 0.0008 * k * math.log(1.0 + 2.15e-4 * V * V)

def s_concrete(thick, fc_psi=5000.0, steel_pct=2.0, cure_yr=1.0, d=TB_D):
    tc = min(thick / d, 6.0); return 0.085 * (11.0 - steel_pct) * (cure_yr * tc) ** -0.06 * (5000.0 / fc_psi) ** 0.3

# ---- the ground (invented site): moist clay and loam
S_SOIL = 7.0
D_PATH = young_depth(S_SOIL, V_HIT); T_STOP = 2.0 * D_PATH / V_HIT          # distance along its path until it stops, and how long that takes

def pen_state(tp):
    """Distance of the nose along the path below the surface (m) and the speed (m/s), tp seconds after it touches."""
    if tp <= 0:
        return V_HIT * tp, V_HIT
    if tp >= T_STOP:
        return D_PATH, 0.0
    return V_HIT * tp * (1.0 - tp / (2.0 * T_STOP)), V_HIT * (1.0 - tp / T_STOP)

S_BURST, V_BURST = pen_state(FUZE_DELAY)
CHARGE_BACK = 1.70                                     # the middle of the filling lies about this far behind the tip of the nose
BURST = U * (S_BURST - CHARGE_BACK)                    # the middle of the charge when it fires
DEPTH_BURST = -float(BURST[2])
# ---- what the burst does
CRATER_R = 50.0 * FT; CRATER_PUB_D = 80.0 * FT         # published: a crater 100 ft across and 80 ft deep
CRATER_D = 9.0                                         # the open crater as drawn (the published depth includes the broken ground beneath it)
_K = (FILL / 87.0) ** (1.0 / 3.0)                      # radii scaled from the Mk 82's published ones by the cube root of the filling, as in segment 07
R_STRUCT = 16.0 * _K                                   # reinforced-concrete buildings destroyed within (estimate)
R_BLAST = 31.0 * _K                                    # 34 kPa (5 psi) reaches (estimate, for a burst at the surface)
R_MK84 = 31.0 * (428.0 / 87.0) ** (1.0 / 3.0)          # the same radius for a 2,000 lb Mk 84, for comparison
TNT_EQ = FILL * 1.5                                    # Torpex is about half as powerful again as TNT, weight for weight

if __name__ == "__main__":
    print("release %.0f m (%.0f ft) up at %.0f m/s (%.0f mph)   fall %.1f s   throw %.0f m" % (H_REL, H_REL / FT, V_REL, V_REL / MPH, TOF, THROW))
    print("impact %.0f m/s (%.0f ft/s, %.0f mph, %.0f km/h, Mach %.2f) at %.1f deg; spin %.0f rpm" % (V_HIT, V_HIT / FT, V_HIT / MPH, V_HIT * 3.6, MACH_HIT, DIVE, RPM_HIT))
    print("soil S %.1f, N %.3f: stops after %.1f m along its path (%.1f m down) in %.0f ms; charge fires at %.0f ms, %.1f m down" % (S_SOIL, N_NOSE, D_PATH, D_PATH * sinD, T_STOP * 1e3, FUZE_DELAY * 1e3, DEPTH_BURST))
    print("the same bomb into 5 m of reinforced concrete: %.1f m (Project Ruby, 1946: 1.7 m)" % (young_depth(s_concrete(5.0), V_HIT) * sinD))
    print("crater %.0f m across (published); R_STRUCT %.0f m  R_BLAST %.0f m  (Mk 84: %.0f m)  scaled depth of burst %.2f m/kg^1/3" % (2 * CRATER_R, R_STRUCT, R_BLAST, R_MK84, DEPTH_BURST / TNT_EQ ** (1 / 3)))
