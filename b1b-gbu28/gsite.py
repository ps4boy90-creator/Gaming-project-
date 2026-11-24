"""The target: concrete chambers 17 m under a flat desert, from outside and as a section.

The bunker is invented, on the pattern described for the Iraqi command bunkers of 1991: about 50 ft of soil, a
two-foot slab of reinforced concrete laid over the whole complex, then the chambers; a stair down from a small
entrance building, and air shafts to the surface.  Nobody is modelled in it.

Outside(sc, col)   the plain with the entrance building and the two air shafts
Section(sc, col)   the same ground cut along the plane y = 0 and seen from the +Y side
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
import env, htown
import gconst as C

A0, A1 = C.ROOM_A; B0, B1 = C.ROOM_B; ZF = C.Z_FLOOR; ZC = C.Z_CEIL; ZR = C.Z_ROOF; ZS = C.Z_SLAB; W = C.WALL; CH = C.COR_H; CW = C.COR_W; S0 = C.STAIR_X[0]; EX0 = C.ENTR_X
LIN = 0.4; ST_H = 3.0; ST_LIN = 0.55; DEPTH = 5.0                     # lining; the stair's headroom and lining measured upright; how far the chambers reach behind the cut
VENTS = (A1 + 3.5, C.VENTS[1]); VR = C.VENT_R
SLAB_X = (S0 + 2.0, B1 + 6.0)
CONC = (0.50, 0.49, 0.46, 1); CONC2 = (0.40, 0.39, 0.37, 1); STEELC = (0.16, 0.18, 0.17, 1); DARKC = (0.02, 0.02, 0.02, 1)
HUT = (EX0 - 1.6, S0 - (-ZF - ST_H) + 1.2)                            # the entrance building stands over the head of the stair

def _ground_mat():
    m = env.mat_ground()
    for nd in m.node_tree.nodes:
        if nd.type == 'VALTORGB' and abs(nd.color_ramp.elements[0].color[0] - 0.160) < 1e-3:
            nd.color_ramp.elements[0].color = (0.250, 0.200, 0.140, 1); nd.color_ramp.elements[1].color = (0.470, 0.390, 0.280, 1)
    if "Blast" in m.node_tree.nodes:
        m.node_tree.nodes["Blast"].outputs[0].default_value = 0.0
    return m

def _plain(col, ymax=None):
    """Flat desert: a fine sheet round the bunker, a disc out to the hills and a ring out to the horizon."""
    m = _ground_mat(); xs = np.arange(-70.0, 50.01, 0.25); ys = np.arange(-36.0, (36.0 if ymax is None else ymax) + 1e-3, 0.25)
    X, Y = np.meshgrid(xs, ys, indexing="ij"); edge = np.minimum.reduce([X + 70, 50 - X, Y + 36, (36 - Y) if ymax is None else np.full_like(Y, 9.0)]); k = np.clip(edge / 4.0, 0, 1); k = k * k * (3 - 2 * k)
    Z = (0.03 * np.sin(X * 0.31 + 0.7) * np.cos(Y * 0.27 - 0.4) + 0.02 * (fbm(X * 1.7, Y * 1.7, 3, 4) - 0.5)) * k * np.clip(np.hypot(X, Y) / 3.0, 0, 1)
    near = new_obj("GroundNear", new_mesh("ground_near", np.stack([X, Y, Z], -1).reshape(-1, 3), [grid_faces(len(xs), len(ys))]), col, m)
    for name, r0, r1, n in (("GroundFar", 0.0, 2600.0, 2), ("GroundHuge", 2500.0, 9.0e5, 40)):
        na = 120; a = np.linspace(0, math.pi if ymax is not None else 2 * math.pi, na, endpoint=ymax is not None); rr = np.geomspace(max(r0, 30.0), r1, n) if r0 == 0 else np.geomspace(r0, r1, n)
        if r0 == 0:
            rr = np.concatenate([[0.0], rr])
        Aa, Rr = np.meshgrid(a, rr, indexing="ij"); V = np.stack([Rr * np.cos(Aa), -Rr * np.sin(Aa) if ymax is not None else Rr * np.sin(Aa), np.full_like(Aa, -0.03)], -1).reshape(-1, 3)
        o = new_obj(name, new_mesh(name.lower(), V, [grid_faces(na, len(rr), wrap_u=ymax is None)]), col, m)
        o.data.use_auto_texspace = False; o.data.texspace_location = (0.0, 0.0, -0.03); o.data.texspace_size = (2600.0, 2600.0, 1.0)
    return near

def _hut(S, half=False):
    """The entrance building: a low concrete box over the head of the stair, its doorway facing away from the bunker."""
    x0, x1 = HUT; h = 2.7; ys = (-1,) if half else (-1, 1); hw = CW / 2 + 0.5
    for sg in ys:
        S.add(*gbox(((x0 + x1) / 2, sg * (hw - 0.2), h / 2), (x1 - x0, 0.4, h)), color=CONC)                              # side wall
        S.add(*gbox(((x0 + x1) / 2, sg * hw / 2, h + 0.15), (x1 - x0 + 0.5, hw + 0.25, 0.3)), color=CONC2)                 # roof
        S.add(*gbox((x1 - 0.2, sg * hw / 2, h / 2), (0.4, hw, h)), color=CONC)                                             # back wall
        S.add(*gbox((x0 + 0.2, sg * (CW / 4 + hw / 2), h / 2), (0.4, hw - CW / 2, h)), color=CONC)                         # front wall beside the doorway
        S.add(*gbox((x0 + 0.2, sg * CW / 4, (2.2 + h) / 2), (0.4, CW / 2, h - 2.2)), color=CONC)                           # and over it

def _vent_cap(S, xv, y=0.0, half=False):
    a1 = math.pi if half else 2 * math.pi; n = 12 if half else 24; t = np.linspace(0, a1, n, endpoint=half)
    for (r0, r1, z0, z1, c) in ((VR + 0.05, VR + 0.30, 0.0, 0.9, CONC), (VR + 0.30, VR + 0.55, 0.9, 1.05, CONC2)):
        ring = lambda r, z: np.stack([xv + r * np.cos(t), y - r * np.sin(t) if half else y + r * np.sin(t), np.full_like(t, z)], 1)
        V = np.vstack([ring(r0, z0), ring(r1, z0), ring(r1, z1), ring(r0, z1)]); m = len(t); k = np.arange(m - 1 if half else m); k1 = (k + 1) % m; Q = []
        for a, b in ((0, 1), (1, 2), (2, 3), (3, 0)):
            Q.append(np.stack([a * m + k, a * m + k1, b * m + k1, b * m + k], 1))
        S.add(V, np.vstack(Q), None, c)

class Outside:
    def __init__(self, sc, col):
        rng = np.random.default_rng(7); np.random.seed(7); self.col = col; env.make_world(sc); _plain(col); htown.desert_hills(col, rng, 2.4)
        self.mat = bpy.data.materials.get("SitePaint") or paint_mat("SitePaint", rough=0.85, bump=0.4)
        S = Shell(); _hut(S)
        S.add(*gbox((HUT[0] + 2.2, 0, 1.1), (3.2, CW - 0.1, 2.2)), color=DARKC)                                                  # the dark of the stair behind the door
        for xv in VENTS:
            _vent_cap(S, xv); S.add(*gbox((xv, 0, 0.5), (2 * VR, 2 * VR, 0.9)), color=DARKC)
        g = Geo()
        for k in range(160):                                                                                              # stones on the plain
            x = float(rng.uniform(-65, 45)); y = float(rng.uniform(-32, 32)); s_ = float(min(np.exp(rng.normal(-2.4, 0.6)), 0.5))
            if abs(x) < 2 and abs(y) < 2:
                continue
            env.rock_geo(g, rng, (x, y, s_ * 0.2), s_, 2, [(0.15, 0.12, 0.09, 1), (0.20, 0.17, 0.14, 1), (0.10, 0.085, 0.07, 1)][k % 3])
        new_obj("Stones", g.mesh("stones"), col, env.mat_vcol("StoneMat", rough=0.9, bump_scale=6))
        self.fixed = new_obj("SurfaceFixed", S.mesh("surface_fixed"), col, self.mat)
        D_ = Shell(); D_.add(*gbox((0, 0, 0), (0.08, CW - 0.04, 2.15)), color=STEELC); ob = new_obj("HutDoor", D_.mesh("hut_door"), col, self.mat)
        self.door = Piece(ob, (HUT[0] - 0.05, 0.0, 1.1), (-19.0, 2.0, 5.0), (0.2, 1.0, 0.3), 6.0, 0.06, tuple(Quaternion((0, 1, 0), math.pi / 2)), drag=0.3)
        hm, N, L, P = nodemat("EntryHole"); P.inputs["Base Color"].default_value = (0.012, 0.011, 0.010, 1); P.inputs["Roughness"].default_value = 1.0
        a = np.linspace(0, 2 * np.pi, 24, endpoint=False); V = np.vstack([[[0, 0, 0.04]], [[0.5 * math.cos(t) * (1 + 0.2 * math.sin(3 * t)), 0.5 * math.sin(t) * (1 + 0.2 * math.sin(3 * t)), 0.04] for t in a]]); k = np.arange(24)
        self.hole = new_obj("EntryHole", new_mesh("entry_hole", V, [np.stack([np.zeros(24, int), 1 + k, 1 + (k + 1) % 24], 1)], smooth=False), col, hm); self.hole.visible_shadow = False
        g = Geo()                                                                                                         # the lip of earth thrown up round the hole
        for k in range(70):
            a_ = float(rng.uniform(0, 6.283)); r = float(rng.uniform(0.55, 2.4)); s_ = float(rng.uniform(0.08, 0.32) * (1.4 - r / 2.4))
            env.rock_geo(g, rng, (r * math.cos(a_), r * math.sin(a_), s_ * 0.3), s_, 2, [(0.20, 0.16, 0.11, 1), (0.27, 0.22, 0.16, 1), (0.15, 0.12, 0.09, 1)][k % 3])
        self.lip = new_obj("HoleLip", g.mesh("hole_lip"), col, env.mat_vcol("LipMat", rough=0.9, bump_scale=8))
        self.update(-1.0)

    def update(self, tp):
        """tp: seconds after the bomb touches the ground (the charge fires at FUZE_DELAY)."""
        td = tp - C.FUZE_DELAY; self.hole.hide_render = tp < 0.0; self.lip.hide_render = tp < 0.02
        p, q = self.door.at(td - T_DOOR); self.door.ob.location = p; self.door.ob.rotation_quaternion = q

T_DOOR = 0.16                                                          # the blast reaches the head of the stair about this long after the burst (staging)

# ----------------------------------------------------------------------------- the section
def _column(x):
    """What is solid along a vertical line at x on the plane of the section: [(z_low, z_high, kind)] from the bottom up."""
    zb = -48.0; conc = []; void = []
    if SLAB_X[0] <= x <= SLAB_X[1]:
        conc.append((ZS - C.SLAB, ZS))
    for r0, r1 in ((A0, A1), (B0, B1)):
        if r0 - W <= x <= r1 + W:
            conc.append((ZF - C.FLOOR, ZR))
        if r0 <= x <= r1:
            void.append((ZF, ZC))
    if S0 <= x <= A0 or A1 <= x <= B0:
        conc.append((ZF - LIN, ZF + CH + LIN)); void.append((ZF, ZF + CH))
    if HUT[0] <= x < S0:
        zs = ZF + (S0 - x); conc.append((zs - ST_LIN, min(zs + ST_H + ST_LIN, 0.0))); void.append((zs, min(zs + ST_H, 0.0)))
    for k, xv in enumerate(VENTS):
        if abs(x - xv) < VR:
            void.append(((ZF + CH) if k == 0 else ZC, 0.0))
    cuts = sorted(set([zb, 0.0] + [z for iv in conc + void for z in iv if zb < z < 0.0])); out = []
    for z0, z1 in zip(cuts[:-1], cuts[1:]):
        zm = (z0 + z1) / 2
        if any(a < zm < b for a, b in void):
            continue
        kind = "conc" if any(a < zm < b for a, b in conc) else "soil"
        if A0 < x < A1 and zm > ZC:
            continue                                                    # over the target chamber everything moves, so Section draws it frame by frame
        if out and out[-1][2] == kind and abs(out[-1][1] - z0) < 1e-9:
            out[-1] = (out[-1][0], z1, kind)
        else:
            out.append((z0, z1, kind))
    return out

def _face_mat(name, c0, c1, scale, stones=0.0, stretch=3.2):
    m, N, L, P = nodemat(name); tc = N.new("ShaderNodeTexCoord"); n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = 6; n.inputs["Roughness"].default_value = 0.62
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1.0, 1.0, stretch); L.new(tc.outputs["Object"], mp.inputs["Vector"]); L.new(mp.outputs[0], n.inputs["Vector"])
    r = N.new("ShaderNodeValToRGB"); e = r.color_ramp.elements; e[0].position = 0.34; e[0].color = (*c0, 1); e[1].position = 0.68; e[1].color = (*c1, 1); L.new(n.outputs["Fac"], r.inputs["Fac"])
    if stones:
        v = N.new("ShaderNodeTexVoronoi"); v.inputs["Scale"].default_value = stones; L.new(tc.outputs["Object"], v.inputs["Vector"]); st = N.new("ShaderNodeMapRange"); st.inputs["From Min"].default_value = 0.10; st.inputs["From Max"].default_value = 0.22
        st.inputs["To Min"].default_value = 0.62; st.inputs["To Max"].default_value = 1.0; L.new(v.outputs["Distance"], st.inputs["Value"]); mx = N.new("ShaderNodeMixRGB"); mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0
        L.new(r.outputs["Color"], mx.inputs[1]); L.new(st.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], P.inputs["Base Color"])
    else:
        L.new(r.outputs["Color"], P.inputs["Base Color"])
    P.inputs["Roughness"].default_value = 0.9
    return m

ROOF_DROP = 2.4

def shape(x):
    s = np.clip((np.asarray(x, float) - A0) / (A1 - A0), 0.0, 1.0); return np.sin(math.pi * s) ** 1.5

def zmove(td):
    """How far the target chamber's roof has moved at mid-span: a short lift from the gas, then down into the room (staging)."""
    if td <= 0:
        return 0.0
    return 0.30 * math.sin(math.pi * td / 0.30) if td < 0.30 else -ROOF_DROP * smoothstep(0.30, 1.45, td)

def level(z):
    """How much of that movement reaches height z: all of it at the roof, none at the surface 17 m above."""
    return np.where(np.asarray(z) <= ZS, 1.0 - 0.15 * np.clip((np.asarray(z) - ZR) / (ZS - ZR), 0, 1), 0.85 * (1.0 - np.clip((np.asarray(z) - ZS) / (0.0 - ZS), 0, 1)))

def _room(S, x0, x1, z0, z1, depth, col=CONC):
    """Concrete seen through a hollow in the cut: back wall, floor and ceiling of a space `depth` deep behind the plane."""
    S.add(*gbox(((x0 + x1) / 2, -depth - 0.15, (z0 + z1) / 2), (x1 - x0 + 0.6, 0.3, z1 - z0 + 0.6)), color=col)
    S.add(*gbox(((x0 + x1) / 2, -depth / 2, z0 - 0.15), (x1 - x0, depth, 0.3)), color=CONC2); S.add(*gbox(((x0 + x1) / 2, -depth / 2, z1 + 0.15), (x1 - x0, depth, 0.3)), color=col)
    for xw in (x0 - 0.15, x1 + 0.15):
        S.add(*gbox((xw, -depth / 2, (z0 + z1) / 2), (0.3, depth, z1 - z0)), color=col)

class Section:
    """Everything on and behind the cut.  The solid ground is the half y <= 0; the camera stands on the +Y side."""
    def __init__(self, sc, col):
        rng = np.random.default_rng(19); np.random.seed(19); self.col = col; env.make_world(sc); _plain(col, ymax=0.0); htown.desert_hills(col, rng, 2.4)
        self.mat = bpy.data.materials.get("SitePaint") or paint_mat("SitePaint", rough=0.85, bump=0.4)
        mats = self.mats = {"soil": _face_mat("CutSoil", (0.215, 0.165, 0.110), (0.385, 0.300, 0.205), 0.9, stones=2.2, stretch=5.0), "conc": _face_mat("CutConcrete", (0.36, 0.355, 0.34), (0.52, 0.51, 0.49), 5.0, stones=14.0, stretch=1.0)}
        e = 1e-3; brk = [SLAB_X[0], SLAB_X[1], A0 - W, A0, A1, A1 + W, B0 - W, B0, B1, B1 + W, S0, HUT[0], S0 + ZF + ST_H + ST_LIN, S0 + ZF + ST_H, S0 + ZF, S0 + ZF - ST_LIN] + [xv + s * VR for xv in VENTS for s in (-1, 1)]
        xs = sorted(set(list(np.arange(-150.0, 150.01, 1.0)) + [b + s * e for b in brk for s in (-1, 1)])); quads = {k: [] for k in mats}
        for xa, xb in zip(xs[:-1], xs[1:]):
            if xb - xa < 5 * e:
                continue
            ca = _column(xa + 2 * e); cb = _column(xb - 2 * e)
            if len(ca) != len(cb) or any(a[2] != b[2] for a, b in zip(ca, cb)):
                continue
            for (a0, a1, kind), (b0, b1, _) in zip(ca, cb):
                quads[kind].append([(xa, 0.003, a0), (xb, 0.003, b0), (xb, 0.003, b1), (xa, 0.003, a1)])
        for kind, qs in quads.items():
            V = np.array(qs, float).reshape(-1, 3); new_obj("Cut_" + kind, new_mesh("cut_" + kind, V, [np.arange(len(V)).reshape(-1, 4)], smooth=False), col, mats[kind])
        # ---- behind the cut
        S = Shell(); _room(S, A0, A1, ZF, ZC + 3.2, DEPTH); _room(S, B0, B1, ZF, ZC, DEPTH); _room(S, S0, A0, ZF, ZF + CH, CW); _room(S, A1, B0, ZF, ZF + CH, CW)
        zs0, zs1 = ZF, ZF + (S0 - HUT[0])                                                                                 # the stair: back wall, floor and ceiling as slabs set on the slope
        S.add(*plate([(S0, 0, zs0 - 0.3), (S0, 0, zs0 + ST_H + 0.3), (HUT[0], 0, zs1 + ST_H + 0.3), (HUT[0], 0, zs1 - 0.3)], EY, 0.3), color=CONC); S.v[-1][:, 1] += -CW - 0.15
        for dz, c in ((-0.3, CONC2), (ST_H, CONC)):
            S.add(*plate([(S0, 0, zs0 + dz), (S0, 0, zs0 + dz + 0.3), (HUT[0], 0, zs1 + dz + 0.3), (HUT[0], 0, zs1 + dz)], EY, CW), color=c); S.v[-1][:, 1] += -CW / 2
        for k in range(int((S0 - HUT[0]) / 0.6)):                                                                          # treads
            x = S0 - 0.6 * k - 0.3; S.add(*gbox((x, -CW / 2, ZF + 0.6 * k + 0.3), (0.6, CW, 0.6)), color=CONC2)
        for k, xv in enumerate(VENTS):                                                                                     # the air shafts: half a steel pipe behind the cut, a cap on the surface
            S.add(*gbox((xv, -VR - 0.05, ((ZF + CH) if k == 0 else ZC) / 2), (2 * VR + 0.2, 0.1, -((ZF + CH) if k == 0 else ZC))), color=STEELC); _vent_cap(S, xv, half=True)
        _hut(S, half=True)
        self.fixed = new_obj("BunkerFixed", S.mesh("bunker_fixed"), col, self.mat)
        K = Shell()                                                                                                       # stand-ins for what is kept there: racks, desks, cabinets (no people)
        for (x, sx, sz, c) in ((A0 + 1.6, 2.2, 2.0, (0.12, 0.15, 0.13, 1)), (A0 + 4.3, 1.6, 1.0, (0.16, 0.13, 0.09, 1)), (A1 - 5.0, 1.8, 0.9, (0.16, 0.13, 0.09, 1)), (A1 - 2.2, 2.0, 2.1, (0.14, 0.14, 0.15, 1)), (A1 - 0.7, 0.8, 1.2, (0.10, 0.12, 0.16, 1))):
            K.add(*gbox((x, -DEPTH + 0.6, ZF + sz / 2), (sx, 0.9, sz)), color=c)
        for x in (A0 + 6.4, A0 + 7.3):
            K.add(*gbox((x, -2.6, ZF + 0.4), (0.7, 1.4, 0.8)), color=(0.16, 0.13, 0.09, 1))
        self.contents = new_obj("Contents", K.mesh("contents"), col, self.mat)
        K = Shell()
        for (x, sx, sz, c) in ((B0 + 1.5, 2.0, 1.9, (0.12, 0.15, 0.13, 1)), (B0 + 4.4, 1.8, 0.9, (0.16, 0.13, 0.09, 1)), (B1 - 4.0, 2.2, 1.0, (0.16, 0.13, 0.09, 1)), (B1 - 1.4, 1.6, 2.0, (0.14, 0.14, 0.15, 1))):
            K.add(*gbox((x, -DEPTH + 0.6, ZF + sz / 2), (sx, 0.9, sz)), color=c)
        new_obj("ContentsB", K.mesh("contents_b"), col, self.mat)
        D_ = Shell(); D_.add(*gbox((0, 0, 0), (0.08, CW - 0.04, 2.15)), color=STEELC); ob = new_obj("SecDoor", D_.mesh("sec_door"), col, self.mat)
        self.door = Piece(ob, (HUT[0] - 0.05, -CW / 2, 1.1), (-19.0, -1.5, 5.0), (0.2, 1.0, 0.3), 6.0, 0.06, tuple(Quaternion((0, 1, 0), math.pi / 2)), drag=0.3)
        # ---- over the target chamber: roof and slab as blocks, the soil as sheets that move with them
        self.blocks = []
        for name, n, z0, z1, f in (("Roof", 8, ZC, ZR, 1.0), ("Slab", 7, ZS - C.SLAB, ZS, 0.85)):
            bw = (A1 - A0) / n
            for i in range(n):
                B = Shell(); B.add(*gbox((0, 0, 0), (bw - 0.02, DEPTH, z1 - z0))); ob = new_obj("%s%d" % (name, i), B.mesh("%s%d" % (name.lower(), i)), col, mats["conc"]); ob.rotation_mode = 'QUATERNION'
                self.blocks.append((ob, A0 + bw * (i + 0.5), (z0 + z1) / 2, f, float(rng.uniform(-1, 1)), float(rng.uniform(-1, 1))))
        self.gx = np.linspace(A0, A1, 57); self.gz = np.concatenate([np.linspace(ZS, 0.0, 22)]); self.lens = new_obj("Cut_cover", bpy.data.meshes.new("cut_cover"), col, mats["soil"]); self.gap = new_obj("Cut_gap", bpy.data.meshes.new("cut_gap"), col, mats["soil"])
        hm, N, L, P = nodemat("Channel"); P.inputs["Base Color"].default_value = (0.012, 0.011, 0.010, 1); P.inputs["Roughness"].default_value = 1.0
        self.chan = new_obj("Channel", bpy.data.meshes.new("channel"), col, hm); self.chan.visible_shadow = False; self.chan.hide_render = True
        g = Geo()                                                                                                         # broken concrete and soil that ends up in the chamber
        for k in range(420):
            x = float(rng.uniform(A0 + 0.2, A1 - 0.2)); hmax = (C.ROOM_H - ROOF_DROP * float(shape(x))) * 0.95; s_ = float(rng.uniform(0.14, 0.5)); z = hmax * float(rng.uniform(0, 1)) ** 1.5
            env.rock_geo(g, rng, (x, float(rng.uniform(-DEPTH + 0.2, -0.2)), z), s_, 2, [(0.42, 0.41, 0.38, 1), (0.36, 0.28, 0.19, 1), (0.30, 0.24, 0.17, 1)][k % 3])
        self.rubble = new_obj("Rubble", g.mesh("rubble"), col, env.mat_vcol("RubbleMat", rough=0.9, bump_scale=8)); self.rubble.location = (0, 0, ZF)
        self.spall = []; lr = C.layer_at("roof")
        for k in range(40):
            Bk = Shell(); s = rng.uniform(0.07, 0.26, 3); Bk.add(*gbox((0, 0, 0), s), color=CONC if k % 2 else CONC2); ob = new_obj("Spall%d" % k, Bk.mesh("spall%d" % k), col, self.mat)
            p0 = C.U * lr[3] + np.array([rng.uniform(-0.4, 0.4), rng.uniform(-0.6, 0.0), 0.0]); v0 = C.U * rng.uniform(15.0, 110.0) + np.array([rng.uniform(-12, 12), rng.uniform(-12, 2), rng.uniform(-5, 5)])
            self.spall.append((Piece(ob, p0, v0, tuple(rng.uniform(-1, 1, 3)), rng.uniform(-30, 30), ZF + 0.08, tuple(Quaternion(Vector(rng.uniform(-1, 1, 3)).normalized(), rng.uniform(0, 3))), drag=0.8), lr[7]))
        self.lamps = []
        for (lx, lz, e_) in ((A0 + 3.5, ZC - 0.3, 380.0), (A1 - 3.5, ZC - 0.3, 380.0), (B0 + 3.0, ZC - 0.3, 380.0), (B1 - 3.0, ZC - 0.3, 380.0), ((A1 + B0) / 2, ZF + CH - 0.2, 110.0), ((S0 + A0) / 2, ZF + CH - 0.2, 110.0), (S0 - 7.0, ZF + 7.0 + ST_H - 0.6, 110.0)):
            ld = bpy.data.lights.new("Lamp", 'AREA'); ld.size = 1.0; ld.energy = e_; ld.color = (1.0, 0.93, 0.80); lo = bpy.data.objects.new("Lamp", ld); col.objects.link(lo); lo.location = (lx, -1.4, lz); self.lamps.append((lo, e_, lx))
        self.update(-1.0)

    def _mesh(self, ob, V, F, mat):
        me = new_mesh(ob.name.lower(), V, [F], smooth=False); me.materials.append(mat); old = ob.data; ob.data = me; bpy.data.meshes.remove(old)

    def update(self, tp):
        td = tp - C.FUZE_DELAY; s, _ = C.pen_state(tp); zm = zmove(td); sh = shape(self.gx); gx = self.gx
        if not hasattr(self, "_zm") or abs(zm - self._zm) > 1e-7:                                                          # only rebuild what moves when it moves
            self._zm = zm
            X, Z = np.meshgrid(gx, self.gz, indexing="ij"); Zd = Z + zm * shape(X) * level(Z); V = np.stack([X, np.full_like(X, 0.003), Zd], -1).reshape(-1, 3); self._mesh(self.lens, V, grid_faces(len(gx), len(self.gz)), self.mats["soil"])
            zb = ZR + zm * sh; zt = (ZS - C.SLAB) + zm * sh * 0.85; n = len(gx); k = np.arange(n - 1)
            V = np.concatenate([np.stack([gx, np.full_like(gx, 0.003), zb], 1), np.stack([gx, np.full_like(gx, 0.003), zt], 1)]); self._mesh(self.gap, V, np.stack([k, k + 1, k + 1 + n, k + n], 1), self.mats["soil"])
            e = 0.02
            for ob, xc, zc, f, r1, r2 in self.blocks:
                dz = zm * float(shape(xc)) * f; sl = zm * f * float(shape(xc + e) - shape(xc - e)) / (2 * e); w = min(abs(dz) / 1.2, 1.0)
                ob.location = (xc + 0.05 * r1 * w, -DEPTH / 2, zc + dz); ob.rotation_quaternion = Quaternion((0, 1, 0), -math.atan(sl) + math.radians(4.0) * r2 * w)
        for pc, t0 in self.spall:
            pc.ob.hide_render = tp < t0 or td > 0.02; p, q = pc.at(tp - t0); pc.ob.location = p; pc.ob.rotation_quaternion = q
        p, q = self.door.at(td - T_DOOR); self.door.ob.location = p; self.door.ob.rotation_quaternion = q
        for lo, e_, lx in self.lamps:                                                                                      # the lights go out as the blast reaches them
            on = td < 0.004 + 0.0030 * abs(lx - C.BURST[0]); lo.data.energy = e_ if on else 0.0; lo.hide_render = not on
        self.contents.hide_render = td > 0.010; self.rubble.hide_render = td < 0.45; self.rubble.scale = (1, 1, 0.08 + 0.92 * smoothstep(0.45, 1.45, td))
        qs = []; nrm = np.array([C.U[2], 0.0, -C.U[0]]); w = 0.5 * C.BLU_D * 1.15
        for name, kind, s0, s1, v0, v1, t0, t1 in C.RUN:
            if kind == "air" or (td > 0.004 and name != "soil"):
                continue                                                # after the burst only the hole through the soil is left to see
            b = min(s, s1)
            if b > s0 + 1e-3:
                pa = C.U * s0; pb = C.U * b; qs.append([pa - nrm * w, pb - nrm * w, pb + nrm * w, pa + nrm * w])
        self.chan.hide_render = not qs
        if qs:
            V = np.array(qs, float).reshape(-1, 3); V[:, 1] = 0.006; self._mesh(self.chan, V, np.arange(len(V)).reshape(-1, 4), self.chan.data.materials[0] if self.chan.data.materials else bpy.data.materials["Channel"])
