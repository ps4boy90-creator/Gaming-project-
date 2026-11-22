"""UGM-109E Tomahawk Block IV (Tactical Tomahawk) in its submarine configuration.

Missile frame: centre of the 5.56 m airframe at the origin, nose towards +X, up +Z.  Stations are metres from the nose.
From sources (US Navy fact file, NAVAIR, the TACTOM system manual): 5.56 m long (6.25 m with the rocket motor),
0.52 m diameter, 2.67 m span; straight wings that swing out of slots in the body; three tail fins that swing out
through 134 degrees; a flush engine inlet under the aft body with a jettisoned cover; for submarine launch, plugs
in the wing slots and "continuity shrouds" over the folded fins that make the tail a smooth cylinder up to the
booster.  Proportions of the nose, wing chord, fin size and the layout of the three fins (one up, two down) are
estimates.  Everything that is thrown off has a loose twin in self.free for the shots to fly.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "reaper-hellfire")); sys.path.insert(0, HERE)
from qgeo import *
from qhell import flame_mat
from util import new_mesh, new_obj, grid_faces
import tconst as C

L = C.LEN; R = C.DIA / 2; BL = C.LEN_B - C.LEN
GREY = (0.36, 0.38, 0.40, 1); NOSE = (0.31, 0.32, 0.33, 1); DARK = (0.03, 0.03, 0.035, 1); SEAM = (0.10, 0.11, 0.12, 1); MOTOR = (0.20, 0.21, 0.22, 1); STEEL = (0.12, 0.12, 0.13, 1)
S_NOSE = 0.66; S_TAPER = 4.58; R_TAIL = 0.165
WING_S = 2.62; WING_Z = (-0.095, -0.135); FIN_S = (5.08, 5.44); FIN_SPAN = 0.46; FIN_ANG = (90.0, 215.0, 325.0)
INLET = (3.98, 4.50); SLOT = (2.52, 3.80)

def X(s):
    return L / 2 - s

def r_at(s):
    if s < S_NOSE:
        return max(R * math.sin(math.pi / 2 * (s / S_NOSE)) ** 0.60, 0.0)
    if s < S_TAPER:
        return R
    return R + (R_TAIL - R) * ((s - S_TAPER) / (L - S_TAPER)) ** 1.25

def _body():
    S = Shell(); ss = sorted(set([0.0, 0.004, 0.02, 0.05] + list(np.linspace(0.09, S_NOSE, 12)) + list(np.arange(S_NOSE, S_TAPER, 0.13)) + list(np.linspace(S_TAPER, L, 9))))
    segs = 40; V, Q, T = revolve([(X(s) - 0.0, r_at(s)) for s in ss][::-1], segs)
    s_ = L / 2 - V[:, 0]; ang = np.degrees(np.arctan2(V[:, 2], V[:, 1])); c = np.tile(np.array(GREY), (len(V), 1)); c[s_ < S_NOSE] = NOSE
    S.add(V, Q, T, c)
    def patch(s0, s1, a0, a1, w0=1.0):                                    # dark panel lying on the skin; w0 narrows its front end
        ss = np.linspace(s0, s1, 6); n = 7; am = (a0 + a1) / 2
        P = np.array([[X(sv), (R + 0.0025) * math.cos(math.radians(am + (a - am) * (w0 + (1 - w0) * (sv - s0) / (s1 - s0)))), (R + 0.0025) * math.sin(math.radians(am + (a - am) * (w0 + (1 - w0) * (sv - s0) / (s1 - s0))))] for sv in ss for a in np.linspace(a0, a1, n)])
        S.add(P, grid_faces(len(ss), n), None, DARK)
    patch(INLET[0], INLET[1], -114, -66, 0.45)                             # flush engine inlet, widening aft
    patch(SLOT[0], SLOT[1], -22, -14); patch(SLOT[0], SLOT[1], -166, -158)  # wing slots
    S.add(*revolve([(X(0.80) + 0.03, R + 0.0012), (X(0.80) - 0.03, R + 0.0012)], segs), color=DARK)                                        # dark band behind the nose
    for s in (S_NOSE, 1.55, 2.25, 3.76, S_TAPER):                                                                                               # section joints
        S.add(*revolve([(X(s) + 0.006, R + 0.0012), (X(s) - 0.006, R + 0.0012)], segs), color=SEAM)
    S.add(*revolve([(X(L) + 0.002, R_TAIL - 0.004), (X(L) + 0.25, 0.10), (X(L) + 0.26, 0.0)], 24), color=DARK)                                # exhaust
    S.add(*revolve([(X(L) - 0.004, R_TAIL - 0.022), (X(L) - 0.006, 0.0)], 24), color=DARK)                                                       # the jet pipe, seen from behind
    S.add(*box((X(0.40), 0, -r_at(0.40) + 0.012), (0.20, 0.13, 0.03)), color=DARK)                                                             # scene-matching camera window under the nose
    S.add(*ellipsoid((X(1.9), 0, R - 0.006), (0.16, 0.05, 0.02)), color=SEAM)                                                                   # satellite antenna blister
    return S.mesh("tlam_body", sharp=math.radians(40))

def _panel(name, s0, s1, a0, a1, color, r=None):
    """Thin shell patch at radius r (default: just proud of the cylinder)."""
    r = (R + 0.004) if r is None else r; n = max(4, int(abs(a1 - a0) / 9)); ss = np.linspace(s0, s1, 8); aa = np.radians(np.linspace(a0, a1, n)); S = Shell()
    for rr in (r - 0.006, r):
        S.add(np.array([[X(s), rr * math.cos(a), rr * math.sin(a)] for s in ss for a in aa]), grid_faces(len(ss), n), None, color)
    return S.mesh(name, sharp=3.0)

def _wing(sign):
    """Wing in its own frame: pivot at the origin, tip towards sign*Y when deployed."""
    S = Shell(); half = C.SPAN / 2 - 0.05
    V, Q, T = wing((0.16, 0, 0), 0.32, 0.10, (0.15, sign * half, 0), 0.27, 0.09, (0, 0, 1), n=14, k=4); S.add(V, Q, T, GREY)
    return S.mesh("tlam_wing%+d" % sign, sharp=math.radians(40))

def _fin():
    """Fin in its own frame: pivot at the front of the root, blade towards +Z and swept back when deployed."""
    S = Shell(); c0 = FIN_S[1] - FIN_S[0]
    V, Q, T = wing((0.0, 0, 0.0), c0, 0.07, (-0.10, 0, FIN_SPAN), 0.27, 0.06, (0, 1, 0), n=10, k=3, tip_round=False); S.add(V, Q, T, GREY)
    return S.mesh("tlam_fin", sharp=math.radians(40))

def _booster():
    """Mk 135 rocket motor assembly on the tail; its own frame is the missile frame."""
    S = Shell(); x0 = X(L)
    S.add(*revolve([(x0 + 0.02, R), (x0 - 0.47, R), (x0 - 0.54, R - 0.035), (x0 - BL, 0.185)], 36), color=MOTOR)
    S.add(*revolve([(x0 - BL + 0.004, 0.17), (x0 - BL + 0.20, 0.07), (x0 - BL + 0.21, 0.0)], 24), color=DARK)                 # nozzle
    S.add(*revolve([(x0 + 0.018, R + 0.004), (x0 - 0.03, R + 0.004)], 36), color=STEEL)                                        # separation ring
    for k in range(4):                                                                                                          # jet-tab actuators round the nozzle
        a = math.pi / 4 + k * math.pi / 2; S.add(*box((x0 - BL + 0.05, 0.215 * math.cos(a), 0.215 * math.sin(a)), (0.10, 0.07, 0.07)), color=STEEL)
    return S.mesh("tlam_booster", sharp=math.radians(40))

def _flame_mesh():
    S = Shell(); S.add(*revolve([(0.0, 0.16), (-0.12, 0.24), (-0.45, 0.30), (-1.0, 0.22), (-1.6, 0.0)], 20)); return S.mesh("tlam_flame", sharp=3.0)

class Tomahawk:
    def __init__(self, col=None, name="TLAM"):
        col = col or bpy.context.scene.collection; M = bpy.data.materials; D = bpy.data.meshes
        pm = M.get("TLAMPaint") or paint_mat("TLAMPaint", rough=0.46)
        self.root = bpy.data.objects.new(name, None); col.objects.link(self.root); self.root.rotation_mode = 'QUATERNION'; self.col = col
        def add(nm, me, parent=True):
            ob = bpy.data.objects.new(name + "_" + nm, me); col.objects.link(ob)
            if not me.materials:
                me.materials.append(pm)
            if parent:
                ob.parent = self.root
            else:
                ob.rotation_mode = 'QUATERNION'; ob.hide_render = True
            return ob
        self.body = add("Body", D.get("tlam_body") or _body())
        self.wings = []
        for k, sg in enumerate((1, -1)):
            w = add("Wing%d" % k, D.get("tlam_wing%+d" % sg) or _wing(sg)); w.location = (X(WING_S), sg * 0.05, WING_Z[k]); self.wings.append((w, sg))
        self.fins = []
        for a in FIN_ANG:
            f = add("Fin%d" % int(a), D.get("tlam_fin") or _fin()); r = r_at(FIN_S[0]) - 0.012; f.rotation_mode = 'YXZ'      # fold about the fin's own Y first, then set it round the body
            f.location = (X(FIN_S[0]), r * math.cos(math.radians(a)), r * math.sin(math.radians(a))); self.fins.append((f, a))
        parts = {"cover": lambda: _panel("tlam_cover", INLET[0] - 0.05, INLET[1] + 0.05, -122, -58, GREY),
                 "plugL": lambda: _panel("tlam_plugL", SLOT[0] - 0.03, SLOT[1] + 0.03, -26, -10, GREY), "plugR": lambda: _panel("tlam_plugR", SLOT[0] - 0.03, SLOT[1] + 0.03, -170, -154, GREY),
                 "shroudA": lambda: _panel("tlam_shroudA", S_TAPER - 0.02, L + 0.01, 2, 178, GREY, r=R + 0.002), "shroudB": lambda: _panel("tlam_shroudB", S_TAPER - 0.02, L + 0.01, 182, 358, GREY, r=R + 0.002),
                 "booster": _booster}
        self.on = {}; self.free = {}
        for nm, fn in parts.items():
            me = D.get("tlam_" + nm) or fn(); self.on[nm] = add(nm, me); self.free[nm] = add(nm + "_free", me, parent=False)
        fm = M.get("MotorFlame") or flame_mat(); self.flame = new_obj(name + "_Flame", D.get("tlam_flame") or _flame_mesh(), col, fm); self.flame.parent = self.root
        self.flame.location = (X(L) - BL, 0, 0); self.flame.visible_shadow = False; self.em = fm.node_tree.nodes[fm["em_node"]]
        ld = bpy.data.lights.new(name + "_Glow", 'POINT'); ld.color = (1.0, 0.70, 0.40); ld.shadow_soft_size = 0.4; ld.energy = 0
        self.glow = bpy.data.objects.new(name + "_Glow", ld); col.objects.link(self.glow); self.glow.parent = self.root; self.glow.location = (X(L) - BL - 1.2, 0, 0)
        self.config()

    def config(self, wings=1.0, fins=1.0, booster=False, shroud=False, plugs=False, cover=False, burn=0.0, flame_len=3.0):
        """wings, fins: 0 folded .. 1 out.  booster / shroud / plugs / cover: still attached?  burn: 0..1 booster flame."""
        for w, sg in self.wings:
            w.rotation_euler = (0, 0, sg * math.radians(90.0) * (1.0 - wings)); w.hide_render = wings < 0.02
        for f, a in self.fins:
            f.rotation_euler = (math.radians(a - 90.0), math.radians(-95.0) * (1.0 - fins), 0)       # folded: lying aft along the tail cone, under the shroud
        for nm, v in (("booster", booster), ("shroudA", shroud), ("shroudB", shroud), ("plugL", plugs), ("plugR", plugs), ("cover", cover)):
            self.on[nm].hide_render = not v
        on = burn > 0.01 and booster; self.flame.hide_render = not on; self.glow.hide_render = not on
        if on:
            self.flame.scale = (flame_len * (0.7 + 0.3 * burn), 1.6, 1.6); self.em.inputs["Strength"].default_value = 90.0 * burn; self.glow.data.energy = 60000.0 * burn

    def hide(self, v=True):
        for o in [self.body] + [w for w, _ in self.wings] + [f for f, _ in self.fins] + list(self.on.values()) + [self.flame, self.glow]:
            o.hide_render = v
