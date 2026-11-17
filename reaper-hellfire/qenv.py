"""The two places of the MQ-9 / Hellfire segment: open desert with a vehicle track (target set) and the same desert
seen from 20,000 ft (air set)."""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
import env, htown
from util import new_mesh, new_obj, grid_faces, nodemat, fbm
import qconst as C

CRATER_R = 0.75
TRACK_W = 3.6

def _track(col):
    """Vehicle track along Y through the target point: two wheel ruts of compacted sand, drawn just above the ground."""
    ny, nx = 620, 9; ys = np.linspace(-520.0, 100.0, ny); us = np.linspace(-0.5, 0.5, nx)
    Y, Uq = np.meshgrid(ys, us, indexing="ij"); X = Uq * TRACK_W + 0.9 * np.sin(Y * 0.011 + 0.4) * np.clip(np.abs(Y) / 60.0 - 0.4, 0, 1)
    edge = np.minimum.reduce([X + 52, 30 - X, Y + 24, 32 - Y]); k = np.clip(edge / 4.0, 0, 1); k = k * k * (3 - 2 * k)
    Z = -0.035 + (env.ground_h(X, Y) + 0.035) * k + 0.022
    V = np.stack([X, Y, Z], -1).reshape(-1, 3); uv = np.stack([Uq + 0.5, Y / 4.0], -1).reshape(-1, 2)
    me = new_mesh("track", V, [grid_faces(ny, nx)], uvs=uv)
    m, N, L, P = nodemat("TrackMat"); tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["UV"], sep.inputs[0])
    def bump(center):
        a = N.new("ShaderNodeMath"); a.operation = 'SUBTRACT'; a.inputs[1].default_value = center; L.new(sep.outputs["X"], a.inputs[0])
        b = N.new("ShaderNodeMath"); b.operation = 'ABSOLUTE'; L.new(a.outputs[0], b.inputs[0])
        c = N.new("ShaderNodeMapRange"); c.inputs["From Min"].default_value = 0.13; c.inputs["From Max"].default_value = 0.02; L.new(b.outputs[0], c.inputs["Value"]); return c
    r1 = bump(0.27); r2 = bump(0.73); mx = N.new("ShaderNodeMath"); mx.operation = 'MAXIMUM'; L.new(r1.outputs[0], mx.inputs[0]); L.new(r2.outputs[0], mx.inputs[1])
    edge_ = N.new("ShaderNodeMath"); edge_.operation = 'SUBTRACT'; edge_.inputs[1].default_value = 0.5; L.new(sep.outputs["X"], edge_.inputs[0])
    ea = N.new("ShaderNodeMath"); ea.operation = 'ABSOLUTE'; L.new(edge_.outputs[0], ea.inputs[0])
    band = N.new("ShaderNodeMapRange"); band.inputs["From Min"].default_value = 0.5; band.inputs["From Max"].default_value = 0.36; band.inputs["To Max"].default_value = 0.30; L.new(ea.outputs[0], band.inputs["Value"])
    n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 0.9; n.inputs["Detail"].default_value = 5; L.new(tc.outputs["Object"], n.inputs["Vector"])
    al = N.new("ShaderNodeMath"); al.operation = 'MULTIPLY'; al.inputs[1].default_value = 0.62; L.new(mx.outputs[0], al.inputs[0])
    al2 = N.new("ShaderNodeMath"); al2.operation = 'ADD'; L.new(al.outputs[0], al2.inputs[0]); L.new(band.outputs[0], al2.inputs[1])
    al3 = N.new("ShaderNodeMath"); al3.operation = 'MULTIPLY'; L.new(al2.outputs[0], al3.inputs[0]); L.new(n.outputs["Fac"], al3.inputs[1])
    al4 = N.new("ShaderNodeMath"); al4.operation = 'MULTIPLY'; al4.inputs[1].default_value = 1.7; al4.use_clamp = True; L.new(al3.outputs[0], al4.inputs[0])
    L.new(al4.outputs[0], P.inputs["Alpha"]); P.inputs["Base Color"].default_value = (0.215, 0.165, 0.110, 1); P.inputs["Roughness"].default_value = 0.95
    ob = new_obj("Track", me, col, m); ob.visible_shadow = False
    return ob

def build_target(sc, seed=11):
    rng = np.random.default_rng(seed); np.random.seed(seed)
    col = bpy.data.collections.new("ENV"); sc.collection.children.link(col)
    env.make_world(sc); ground = env.build_ground(col); htown.sandy(ground, CRATER_R); env.build_stones(col, rng, -200.0); htown.desert_hills(col, rng, 2.4)
    _track(col)
    return col, ground

def desert_floor_mat():
    """Desert from high altitude: pale sand sheets, darker gravel plains, branching dry wadis; fades into haze with distance."""
    m, N, L, P = nodemat("DesertFar"); tc = N.new("ShaderNodeTexCoord")
    def noise(scale, detail=8, rough=0.55, dist=0.0):
        n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail; n.inputs["Roughness"].default_value = rough
        n.inputs["Distortion"].default_value = dist; L.new(tc.outputs["Object"], n.inputs["Vector"]); return n
    big = noise(1 / 5200.0, 9, 0.60, 0.6); mid = noise(1 / 900.0, 9, 0.62, 0.3); fine = noise(1 / 110.0, 7, 0.6)
    r1 = N.new("ShaderNodeValToRGB"); e = r1.color_ramp.elements; e[0].position = 0.30; e[0].color = (0.105, 0.070, 0.040, 1); e[1].position = 0.70; e[1].color = (0.300, 0.215, 0.120, 1)
    el = r1.color_ramp.elements.new(0.52); el.color = (0.200, 0.140, 0.080, 1); L.new(big.outputs["Fac"], r1.inputs["Fac"])
    r2 = N.new("ShaderNodeValToRGB"); e = r2.color_ramp.elements; e[0].position = 0.36; e[0].color = (0.42, 0.38, 0.33, 1); e[1].position = 0.70; e[1].color = (1.35, 1.25, 1.08, 1); L.new(mid.outputs["Fac"], r2.inputs["Fac"])
    m1 = N.new("ShaderNodeMixRGB"); m1.blend_type = 'MULTIPLY'; m1.inputs[0].default_value = 1.0; L.new(r1.outputs["Color"], m1.inputs[1]); L.new(r2.outputs["Color"], m1.inputs[2])
    wad = noise(1 / 2600.0, 10, 0.68, 2.2)                                    # wadis: thin dark lines where a distorted noise crosses 0.5
    wa = N.new("ShaderNodeMath"); wa.operation = 'SUBTRACT'; wa.inputs[1].default_value = 0.5; L.new(wad.outputs["Fac"], wa.inputs[0])
    wb = N.new("ShaderNodeMath"); wb.operation = 'ABSOLUTE'; L.new(wa.outputs[0], wb.inputs[0])
    wc = N.new("ShaderNodeMapRange"); wc.inputs["From Min"].default_value = 0.0; wc.inputs["From Max"].default_value = 0.014; wc.inputs["To Min"].default_value = 0.38; wc.inputs["To Max"].default_value = 1.0; L.new(wb.outputs[0], wc.inputs["Value"])
    m2 = N.new("ShaderNodeMixRGB"); m2.blend_type = 'MULTIPLY'; m2.inputs[0].default_value = 1.0; L.new(m1.outputs[0], m2.inputs[1]); L.new(wc.outputs[0], m2.inputs[2])
    r3 = N.new("ShaderNodeMapRange"); r3.inputs["To Min"].default_value = 0.70; r3.inputs["To Max"].default_value = 1.25; L.new(fine.outputs["Fac"], r3.inputs["Value"])
    m3 = N.new("ShaderNodeMixRGB"); m3.blend_type = 'MULTIPLY'; m3.inputs[0].default_value = 1.0; L.new(m2.outputs[0], m3.inputs[1]); L.new(r3.outputs[0], m3.inputs[2])
    L.new(m3.outputs[0], P.inputs["Base Color"]); P.inputs["Roughness"].default_value = 0.95
    cd = N.new("ShaderNodeCameraData"); hz = N.new("ShaderNodeMapRange"); hz.inputs["From Min"].default_value = 7000.0; hz.inputs["From Max"].default_value = 260000.0; hz.inputs["To Max"].default_value = 1.0
    L.new(cd.outputs["View Distance"], hz.inputs["Value"]); pw = N.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 0.62; L.new(hz.outputs[0], pw.inputs[0])
    em = N.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.50, 0.61, 0.78, 1); em.inputs["Strength"].default_value = 0.60
    mixs = N.new("ShaderNodeMixShader"); out = [n for n in N if n.type == 'OUTPUT_MATERIAL'][0]
    L.new(pw.outputs[0], mixs.inputs["Fac"]); L.new(P.outputs[0], mixs.inputs[1]); L.new(em.outputs[0], mixs.inputs[2]); L.new(mixs.outputs[0], out.inputs["Surface"])
    m["haze"] = em.name
    return m

def build_air(sc, alt=C.ALT):
    """Sky and the desert floor `alt` metres below the origin, out to the horizon."""
    col = bpy.data.collections.new("ENV"); sc.collection.children.link(col)
    env.make_world(sc)
    na = 180; rr = np.concatenate([[0.0], np.geomspace(200.0, 9.0e5, 60)]); a = np.linspace(0, 2 * np.pi, na, endpoint=False)
    A, Rr = np.meshgrid(a, rr, indexing="ij"); V = np.stack([Rr * np.cos(A), Rr * np.sin(A), np.full_like(A, -alt)], -1).reshape(-1, 3)
    ob = new_obj("DesertFloor", new_mesh("desert_floor", V, [grid_faces(na, len(rr), wrap_u=True)]), col, desert_floor_mat())
    return col, ob
