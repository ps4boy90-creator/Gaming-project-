"""Mesh-building helpers for the MQ-9 / Hellfire segment: lofts, airfoil surfaces, bodies of revolution, plates."""
import bpy, bmesh, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion"))
from mathutils import Vector, Quaternion
from util import new_mesh, new_obj, grid_faces, nodemat, simple_mat

EX = np.array([1.0, 0, 0]); EY = np.array([0, 1.0, 0]); EZ = np.array([0, 0, 1.0])

def aim_quat(v, roll=0.0):
    """Quaternion turning local +X onto v (local +Z kept as near up as possible), then rolled about the axis."""
    return Vector(v).to_track_quat('X', 'Z') @ Quaternion((1, 0, 0), roll)

class Shell:
    """Accumulates coloured geometry; mesh() gives one object-ready mesh with consistent normals and a 'col' attribute."""
    def __init__(self):
        self.v = []; self.q = []; self.t = []; self.c = []; self.n = 0
    def add(self, verts, quads=None, tris=None, color=(1, 1, 1, 1)):
        verts = np.asarray(verts, np.float64).reshape(-1, 3); self.v.append(verts)
        if quads is not None and len(quads):
            self.q.append(np.asarray(quads, np.int32).reshape(-1, 4) + self.n)
        if tris is not None and len(tris):
            self.t.append(np.asarray(tris, np.int32).reshape(-1, 3) + self.n)
        c = np.asarray(color, np.float32)
        self.c.append(np.broadcast_to(c, (len(verts), 4)).copy() if c.ndim == 1 else c)
        self.n += len(verts)
        return self
    def mesh(self, name, sharp=math.radians(38)):
        faces = ([np.concatenate(self.q)] if self.q else []) + ([np.concatenate(self.t)] if self.t else [])
        me = new_mesh(name, np.concatenate(self.v), faces, attrs={"col": np.concatenate(self.c)})
        bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
        try:
            me.set_sharp_from_angle(angle=sharp)
        except Exception:
            pass
        return me

def paint_mat(name, rough=0.5, metal=0.0, bump=0.0, spec=0.5):
    """Painted surface whose colour comes from the 'col' vertex attribute, with a little roughness breakup."""
    m, N, L, P = nodemat(name)
    a = N.new("ShaderNodeAttribute"); a.attribute_name = "col"
    tc = N.new("ShaderNodeTexCoord"); n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 3.0; n.inputs["Detail"].default_value = 5
    L.new(tc.outputs["Object"], n.inputs["Vector"])
    mix = N.new("ShaderNodeMixRGB"); mix.blend_type = 'MULTIPLY'; mix.inputs[0].default_value = 0.10
    L.new(a.outputs["Color"], mix.inputs[1]); L.new(n.outputs["Color"], mix.inputs[2]); L.new(mix.outputs[0], P.inputs["Base Color"])
    mr = N.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = rough - 0.07; mr.inputs["To Max"].default_value = rough + 0.07
    L.new(n.outputs["Fac"], mr.inputs["Value"]); L.new(mr.outputs[0], P.inputs["Roughness"])
    P.inputs["Metallic"].default_value = metal
    if bump:
        f = N.new("ShaderNodeTexNoise"); f.inputs["Scale"].default_value = 60; L.new(tc.outputs["Object"], f.inputs["Vector"])
        b = N.new("ShaderNodeBump"); b.inputs["Strength"].default_value = bump; b.inputs["Distance"].default_value = 0.002
        L.new(f.outputs["Fac"], b.inputs["Height"]); L.new(b.outputs["Normal"], P.inputs["Normal"])
    return m

def glass_mat(name, color=(0.02, 0.03, 0.04), rough=0.03):
    m, N, L, P = nodemat(name)
    P.inputs["Base Color"].default_value = (*color, 1); P.inputs["Roughness"].default_value = rough; P.inputs["Metallic"].default_value = 0.0
    try:
        P.inputs["Coat Weight"].default_value = 1.0; P.inputs["Coat Roughness"].default_value = 0.02
    except Exception:
        pass
    return m

# ---------------------------------------------------------------- primitives
def naca(t, n=20, camber=0.0):
    """Closed unit-chord airfoil loop (c, z): upper surface TE->LE, then lower surface LE->TE.  c runs 0 (LE) .. 1 (TE)."""
    b = (1 - np.cos(np.linspace(0, np.pi, n))) / 2
    yt = 5 * t * (0.2969 * np.sqrt(b) - 0.1260 * b - 0.3516 * b ** 2 + 0.2843 * b ** 3 - 0.1036 * b ** 4)
    yc = camber * 4 * b * (1 - b)
    up = np.stack([b[::-1], (yc + yt)[::-1]], 1); lo = np.stack([b[1:-1], (yc - yt)[1:-1]], 1)
    return np.vstack([up, lo])

def loft(rings, cap0=True, cap1=True):
    """rings: (k, m, 3) closed loops.  Returns verts, quads, tris (end caps as fans)."""
    R = np.asarray(rings, np.float64); k, m, _ = R.shape
    V = R.reshape(-1, 3); Q = grid_faces(k, m, wrap_v=True); T = []
    j = np.arange(m); j1 = (j + 1) % m
    if cap0:
        V = np.vstack([V, R[0].mean(0)]); T.append(np.stack([np.full(m, len(V) - 1), j1, j], 1))
    if cap1:
        V = np.vstack([V, R[-1].mean(0)]); T.append(np.stack([np.full(m, len(V) - 1), (k - 1) * m + j, (k - 1) * m + j1], 1))
    return V, Q, (np.vstack(T) if T else None)

def surface(stations, n=20, camber=0.0):
    """Lifting surface through stations (le_point, chord, thickness_ratio, chord_dir, up_dir).  chord_dir points LE -> TE."""
    rings = []
    for le, c, t, cd, up in stations:
        a = naca(t, n, camber); cd = np.asarray(cd, float); up = np.asarray(up, float)
        rings.append(np.asarray(le, float)[None] + c * a[:, :1] * cd[None] + c * a[:, 1:] * up[None])
    return loft(rings)

def wing(le0, c0, t0, le1, c1, t1, up, n=20, camber=0.0, cdir=(-1, 0, 0), k=6, tip_round=True):
    """Straight-tapered surface from root to tip with k spanwise stations and a rounded tip."""
    le0 = np.asarray(le0, float); le1 = np.asarray(le1, float); st = []
    for u in np.linspace(0, 1, k):
        st.append((le0 + (le1 - le0) * u, c0 + (c1 - c0) * u, t0 + (t1 - t0) * u, cdir, up))
    if tip_round:
        d = (le1 - le0); d /= np.linalg.norm(d); cd = np.asarray(cdir, float)
        for f, s in ((0.5, 0.80), (0.85, 0.45)):
            w = c1 * t1 * f; st.append((le1 + d * w + cd * c1 * (1 - s) * 0.35, c1 * s, t1 * math.sqrt(max(1 - f * f, 0.05)) / s * 0.9, cdir, up))
    return surface(st, n, camber)

def revolve(profile, segs=24, axis=EX, origin=(0, 0, 0), side=EY):
    """Body of revolution: profile [(s, r)] along `axis` from `origin`."""
    axis = np.asarray(axis, float); axis = axis / np.linalg.norm(axis); side = np.asarray(side, float)
    side = side - axis * np.dot(side, axis); side /= np.linalg.norm(side); third = np.cross(axis, side)
    a = np.linspace(0, 2 * np.pi, segs, endpoint=False)
    rings = [np.asarray(origin, float)[None] + s * axis[None] + r * (np.cos(a)[:, None] * side[None] + np.sin(a)[:, None] * third[None]) for s, r in profile]
    return loft(rings)

def box(center, size, rot=None):
    s = np.asarray(size, float) / 2
    V = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], float) * s
    if rot is not None:
        V = V @ np.asarray(rot).T
    V = V + np.asarray(center, float)
    Q = np.array([[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]])
    return V, Q, None

def plate(pts, normal, thick):
    """Thin prism through a planar polygon (list of 3-D points), thickened along `normal`."""
    P = np.asarray(pts, float); nrm = np.asarray(normal, float); nrm = nrm / np.linalg.norm(nrm); m = len(P)
    V = np.vstack([P - nrm * thick / 2, P + nrm * thick / 2])
    j = np.arange(m); j1 = (j + 1) % m
    Q = np.stack([j, j1, j1 + m, j + m], 1)
    T = np.vstack([np.stack([np.zeros(m - 2, int), j[1:-1] + 1, j[1:-1]], 1), np.stack([np.full(m - 2, m), m + j[1:-1], m + j[1:-1] + 1], 1)])
    return V, Q, T

def ellipsoid(center, radii, nu=20, nv=12, rot=None):
    u = np.linspace(0, 2 * np.pi, nu, endpoint=False); v = np.linspace(-np.pi / 2, np.pi / 2, nv)
    rings = []
    for vv in v:
        r = max(math.cos(vv), 1e-4); rings.append(np.stack([r * np.cos(u), r * np.sin(u), np.full(nu, math.sin(vv))], 1) * np.asarray(radii, float))
    R = np.asarray(rings)
    if rot is not None:
        R = R @ np.asarray(rot).T
    return loft(R + np.asarray(center, float))

def mirror_y(V):
    V = np.asarray(V, float).copy(); V[:, 1] *= -1; return V
