"""The gun crew of the howitzer segment: six Ghost Men and everything they handle, as functions of time.

Timeline (t = seconds, the charge fires at t = 0), following the US Marine M777 drill as described by
DVIDS ("On the gun line with cannon cockers"):
  -16.0  cannoneer 2 (standing on the left stabiliser arm) opens the breech; the loading tray lies outboard on the right
  -15.6  cannoneers 4 and 5 bring the 46.7 kg projectile up from the right and set it on the tray
  -13.3  cannoneer 5 heaves the tray up and over into line with the bore
  -10.0  cannoneers 4 and 5, between the trails, ram the projectile home with the rammer staff
   -7.0  cannoneer 2 loads the propelling charge; the tray goes back outboard; he closes the breech
   -4.1  cannoneer 1 steps up on the right stabiliser arm, hooks the lanyard and walks clear; the gunner lays the tube from loading elevation to QE
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
SHELL_ON_TRAY = -0.86              # tray-local x of the projectile base (its nose just behind the breech face)
S_TRAY = C.S_BREECH - 0.02 + SHELL_ON_TRAY
TREAD_Z = 0.45                     # top of the stabiliser arms the two cannoneers stand on
NAMES = ("chief", "gunner", "n1", "n2", "n4", "n5")

def track(t, pts):
    """Piecewise smooth-step interpolation through (time, value) points."""
    sc = np.isscalar(pts[0][1])
    if t <= pts[0][0]:
        return pts[0][1] if sc else np.asarray(pts[0][1], float)
    for (t0, v0), (t1, v1) in zip(pts[:-1], pts[1:]):
        if t <= t1:
            u = smoothstep(0.0, 1.0, (t - t0) / (t1 - t0))
            return v0 * (1 - u) + v1 * u if sc else np.asarray(v0, float) * (1 - u) + np.asarray(v1, float) * u
    return pts[-1][1] if sc else np.asarray(pts[-1][1], float)

# ----------------------------------------------------------------------------- the gun's moving parts
def elev(t):
    return track(t, [(-3.4, EL_LOAD), (-1.5, C.ELEV)])

def bore_q(t):
    e = elev(t); return aim_quat((math.cos(e), 0.0, math.sin(e)))

def cradle_pt(t, p):
    """World position of a point given in cradle coordinates (origin on the trunnion axis)."""
    return np.array(Vector(C.TRUN) + bore_q(t) @ Vector(p))

def bore_pt(t, s, y=0.0, z=0.0):
    """World position of a point s metres along the bore axis (y, z offsets across it)."""
    return cradle_pt(t, (s, y, C.BZ + z))

def bore_dir(t):
    e = elev(t); return np.array([math.cos(e), 0.0, math.sin(e)])

def breech_angle(t):
    return track(t, [(-16.0, 0.0), (-15.2, h777.BREECH_OPEN), (-4.7, h777.BREECH_OPEN), (-3.95, 0.0)])

def tray_phi(t):
    return track(t, [(-13.3, h777.TRAY_OUT), (-12.5, h777.TRAY_IN), (-5.55, h777.TRAY_IN), (-4.85, h777.TRAY_STOW)])

def breech_pt(t, p):
    """World position of a point given in breech-carrier coordinates."""
    r = C.recoil(t); q = Quaternion((0, 1, 0), breech_angle(t)) @ Vector(p)
    return bore_pt(t, C.S_BREECH - r + q.x, q.y, 0.215 + q.z)

def tray_pt(t, p):
    """World position of a point given in tray coordinates (origin = front centre of the trough)."""
    return cradle_pt(t, h777.tray_offset(tray_phi(t)) + np.asarray(p, float))

HANDLE = (-0.14, 0.215, -0.20)                     # breech operating handle, on the left of the carrier
LEVER = (-0.115, -0.250, -0.130)                   # firing lever, on the right of the carrier
TRAY_GRIP = (-0.62, -0.07, 0.05)                    # outer lip of the tray

# ----------------------------------------------------------------------------- projectile, rammer, charge
def ram_head(t):
    """Bore coordinate of the rammer head."""
    return track(t, [(-10.45, S_TRAY - 0.34), (-10.05, S_TRAY - 0.66), (-9.42, C.S_SEAT), (-9.28, C.S_SEAT), (-8.35, S_TRAY - 0.85), (-7.8, S_TRAY - 1.3)])

def shell_state(t):
    """(base point, axis) of the projectile in the gun set."""
    a = bore_dir(t)
    if t >= 0:
        return C.launch_pos(t), a
    if t < -12.5:                                                    # carried in from the right, set on the tray, swung over with it
        on = tray_pt(t, (SHELL_ON_TRAY, 0, 0))
        if t >= -13.6:
            return on, a
        return track(t, [(-15.6, on + np.array([0, -1.80, -0.04])), (-14.2, on + np.array([0, 0, 0.06])), (-13.6, on)]), a
    s = max(S_TRAY, min(ram_head(t), C.S_SEAT)) if t < -9.42 else C.S_SEAT
    return bore_pt(t, s), a

def rammer_state(t):
    return bore_pt(t, ram_head(t)), bore_dir(t)

def charge_s(t):
    return track(t, [(-7.0, C.S_BREECH - 0.63), (-5.75, C.S_CHAMBER + 0.02)])

def charge_state(t):
    return bore_pt(t, charge_s(t)), bore_dir(t)

def lanyard_hand(t):
    if t < -3.5:
        return breech_pt(t, LEVER)
    return track(t, [(-3.5, breech_pt(-3.5, LEVER)), (-2.2, np.array([-1.30, -2.42, 1.08])), (-0.17, np.array([-1.30, -2.42, 1.08])), (-0.03, np.array([-1.56, -2.82, 1.02]))])

# ----------------------------------------------------------------------------- body generator
def stand(x, y, hd, crouch=0.0, lean=0.0, twist=0.0, gait=None, spread=0.13, head=None, side=0.0, z0=0.0):
    """A standing/leaning pose at world (x, y, z0) facing heading hd (deg). gait = walking phase (cycles) or None."""
    h = D(hd); f = np.array([math.cos(h), math.sin(h), 0.0]); l = np.array([-math.sin(h), math.cos(h), 0.0]); b = np.array([x, y, z0])
    fl = b + l * spread; fr = b - l * spread
    if gait is not None:
        ph = 2 * math.pi * gait
        fl = fl + f * 0.26 * math.sin(ph) + np.array([0, 0, max(0.0, 0.10 * math.cos(ph))]); fr = fr - f * 0.26 * math.sin(ph) + np.array([0, 0, max(0.0, -0.10 * math.cos(ph))])
    else:
        fl = fl + f * 0.10 * (lean > 0.15); fr = fr - f * 0.16 * (lean > 0.15)
    pel = b + np.array([0, 0, 0.955 - crouch]) + f * (0.28 * lean) + l * side
    return dict(pelvis=pel, pelvis_yaw=h, lean=f * lean + l * side * 0.5 + np.array([0, 0, 1.0]), chest_yaw=h + D(twist),
                hand_r=b - l * 0.27 + f * 0.05 + np.array([0, 0, 0.82 - crouch]), hand_l=b + l * 0.27 + f * 0.05 + np.array([0, 0, 0.82 - crouch]),
                foot_r=fr, foot_l=fl, elbow_r=-l * 0.6 - f * 0.1 + np.array([0, 0, -0.8]), elbow_l=l * 0.6 - f * 0.1 + np.array([0, 0, -0.8]),
                foot_yaw_r=h - D(8), foot_yaw_l=h + D(8), foot_pitch_r=0.0, foot_pitch_l=0.0, head_yaw=h if head is None else D(head))

def _attach(pose, hand, target, w=1.0):
    J = figure.solve(pose); s = "r" if hand == "r" else "l"
    sh = J["sho_" + s]; d = np.asarray(target, float) - sh; d /= np.linalg.norm(d) + 1e-9
    tgt = np.asarray(target, float) - d * 0.052                       # the solver places the wrist; the fist sits 5 cm beyond it
    pose["hand_" + s] = np.asarray(pose["hand_" + s]) * (1 - w) + tgt * w

def _win(t, t0, t1, ramp=0.18):
    return smoothstep(t0 - ramp, t0, t) * (1 - smoothstep(t1, t1 + ramp, t))

def _flinch(t):
    return (1 - math.exp(-t / 0.03)) * math.exp(-t / 0.5) if t > 0 else 0.0

def _shell_grip(t, x, dy):
    p, a = shell_state(t); ey = np.array([0.0, 1.0, 0.0]); up = np.cross(a, ey); up = up if up[2] > 0 else -up
    return p + a * x + ey * dy - up * 0.066

def pose(name, t):
    k = _flinch(t)
    if name == "chief":
        hd = -32.0; b = np.array([-4.4, 2.9, 0.0]); p = stand(b[0], b[1], hd, lean=-0.04 * k)
        f = np.array([math.cos(D(hd)), math.sin(D(hd)), 0]); l = np.array([-f[1], f[0], 0])
        up = b - l * 0.30 + f * 0.10 + np.array([0, 0, 2.02]); dn = b - l * 0.26 + f * 0.62 + np.array([0, 0, 1.05])
        w = _win(t, -1.9, 0.5, 0.35)
        if w > 0:
            p["elbow_r"] = -l * 0.8 + np.array([0, 0, 0.2]); _attach(p, "r", track(t, [(-0.55, up), (-0.36, dn)]), w)
        return p
    if name == "gunner":                                               # left of the saddle, cranking the elevating handwheel
        p = stand(-0.52, 1.50, -63, lean=0.24 - 0.05 * k, head=-40)
        ax = np.array([-0.45, 0.89, 0.0]); ax /= np.linalg.norm(ax); tg = np.array([ax[1], -ax[0], 0.0]); wc = np.array([-0.16, 0.78, 0.88]) + ax * 0.37
        a = 2 * math.pi * 3.0 * smoothstep(-3.4, -1.5, t)
        _attach(p, "r", wc + ax * 0.03 + 0.17 * (tg * math.cos(a) + np.array([0, 0, 1.0]) * math.sin(a))); _attach(p, "l", wc - ax * 0.20 + np.array([0, 0, 0.05]))
        return p
    if name == "n2":                                                   # on the left stabiliser arm beside the breech
        on = track(t, [(-3.75, 1.0), (-2.9, 0.0)])                     # steps down and clear before the gun fires
        x = lerp(0.45, 0.86, on); y = lerp(1.85, 0.80, on); z0 = TREAD_Z * smoothstep(0.35, 0.75, on)
        g = None if not (-3.75 < t < -2.9) else (t + 3.75) * 1.6
        ln = track(t, [(-16.2, 0.30), (-15.1, 0.30), (-14.6, 0.08), (-7.6, 0.10), (-7.3, 0.38), (-6.2, 0.40), (-5.5, 0.30), (-3.95, 0.32), (-3.6, 0.05)])
        cr = track(t, [(-7.6, 0.10), (-7.3, 0.24), (-5.8, 0.24), (-5.4, 0.10)])
        p = stand(x, y, -90.0, lean=ln - 0.05 * k, gait=g, z0=z0, crouch=cr * on)
        w = _win(t, -16.15, -15.05) + _win(t, -4.75, -3.9)
        if w > 0:
            _attach(p, "r", breech_pt(t, HANDLE), min(w, 1.0))
        w = _win(t, -7.6, -6.25, 0.12)
        if w > 0:
            cp, a = charge_state(t); off = track(t, [(-7.0, 0.14), (-6.4, -0.02)])
            _attach(p, "r", cp + a * off + np.array([0, 0.03, 0.0]), w); _attach(p, "l", cp + a * (off + 0.34) + np.array([0, 0.06, 0.07]), w)
        w = _win(t, -5.6, -5.25, 0.10)
        if w > 0:
            _attach(p, "l", tray_pt(t, (-0.25, 0.07, 0.05)), w)
        return p
    if name == "n1":                                                   # waits clear with the lanyard, hooks it on from the right stabiliser arm
        P0 = (-0.90, -2.20); P1 = (0.97, -0.88); P2 = (-1.42, -2.72)
        x = track(t, [(-5.9, P0[0]), (-4.5, P1[0]), (-3.45, P1[0]), (-2.2, P2[0])]); y = track(t, [(-5.9, P0[1]), (-4.5, P1[1]), (-3.45, P1[1]), (-2.2, P2[1])])
        hd = track(t, [(-5.9, 35.0), (-4.9, 35.0), (-4.5, 90.0), (-3.45, 90.0), (-2.2, 58.0)])
        z0 = (TREAD_Z + 0.02) * (smoothstep(-4.8, -4.5, t) - smoothstep(-3.4, -3.1, t))
        g = (t + 5.9) * 1.6 if -5.9 < t < -4.5 else ((t + 3.45) * 1.6 if -3.45 < t < -2.2 else None)
        ln = track(t, [(-4.5, 0.08), (-4.1, 0.38), (-3.5, 0.38), (-3.2, 0.03)])
        cr = track(t, [(-4.4, 0.0), (-4.1, 0.14), (-3.5, 0.14), (-3.3, 0.0)])
        p = stand(x, y, hd, lean=ln - 0.05 * k, gait=g, z0=z0, crouch=cr, spread=0.10)
        w = _win(t, -4.12, 9.0, 0.22)
        if w > 0:
            _attach(p, "r", lanyard_hand(t), w)
        return p
    front = name == "n4"                                               # n4 takes the nose end / is the front rammer
    if t < -11.0:                                                      # bring the projectile up from the right and set it on the tray;
        x = C.S_BREECH + (-0.35 if front else -0.83)                  # n5 then heaves the tray up and over into line with the bore
        back = (-13.5, -12.9) if front else (-12.85, -12.25)
        y = track(t, [(-15.6, -3.10), (-14.2, -1.36), (back[0], -1.36), (back[1], -1.98)])
        g = (t + 15.6) * 1.2 if -15.6 < t < -14.2 else ((t - back[0]) * 1.4 if back[0] < t < back[1] else None)
        ln = track(t, [(-15.6, 0.06), (-14.2, 0.14), (-13.6, 0.26), (-13.3, 0.05)]) if front else track(t, [(-15.6, 0.06), (-14.2, 0.14), (-13.6, 0.26), (-13.3, 0.30), (-12.95, 0.36), (-12.7, 0.05)])
        p = stand(x, y, 90.0, lean=ln, gait=g)
        w = 1 - smoothstep(-13.6, -13.35, t)
        if w > 0:
            xa, xb = (0.56, 0.70) if front else (0.08, 0.24)
            _attach(p, "l", _shell_grip(t, xa, -0.02), w); _attach(p, "r", _shell_grip(t, xb, -0.02), w)
        if not front:
            w = _win(t, -13.3, -12.95, 0.10)
            if w > 0:
                _attach(p, "l", tray_pt(t, (TRAY_GRIP[0] + 0.18, TRAY_GRIP[1], TRAY_GRIP[2])), w); _attach(p, "r", tray_pt(t, (TRAY_GRIP[0] - 0.18, TRAY_GRIP[1], TRAY_GRIP[2])), w)
        return p
    # ramming: both hold the staff, behind the gun, and run the projectile home
    sgn = 1.0 if front else -1.0
    d0, d1 = (3.00, 3.36) if front else (3.48, 3.84)
    hp, a = rammer_state(t)
    held = 1 - smoothstep(-8.3, -8.0, t)
    xb = hp[0] - a[0] * (d0 + d1) / 2 - 0.34
    if t > -8.3:
        xb = track(t, [(-8.3, xb), (-7.85, -3.0 - 0.4 * (not front)), (-7.3, -3.5 - 0.5 * (not front))])
    ph = (xb + 6.0) / 0.95 + 1.5 * smoothstep(-8.3, -7.3, t)
    moving = -10.45 < t < -7.3
    ln = track(t, [(-10.45, 0.12), (-10.05, 0.02), (-9.42, 0.42), (-9.2, 0.30), (-8.3, 0.05)])
    yb = sgn * (0.27 + 2.45 * smoothstep(-7.95, -7.25, t))
    p = stand(xb, yb, -4.0 * sgn, lean=ln - 0.05 * k, gait=ph if moving else None, twist=-10.0 * sgn)
    if held > 0:
        _attach(p, "l" if front else "r", hp - a * d0 + np.array([0, sgn * 0.02, 0.0]), held); _attach(p, "r" if front else "l", hp - a * d1 + np.array([0, sgn * 0.02, 0.0]), held)
    return p
