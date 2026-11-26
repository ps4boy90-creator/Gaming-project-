"""A second target for the MOAB segment: an invented ruined city district (MOAB_SITE=city).

Nobody is modelled, and it is no real place: flat ground, a grid of streets, blocks of five- and nine-storey
apartment slabs of the Soviet large-panel kind and a few low buildings, already burnt out and partly fallen in before
the bomb arrives, as in the towns fought over in eastern Ukraine.  The drop itself is hypothetical: this bomb has
never been used on a city.

What the blast does to each building follows from the pressure calculated for its distance (aconst.psi): at 10 psi
and more it comes down; from 5 to 10 psi about half of it comes down; from 2 to 5 psi it loses a floor here and
there; below that the shell stands.  Those thresholds are general published guidance for concrete buildings under
long blasts; a blast as short as this one does less at the same peak pressure, so they are if anything too severe.
Buildings shelter one another and channel the blast along streets; none of that is worked out.

Same interface as asite: ground, Site (with comps and update), AirFloor, target, CAM_H.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire", "tomahawk-sub"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
from mathutils import Quaternion
from qgeo import Shell, box as gbox, paint_mat
from util import new_mesh, new_obj, grid_faces, nodemat, smoothstep, fbm, Geo
import env
import aconst as C
import asite as _valley

env.SUN_ELEV = math.radians(30.0)
CAM_H = 150.0                                                         # the strike is seen from a drone's height
FLOOR_H = 2.8; BAY = 3.2; SEG = 2 * BAY                               # storey height, window spacing, one stair-section's width
SX, SY = 150.0, 115.0; X0S, Y0S = -70.0, -55.0; EXT = 900.0           # street spacing, the grid's offset (the burst is in a courtyard), half-size of the district
WALLS = ((0.42, 0.41, 0.38, 1), (0.47, 0.44, 0.38, 1), (0.36, 0.36, 0.35, 1), (0.44, 0.38, 0.32, 1)); CONC = ((0.215, 0.213, 0.205, 0), (0.17, 0.17, 0.165, 0), (0.255, 0.245, 0.23, 0)); ASPHALT = (0.060, 0.060, 0.063, 0)

def ground(x, y, fine=1):
    x = np.asarray(x, float); y = np.asarray(y, float); return 0.12 * (fbm(x / 23.0, y / 23.0, 5, 2) - 0.5) * fine + 0.0 * x

def target(k=0):
    return np.array([0.0, 0.0, 3.0])

def facade_mat():
    """Walls with rows of window openings worked out from position: 'col' gives the wall's colour, alpha 0 switches the windows off (rubble, streets)."""
    m = bpy.data.materials.get("Facade")
    if m:
        return m
    m, N, L, P = nodemat("Facade"); at = N.new("ShaderNodeAttribute"); at.attribute_name = "col"; tc = N.new("ShaderNodeTexCoord"); geo = N.new("ShaderNodeNewGeometry")
    sp = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sp.inputs[0]); sn = N.new("ShaderNodeSeparateXYZ"); L.new(geo.outputs["Normal"], sn.inputs[0])
    def M(op, a, b=None):
        n = N.new("ShaderNodeMath"); n.operation = op
        for k, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[k].default_value = v
            else:
                L.new(v, n.inputs[k])
        return n.outputs[0]
    ax = M('GREATER_THAN', M('ABSOLUTE', sn.outputs["X"]), 0.5); u = M('ADD', M('MULTIPLY', sp.outputs["Y"], ax), M('MULTIPLY', sp.outputs["X"], M('SUBTRACT', 1.0, ax)))     # along the wall
    cu = M('DIVIDE', u, BAY); cv = M('DIVIDE', sp.outputs["Z"], FLOOR_H); fu = M('FRACT', cu); fv = M('FRACT', cv)
    inu = M('MULTIPLY', M('GREATER_THAN', fu, 0.24), M('LESS_THAN', fu, 0.76)); inv = M('MULTIPLY', M('GREATER_THAN', fv, 0.30), M('LESS_THAN', fv, 0.80))
    wall = M('LESS_THAN', M('ABSOLUTE', sn.outputs["Z"]), 0.5); win = M('MULTIPLY', M('MULTIPLY', inu, inv), M('MULTIPLY', wall, M('GREATER_THAN', at.outputs["Alpha"], 0.5)))
    cell = N.new("ShaderNodeCombineXYZ"); L.new(M('FLOOR', cu), cell.inputs[0]); L.new(M('FLOOR', cv), cell.inputs[1]); L.new(ax, cell.inputs[2]); wn = N.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = '3D'; L.new(cell.outputs[0], wn.inputs["Vector"])
    burnt = M('LESS_THAN', wn.outputs["Value"], 0.62)
    soot = M('MULTIPLY', M('MULTIPLY', M('MULTIPLY', inu, M('GREATER_THAN', fv, 0.80)), burnt), M('MULTIPLY', wall, M('GREATER_THAN', at.outputs["Alpha"], 0.5)))     # black above a burnt-out window
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.11; nz.inputs["Detail"].default_value = 5; L.new(tc.outputs["Object"], nz.inputs["Vector"])
    dirt = N.new("ShaderNodeMapRange"); dirt.inputs["From Min"].default_value = 0.3; dirt.inputs["From Max"].default_value = 0.7; dirt.inputs["To Min"].default_value = 0.62; dirt.inputs["To Max"].default_value = 1.08; L.new(nz.outputs["Fac"], dirt.inputs["Value"])
    c0 = N.new("ShaderNodeMixRGB"); c0.blend_type = 'MULTIPLY'; c0.inputs[0].default_value = 1.0; L.new(at.outputs["Color"], c0.inputs[1]); L.new(dirt.outputs[0], c0.inputs[2])
    roof = M('MULTIPLY', M('GREATER_THAN', sn.outputs["Z"], 0.5), M('GREATER_THAN', at.outputs["Alpha"], 0.5)); c1 = N.new("ShaderNodeMixRGB"); L.new(roof, c1.inputs[0]); L.new(c0.outputs[0], c1.inputs[1]); c1.inputs[2].default_value = (0.085, 0.085, 0.09, 1)
    c2 = N.new("ShaderNodeMixRGB"); L.new(M('MULTIPLY', soot, 0.8), c2.inputs[0]); L.new(c1.outputs[0], c2.inputs[1]); c2.inputs[2].default_value = (0.02, 0.018, 0.016, 1)
    c3 = N.new("ShaderNodeMixRGB"); L.new(win, c3.inputs[0]); L.new(c2.outputs[0], c3.inputs[1]); c3.inputs[2].default_value = (0.010, 0.010, 0.011, 1)
    L.new(c3.outputs[0], P.inputs["Base Color"]); P.inputs["Roughness"].default_value = 0.9
    return m

def _heap(S, rng, x, y, sx, sy, hmax):
    """What is left of a fallen section: a heap of concrete with floor slabs lying on it at all angles."""
    h = float(rng.uniform(0.35, 1.0)) * hmax; S.add(*gbox((x, y, h / 2 - 0.3), (sx * rng.uniform(0.95, 1.25), sy * rng.uniform(1.1, 1.6), h + 0.6), rot=_valley._rot(rng.uniform(-0.12, 0.12))), color=CONC[int(rng.integers(0, 3))])
    for k in range(4):
        a = rng.uniform(0, 3.14); t = rng.uniform(-0.5, 0.5); c, s = math.cos(a), math.sin(a); ct, st_ = math.cos(t), math.sin(t)
        R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]]) @ np.array([[ct, 0, st_], [0, 1, 0], [-st_, 0, ct]])
        S.add(*gbox((x + rng.uniform(-0.5, 0.5) * sx, y + rng.uniform(-0.7, 0.7) * sy, h * rng.uniform(0.5, 1.0) + 0.3), (rng.uniform(2.5, 5.5), rng.uniform(2.0, 3.2), 0.22), rot=R), color=CONC[k % 3])

def _mesh(name, b, floors):
    """One building from its sections' heights in storeys (0 = fallen)."""
    S = Shell(); rng = np.random.default_rng(b["seed"] + 7)
    for (x, y, sx, sy), f in zip(b["segs"], floors):
        if f >= 1:
            h = f * FLOOR_H; S.add(*gbox((x, y, h / 2 - 0.25), (sx, sy, h + 0.5)), color=b["wall"])
        else:
            _heap(S, rng, x, y, sx, sy, min(1.0 + 0.45 * b["floors"], 4.5))
    return S.mesh(name, sharp=math.radians(40))

def _layout(rng):
    """Buildings as dicts: sections (x, y, size x, size y), storeys, how ruined it is already."""
    out = []
    def slab(cx, cy, ln, along_x, floors, depth=12.0):
        n = max(int(round(ln / SEG)), 2); segs = []
        for k in range(n):
            o = (k - (n - 1) / 2) * SEG; segs.append((cx + o, cy, SEG, depth) if along_x else (cx, cy + o, depth, SEG))
        out.append(dict(segs=segs, floors=floors, x=cx, y=cy, wall=tuple(np.array(WALLS[int(rng.integers(0, len(WALLS)))]) * np.array([1, 1, 1, 0]) * float(rng.uniform(0.58, 1.0)) + np.array([0, 0, 0, 1.0])), seed=int(rng.integers(0, 1 << 30)), ruin=float(rng.uniform(0.4, 1.0))))      # many walls are blackened by fire
    for bx in np.arange(X0S - 6 * SX, EXT, SX):
        for by in np.arange(Y0S - 8 * SY, EXT, SY):
            cx = bx + SX / 2; cy = by + SY / 2
            if abs(cx) > EXT - 40 or abs(cy) > EXT - 40:
                continue
            home = abs(cx - 5.0) < 1.0 and abs(cy - 2.5) < 1.0; kind = 0 if home else int(rng.integers(0, 4)); tall = lambda: 9 if rng.uniform() < 0.28 else 5
            if kind in (0, 1):                                         # two long slabs along the streets, one across the end: a courtyard between them
                slab(cx + rng.uniform(-6, 6) * (not home), cy + 38.0, float(rng.uniform(96, 118)), True, tall()); slab(cx + rng.uniform(-6, 6) * (not home), cy - 38.0, float(rng.uniform(96, 118)), True, tall())
                slab(cx + (60.0 if rng.uniform() < 0.5 else -60.0), cy, 50.0, False, 5)
            elif kind == 2:                                            # slabs side by side, end on to the street
                for dx in (-46.0, 0.0, 46.0):
                    slab(cx + dx, cy + rng.uniform(-5, 5), float(rng.uniform(64, 84)), False, tall())
            else:                                                      # a school or a shop, and one slab
                slab(cx - 30.0, cy - 18.0, 52.0, True, 2, depth=26.0); slab(cx + 10.0, cy + 36.0, float(rng.uniform(84, 108)), True, tall())
    return out

def _ruin(rng, b):
    """Storeys of each section before the bomb: burnt out and, here and there, fallen in already."""
    n = len(b["segs"]); f = np.full(n, b["floors"]); q = b["ruin"]
    for k in range(n):
        if rng.uniform() < 0.18 + 0.36 * q:
            f[k] = max(f[k] - int(rng.integers(1, 4)), 1)
    for rep in range(2):
        if rng.uniform() < (0.80, 0.35)[rep] * q:
            k0 = int(rng.integers(0, n)); f[k0:k0 + int(rng.integers(1, 6))] = 0
    return f

def _after(rng, f0, state):
    f = f0.copy(); n = len(f)
    if state == 3:
        f[:] = 0
    elif state == 2:
        for k in range(n):
            f[k] = 0 if rng.uniform() < 0.5 else max(f[k] - int(rng.integers(1, 4)), 0)
    elif state == 1:
        for k in range(n):
            if rng.uniform() < 0.22:
                f[k] = max(f[k] - int(rng.integers(1, 3)), 0)
    return f

class City:
    def __init__(self, sc, col):
        rng = np.random.default_rng(31); self.col = col; env.make_world(sc); fm = facade_mat()
        # ---- the ground: bare earth and dead grass, the streets, the open country round the district
        xs = np.concatenate([-np.geomspace(90000.0, 960.0, 26), np.arange(-930.0, 930.1, 6.0), np.geomspace(960.0, 90000.0, 26)]); X, Y = np.meshgrid(xs, xs, indexing="ij")
        gm, N, L, P = nodemat("CityGround"); tc = N.new("ShaderNodeTexCoord"); nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.035; nz.inputs["Detail"].default_value = 8; nz.inputs["Roughness"].default_value = 0.7; L.new(tc.outputs["Object"], nz.inputs["Vector"])
        cr = N.new("ShaderNodeValToRGB"); e = cr.color_ramp.elements; e[0].position = 0.32; e[0].color = (0.085, 0.078, 0.062, 1); e[1].position = 0.70; e[1].color = (0.165, 0.150, 0.110, 1); L.new(nz.outputs["Fac"], cr.inputs["Fac"]); L.new(cr.outputs["Color"], P.inputs["Base Color"]); P.inputs["Roughness"].default_value = 0.95
        self.ground = new_obj("Ground", new_mesh("city_ground", np.stack([X, Y, ground(X, Y)], -1).reshape(-1, 3), [grid_faces(len(xs), len(xs))]), col, gm)
        S = Shell()
        for x in np.arange(X0S - 6 * SX, EXT + 1, SX):
            S.add(*gbox((x, 0, 0.10), (14.0, 2 * EXT, 0.12)), color=ASPHALT)
        for y in np.arange(Y0S - 8 * SY, EXT + 1, SY):
            S.add(*gbox((0, y, 0.11), (2 * EXT, 12.0, 0.12)), color=ASPHALT)
        new_obj("Streets", S.mesh("streets"), col, fm)
        # ---- buildings: as they stand before the bomb, and as it leaves them
        self.comps = []
        for i, b in enumerate(_layout(rng)):
            r = float(min(math.hypot(x, y) for (x, y, sx, sy) in b["segs"])); p = float(C.psi(max(r, 5.0))); state = 3 if p >= 10.0 else (2 if p >= 5.0 else (1 if p >= 2.0 else 0)); r0 = np.random.default_rng(b["seed"]); f0 = _ruin(r0, b)
            a = new_obj("Bld%03d" % i, _mesh("bld%03d" % i, b, f0), col, fm); bo = None
            if state:
                f1 = _after(r0, f0, state); bo = new_obj("Bld%03d_after" % i, _mesh("bld%03d_after" % i, b, f1), col, fm); drop = 1.0 - (float(f1.sum()) + 0.6 * len(f1)) / (float(f0.sum()) + 0.6 * len(f0))
            self.comps.append(dict(a=a, b=bo, r=r, t=float(C.t_front(r)), state={3: 2, 2: 1, 1: 1, 0: 0}[state], lvl=state, x=b["x"], y=b["y"], z=b["floors"] * FLOOR_H, drop=drop if state else 0.0))
        # ---- rubble in the streets and yards (there before the bomb), and what the bomb adds near the burst
        g = Geo(); g2 = Geo(); rm = env.mat_vcol("RubbleMat", rough=0.92, bump_scale=6); cols = [(0.26, 0.26, 0.25, 1), (0.20, 0.20, 0.195, 1), (0.31, 0.29, 0.26, 1)]
        for k in range(900):
            c = self.comps[int(rng.integers(0, len(self.comps)))]; x = c["x"] + float(rng.normal(0, 34.0)); y = c["y"] + float(rng.normal(0, 26.0)); s = float(rng.uniform(0.3, 1.3)); env.rock_geo(g, rng, (x, y, 0.1 * s), s, 2, cols[k % 3])
        for k in range(700):
            r = float(abs(rng.normal(0, 85.0))) + 8.0; a = float(rng.uniform(0, 6.283)); s = float(rng.uniform(0.3, 1.5)); env.rock_geo(g2, rng, (r * math.cos(a), r * math.sin(a), 0.1 * s), s, 2, cols[k % 3])
        new_obj("Rubble", g.mesh("rubble"), col, rm); self.debris = new_obj("Debris", g2.mesh("debris"), col, rm)
        # ---- trees along the streets: bare
        tm = bpy.data.materials.get("TreePaint") or paint_mat("TreePaint", rough=0.85, bump=0.3); self.trees = []
        for i in range(520):
            if i % 2:
                x = float(X0S + SX * int(rng.integers(-5, 6)) + (9.5 if rng.uniform() < 0.5 else -9.5)); y = float(rng.uniform(-EXT + 30, EXT - 30))
            else:
                y = float(Y0S + SY * int(rng.integers(-7, 8)) + (8.5 if rng.uniform() < 0.5 else -8.5)); x = float(rng.uniform(-EXT + 30, EXT - 30))
            r = math.hypot(x, y)
            if r < 16.0:
                continue
            k = int(rng.integers(0, 3)); me = _valley._tree_mesh(k, True)
            if not me.materials:
                me.materials.append(tm)
            ob = new_obj("Tree%03d" % i, me, col, None); ob.rotation_mode = 'QUATERNION'; ob.location = (x, y, -0.1); s = float(rng.uniform(0.8, 1.2)); ob.scale = (s, s, s)
            self.trees.append(dict(ob=ob, r=r, d=np.array([x, y]) / r, t=float(C.t_front(r)), p=float(C.psi(r)), yaw=float(rng.uniform(0, 6.283)), j=float(rng.uniform(0, 1))))
        # ---- the ground under the fireball, burnt
        R1 = 0.75 * C.FB_D; a_ = np.linspace(0, 2 * np.pi, 72, endpoint=False); rr = np.linspace(0.0, R1, 16)[1:]; V = [[0.0, 0.0, 0.2]]; A = [[0.03, 0.028, 0.026, 0.92]]
        for q in rr:
            for t in a_:
                x = q * math.cos(t); y = q * math.sin(t); V.append([x, y, 0.2]); A.append([0.03, 0.028, 0.026, 0.92 * float(1 - smoothstep(0.45 * R1, R1, q * (1 + 0.25 * (fbm(x / 9.0, y / 9.0, 3, 3) - 0.5))))])
        n = len(a_); F3 = [[0, 1 + k, 1 + (k + 1) % n] for k in range(n)]; F4 = [[1 + j * n + k, 1 + (j + 1) * n + k, 1 + (j + 1) * n + (k + 1) % n, 1 + j * n + (k + 1) % n] for j in range(len(rr) - 1) for k in range(n)]
        self.scorch = new_obj("Scorch", new_mesh("scorch", np.array(V), [np.array(F3), np.array(F4)], attrs={"col": np.array(A, np.float32)}), col, _valley._alpha_mat("ScorchMat")); self.scorch.visible_shadow = False
        self.update(-1.0)

    def update(self, tb):
        """tb: seconds after the burst."""
        self.scorch.hide_render = tb < 0.2; self.debris.hide_render = tb < 1.2
        for c in self.comps:
            if c["b"] is None:
                continue
            tau = tb - c["t"] - 0.08; fall = 0.9 + 0.05 * c["z"]; u = smoothstep(0.0, fall, tau); c["a"].hide_render = u >= 1.0; c["b"].hide_render = u < 1.0     # a tall building takes a second or two to come down
            c["a"].scale = (1.0, 1.0, 1.0 - c["drop"] * u)
        for t in self.trees:
            tau = tb - t["t"]; p = t["p"]; ang = 0.0
            if tau > 0:
                if p >= 5.0:
                    ang = math.radians(84.0 + 5.0 * t["j"]) * smoothstep(0.0, 0.42 + 0.2 * t["j"], tau)
                elif p >= 2.0:
                    ang = math.radians(4.0 + 20.0 * t["j"] * (p - 2.0) / 3.0) * smoothstep(0.0, 0.3, tau) + math.radians(7.0) * math.exp(-tau / 0.7) * math.sin(9.0 * tau)
                else:
                    ang = math.radians(min(4.0 * p, 5.0)) * math.exp(-tau / 0.9) * math.sin(8.0 * tau)
            d = t["d"]; t["ob"].rotation_quaternion = Quaternion((-d[1], d[0], 0.0), ang) @ Quaternion((0, 0, 1), t["yaw"])

Site = City

class AirFloor:
    """Flat farming country from the aircraft, with the grey of the district under the flight path; ob is moved so that it slides past underneath."""
    def __init__(self, sc, col):
        env.make_world(sc)
        m, N, L, P = nodemat("Fields"); tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1 / 520.0, 1 / 380.0, 1.0); L.new(tc.outputs["Object"], mp.inputs["Vector"])
        vo = N.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 1.0; L.new(mp.outputs[0], vo.inputs["Vector"]); cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.interpolation = 'CONSTANT'; e = cr.color_ramp.elements
        e[0].position = 0.0; e[0].color = (0.075, 0.095, 0.045, 1); e[1].position = 0.30; e[1].color = (0.150, 0.130, 0.080, 1)
        for pos, c in ((0.52, (0.095, 0.110, 0.055, 1)), (0.72, (0.180, 0.160, 0.100, 1)), (0.88, (0.060, 0.080, 0.045, 1))):
            el = e.new(pos); el.color = c
        sep = N.new("ShaderNodeSeparateColor"); L.new(vo.outputs["Color"], sep.inputs[0]); L.new(sep.outputs[0], cr.inputs["Fac"])
        d = N.new("ShaderNodeVectorMath"); d.operation = 'LENGTH'; L.new(tc.outputs["Object"], d.inputs[0]); mr = N.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 850.0; mr.inputs["From Max"].default_value = 1150.0; mr.inputs["To Min"].default_value = 1.0; mr.inputs["To Max"].default_value = 0.0; L.new(d.outputs["Value"], mr.inputs["Value"])
        mx = N.new("ShaderNodeMixRGB"); L.new(mr.outputs[0], mx.inputs[0]); L.new(cr.outputs["Color"], mx.inputs[1]); mx.inputs[2].default_value = (0.115, 0.112, 0.105, 1); L.new(mx.outputs[0], P.inputs["Base Color"]); P.inputs["Roughness"].default_value = 0.95
        xs = np.array([-500000.0, -60000.0, -12000.0, -3000.0, 0.0, 3000.0, 12000.0, 60000.0, 500000.0]); X, Y = np.meshgrid(xs, xs, indexing="ij")
        self.ob = new_obj("Country", new_mesh("country", np.stack([X, Y, 0 * X], -1).reshape(-1, 3), [grid_faces(len(xs), len(xs))]), col, m)
    def set(self, t):
        p = C.ac_pos(t); self.ob.location = (-float(p[0]), 0.0, -float(p[2]))
