"""Sikorsky UH-60L Black Hawk with the External Stores Support System (ESSS) and four Mk 77 Mod 5 fire bombs.

Helicopter frame: nose towards +X, left +Y, up +Z; the origin is on the ground under the main rotor mast (wheels on
z = 0).  Published figures (Sikorsky / US Army): fuselage 15.27 m, main rotor 16.36 m (four blades, 258 rpm,
anticlockwise seen from above, 0.53 m chord, tips swept 20 deg), tail rotor 3.35 m (four blades, canted 20 deg, on
the right of the tail pylon), height 5.13 m, fuselage width 2.36 m, stabilator span 4.37 m, wheel track 2.71 m,
wheelbase 8.82 m.  Mk 77 Mod 5: 2.06 m long, 0.47 m across, unfinned aluminium canister, two lugs 14 in apart.
Everything else is proportioned from service photographs (see README).  The Mk 77 is not a cleared store on any
H-60; the load shown here is hypothetical.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, os.path.join(HERE, "..", "reaper-hellfire")); sys.path.insert(0, HERE)
from mathutils import Quaternion
from qgeo import *
from util import nodemat, new_mesh, grid_faces, tube
import nconst as C

OLIVE = (0.078, 0.088, 0.058, 1); DARK = (0.016, 0.017, 0.016, 1); STEEL = (0.10, 0.10, 0.10, 1); TYRE = (0.02, 0.02, 0.022, 1); ALU = (0.62, 0.63, 0.64, 1); REDM = (0.45, 0.03, 0.02, 1)
HUB = np.array([0.0, 0.0, 3.76]); TAIL_HUB = np.array([-10.95, -0.42, 3.92]); TAIL_AX = np.array([0.0, -math.cos(math.radians(20)), math.sin(math.radians(20))])
R_MAIN = C.ROTOR_D / 2; R_TAIL = C.TAIL_ROTOR_D / 2
PYLONS = [(2.05, 1), (2.95, 1), (2.05, -1), (2.95, -1)]          # (|y|, side) of the four ESSS pylons

# fuselage stations: x, centre z, half width, half height up, half height down, squareness exponent
_FUS = [(3.90, 1.12, 0.26, 0.22, 0.26, 2.2), (3.72, 1.13, 0.60, 0.44, 0.50, 2.3), (3.35, 1.18, 0.86, 0.62, 0.66, 2.5), (2.80, 1.26, 1.02, 0.76, 0.76, 2.9), (2.20, 1.38, 1.13, 0.92, 0.86, 3.2),
        (1.50, 1.43, 1.18, 0.95, 0.92, 3.6), (0.50, 1.43, 1.18, 0.95, 0.93, 3.8), (-1.60, 1.43, 1.18, 0.95, 0.93, 3.8), (-2.70, 1.46, 1.14, 0.92, 0.90, 3.4), (-3.50, 1.55, 0.92, 0.80, 0.74, 2.8),
        (-4.60, 1.66, 0.60, 0.62, 0.50, 2.4), (-6.50, 1.72, 0.42, 0.50, 0.40, 2.2), (-8.50, 1.80, 0.30, 0.40, 0.32, 2.2), (-9.90, 1.90, 0.22, 0.30, 0.26, 2.2)]

def _fus_at(x):
    a = np.array(sorted(_FUS)); return [float(np.interp(x, a[:, 0], a[:, k])) for k in range(1, 6)]

def fus_point(x, th, out=1.0):
    """Point on the fuselage skin at station x and angle th (0 = left side, 90 deg = top), pushed out by `out`."""
    zc, w, up, dn, e = _fus_at(x); cs, sn = math.cos(th), math.sin(th); p = 2.0 / e
    return np.array([x, out * w * math.copysign(abs(cs) ** p, cs), zc + out * (up if sn > 0 else dn) * math.copysign(abs(sn) ** p, sn)])

def _fuselage(S):
    xs = 3.90 - 13.80 * np.linspace(0, 1, 80) ** 1.25; m = 36; th = np.linspace(0, 2 * np.pi, m, endpoint=False)
    V, Q, T = loft([np.array([fus_point(x, t) for t in th]) for x in xs]); S.add(V, Q, T, OLIVE)

def _patch(G, x0, x1, t0, t1, nx=6, nt=6):
    """A pane of glazing lying on the fuselage skin."""
    P = np.array([[fus_point(x, math.radians(t), 1.006) for t in np.linspace(t0, t1, nt)] for x in np.linspace(x0, x1, nx)]).reshape(-1, 3)
    G.add(P, grid_faces(nx, nt), None, (0.02, 0.025, 0.03, 1))

def _glazing():
    G = Shell()
    for a, b in ((38, 86), (94, 142)):
        _patch(G, 2.15, 3.18, a, b)                                   # windscreens
    for sgn in (1, -1):
        f = (lambda a: a) if sgn > 0 else (lambda a: 180 - a)
        _patch(G, 1.15, 2.05, f(2), f(34)); _patch(G, 2.95, 3.55, f(-22), f(-52))        # cockpit door window, chin window
        _patch(G, -0.05, 0.60, f(4), f(32)); _patch(G, -0.95, -0.30, f(4), f(32))         # cabin door windows
    return G

def _top(S):
    """Gearbox fairing, the two engine nacelles with intakes and exhausts, rotor mast and hub."""
    st = [(1.75, 2.30, 0.30, 0.04), (1.20, 2.48, 0.52, 0.22), (0.30, 2.60, 0.62, 0.36), (-1.20, 2.62, 0.60, 0.36), (-2.60, 2.50, 0.48, 0.28), (-3.60, 2.28, 0.26, 0.10)]
    m = 20; a = np.linspace(0, 2 * np.pi, m, endpoint=False)
    S.add(*loft([np.stack([np.full(m, x), w * np.cos(a), zc + h * np.sin(a)], 1) for x, zc, w, h in st]), color=OLIVE)
    for s in (1, -1):
        S.add(*revolve([(0.95, 0.20), (0.80, 0.30), (0.30, 0.33), (-1.30, 0.33), (-1.75, 0.27)], 18, origin=(0, s * 0.80, 2.50)), color=OLIVE)
        S.add(*revolve([(0.955, 0.19), (0.90, 0.17), (0.80, 0.0)], 14, origin=(0, s * 0.80, 2.50)), color=DARK)                       # intake
        d = np.array([-0.80, s * 0.42, 0.42]); d /= np.linalg.norm(d)
        S.add(*revolve([(0.0, 0.24), (0.55, 0.21)], 12, axis=d, origin=(-1.65, s * 0.80, 2.50)), color=STEEL)                         # exhaust (suppressor) turned out and up
        S.add(*revolve([(0.50, 0.19), (0.56, 0.0)], 12, axis=d, origin=(-1.65, s * 0.80, 2.50)), color=DARK)
    S.add(*revolve([(2.85, 0.16), (3.62, 0.13)], 14, axis=EZ, origin=(0, 0, 0), side=EX), color=STEEL)

def _tail(S):
    S.add(*wing(np.array([-9.20, 0, 1.85]), 1.30, 0.16, np.array([-10.55, 0, 4.65]), 0.80, 0.14, (0, 1, 0), k=5), color=OLIVE)        # tail pylon
    for s in (1, -1):                                                                                                                 # stabilator
        S.add(*wing(np.array([-9.75, s * 0.05, 1.55]), 1.05, 0.10, np.array([-9.90, s * 2.185, 1.55]), 0.78, 0.09, (0, 0, 1), k=4), color=OLIVE)
    S.add(*revolve([(0.0, 0.10), (0.34, 0.09)], 10, axis=TAIL_AX, origin=TAIL_HUB - TAIL_AX * 0.34, side=EX), color=STEEL)            # tail rotor shaft

def _gear(S, W):
    for s in (1, -1):
        w = np.array([1.37, s * 1.355, 0.34]); top = np.array([0.55, s * 1.12, 1.95]); fwd = np.array([1.95, s * 1.10, 0.80])
        for a_, b_, r in ((w + np.array([0, -s * 0.16, 0.05]), top, 0.065), (w + np.array([0, -s * 0.16, 0.0]), fwd, 0.05)):
            v, f, t = tube(np.array([a_, b_]), np.array([r, r]), 10); S.add(v, f, t, STEEL)
        W.add(*revolve([(-0.11, 0.24), (-0.11, 0.31), (-0.06, 0.34), (0.06, 0.34), (0.11, 0.31), (0.11, 0.24)], 20, axis=EY, origin=w, side=EX), color=TYRE)
        W.add(*revolve([(-0.09, 0.0), (-0.09, 0.19), (0.09, 0.19), (0.09, 0.0)], 14, axis=EY, origin=w, side=EX), color=STEEL)
    tw = np.array([-7.45, 0, 0.19]); v, f, t = tube(np.array([tw + np.array([0, 0, 0.05]), np.array([-7.25, 0, 1.36])]), np.array([0.05, 0.05]), 10); S.add(v, f, t, STEEL)
    W.add(*revolve([(-0.07, 0.10), (-0.07, 0.17), (-0.03, 0.19), (0.03, 0.19), (0.07, 0.17), (0.07, 0.10)], 16, axis=EY, origin=tw, side=EX), color=TYRE)

def esss_wing(y):
    """Leading edge point of the stores support at span station y (it slopes down towards the tip)."""
    ay = abs(y); return np.array([0.62, y, 2.30 - 0.20 * (ay - 1.10)])

def store_centre(ay, side):
    """Centre of the canister hung on the pylon at |y| = ay (helicopter frame)."""
    le = esss_wing(side * ay); return np.array([C.STORE_X, side * ay, le[2] - 0.10 - 0.42 - 0.07 - C.B_DIA / 2])

def _esss(S):
    for s in (1, -1):
        S.add(*wing(esss_wing(s * 1.08), 0.62, 0.22, esss_wing(s * 3.20), 0.50, 0.20, (0, 0, 1), k=4), color=OLIVE)
        for ay in (2.05, 2.95):
            le = esss_wing(s * ay)
            S.add(*wing(le + np.array([-0.02, 0, -0.06]), 0.60, 0.20, le + np.array([-0.04, 0, -0.50]), 0.56, 0.20, (0, 1, 0), k=3, tip_round=False), color=OLIVE)   # pylon
            S.add(*box(le + np.array([-0.31, 0, -0.545]), (0.70, 0.11, 0.09)), color=STEEL)                                                                      # ejector rack
        for xb in (0.75, -0.55):                                                                                                                                 # brace struts
            v, f, t = tube(np.array([esss_wing(s * 2.35) + np.array([-0.30, 0, -0.06]), np.array([xb, s * 1.17, 0.78])]), np.array([0.045, 0.045]), 10); S.add(v, f, t, OLIVE)

def mk77_shell():
    """Mk 77 Mod 5 about its own centre, long axis X: cigar-shaped canister with blunt domed ends and end plugs."""
    S = Shell(); h = C.B_LEN / 2; r = C.B_DIA / 2
    pr = [(-h, 0.0), (-h, 0.105)] + [(-h + 0.26 * (1 - math.cos(a)), 0.105 + (r - 0.105) * math.sin(a)) for a in np.linspace(0, math.pi / 2, 8)[1:]]
    pr = pr + [(-x, rr) for x, rr in reversed(pr)]
    S.add(*revolve(pr, 28), color=ALU)
    for x in (-h + 0.26, 0.0, h - 0.26):                                    # weld seams
        S.add(*revolve([(x - 0.012, r + 0.003), (x + 0.012, r + 0.003)], 28), color=(0.50, 0.51, 0.52, 1))
    for x in (-h - 0.012, h + 0.012):                                       # end plugs (fuze wells)
        S.add(*revolve([(x - 0.012, 0.055), (x + 0.012, 0.055)], 14), color=STEEL)
    for sx in (-0.178, 0.178):                                              # suspension lugs, 14 in apart
        S.add(*box((sx, 0, r + 0.02), (0.06, 0.03, 0.05)), color=STEEL)
    for sy in (1, -1):                                                      # filler caps / igniters, 31 deg down from the top
        a = math.radians(31) * sy; d = np.array([0, math.sin(a), math.cos(a)])
        S.add(*revolve([(r - 0.01, 0.050), (r + 0.035, 0.045), (r + 0.04, 0.0)], 12, axis=d, origin=(0.42 * sy, 0, 0), side=EX), color=REDM)
    return S

def metal_mat(name):
    m = paint_mat(name, rough=0.34, metal=0.85, bump=0.02); return m

class Mk77:
    def __init__(self, col, name="Mk77"):
        me = bpy.data.meshes.get("mk77") or mk77_shell().mesh("mk77")
        if not me.materials:
            me.materials.append(bpy.data.materials.get("Mk77Alu") or metal_mat("Mk77Alu"))
        self.ob = bpy.data.objects.new(name, me); col.objects.link(self.ob); self.ob.rotation_mode = 'QUATERNION'

def _rotor(col, root, name, n, R, chord, hub, axis, side, sweep=True):
    """Blades about `hub`, turning about `axis`; returns (blades object, blur disc object)."""
    axis = np.asarray(axis, float); side = np.asarray(side, float); third = np.cross(axis, side); S = Shell()
    for k in range(n):
        a = k * 2 * math.pi / n; er = side * math.cos(a) + third * math.sin(a); et = np.cross(axis, er); st = []
        for u in np.linspace(0.10, 1.0, 9):
            r = R * u; sw = (r - 0.93 * R) * math.tan(math.radians(20)) if (sweep and u > 0.93) else 0.0
            pitch = math.radians(9 - 8 * u); cd = -(et * math.cos(pitch) - axis * math.sin(pitch)); up = np.cross(er, cd)
            c = chord * (0.55 if u < 0.16 else 1.0)
            st.append((er * r + axis * (0.035 * r) - cd * (0.25 * c - sw) , c, 0.10, cd, up))
        S.add(*surface(st, 10), color=(0.03, 0.03, 0.032, 1))
    S.add(*revolve([(-0.16, 0.0), (-0.16, R * 0.045 + 0.10), (0.10, R * 0.035 + 0.08), (0.14, 0.0)], 16, axis=axis, side=side), color=STEEL)
    ob = new_obj(name, S.mesh(name.lower()), col, paint_mat(name + "Paint", rough=0.5)); ob.parent = root; ob.location = hub; ob.rotation_mode = 'QUATERNION'
    a = np.linspace(0, 2 * np.pi, 72, endpoint=False); rr = np.linspace(0.08, 1.0, 9) * R
    A_, R_ = np.meshgrid(a, rr, indexing="ij"); V = (R_[..., None] * (np.cos(A_)[..., None] * side + np.sin(A_)[..., None] * third) + axis * (0.035 * R_[..., None])).reshape(-1, 3)
    dm, N, L, P = nodemat(name + "Disc"); P.inputs["Base Color"].default_value = (0.03, 0.03, 0.03, 1); P.inputs["Alpha"].default_value = min(0.5, 0.75 * n * chord / (2 * math.pi * 0.6 * R))
    disc = new_obj(name + "_Disc", new_mesh(name.lower() + "_disc", V, [grid_faces(72, 9, wrap_u=True)]), col, dm); disc.parent = root; disc.location = hub; disc.visible_shadow = False; disc.hide_render = True
    try:
        ob.cycles.use_motion_blur = True; ob.cycles.motion_steps = 5
    except Exception:
        pass
    ob["disc"] = disc.name; ob["axis"] = [float(v) for v in axis]
    return ob

def spin(rot, sc, t, dt_out, rps, shutter=0.5):
    """Turn a rotor to its angle at time t; key one frame either side for motion blur, or swap in the blur disc when the
    blades would sweep more than a third of the gap between them during the exposure... of a full turn."""
    ax = rot["axis"]; disc = bpy.data.objects.get(rot["disc"]); rot.animation_data_clear(); F = sc.frame_current
    q = lambda tt: Quaternion(ax, 2 * math.pi * rps * tt)
    blur = dt_out > 0 and rps * dt_out * shutter > 0.30
    rot.hide_render = blur; disc.hide_render = not blur
    if dt_out > 0 and not blur:
        for k in (-1, 0, 1):
            rot.rotation_quaternion = q(t + k * dt_out); rot.keyframe_insert("rotation_quaternion", frame=F + k)
        act = rot.animation_data.action
        try:
            fcs = list(act.fcurves)
        except AttributeError:
            fcs = [fc for layer in act.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]
        for fc in fcs:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    rot.rotation_quaternion = q(t)

def build(col=None, name="UH60"):
    """Returns dict: root, main, tail (rotors), bombs (list of Mk77; index 1 hangs on the left outboard pylon, the one that is dropped), stores (their rest positions)."""
    col = col or bpy.context.scene.collection
    root = bpy.data.objects.new(name, None); col.objects.link(root); root.rotation_mode = 'QUATERNION'
    S = Shell(); W = Shell(); _fuselage(S); _top(S); _tail(S); _gear(S, W); _esss(S)
    body = new_obj(name + "_Body", S.mesh("uh60_body"), col, paint_mat("UH60Paint", rough=0.62, bump=0.03)); body.parent = root
    wheels = new_obj(name + "_Wheels", W.mesh("uh60_wheels"), col, paint_mat("UH60Tyre", rough=0.8)); wheels.parent = root
    glass = new_obj(name + "_Glass", _glazing().mesh("uh60_glass"), col, glass_mat("UH60Glass", (0.02, 0.03, 0.035), 0.05)); glass.parent = root
    main = _rotor(col, root, name + "_MainRotor", 4, R_MAIN, 0.527, HUB, EZ, EX)
    tail = _rotor(col, root, name + "_TailRotor", 4, R_TAIL, 0.247, TAIL_HUB, TAIL_AX, EX, sweep=False)
    bombs = []; stores = []
    for k, (ay, side) in enumerate(PYLONS):
        b = Mk77(col, "Mk77_%d" % k); b.ob.parent = root; p = store_centre(ay, side); b.ob.location = p; bombs.append(b); stores.append(p)
    return dict(root=root, body=body, main=main, tail=tail, bombs=bombs, stores=stores)
