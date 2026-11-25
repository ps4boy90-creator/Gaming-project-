"""Lockheed C-130E Hercules, rigged for a heavy airdrop: ramp level, the hold open to the rear.

Aircraft frame: nose towards +X, left +Y, up +Z, z = 0 on the cargo floor; geometry is laid out by station s (metres
aft of the nose tip), x = X0 - s.
From sources (USAF fact sheet, Lockheed data): 29.79 m long, 40.41 m span, 11.66 m high; a high straight wing of
162 m2; four Allison T56 turboprops with four-bladed Hamilton Standard propellers 4.11 m across; a tailplane 16.05 m
across; a hold 12.2 m long, 3.02 m wide and 2.74 m high with a 3.1 m ramp; two fuel tanks under the wings between the
engines (the E model).  The paint is the three-colour camouflage of the tactical airlift wings in South-East Asia.
Section shapes, the stations of wing, tail and engines, nacelle and fairing shapes are estimated from photographs and
published three-view drawings.  The landing gear is up; no panel lines, markings or crew.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "reaper-hellfire")); sys.path.insert(0, HERE)
from mathutils import Quaternion
from qgeo import *
from util import new_obj, new_mesh, grid_faces, nodemat, smoothstep
import dconst as C

X0 = C.X0
CAMO = (0.0, 0.0, 0.0, 0.0)                                           # alpha 0: the camouflage pattern is painted by the material
BLACK = (0.012, 0.012, 0.014, 1); GLASS = (0.010, 0.012, 0.016, 1); METAL = (0.13, 0.12, 0.11, 1); INNER = (0.16, 0.18, 0.15, 1); FLOOR = (0.24, 0.25, 0.24, 1); RAIL = (0.42, 0.43, 0.44, 1); BLADE = (0.025, 0.025, 0.028, 1); TIPC = (0.65, 0.50, 0.05, 1)
LEN = 29.79; SPAN = 40.41; TOP = 3.70; BOT = -0.45; HOLD = (6.5, 25.2); OPEN = (C.RAMP_S[0], 25.2); OPEN_W = 1.50; CEIL = 2.74
WING_Z = 3.50; WING_LE = 10.2; ENG_Y = (4.95, 10.10); PROP_S = 6.9; PROP_D = 4.11; TANK_Y = 7.55
# s, top, bottom, half width, squareness
_FUS = [(0.0, 0.97, 0.93, 0.02, 2.0), (0.45, 1.50, 0.42, 0.55, 2.0), (1.3, 2.05, 0.00, 1.08, 2.0), (2.2, 2.75, -0.22, 1.58, 2.1), (3.4, 3.42, -0.36, 1.95, 2.2), (5.0, 3.66, -0.43, 2.13, 2.3), (6.5, TOP, BOT, 2.17, 2.4),
        (19.0, TOP, BOT, 2.17, 2.4), (21.0, 3.70, 0.12, 2.05, 2.3), (23.0, 3.72, 0.88, 1.76, 2.2), (25.0, 3.75, 1.64, 1.36, 2.1), (27.0, 3.78, 2.40, 0.92, 2.0), (28.8, 3.78, 3.05, 0.45, 2.0), (LEN, 3.52, 3.44, 0.03, 2.0)]

def P(s, y, z):
    return np.array([X0 - s, y, z])

def fus(s):
    a = np.array(_FUS); return [float(np.interp(s, a[:, 0], a[:, k])) for k in range(1, 5)]

def fus_pt(s, ang, out=0.0):
    """Point on the skin at station s and angle ang (radians; 0 = left side, pi/2 = top), pushed out by `out`."""
    top, bot, w, e = fus(s); zc = (top + bot) / 2; h = (top - bot) / 2; p = 2.0 / e; cs, sn = math.cos(ang), math.sin(ang)
    return np.array([X0 - s, (w + out) * math.copysign(abs(cs) ** p, cs), zc + (h + out) * math.copysign(abs(sn) ** p, sn)])

def edge_z(s):
    """Height of the skin along the side of the rear opening (y = OPEN_W) at station s."""
    top, bot, w, e = fus(s); zc = (top + bot) / 2; h = (top - bot) / 2
    return zc - h * (1 - (OPEN_W / w) ** e) ** (1 / e) if w > OPEN_W else zc

def _fuselage(S):
    ss = sorted(set(list(LEN * np.linspace(0, 1, 120) ** 1.05) + [OPEN[0] - 0.02, OPEN[0] + 0.02, OPEN[1] - 0.02, OPEN[1] + 0.02, 1.28, 1.32])); m = 64; rings = []; cols = []; uni = np.linspace(0, 2 * np.pi, m, endpoint=False); idx = np.arange(m)
    for s in ss:
        top, bot, w, e = fus(s); zc = (top + bot) / 2; h = (top - bot) / 2; p = 2.0 / e
        # round the rear opening the points of every ring are spaced so that two fixed ones (38 and 58) lie on its edges
        a_ = max(math.acos(min((OPEN_W / w) ** (1 / p), 1.0)) if w > OPEN_W else 0.0, 0.03); f = smoothstep(15.0, 18.0, s)
        th = uni + f * (np.interp(idx, [0, 32, 38, 58, 64], [0, np.pi, np.pi + a_, 2 * np.pi - a_, 2 * np.pi]) - uni); cs, sn = np.cos(th), np.sin(th)
        y = w * np.sign(cs) * np.abs(cs) ** p; z = zc + h * np.sign(sn) * np.abs(sn) ** p; c = np.tile(np.array(CAMO if s > 1.3 else BLACK), (m, 1))
        if OPEN[0] < s < OPEN[1]:                                     # the open rear: the belly is pushed up to the ceiling of the hold
            inb = (idx > 38) & (idx < 58); z = np.where(inb, CEIL + 0.04, z); c[inb] = INNER
        rings.append(np.stack([np.full(m, X0 - s), y, z], 1)); cols.append(c)
    V, Q, T = loft(rings); n = len(ss) * m; c = np.tile(np.array(CAMO), (len(V), 1)); c[:n] = np.concatenate(cols); S.add(V, Q, T, c)
    def window(s0, s1, a0, a1):
        ss_ = np.linspace(s0, s1, 4); aa = np.radians(np.linspace(a0, a1, 5)); S.add(np.array([fus_pt(s, a, 0.015) for s in ss_ for a in aa]), grid_faces(4, 5), None, GLASS)
    for sg in (1, -1):                                                # the flight deck's glazing: windscreen, side panes, and the low windows by the pilots' feet
        window(1.95, 2.95, 90 - sg * 4, 90 - sg * 24); window(2.05, 3.05, 90 - sg * 27, 90 - sg * 47); window(2.25, 3.30, 90 - sg * 50, 90 - sg * 68); window(2.75, 3.75, 90 - sg * 71, 90 - sg * 84)
        window(1.75, 2.35, 90 - sg * 86, 90 - sg * 100); window(1.55, 2.15, 90 - sg * 62, 90 - sg * 80)
    for sg in (1, -1):                                                # main gear fairings
        S.add(*ellipsoid(P(14.3, sg * 2.02, 0.22), (3.9, 0.80, 0.82), 24, 12), color=CAMO)

def _hold(S):
    """The inside of the hold, seen through the open rear: walls, ceiling, floor with its roller rails, the level ramp."""
    ss = np.arange(HOLD[0], HOLD[1] + 0.01, 0.55); rings = []
    for s in ss:
        top, bot, w, e = fus(s); hw = min(OPEN_W + 0.02, w * 0.80); zb = 0.0 if s <= OPEN[0] else min(edge_z(s) + 0.04, CEIL - 0.05)
        rings.append([[X0 - s, hw, zb], [X0 - s, hw, CEIL], [X0 - s, -hw, CEIL], [X0 - s, -hw, zb]])
    S.add(np.array(rings).reshape(-1, 3), grid_faces(len(ss), 4), None, INNER)
    S.add(*box(P((HOLD[0] + OPEN[0]) / 2, 0, -0.03), (OPEN[0] - HOLD[0], 3.04, 0.06)), color=FLOOR)
    S.add(*box(P(HOLD[0], 0, CEIL / 2), (0.06, 3.04, CEIL)), color=INNER)
    r0, r1 = C.RAMP_S; S.add(*box(P((r0 + r1) / 2, 0, -0.07), (r1 - r0, 3.0, 0.14)), color=FLOOR)                         # the ramp, lowered until it is level with the floor
    S.add(*box(P((r0 + r1) / 2, 0, -0.16), (r1 - r0 + 0.02, 3.02, 0.05)), color=CAMO)
    for sg in (1, -1):                                                # the rails that guide and lock the platform, and the roller conveyors
        S.add(*box(P((HOLD[0] + r1) / 2 + 0.4, sg * (C.PLAT_W / 2 + 0.05), 0.06), (r1 - HOLD[0] - 0.8, 0.06, 0.12)), color=RAIL)
        for yy in (0.45, 1.05):
            S.add(*box(P((HOLD[0] + r1) / 2 + 0.4, sg * yy, 0.012), (r1 - HOLD[0] - 0.8, 0.12, 0.024)), color=RAIL)

def _wing(S):
    for sg in (1, -1):
        st = []
        for y in (0.0, 2.2, 5.0, 8.0, 12.0, 16.0, 19.6):
            u = max(y - 5.0, 0.0) / 15.2; c = 4.9 - 2.45 * u; sle = WING_LE + 0.45 * u; z = WING_Z + max(y - 5.0, 0.0) * math.tan(math.radians(2.5))
            st.append((P(sle, sg * y, z), c, 0.18 - 0.06 * u, (-1, 0, 0), (0, 0, 1)))
        y, c = 20.0, 2.2; st.append((P(WING_LE + 0.62, sg * y, WING_Z + 15.0 * math.tan(math.radians(2.5))), c, 0.10, (-1, 0, 0), (0, 0, 1)))
        y, c = 20.2, 1.5; st.append((P(WING_LE + 0.95, sg * y, WING_Z + 15.2 * math.tan(math.radians(2.5))), c, 0.08, (-1, 0, 0), (0, 0, 1)))
        V, Q, T = surface(st, 26, camber=0.02); S.add(V, Q, T, CAMO)
    S.add(*ellipsoid(P(WING_LE + 2.3, 0, TOP - 0.02), (4.4, 1.75, 0.42), 24, 10), color=CAMO)                              # wing root fairing over the hold

def eng_z(y):
    return WING_Z - 0.32 + max(y - 5.0, 0.0) * math.tan(math.radians(2.5))

def _nacelles(S):
    for sg in (1, -1):
        for y in ENG_Y:
            z = eng_z(y); o = P(PROP_S, sg * y, z)
            S.add(*revolve([(-0.16, 0.50), (-0.6, 0.58), (-1.6, 0.60), (-3.3, 0.58), (-5.2, 0.46), (-6.6, 0.30), (-6.7, 0.0)], 26, axis=EX, origin=o), color=CAMO)
            S.add(*ellipsoid(o + np.array([-1.05, 0, -0.56]), (0.95, 0.36, 0.30), 16, 8), color=CAMO)                      # the air intake under the spinner
            S.add(*ellipsoid(o + np.array([-0.24, 0, -0.60]), (0.07, 0.26, 0.19), 12, 6), color=BLACK)
            S.add(*revolve([(-6.55, 0.27), (-6.95, 0.25)], 16, axis=EX, origin=o + np.array([0, 0, -0.10])), color=METAL)  # tailpipe under the wing
        yt = sg * TANK_Y; zt = eng_z(TANK_Y) - 1.42                   # the 1,360 gallon tank on its pylon
        S.add(*revolve([(0.0, 0.0), (0.25, 0.26), (0.9, 0.50), (2.0, 0.60), (5.2, 0.60), (6.6, 0.42), (7.5, 0.10), (7.6, 0.0)], 24, axis=-EX, origin=P(8.3, yt, zt)), color=CAMO)
        S.add(*box(P(12.3, yt, zt + 0.92), (3.6, 0.16, 0.9)), color=CAMO)

def _tail(S):
    V, Q, T = wing(P(22.2, 0, TOP - 0.3), 6.4, 0.10, P(26.9, 0, 10.63), 2.6, 0.09, (0, 1, 0), n=20, k=6); S.add(V, Q, T, CAMO)                       # fin
    S.add(*plate([P(18.3, 0, TOP - 0.05), P(22.6, 0, TOP - 0.05), P(23.4, 0, 5.2)], EY, 0.16), color=CAMO)                                           # dorsal fin
    for sg in (1, -1):
        V, Q, T = wing(P(24.5, sg * 0.3, 3.90), 4.4, 0.11, P(25.8, sg * 8.02, 3.90), 2.0, 0.10, (0, 0, 1), n=18, k=5); S.add(V, Q, T, CAMO)           # tailplane, 16.05 m across

def _prop():
    """Hub, spinner and four broad blades; turns about its X axis."""
    S = Shell(); S.add(*revolve([(0.62, 0.0), (0.58, 0.10), (0.40, 0.26), (0.10, 0.40), (-0.14, 0.44), (-0.16, 0.0)], 20), color=BLACK)
    R_ = PROP_D / 2
    for k in range(4):
        a = k * math.pi / 2; er = np.array([0, math.cos(a), math.sin(a)]); et = np.cross(EX, er); st = []
        for r, ch, pitch in ((0.30, 0.26, 62), (0.60, 0.40, 54), (1.00, 0.47, 44), (1.50, 0.46, 34), (1.90, 0.42, 28), (R_, 0.36, 26)):
            cd = EX * (-math.sin(math.radians(pitch))) + et * math.cos(math.radians(pitch)); up = np.cross(cd, er)
            st.append((er * r - cd * ch / 2, ch, 0.10 if r > 0.5 else 0.3, cd, up))
        V, Q, T = surface(st, 10); c = np.tile(np.array(BLADE), (len(V), 1)); c[np.linalg.norm(V[:, 1:], axis=1) > R_ - 0.12] = TIPC; S.add(V, Q, T, c)
    return S.mesh("c130_prop", sharp=math.radians(40))

def camo_mat():
    """Tan and two greens above, pale grey below; parts with their own colour (alpha 1 in the 'col' attribute) keep it."""
    m = bpy.data.materials.get("HercPaint")
    if m:
        return m
    m, N, L, P_ = nodemat("HercPaint"); a = N.new("ShaderNodeAttribute"); a.attribute_name = "col"; tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.16, 0.22, 0.30); L.new(tc.outputs["Object"], mp.inputs["Vector"])
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.0; nz.inputs["Detail"].default_value = 1.5; nz.inputs["Distortion"].default_value = 0.6; L.new(mp.outputs[0], nz.inputs["Vector"])
    cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.interpolation = 'CONSTANT'; e = cr.color_ramp.elements
    e[0].position = 0.0; e[0].color = (0.030, 0.050, 0.022, 1); e[1].position = 0.47; e[1].color = (0.050, 0.085, 0.030, 1); t_ = e.new(0.56); t_.color = (0.260, 0.180, 0.085, 1)
    L.new(nz.outputs["Fac"], cr.inputs["Fac"])
    geo = N.new("ShaderNodeNewGeometry"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(geo.outputs["Normal"], sep.inputs[0])
    sp = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sp.inputs[0])
    under = N.new("ShaderNodeMath"); under.operation = 'LESS_THAN'; under.inputs[1].default_value = -0.45; L.new(sep.outputs["Z"], under.inputs[0])
    low = N.new("ShaderNodeMath"); low.operation = 'LESS_THAN'; low.inputs[1].default_value = 3.3; L.new(sp.outputs["Z"], low.inputs[0])       # only the fuselage's belly, the tanks and the wing's underside
    um = N.new("ShaderNodeMath"); um.operation = 'MULTIPLY'; L.new(under.outputs[0], um.inputs[0]); um.inputs[1].default_value = 1.0
    mixu = N.new("ShaderNodeMixRGB"); mixu.inputs[2].default_value = (0.42, 0.44, 0.45, 1); L.new(um.outputs[0], mixu.inputs[0]); L.new(cr.outputs["Color"], mixu.inputs[1])
    mixo = N.new("ShaderNodeMixRGB"); L.new(a.outputs["Alpha"], mixo.inputs[0]); L.new(mixu.outputs[0], mixo.inputs[1]); L.new(a.outputs["Color"], mixo.inputs[2])
    back = N.new("ShaderNodeMixRGB"); back.inputs[2].default_value = INNER; L.new(geo.outputs["Backfacing"], back.inputs[0]); L.new(mixo.outputs[0], back.inputs[1])       # the skin seen from inside the hold
    L.new(back.outputs[0], P_.inputs["Base Color"]); P_.inputs["Roughness"].default_value = 0.62
    return m

class C130:
    def __init__(self, col=None, name="C130"):
        col = col or bpy.context.scene.collection
        self.root = bpy.data.objects.new(name, None); col.objects.link(self.root); self.root.rotation_mode = 'QUATERNION'
        pm = camo_mat(); me = bpy.data.meshes.get("c130_body")
        if me is None:
            S = Shell(); _fuselage(S); _hold(S); _wing(S); _nacelles(S); _tail(S); me = S.mesh("c130_body", sharp=math.radians(32))
        self.body = new_obj(name + "_Body", me, col, None if me.materials else pm); self.body.parent = self.root
        self.props = []; pme = bpy.data.meshes.get("c130_prop") or _prop()
        for sg in (1, -1):
            for y in ENG_Y:
                p = new_obj(name + "_Prop%+d_%d" % (sg, int(y)), pme, col, None if pme.materials else pm); p.parent = self.root; p.location = tuple(P(PROP_S, sg * y, eng_z(y))); p.rotation_mode = 'QUATERNION'; self.props.append(p)
    def prop_quat(self, t, k=0):
        return Quaternion((1, 0, 0), -2 * math.pi * 17.0 * t + 0.7 * k)                          # 1,020 turns a minute
    def set_props(self, t):
        for k, p in enumerate(self.props):
            p.rotation_quaternion = self.prop_quat(t, k)
