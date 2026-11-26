"""A second target for the MOAB segment: an invented ruined city, the whole of it (MOAB_SITE=city).

Nobody is modelled, and it is no real place.  A city about 9 km across on flat ground: a centre of older blocks
round courtyards with a few towers; apartment districts of five- and nine-storey slabs of the Soviet large-panel
kind, each on its own street grid; a steel works and another factory district (long halls, chimneys, tanks); a river
with three road bridges, two of them broken; a railway; parks; and wide outskirts of small houses.  All of it is
already burnt out and partly fallen in before the bomb arrives, as in the cities fought over in eastern Ukraine.
The drop itself is hypothetical: this bomb has never been used on a city.

What the blast does to each building follows from the pressure calculated for its distance (aconst.psi): at 10 psi
and more it comes down; from 5 to 10 psi about half of it comes down; from 2 to 5 psi it loses a floor here and
there; below that the shell stands.  Those thresholds are general published guidance for concrete buildings under
long blasts; a blast as short as this one does less at the same peak pressure, so they are if anything too severe.
Buildings shelter one another and channel the blast along streets; none of that is worked out.

Same interface as asite: ground, Site (with comps and update), AirFloor, target, CAM_H.  Buildings within 700 m of
the burst are separate objects (those the blast changes have a second, damaged form); the rest of the city is merged
into a few large meshes.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire", "tomahawk-sub"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
from mathutils import Quaternion
from qgeo import Shell, box as gbox, revolve, paint_mat, EZ
from util import new_mesh, new_obj, grid_faces, nodemat, smoothstep, fbm, Geo
import env
import aconst as C
import asite as _valley

env.SUN_ELEV = math.radians(30.0)
CAM_H = 150.0                                                         # the strike is seen from a drone's height
FLOOR_H = 2.8; BAY = 3.2; SEG = 2 * BAY                               # storey height, window spacing, one stair-section's width
SX, SY = 150.0, 115.0; X0S, Y0S = -70.0, -55.0                        # the street grid of the district the bomb falls on (the burst is in a courtyard)
NEAR = 700.0                                                          # buildings nearer the burst than this are objects of their own
CENTRE = (900.0, 400.0)                                               # the middle of the city; the burst is in an apartment district south-west of it
RIVER_HW = 60.0
WALLS = ((0.42, 0.41, 0.38), (0.47, 0.44, 0.38), (0.36, 0.36, 0.35), (0.44, 0.38, 0.32)); OLD = ((0.46, 0.40, 0.30), (0.42, 0.33, 0.26), (0.50, 0.46, 0.38), (0.38, 0.30, 0.25)); RUST = ((0.20, 0.19, 0.185), (0.24, 0.17, 0.12), (0.17, 0.18, 0.19), (0.28, 0.26, 0.23))
CONC = ((0.215, 0.213, 0.205, 0), (0.17, 0.17, 0.165, 0), (0.255, 0.245, 0.23, 0)); ASPHALT = (0.060, 0.060, 0.063, 0)
# the districts: middle, kind, angle of the street grid (degrees), weight in deciding which district a place belongs to
SEEDS = [(0.0, 0.0, "panel", 0.0, 1.0), (1500.0, 550.0, "centre", 8.0, 0.80), (-1800.0, 650.0, "panel", -14.0, 1.0), (350.0, -1650.0, "panel", 20.0, 1.0), (2750.0, -650.0, "panel", -8.0, 1.0),
         (900.0, 2650.0, "panel", 12.0, 1.0), (-2500.0, -1000.0, "panel", 6.0, 0.9), (3350.0, 1300.0, "works", -5.0, 1.05), (-1500.0, -2500.0, "works", 15.0, 0.75),
         (-3400.0, 1500.0, "houses", 25.0, 1.0), (2300.0, -2400.0, "houses", -20.0, 1.0), (-300.0, 3300.0, "houses", -10.0, 1.0), (4200.0, 100.0, "houses", 10.0, 0.9), (-800.0, -3200.0, "houses", 5.0, 0.9),
         (2000.0, 3200.0, "houses", 30.0, 1.0), (-3800.0, -300.0, "houses", -18.0, 1.0), (750.0, -760.0, "park", 0.0, 0.42), (-1000.0, 1750.0, "park", 0.0, 0.40), (2350.0, 1250.0, "park", 0.0, 0.36)]
GRID = {"panel": (150.0, 115.0), "centre": (120.0, 96.0), "houses": (132.0, 66.0), "works": (430.0, 310.0), "park": (150.0, 150.0)}
LABELS = {"centre": (1500.0, 550.0, 45.0), "works": (3350.0, 1300.0, 70.0), "houses": (-3400.0, 1500.0, 15.0), "river": (-500.0, 1300.0, 5.0)}

def ground(x, y, fine=1):
    x = np.asarray(x, float); y = np.asarray(y, float); return 0.12 * (fbm(x / 23.0, y / 23.0, 5, 2) - 0.5) * fine + 0.0 * x

def target(k=0):
    return np.array([0.0, 0.0, 3.0])

def edge_r(th):
    return 3550.0 * (1 + 0.16 * math.sin(2 * th + 0.6) + 0.09 * math.sin(3 * th + 2.0) + 0.06 * math.sin(5 * th + 1.0))

def inside(x, y, m=0.0):
    dx = (x - CENTRE[0]) / 1.25; dy = y - CENTRE[1]; return math.hypot(dx, dy) < edge_r(math.atan2(dy, dx)) - m

def river_y(x):
    return 1500.0 + 420.0 * np.sin(x / 1500.0 + 0.4) + 150.0 * np.sin(x / 520.0 + 1.0)

def rail_y(x):
    return -2250.0 + 0.10 * x

def free(x, y):
    """Not in the river, on the railway or on a bridge's approach."""
    return abs(y - float(river_y(x))) > RIVER_HW + 28.0 and abs(y - rail_y(x)) > 24.0

def district(x, y):
    return int(np.argmin([math.hypot(x - sx, y - sy) / w for (sx, sy, k, a, w) in SEEDS]))

def _rot(a):
    c, s = math.cos(a), math.sin(a); return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])

def facade_mat():
    """Walls with rows of window openings worked out from position: 'col' gives the wall's colour, alpha 0 switches the windows off (rubble, streets, sheds)."""
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
    ax = M('GREATER_THAN', M('ABSOLUTE', sn.outputs["X"]), 0.707); u = M('ADD', M('MULTIPLY', sp.outputs["Y"], ax), M('MULTIPLY', sp.outputs["X"], M('SUBTRACT', 1.0, ax)))     # along the wall
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

def fields_mat():
    m = bpy.data.materials.get("Fields")
    if m:
        return m
    m, N, L, P = nodemat("Fields"); tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1 / 520.0, 1 / 380.0, 1.0); L.new(tc.outputs["Object"], mp.inputs["Vector"])
    vo = N.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 1.0; L.new(mp.outputs[0], vo.inputs["Vector"]); cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.interpolation = 'CONSTANT'; e = cr.color_ramp.elements
    e[0].position = 0.0; e[0].color = (0.075, 0.095, 0.045, 1); e[1].position = 0.30; e[1].color = (0.150, 0.130, 0.080, 1)
    for pos, c in ((0.52, (0.095, 0.110, 0.055, 1)), (0.72, (0.180, 0.160, 0.100, 1)), (0.88, (0.060, 0.080, 0.045, 1))):
        el = e.new(pos); el.color = c
    sep = N.new("ShaderNodeSeparateColor"); L.new(vo.outputs["Color"], sep.inputs[0]); L.new(sep.outputs[0], cr.inputs["Fac"]); L.new(cr.outputs["Color"], P.inputs["Base Color"]); P.inputs["Roughness"].default_value = 0.95
    return m

def _heap(S, rng, x, y, sx, sy, hmax, ang=0.0, lite=False):
    """What is left of a fallen section: a heap of concrete with floor slabs lying on it at all angles."""
    h = float(rng.uniform(0.35, 1.0)) * hmax; S.add(*gbox((x, y, h / 2 - 0.3), (sx * rng.uniform(0.95, 1.25), sy * rng.uniform(1.1, 1.6), h + 0.6), rot=_rot(ang + rng.uniform(-0.12, 0.12))), color=CONC[int(rng.integers(0, 3))])
    for k in range(1 if lite else 4):
        a = rng.uniform(0, 3.14); t = rng.uniform(-0.5, 0.5); c, s = math.cos(a), math.sin(a); ct, st_ = math.cos(t), math.sin(t)
        R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]]) @ np.array([[ct, 0, st_], [0, 1, 0], [-st_, 0, ct]])
        S.add(*gbox((x + rng.uniform(-0.5, 0.5) * sx, y + rng.uniform(-0.7, 0.7) * sy, h * rng.uniform(0.5, 1.0) + 0.3), (rng.uniform(2.5, 5.5), rng.uniform(2.0, 3.2), 0.22), rot=R), color=CONC[k % 3])

def _add(S, b, floors, lite=False):
    """One building from its sections' heights in storeys (0 = fallen)."""
    rng = np.random.default_rng(b["seed"] + 7); fh = b["fh"]; R = _rot(b["ang"])
    for (x, y, sx, sy), f in zip(b["segs"], floors):
        if f >= 1:
            h = f * fh; S.add(*gbox((x, y, h / 2 - 0.25), (sx, sy, h + 0.5), rot=R), color=b["wall"])
        else:
            _heap(S, rng, x, y, sx, sy, min(1.0 + 0.16 * b["floors"] * fh, 4.5), b["ang"], lite)

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

def _plan(rng):
    """The whole city: buildings (dicts), the yards of the blocks, the small houses, chimneys and tanks, park trees."""
    blds = []; yards = []; houses = []; stacks = []; trees = []
    for di, (sx0, sy0, kind, deg, w) in enumerate(SEEDS):
        ang = math.radians(deg); R = _rot(ang)[:2, :2]; gx, gy = GRID[kind]; o = np.array([5.0, 2.5]) if di == 0 else np.array([sx0, sy0]); n = int(3200.0 / min(gx, gy)) + 1
        W = lambda u, v, c: c + R @ np.array([u, v])
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                c = o + R @ np.array([i * gx, j * gy])
                if math.hypot(c[0] - sx0, c[1] - sy0) > 3300.0 or district(c[0], c[1]) != di or not inside(c[0], c[1], 40.0):
                    continue
                home = di == 0 and i == 0 and j == 0; q = float(rng.uniform(0.4, 1.0))
                def slab(u, v, ln, along_u, floors, depth=12.0, pal=WALLS, fh=FLOOR_H, seg=SEG, plain=False):
                    m = max(int(round(ln / seg)), 2); segs = []
                    for k in range(m):
                        off = (k - (m - 1) / 2) * seg; p = W(u + off, v, c) if along_u else W(u, v + off, c)
                        if free(p[0], p[1]):
                            segs.append((float(p[0]), float(p[1]), seg if along_u else depth, depth if along_u else seg))
                    if len(segs) >= 2:
                        col = np.array(pal[int(rng.integers(0, len(pal)))]) * float(rng.uniform(0.58, 1.0))         # many walls are blackened by fire
                        blds.append(dict(segs=segs, ang=ang, floors=floors, fh=fh, x=float(np.mean([s[0] for s in segs])), y=float(np.mean([s[1] for s in segs])), wall=(float(col[0]), float(col[1]), float(col[2]), 0.0 if plain else 1.0),
                                         seed=int(rng.integers(0, 1 << 30)), ruin=q * float(rng.uniform(0.7, 1.0))))
                if kind == "park":
                    yards.append((float(c[0]), float(c[1]), gx + 1.0, gy + 1.0, ang, kind))
                    for k in range(26):
                        p = W(rng.uniform(-gx / 2, gx / 2), rng.uniform(-gy / 2, gy / 2), c)
                        if free(p[0], p[1]):
                            trees.append((float(p[0]), float(p[1]), float(rng.uniform(5.0, 11.0))))
                    continue
                yards.append((float(c[0]), float(c[1]), gx - 14.0, gy - 12.0, ang, kind))
                if kind == "panel":
                    kd = 0 if home else int(rng.integers(0, 4)); tall = lambda: 9 if rng.uniform() < 0.28 else 5
                    if kd in (0, 1):                                   # two long slabs along the streets, one across the end: a courtyard between them
                        slab(rng.uniform(-6, 6) * (not home), 38.0, float(rng.uniform(96, 118)), True, tall()); slab(rng.uniform(-6, 6) * (not home), -38.0, float(rng.uniform(96, 118)), True, tall()); slab(60.0 if rng.uniform() < 0.5 else -60.0, 0.0, 50.0, False, 5)
                    elif kd == 2:                                      # slabs side by side, end on to the street
                        for du in (-46.0, 0.0, 46.0):
                            slab(du, rng.uniform(-5, 5), float(rng.uniform(64, 84)), False, tall())
                    else:                                              # a school or a shop, and one slab
                        slab(-30.0, -18.0, 52.0, True, 2, depth=26.0); slab(10.0, 36.0, float(rng.uniform(84, 108)), True, tall())
                elif kind == "centre":                                 # older blocks built round their courtyards; now and then a tower
                    fl = int(rng.integers(4, 7)); slab(0.0, gy / 2 - 16.0, gx - 34.0, True, fl, 14.0, OLD); slab(0.0, -gy / 2 + 16.0, gx - 34.0, True, fl, 14.0, OLD)
                    slab(gx / 2 - 17.0, 0.0, gy - 58.0, False, fl, 14.0, OLD); slab(-gx / 2 + 17.0, 0.0, gy - 58.0, False, int(rng.integers(3, 6)), 14.0, OLD)
                    if rng.uniform() < 0.16:
                        slab(0.0, 0.0, 22.0, True, int(rng.integers(11, 17)), 22.0, WALLS, seg=11.0)
                elif kind == "works":                                  # long sheds, chimneys, tanks
                    v = -gy / 2 + 60.0
                    for h in range(int(rng.integers(2, 4))):
                        wd = float(rng.uniform(44, 70)); slab(rng.uniform(-30, 30), v + wd / 2, float(rng.uniform(190, 340)), True, 3, wd, RUST, fh=float(rng.uniform(5.5, 8.0)), seg=22.0, plain=True); v += wd + float(rng.uniform(26, 50))
                    for k in range(int(rng.integers(1, 4))):
                        p = W(rng.uniform(-gx / 2 + 30, gx / 2 - 30), gy / 2 - rng.uniform(14, 40), c)
                        if free(p[0], p[1]):
                            stacks.append((float(p[0]), float(p[1]), 3.6, float(rng.uniform(55, 110)) * (0.4 if rng.uniform() < 0.25 else 1.0), 0))
                    for k in range(int(rng.integers(0, 4))):
                        p = W(-gx / 2 + 24.0 + 30.0 * k, gy / 2 - 70.0, c)
                        if free(p[0], p[1]):
                            stacks.append((float(p[0]), float(p[1]), 11.0, float(rng.uniform(9, 15)), 1))
                else:                                                  # two rows of small houses, back to back
                    for sv in (-1, 1):
                        for u in np.arange(-gx / 2 + 16.0, gx / 2 - 10.0, 21.0):
                            p = W(u + rng.uniform(-2, 2), sv * 15.0 + rng.uniform(-2, 2), c)
                            if free(p[0], p[1]) and rng.uniform() < 0.9:
                                houses.append((float(p[0]), float(p[1]), ang + (math.pi / 2 if rng.uniform() < 0.3 else 0.0), float(rng.uniform(7.5, 10.5)), float(rng.uniform(9.0, 13.0)), int(rng.choice([0, 1, 1, 2, 2, 3])), int(rng.integers(0, 4)), float(rng.uniform(0.55, 1.0))))
    return blds, yards, houses, stacks, trees

def _houses(houses):
    """Small houses in one mesh.  State 0 roofed, 1 and 2 burnt out (walls only), 3 fallen in."""
    S = Shell()
    for (x, y, a, w, l, st, ci, dk) in houses:
        R = _rot(a); col = tuple(np.array(OLD[ci]) * dk * (0.6 if st in (1, 2) else 1.0)) + (1.0,)
        if st == 3:
            S.add(*gbox((x, y, 0.35), (w * 1.1, l * 1.1, 0.9), rot=R), color=CONC[ci % 3]); continue
        hw = 3.3; S.add(*gbox((x, y, hw / 2 - 0.2), (w, l, hw + 0.4), rot=R), color=col)
        if st == 0:                                                    # a gable roof
            P = np.array([[-w / 2 - 0.3, -l / 2 - 0.3, hw], [w / 2 + 0.3, -l / 2 - 0.3, hw], [0, -l / 2 - 0.3, hw + 2.3], [-w / 2 - 0.3, l / 2 + 0.3, hw], [w / 2 + 0.3, l / 2 + 0.3, hw], [0, l / 2 + 0.3, hw + 2.3]]) @ R.T + np.array([x, y, 0.0])
            S.add(P, [[0, 3, 5, 2], [1, 2, 5, 4]], [[0, 2, 1], [3, 4, 5]], (0.16 * dk, 0.10 * dk, 0.08 * dk, 0.0))
    return S

class City:
    def __init__(self, sc, col, air=False):
        rng = np.random.default_rng(31); self.col = col; env.make_world(sc); fm = facade_mat(); self.root = bpy.data.objects.new("City", None); col.objects.link(self.root)
        def put(name, me, mat):
            ob = new_obj(name, me, col, mat); ob.parent = self.root; return ob
        blds, yards, houses, stacks, trees = _plan(rng); self.count = dict(buildings=len(blds), houses=len(houses), blocks=len(yards))
        # ---- the ground: farmland, the city's own ground, the yards of the blocks (the streets are what is left between them)
        xs = np.concatenate([-np.geomspace(300000.0, 7000.0, 14), np.arange(-6000.0, 6000.1, 1000.0), np.geomspace(7000.0, 300000.0, 14)]); X, Y = np.meshgrid(xs, xs, indexing="ij")
        self.ground = put("Ground", new_mesh("city_ground", np.stack([X, Y, 0 * X], -1).reshape(-1, 3), [grid_faces(len(xs), len(xs))]), fields_mat())
        S = Shell(); th = np.linspace(0, 2 * np.pi, 180, endpoint=False); V = np.array([[CENTRE[0], CENTRE[1], 0.04]] + [[CENTRE[0] + 1.25 * (edge_r(t) + 60.0) * math.cos(t), CENTRE[1] + (edge_r(t) + 60.0) * math.sin(t), 0.04] for t in th]); k = np.arange(180)
        S.add(V, None, np.stack([np.zeros(180, int), 1 + k, 1 + (k + 1) % 180], 1), (0.062, 0.060, 0.058, 0))
        YC = {"panel": (0.135, 0.122, 0.092, 0), "centre": (0.115, 0.108, 0.095, 0), "houses": (0.105, 0.112, 0.070, 0), "works": (0.088, 0.082, 0.078, 0), "park": (0.085, 0.100, 0.055, 0)}
        for (x, y, w, d, a, kind) in yards:
            S.add(*gbox((x, y, 0.07), (w, d, 0.10), rot=_rot(a)), color=YC[kind])
        xr = np.arange(-7000.0, 8000.1, 40.0); yr = river_y(xr)                                                    # the railway and, on top, nothing else: its bed only
        for xa, xb in zip(np.arange(-5200.0, 6200.0, 200.0), np.arange(-5000.0, 6400.0, 200.0)):
            if inside(xa, rail_y(xa), -400.0):
                S.add(*gbox(((xa + xb) / 2, rail_y((xa + xb) / 2), 0.12), (201.0, 26.0, 0.16), rot=_rot(math.atan(0.10))), color=(0.075, 0.066, 0.058, 0))
        put("CityFloor", S.mesh("city_floor"), fm)
        wm, N, L, P = nodemat("RiverWater"); P.inputs["Base Color"].default_value = (0.020, 0.034, 0.040, 1); P.inputs["Roughness"].default_value = 0.12
        Vw = np.concatenate([np.stack([xr, yr - RIVER_HW, np.full_like(xr, 0.22)], 1), np.stack([xr, yr + RIVER_HW, np.full_like(xr, 0.22)], 1)]); n = len(xr); k = np.arange(n - 1)
        put("River", new_mesh("river", Vw, [np.stack([k, k + 1, k + 1 + n, k + n], 1)]), wm)
        S = Shell()                                                    # three road bridges; the middle spans of two of them lie in the water
        for bi, bx in enumerate((-1500.0, 700.0, 2500.0)):
            by = float(river_y(bx)); L_ = 2 * RIVER_HW + 50.0
            for k, v in enumerate((-L_ / 3, 0.0, L_ / 3)):
                broken = k == 1 and bi != 1; t = 0.22 if broken else 0.0; c, s_ = math.cos(t), math.sin(t)
                S.add(*gbox((bx, by + v, 3.2 - (4.2 if broken else 0.0) * 0.5), (13.0, L_ / 3 + 0.5, 1.1), rot=np.array([[1, 0, 0], [0, c, -s_], [0, s_, c]])), color=CONC[k % 3])
            for v in (-L_ / 6, L_ / 6):
                S.add(*gbox((bx, by + v, 1.2), (9.0, 3.0, 3.6)), color=CONC[1])
        for (x, y, r, h, tank) in stacks:                              # chimneys and tanks
            prof = [(0.0, r), (h, r)] + ([(h, 0.0)] if tank else []) if tank else [(0.0, r), (h, r * 0.62), (h, r * 0.45)]
            Vv, Q, T = revolve(prof, 14, axis=EZ, origin=(x, y, 0.0)); S.add(Vv, Q, T, (0.17, 0.165, 0.16, 0) if tank else (0.22, 0.14, 0.10, 0))
        for (x, y, h) in trees:                                        # the parks' trees, bare
            a = float(rng.uniform(0, 3.1)); S.add(*gbox((x, y, h * 0.3), (0.5, 0.5, h * 0.6), rot=_rot(a)), color=(0.07, 0.055, 0.04, 0))
            for sg in (-1, 1):
                t = sg * 0.6; c, s_ = math.cos(t), math.sin(t); S.add(*gbox((x + sg * h * 0.14 * math.cos(a), y + sg * h * 0.14 * math.sin(a), h * 0.72), (0.3, 0.3, h * 0.5), rot=_rot(a) @ np.array([[c, 0, s_], [0, 1, 0], [-s_, 0, c]])), color=(0.07, 0.055, 0.04, 0))
        put("CityExtras", S.mesh("city_extras", sharp=math.radians(40)), fm)
        put("CityHouses", _houses(houses).mesh("city_houses", sharp=math.radians(40)), fm)
        # ---- buildings: far ones merged; near ones as they stand before the bomb, and as it leaves them
        far = Shell(); self.comps = []; i = 0
        for b in blds:
            r = float(min(math.hypot(x, y) for (x, y, sx, sy) in b["segs"])); r0 = np.random.default_rng(b["seed"]); f0 = _ruin(r0, b)
            if r > NEAR or air:
                _add(far, b, f0, lite=True); continue
            p = float(C.psi(max(r, 5.0))); state = 3 if p >= 10.0 else (2 if p >= 5.0 else (1 if p >= 2.0 else 0)); S = Shell(); _add(S, b, f0); a = put("Bld%03d" % i, S.mesh("bld%03d" % i, sharp=math.radians(40)), fm); bo = None; drop = 0.0
            if state:
                f1 = _after(r0, f0, state); S = Shell(); _add(S, b, f1); bo = put("Bld%03d_after" % i, S.mesh("bld%03d_after" % i, sharp=math.radians(40)), fm); drop = 1.0 - (float(f1.sum()) + 0.6 * len(f1)) / (float(f0.sum()) + 0.6 * len(f0))
            self.comps.append(dict(a=a, b=bo, r=r, t=float(C.t_front(r)), state={3: 2, 2: 1, 1: 1, 0: 0}[state], lvl=state, x=b["x"], y=b["y"], z=b["floors"] * b["fh"], drop=drop)); i += 1
        put("CityFar", far.mesh("city_far", sharp=math.radians(40)), fm)
        self.trees = []; self.scorch = None; self.debris = None
        if air:
            return
        # ---- rubble in the streets and yards near the burst (there before the bomb), and what the bomb adds
        g = Geo(); g2 = Geo(); rm = env.mat_vcol("RubbleMat", rough=0.92, bump_scale=6); cols = [(0.26, 0.26, 0.25, 1), (0.20, 0.20, 0.195, 1), (0.31, 0.29, 0.26, 1)]
        for k in range(900):
            c = self.comps[int(rng.integers(0, len(self.comps)))]; x = c["x"] + float(rng.normal(0, 34.0)); y = c["y"] + float(rng.normal(0, 26.0)); s = float(rng.uniform(0.3, 1.3)); env.rock_geo(g, rng, (x, y, 0.1 * s), s, 2, cols[k % 3])
        for k in range(700):
            r = float(abs(rng.normal(0, 85.0))) + 8.0; a = float(rng.uniform(0, 6.283)); s = float(rng.uniform(0.3, 1.5)); env.rock_geo(g2, rng, (r * math.cos(a), r * math.sin(a), 0.1 * s), s, 2, cols[k % 3])
        put("Rubble", g.mesh("rubble"), rm); self.debris = put("Debris", g2.mesh("debris"), rm)
        # ---- trees along the streets near the burst: bare
        tm = bpy.data.materials.get("TreePaint") or paint_mat("TreePaint", rough=0.85, bump=0.3)
        for i in range(420):
            if i % 2:
                x = float(X0S + SX * int(rng.integers(-4, 5)) + (9.5 if rng.uniform() < 0.5 else -9.5)); y = float(rng.uniform(-NEAR, NEAR))
            else:
                y = float(Y0S + SY * int(rng.integers(-5, 6)) + (8.5 if rng.uniform() < 0.5 else -8.5)); x = float(rng.uniform(-NEAR, NEAR))
            r = math.hypot(x, y)
            if r < 16.0 or r > NEAR or district(x, y) != 0:
                continue
            k = int(rng.integers(0, 3)); me = _valley._tree_mesh(k, True)
            if not me.materials:
                me.materials.append(tm)
            ob = put("Tree%03d" % i, me, None); ob.rotation_mode = 'QUATERNION'; ob.location = (x, y, -0.1); s = float(rng.uniform(0.8, 1.2)); ob.scale = (s, s, s)
            self.trees.append(dict(ob=ob, r=r, d=np.array([x, y]) / r, t=float(C.t_front(r)), p=float(C.psi(r)), yaw=float(rng.uniform(0, 6.283)), j=float(rng.uniform(0, 1))))
        # ---- the ground under the fireball, burnt
        R1 = 0.75 * C.FB_D; a_ = np.linspace(0, 2 * np.pi, 72, endpoint=False); rr = np.linspace(0.0, R1, 16)[1:]; V = [[0.0, 0.0, 0.2]]; A = [[0.03, 0.028, 0.026, 0.92]]
        for q in rr:
            for t in a_:
                x = q * math.cos(t); y = q * math.sin(t); V.append([x, y, 0.2]); A.append([0.03, 0.028, 0.026, 0.92 * float(1 - smoothstep(0.45 * R1, R1, q * (1 + 0.25 * (fbm(x / 9.0, y / 9.0, 3, 3) - 0.5))))])
        n = len(a_); F3 = [[0, 1 + k, 1 + (k + 1) % n] for k in range(n)]; F4 = [[1 + j * n + k, 1 + (j + 1) * n + k, 1 + (j + 1) * n + (k + 1) % n, 1 + j * n + (k + 1) % n] for j in range(len(rr) - 1) for k in range(n)]
        self.scorch = put("Scorch", new_mesh("scorch", np.array(V), [np.array(F3), np.array(F4)], attrs={"col": np.array(A, np.float32)}), _valley._alpha_mat("ScorchMat")); self.scorch.visible_shadow = False
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
    """The same city from the aircraft, 6 km up: the whole of it is moved so that it slides past underneath."""
    def __init__(self, sc, col):
        self.city = City(sc, col, air=True); self.ob = self.city.root
    def set(self, t):
        p = C.ac_pos(t); self.ob.location = (-float(p[0]), 0.0, -float(p[2]))
