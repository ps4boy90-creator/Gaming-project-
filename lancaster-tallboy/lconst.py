"""Shared numbers, the bomb's fall, how deep it goes into the ground and the size of what follows, for the
Lancaster / Tallboy segment and, with LANC_BOMB=grandslam in the environment, the Lancaster / Grand Slam segment
(no bpy imports).

Site coordinates: the bomb meets the ground at the origin; +Z is up; the bomb travels in the X-Z plane.
Times: t = seconds after release; tp = seconds after the nose touches the ground; the charge fires at tp = FUZE_DELAY.

The target is an invented German army depot of 1944 on open ground.  How deep the bomb goes before its fuze fires
is calculated with the Young / Sandia penetration equations (SAND97-2426); the crater's width is the published one.
"""
import math, os
import numpy as np

FPS = 24
G = 9.81
FT = 0.3048; LB = 0.45359237; MPH = 0.44704
# ---- the two bombs (sources: see each segment's README).  Every other module reads the chosen one through the names below.
BOMB = os.environ.get("LANC_BOMB", "tallboy").lower()
_SPEC = {
    "tallboy": dict(                                   # Bomb, H.E., M.C., 12,000 lb
        name="Tallboy", length=21.0 * FT, dia=38.0 * 0.0254, mass=11885.0 * LB, fill=5200.0 * LB,   # OP 1665: 21 ft; 3 ft 2 in; 11,885 lb all up; about 5,200 lb of Torpex
        case=(10.0 + 4.0 / 12.0) * FT,                 # body 10 ft 4 in; the light-alloy tail is the other 10 ft 8 in
        tail_w=42.0 * 0.0254,                          # across the fins: 3 ft 6 in (OP 1665), a little more than the body
        nose=1.65, charge_back=1.75,                   # length of the ogival nose (measured off IWM CH 15363 and CH 15369); the middle of the filling behind the tip (estimated)
        h_rel=18000.0 * FT, v_rel=200.0 * MPH,         # the release: level, 18,000 ft above the target at 200 mph (the case given in OP 1665)
        spin=300.0,                                    # published spin at impact (OP 1665)
        fuze=0.5,                                      # delays of 0.5 s and 11 s are recorded for Tallboys (USSBS, Brest)
        crater_r=50.0 * FT, crater_pub_d=80.0 * FT,    # published: a crater 100 ft across and 80 ft deep
        crater_d=9.0,                                  # the open crater as drawn (the published depth includes the broken ground beneath it)
        r_brick=120.0 * FT,                            # brick wall-bearing buildings demolished to about 120 ft by a burst at ground level (von Karman, NDRC)
        published=dict(v_fps=1097.0, tof=37.0, ruby_m=1.70)),   # OP 1665: 1,097 ft/s; 37 s of fall (BCMC); Project Ruby: 5 ft 7 in into concrete
    "grandslam": dict(                                 # Bomb, H.E., M.C., 22,000 lb (OP 1665 unless noted)
        name="Grand Slam", length=(25.0 + 5.0 / 12.0) * FT, dia=46.0 * 0.0254, mass=22400.0 * LB, fill=9135.0 * LB,   # 25 ft 5 in; 3 ft 10 in; 22,400 lb all up; 9,135 lb of Torpex (BBMF; 9,200 lb in Flower)
        case=12.5 * FT,                                # body 12 ft 6 in; the 13 ft 4 in tail overlaps it by 5 in
        tail_w=52.0 * 0.0254,                          # 4 ft 4 in across the fins
        nose=1.65 * 46.0 / 38.0, charge_back=1.75 * 25.417 / 21.0,   # the same proportions as the Tallboy's
        h_rel=12000.0 * FT, v_rel=200.0 * MPH,         # the first one, at Bielefeld on 14 March 1945, was released at 11,965 ft; 200 mph was the usual bombing speed
        spin=60.0,                                     # published spin at impact (OP 1665)
        fuze=11.0,                                     # the delay used at Bielefeld and Arnsberg
        crater_r=62.0 * FT, crater_pub_d=34.0 * FT,    # published for the live trial at Ashley Walk, 13 March 1945: 124 ft across and 34 ft deep
        crater_d=34.0 * FT,
        r_brick=150.0 * FT,                            # brick wall-bearing buildings demolished to about 150 ft by a burst at ground level (von Karman, NDRC)
        published=dict(v_fps=1049.0, tof=35.0, ruby_m=2.34)),   # 1,049 ft/s (Webster & Frankland; height not given); 35 s at Bielefeld; Project Ruby: 7 ft 8 in at 1,150 ft/s
}
SPEC = _SPEC[BOMB]; NAME = SPEC["name"]
TB_L = SPEC["length"]                                  # overall length
TB_D = SPEC["dia"]                                     # across the body
TB_M = SPEC["mass"]
FILL = SPEC["fill"]                                    # Torpex D1
CASE_L = SPEC["case"]                                  # the steel case; the rest is the light-alloy tail
TAIL_L = TB_L - CASE_L
FIN_CANT = 5.0                                         # the four fins are set at 5 degrees so that the bomb spins as it falls
FUZE_REAL = SPEC["fuze"]                               # three No. 58 tail pistols; the delay set
FUZE_DELAY = 0.5                                       # the wait as the film shows and simulates it: the bomb has stopped long before either delay runs out
FUZE_CUT = FUZE_REAL - FUZE_DELAY                      # seconds the film leaves out between the bomb going in and the burst (none for the Tallboy)
TAIL_W = SPEC["tail_w"]
SPIN_RPM = SPEC["spin"]
PUBLISHED = SPEC["published"]
K_L = TB_L / _SPEC["tallboy"]["length"]; K_D = TB_D / _SPEC["tallboy"]["dia"]     # how much longer and fatter than a Tallboy (the two bombs are nearly the same shape)
K_W = (FILL / _SPEC["tallboy"]["fill"]) ** (1.0 / 3.0)     # cube root of the fillings' ratio: the scale of the burst against a Tallboy's
# ---- the release
H_REL = SPEC["h_rel"]; TARGET_ELEV = 60.0

def _air(h):
    T = max(288.15 - 0.0065 * h, 216.65); return 1.225 * (T / 288.15) ** 4.256 if h < 11000 else 0.3639 * math.exp(-(h - 11000) / 6341.6), math.sqrt(1.4 * 287.05 * T)

V_REL = SPEC["v_rel"]

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
NOSE_L = SPEC["nose"]                                 # length of the ogival nose (from drawings; estimated)
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
CHARGE_BACK = SPEC["charge_back"]                      # the middle of the filling lies about this far behind the tip of the nose
BURST = U * (S_BURST - CHARGE_BACK)                    # the middle of the charge when it fires
DEPTH_BURST = -float(BURST[2])
# ---- what the burst does
CRATER_R = SPEC["crater_r"]; CRATER_PUB_D = SPEC["crater_pub_d"]
CRATER_D = SPEC["crater_d"]                            # the open crater as drawn
_K = (FILL / 87.0) ** (1.0 / 3.0)                      # radii scaled from the Mk 82's published ones by the cube root of the filling, as in segment 07
R_STRUCT = SPEC["r_brick"]                             # brick wall-bearing buildings demolished within (published, for a burst at ground level)
R_BLAST = 31.0 * _K                                    # 34 kPa (5 psi) reaches (estimate, for a burst at the surface)
R_MK84 = 31.0 * (428.0 / 87.0) ** (1.0 / 3.0)          # the same radius for a 2,000 lb Mk 84, for comparison
R_TALLBOY = _SPEC["tallboy"]["r_brick"]                # a Tallboy's published radius for brick buildings
R_CMP = R_MK84 if BOMB == "tallboy" else R_TALLBOY     # the comparison circle drawn in the radius shot
TNT_EQ = FILL * 1.5                                    # Torpex is about half as powerful again as TNT, weight for weight

if __name__ == "__main__":
    print(NAME); print("release %.0f m (%.0f ft) up at %.0f m/s (%.0f mph)   fall %.1f s   throw %.0f m" % (H_REL, H_REL / FT, V_REL, V_REL / MPH, TOF, THROW))
    print("impact %.0f m/s (%.0f ft/s, %.0f mph, %.0f km/h, Mach %.2f) at %.1f deg; spin %.0f rpm" % (V_HIT, V_HIT / FT, V_HIT / MPH, V_HIT * 3.6, MACH_HIT, DIVE, RPM_HIT))
    print("soil S %.1f, N %.3f: stops after %.1f m along its path (%.1f m down) in %.0f ms; charge fires after %.1f s, %.1f m down" % (S_SOIL, N_NOSE, D_PATH, D_PATH * sinD, T_STOP * 1e3, FUZE_REAL, DEPTH_BURST))
    print("the same bomb into 5 m of reinforced concrete: %.1f m; at 1,150 ft/s: %.1f m (Project Ruby, 1946: %.2f m)" % (young_depth(s_concrete(5.0), V_HIT) * sinD, young_depth(s_concrete(5.0), 1150 * FT), PUBLISHED["ruby_m"]))
    print("vacuum fall %.1f s, vacuum speed %.0f ft/s" % (math.sqrt(2 * H_REL / G), math.hypot(V_REL, math.sqrt(2 * G * H_REL)) / FT)); print("crater %.0f m across (published); R_STRUCT %.0f m  R_BLAST %.0f m  (Mk 84: %.0f m)  scaled depth of burst %.2f m/kg^1/3" % (2 * CRATER_R, R_STRUCT, R_BLAST, R_MK84, DEPTH_BURST / TNT_EQ ** (1 / 3)))
