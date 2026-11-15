"""Small numpy/bpy helpers shared by the scene modules."""
import bpy, math
import numpy as np
from mathutils import Matrix, Vector, Quaternion

def new_mesh(name, verts, faces_list, uvs=None, smooth=True, attrs=None):
    """faces_list: list of int arrays (n,k); uvs: per-vertex (n,2); attrs: name -> per-vertex float or RGBA."""
    me = bpy.data.meshes.new(name)
    v = np.ascontiguousarray(verts, dtype=np.float32).reshape(-1, 3)
    faces_list = [np.asarray(f, dtype=np.int32) for f in faces_list if len(f)]
    me.vertices.add(len(v)); me.vertices.foreach_set("co", v.ravel())
    loops = np.concatenate([f.ravel() for f in faces_list])
    starts = []; off = 0
    for f in faces_list:
        n, k = f.shape
        starts.append(off + np.arange(n, dtype=np.int32) * k); off += n * k
    starts = np.concatenate(starts)
    me.loops.add(len(loops)); me.loops.foreach_set("vertex_index", loops)
    me.polygons.add(len(starts)); me.polygons.foreach_set("loop_start", starts)
    me.update(calc_edges=True)
    if smooth:
        me.shade_smooth()
    if uvs is not None:
        uvl = me.uv_layers.new(name="UVMap")
        uvl.data.foreach_set("uv", np.asarray(uvs, np.float32)[loops].ravel())
    if attrs:
        for k, a in attrs.items():
            a = np.asarray(a, np.float32)
            if a.ndim == 1:
                at = me.attributes.new(k, 'FLOAT', 'POINT'); at.data.foreach_set("value", a)
            else:
                at = me.attributes.new(k, 'FLOAT_COLOR', 'POINT'); at.data.foreach_set("color", a.ravel())
    return me

def new_obj(name, me, col=None, mat=None, loc=(0, 0, 0)):
    ob = bpy.data.objects.new(name, me)
    (col or bpy.context.scene.collection).objects.link(ob)
    if mat is not None:
        me.materials.append(mat)
    ob.location = loc
    return ob

def grid_faces(nu, nv, wrap_u=False, wrap_v=False, offset=0, flip=False):
    """Quads for a vertex grid indexed [iu*nv + iv]."""
    iu = np.arange(nu if wrap_u else nu - 1); iv = np.arange(nv if wrap_v else nv - 1)
    U, V = np.meshgrid(iu, iv, indexing="ij")
    U1 = (U + 1) % nu; V1 = (V + 1) % nv
    q = np.stack([U * nv + V, U1 * nv + V, U1 * nv + V1, U * nv + V1], -1).reshape(-1, 4)
    if flip:
        q = q[:, ::-1]
    return (q + offset).astype(np.int32)

class Geo:
    """Accumulates verts / faces / uvs / per-vertex colour into one mesh."""
    def __init__(self):
        self.v = []; self.f = {}; self.uv = []; self.c = []; self.n = 0
    def add(self, verts, faces, uv=None, color=None):
        verts = np.asarray(verts, np.float32).reshape(-1, 3); faces = np.asarray(faces, np.int32)
        self.v.append(verts)
        self.f.setdefault(faces.shape[1], []).append(faces + self.n)
        self.uv.append(np.zeros((len(verts), 2), np.float32) if uv is None else np.asarray(uv, np.float32))
        if color is None:
            color = (1, 1, 1, 1)
        c = np.asarray(color, np.float32)
        self.c.append(np.broadcast_to(c, (len(verts), 4)) if c.ndim == 1 else c)
        self.n += len(verts)
    def mesh(self, name, smooth=True):
        faces = [np.concatenate(v) for v in self.f.values()]
        return new_mesh(name, np.concatenate(self.v), faces, uvs=np.concatenate(self.uv), smooth=smooth,
                        attrs={"col": np.concatenate(self.c)})

def frames_along(path):
    """Parallel-transport frames (T, N, B) along a polyline (n,3)."""
    p = np.asarray(path, np.float64); n = len(p)
    T = np.zeros_like(p); T[1:-1] = p[2:] - p[:-2]; T[0] = p[1] - p[0]; T[-1] = p[-1] - p[-2]
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    ref = np.array([0, 0, 1.0]) if abs(T[0, 2]) < 0.9 else np.array([1.0, 0, 0])
    N = np.zeros_like(p); N[0] = np.cross(np.cross(T[0], ref), T[0]); N[0] /= np.linalg.norm(N[0])
    for i in range(1, n):
        v = N[i - 1] - T[i] * np.dot(N[i - 1], T[i])
        N[i] = v / (np.linalg.norm(v) + 1e-12)
    B = np.cross(T, N)
    return T, N, B

def tube(path, radii, segs=12, side=None, caps=True):
    """Swept tube. radii: (n,) or (n,2) [along N/side, along B]. side: optional (n,3) vectors fixing the N axis."""
    p = np.asarray(path, np.float64); n = len(p)
    r = np.asarray(radii, np.float64)
    if r.ndim == 1:
        r = np.stack([r, r], 1)
    T, N, B = frames_along(p)
    if side is not None:
        s = np.asarray(side, np.float64)
        s = s - T * np.sum(s * T, 1, keepdims=True); s /= np.linalg.norm(s, axis=1, keepdims=True) + 1e-12
        N = s; B = np.cross(T, N)
    a = np.linspace(0, 2 * np.pi, segs, endpoint=False)
    ring = (np.cos(a)[None, :, None] * N[:, None, :] * r[:, 0, None, None]
            + np.sin(a)[None, :, None] * B[:, None, :] * r[:, 1, None, None])
    verts = (p[:, None, :] + ring).reshape(-1, 3)
    faces = grid_faces(n, segs, wrap_v=True)
    tris = []
    if caps:
        c0 = len(verts); c1 = c0 + 1
        verts = np.vstack([verts, p[0], p[-1]])
        k = np.arange(segs); k1 = (k + 1) % segs
        tris = np.vstack([np.stack([np.full(segs, c0), k1, k], 1),
                          np.stack([np.full(segs, c1), (n - 1) * segs + k, (n - 1) * segs + k1], 1)])
    return verts, faces, np.asarray(tris, np.int32).reshape(-1, 3)

def ellipsoid(center, radii, nu=24, nv=14, power=1.0, rot=None):
    """UV ellipsoid / superellipsoid. Returns verts, faces, uv."""
    u = np.linspace(0, 2 * np.pi, nu + 1); v = np.linspace(-np.pi / 2, np.pi / 2, nv + 1)
    U, V = np.meshgrid(u, v, indexing="ij")
    sp = lambda x, e: np.sign(x) * np.abs(x) ** e
    x = sp(np.cos(V), power) * sp(np.cos(U), power); y = sp(np.cos(V), power) * sp(np.sin(U), power); z = sp(np.sin(V), power)
    P = np.stack([x, y, z], -1).reshape(-1, 3) * np.asarray(radii)
    if rot is not None:
        P = P @ np.asarray(rot).T
    P = P + np.asarray(center)
    uv = np.stack([U / (2 * np.pi), (V + np.pi / 2) / np.pi], -1).reshape(-1, 2)
    return P, grid_faces(nu + 1, nv + 1), uv

def rot_z(a):
    c, s = math.cos(a), math.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])
def rot_y(a):
    c, s = math.cos(a), math.sin(a); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
def rot_x(a):
    c, s = math.cos(a), math.sin(a); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])

# ---------- value noise (numpy) ----------
def _hash(ix, iy, seed):
    h = (ix * 374761393 + iy * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0

def vnoise(x, y, seed=0):
    x = np.asarray(x, np.float64); y = np.asarray(y, np.float64)
    ix = np.floor(x).astype(np.int64); iy = np.floor(y).astype(np.int64)
    fx = x - ix; fy = y - iy
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    a = _hash(ix, iy, seed); b = _hash(ix + 1, iy, seed); c = _hash(ix, iy + 1, seed); d = _hash(ix + 1, iy + 1, seed)
    return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy

def fbm(x, y, seed=0, octaves=4, lac=2.0, gain=0.5):
    s = 0.0; amp = 1.0; tot = 0.0
    for o in range(octaves):
        s = s + amp * vnoise(x * lac ** o, y * lac ** o, seed + o * 17); tot += amp; amp *= gain
    return s / tot

# ---------- materials ----------
def nodemat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree
    return m, nt.nodes, nt.links, nt.nodes["Principled BSDF"]

def simple_mat(name, color, rough=0.5, metal=0.0, **kw):
    m, N, L, P = nodemat(name)
    P.inputs["Base Color"].default_value = (*color, 1); P.inputs["Roughness"].default_value = rough
    P.inputs["Metallic"].default_value = metal
    for k, v in kw.items():
        P.inputs[k].default_value = v
    return m

def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a))) if b != a else float(x >= b)
    return t * t * (3 - 2 * t)

def lerp(a, b, t):
    return a + (b - a) * t
