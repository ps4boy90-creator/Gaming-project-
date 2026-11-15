"""Volume shader for the blast: sooty/dusty smoke (per-voxel colour) + blackbody-ish fire."""
import bpy

def blast_material(density=10.0, fire=120.0, ambient=0.085):
    mat = bpy.data.materials.new("BlastVolume")
    mat.use_nodes = True
    nt = mat.node_tree; N = nt.nodes; L = nt.links
    N.clear()
    out = N.new("ShaderNodeOutputMaterial")
    a_d = N.new("ShaderNodeAttribute"); a_d.attribute_name = "density"
    a_c = N.new("ShaderNodeAttribute"); a_c.attribute_name = "color"
    a_f = N.new("ShaderNodeAttribute"); a_f.attribute_name = "flame"
    # colour grid is premultiplied by density -> un-premultiply
    div = N.new("ShaderNodeVectorMath"); div.operation = 'DIVIDE'
    mx = N.new("ShaderNodeMath"); mx.operation = 'MAXIMUM'; mx.inputs[1].default_value = 1e-4
    L.new(a_d.outputs["Fac"], mx.inputs[0])
    L.new(a_c.outputs["Vector"], div.inputs[0]); L.new(mx.outputs[0], div.inputs[1])
    # soft density curve: thin wisps stay thin, cores go opaque
    dm = N.new("ShaderNodeMath"); dm.operation = 'MULTIPLY'; dm.inputs[1].default_value = density
    L.new(a_d.outputs["Fac"], dm.inputs[0])
    pv = N.new("ShaderNodeVolumePrincipled")
    pv.inputs["Anisotropy"].default_value = 0.40
    # lift the (dark, sooty) sim colours towards dusty grey-brown
    lift = N.new("ShaderNodeVectorMath"); lift.operation = 'POWER'; lift.inputs[1].default_value = (0.55, 0.55, 0.55)
    cl = N.new("ShaderNodeVectorMath"); cl.operation = 'MAXIMUM'; cl.inputs[1].default_value = (0.02, 0.02, 0.02)
    L.new(div.outputs[0], cl.inputs[0]); L.new(cl.outputs[0], lift.inputs[0])
    mn = N.new("ShaderNodeVectorMath"); mn.operation = 'MINIMUM'; mn.inputs[1].default_value = (0.80, 0.74, 0.66)
    warm = N.new("ShaderNodeVectorMath"); warm.operation = 'MULTIPLY'; warm.inputs[1].default_value = (1.0, 0.90, 0.78)
    L.new(lift.outputs[0], warm.inputs[0]); L.new(warm.outputs[0], mn.inputs[0])
    L.new(mn.outputs[0], pv.inputs["Color"])
    L.new(dm.outputs[0], pv.inputs["Density"])
    # cheap stand-in for multiple scattering / sky fill: a faint self-glow in the smoke's own colour
    amb = N.new("ShaderNodeEmission"); amb.inputs["Strength"].default_value = ambient
    tint = N.new("ShaderNodeVectorMath"); tint.operation = 'MULTIPLY'; tint.inputs[1].default_value = (1.0, 0.95, 0.90)
    L.new(mn.outputs[0], tint.inputs[0]); L.new(tint.outputs[0], amb.inputs["Color"])
    ambd = N.new("ShaderNodeMath"); ambd.operation = 'MULTIPLY'; ambd.inputs[1].default_value = ambient
    dcl = N.new("ShaderNodeMath"); dcl.operation = 'MINIMUM'; dcl.inputs[1].default_value = 6.0
    L.new(dm.outputs[0], dcl.inputs[0]); L.new(dcl.outputs[0], ambd.inputs[0]); L.new(ambd.outputs[0], amb.inputs["Strength"])
    # fire: flame grid 0..1 -> emission ramp (deep red -> orange -> yellow-white)
    ramp = N.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.02; cr.elements[0].color = (0, 0, 0, 1)
    cr.elements[1].position = 1.0; cr.elements[1].color = (1.0, 0.86, 0.55, 1)
    e = cr.elements.new(0.18); e.color = (0.75, 0.10, 0.0, 1)
    e = cr.elements.new(0.45); e.color = (1.0, 0.40, 0.04, 1)
    e = cr.elements.new(0.75); e.color = (1.0, 0.68, 0.22, 1)
    L.new(a_f.outputs["Fac"], ramp.inputs["Fac"])
    fs = N.new("ShaderNodeMath"); fs.operation = 'POWER'; fs.inputs[1].default_value = 1.6
    L.new(a_f.outputs["Fac"], fs.inputs[0])
    fm = N.new("ShaderNodeMath"); fm.operation = 'MULTIPLY'; fm.inputs[1].default_value = fire
    L.new(fs.outputs[0], fm.inputs[0])
    L.new(ramp.outputs["Color"], pv.inputs["Emission Color"])
    L.new(fm.outputs[0], pv.inputs["Emission Strength"])
    pv.inputs["Blackbody Intensity"].default_value = 0.0
    add = N.new("ShaderNodeAddShader"); L.new(pv.outputs[0], add.inputs[0]); L.new(amb.outputs[0], add.inputs[1])
    L.new(add.outputs[0], out.inputs["Volume"])
    mat["density_node"] = dm.name; mat["fire_node"] = fm.name
    return mat
