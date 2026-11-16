"""Bake the two Mantaflow gas sims of the RPG-7 segment to OpenVDB caches.

  python3 rsim.py launch|impact <cache_dir> <resolution> <frames> [noise 0|1]

launch : backblast out of the blast bell, muzzle puff, dust kicked up behind the shooter (frame 1 = trigger)
impact : HEAT warhead on the brick wall - fireball and soot on the front face, brick dust thrown off the
         face, and the jet / spall cloud bursting out of the back through the breach (frame 1 = impact)
Master timeline: 1 frame = 1/240 s (scene fps 24 * time_scale 0.1).
"""
import bpy, sys, math, random, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, HERE)
import manta_fix  # noqa: F401
from mathutils import Vector
import rconst as C

TIME_SCALE = 0.1
DT = TIME_SCALE / 24.0
DOMAINS = {"launch": ((15.0, 7.0, 5.2), (C.SHOOT_X - 3.0, 0.0)), "impact": ((12.0, 9.0, 6.5), (-0.5, 0.0))}
BRICK = [(0.50, 0.37, 0.29), (0.43, 0.32, 0.26), (0.55, 0.43, 0.34)]

def make_domain(kind, cache_dir, res, frames, noise):
    sc = bpy.context.scene; sc.render.fps = 24; sc.frame_start, sc.frame_end = 1, frames
    size, (cx, cy) = DOMAINS[kind]
    bpy.ops.mesh.primitive_cube_add(size=1)
    dom = bpy.context.active_object; dom.name = "BlastDomain"; dom.scale = size; dom.location = (cx, cy, -0.12 + size[2] / 2)
    m = dom.modifiers.new("Fluid", 'FLUID'); m.fluid_type = 'DOMAIN'; d = m.domain_settings
    d.domain_type = 'GAS'; d.resolution_max = res; d.time_scale = TIME_SCALE
    d.use_adaptive_timesteps = True; d.cfl_condition = 4.0; d.timesteps_max = 10; d.timesteps_min = 1
    d.use_collision_border_bottom = True
    for k in ("front", "back", "left", "right", "top"):
        setattr(d, "use_collision_border_" + k, False)
    d.alpha = -0.18; d.beta = 1.5; d.vorticity = 0.4
    d.use_dissolve_smoke = False
    d.burning_rate = 5.0 if kind == "impact" else 3.4; d.flame_smoke = 2.2; d.flame_vorticity = 0.6; d.flame_ignition = 1.5; d.flame_max_temp = 3.2
    d.flame_smoke_color = (0.13, 0.12, 0.11) if kind == "impact" else (0.5, 0.49, 0.47)
    d.use_noise = bool(noise)
    if noise:
        d.noise_scale = 2; d.noise_strength = 1.4; d.noise_pos_scale = 2.5; d.noise_time_anim = 0.15
    d.cache_type = 'ALL'; d.cache_data_format = 'OPENVDB'; d.openvdb_cache_compress_type = 'ZIP'
    d.cache_directory = cache_dir; d.cache_frame_start = 1; d.cache_frame_end = frames; d.cache_resumable = False
    return dom

def flow(ob, kind, on, off, dens=1.0, temp=1.0, fuel=0.0, color=None, vn=0.0, vfac=0.0, vinit=None, sub=2):
    m = ob.modifiers.new("Fluid", 'FLUID'); m.fluid_type = 'FLOW'; f = m.flow_settings
    f.flow_type = kind; f.flow_behavior = 'INFLOW'; f.flow_source = 'MESH'; f.density = dens; f.temperature = temp
    if kind in ('FIRE', 'BOTH'):
        f.fuel_amount = fuel
    if color:
        f.use_absolute = False; f.smoke_color = color
    f.surface_distance = 0.6; f.volume_density = 1.0; f.subframes = sub
    f.use_initial_velocity = True; f.velocity_normal = vn; f.velocity_factor = vfac
    if vinit:
        f.velocity_coord = tuple(vinit)
    for fr, val in ((on - 1, False), (on, True), (off, True), (off + 1, False)):
        f.use_inflow = val; f.keyframe_insert("use_inflow", frame=fr)
    return f

def ico(name, r, loc, sub=3, rough=0.0, scale=None):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=tuple(loc))
    ob = bpy.context.active_object; ob.name = name
    for v in ob.data.vertices:
        if rough:
            v.co *= 1.0 + random.uniform(-rough, rough)
        if scale:
            v.co.x *= scale[0]; v.co.y *= scale[1]; v.co.z *= scale[2]
    return ob

def jet(name, origin, dirv, speed, drag, life, r, color, start=1, dens=1.6, zmin=0.08):
    """Small emitter thrown along a ballistic path with drag; leaves a dust trail."""
    e = ico(name, r, origin, sub=1); dirv = Vector(dirv).normalized(); o = Vector(origin)
    for fr in range(start, start + life + 2):
        t = (fr - start) * DT
        p = o + dirv * (speed / drag * (1 - math.exp(-drag * t))) + Vector((0, 0, -0.5 * 9.81 * t * t)); p.z = max(p.z, zmin)
        e.location = p; e.keyframe_insert("location", frame=fr)
        s = max(0.25, 1.0 - 0.6 * (fr - start) / life); e.scale = (s, s, s); e.keyframe_insert("scale", frame=fr)
    flow(e, 'SMOKE', start, start + life, dens=dens, temp=0.2, color=color, vn=1.5, vfac=0.55, sub=3)

def cone_dir(axis_sign, max_deg, up_bias=0.0):
    c = math.radians(random.uniform(4, max_deg)); a = random.uniform(0, math.tau)
    return (axis_sign * math.cos(c), math.sin(c) * math.cos(a), math.sin(c) * math.sin(a) + up_bias)

def build_impact():
    Z = C.ZI; T = C.WALL_T; hw = C.WALL_W / 2                 # collider: the wall with a ragged round breach
    import bmesh
    bm = bmesh.new(); n = 28
    def rim(a):
        return 0.33 * (1 + 0.16 * math.sin(3 * a + 1.0) + 0.10 * math.sin(7 * a + 0.4))
    def edge(a):                                             # where the ray from the impact point leaves the wall outline
        c, s_ = math.cos(a), math.sin(a); ts = []
        if abs(c) > 1e-6:
            ts.append((hw if c > 0 else -hw) / c)
        if abs(s_) > 1e-6:
            ts.append(((C.WALL_H - Z) if s_ > 0 else (-0.1 - Z)) / s_)
        return min(t for t in ts if t > 0)
    for k in range(n):
        a0, a1 = k * math.tau / n, (k + 1) * math.tau / n
        quad = [(rim(a0), a0), (edge(a0), a0), (edge(a1), a1), (rim(a1), a1)]
        vs = [bm.verts.new((x, r * math.cos(a), Z + r * math.sin(a))) for x in (0.0, T) for r, a in quad]
        for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            bm.faces.new([vs[i] for i in f])
    me = bpy.data.meshes.new("E_wall"); bm.to_mesh(me); bm.free()
    wall = bpy.data.objects.new("E_wall", me); bpy.context.scene.collection.objects.link(wall)
    m = wall.modifiers.new("Fluid", 'FLUID'); m.fluid_type = 'EFFECTOR'; m.effector_settings.effector_type = 'COLLISION'
    m.effector_settings.surface_distance = 0.0
    core = ico("E_core", 0.36, (-0.30, 0, Z), rough=0.4)
    flow(core, 'BOTH', 1, 2, dens=2.2, temp=2.2, fuel=0.8, color=(0.15, 0.14, 0.13), vn=20.0, vinit=(-12, 0, 3.0))
    soot = ico("E_soot", 0.44, (-0.34, 0, Z), rough=0.45)
    flow(soot, 'SMOKE', 2, 8, dens=2.6, temp=0.9, color=(0.30, 0.25, 0.21), vn=12.0, vinit=(-9, 0, 3.5))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.52, minor_radius=0.15, major_segments=40, minor_segments=10, location=(-0.17, 0, Z),
                                     rotation=(0, math.pi / 2, 0))
    ring = bpy.context.active_object; ring.name = "E_ring"
    for v in ring.data.vertices:
        a = math.atan2(v.co.y, v.co.x); k = 1.0 + 0.30 * math.sin(a * 5 + 1.3) + 0.2 * math.sin(a * 11)
        v.co.x *= k; v.co.y *= k
    flow(ring, 'SMOKE', 1, 7, dens=2.3, temp=0.3, color=BRICK[0], vn=17.0, vinit=(-2.5, 0, 1.5))
    # out of the back: a short burst of flame, the jet of pulverised brick, then the slower spall cloud
    burst = ico("E_burst", 0.16, (T + 0.22, 0, Z), rough=0.3)
    flow(burst, 'BOTH', 1, 2, dens=1.8, temp=2.0, fuel=0.5, color=(0.2, 0.17, 0.15), vn=8.0, vinit=(26, 0, 1.0))
    jet("E_backjet", (T + 0.15, 0, Z), (1, 0, 0.03), 46.0, 8.0, 15, 0.27, BRICK[0], dens=2.5, zmin=0.3)
    spall = ico("E_spall", 0.42, (T + 0.34, 0, Z), rough=0.45)
    flow(spall, 'SMOKE', 2, 9, dens=2.4, temp=0.5, color=BRICK[1], vn=7.0, vinit=(13, 0, 2.0))
    for i in range(13):
        jet("E_jb%02d" % i, (T + 0.15, 0, Z), cone_dir(1, 42, 0.08), random.uniform(16, 34), random.uniform(5, 9), random.randint(9, 20),
            random.uniform(0.09, 0.17), random.choice(BRICK))
    for i in range(9):
        jet("E_jf%02d" % i, (-0.15, 0, Z), cone_dir(-1, 72, 0.15), random.uniform(12, 26), random.uniform(5, 9), random.randint(9, 18),
            random.uniform(0.09, 0.16), random.choice(BRICK + [(0.3, 0.26, 0.22)]))

def build_launch():
    A = Vector(C.AIM); B = Vector(C.BREECH); M = Vector(C.MUZZLE)
    flash = ico("E_flash", 0.15, B - A * 0.22, rough=0.3)
    flow(flash, 'BOTH', 1, 3, dens=1.3, temp=2.0, fuel=0.7, color=(0.55, 0.54, 0.52), vn=7.0, vinit=-A * 62)
    smoke = ico("E_smoke", 0.20, B - A * 0.45, rough=0.35)
    flow(smoke, 'SMOKE', 2, 11, dens=2.8, temp=0.55, color=(0.66, 0.64, 0.60), vn=5.0, vinit=-A * 36)
    mf = ico("E_mflash", 0.07, M + A * 0.22, rough=0.3)
    flow(mf, 'BOTH', 1, 1, dens=0.9, temp=1.6, fuel=0.4, color=(0.6, 0.59, 0.57), vn=6.0, vinit=A * 20)
    ms = ico("E_msmoke", 0.13, M + A * 0.30, rough=0.3)
    flow(ms, 'SMOKE', 2, 7, dens=1.5, temp=0.4, color=(0.68, 0.66, 0.62), vn=4.0, vinit=A * 9)
    # dust torn off the ground behind the shooter by the backblast
    gd = ico("E_gdust", 1.0, (C.SHOOT_X - 3.4, 0, 0.10), rough=0.3, scale=(1.9, 0.75, 0.07))
    flow(gd, 'SMOKE', 5, 18, dens=1.3, temp=0.2, color=(0.56, 0.46, 0.33), vn=2.0, vinit=(-7, 0, 1.6))
    for i in range(9):
        d = (-1.0, random.uniform(-0.45, 0.45), random.uniform(-0.12, 0.22))
        jet("E_jl%02d" % i, tuple(B - A * 0.6), d, random.uniform(22, 40), random.uniform(5, 8), random.randint(10, 20), random.uniform(0.10, 0.17),
            random.choice([(0.64, 0.62, 0.58), (0.58, 0.52, 0.44), (0.56, 0.46, 0.33)]), start=2, dens=1.4, zmin=0.12)

if __name__ == "__main__":
    kind, cache_dir, res, frames = sys.argv[1], os.path.abspath(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    noise = len(sys.argv) > 5 and sys.argv[5] == "1"
    random.seed(11 if kind == "impact" else 23)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dom = make_domain(kind, cache_dir, res, frames, noise)
    (build_impact if kind == "impact" else build_launch)()
    os.makedirs(cache_dir, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(cache_dir, "sim.blend"))
    bpy.context.view_layer.objects.active = dom
    import time; t0 = time.time()
    with bpy.context.temp_override(object=dom, active_object=dom, selected_objects=[dom]):
        bpy.ops.fluid.bake_all()
    print("BAKE DONE %.1fs" % (time.time() - t0))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(cache_dir, "sim.blend"))
    open(os.path.join(cache_dir, "DONE"), "w").write("ok")
    sys.stdout.flush(); os._exit(0)
