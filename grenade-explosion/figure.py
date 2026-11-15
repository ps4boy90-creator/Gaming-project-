"""Transparent 'silhouette' human: a procedural mannequin rebuilt every frame from a pose
(2-bone IK limbs, lofted tubes fused with a voxel remesh) and shaded as refractive glass
with a bright fresnel rim, so it reads as a person without pulling focus from the grenade."""
import bpy, math
import numpy as np
from util import *

THIGH, SHIN, UARM, FARM, SPINE = 0.445, 0.445, 0.30, 0.265, 0.50
HIP_W, SHO_W = 0.095, 0.195

def ghost_material(name="Ghost", tint=(0.80, 0.93, 1.0), rim=(0.55, 0.85, 1.0), rim_strength=2.2):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links; N.clear()
    out = N.new("ShaderNodeOutputMaterial")
    glass = N.new("ShaderNodeBsdfGlass"); glass.inputs["Color"].default_value = (*tint, 1)
    glass.inputs["Roughness"].default_value = 0.04; glass.inputs["IOR"].default_value = 1.10
    lw = N.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.22
    pw = N.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 1.6
    L.new(lw.outputs["Facing"], pw.inputs[0])
    em = N.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*rim, 1); em.inputs["Strength"].default_value = rim_strength
    fac = N.new("ShaderNodeMath"); fac.operation = 'MULTIPLY'; fac.inputs[1].default_value = 0.85
    L.new(pw.outputs[0], fac.inputs[0])
    mix = N.new("ShaderNodeMixShader"); L.new(fac.outputs[0], mix.inputs[0]); L.new(glass.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2])
    # light, tinted shadow instead of a solid one (it is a ghost, not a statue)
    lp = N.new("ShaderNodeLightPath")
    tr = N.new("ShaderNodeBsdfTransparent"); tr.inputs["Color"].default_value = (0.55, 0.62, 0.68, 1)
    mix2 = N.new("ShaderNodeMixShader"); L.new(lp.outputs["Is Shadow Ray"], mix2.inputs[0]); L.new(mix.outputs[0], mix2.inputs[1]); L.new(tr.outputs[0], mix2.inputs[2])
    L.new(mix2.outputs[0], out.inputs["Surface"])
    return m

def _n(v):
    v = np.asarray(v, float); return v / (np.linalg.norm(v) + 1e-12)

def ik2(a, t, l1, l2, hint):
    a = np.asarray(a, float); t = np.asarray(t, float)
    d = t - a; dist = np.linalg.norm(d)
    dist_c = min(max(dist, abs(l1 - l2) + 1e-3), l1 + l2 - 1e-3)
    n = d / (dist + 1e-12)
    t = a + n * dist_c
    ca = (l1 * l1 + dist_c * dist_c - l2 * l2) / (2 * l1 * dist_c)
    sa = math.sqrt(max(0.0, 1 - ca * ca))
    h = np.asarray(hint, float); perp = h - n * np.dot(n, h)
    if np.linalg.norm(perp) < 1e-6:
        perp = np.cross(n, [0, 0, 1.0])
    perp = _n(perp)
    return a + n * (l1 * ca) + perp * (l1 * sa), t

def solve(pose):
    """pose -> dict of joint positions (figure-local, metres)."""
    P = {}
    pel = np.asarray(pose["pelvis"], float)
    yp, yc = pose["pelvis_yaw"], pose["chest_yaw"]
    side_p = np.array([-math.sin(yp), math.cos(yp), 0.0]); side_c = np.array([-math.sin(yc), math.cos(yc), 0.0])
    sdir = _n(pose["lean"])
    chest = pel + sdir * SPINE
    side_c = _n(side_c - sdir * np.dot(side_c, sdir))
    P.update(pelvis=pel, chest=chest, sdir=sdir, side_p=side_p, side_c=side_c)
    P["hip_l"] = pel + side_p * HIP_W - sdir * 0.03; P["hip_r"] = pel - side_p * HIP_W - sdir * 0.03
    P["sho_l"] = chest + side_c * SHO_W - sdir * 0.055; P["sho_r"] = chest - side_c * SHO_W - sdir * 0.055
    hy = pose.get("head_yaw", yc * 0.3)
    hdir = _n(sdir * 0.55 + np.array([0, 0, 0.45]) + np.array([math.cos(hy), math.sin(hy), 0]) * 0.10)
    P["neck"] = chest + sdir * 0.02
    P["head"] = P["neck"] + hdir * 0.185; P["head_fwd"] = np.array([math.cos(hy), math.sin(hy), 0.0]); P["head_up"] = hdir
    for s in ("l", "r"):
        sg = 1 if s == "l" else -1
        hand = np.asarray(pose["hand_" + s], float)
        P["elb_" + s], P["wri_" + s] = ik2(P["sho_" + s], hand, UARM, FARM, pose.get("elbow_" + s, (-0.3, sg * 0.6, -0.8)))
        ank = np.asarray(pose["foot_" + s], float) + np.array([0, 0, 0.075])
        fy = pose.get("foot_yaw_" + s, 0.0)
        fdir = np.array([math.cos(fy), math.sin(fy), 0.0])
        P["knee_" + s], P["ank_" + s] = ik2(P["hip_" + s], ank, THIGH, SHIN, pose.get("knee_" + s, fdir + side_p * sg * 0.25 + np.array([0, 0, 0.1])))
        pitch = pose.get("foot_pitch_" + s, 0.0)        # heel-up angle
        tdir = fdir * math.cos(pitch) - np.array([0, 0, 1.0]) * math.sin(pitch)
        P["toe_" + s] = P["ank_" + s] + tdir * 0.17 - np.array([0, 0, 0.045]) * math.cos(pitch)
        P["heel_" + s] = P["ank_" + s] - tdir * 0.065 - np.array([0, 0, 0.04]) * math.cos(pitch) + np.array([0, 0, 1.0]) * 0.0
    return P

def body_geo(P):
    g = Geo()
    def add_tube(path, radii, segs=14, side=None):
        v, f, t = tube(np.array(path), np.array(radii), segs, side=side)
        g.add(v, f); g.add(v, t)
    pel, chest, sdir = P["pelvis"], P["chest"], P["sdir"]
    # torso: crotch -> shoulders, twisting from pelvis orientation to chest orientation
    ts = np.array([-0.24, -0.13, 0.0, 0.22, 0.42, 0.64, 0.82, 0.95, 1.03, 1.10])
    rad = np.array([(0.07, 0.06), (0.165, 0.112), (0.186, 0.124), (0.166, 0.112), (0.156, 0.106), (0.178, 0.120),
                    (0.200, 0.130), (0.190, 0.118), (0.120, 0.090), (0.062, 0.060)])
    path = pel[None] + sdir[None] * (ts[:, None] * SPINE)
    w = np.clip(ts, 0, 1)[:, None]
    side = P["side_p"][None] * (1 - w) + P["side_c"][None] * w
    add_tube(path, rad, 20, side=side)
    # neck + head
    add_tube([P["neck"] - sdir * 0.03, P["neck"] + (P["head"] - P["neck"]) * 0.6], [0.064, 0.058], 12)
    up = P["head_up"]; fwd = _n(P["head_fwd"] - up * np.dot(P["head_fwd"], up)); lft = np.cross(up, fwd)
    Rh = np.stack([fwd, lft, up], 1)
    v, f, _ = ellipsoid(P["head"] + up * 0.02 + fwd * 0.012, (0.108, 0.086, 0.128), 20, 12, rot=Rh); g.add(v, f)
    v, f, _ = ellipsoid(P["head"] - up * 0.045 + fwd * 0.035, (0.078, 0.068, 0.082), 16, 10, rot=Rh); g.add(v, f)   # jaw
    for s in ("l", "r"):
        S, E, W = P["sho_" + s], P["elb_" + s], P["wri_" + s]
        v, f, _ = ellipsoid(S, (0.078, 0.078, 0.078), 14, 8); g.add(v, f)
        add_tube([S, (S + E) / 2, E, E + (W - E) * 0.3, W], [0.066, 0.060, 0.047, 0.050, 0.034], 12)
        hd = _n(W - E)
        v, f, _ = ellipsoid(W + hd * 0.055, (0.054, 0.048, 0.050), 14, 8); g.add(v, f)             # fist
        H, K, A = P["hip_" + s], P["knee_" + s], P["ank_" + s]
        add_tube([H + sdir * 0.04, (H + K) / 2, K, K + (A - K) * 0.3, A, A + _n(A - K) * 0.04], [0.106, 0.092, 0.066, 0.070, 0.046, 0.042], 14)
        T, Hl = P["toe_" + s], P["heel_" + s]
        add_tube([Hl, Hl + (T - Hl) * 0.35, Hl + (T - Hl) * 0.8, T], [(0.040, 0.036), (0.046, 0.040), (0.050, 0.030), (0.036, 0.020)], 12,
                 side=np.tile(np.cross(_n(T - Hl), [0, 0, 1.0]), (4, 1)))
    return g

class Figure:
    def __init__(self, col, name="Thrower", mat=None, voxel=0.011):
        self.me = bpy.data.meshes.new(name)
        self.ob = bpy.data.objects.new(name, self.me); col.objects.link(self.ob)
        self.mat = mat or ghost_material()
        rm = self.ob.modifiers.new("remesh", 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = voxel; rm.use_smooth_shade = True
        sm = self.ob.modifiers.new("smooth", 'SMOOTH'); sm.factor = 0.6; sm.iterations = 8
        self.joints = None
    def set_pose(self, pose):
        self.joints = solve(pose)
        me = body_geo(self.joints).mesh(self.ob.name + "_m")
        me.materials.append(self.mat)
        old = self.ob.data; self.ob.data = me
        bpy.data.meshes.remove(old)
        return self.joints

# ----------------------------------------------------------------- animation: overhand grenade throw
D = math.radians
def _k(t, pelvis, pyaw, lean, cyaw, hr, hl, fr, fl, er=(0.0, -0.6, -0.8), el=(-0.2, 0.7, -0.7), fyr=-80, fyl=-25, fpr=0.0, fpl=0.0, head=-10):
    return dict(t=t, pelvis=pelvis, pelvis_yaw=D(pyaw), lean=lean, chest_yaw=D(cyaw), hand_r=hr, hand_l=hl, foot_r=fr, foot_l=fl,
                elbow_r=er, elbow_l=el, foot_yaw_r=D(fyr), foot_yaw_l=D(fyl), foot_pitch_r=D(fpr), foot_pitch_l=D(fpl), head_yaw=D(head))

THROW_KEYS = [
    _k(-2.40, (-0.04, 0.00, 0.955), -72, (0.00, 0.00, 1), -80, (0.04, -0.24, 1.24), (0.13, -0.20, 1.22), (-0.22, -0.05, 0), (0.22, 0.05, 0), er=(-0.2, -0.3, -1)),
    _k(-1.55, (-0.04, 0.00, 0.955), -72, (0.00, 0.00, 1), -80, (0.04, -0.24, 1.24), (0.13, -0.20, 1.22), (-0.22, -0.05, 0), (0.22, 0.05, 0), er=(-0.2, -0.3, -1)),
    _k(-1.25, (-0.05, 0.00, 0.955), -74, (-0.02, 0.00, 1), -84, (0.00, -0.27, 1.26), (0.34, -0.02, 1.12), (-0.22, -0.05, 0), (0.22, 0.05, 0), er=(-0.2, -0.3, -1)),
    _k(-0.66, (-0.15, 0.00, 0.930), -86, (-0.24, -0.03, 1), -102, (-0.60, -0.22, 1.00), (0.56, 0.10, 1.50), (-0.22, -0.05, 0), (0.30, 0.06, 0.10),
       er=(-0.2, -0.5, -0.9), el=(0.0, 0.5, -0.9), fpl=-12),
    _k(-0.30, (0.04, 0.00, 0.905), -58, (-0.12, -0.05, 1), -96, (-0.46, -0.30, 1.60), (0.52, 0.18, 1.40), (-0.22, -0.05, 0), (0.56, 0.08, 0.0),
       er=(0.1, -1.0, 0.4), el=(0.0, 0.6, -0.8), fyl=-8, fpr=18),
    _k(-0.08, (0.17, 0.00, 0.920), -18, (0.10, 0.00, 1), -34, (-0.26, -0.34, 1.86), (0.30, 0.25, 1.20), (-0.21, -0.07, 0), (0.56, 0.08, 0.0),
       er=(0.7, -0.8, 0.4), fyl=-5, fpr=38, fyr=-40),
    _k(0.00, (0.24, 0.00, 0.930), 0, (0.28, 0.03, 1), 12, (0.80, -0.26, 1.93), (0.22, 0.24, 1.10), (-0.19, -0.08, 0.02), (0.56, 0.08, 0.0),
       er=(0.3, -0.6, -0.5), fyl=-5, fpr=55, fyr=-20, head=0),
    _k(0.22, (0.33, 0.00, 0.880), 20, (0.55, 0.08, 1), 46, (0.62, 0.10, 0.95), (0.10, 0.30, 1.05), (0.12, -0.17, 0.13), (0.56, 0.08, 0.0),
       er=(0.0, -0.7, -0.6), fyl=-5, fpr=30, fyr=0, head=0),
    _k(0.62, (0.38, 0.00, 0.900), 8, (0.36, 0.00, 1), 18, (0.46, -0.06, 0.86), (0.22, 0.28, 0.98), (0.44, -0.19, 0.0), (0.56, 0.08, 0.0), fyl=-5, fyr=0, head=0),
    _k(1.35, (0.34, 0.00, 0.640), 0, (0.50, 0.00, 1), 0, (0.56, -0.20, 0.66), (0.60, 0.22, 0.66), (0.44, -0.19, 0.0), (0.56, 0.08, 0.0), fyl=-5, fyr=0, head=0),
    _k(9.00, (0.34, 0.00, 0.640), 0, (0.50, 0.00, 1), 0, (0.56, -0.20, 0.66), (0.60, 0.22, 0.66), (0.44, -0.19, 0.0), (0.56, 0.08, 0.0), fyl=-5, fyr=0, head=0),
]
STAND = dict(pelvis=(0, 0, 0.965), pelvis_yaw=0, lean=(0.02, 0, 1), chest_yaw=0, hand_r=(0.04, -0.27, 0.80), hand_l=(0.04, 0.27, 0.80),
             foot_r=(0, -0.11, 0), foot_l=(0, 0.11, 0), foot_yaw_r=D(-8), foot_yaw_l=D(8), head_yaw=0)

def _cr(p0, p1, p2, p3, u):
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)

def throw_pose(t, keys=THROW_KEYS):
    """Catmull-Rom blend of the key poses at time t (seconds, release at t = 0)."""
    ts = [k["t"] for k in keys]
    t = min(max(t, ts[0]), ts[-1] - 1e-6)
    i = max(0, np.searchsorted(ts, t, side="right") - 1); i = min(i, len(keys) - 2)
    u = (t - ts[i]) / (ts[i + 1] - ts[i])
    k0, k1, k2, k3 = keys[max(i - 1, 0)], keys[i], keys[i + 1], keys[min(i + 2, len(keys) - 1)]
    out = {}
    for name in k1:
        if name == "t":
            continue
        a, b, c, d = (np.asarray(k[name], float) for k in (k0, k1, k2, k3))
        # non-uniform key spacing: scale tangents so overshoot stays small
        v = _cr(a, b, c, d, u) * 0.6 + (b + (c - b) * (u * u * (3 - 2 * u))) * 0.4
        out[name] = v if v.ndim else float(v)
    for s in ("r", "l"):                       # keep planted feet on the ground
        f = np.array(out["foot_" + s]); f[2] = max(f[2], 0.0); out["foot_" + s] = f
    return out
