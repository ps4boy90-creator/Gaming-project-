"""RPG-7 launcher and PG-7V HEAT rocket, modelled from public dimensions and reference photos.

Launcher (local +X = direction of fire, origin = centre of the muzzle face, +Z up, +Y = shooter's left):
40 mm steel tube 950 mm long; muzzle ring; front and rear iron sights; trigger group with pistol
grip; second (rear) grip; wooden heat shield over the wider charge chamber, held by steel bands;
conical blast bell with a rolled rim; PGO-7 optical sight on a bracket on the left side.

Rocket (local +X = flight direction, origin = nose tip): brass fuze cap, long conical nose,
85 mm body, tapered rear, nozzle block with six canted nozzles, 40 mm sustainer motor tube,
stabiliser tube with four spring-open fins and the tail turbine (flight configuration).
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion"))
from mathutils import Quaternion, Vector
from util import *
import env

GRIP_R = np.array([-0.350, 0.0, -0.112])     # middle of the trigger (pistol) grip
GRIP_L = np.array([-0.476, 0.0, -0.104])     # middle of the rear grip
FIN_HINGE_X = -0.720
FIN_LEN = 0.160
NOZZLE_X = -0.430

# ----------------------------------------------------------------------------- materials
def _noise_rough(N, L, P, scale, lo, hi):
    tc = N.new("ShaderNodeTexCoord"); n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = 4
    L.new(tc.outputs["Object"], n.inputs["Vector"])
    r = N.new("ShaderNodeMapRange"); r.inputs["To Min"].default_value = lo; r.inputs["To Max"].default_value = hi
    L.new(n.outputs["Fac"], r.inputs["Value"]); L.new(r.outputs["Result"], P.inputs["Roughness"])
    return tc, n

def materials():
    if "RpgSteel" in bpy.data.materials:
        return {m.name: m for m in bpy.data.materials if m.name.startswith("Rpg")}
    M = {}
    def metal(name, col, metallic, lo, hi, scale=140):
        m, N, L, P = nodemat(name); P.inputs["Base Color"].default_value = (*col, 1); P.inputs["Metallic"].default_value = metallic
        tc, n = _noise_rough(N, L, P, scale, lo, hi)
        b = N.new("ShaderNodeBump"); b.inputs["Strength"].default_value = 0.12; b.inputs["Distance"].default_value = 0.0004
        f = N.new("ShaderNodeTexNoise"); f.inputs["Scale"].default_value = 700; L.new(tc.outputs["Object"], f.inputs["Vector"])
        L.new(f.outputs["Fac"], b.inputs["Height"]); L.new(b.outputs["Normal"], P.inputs["Normal"])
        M[name] = m; return m
    metal("RpgSteel", (0.030, 0.032, 0.035), 0.85, 0.36, 0.56)            # blued / painted launcher steel
    metal("RpgAlu", (0.62, 0.62, 0.60), 1.0, 0.28, 0.42)                  # stabiliser tube, fins
    metal("RpgBrass", (0.62, 0.44, 0.16), 1.0, 0.25, 0.40)
    metal("RpgOlive", (0.050, 0.062, 0.030), 0.25, 0.42, 0.62)            # warhead
    metal("RpgOlive2", (0.100, 0.112, 0.045), 0.2, 0.45, 0.62)            # motor tube
    metal("RpgNozzle", (0.045, 0.050, 0.038), 0.55, 0.42, 0.6)
    # varnished plywood heat shield
    m, N, L, P = nodemat("RpgWood")
    tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (2.5, 55.0, 55.0)
    L.new(tc.outputs["Object"], mp.inputs[0])
    n = N.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 3.0; n.inputs["Detail"].default_value = 6; n.inputs["Distortion"].default_value = 1.2
    L.new(mp.outputs[0], n.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB"); e = ramp.color_ramp.elements
    e[0].position = 0.30; e[0].color = (0.085, 0.022, 0.008, 1); e[1].position = 0.72; e[1].color = (0.235, 0.072, 0.024, 1)
    L.new(n.outputs["Fac"], ramp.inputs["Fac"]); L.new(ramp.outputs["Color"], P.inputs["Base Color"])
    P.inputs["Roughness"].default_value = 0.34; P.inputs["Coat Weight"].default_value = 0.5; P.inputs["Coat Roughness"].default_value = 0.22
    M["RpgWood"] = m
    M["RpgGrip"] = simple_mat("RpgGrip", (0.050, 0.018, 0.009), rough=0.42)        # bakelite grips
    M["RpgRubber"] = simple_mat("RpgRubber", (0.012, 0.012, 0.012), rough=0.75)
    M["RpgLens"] = simple_mat("RpgLens", (0.01, 0.02, 0.04), rough=0.03, metal=0.6)
    M["RpgCanvas"] = simple_mat("RpgCanvas", (0.17, 0.15, 0.085), rough=0.95)
    return M

# ----------------------------------------------------------------------------- geometry helpers
def lathe(g, prof, segs=40, center=(0, 0, 0), close=False):
    """Revolve an (x, r) profile about the X axis."""
    p = np.asarray(prof, float); a = np.linspace(0, 2 * np.pi, segs, endpoint=False)
    V = np.stack([np.repeat(p[:, 0], segs), np.outer(p[:, 1], np.cos(a)).ravel(), np.outer(p[:, 1], np.sin(a)).ravel()], 1)
    g.add(V + np.asarray(center), grid_faces(len(p), segs, wrap_u=close, wrap_v=True))

def ring(g, x, r, w, h=0.0022, segs=40, center=(0, 0, 0)):
    """Raised band of width w around radius r."""
    lathe(g, [(x + w / 2, r - 0.001), (x + w / 2, r + h), (x - w / 2, r + h), (x - w / 2, r - 0.001)], segs, center)

def pipe(g, path, radii, segs=12, side=None):
    v, f, t = tube(np.array(path, float), np.array(radii, float), segs, side=side)
    g.add(v, f); g.add(v, t)

def box(g, size, center, rot=None):
    env.box_geo(g, size, center, rot)

def _finish(g, name, col, mat, parent, angle=38.0):
    me = g.mesh(name)
    try:
        me.set_sharp_from_angle(angle=math.radians(angle))
    except Exception:
        pass
    ob = new_obj(name, me, col, mat); ob.parent = parent
    return ob

def _root(name, col):
    ob = bpy.data.objects.new(name, None); (col or bpy.context.scene.collection).objects.link(ob)
    ob.rotation_mode = 'QUATERNION'; ob.empty_display_size = 0.1
    return ob

# ----------------------------------------------------------------------------- launcher
def build_launcher(col=None, sling=False, name="RPG7"):
    M = materials(); root = _root(name, col)
    st = Geo(); wd = Geo(); gr = Geo(); rb = Geo(); ln = Geo()
    # --- tube: outer skin, blast bell, then back up the inside (venturi throat, chamber, 40 mm bore)
    lathe(st, [(0.000, 0.0200), (0.000, 0.0265), (-0.014, 0.0265), (-0.016, 0.0235), (-0.425, 0.0235), (-0.427, 0.0300),
               (-0.790, 0.0300), (-0.792, 0.0275), (-0.802, 0.0275), (-0.822, 0.0300), (-0.935, 0.0560), (-0.944, 0.0605),
               (-0.950, 0.0610), (-0.950, 0.0575), (-0.936, 0.0535), (-0.822, 0.0270), (-0.795, 0.0160), (-0.745, 0.0270),
               (-0.500, 0.0270), (-0.470, 0.0200)], 48, close=True)
    # --- wooden heat shield: thick over the charge chamber, waisted towards the rear
    lathe(wd, [(-0.430, 0.0300), (-0.432, 0.0375), (-0.446, 0.0405), (-0.600, 0.0405), (-0.640, 0.0372), (-0.676, 0.0336),
               (-0.784, 0.0330), (-0.790, 0.0300)], 48)
    for x, r in ((-0.440, 0.0396), (-0.668, 0.0338), (-0.781, 0.0326)):
        ring(st, x, r, 0.011)
        box(st, (0.011, 0.012, 0.010), (x, 0, -r - 0.006))                      # clamp lug under each band
    # --- front sight: collar, base, folding post with protective ears
    ring(st, -0.078, 0.0235, 0.034, 0.003)
    box(st, (0.030, 0.022, 0.014), (-0.078, 0, 0.033))
    box(st, (0.005, 0.004, 0.040), (-0.078, 0, 0.060))
    for sy in (-1, 1):
        box(st, (0.012, 0.003, 0.030), (-0.078, sy * 0.010, 0.054))
    # --- sight / trigger housing band, rear sight leaf
    ring(st, -0.340, 0.0235, 0.090, 0.0035)
    box(st, (0.052, 0.030, 0.014), (-0.345, 0, 0.034))
    box(st, (0.005, 0.024, 0.044), (-0.352, 0, 0.062))
    box(st, (0.012, 0.004, 0.030), (-0.346, 0.013, 0.054)); box(st, (0.012, 0.004, 0.030), (-0.346, -0.013, 0.054))
    # --- trigger group: housing, hammer, guard, trigger
    box(st, (0.098, 0.026, 0.034), (-0.326, 0, -0.041))
    box(st, (0.022, 0.014, 0.024), (-0.388, 0, -0.036), rot_y(math.radians(-25)))
    pipe(st, [(-0.283, 0, -0.058), (-0.268, 0, -0.072), (-0.268, 0, -0.090), (-0.282, 0, -0.099), (-0.322, 0, -0.099), (-0.336, 0, -0.090)],
         [0.0024] * 6, 8)
    box(st, (0.005, 0.008, 0.024), (-0.300, 0, -0.072), rot_y(math.radians(18)))
    # --- grips (bakelite): pistol grip raked back, rear grip behind it under the front of the shield
    fwd = np.tile([1.0, 0, 0], (5, 1))
    def grip(top, bot, r0=(0.0185, 0.0135)):
        top = np.array(top); bot = np.array(bot)
        pts = [top + (bot - top) * u for u in (0, 0.2, 0.55, 0.9, 1.0)]
        pipe(gr, pts, [r0, r0, (r0[0] * 1.06, r0[1] * 1.04), (r0[0] * 1.02, r0[1]), (r0[0] * 0.8, r0[1] * 0.8)], 16, side=fwd)
    grip((-0.332, 0, -0.056), (-0.372, 0, -0.170))
    grip((-0.458, 0, -0.040), (-0.496, 0, -0.166), (0.0175, 0.013))
    ring(st, -0.458, 0.0396, 0.012)
    # --- PGO-7 optical sight on the left-hand bracket (periscopic: objective above the eyepiece)
    cy = 0.060
    box(st, (0.075, 0.010, 0.046), (-0.345, 0.031, 0.022))                      # dovetail plate on the housing band
    box(st, (0.036, 0.014, 0.040), (-0.345, 0.044, 0.050))                      # bracket arm
    box(st, (0.052, 0.040, 0.050), (-0.345, cy, 0.088))                         # prism housing
    box(st, (0.046, 0.036, 0.034), (-0.333, cy, 0.118), rot_y(math.radians(-20)))
    box(st, (0.030, 0.034, 0.030), (-0.366, cy, 0.074), rot_y(math.radians(25)))
    lathe(st, [(-0.322, 0.0170), (-0.286, 0.0170), (-0.284, 0.0190), (-0.272, 0.0190), (-0.272, 0.0155)], 24, (0, cy, 0.124))      # objective
    lathe(ln, [(-0.2735, 0.0155), (-0.2735, 0.0)], 24, (0, cy, 0.124))
    lathe(st, [(-0.366, 0.0145), (-0.410, 0.0145)], 24, (0, cy, 0.078))                                                            # eyepiece tube
    lathe(rb, [(-0.406, 0.0155), (-0.424, 0.0170), (-0.452, 0.0245), (-0.454, 0.0225), (-0.430, 0.0145), (-0.418, 0.0130)], 24, (0, cy, 0.078))
    lathe(ln, [(-0.419, 0.0130), (-0.419, 0.0)], 24, (0, cy, 0.078))
    pipe(st, [(-0.345, cy + 0.020, 0.090), (-0.345, cy + 0.031, 0.090)], [0.0085, 0.0085], 14)   # range / reticle knobs
    pipe(st, [(-0.345, cy, 0.136), (-0.345, cy, 0.146)], [0.0075, 0.0075], 14)
    if sling:
        u = np.linspace(0, 1, 26)
        path = np.stack([-0.095 - 0.68 * u, 0.034 + 0.004 * np.sin(u * np.pi), -0.012 - 0.13 * 4 * u * (1 - u)], 1)
        sl = Geo(); pipe(sl, path, np.tile([0.014, 0.0014], (26, 1)), 8, side=np.tile([0.0, 0.0, 1.0], (26, 1)))
        _finish(sl, name + "_sling", col, M["RpgCanvas"], root)
        for x in (-0.095, -0.775):
            pipe(st, [(x, 0.024, -0.006), (x, 0.040, -0.012)], [0.003, 0.003], 8)
    _finish(st, name + "_steel", col, M["RpgSteel"], root); _finish(wd, name + "_wood", col, M["RpgWood"], root)
    _finish(gr, name + "_grips", col, M["RpgGrip"], root); _finish(rb, name + "_rubber", col, M["RpgRubber"], root)
    _finish(ln, name + "_lens", col, M["RpgLens"], root)
    return root

# ----------------------------------------------------------------------------- rocket
class Rocket:
    def __init__(self, col=None, name="PG7V"):
        M = materials(); self.root = root = _root(name, col)
        br = Geo(); ol = Geo(); o2 = Geo(); nz = Geo(); al = Geo()
        # fuze cap + fuze body
        lathe(br, [(0.0, 0.0005), (-0.0012, 0.0055), (-0.0045, 0.0085), (-0.0200, 0.0085), (-0.0205, 0.0060)], 28)
        lathe(nz, [(-0.0200, 0.0105), (-0.0360, 0.0105), (-0.0365, 0.0125)], 28)
        # ballistic cone, 85 mm body, tapered rear
        lathe(ol, [(-0.0365, 0.0125), (-0.1900, 0.0375), (-0.2150, 0.0410), (-0.2320, 0.0425), (-0.2440, 0.0425), (-0.2440, 0.0434),
                   (-0.2500, 0.0434), (-0.2500, 0.0425), (-0.2640, 0.0424), (-0.2850, 0.0408), (-0.3300, 0.0340), (-0.3850, 0.0246),
                   (-0.3920, 0.0236)], 48)
        # nozzle block: crown with six nozzles canted outwards
        lathe(nz, [(-0.3920, 0.0236), (-0.4040, 0.0236), (-0.4090, 0.0275), (-0.4180, 0.0318), (-0.4380, 0.0318), (-0.4450, 0.0262),
                   (-0.4450, 0.0200)], 36)
        for k in range(6):
            a = k * math.pi / 3 + 0.3; c, s = math.cos(a), math.sin(a)
            pipe(nz, [(-0.4330, 0.0255 * c, 0.0255 * s), (-0.4500, 0.0300 * c, 0.0300 * s)], [0.0046, 0.0052], 10)
        # sustainer motor tube
        lathe(o2, [(-0.4450, 0.0200), (-0.6990, 0.0200), (-0.7000, 0.0180), (-0.7000, 0.0095)], 32)
        for x in (-0.520, -0.605):
            ring(o2, x, 0.0200, 0.008, 0.0012, 32)
        # stabiliser tube, fin hub, tail turbine
        lathe(al, [(-0.7000, 0.0095), (-0.9050, 0.0095)], 20)
        lathe(al, [(-0.7040, 0.0100), (-0.7050, 0.0152), (-0.7360, 0.0152), (-0.7370, 0.0100)], 20)
        lathe(al, [(-0.9000, 0.0095), (-0.9020, 0.0125), (-0.9250, 0.0125), (-0.9250, 0.0010)], 20)
        for k in range(6):
            a = k * math.pi / 3; R = rot_x(a) @ rot_z(math.radians(28))
            box(al, (0.018, 0.0010, 0.0080), tuple(np.array([-0.9135, 0, 0]) + rot_x(a) @ np.array([0, 0, 0.0158])), R)
        _finish(br, name + "_brass", col, M["RpgBrass"], root); _finish(ol, name + "_body", col, M["RpgOlive"], root)
        _finish(o2, name + "_motor", col, M["RpgOlive2"], root); _finish(nz, name + "_nozzle", col, M["RpgNozzle"], root)
        _finish(al, name + "_tail", col, M["RpgAlu"], root)
        self.parts = list(root.children)
        # four fins: fin-local +Z is radial, blade lies along -X when folded and swings outwards about local Y
        self.fins = []
        for k in range(4):
            g = Geo(); box(g, (FIN_LEN, 0.0012, 0.020), (-FIN_LEN / 2 - 0.004, 0, 0.0))
            ob = _finish(g, "%s_fin%d" % (name, k), col, M["RpgAlu"], root); ob.rotation_mode = 'QUATERNION'
            self.fins.append(ob)
        self.set_fins(math.radians(70))
        # tracer in the tail
        tm = bpy.data.materials.new(name + "Tracer"); tm.use_nodes = True; nt = tm.node_tree; nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (1.0, 0.45, 0.15, 1); em.inputs["Strength"].default_value = 0.0
        nt.links.new(em.outputs[0], out.inputs["Surface"]); self.tracer_em = em
        g = Geo(); lathe(g, [(-0.9255, 0.0085), (-0.9255, 0.0)], 12)
        self.tracer = _finish(g, name + "_tracer", col, tm, root); self.tracer.visible_shadow = False

    def set_fins(self, angle, visible=True):
        for k, ob in enumerate(self.fins):
            phi = k * math.pi / 2 + math.pi / 4
            ob.location = (FIN_HINGE_X, -0.0152 * math.sin(phi), 0.0152 * math.cos(phi))
            ob.rotation_quaternion = Quaternion((1, 0, 0), phi) @ Quaternion((0, 1, 0), angle) @ Quaternion((0, 0, 1), math.radians(2.5))
            ob.hide_render = not visible

    def set_visible(self, v):
        for ob in self.parts + self.fins + [self.tracer]:
            ob.hide_render = not v

def aim_quat(direction, roll=0.0):
    q = Vector(direction).to_track_quat('X', 'Z')
    return q @ Quaternion((1, 0, 0), roll) if roll else q
