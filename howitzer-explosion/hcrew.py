"""The gun crew of the howitzer segment: six Ghost Men and everything they handle, as functions of time.

Timeline (t = seconds, the charge fires at t = 0), following the US Marine M777 drill as described by
DVIDS ("On the gun line with cannon cockers"):
  -16.0  cannoneer 2 opens the breech, cannoneer 1 swings the loading tray in
  -15.0  cannoneers 4 and 5 bring the 46.7 kg projectile up and slide it onto the tray
  -10.0  they ram it home with the rammer staff
   -7.0  cannoneer 2 loads the propelling charge, the tray swings out, he closes the breech
   -3.9  cannoneer 1 hooks the lanyard and steps clear; the gunner lays the tube from loading elevation to QE
   -0.5  the section chief drops his arm; cannoneer 1 pulls the lanyard

World frame = gun frame (origin on the ground under the trunnions, +X = direction of fire, +Y = left).
All poses are in world coordinates (the figures sit at the origin).
"""
import math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
from mathutils import Vector, Quaternion
import figure
from util import smoothstep, lerp
import h777, hconst as C
from h777 import aim_quat

D = math.radians
EL_LOAD = D(5.0)
S_TRAY = -0.90                     # base of the projectile once it has been slid up the tray, nose just inside the breech ring
NAMES = ("chief", "gunner", "n1", "n2", "n4", "n5")

def track(t, pts):
    """Piecewise smooth-step interpolation through (time, value) points."""
    if t <= pts[0][0]:
        return np.asarray(pts[0][1], float) if not np.isscalar(pts[0][1]) else pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts[:-1], pts[1:]):
        if t <= t1:
            u = smoothstep(0.0, 1.0, (t - t0) / (t1 - t0))
            return np.asarray(v0, float) * (1 - u) + np.asarray(v1, float) * u if not np.isscalar(v0) else v0 * (1 - u) + v1 * u
    return np.asarray(pts[-1][1], float) if not np.isscalar(pts[-1][1]) else pts[-1][1]

# ----------------------------------------------------------------------------- the gun's moving parts
def elev(t):
    return track(t, [(-3.4, EL_LOAD), (-1.5, C.ELEV)])

def bore_q(t):
    e = elev(t); return aim_quat((math.cos(e), 0.0, math.sin(e)))

def bore_pt(t, s, y=0.0, z=0.0):
    return np.array(Vector(C.TRUN) + bore_q(t) @ Vector((s, y, z)))

def bore_dir(t):
    e = elev(t); return np.array([math.cos(e), 0.0, math.sin(e)])

def breech_angle(t):
    return track(t, [(-16.0, 0.0), (-15.2, h777.BREECH_OPEN), (-4.7, h777.BREECH_OPEN), (-3.95, 0.0)])

def tray_angle(t):
    return track(t, [(-15.7, h777.TRAY_STOW), (-14.9, 0.0), (-5.55, 0.0), (-4.85, h777.TRAY_STOW)])

def breech_pt(t, p):
    """World position of a point given in breech-carrier coordinates."""
    r = C.recoil(t); q = Quaternion((0, 1, 0), breech_angle(t)) @ Vector(p)
    return bore_pt(t, C.S_BREECH - r + q.x, q.y, 0.215 + q.z)

def tray_pt(t, p):
    q = Quaternion((1, 0, 0), tray_angle(t)) @ Vector(p)
    return bore_pt(t, h777.TRAY_PIVOT[0] + q.x, h777.TRAY_PIVOT[1] + q.y, h777.TRAY_PIVOT[2] + q.z)

HANDLE = (-0.16, -0.20, -0.27)                     # breech operating handle (carrier coordinates)
LEVER = (-0.115, 0.185, -0.160)                    # firing lever, on the left of the carrier
TRAY_GRIP = (-0.72, -h777.TRAY_PIVOT[1] + 0.10, -h777.TRAY_PIVOT[2] + 0.03)

# ----------------------------------------------------------------------------- projectile, rammer, charge
def ram_head(t):
    """Bore coordinate of the rammer head."""
    return track(t, [(-10.45, -1.22), (-10.05, -1.52), (-9.42, C.S_SEAT), (-9.28, C.S_SEAT), (-8.35, -1.75), (-7.8, -2.2)])

def shell_state(t):
    """(base point, axis) of the projectile in the gun set."""
    if t >= 0:
        return C.launch_pos(t) - bore_dir(t) * 0.0, bore_dir(t)
    a = bore_dir(t)
    if t < -12.7:
        carry = np.array([-2.72, 0.0, 1.02]); over = bore_pt(t, -1.95, 0, 0.035); on = bore_pt(t, S_TRAY)
        p = track(t, [(-15.0, carry), (-13.7, over), (-12.8, on)])
        return p, a
    s = max(S_TRAY, min(ram_head(t), C.S_SEAT)) if t < -9.42 else C.S_SEAT
    return bore_pt(t, s - (C.recoil(t) if t > 0 else 0.0)), a

def rammer_state(t):
    a = bore_dir(t)
    if t < -8.3:
        return bore_pt(t, ram_head(t)), a
    u = smoothstep(-8.3, -7.6, t)                                    # carried off to the left afterwards
    return bore_pt(t, ram_head(t)) + np.array([-0.3, 1.2, -0.25]) * u, a

def charge_s(t):
    return track(t, [(-7.0, -1.44), (-5.75, C.S_CHAMBER + 0.02)])

def charge_state(t):
    return bore_pt(t, charge_s(t)), bore_dir(t)

LANYARD_HAND = [(-3.95, None), (-3.3, None), (-2.3, np.array([-1.70, 2.20, 1.08])), (-0.17, np.array([-1.70, 2.20, 1.08])), (-0.03, np.array([-1.95, 2.60, 1.02]))]

def lanyard_hand(t):
    if t < -3.3:
        return breech_pt(t, LEVER)
    pts = [(-3.3, breech_pt(-3.3, LEVER))] + [(a, b) for a, b in LANYARD_HAND[2:]]
    return track(t, pts)

# ----------------------------------------------------------------------------- body generator
def stand(x, y, hd, crouch=0.0, lean=0.0, twist=0.0, gait=None, spread=0.13, head=None, side=0.0):
    """A standing/leaning pose at world (x, y) facing heading hd (deg). gait = walking phase (cycles) or None."""
    h = D(hd); f = np.array([math.cos(h), math.sin(h), 0.0]); l = np.array([-math.sin(h), math.cos(h), 0.0]); b = np.array([x, y, 0.0])
    fl = b + l * spread; fr = b - l * spread; pitch_l = pitch_r = 0.0
    if gait is not None:
        ph = 2 * math.pi * gait
        fl = fl + f * 0.26 * math.sin(ph) + np.array([0, 0, max(0.0, 0.10 * math.cos(ph))]); fr = fr - f * 0.26 * math.sin(ph) + np.array([0, 0, max(0.0, -0.10 * math.cos(ph))])
    else:
        fl = fl + f * 0.10 * (lean > 0.15); fr = fr - f * 0.16 * (lean > 0.15)
    pel = b + np.array([0, 0, 0.955 - crouch]) + f * (0.28 * lean) + l * side
    return dict(pelvis=pel, pelvis_yaw=h, lean=f * lean + l * side * 0.5 + np.array([0, 0, 1.0]), chest_yaw=h + D(twist),
                hand_r=b - l * 0.27 + f * 0.05 + np.array([0, 0, 0.82 - crouch]), hand_l=b + l * 0.27 + f * 0.05 + np.array([0, 0, 0.82 - crouch]),
                foot_r=fr, foot_l=fl, elbow_r=-l * 0.6 - f * 0.1 + np.array([0, 0, -0.8]), elbow_l=l * 0.6 - f * 0.1 + np.array([0, 0, -0.8]),
                foot_yaw_r=h - D(8), foot_yaw_l=h + D(8), foot_pitch_r=pitch_r, foot_pitch_l=pitch_l, head_yaw=h if head is None else D(head))

def _attach(pose, hand, target, w=1.0):
    J = figure.solve(pose); s = "r" if hand == "r" else "l"
    sh = J["sho_" + s]; d = np.asarray(target, float) - sh; d /= np.linalg.norm(d) + 1e-9
    tgt = np.asarray(target, float) - d * 0.052                       # the solver places the wrist; the fist sits 5 cm beyond it
    pose["hand_" + s] = np.asarray(pose["hand_" + s]) * (1 - w) + tgt * w

def _win(t, t0, t1, ramp=0.18):
    return smoothstep(t0 - ramp, t0, t) * (1 - smoothstep(t1, t1 + ramp, t))

def _flinch(t):
    return (1 - math.exp(-t / 0.03)) * math.exp(-t / 0.5) if t > 0 else 0.0

def _shell_grip(t, x, side):
    p, a = shell_state(t); ey = np.array([0.0, 1.0, 0.0]); up = np.cross(a, ey); up = up if up[2] > 0 else -up
    return p + a * x + ey * side * 0.062 - up * 0.062

def pose(name, t):
    k = _flinch(t)
    if name == "chief":
        p = stand(-4.9, 2.9, -28, lean=-0.04 * k)
        b = np.array([-4.9, 2.9, 0.0]); f = np.array([math.cos(D(-28)), math.sin(D(-28)), 0]); l = np.array([-f[1], f[0], 0])
        up = b - l * 0.30 + f * 0.10 + np.array([0, 0, 2.02]); dn = b - l * 0.26 + f * 0.62 + np.array([0, 0, 1.05])
        w = _win(t, -1.9, 0.5, 0.35)
        if w > 0:
            p["elbow_r"] = -l * 0.8 + np.array([0, 0, 0.2]); _attach(p, "r", track(t, [(-0.55, up), (-0.36, dn)]), w)
        return p
    if name == "gunner":
        p = stand(-0.66, 1.26, -22, lean=0.10 - 0.05 * k, head=-10)
        c = np.array([-0.32, 0.77, 1.05]); a = 2 * math.pi * 1.6 * smoothstep(-3.4, -1.5, t) * 1.9
        _attach(p, "r", c + 0.15 * np.array([math.cos(a), 0, math.sin(a)])); _attach(p, "l", np.array([-0.52, 0.66, 1.34]))
        return p
    if name == "n1":
        x = track(t, [(-3.3, -1.05), (-2.3, -1.95)]); y = track(t, [(-3.3, 1.28), (-2.3, 2.62)]); hd = track(t, [(-3.3, -82.0), (-2.3, -58.0)])
        g = None if not (-3.3 < t < -2.3) else (t + 3.3) * 1.6
        ln = track(t, [(-16.2, 0.05), (-15.8, 0.30), (-14.7, 0.30), (-14.2, 0.05), (-5.9, 0.05), (-5.5, 0.30), (-3.4, 0.30), (-2.6, 0.02)])
        p = stand(x, y, hd, lean=ln - 0.05 * k, gait=g)
        w = _win(t, -15.9, -14.7) + _win(t, -5.65, -4.75)
        if w > 0:
            _attach(p, "r", tray_pt(t, TRAY_GRIP), min(w, 1.0))
        w = _win(t, -4.15, 9.0, 0.30)
        if w > 0:
            _attach(p, "r", lanyard_hand(t), w)
        return p
    if name == "n2":
        at_breech = track(t, [(-7.6, 1.0), (-7.45, 0.0), (-5.55, 0.0), (-4.85, 1.0)])
        x = lerp(-1.78, -0.92, at_breech); y = lerp(-0.40, -1.22, at_breech); hd = lerp(4.0, 90.0, at_breech)
        g = None if not (-5.55 < t < -4.85) else (t + 5.55) * 1.6
        ln = 0.26 if at_breech > 0.5 else track(t, [(-7.0, 0.12), (-5.8, 0.34)])
        p = stand(x, y, hd, lean=ln - 0.05 * k, gait=g)
        w = _win(t, -16.15, -15.05) + _win(t, -4.8, -3.85)
        if w > 0:
            _attach(p, "r", breech_pt(t, HANDLE), min(w, 1.0))
        w = _win(t, -7.5, -5.7, 0.12)
        if w > 0:
            cp, a = charge_state(t); up = np.array([0, 0, 1.0])
            _attach(p, "r", cp - a * 0.035 + up * 0.0, w); _attach(p, "l", cp + a * 0.42 + up * 0.085 + np.array([0, -0.03, 0]), w)
        return p
    sgn = 1.0 if name == "n4" else -1.0                                # n4 works on the left of the projectile, n5 on the right
    if t < -11.0:                                                      # carry and slide onto the tray
        x = track(t, [(-15.0, -2.42), (-13.7, -1.72), (-12.8, -1.52), (-12.2, -2.05)]); g = None if not (-15.0 < t < -13.7) else (t + 15.0) * 1.25
        y = sgn * track(t, [(-12.8, 0.50), (-12.2, 0.78)])
        ln = track(t, [(-15.0, 0.06), (-13.7, 0.16), (-12.8, 0.36), (-12.2, 0.05)])
        p = stand(x, y, -8.0 * sgn, lean=ln, gait=g, twist=-14.0 * sgn)
        w = 1 - smoothstep(-12.8, -12.5, t)
        if w > 0:
            gx = track(t, [(-13.7, 0.0), (-12.8, 1.0)]); xa = lerp(0.52 if sgn > 0 else 0.60, 0.24 if sgn > 0 else 0.30, gx); xb = lerp(0.22 if sgn > 0 else 0.30, 0.03, gx)
            _attach(p, "l" if sgn > 0 else "r", _shell_grip(t, xa, sgn), w); _attach(p, "r" if sgn > 0 else "l", _shell_grip(t, xb, sgn), w)
        return p
    # ramming: both hold the staff and run the projectile home
    d0, d1 = (1.50, 1.90) if sgn > 0 else (2.20, 2.60)
    hp, a = rammer_state(t)
    held = 1 - smoothstep(-8.3, -8.0, t)
    xb = hp[0] - a[0] * (d0 + d1) / 2 - 0.34
    if t > -8.3:
        xb = track(t, [(-8.3, xb), (-7.4, -2.6 - 0.5 * (sgn < 0))])
    ph = (xb + 5.0) / 0.95
    moving = -10.45 < t < -8.3
    ln = track(t, [(-10.45, 0.12), (-10.05, 0.02), (-9.42, 0.42), (-9.2, 0.30), (-8.3, 0.05)])
    yb = sgn * (0.47 + 0.45 * smoothstep(-8.3, -7.5, t))
    p = stand(xb, yb, -4.0 * sgn, lean=ln - 0.05 * k, gait=ph if moving else None, twist=-10.0 * sgn)
    if held > 0:
        _attach(p, "l" if sgn > 0 else "r", hp - a * d0 + np.array([0, sgn * 0.02, 0.0]), held); _attach(p, "r" if sgn > 0 else "l", hp - a * d1 + np.array([0, sgn * 0.02, 0.0]), held)
    return p
