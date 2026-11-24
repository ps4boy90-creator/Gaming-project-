"""The target: a cut-and-cover bunker let into a mountainside, as an outside view and as a section.

The bunker is invented and nobody is modelled in it: a reinforced-concrete room 10 m by 6 m by 3 m with a 0.9 m roof,
built in a trench in the slope and covered again with compacted earth and broken rock, and reached by a level
tunnel from a concrete portal lower down the slope.  ground(x, y) is the surface everywhere; near the bunker it is the
plain 25 degree slope that the penetration calculation in pconst assumes.

Outside(col)   the mountainside with the portal, for views from the air and from the valley
Section(col)   the same ground cut along the plane y = 0 and seen from the +Y side: the layers the bomb goes through,
               the room and the tunnel behind the cut
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire", "tomahawk-sub"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
from mathutils import Quaternion, Vector
from qgeo import Shell, box as gbox, revolve, plate, paint_mat, EX, EY, EZ
from qtruck import Piece
from util import new_mesh, new_obj, grid_faces, nodemat, simple_mat, smoothstep, fbm, Geo
import env, tland
import pconst as C

M = math.tan(math.radians(C.SLOPE)); ZF = C.Z_FLOOR; ZC = C.Z_CEIL; ZR = C.Z_ROOF_TOP; X0, X1 = C.ROOM_X; PX = C.PORTAL_X; TH = C.TUN_H; TW = C.TUN_W / 2; LIN = 0.4
ROCK = (0.20, 0.17, 0.145, 1); ROCK2 = (0.30, 0.25, 0.20, 1); FILLC = (0.40, 0.31, 0.21, 1); CONC = (0.50, 0.49, 0.46, 1); CONC2 = (0.40, 0.39, 0.37, 1); STEELC = (0.16, 0.18, 0.17, 1); DARKC = (0.02, 0.02, 0.02, 1)
TRENCH = (X0 - 1.6, X1 + 1.6)
XF = PX + (TH + LIN) / M                              # the portal's face: where the tunnel's lined roof meets the slope; in front of it an open cutting
CUT_W = 2.6

def ground(x, y, fine=2):
    """Height of the mountainside.  Within 24 m of the bunker it is the plain 25 degree slope of the calculation."""
    x = np.asarray(x, float); y = np.asarray(y, float); r = np.hypot(x - 2.0, y)
    w = np.clip((r - 24.0) / 90.0, 0.0, 1.0); w = w * w * (3 - 2 * w)
    steep = 0.42 * np.clip(x - 90.0, 0.0, None) - 0.30 * np.clip(x - 640.0, 0.0, None) * 2.2                  # steeper above, a crest far up
    valley = np.clip(-(x + 60.0), 0.0, None) * M * 0.92                                                       # the slope runs out into a valley floor
    h = M * x + steep + valley + w * 70.0 * (fbm(x / 420.0 + 3.3, y / 420.0 + 1.1, 5, 5) - 0.5)
    if fine:                                                                                                  # detail that the coarse far sheet could not carry; it dies away with distance
        near = 1.0 - np.clip((r - 1000.0) / 600.0, 0.0, 1.0); w2 = np.clip((r - 32.0) / 60.0, 0.0, 1.0); rib = np.abs(fbm(y / 260.0 + 5.1, x / 1500.0 + 2.2, 11, 3) - 0.5) * 2.0
        h = h + near * (w * 9.0 * (fbm(x / 60.0, y / 60.0, 7, 3 if fine > 1 else 2) - 0.5) + (0.5 * w * (fbm(x / 6.0, y / 6.0, 9, 3) - 0.5) if fine > 1 else 0.0) - 16.0 * w2 * (1 - np.clip(rib * 3.0, 0, 1)) ** 2)   # hummocks, and ravines running down the slope
    apron = np.clip((5.5 - np.abs(y)) / 2.0, 0.0, 1.0) * np.clip((x - (PX - 11.0)) / 4.0, 0.0, 1.0) * (x < PX)                         # a level apron built out in front
    cut = np.clip((CUT_W - np.abs(y)) / 0.04, 0.0, 1.0) * np.clip((XF - x) / 0.04, 0.0, 1.0) * (x >= PX)                               # and a cutting with upright sides back to the portal
    pad = np.maximum(apron, cut)
    return h * (1 - pad) + ZF * pad

def _terrain(col, ymax=None):
    m = tland.land_mat("MountainRock")
    for nd in m.node_tree.nodes:
        if nd.type == 'VALTORGB' and abs(nd.color_ramp.elements[0].color[0] - 0.170) < 1e-3:
            nd.color_ramp.elements[0].color = (0.150, 0.120, 0.090, 1); nd.color_ramp.elements[1].color = (0.360, 0.300, 0.220, 1)
    obs = []
    for name, half, step, skirt, hole in (("Near", 150.0, 1.25, 4.0, 0.0), ("Mid", 1800.0, 15.0, 40.0, 150.0), ("Far", 26000.0, 220.0, 0.0, 1800.0)):
        xs = np.arange(-half, half + 1e-3, step); ys = np.arange(-half, half + 1e-3, step)
        if name == "Near":                                                 # grid lines on the edges of the cutting, so that its sides stand upright
            xs = np.array(sorted(set(xs) | {PX, XF - 0.04, XF})); ys = np.array(sorted(set(ys) | {-CUT_W, -CUT_W + 0.04, CUT_W - 0.04, CUT_W}))
        if ymax is not None:
            ys = np.append(ys[ys < ymax - 1e-6], ymax)
        X, Y = np.meshgrid(xs, ys, indexing="ij"); Z = ground(X, Y, fine={"Near": 2, "Mid": 1, "Far": 0}[name]); V = np.stack([X, Y, Z], -1).reshape(-1, 3); F = [grid_faces(len(xs), len(ys))]; nx, ny = len(xs), len(ys)
        if hole:                                                           # the coarser sheets are left open where a finer one lies, or their flat facets would stand proud of it
            c = V[F[0]].mean(1); F[0] = F[0][~((np.abs(c[:, 0]) < hole - 1e-3) & (np.abs(c[:, 1]) < hole - 1e-3))]
        if skirt:                                                          # an apron hanging from the edge hides the small gaps where a fine sheet meets a coarse one
            for e in [np.arange(nx) * ny, (nx - 1) * ny + np.arange(ny), np.arange(ny)] + ([np.arange(nx) * ny + ny - 1] if ymax is None else []):
                n0 = len(V); top = V[e]; bot = top - np.array([0.0, 0.0, skirt]); V = np.vstack([V, top, bot]); k = np.arange(len(e) - 1); F.append(np.stack([n0 + k, n0 + k + 1, n0 + len(e) + k + 1, n0 + len(e) + k], 1))
        obs.append(new_obj("Ground" + name, new_mesh("ground_" + name.lower(), V, F), col, m))
    return obs

def _portal(S, half=False):
    """The entrance: a concrete headwall round the tunnel mouth and two retaining walls along the cutting."""
    top = ZF + TH + LIN + 0.7; ys = (-1,) if half else (-1, 1)
    for sg in ys:
        S.add(*gbox((XF + 0.25, sg * (TW + (CUT_W + 0.6 - TW) / 2), (ZF + top) / 2), (0.5, CUT_W + 0.6 - TW, top - ZF)), color=CONC)                       # headwall beside the opening
        S.add(*gbox((XF + 0.25, sg * TW / 2, (ZF + TH + top) / 2), (0.5, TW, top - ZF - TH)), color=CONC)                                               # and over it
        S.add(*gbox((XF + 0.25, sg * (CUT_W + 0.6) / 2, top + 0.12), (0.7, CUT_W + 0.6, 0.24)), color=CONC2)                                           # coping
        S.add(*plate([(PX - 0.6, 0, ZF - 0.5), (XF, 0, ZF - 0.5), (XF, 0, top), (PX - 0.6, 0, ZF + 0.45)], EY, 0.45), color=CONC)                       # retaining wall, built below
        S.v[-1][:, 1] += sg * (CUT_W + 0.2)

V_HEAVE = 5.4; ROOF_DROP = 2.2; SURF_DROP = 1.9

def _ball(td):
    return V_HEAVE * td - 0.5 * C.G * td * td if td > 0 else 0.0

def roof_shape(x):
    s = np.clip((np.asarray(x, float) - (X0 - C.WALL)) / (X1 - X0 + 2 * C.WALL), 0.0, 1.0); return np.sin(math.pi * s) ** 1.5

def roof_dz(x, td):
    """How far the roof slab has moved at x: thrown up by the gas, then down into the room (illustrative)."""
    return roof_shape(x) * max(_ball(td), -ROOF_DROP)

def surf_k(td):
    """The same for the ground surface, as a fraction of the final hollow (negative while it is lifted)."""
    return min(-0.75 * _ball(td) / SURF_DROP, 1.0)

def hollow(x, y):
    """The hollow left in the surface when the cover has fallen into the room (z change, final)."""
    x = np.asarray(x, float); y = np.asarray(y, float); e = ((x - 3.6) / 6.2) ** 2 + (y / 4.2) ** 2
    return -SURF_DROP * np.exp(-e) + 0.45 * np.exp(-((np.sqrt(e) - 1.35) / 0.35) ** 2) + 0.25 * np.exp(-e / 2.5) * (fbm(x * 0.9, y * 0.9, 5, 3) - 0.5) * 2

def _hollow_key(ob):
    me = ob.data; n = len(me.vertices); V = np.empty(n * 3, np.float32); me.vertices.foreach_get("co", V); V = V.reshape(-1, 3)
    ob.shape_key_add(name="Basis"); sk = ob.shape_key_add(name="Collapse"); co = V.copy(); co[:, 2] += hollow(V[:, 0], V[:, 1])
    sk.data.foreach_set("co", co.astype(np.float32).ravel()); sk.slider_min = -3.0; sk.value = 0.0; return sk

def _rocks(col, rng, ymax=None):
    """Loose rock and boulders on the slope round the bunker (none on the ground the bomb goes through, or on the apron)."""
    g = Geo(); n = 420; r = 6.0 + np.abs(rng.normal(0, 46.0, n)); a = rng.uniform(0, 6.283, n); xs = 2.0 + r * np.cos(a); ys = r * np.sin(a)
    for x, y in zip(xs, ys):
        if (abs(y) < 7.0 and PX - 13.0 < x < XF + 2.0) or (ymax is not None and y > ymax - 1.5):
            continue
        s = float(min(np.exp(rng.normal(-1.25, 0.65)), 2.4)); c = [(0.15, 0.12, 0.09, 1), (0.20, 0.17, 0.14, 1), (0.10, 0.085, 0.07, 1)][int(rng.integers(0, 3))]
        env.rock_geo(g, rng, (x, y, float(ground(x, y)) + s * 0.12), s, 2 if s < 0.8 else 3, c)
    return new_obj("Rocks", g.mesh("rocks"), col, env.mat_vcol("RockMat", rough=0.9, bump_scale=6))

class Outside:
    def __init__(self, col):
        rng = np.random.default_rng(7); self.col = col; self.mat = bpy.data.materials.get("SitePaint") or paint_mat("SitePaint", rough=0.85, bump=0.4)
        self.ground = _terrain(col)[0]; _rocks(col, rng)
        self.collapse = _hollow_key(self.ground)
        S = Shell(); _portal(S)
        S.add(*gbox((XF + 3.3, 0, ZF + TH / 2), (5.0, 2 * TW, TH)), color=DARKC)                                               # the dark of the tunnel behind the doors
        for (vx, vy) in ((1.0, 2.0), (6.5, -2.0)):                                                                              # ventilation pipes over the room
            S.add(*revolve([(-0.5, 0.16), (1.1, 0.16), (1.1, 0.24), (1.3, 0.24), (1.3, 0.0)], 12, axis=EZ, origin=(vx, vy, float(ground(vx, vy)))), color=STEELC)
        self.fixed = new_obj("PortalFixed", S.mesh("portal_fixed"), col, self.mat)
        self.doors = []
        for sg in (1, -1):                                                                                                      # steel doors, thrown out when the blast comes down the tunnel
            D_ = Shell(); D_.add(*gbox((0, 0, 0), (0.08, TW - 0.02, TH - 0.05)), color=STEELC); D_.add(*gbox((-0.05, 0, 0.3), (0.04, TW - 0.3, 0.08)), color=STEELC)
            ob = new_obj("Door%+d" % sg, D_.mesh("site_door%+d" % sg), col, self.mat)
            self.doors.append(Piece(ob, (XF - 0.05, sg * TW / 2, ZF + TH / 2), (-26.0 - 4 * sg, 2.0 * sg, 4.0 + sg), (0.2, 1.0, 0.3 * sg), 5.0 * sg, ZF + 0.06, tuple(Quaternion((0, 1, 0), math.pi / 2)), drag=0.3))
        hm, N, L, P = nodemat("EntryHole"); P.inputs["Base Color"].default_value = (0.012, 0.011, 0.010, 1); P.inputs["Roughness"].default_value = 1.0
        a = np.linspace(0, 2 * np.pi, 24, endpoint=False); nrm = np.array([-math.sin(math.radians(C.SLOPE)), 0, math.cos(math.radians(C.SLOPE))]); t1 = np.array([math.cos(math.radians(C.SLOPE)), 0, math.sin(math.radians(C.SLOPE))])
        V = np.vstack([[nrm * 0.03], [nrm * 0.03 + 0.42 * (math.cos(t) * t1 + math.sin(t) * EY) * (1 + 0.2 * math.sin(3 * t)) for t in a]]); k = np.arange(24)
        self.hole = new_obj("EntryHole", new_mesh("entry_hole", V, [np.stack([np.zeros(24, int), 1 + k, 1 + (k + 1) % 24], 1)], smooth=False), col, hm); self.hole.visible_shadow = False
        g = Geo()                                                                                                                # broken ground in the hollow
        for k in range(150):
            x = float(rng.normal(3.6, 3.4)); y = float(rng.normal(0.0, 2.3)); s_ = float(rng.uniform(0.15, 0.75))
            env.rock_geo(g, rng, (x, y, float(ground(x, y) + hollow(x, y)) + 0.1 * s_), s_, 2, [(0.17, 0.14, 0.10, 1), (0.24, 0.20, 0.15, 1), (0.30, 0.29, 0.27, 1)][k % 3])
        self.rubble = new_obj("HollowRubble", g.mesh("hollow_rubble"), col, env.mat_vcol("HollowMat", rough=0.9, bump_scale=8))
        self.update(-1.0)

    def update(self, tp):
        """tp: seconds after the bomb touches the slope (the charge fires at FUZE_DELAY)."""
        td = tp - C.FUZE_DELAY; self.hole.hide_render = tp < 0.0 or td > 0.2; self.rubble.hide_render = td < 1.45
        for pc in self.doors:
            p, q = pc.at(td - 0.02); pc.ob.location = p; pc.ob.rotation_quaternion = q
        self.collapse.value = surf_k(td)

def _column(x):
    """What lies along a vertical line at x in the plane of the section: (z_low, z_high, kind) from the bottom up."""
    top = float(ground(x, 0.0)); out = []; zb = -45.0
    def add(z0, z1, kind):
        out.append((z0, max(z1, z0), kind))
    if x < PX:
        nat = float(M * x - np.clip(-(x + 60.0), 0.0, None) * M * 0.92); add(zb, min(nat, top), "rock"); add(min(nat, top), top, "fill"); return out
    if x < XF:                                                         # the open cutting in front of the portal
        add(zb, ZF - LIN, "rock"); add(ZF - LIN, ZF, "conc"); return out
    if x < X0 - C.WALL:                                                # along the tunnel
        add(zb, ZF - LIN, "rock"); add(ZF - LIN, ZF, "conc"); add(ZF + TH, ZF + TH + LIN, "conc"); lt = ZF + TH + LIN
        add(lt, max(top - 1.6, lt), "rock"); add(max(top - 1.6, lt), top, "weath"); return out
    if x > X1 + C.WALL:
        add(zb, max(top - 1.6, zb), "rock"); add(max(top - 1.6, zb), top, "weath"); return out
    add(zb, ZF - C.FLOOR, "rock"); add(ZF - C.FLOOR, ZF, "conc")
    if x < X0 or x > X1:
        add(ZF, ZR, "conc")                                             # end walls (the roof slab itself is loose blocks, see Section)
    return out                                                         # the fill over the roof moves, so Section draws it frame by frame

def _face_mat(name, c0, c1, scale, stones=0.0):
    m, N, L, P = nodemat(name); tc = N.new("ShaderNodeTexCoord"); n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = 6; n.inputs["Roughness"].default_value = 0.62
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1.0, 1.0, 3.2); mp.inputs["Rotation"].default_value = (0, math.radians(-12), 0); L.new(tc.outputs["Object"], mp.inputs["Vector"]); L.new(mp.outputs[0], n.inputs["Vector"])
    r = N.new("ShaderNodeValToRGB"); e = r.color_ramp.elements; e[0].position = 0.34; e[0].color = (*c0, 1); e[1].position = 0.68; e[1].color = (*c1, 1); L.new(n.outputs["Fac"], r.inputs["Fac"])
    if stones:
        v = N.new("ShaderNodeTexVoronoi"); v.inputs["Scale"].default_value = stones; L.new(tc.outputs["Object"], v.inputs["Vector"]); st = N.new("ShaderNodeMapRange"); st.inputs["From Min"].default_value = 0.10; st.inputs["From Max"].default_value = 0.22
        st.inputs["To Min"].default_value = 0.55; st.inputs["To Max"].default_value = 1.0; L.new(v.outputs["Distance"], st.inputs["Value"]); mx = N.new("ShaderNodeMixRGB"); mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0
        L.new(r.outputs["Color"], mx.inputs[1]); L.new(st.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], P.inputs["Base Color"])
    else:
        L.new(r.outputs["Color"], P.inputs["Base Color"])
    P.inputs["Roughness"].default_value = 0.9
    return m

class Section:
    """Everything on and behind the cut.  The solid ground is the half y <= 0; the camera stands on the +Y side."""
    def __init__(self, col):
        rng = np.random.default_rng(19); self.col = col; self.mat = bpy.data.materials.get("SitePaint") or paint_mat("SitePaint", rough=0.85, bump=0.4)
        self.collapse = _hollow_key(_terrain(col, ymax=0.0)[0]); _rocks(col, rng, ymax=0.0)
        mats = self.mats = {"rock": _face_mat("CutRock", (0.050, 0.045, 0.042), (0.125, 0.110, 0.098), 0.55), "weath": _face_mat("CutWeathered", (0.115, 0.090, 0.066), (0.215, 0.170, 0.120), 1.2, stones=1.6),
                            "fill": _face_mat("CutFill", (0.26, 0.195, 0.125), (0.43, 0.335, 0.225), 2.2, stones=3.4), "conc": _face_mat("CutConcrete", (0.36, 0.355, 0.34), (0.52, 0.51, 0.49), 5.0, stones=14.0)}
        xs = sorted(set(list(np.arange(-150.0, 150.01, 1.0)) + [PX - 11, PX - 7, PX - 1e-3, PX + 1e-3, XF - 1e-3, XF + 1e-3, X0 - C.WALL - 1e-3, X0 - C.WALL + 1e-3, X0 - 1e-3, X0 + 1e-3, X1 - 1e-3, X1 + 1e-3, X1 + C.WALL - 1e-3, X1 + C.WALL + 1e-3]))
        quads = {k: [] for k in mats}
        for xa, xb in zip(xs[:-1], xs[1:]):
            if xb - xa < 5e-3 or (xa < X0 - C.WALL < xb) or (xa < X1 + C.WALL < xb):
                continue
            ca = _column(xa + 2e-3); cb = _column(xb - 2e-3)
            if len(ca) != len(cb) or any(a[2] != b[2] for a, b in zip(ca, cb)):
                continue
            for (a0, a1, kind), (b0, b1, _) in zip(ca, cb):
                quads[kind].append([(xa, 0.003, a0), (xb, 0.003, b0), (xb, 0.003, b1), (xa, 0.003, a1)])
        for kind, qs in quads.items():
            V = np.array(qs, float).reshape(-1, 3); F = np.arange(len(V)).reshape(-1, 4); new_obj("Cut_" + kind, new_mesh("cut_" + kind, V, [F], smooth=False), col, mats[kind])
        self.fx = np.linspace(X0 - C.WALL, X1 + C.WALL, 71); self.fill = new_obj("Cut_cover", bpy.data.meshes.new("cut_cover"), col, mats["fill"])
        # ---- behind the cut: the room, the tunnel, the portal
        S = Shell()
        S.add(*gbox(((X0 + X1) / 2, -C.ROOM_Y - C.WALL / 2, (ZF + ZR) / 2), (X1 - X0 + 2 * C.WALL, C.WALL, ZR - ZF)), color=CONC)                       # back wall
        S.add(*gbox((X1 + C.WALL / 2, -C.ROOM_Y / 2 - 0.3, (ZF + ZR) / 2), (C.WALL, C.ROOM_Y + 0.6, ZR - ZF)), color=CONC)                              # far end wall
        S.add(*gbox(((PX + X1) / 2, -C.ROOM_Y / 2 - 0.3, ZF - C.FLOOR / 2), (X1 - PX + 1.2, C.ROOM_Y + 0.6, C.FLOOR)), color=CONC2)                        # floor slab, room and tunnel
        S.add(*gbox(((XF + X0) / 2, -TW - LIN / 2, ZF + (TH + LIN) / 2), (X0 - XF, LIN, TH + LIN)), color=CONC)                                           # tunnel: far wall
        S.add(*gbox(((XF + X0 - C.WALL) / 2, -TW / 2 - 0.2, ZF + TH + LIN / 2), (X0 - C.WALL - XF, TW + 0.4, LIN)), color=CONC)                             # tunnel: roof
        S.add(*gbox((X0 - C.WALL / 2, -(TW + C.ROOM_Y) / 2 - 0.3, (ZF + ZR) / 2), (C.WALL, C.ROOM_Y - TW + 0.6, ZR - ZF)), color=CONC)                     # room wall beside the doorway
        S.add(*gbox((X0 - C.WALL / 2, -TW / 2, (ZF + TH + ZR) / 2), (C.WALL, TW, ZR - ZF - TH)), color=CONC)                                               # lintel over the doorway
        _portal(S, half=True)
        self.fixed = new_obj("BunkerFixed", S.mesh("bunker_fixed"), col, self.mat)
        K = Shell()                                                                                                                                       # what stands in the room: racks, crates, a generator, drums (no people)
        for (x, y, sx, sy, sz, c) in ((7.2, -2.3, 1.8, 1.0, 2.0, (0.12, 0.15, 0.13, 1)), (5.6, -2.5, 1.2, 0.7, 1.7, (0.14, 0.14, 0.15, 1)), (0.3, -2.4, 1.6, 0.8, 0.9, (0.16, 0.13, 0.09, 1)), (-0.6, -1.3, 0.9, 0.7, 0.8, (0.16, 0.13, 0.09, 1)),
                                      (7.6, -0.9, 1.0, 1.0, 1.0, (0.10, 0.12, 0.16, 1)), (1.6, -2.55, 0.6, 0.6, 0.9, (0.25, 0.08, 0.06, 1))):
            K.add(*gbox((x, y, ZF + sz / 2), (sx, sy, sz)), color=c)
        for x in (3.3, 3.95, 4.6):
            K.add(*revolve([(0.0, 0.0), (0.0, 0.29), (0.88, 0.29), (0.88, 0.0)], 14, axis=EZ, origin=(x, -2.5, ZF)), color=(0.10, 0.16, 0.11, 1))
        self.contents = new_obj("Contents", K.mesh("contents"), col, self.mat)
        D_ = Shell(); D_.add(*gbox((0, 0, 0), (0.08, TW - 0.02, TH - 0.05)), color=STEELC); ob = new_obj("SecDoor", D_.mesh("sec_door"), col, self.mat)   # the door leaf behind the cut
        self.door = Piece(ob, (XF - 0.05, -TW / 2, ZF + TH / 2), (-24.0, -1.0, 3.0), (0.2, 1.0, 0.3), -5.0, ZF + 0.06, tuple(Quaternion((0, 1, 0), math.pi / 2)), drag=0.3)
        # ---- the roof slab: ten blocks that move with the cover; their front faces are the section of the slab
        self.roof = []; nb = 10; bw = (X1 - X0 + 2 * C.WALL) / nb
        for i in range(nb):
            xc = X0 - C.WALL + bw * (i + 0.5); B = Shell(); B.add(*gbox((0, 0, 0), (bw - 0.012, C.ROOM_Y + C.WALL, C.ROOF)))
            ob = new_obj("Roof%d" % i, B.mesh("roof%d" % i), col, mats["conc"]); ob.rotation_mode = 'QUATERNION'; self.roof.append((ob, xc, float(rng.uniform(-1, 1)), float(rng.uniform(-1, 1))))
        # ---- the hole the bomb leaves and the crater in the floor, drawn on the cut
        hm, N, L, P = nodemat("Channel"); P.inputs["Base Color"].default_value = (0.012, 0.011, 0.010, 1); P.inputs["Roughness"].default_value = 1.0
        self.chan = new_obj("Channel", bpy.data.meshes.new("channel"), col, hm); self.chan.visible_shadow = False; self.chan.hide_render = True
        cx = float((C.U * C.S3)[0]) + 0.25; a = np.linspace(0, math.pi, 17); V = np.array([[cx, 0.005, ZF + 0.02]] + [[cx + 1.15 * math.cos(t) * (1 + 0.12 * math.sin(5 * t)), 0.005, ZF + 0.02 - 0.95 * math.sin(t) * (1 + 0.15 * math.sin(7 * t + 1))] for t in a])
        k = np.arange(16); self.crater = new_obj("FloorCrater", new_mesh("floor_crater", V, [np.stack([np.zeros(16, int), 1 + k, 2 + k], 1)], smooth=False), col, hm); self.crater.visible_shadow = False
        # ---- broken concrete and earth that ends up in the room
        g = Geo()
        for k in range(300):
            x = float(rng.uniform(X0 + 0.2, X1 - 0.2)); hmax = (C.ROOM_H - ROOF_DROP * float(roof_shape(x))) * 0.92; s_ = float(rng.uniform(0.12, 0.42)); z = hmax * float(rng.uniform(0, 1)) ** 1.6
            env.rock_geo(g, rng, (x, float(rng.uniform(-2.9, -0.15)), z), s_, 2, [(0.30, 0.29, 0.27, 1), (0.22, 0.17, 0.12, 1), (0.17, 0.16, 0.15, 1)][k % 3])
        self.rubble = new_obj("Rubble", g.mesh("rubble"), col, env.mat_vcol("RubbleMat", rough=0.9, bump_scale=8)); self.rubble.location = (0, 0, ZF)
        # ---- concrete knocked off the underside of the roof and out of the floor as the bomb goes through
        self.spall = []
        for k in range(46):
            Bk = Shell(); s = rng.uniform(0.05, 0.22, 3); Bk.add(*gbox((0, 0, 0), s), color=CONC if k % 2 else CONC2); ob = new_obj("Spall%d" % k, Bk.mesh("spall%d" % k), col, self.mat); top = k < 30
            p0 = (C.U * (C.S2 if top else C.S3 + 0.1) + np.array([rng.uniform(-0.3, 0.3), rng.uniform(-0.45, 0.0), 0.0])); d = C.U if top else np.array([-C.U[0], 0, -C.U[2]])
            v0 = d * rng.uniform(8.0, 60.0 if top else 22.0) + np.array([rng.uniform(-9, 9), rng.uniform(-9, 2), rng.uniform(-4, 4)])
            self.spall.append((Piece(ob, p0, v0, tuple(rng.uniform(-1, 1, 3)), rng.uniform(-30, 30), ZF + 0.06, tuple(Quaternion(Vector(rng.uniform(-1, 1, 3)).normalized(), rng.uniform(0, 3))), drag=0.8), C.TP[2] if top else C.TP[3] + 0.002))
        self.lamps = []
        for (lx, lz, e) in ((1.2, ZC - 0.25, 150.0), (6.0, ZC - 0.25, 150.0), ((XF + X0) / 2, ZF + TH - 0.2, 60.0)):
            ld = bpy.data.lights.new("Lamp", 'AREA'); ld.size = 0.9; ld.energy = e; ld.color = (1.0, 0.93, 0.80); lo = bpy.data.objects.new("Lamp", ld); col.objects.link(lo); lo.location = (lx, -1.3, lz); self.lamps.append((lo, e))
        self.update(-1.0)

    def update(self, tp):
        td = tp - C.FUZE_DELAY; s, _ = C.pen_state(tp); self.collapse.value = surf_k(td)
        # the cover over the roof: from the slab's top to the surface, both moving
        fx = self.fx; zb = ZR + roof_dz(fx, td); zt = ground(fx, np.zeros_like(fx)) + surf_k(td) * hollow(fx, np.zeros_like(fx)); zt = np.maximum(zt, zb + 0.05)
        V = np.concatenate([np.stack([fx, np.full_like(fx, 0.003), zb], 1), np.stack([fx, np.full_like(fx, 0.003), zt], 1)]); n = len(fx); k = np.arange(n - 1)
        me = new_mesh("cut_cover", V, [np.stack([k, k + 1, k + 1 + n, k + n], 1)], smooth=False); me.materials.append(self.mats["fill"]); old = self.fill.data; self.fill.data = me; bpy.data.meshes.remove(old)
        e = 0.02
        for ob, xc, r1, r2 in self.roof:
            dz = float(roof_dz(xc, td)); sl = float(roof_dz(xc + e, td) - roof_dz(xc - e, td)) / (2 * e); w = min(abs(dz) / 1.2, 1.0)
            ob.location = (xc + 0.05 * r1 * w, -(C.ROOM_Y + C.WALL) / 2, (ZC + ZR) / 2 + dz); ob.rotation_quaternion = Quaternion((0, 1, 0), -math.atan(sl) + math.radians(5.0) * r2 * w)
        for pc, t0 in self.spall:
            pc.ob.hide_render = tp < t0 or td > 0.02; p, q = pc.at(tp - t0); pc.ob.location = p; pc.ob.rotation_quaternion = q
        p, q = self.door.at(td - 0.02); self.door.ob.location = p; self.door.ob.rotation_quaternion = q
        for lo, e_ in self.lamps:
            lo.data.energy = e_ if td < 0 else 0.0; lo.hide_render = td >= 0
        self.contents.hide_render = td > 0.010; self.crater.hide_render = td < 0.004
        self.rubble.hide_render = td < 0.30; self.rubble.scale = (1, 1, 0.08 + 0.92 * smoothstep(0.30, 1.40, td))
        segs = [(0.0, min(s, C.S1)), (C.S1, min(s, C.S2)), (C.S3, min(s, C.S_END))] if td < 0.004 else ([(0.0, C.S1)] if td < 0.05 else []); qs = []; nrm = np.array([C.U[2], 0.0, -C.U[0]])
        for a, b in segs:
            if b > a + 1e-3:
                w = 0.5 * C.BLU_D * 1.12; pa = C.U * a; pb = C.U * b; qs.append([pa - nrm * w, pb - nrm * w, pb + nrm * w, pa + nrm * w])
        self.chan.hide_render = not qs
        if qs:
            V = np.array(qs, float).reshape(-1, 3); V[:, 1] = 0.006; me = new_mesh("channel", V, [np.arange(len(V)).reshape(-1, 4)], smooth=False); me.materials.append(self.chan.data.materials[0]); old = self.chan.data; self.chan.data = me; bpy.data.meshes.remove(old)
