"""The target: a German army depot of 1944 on open ground, seen from the air and from the ground.

The depot is invented: a gravel yard with a vehicle park, barrack blocks, garages, stores, a headquarters block,
watch towers and a fence.  Buildings and lorries are plain shapes of about the right size; nobody is modelled and
there are no flags or insignia.  The bomb comes down in the yard.

Base(sc, col).update(tp)   tp = seconds after the bomb touches the ground (the charge fires at FUZE_DELAY)
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
from mathutils import Quaternion, Vector
from qgeo import Shell, box as gbox, revolve, plate, paint_mat, EX, EY, EZ
from qtruck import Piece
from util import new_mesh, new_obj, grid_faces, nodemat, smoothstep, fbm, Geo
import env
import lconst as C

RC = C.CRATER_R; DC = C.CRATER_D
YARD = (-78.0, 78.0, -52.0, 52.0)                                      # the gravel yard: x0, x1, y0, y1
GRASS = (0.060, 0.085, 0.035, 1); GRAVEL = (0.30, 0.285, 0.25, 1); ROAD = (0.17, 0.165, 0.155, 1); SOIL = (0.150, 0.110, 0.070, 1); SOIL2 = (0.105, 0.078, 0.050, 1)
WALL = (0.46, 0.42, 0.35, 1); WALL2 = (0.36, 0.34, 0.30, 1); BRICK = (0.30, 0.16, 0.11, 1); ROOF = (0.20, 0.09, 0.065, 1); ROOF2 = (0.13, 0.135, 0.14, 1); TIMBER = (0.16, 0.11, 0.07, 1)
FELDGRAU = (0.105, 0.115, 0.100, 1); TYRE = (0.02, 0.02, 0.022, 1); CANVAS = (0.17, 0.16, 0.12, 1); DARKC = (0.012, 0.012, 0.012, 1)
# buildings: x, y, length (x), width (y), eaves height, roof ("gable" along x, "gabley" along y, "flat"), wall colour
BUILDINGS = [(x, 96.0, 44.0, 11.0, 5.5, "gable", WALL) for x in (-112.0, -56.0, 0.0, 56.0, 112.0)] + [(x, 126.0, 44.0, 11.0, 5.5, "gable", WALL) for x in (-112.0, -56.0, 0.0, 56.0, 112.0)] + \
            [(x, -84.0, 46.0, 15.0, 5.0, "flat", WALL2) for x in (-96.0, -36.0, 24.0, 84.0)] + [(118.0, -8.0, 20.0, 46.0, 9.0, "gabley", BRICK), (-118.0, 26.0, 18.0, 34.0, 6.0, "gabley", WALL2), (-118.0, -28.0, 18.0, 30.0, 6.0, "gabley", WALL2)] + \
            [(-42.0, 36.0, 22.0, 9.0, 4.2, "flat", WALL2), (44.0, -34.0, 20.0, 9.0, 4.2, "flat", WALL2), (30.0, 40.0, 9.0, 7.0, 3.2, "gable", BRICK), (-58.0, -30.0, 12.0, 8.0, 3.6, "gable", WALL)]
LORRIES = [(-26.0, 20.0, 0.0), (-26.0, 14.0, 0.0), (-26.0, 8.0, 0.0), (22.0, -20.0, 3.14), (22.0, -13.0, 3.14), (52.0, 16.0, 1.57), (58.0, 16.0, 1.57), (64.0, 16.0, 1.57), (-60.0, 6.0, 0.0), (-60.0, 12.0, 0.0), (10.0, 30.0, 0.3), (-8.0, -34.0, 2.9)]

def crater_z(r):
    """Height of the ground after the burst at distance r from the middle: a bowl with a raised lip."""
    r = np.asarray(r, float); bowl = -DC * np.clip(1.0 - (r / (RC * 0.93)) ** 2, 0.0, 1.0) ** 0.85
    return bowl + 1.9 * np.exp(-((r - RC * 1.04) / (RC * 0.30)) ** 2) * (r > RC * 0.6)

def _ground_mat():
    """Colours from the 'col' attribute, broken up by noise at three scales."""
    m, N, L, P = nodemat("BaseGround"); a = N.new("ShaderNodeAttribute"); a.attribute_name = "col"; tc = N.new("ShaderNodeTexCoord"); prev = a.outputs["Color"]
    for scale, lo, hi in ((0.05, 0.72, 1.20), (1.3, 0.80, 1.18), (14.0, 0.86, 1.12)):
        n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = 5; L.new(tc.outputs["Object"], n.inputs["Vector"])
        mr = N.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = lo; mr.inputs["To Max"].default_value = hi; L.new(n.outputs["Fac"], mr.inputs["Value"])
        mx = N.new("ShaderNodeMixRGB"); mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0; L.new(prev, mx.inputs[1]); L.new(mr.outputs[0], mx.inputs[2]); prev = mx.outputs[0]
    L.new(prev, P.inputs["Base Color"]); P.inputs["Roughness"].default_value = 0.95
    return m

def _ground_cols(X, Y):
    c = np.tile(np.array(GRASS, np.float32), X.shape + (1,))
    road = (np.abs(Y - 68.0) < 4.0) | (np.abs(X + 94.0) < 4.0) | (np.abs(X - 98.0) < 4.0) | (np.abs(Y + 66.0) < 4.0)
    c[road] = ROAD; yard = (X > YARD[0]) & (X < YARD[1]) & (Y > YARD[2]) & (Y < YARD[3]); c[yard] = GRAVEL
    return c

def _building(S, x, y, lx, ly, h, roof, col):
    S.add(*gbox((x, y, h / 2), (lx, ly, h)), color=col)
    if roof == "flat":
        S.add(*gbox((x, y, h + 0.2), (lx + 0.8, ly + 0.8, 0.4)), color=ROOF2)
        for dx in np.arange(-lx / 2 + 4.0, lx / 2 - 1.0, 7.5):                 # garage doors
            S.add(*gbox((x + dx, y + ly / 2 + 0.03, 1.9), (5.0, 0.06, 3.8)), color=TIMBER)
        return
    along_x = roof == "gable"; rh = (ly if along_x else lx) * 0.30; e = 0.5
    a, b = (lx / 2 + e, ly / 2 + e) if along_x else (ly / 2 + e, lx / 2 + e)
    P_ = np.array([[-a, -b, h], [a, -b, h], [a, b, h], [-a, b, h], [-a, 0, h + rh], [a, 0, h + rh]], float)
    if not along_x:
        P_ = P_[:, [1, 0, 2]]
    S.add(P_ + np.array([x, y, 0.0]), np.array([[0, 1, 5, 4], [2, 3, 4, 5]]), np.array([[0, 4, 3], [1, 2, 5]]), ROOF if col is not WALL2 else ROOF2)
    n = int((lx if along_x else ly) // 4.5)                                   # a row of windows down each long side
    for i in range(n):
        d = (i - (n - 1) / 2) * 4.5
        for sg in (1, -1):
            c_ = (x + d, y + sg * (ly / 2 + 0.03), h * 0.55) if along_x else (x + sg * (lx / 2 + 0.03), y + d, h * 0.55)
            S.add(*gbox(c_, (1.2, 0.06, 1.5) if along_x else (0.06, 1.2, 1.5)), color=DARKC)

def _lorry_mesh():
    """A 3-ton lorry of the Opel Blitz kind as plain shapes, about 6 m long: bonnet, cab, canvas-covered body, four wheels."""
    S = Shell(); S.add(*gbox((2.35, 0, 1.15), (1.3, 1.5, 0.9)), color=FELDGRAU); S.add(*gbox((1.2, 0, 1.55), (1.3, 2.0, 1.7)), color=FELDGRAU); S.add(*gbox((1.86, 0, 1.95), (0.04, 1.7, 0.6)), color=DARKC)
    S.add(*gbox((-1.3, 0, 1.15), (3.6, 2.2, 0.5)), color=FELDGRAU); S.add(*gbox((-1.3, 0, 2.0), (3.5, 2.15, 1.25)), color=CANVAS); S.add(*gbox((0.2, 0, 0.75), (5.6, 0.9, 0.3)), color=DARKC)
    for wx in (2.2, -1.9):
        for sg in (1, -1):
            S.add(*revolve([(-0.13, 0.0), (-0.13, 0.42), (0.13, 0.42), (0.13, 0.0)], 14, axis=EY, origin=(wx, sg * 0.92, 0.42), side=EX), color=TYRE)
    return S.mesh("lorry", sharp=math.radians(40))

def _tower(S, x, y):
    for sx in (-1, 1):
        for sy in (-1, 1):
            S.add(*gbox((x + sx * 1.3, y + sy * 1.3, 4.0), (0.22, 0.22, 8.0)), color=TIMBER)
    S.add(*gbox((x, y, 8.1), (3.4, 3.4, 0.2)), color=TIMBER); S.add(*gbox((x, y, 8.7), (3.2, 3.2, 1.0)), color=TIMBER); S.add(*gbox((x, y, 10.6), (4.0, 4.0, 0.2)), color=ROOF2)

class Base:
    def __init__(self, sc, col):
        rng = np.random.default_rng(7); np.random.seed(7); self.col = col; env.make_world(sc)
        self.mat = bpy.data.materials.get("SitePaint") or paint_mat("SitePaint", rough=0.85, bump=0.35); gm = _ground_mat()
        xs = np.arange(-170.0, 170.01, 1.25); X, Y = np.meshgrid(xs, xs, indexing="ij"); Rr = np.hypot(X, Y); cols = _ground_cols(X, Y); F = grid_faces(len(xs), len(xs))
        Z0 = 0.05 * (fbm(X * 0.08, Y * 0.08, 3, 3) - 0.5) * np.clip(Rr / 20.0, 0, 1)
        self.g0 = new_obj("Ground", new_mesh("ground", np.stack([X, Y, Z0], -1).reshape(-1, 3), [F], attrs={"col": cols.reshape(-1, 4)}), col, gm)
        wob = 1.0 + 0.10 * np.sin(3 * np.arctan2(Y, X) + 1.0) + 0.06 * np.sin(7 * np.arctan2(Y, X)); Z1 = Z0 + crater_z(Rr / wob); c1 = cols.copy()               # the same ground with the crater in it
        k = np.clip((RC * 2.6 - Rr) / (RC * 1.3), 0, 1)[..., None]; soil = np.where((fbm(X * 0.5, Y * 0.5, 5, 3) > 0.5)[..., None], np.array(SOIL, np.float32), np.array(SOIL2, np.float32)); c1 = c1 * (1 - k) + soil * k
        self.g1 = new_obj("GroundCrater", new_mesh("ground_crater", np.stack([X, Y, Z1], -1).reshape(-1, 3), [F], attrs={"col": c1.reshape(-1, 4).astype(np.float32)}), col, gm)
        Ff = 9.0e5; V = []; Q = []                                                                                    # the country round the depot, out to the horizon
        for (x0, x1, y0, y1) in ((-Ff, -170.0, -Ff, Ff), (170.0, Ff, -Ff, Ff), (-170.0, 170.0, -Ff, -170.0), (-170.0, 170.0, 170.0, Ff)):
            n = len(V); V += [(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)]; Q.append([n, n + 1, n + 2, n + 3])
        new_obj("GroundFar", new_mesh("ground_far", np.array(V, float), [np.array(Q)], smooth=False, attrs={"col": np.tile(np.array(GRASS, np.float32), (len(V), 1))}), col, gm)
        # ---- buildings (those inside the blast circle are wrecked by it), towers, fence
        S = Shell(); self.near = []
        for k_, (x, y, lx, ly, h, roof, cw) in enumerate(BUILDINGS):
            d = math.hypot(x, y) - 0.5 * min(lx, ly)
            if d < C.R_STRUCT * 1.15:
                B = Shell(); _building(B, x, y, lx, ly, h, roof, cw); ob = new_obj("Near%d" % k_, B.mesh("near%d" % k_, sharp=math.radians(30)), col, self.mat)
                g = Geo()
                for j in range(int(lx * ly * 0.55)):
                    s_ = float(rng.uniform(0.3, 1.1)); env.rock_geo(g, rng, (x + float(rng.uniform(-lx, lx)) * 0.62, y + float(rng.uniform(-ly, ly)) * 0.62, s_ * 0.3), s_, 2, [cw, (0.20, 0.19, 0.17, 1), TIMBER, ROOF][j % 4])
                rub = new_obj("Rubble%d" % k_, g.mesh("rubble%d" % k_), col, env.mat_vcol("RubbleMat%d" % k_, rough=0.9, bump_scale=6))
                W_ = Shell()
                for j in range(6):                                     # stumps of wall left standing
                    sx, sy = [(-1, -1), (1, -1), (1, 1), (-1, 1), (0, -1), (0, 1)][j]; hh = float(rng.uniform(0.6, 2.0)); W_.add(*gbox((x + sx * lx / 2 * 0.96, y + sy * ly / 2 * 0.96, hh / 2), (float(rng.uniform(2, 5)), 0.5, hh)), color=cw)
                st = new_obj("Stumps%d" % k_, W_.mesh("stumps%d" % k_), col, self.mat); self.near.append((ob, [rub, st], max(d, 5.0)))
            else:
                _building(S, x, y, lx, ly, h, roof, cw)
        for (x, y) in ((-150, -150), (150, -150), (150, 150), (-150, 150), (0, -150), (0, 150)):
            _tower(S, x, y)
        for t in np.arange(-156.0, 156.01, 6.0):                                                                      # fence posts and rails
            for (x, y) in ((t, -156.0), (t, 156.0), (-156.0, t), (156.0, t)):
                S.add(*gbox((x, y, 1.1), (0.14, 0.14, 2.2)), color=TIMBER)
        for (x, y, sx, sy) in ((0, -156, 312, 0.05), (0, 156, 312, 0.05), (-156, 0, 0.05, 312), (156, 0, 0.05, 312)):
            for z in (0.9, 1.9):
                S.add(*gbox((x, y, z), (sx, sy, 0.05)), color=DARKC)
        for k_ in range(60):                                                                                          # trees outside the fence: dark rounded masses
            a_ = float(rng.uniform(0, 6.283)); r = float(rng.uniform(190, 520)); s_ = float(rng.uniform(4, 8)); S.add(*revolve([(0.0, 0.0), (s_ * 0.5, s_ * 0.62), (s_ * 1.1, s_ * 0.55), (s_ * 1.5, 0.0)], 9, axis=EZ, origin=(r * math.cos(a_), r * math.sin(a_), 1.5)), color=(0.030, 0.050, 0.022, 1))
        self.fixed = new_obj("Depot", S.mesh("depot", sharp=math.radians(30)), col, self.mat)
        # ---- lorries: those near the burst are thrown aside, the others stay
        lm = _lorry_mesh(); lm.materials.append(self.mat); self.lorries = []
        for k_, (x, y, yaw) in enumerate(LORRIES):
            ob = bpy.data.objects.new("Lorry%d" % k_, lm); col.objects.link(ob); d = math.hypot(x, y)
            q0 = Quaternion((0, 0, 1), yaw); ob.rotation_mode = 'QUATERNION'; ob.location = (x, y, 0.0); ob.rotation_quaternion = q0
            if d < C.R_STRUCT * 1.3:
                v = 34.0 * (1.0 - d / (C.R_STRUCT * 1.6)); rest = q0 @ Quaternion((1, 0, 0), float(rng.choice([math.pi / 2, -math.pi / 2, math.pi])))
                pc = Piece(ob, (x, y, 0.9), (x / d * v, y / d * v, v * 0.75), (-y / d, x / d, 0.2), float(rng.uniform(2.5, 5.0)), 0.9, tuple(rest), drag=0.5); self.lorries.append((ob, pc, q0, d))
        # ---- the hole it goes in by, clods round the crater, earth thrown out
        hm, N, L, P = nodemat("EntryHole"); P.inputs["Base Color"].default_value = (0.012, 0.011, 0.010, 1); P.inputs["Roughness"].default_value = 1.0
        a = np.linspace(0, 2 * np.pi, 24, endpoint=False); V = np.vstack([[[0, 0, 0.06]], [[0.8 * math.cos(t) * (1 + 0.2 * math.sin(3 * t)), 0.8 * math.sin(t) * (1 + 0.2 * math.sin(3 * t)), 0.06] for t in a]]); k = np.arange(24)
        self.hole = new_obj("EntryHole", new_mesh("entry_hole", V, [np.stack([np.zeros(24, int), 1 + k, 1 + (k + 1) % 24], 1)], smooth=False), col, hm); self.hole.visible_shadow = False
        g = Geo()
        for k_ in range(420):
            a_ = float(rng.uniform(0, 6.283)); r = float(RC * rng.uniform(0.25, 3.4)); s_ = float(rng.uniform(0.25, 1.3) * (1.25 - r / (RC * 3.6)))
            env.rock_geo(g, rng, (r * math.cos(a_), r * math.sin(a_), float(crater_z(r)) + s_ * 0.25), s_, 2, [(0.15, 0.11, 0.07, 1), (0.20, 0.155, 0.10, 1), (0.105, 0.078, 0.05, 1)][k_ % 3])
        self.clods = new_obj("Clods", g.mesh("clods"), col, env.mat_vcol("ClodMat", rough=0.95, bump_scale=6))
        self.thrown = []
        for k_ in range(90):
            B = Shell(); s = rng.uniform(0.4, 1.6, 3) * np.array([1.0, 0.8, 0.6]); B.add(*gbox((0, 0, 0), s), color=SOIL if k_ % 2 else SOIL2); ob = new_obj("Clod%d" % k_, B.mesh("clod%d" % k_), col, self.mat)
            a_ = rng.uniform(0, 6.283); el = math.radians(rng.uniform(40, 86)); v = rng.uniform(35, 120); r = rng.uniform(1.0, RC * 0.8)
            self.thrown.append(Piece(ob, (r * math.cos(a_), r * math.sin(a_), 0.5), (v * math.cos(a_) * math.cos(el), v * math.sin(a_) * math.cos(el), v * math.sin(el)), tuple(rng.uniform(-1, 1, 3)), rng.uniform(-7, 7), 0.3, tuple(Quaternion(Vector(rng.uniform(-1, 1, 3)).normalized(), rng.uniform(0, 3))), drag=0.22))
        self.update(-1.0)

    def update(self, tp):
        td = tp - C.FUZE_DELAY; fired = bool(td >= 0.06)
        self.g0.hide_render = fired; self.g1.hide_render = not fired; self.clods.hide_render = not fired; self.hole.hide_render = bool(tp < 0.0 or fired)
        for ob, wreck, d in self.near:                                  # the blast and the falling earth reach a building after about d / 250 seconds
            gone = bool(td > 0.08 + d / 250.0); ob.hide_render = gone
            for w in wreck:
                w.hide_render = not gone
        for ob, pc, q0, d in self.lorries:
            go = td > d / 300.0; p, q = pc.at(td - d / 300.0); ob.location = p if go else (pc.p0[0], pc.p0[1], 0.0); ob.rotation_quaternion = (q @ q0) if go else q0; ob.hide_render = bool(fired and d < RC * 1.05)
        for pc in self.thrown:
            p, q = pc.at(td - 0.05); pc.ob.location = p; pc.ob.rotation_quaternion = q; pc.ob.hide_render = bool(td <= 0.05)
