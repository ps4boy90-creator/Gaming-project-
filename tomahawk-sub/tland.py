"""Desert hill country for the low-level cruise, and the coast the missile crosses on the way in.

height(x, y) is the ground everywhere; the missile's track is the line y = 0 flown towards +X.  The country is
invented: bare ridges and gravel fans of the kind found in southern Afghanistan, not a real place."""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("grenade-explosion", "rpg7-explosion", "mortar-explosion", "howitzer-explosion", "reaper-hellfire"):
    sys.path.insert(0, os.path.join(HERE, "..", p))
sys.path.insert(0, HERE)
import env
from util import new_mesh, new_obj, grid_faces, nodemat, fbm
import tconst as C

def height(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    big = fbm(x / 3400.0 + 11.3, y / 3400.0 + 4.1, 5, 4)
    ridge = 1.0 - np.abs(2.0 * fbm(x / 1900.0 + 3.1, y / 1500.0 - 1.7, 11, 5) - 1.0)
    mask = np.clip((big - 0.36) / 0.34, 0.0, 1.0); mask = mask * mask * (3 - 2 * mask)
    h = 330.0 * ridge ** 2.4 * mask + 150.0 * (big - 0.5) + 22.0 * (fbm(x / 260.0, y / 260.0, 7, 4) - 0.5) + 2.2 * (fbm(x / 28.0, y / 28.0, 9, 3) - 0.5)
    return h + 75.0

_XS = np.arange(-4000.0, 14000.0, 20.0)
def _track():
    h = height(_XS, np.zeros_like(_XS)); n = len(h); w = 9                           # highest ground within 180 m ahead and behind, then smoothed: what a terrain-following autopilot flies
    hm = np.array([h[max(0, i - w):i + w + 1].max() for i in range(n)]); k = np.exp(-0.5 * (np.arange(-30, 31) / 11.0) ** 2); k /= k.sum()
    return np.convolve(np.pad(hm, 30, mode="edge"), k, mode="valid") + 42.0
_ALT = _track()

def track_alt(x):
    return float(np.interp(x, _XS, _ALT))

def cruise_state(tc, x0=0.0):
    """Land set: body centre and velocity tc seconds into the low-level run."""
    x = x0 + C.V_CRUISE * tc; e = 4.0; z = track_alt(x); dz = (track_alt(x + e) - track_alt(x - e)) / (2 * e)
    return np.array([x, 0.0, z]), np.array([1.0, 0.0, dz]) / math.hypot(1.0, dz) * C.V_CRUISE

def land_mat(name="Desert"):
    """Sand on the flats, darker bare rock where it is steep, paler dust in the hollows."""
    m, N, L, P = nodemat(name); geo = N.new("ShaderNodeNewGeometry"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(geo.outputs["Normal"], sep.inputs[0])
    tc = N.new("ShaderNodeTexCoord")
    def noise(scale, detail=6, rough=0.6):
        n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail; n.inputs["Roughness"].default_value = rough; L.new(tc.outputs["Object"], n.inputs["Vector"]); return n
    n1 = noise(1 / 420.0, 8, 0.62); n2 = noise(1 / 38.0, 6); n3 = noise(1 / 2.2, 4)
    sand = N.new("ShaderNodeValToRGB"); e = sand.color_ramp.elements; e[0].position = 0.34; e[0].color = (0.170, 0.122, 0.078, 1); e[1].position = 0.70; e[1].color = (0.470, 0.375, 0.250, 1); L.new(n1.outputs["Fac"], sand.inputs["Fac"])
    rock = N.new("ShaderNodeValToRGB"); e = rock.color_ramp.elements; e[0].position = 0.30; e[0].color = (0.085, 0.066, 0.050, 1); e[1].position = 0.75; e[1].color = (0.215, 0.165, 0.120, 1); L.new(n2.outputs["Fac"], rock.inputs["Fac"])
    steep = N.new("ShaderNodeMapRange"); steep.inputs["From Min"].default_value = 0.985; steep.inputs["From Max"].default_value = 0.90; L.new(sep.outputs["Z"], steep.inputs["Value"])
    mix = N.new("ShaderNodeMixRGB"); L.new(steep.outputs[0], mix.inputs[0]); L.new(sand.outputs["Color"], mix.inputs[1]); L.new(rock.outputs["Color"], mix.inputs[2])
    var = N.new("ShaderNodeMapRange"); var.inputs["To Min"].default_value = 0.78; var.inputs["To Max"].default_value = 1.18; L.new(n2.outputs["Fac"], var.inputs["Value"])
    m2 = N.new("ShaderNodeMixRGB"); m2.blend_type = 'MULTIPLY'; m2.inputs[0].default_value = 1.0; L.new(mix.outputs[0], m2.inputs[1]); L.new(var.outputs[0], m2.inputs[2]); L.new(m2.outputs[0], P.inputs["Base Color"])
    P.inputs["Roughness"].default_value = 0.95
    b = N.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.6; b.inputs["Distance"].default_value = 0.6; L.new(n3.outputs["Fac"], b.inputs["Height"]); L.new(b.outputs["Normal"], P.inputs["Normal"])
    return m

def _grid(name, xs, ys, col, mat, coast=None, drop=0.0):
    X, Y = np.meshgrid(xs, ys, indexing="ij"); Z = height(X, Y) - drop
    if coast is not None:                                              # fade the land into the sea along a wandering shore
        shore = coast + 700.0 * (fbm(Y / 5200.0 + 2.2, Y * 0.0 + 0.3, 3, 4) - 0.5); k = np.clip((X - shore) / 2600.0, -0.02, 1.0); k = np.where(k > 0, k * k * (3 - 2 * k), k); Z = Z * np.maximum(k, 0) + 240.0 * np.minimum(k, 0) + 1.5 * (k > 0)
    V = np.stack([X, Y, Z], -1).reshape(-1, 3); return new_obj(name, new_mesh(name, V, [grid_faces(len(xs), len(ys))]), col, mat)

def build_land(sc, x0, x1, half=2600.0):
    """Sky, sun and the hills: a fine sheet under the run from x0 to x1 and a coarse one out to the haze."""
    col = bpy.data.collections.new("ENV"); sc.collection.children.link(col); env.make_world(sc); m = land_mat()
    _grid("LandNear", np.arange(x0 - 600.0, x1 + 3200.0, 11.0), np.arange(-half, half + 1, 11.0), col, m)
    _grid("LandFar", np.arange(x0 - 9000.0, x1 + 46000.0, 170.0), np.arange(-26000.0, 26001.0, 170.0), col, m, drop=5.0)
    return col

def build_coast(sc, coast_x=5200.0):
    """Sky, sun, and the land beyond a shore that lies across the track at about coast_x; the sea itself comes from tsea."""
    col = bpy.data.collections.new("LAND"); sc.collection.children.link(col); m = land_mat("DesertCoast")
    _grid("Coast", np.arange(coast_x - 1600.0, coast_x + 42000.0, 110.0), np.arange(-30000.0, 30001.0, 110.0), col, m, coast=coast_x)
    return col
