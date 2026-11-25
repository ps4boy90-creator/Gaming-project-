"""Shared numbers, the bomb's fall under its parachute and the size of what the burst does, for the C-130 / BLU-82
segment (no bpy imports).

Site coordinates: the bomb's fuze extender touches the ground at the origin; +Z is up; the aircraft flies along +X.
Times: t = seconds after the bomb leaves the ramp; td = seconds after the burst.
The place is invented.  Sources for the figures are in the README.
"""
import math
import numpy as np

FPS = 24
G = 9.81
FT = 0.3048; LB = 0.45359237; KT = 0.514444; IN = 0.0254
# ---- BLU-82/B (sources: see README)
DIA = 54.0 * IN                                        # 4 ft 6 in across
LEN = 141.6 * IN                                       # the bomb without its fuze extender (11 ft 6 in in the 1970 report)
EXT = 36.0 * IN                                        # the M1A1 fuze extender: it fires the bomb three feet above the ground
MASS = 15000.0 * LB                                    # filled
M_RIG = 20000.0 * LB                                   # rigged for the drop, with cradle and platform
FILL = 12600.0 * LB                                    # ammonium nitrate and aluminium slurry
TNT_REL = 0.82                                         # "roughly 82% as powerful as TNT"
CONE_L = 0.95                                          # length of the conical nose (from photographs)
NOSE_R = 0.14                                          # radius of its blunt front
D_EXT = 15.0 * FT; D_STAB = 24.0 * FT                  # the extraction parachute and the slotted stabilising parachute
# ---- the drop
H_REL = 6000.0 * FT                                    # above the ground: the usual height
V_REL = 150.0 * KT                                     # true airspeed
PUBLISHED = dict(tof=(26.0, 27.0), v_fps=338.0, throw_ft=2700.0)   # time from release, rate of fall (AFI 11-231), forward travel (Armament Museum diagram)

def _air(h):
    T = 288.15 - 0.0065 * h; return 1.225 * (T / 288.15) ** 4.256

ELEV = 300.0                                           # height of the ground above the sea (invented site)
# -- out of the aircraft: the extraction parachute drags the load down the rollers and off the ramp
CDS_EXT = 0.55 * math.pi * D_EXT ** 2 / 4              # a ring-slot canopy's drag area (drag coefficient estimated)
HOLD_RUN = 9.0                                         # metres from where the load is locked to the edge of the ramp (estimate)
A_EXT = 0.5 * _air(ELEV + H_REL) * V_REL ** 2 * CDS_EXT / M_RIG       # its acceleration along the floor
T_EXIT = math.sqrt(2.0 * HOLD_RUN / A_EXT); V_OUT = A_EXT * T_EXIT     # seconds from release to the ramp's edge; speed aft, relative to the aircraft, as it leaves
# -- the fall: the stabilising parachute's drag area is set from the published rate of fall
T_CHUTE = 1.5                                          # seconds after leaving the ramp until the stabilising parachute is open and the cradle has gone (estimate)
CDS_BOMB = 0.75 * math.pi * DIA ** 2 / 4               # the drum nose first (estimate)
CDS_STAB = 2.0 * MASS * G / (_air(ELEV) * (PUBLISHED["v_fps"] * FT) ** 2) - CDS_BOMB

def _fall(dt=0.01):
    """Point mass with drag from the edge of the ramp: rows t, x, z, vx, vz (t from leaving the ramp)."""
    x = 0.0; z = H_REL; vx = V_REL - V_OUT; vz = 0.0; t = 0.0; out = [(t, x, z, vx, vz)]
    while z > 0.0:
        k_open = min(max((t - T_CHUTE * 0.4) / (T_CHUTE * 0.6), 0.0), 1.0); cds = (CDS_BOMB * 2.2 + CDS_EXT) * (1.0 - k_open) + (CDS_BOMB + CDS_STAB) * k_open; m = M_RIG + (MASS - M_RIG) * k_open
        v = math.hypot(vx, vz); k = 0.5 * _air(ELEV + z) * cds / m
        vx += -k * v * vx * dt; vz += (-G - k * v * vz) * dt; x += vx * dt; z += vz * dt; t += dt; out.append((t, x, z, vx, vz))
    a, b = np.array(out[-2]), np.array(out[-1]); out[-1] = tuple(a + (b - a) * (a[2] / (a[2] - b[2])))
    return np.array(out)

FALL = _fall()
T_FALL = float(FALL[-1, 0]); TOF = T_EXIT + T_FALL       # seconds of fall from the ramp; seconds from release
THROW = float(FALL[-1, 1]); THROW_REL = THROW + V_REL * T_EXIT          # forward travel from the ramp's edge; from the point of release
V_HIT = float(np.hypot(FALL[-1, 3], FALL[-1, 4])); DIVE = math.degrees(math.atan2(-FALL[-1, 4], FALL[-1, 3]))

T_SEP = 0.6                                            # seconds after leaving the ramp at which the stabilising parachute pulls the bomb off its cradle (estimate)

def _plat(dt=0.01):
    """Cradle and platform once the bomb has left them, still on the extraction parachute: rows t, x, z, vx, vz."""
    i0 = int(np.searchsorted(FALL[:, 0], T_SEP)); t, x, z, vx, vz = FALL[i0]; out = [tuple(FALL[k]) for k in range(i0 + 1)]; m = M_RIG - MASS; cds = CDS_EXT + 5.0
    while z > 0.0:
        v = math.hypot(vx, vz); k = 0.5 * _air(ELEV + z) * cds / m; vx += -k * v * vx * dt; vz += (-G - k * v * vz) * dt; x += vx * dt; z += vz * dt; t += dt; out.append((t, x, z, vx, vz))
    return np.array(out)

PLAT = _plat()

def plat_state(t):
    a = PLAT; tt = min(max(t, 0.0), float(a[-1, 0])); f = lambda k: float(np.interp(tt, a[:, 0], a[:, k]))
    return np.array([f(1) - THROW, 0.0, f(2)]), np.array([f(3), 0.0, f(4)])

def fall_state(t):
    """Site coordinates: where the tip of the fuze extender is and how it moves, t seconds after leaving the ramp."""
    a = FALL; tt = min(max(t, 0.0), T_FALL); f = lambda k: float(np.interp(tt, a[:, 0], a[:, k]))
    return np.array([f(1) - THROW, 0.0, f(2)]), np.array([f(3), 0.0, f(4)])

def plane_pos(t):
    """The edge of the aircraft's ramp, t seconds after the load left it."""
    return np.array([-THROW + V_REL * t, 0.0, H_REL])

# ---- what the burst does
HOB = EXT + LEN / 2                                    # the middle of the bomb above the ground when the extender touches: it comes down nose first
_K = (FILL * TNT_REL / 87.0) ** (1.0 / 3.0)            # radius scaled from the Mk 82's published one by the cube root of the filling, as in segment 07
R_BLAST = 31.0 * _K                                    # 34 kPa (5 psi) reaches (estimate)
R_CLEAR = 40.0                                         # published: an area about 80 m (260 ft) across is cleared
R_DOWN = 1.35 * R_CLEAR                                # trees thrown down a little beyond it (staging, after the photographs)
R_STRIP = 2.0 * R_CLEAR                                # published: the flash burns the foliage out to about twice the usable radius
R_FIRE = 26.0                                          # radius of the fireball (staging)
DENT = (0.3, 4.5)                                      # published for a test: a depression 6 to 12 in deep and 20 to 30 ft across, no crater
ROTOR = 48.0 * FT                                      # a UH-1H's rotor disc, for scale
SAFE = 1500.0                                          # published: friendly troops no nearer than this

if __name__ == "__main__":
    print("release %.0f m (%.0f ft) above the ground at %.0f m/s (%.0f kt)" % (H_REL, H_REL / FT, V_REL, V_REL / KT))
    print("extraction: %.1f m/s2 along the floor; off the ramp %.1f s after release at %.1f m/s aft" % (A_EXT, T_EXIT, V_OUT))
    print("stabilising parachute: drag area %.1f m2 from the published %.0f ft/s (a drag coefficient of %.2f on a 24 ft canopy)" % (CDS_STAB, PUBLISHED["v_fps"], CDS_STAB / (math.pi * D_STAB ** 2 / 4)))
    print("fall from the ramp %.1f s; from release %.1f s (published %.0f to %.0f s)" % (T_FALL, TOF, *PUBLISHED["tof"]))
    print("forward travel %.0f m from the ramp, %.0f m from the point of release (%.0f and %.0f ft; published about %.0f ft)" % (THROW, THROW_REL, THROW / FT, THROW_REL / FT, PUBLISHED["throw_ft"]))
    print("arrives at %.0f m/s (%.0f ft/s), %.0f deg below the horizontal; the aircraft is then %.0f m on and %.2f miles from the burst (published: a little more than a mile)" % (V_HIT, V_HIT / FT, DIVE, V_REL * T_FALL - THROW, math.hypot(V_REL * T_FALL - THROW, H_REL) / 1609.34))
    print("free fall with no parachute and no air: %.1f s, %.0f ft/s" % (math.sqrt(2 * H_REL / G), math.sqrt(2 * G * H_REL) / FT))
    print("burst: middle of the bomb %.1f m above the ground; cleared to %.0f m; trees down to %.0f m; foliage burnt to %.0f m; 5 psi to %.0f m" % (HOB, R_CLEAR, R_DOWN, R_STRIP, R_BLAST))
