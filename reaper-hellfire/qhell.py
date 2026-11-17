"""AGM-114R Hellfire II: 1.63 m long, 178 mm diameter, 0.33 m across the wings (Lockheed Martin product card).

Missile frame: tail (nozzle exit) at the origin, nose towards +X.  Layout from the manufacturer's display model and
service photographs: hemispherical glass seeker dome, four short strakes about 0.3 m behind the nose, four wide-chord
short-span wings on the rear third with the control fins at their trailing edges, launch shoes on top; black body with
a yellow (high explosive) band at the warhead and a brown (rocket motor) band ahead of the wings.
"""
import bpy, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from qgeo import *

LEN = 1.63; R = 0.089; SPAN = 0.33
BODY = (0.022, 0.024, 0.022, 1); YELLOW = (0.70, 0.50, 0.03, 1); BROWN = (0.26, 0.12, 0.05, 1); BRASS = (0.55, 0.42, 0.20, 1); STEEL = (0.18, 0.18, 0.19, 1)

def _mesh():
    S = Shell()
    V, Q, T = revolve([(0.0, 0.070), (0.035, R), (1.455, R), (1.50, R * 0.985)], 28); S.add(V, Q, T, BODY)
    V, Q, T = revolve([(0.0, 0.058), (0.05, 0.030), (0.051, 0.0)], 20); S.add(V, Q, T, (0.01, 0.01, 0.01, 1))                 # nozzle throat
    V, Q, T = revolve([(1.455, R + 0.0012), (1.505, R * 0.985 + 0.0012)], 28); S.add(V, Q, T, BRASS)                         # seeker ring
    V, Q, T = revolve([(0.985, R + 0.001), (1.035, R + 0.001)], 28); S.add(V, Q, T, YELLOW)
    V, Q, T = revolve([(0.555, R + 0.001), (0.605, R + 0.001)], 28); S.add(V, Q, T, BROWN)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2; r = np.array([0, math.cos(a), math.sin(a)]); n = np.array([0, -math.sin(a), math.cos(a)])
        P = lambda x, h: EX * x + r * h
        V, Q, T = plate([P(0.050, R - 0.004), P(0.455, R - 0.004), P(0.300, SPAN / 2), P(0.090, SPAN / 2)], n, 0.009); S.add(V, Q, T, BODY)     # wing
        V, Q, T = plate([P(0.042, R - 0.004), P(0.085, R - 0.004), P(0.085, SPAN / 2 - 0.004), P(0.050, SPAN / 2 - 0.004)], n, 0.011); S.add(V, Q, T, STEEL)   # control fin
        V, Q, T = plate([P(1.135, R - 0.004), P(1.335, R - 0.004), P(1.215, R + 0.050), P(1.150, R + 0.050)], n, 0.007); S.add(V, Q, T, BODY)   # forward strake
    for x in (0.30, 0.86, 1.24):                                                                                             # launch shoes
        V, Q, T = box((x, 0, R + 0.011), (0.075, 0.05, 0.03)); S.add(V, Q, T, STEEL)
    return S.mesh("hellfire")

def _dome():
    S = Shell(); pr = [(1.50, R * 0.985)] + [(1.50 + 0.128 * math.sin(a), R * 0.985 * math.cos(a)) for a in np.linspace(0, math.pi / 2, 9)[1:]]
    V, Q, T = revolve(pr, 28); S.add(V, Q, T, (0.02, 0.02, 0.03, 1))
    return S.mesh("hellfire_dome")

def flame_mat():
    """Rocket flame: emission that fades towards the tail of the cone and at its edge."""
    m = bpy.data.materials.new("MotorFlame"); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; L = nt.links; N.clear()
    out = N.new("ShaderNodeOutputMaterial"); em = N.new("ShaderNodeEmission"); tr = N.new("ShaderNodeBsdfTransparent"); mix = N.new("ShaderNodeMixShader")
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    ramp = N.new("ShaderNodeValToRGB"); e = ramp.color_ramp.elements; e[0].position = 0.0; e[0].color = (1.0, 0.95, 0.85, 1); e[1].position = 1.0; e[1].color = (1.0, 0.42, 0.10, 1)
    mr = N.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.0; mr.inputs["From Max"].default_value = -1.6; L.new(sep.outputs["X"], mr.inputs["Value"])
    L.new(mr.outputs[0], ramp.inputs["Fac"]); L.new(ramp.outputs["Color"], em.inputs["Color"])
    lw = N.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.35
    fade = N.new("ShaderNodeMath"); fade.operation = 'MULTIPLY'; inv = N.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    L.new(mr.outputs[0], inv.inputs[1]); inv2 = N.new("ShaderNodeMath"); inv2.operation = 'SUBTRACT'; inv2.inputs[0].default_value = 1.0; L.new(lw.outputs["Facing"], inv2.inputs[1])
    L.new(inv.outputs[0], fade.inputs[0]); L.new(inv2.outputs[0], fade.inputs[1])
    L.new(fade.outputs[0], mix.inputs["Fac"]); L.new(tr.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2]); L.new(mix.outputs[0], out.inputs["Surface"])
    em.inputs["Strength"].default_value = 60.0
    m["em_node"] = em.name
    return m

class Hellfire:
    def __init__(self, col=None, name="Hellfire"):
        col = col or bpy.context.scene.collection
        self.root = bpy.data.objects.new(name, None); col.objects.link(self.root); self.root.rotation_mode = 'QUATERNION'
        mats = bpy.data.materials
        pm = mats.get("HellfirePaint") or paint_mat("HellfirePaint", rough=0.42)
        gm = mats.get("HellfireDome") or glass_mat("HellfireDome", (0.035, 0.03, 0.025), rough=0.02)
        me = bpy.data.meshes.get("hellfire") or _mesh(); dm = bpy.data.meshes.get("hellfire_dome") or _dome()
        self.body = bpy.data.objects.new(name + "_Body", me); col.objects.link(self.body); self.body.parent = self.root
        if not me.materials:
            me.materials.append(pm)
        self.dome = bpy.data.objects.new(name + "_Dome", dm); col.objects.link(self.dome); self.dome.parent = self.root
        if not dm.materials:
            dm.materials.append(gm)
        self.flame = None; self.light = None
    def add_motor(self, col):
        """Flame cone behind the nozzle and a point light; both off until set_burn()."""
        S = Shell(); V, Q, T = revolve([(0.0, 0.050), (-0.10, 0.075), (-0.40, 0.085), (-0.9, 0.060), (-1.6, 0.0)], 20); S.add(V, Q, T)
        fm = flame_mat(); self.flame = new_obj(self.root.name + "_Flame", S.mesh("flame", sharp=3.0), col, fm); self.flame.parent = self.root
        self.flame.visible_shadow = False; self.em = fm.node_tree.nodes[fm["em_node"]]
        ld = bpy.data.lights.new(self.root.name + "_Glow", 'POINT'); ld.color = (1.0, 0.62, 0.30); ld.shadow_soft_size = 0.15; ld.energy = 0
        self.light = bpy.data.objects.new(self.root.name + "_Glow", ld); col.objects.link(self.light); self.light.parent = self.root; self.light.location = (-0.35, 0, 0)
        self.set_burn(0.0)
    def set_burn(self, k, length=1.0):
        on = k > 0.01
        self.flame.hide_render = not on; self.light.hide_render = not on
        if on:
            self.flame.scale = (length * (0.6 + 0.4 * k), 1, 1); self.em.inputs["Strength"].default_value = 70.0 * k; self.light.data.energy = 1100.0 * k
    def set_visible(self, v):
        self.body.hide_render = not v; self.dome.hide_render = not v
