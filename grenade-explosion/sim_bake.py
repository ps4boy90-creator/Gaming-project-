"""Bake the grenade detonation as a Mantaflow gas sim (fire + smoke + dust) to an OpenVDB cache.

usage: python3 sim_bake.py <cache_dir> <resolution> <frames> [noise 0|1]

Master timeline: 1 frame = 1/120 s of real time (scene fps 24 * time_scale 0.2),
so playing it 1:1 at 24 fps is 5x slow motion. Detonation is at frame DET.
"""
import bpy, sys, math, random, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import manta_fix  # noqa: F401  (repairs Mantaflow class inheritance in pip bpy)
from mathutils import Vector

DET = 1                     # sim-local frame of detonation
DOMAIN_SIZE = (11.0, 11.0, 7.0)
DOMAIN_Z0 = -0.12           # bottom of the domain (just under the ground plane)
TIME_SCALE = 0.2

def build(cache_dir, res, frames, noise=False, seed=7):
    random.seed(seed)
    sc = bpy.context.scene
    sc.render.fps = 24
    sc.frame_start, sc.frame_end = 1, frames
    col = bpy.data.collections.new("SIM"); sc.collection.children.link(col)

    def add(ob):
        col.objects.link(ob); return ob

    # ---- domain
    bpy.ops.mesh.primitive_cube_add(size=1)
    dom = bpy.context.active_object; dom.name = "BlastDomain"
    dom.scale = DOMAIN_SIZE
    dom.location = (0, 0, DOMAIN_Z0 + DOMAIN_SIZE[2] / 2)
    m = dom.modifiers.new("Fluid", 'FLUID'); m.fluid_type = 'DOMAIN'
    d = m.domain_settings
    d.domain_type = 'GAS'
    d.resolution_max = res
    d.time_scale = TIME_SCALE
    d.use_adaptive_timesteps = True
    d.cfl_condition = 4.0
    d.timesteps_max = 8; d.timesteps_min = 1
    d.use_collision_border_bottom = True
    for k in ("front", "back", "left", "right", "top"):
        setattr(d, "use_collision_border_" + k, False)
    d.alpha = -0.22         # density buoyancy (dust is heavy: it settles)
    d.beta = 1.5            # heat buoyancy
    d.vorticity = 0.35
    d.use_dissolve_smoke = False
    d.dissolve_speed = 150
    d.use_dissolve_smoke_log = True
    d.burning_rate = 3.2    # HE: fuel is consumed almost instantly
    d.flame_smoke = 2.4
    d.flame_vorticity = 0.6
    d.flame_ignition = 1.5
    d.flame_max_temp = 3.2
    d.flame_smoke_color = (0.13, 0.12, 0.11)
    d.use_noise = bool(noise)
    if noise:
        d.noise_scale = 2
        d.noise_strength = 1.4
        d.noise_pos_scale = 2.5
        d.noise_time_anim = 0.15
    d.cache_type = 'ALL'
    d.cache_data_format = 'OPENVDB'
    d.openvdb_cache_compress_type = 'ZIP'
    d.cache_directory = cache_dir
    d.cache_frame_start = 1
    d.cache_frame_end = frames
    d.cache_resumable = False

    def flow(ob, kind, on, off, dens=1.0, temp=1.0, fuel=0.0, color=None, vn=0.0, vfac=0.0, vinit=None, sub=2):
        m = ob.modifiers.new("Fluid", 'FLUID'); m.fluid_type = 'FLOW'
        f = m.flow_settings
        f.flow_type = kind; f.flow_behavior = 'INFLOW'
        f.flow_source = 'MESH'
        f.density = dens; f.temperature = temp
        if kind in ('FIRE', 'BOTH'):
            f.fuel_amount = fuel
        if color:
            f.use_absolute = False
            f.smoke_color = color
        f.surface_distance = 0.6
        f.volume_density = 1.0
        f.subframes = sub
        f.use_initial_velocity = True
        f.velocity_normal = vn
        f.velocity_factor = vfac
        if vinit:
            f.velocity_coord = vinit
        for fr, val in ((on - 1, False), (on, True), (off, True), (off + 1, False)):
            f.use_inflow = val
            f.keyframe_insert("use_inflow", frame=fr)
        return f

    def ico(name, r, loc, sub=3, rough=0.0):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=loc)
        ob = bpy.context.active_object; ob.name = name
        if rough:
            for v in ob.data.vertices:
                v.co *= 1.0 + random.uniform(-rough, rough)
        return ob

    # ---- 1. fireball core: tiny, violent, burns out in a few frames
    core = ico("E_core", 0.42, (0, 0, 0.34), rough=0.4)
    flow(core, 'BOTH', DET, DET + 1, dens=2.0, temp=2.2, fuel=1.05, color=(0.15, 0.14, 0.13), vn=14.0, vinit=(0, 0, 4.0))
    # ---- 1b. main dust / soot mass thrown up behind the flash
    dust = ico("E_dust", 0.50, (0, 0, 0.32), rough=0.45)
    flow(dust, 'SMOKE', DET + 1, DET + 7, dens=2.6, temp=0.9, color=(0.36, 0.31, 0.25), vn=9.0, vinit=(0, 0, 5.0))

    # ---- 2. ground dust skirt: ring that shoots outward along the ground
    bpy.ops.mesh.primitive_torus_add(major_radius=0.62, minor_radius=0.22, major_segments=40, minor_segments=10,
                                     location=(0, 0, 0.16))
    ring = bpy.context.active_object; ring.name = "E_ring"
    for v in ring.data.vertices:
        a = math.atan2(v.co.y, v.co.x)
        v.co.x *= 1.0 + 0.30 * math.sin(a * 5 + 1.3) + 0.2 * math.sin(a * 11)
        v.co.y *= 1.0 + 0.30 * math.sin(a * 5 + 1.3) + 0.2 * math.sin(a * 11)
    flow(ring, 'SMOKE', DET, DET + 7, dens=2.4, temp=0.35, color=(0.56, 0.46, 0.33), vn=15.0, vinit=(0, 0, 2.5))

    # ---- 3. dirt jets: small emitters thrown outward on ballistic paths, leaving dust trails
    njet = 22
    for i in range(njet):
        az = (i + random.uniform(-0.4, 0.4)) / njet * math.tau
        el = math.radians(random.choice([random.uniform(8, 30), random.uniform(30, 62), random.uniform(62, 85)]))
        speed = random.uniform(16, 34)          # m/s initial
        r = random.uniform(0.10, 0.19)
        e = ico("E_jet%02d" % i, r, (0, 0, 0.15), sub=1)
        dirv = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)))
        life = random.randint(9, 20)
        k = random.uniform(5.0, 9.0)            # drag (1/s) -> clods decelerate hard
        dt = TIME_SCALE / 24.0
        for fr in range(DET, DET + life + 2):
            t = (fr - DET) * dt
            s = speed / k * (1 - math.exp(-k * t))      # distance travelled with drag
            p = Vector((0, 0, 0.15)) + dirv * s + Vector((0, 0, -0.5 * 9.81 * t * t))
            p.z = max(p.z, 0.08)
            e.location = p
            e.keyframe_insert("location", frame=fr)
            sc_ = max(0.25, 1.0 - 0.6 * (fr - DET) / life)
            e.scale = (sc_, sc_, sc_); e.keyframe_insert("scale", frame=fr)
        flow(e, 'SMOKE', DET, DET + life, dens=1.6, temp=0.2,
             color=random.choice([(0.54, 0.44, 0.32), (0.44, 0.36, 0.27), (0.30, 0.26, 0.21)]),
             vn=1.5, vfac=0.55, sub=3)
    return dom, d

if __name__ == "__main__":
    args = sys.argv[1:]
    cache_dir = os.path.abspath(args[0]); res = int(args[1]); frames = int(args[2])
    noise = len(args) > 3 and args[3] == "1"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    dom, d = build(cache_dir, res, frames, noise)
    os.makedirs(cache_dir, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(cache_dir, "sim.blend"))
    bpy.context.view_layer.objects.active = dom
    import time; t0 = time.time()
    with bpy.context.temp_override(object=dom, active_object=dom, selected_objects=[dom]):
        bpy.ops.fluid.bake_all()
    print("BAKE DONE %.1fs" % (time.time() - t0))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(cache_dir, "sim.blend"))
    open(os.path.join(cache_dir, "DONE"), "w").write("ok")
    sys.stdout.flush(); os._exit(0)      # skip Mantaflow teardown (aborts in module builds)
