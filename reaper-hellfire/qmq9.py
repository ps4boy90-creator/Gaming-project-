"""General Atomics MQ-9A Reaper (Block 5, three-blade propeller) built part by part, flying configuration (gear up).

Aircraft frame: nose towards +X, left wing +Y, up +Z, origin on the fuselage centre line at the wing leading-edge root.
Published figures (USAF fact sheet): wingspan 20.1 m, length 11.0 m, height 3.8 m, Honeywell TPE331-10GD turboprop.
Wing area 25.35 m2 gives a mean chord of 1.26 m; the MTS-B turret is 0.56 m (22 in) across.  Everything else is
proportioned from service photographs (see README).
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from qgeo import *
from util import nodemat, new_mesh, grid_faces
import qhell

SPAN = 20.1; LENGTH = 11.0
NOSE_X = 4.75; TAIL_X = NOSE_X - LENGTH          # spinner tip
GREY = (0.215, 0.225, 0.24, 1); DARK = (0.095, 0.10, 0.11, 1); BLACK = (0.02, 0.02, 0.022, 1)
OLIVE = (0.115, 0.125, 0.07, 1); YELLOW = (0.62, 0.45, 0.03, 1); WHITE = (0.55, 0.55, 0.53, 1)
WING_Z = -0.20; DIHEDRAL = math.radians(2.0)
ST_IN = 1.30; ST_MID = 2.15                      # weapon stations (m from the centre line)
PROP_X = -5.42; PROP_R = 1.40
TURRET = np.array([3.78, 0.0, -0.72])

# fuselage stations: x, centre z, half width, height above centre, depth below centre
_FUS = [(4.75, 0.02, 0.02, 0.02, 0.02), (4.68, 0.02, 0.16, 0.17, 0.15), (4.50, 0.03, 0.30, 0.33, 0.27), (4.20, 0.05, 0.42, 0.50, 0.38), (3.80, 0.06, 0.50, 0.68, 0.45),
        (3.30, 0.06, 0.55, 0.78, 0.49), (2.70, 0.05, 0.56, 0.76, 0.50), (2.10, 0.03, 0.56, 0.63, 0.51), (1.50, 0.01, 0.56, 0.52, 0.52), (0.60, 0.00, 0.56, 0.49, 0.52),
        (-0.80, 0.00, 0.56, 0.49, 0.52), (-2.20, 0.00, 0.54, 0.49, 0.51), (-3.40, 0.01, 0.50, 0.48, 0.48), (-4.30, 0.02, 0.44, 0.45, 0.43), (-4.95, 0.02, 0.38, 0.40, 0.38),
        (-5.38, 0.02, 0.34, 0.35, 0.34)]

def _fus_at(x):
    a = np.array(_FUS); o = np.argsort(a[:, 0]); a = a[o]
    return [float(np.interp(x, a[:, 0], a[:, k])) for k in range(1, 5)]

def wing_le(y):
    """Leading edge point, chord and thickness ratio of the main wing at span station |y|."""
    u = (abs(y) - 0.40) / (SPAN / 2 - 0.40)
    return np.array([0.0 - 0.34 * u, y, WING_Z + (abs(y) - 0.40) * math.tan(DIHEDRAL)]), 1.78 + (0.74 - 1.78) * u, 0.17 + (0.12 - 0.17) * u

def wing_under(y, x):
    le, c, t = wing_le(y); return le[2] - 0.45 * t * c

def _fuselage(S):
    xs = np.linspace(NOSE_X, -5.38, 70); xs = NOSE_X - (NOSE_X + 5.38) * (np.linspace(0, 1, 70) ** 1.35)   # denser at the nose
    P = np.array([_fus_at(x) for x in xs])
    for _ in range(2):                                       # soften the station kinks
        P[1:-1] = 0.25 * P[:-2] + 0.5 * P[1:-1] + 0.25 * P[2:]
    m = 32; th = np.linspace(0, 2 * np.pi, m, endpoint=False); e = 2.0 / 2.5
    cs, sn = np.cos(th), np.sin(th); sx = np.sign(cs) * np.abs(cs) ** e; sz = np.sign(sn) * np.abs(sn) ** e
    rings = []; cols = []
    for x, (zc, w, up, dn) in zip(xs, P):
        z = zc + np.where(sz > 0, up, dn) * sz
        rings.append(np.stack([np.full(m, x), w * sx, z], 1))
        k = np.clip((x - 2.3) / 0.5, 0, 1) * np.clip((zc - 0.10 - z) / 0.06, 0, 1)      # darker lower nose (radar / sensor bay)
        cols.append(np.array(GREY)[None] * (1 - k[:, None]) + np.array(DARK)[None] * k[:, None])
    V, Q, T = loft(rings)
    C = np.vstack(cols + [np.array([GREY]), np.array([GREY])]); S.add(V, Q, T, C)

def _dorsal(S):
    """Engine air intake fairing on the rear spine and the oval exhaust duct above the spinner."""
    st = [(-2.75, 0.47, 0.06, 0.02), (-3.05, 0.53, 0.15, 0.07), (-3.45, 0.60, 0.21, 0.13), (-4.2, 0.66, 0.24, 0.165), (-4.9, 0.70, 0.245, 0.17), (-5.36, 0.71, 0.245, 0.17)]
    m = 20; a = np.linspace(0, 2 * np.pi, m, endpoint=False); rings = [np.stack([np.full(m, x), w * np.cos(a), zc + h * np.sin(a)], 1) for x, zc, w, h in st]
    V, Q, T = loft(rings, cap1=False); S.add(V, Q, T, GREY)
    V, Q, T = loft([np.stack([np.full(m, x), 0.215 * np.cos(a), 0.71 + 0.14 * np.sin(a)], 1) for x in (-5.36, -5.20)], cap0=False); S.add(V, Q, T, BLACK)   # the duct mouth
    V, Q, T = ellipsoid((-3.02, 0, 0.545), (0.035, 0.13, 0.05)); S.add(V, Q, T, BLACK)                                                              # intake lip shadow

def _wings(S):
    for s in (1, -1):
        st = []
        for y in np.linspace(0.40, SPAN / 2 - 0.10, 9):
            le, c, t = wing_le(s * y); st.append((le, c, t, (-1, 0, 0), (0, 0, 1)))
        le, c, t = wing_le(s * (SPAN / 2 - 0.03)); st.append((le + np.array([-0.10, 0, 0]), c * 0.72, t, (-1, 0, 0), (0, 0, 1)))
        le, c, t = wing_le(s * SPAN / 2); st.append((le + np.array([-0.26, 0, 0]), c * 0.36, t * 0.8, (-1, 0, 0), (0, 0, 1)))
        V, Q, T = surface(st, 22, camber=0.03); S.add(V, Q, T, GREY)
        for y in (2.9, 4.6, 6.4, 8.2):                                   # flap / aileron actuator fairings on the upper surface
            le, c, t = wing_le(s * y)
            V, Q, T = ellipsoid(le + np.array([-0.74 * c, 0, 0.40 * t * c]), (0.20, 0.032, 0.045)); S.add(V, Q, T, GREY)
        for y in (6.9, 8.7):                                             # small blade antennas under the outer wing
            le, c, t = wing_le(s * y)
            V, Q, T = plate([le + np.array([-0.35 * c, 0, -0.4 * t * c]), le + np.array([-0.55 * c, 0, -0.4 * t * c]), le + np.array([-0.52 * c, 0, -0.4 * t * c - 0.16]),
                             le + np.array([-0.42 * c, 0, -0.4 * t * c - 0.16])], (0, 1, 0), 0.012); S.add(V, Q, T, DARK)

TAIL_DIH = math.radians(35.0); TAIL_LEN = 3.45
def _tail(S):
    for s in (1, -1):
        d = np.array([0, s * math.cos(TAIL_DIH), math.sin(TAIL_DIH)]); up = np.array([0, -s * math.sin(TAIL_DIH), math.cos(TAIL_DIH)])
        V, Q, T = wing(np.array([-3.92, s * 0.20, 0.22]), 1.22, 0.11, np.array([-4.55, s * 0.20, 0.22]) + d * TAIL_LEN, 0.62, 0.10, up, k=5); S.add(V, Q, T, GREY)
    V, Q, T = wing(np.array([-4.15, 0, -0.30]), 0.98, 0.10, np.array([-4.52, 0, -1.42]), 0.56, 0.09, (0, 1, 0), k=4); S.add(V, Q, T, GREY)

def _details(S):
    V, Q, T = ellipsoid((4.58, 0, 0.275), (0.02, 0.055, 0.04), rot=None); S.add(V, Q, T, BLACK)           # nose camera window
    for x, z, h in ((1.2, 0.50, 0.16), (-1.6, 0.49, 0.13), (0.4, -0.52, -0.12), (-2.6, -0.50, -0.12)):       # blade antennas
        V, Q, T = plate([(x, 0, z), (x - 0.22, 0, z), (x - 0.20, 0, z + h), (x - 0.10, 0, z + h)], (0, 1, 0), 0.014); S.add(V, Q, T, DARK)
    V, Q, T = revolve([(0, 0.20), (0.24, 0.17)], 20, axis=-EZ, origin=(TURRET[0], 0, -0.42)); S.add(V, Q, T, DARK)   # turret mount

def _pylon(S, y):
    le, c, t = wing_le(y); zu = le[2] - 0.40 * t * c
    V, Q, T = wing(np.array([le[0] - 0.22 * c, y, zu + 0.05]), 0.78, 0.15, np.array([le[0] - 0.22 * c - 0.03, y, zu - 0.30]), 0.72, 0.15, (0, 1, 0), k=3, tip_round=False)
    S.add(V, Q, T, GREY)
    return np.array([le[0] - 0.22 * c - 0.40, y, zu - 0.30])      # centre of the pylon foot

def _gbu12(S, c):
    """GBU-12 Paveway II (500 lb, Mk 82 body) hung at c: seeker 'birdie' head, four canards, folded tail wings."""
    o = c + np.array([-1.70, 0, -0.185])
    V, Q, T = revolve([(0.0, 0.075), (0.05, 0.11), (0.62, 0.115), (0.70, 0.105), (1.05, 0.125), (1.60, 0.1365), (2.25, 0.1365), (2.60, 0.118), (2.78, 0.098)], 20, origin=o); S.add(V, Q, T, OLIVE)
    V, Q, T = revolve([(2.78, 0.085), (3.10, 0.085), (3.18, 0.06), (3.26, 0.04)], 16, origin=o); S.add(V, Q, T, WHITE)          # guidance section
    V, Q, T = revolve([(3.26, 0.030), (3.42, 0.032), (3.46, 0.018), (3.47, 0.0)], 12, origin=o); S.add(V, Q, T, DARK)           # gimballed seeker
    V, Q, T = revolve([(3.28, 0.060), (3.36, 0.060), (3.36, 0.054), (3.28, 0.054)], 16, origin=o); S.add(V, Q, T, DARK)         # its ring tail
    V, Q, T = revolve([(2.52, 0.1215), (2.58, 0.1195)], 20, origin=o); S.add(V, Q, T, YELLOW)                                  # HE band
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2; r = np.array([0, math.cos(a), math.sin(a)]); n = np.array([0, -math.sin(a), math.cos(a)])
        P = lambda x, h: o + EX * x + r * h
        V, Q, T = plate([P(2.86, 0.08), P(3.04, 0.08), P(2.98, 0.24), P(2.88, 0.24)], n, 0.010); S.add(V, Q, T, WHITE)          # canard
        V, Q, T = plate([P(0.02, 0.10), P(0.60, 0.10), P(0.52, 0.215), P(0.02, 0.215)], n, 0.014); S.add(V, Q, T, OLIVE)        # folded wing
    for dx in (1.35, 2.05):                                                                                                     # suspension lugs
        V, Q, T = box(o + np.array([dx, 0, 0.15]), (0.06, 0.03, 0.05)); S.add(V, Q, T, DARK)

def launcher_points(y):
    """Tail positions (aircraft frame) of the two Hellfires on the dual-rail launcher at station y."""
    le, c, t = wing_le(y); zu = le[2] - 0.40 * t * c; cx = le[0] - 0.22 * c - 0.40; zr = zu - 0.30 - 0.07 - 0.10
    return [np.array([cx - 0.80, y + dy, zr - 0.114]) for dy in (0.150, -0.150)]

def _launcher(S, y):
    """M299-type dual-rail launcher: a cross beam on the pylon foot and two rails."""
    le, c, t = wing_le(y); zu = le[2] - 0.40 * t * c; cx = le[0] - 0.22 * c - 0.40; zb = zu - 0.30
    V, Q, T = box((cx, y, zb - 0.035), (0.62, 0.44, 0.07)); S.add(V, Q, T, BLACK)
    V, Q, T = box((cx + 0.02, y, zb - 0.085), (0.30, 0.18, 0.06)); S.add(V, Q, T, BLACK)
    for dy in (0.150, -0.150):
        V, Q, T = box((cx + 0.02, y + dy, zb - 0.12), (1.42, 0.085, 0.10)); S.add(V, Q, T, BLACK)
        V, Q, T = box((cx + 0.70, y + dy, zb - 0.105), (0.10, 0.10, 0.13)); S.add(V, Q, T, DARK)
        V, Q, T = box((cx - 0.66, y + dy, zb - 0.105), (0.08, 0.10, 0.13)); S.add(V, Q, T, DARK)

def _prop(col, root):
    S = Shell(); hub = np.array([0.0, 0, 0])
    for k in range(3):
        a = k * 2 * math.pi / 3; er = np.array([0, math.cos(a), math.sin(a)]); et = np.array([0, -math.sin(a), math.cos(a)]); st = []
        for u in np.linspace(0, 1, 9):
            r = 0.20 + (PROP_R - 0.20) * u; pitch = math.radians(62 - 40 * u ** 0.8); c = 0.13 + 0.16 * math.sin(math.pi * min(u * 1.25, 1.0) ** 0.8) * (1 - 0.55 * u ** 3)
            cd = et * math.cos(pitch) - EX * math.sin(pitch); up = np.cross(er, cd)
            st.append((hub + er * r - cd * c * 0.4, c, 0.20 - 0.13 * u, cd, up))
        st.append((hub + er * (PROP_R + 0.012) - st[-1][3] * 0.03, 0.06, 0.07, st[-1][3], st[-1][4]))
        V, Q, T = surface(st, 12, camber=0.02); S.add(V, Q, T, (0.035, 0.035, 0.04, 1))
    ob = new_obj("MQ9_Blades", S.mesh("mq9_blades"), col, paint_mat("PropBlade", rough=0.42)); ob.parent = root; ob.location = (PROP_X, 0, 0.02)
    S2 = Shell(); V, Q, T = revolve([(0.05, 0.33), (0.0, 0.335), (-0.16, 0.30), (-0.32, 0.215), (-0.44, 0.11), (-0.50, 0.04), (-0.515, 0.0)], 28); S2.add(V, Q, T, (0.78, 0.79, 0.80, 1))
    sp = new_obj("MQ9_Spinner", S2.mesh("mq9_spinner"), col, paint_mat("Spinner", rough=0.22, metal=1.0)); sp.parent = ob
    ob.rotation_mode = 'XYZ'
    # at cruise rpm the blades are a blur: a faint disc stands in for them in real-time shots
    a = np.linspace(0, 2 * np.pi, 64, endpoint=False); rr = np.linspace(0.30, PROP_R, 8)
    A_, R_ = np.meshgrid(a, rr, indexing="ij"); V = np.stack([np.zeros_like(A_), R_ * np.cos(A_), R_ * np.sin(A_)], -1).reshape(-1, 3)
    dm, N, L, P = nodemat("PropDisc"); tc = N.new("ShaderNodeTexCoord"); ln = N.new("ShaderNodeVectorMath"); ln.operation = 'LENGTH'; L.new(tc.outputs["Object"], ln.inputs[0])
    ramp = N.new("ShaderNodeValToRGB"); e = ramp.color_ramp.elements; e[0].position = 0.30 / PROP_R * 0.7; e[0].color = (0, 0, 0, 1); e[1].position = 1.0 * 0.7; e[1].color = (0, 0, 0, 1)
    for pos_, v_ in ((0.45 * 0.7, 0.13), (0.80 * 0.7, 0.10), (0.96 * 0.7, 0.04)):
        el = ramp.color_ramp.elements.new(pos_); el.color = (v_, v_, v_, 1)
    sc_ = N.new("ShaderNodeMath"); sc_.operation = 'MULTIPLY'; sc_.inputs[1].default_value = 0.7 / PROP_R; L.new(ln.outputs["Value"], sc_.inputs[0]); L.new(sc_.outputs[0], ramp.inputs["Fac"])
    L.new(ramp.outputs["Color"], P.inputs["Alpha"]); P.inputs["Base Color"].default_value = (0.03, 0.03, 0.035, 1); P.inputs["Roughness"].default_value = 0.5
    disc = new_obj("MQ9_PropDisc", new_mesh("mq9_propdisc", V, [grid_faces(64, 8, wrap_u=True)]), col, dm); disc.parent = root; disc.location = (PROP_X, 0, 0.02)
    disc.visible_shadow = False; disc.hide_render = True; ob["disc"] = disc.name
    try:
        ob.cycles.use_motion_blur = True; ob.cycles.motion_steps = 7
    except Exception:
        pass
    return ob

def _turret(col, root):
    """MTS-B: 0.56 m ball with a large and a small optical window, on a yoke under the chin."""
    S = Shell(); V, Q, T = ellipsoid((0, 0, 0), (0.28, 0.28, 0.28), 28, 16); S.add(V, Q, T, DARK)
    ob = new_obj("MQ9_Turret", S.mesh("mq9_turret"), col, paint_mat("TurretPaint", rough=0.35)); ob.parent = root; ob.location = TURRET
    G = Shell()
    for (az, el, r) in ((0.0, 0.0, 0.165), (0.95, 0.25, 0.075), (-0.95, 0.25, 0.060), (0.0, 0.72, 0.05)):
        d = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
        side = np.cross(d, EZ); side = side / (np.linalg.norm(side) + 1e-9)
        h = math.sqrt(0.28 ** 2 - r ** 2)
        V, Q, T = revolve([(h - 0.004, r), (h + 0.006, r * 0.97), (h + 0.008, 0.0)], 20, axis=d, side=side); G.add(V, Q, T, BLACK)
    g = new_obj("MQ9_TurretGlass", G.mesh("mq9_tglass"), col, glass_mat("TurretGlass", (0.03, 0.02, 0.06))); g.parent = ob
    ob.rotation_mode = 'QUATERNION'; ob.rotation_quaternion = aim_quat((0.8, 0, -0.6))
    return ob

def build(col=None, hellfires=True, name="MQ9"):
    """Returns dict: root, prop, turret, missiles (list of qhell.Hellfire, [0] is the one that is fired), rails (tail positions)."""
    col = col or bpy.context.scene.collection
    root = bpy.data.objects.new(name, None); col.objects.link(root); root.rotation_mode = 'QUATERNION'
    S = Shell(); _fuselage(S); _dorsal(S); _wings(S); _tail(S); _details(S)
    L = Shell(); rails = []
    for s in (1, -1):
        c = _pylon(S, s * ST_IN); _gbu12(L, c)
        _pylon(S, s * ST_MID); _launcher(L, s * ST_MID); rails += launcher_points(s * ST_MID)
    body = new_obj(name + "_Body", S.mesh("mq9_body"), col, paint_mat("MQ9Paint", rough=0.50, bump=0.03)); body.parent = root
    stores = new_obj(name + "_Stores", L.mesh("mq9_stores"), col, paint_mat("StoresPaint", rough=0.55)); stores.parent = root
    prop = _prop(col, root); turret = _turret(col, root)
    missiles = []
    if hellfires:
        for k, p in enumerate(rails):
            h = qhell.Hellfire(col, "Hellfire%d" % k); h.root.parent = root; h.root.location = p; missiles.append(h)
    return dict(root=root, body=body, stores=stores, prop=prop, turret=turret, missiles=missiles, rails=rails)

def spin_prop(prop, sc, t, dt_out, rps=26.5, shutter=0.5):
    """Key the propeller rotation one output frame either side of t so that motion blur follows the real arc; when the
    blades would sweep more than a third of a turn during the exposure, show the blur disc instead."""
    prop.animation_data_clear(); F = sc.frame_current
    disc = bpy.data.objects.get(prop.get("disc", "")); blur = rps * dt_out * shutter > 0.33
    prop.hide_render = blur
    if disc:
        disc.hide_render = not blur
    if dt_out <= 0:
        prop.rotation_euler = (2 * math.pi * rps * t, 0, 0); return
    for k in (-1, 0, 1):
        prop.rotation_euler = (2 * math.pi * rps * (t + k * dt_out), 0, 0); prop.keyframe_insert("rotation_euler", frame=F + k)
    act = prop.animation_data.action
    try:
        fcs = list(act.fcurves)
    except AttributeError:
        fcs = [fc for layer in act.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]
    for fc in fcs:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    prop.rotation_euler = (2 * math.pi * rps * t, 0, 0)
