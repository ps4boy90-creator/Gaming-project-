"""Bake the two Mantaflow gas sims of the 120 mm mortar segment to OpenVDB caches.

  python3 msim.py launch|impact <cache_dir> <resolution> <frames> [noise 0|1]

launch : muzzle flash and smoke jet up the line of the bore, the side ring at the muzzle and the dust
         blown off the ground round the baseplate (frame 1 = the round fires)
impact : point-detonating HE burst on dry ground - short fireball, dark smoke, the dirt skirt and ejecta
         jets, pale dust knocked off the ruin walls by the fragments (frame 1 = detonation)
Master timeline: 1 frame = 1/120 s (scene fps 24 * time_scale 0.2).
"""
import bpy, sys, math, random, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "grenade-explosion")); sys.path.insert(0, HERE)
import manta_fix  # noqa: F401
from mathutils import Vector
import mconst as C

TIME_SCALE = 0.2
DT = TIME_SCALE / 24.0
DOMAINS = {"launch": ((10.0, 8.0, 9.5), (C.MX + 1.9, 0.0)), "impact": ((28.0, 28.0, 20.0), (0.8, 1.0))}
DIRT = [(0.40, 0.31, 0.22), (0.33, 0.26, 0.19), (0.46, 0.38, 0.28)]
DARK = [(0.11, 0.105, 0.10), (0.16, 0.15, 0.14), (0.22, 0.20, 0.18)]

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
    d.alpha = -0.14; d.beta = 1.3; d.vorticity = 0.45
    d.use_dissolve_smoke = False
    d.burning_rate = 4.5 if kind == "impact" else 3.6; d.flame_smoke = 2.4; d.flame_vorticity = 0.6; d.flame_ignition = 1.5; d.flame_max_temp = 3.2
    d.flame_smoke_color = (0.10, 0.095, 0.09) if kind == "impact" else (0.52, 0.51, 0.49)
    d.use_noise = bool(noise)
    if noise:
        d.noise_scale = 2; d.noise_strength = 1.3; d.noise_pos_scale = 2.5; d.noise_time_anim = 0.15
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

def torus(name, R, r, loc, rot=(0, 0, 0), lobes=0.25):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=40, minor_segments=10, location=tuple(loc), rotation=rot)
    ob = bpy.context.active_object; ob.name = name
    for v in ob.data.vertices:
        a = math.atan2(v.co.y, v.co.x); k = 1.0 + lobes * math.sin(a * 5 + 1.3) + 0.6 * lobes * math.sin(a * 11)
        v.co.x *= k; v.co.y *= k
    return ob

def box(name, lo, hi):
    bpy.ops.mesh.primitive_cube_add(size=1, location=[(a + b) / 2 for a, b in zip(lo, hi)])
    ob = bpy.context.active_object; ob.name = name; ob.scale = [abs(b - a) for a, b in zip(lo, hi)]
    return ob

def collider(ob):
    m = ob.modifiers.new("Fluid", 'FLUID'); m.fluid_type = 'EFFECTOR'; m.effector_settings.effector_type = 'COLLISION'; m.effector_settings.surface_distance = 0.0

def jet(name, origin, dirv, speed, drag, life, r, color, start=1, dens=1.6, zmin=0.12, temp=0.2):
    """Small emitter thrown along a ballistic path with drag; leaves a trail of dirt / smoke."""
    e = ico(name, r, origin, sub=1); dirv = Vector(dirv).normalized(); o = Vector(origin)
    for fr in range(start, start + life + 2):
        t = (fr - start) * DT
        p = o + dirv * (speed / drag * (1 - math.exp(-drag * t))) + Vector((0, 0, -0.5 * 9.81 * t * t)); p.z = max(p.z, zmin)
        e.location = p; e.keyframe_insert("location", frame=fr)
        s = max(0.25, 1.0 - 0.6 * (fr - start) / life); e.scale = (s, s, s); e.keyframe_insert("scale", frame=fr)
    flow(e, 'SMOKE', start, start + life, dens=dens, temp=temp, color=color, vn=1.5, vfac=0.55, sub=3)

def build_impact():
    # standing masonry near the burst deflects the cloud: the near wall (either side of its gap) and the house front
    collider(box("E_wallL", (-1.85, 2.58, -0.1), (-1.00, 2.82, 1.7))); collider(box("E_wallR", (1.05, 2.58, -0.1), (1.65, 2.82, 1.4)))
    collider(box("E_houseA", (-2.15, 4.35, -0.1), (3.5, 4.65, 3.0))); collider(box("E_houseA2", (4.7, 4.35, -0.1), (7.15, 4.65, 1.8)))
    collider(box("E_houseL", (-2.15, 4.35, -0.1), (-1.85, 10.6, 3.6)))
    core = ico("E_core", 0.85, (0, 0, 0.55), rough=0.4)
    flow(core, 'BOTH', 1, 2, dens=2.4, temp=2.3, fuel=0.9, color=DARK[0], vn=24.0, vinit=(1.5, 0, 9.0))
    soot = ico("E_soot", 1.30, (0, 0, 0.85), rough=0.45)
    flow(soot, 'SMOKE', 2, 7, dens=3.6, temp=1.0, color=DARK[0], vn=13.0, vinit=(1.0, 0, 11.0))
    column = ico("E_column", 0.75, (0, 0, 1.2), rough=0.35)
    flow(column, 'SMOKE', 4, 14, dens=2.8, temp=1.3, color=DARK[1], vn=4.0, vinit=(0.5, 0, 9.0))
    skirt = torus("E_skirt", 1.7, 0.42, (0, 0, 0.30), lobes=0.30)
    flow(skirt, 'SMOKE', 1, 5, dens=1.9, temp=0.25, color=DIRT[1], vn=19.0, vinit=(0, 0, 2.0))
    sheet = ico("E_sheet", 1.0, (0, 0, 0.12), rough=0.25, scale=(5.0, 5.0, 0.07))
    flow(sheet, 'SMOKE', 3, 7, dens=0.75, temp=0.15, color=DIRT[2], vn=1.5, vinit=(0, 0, 2.2))
    for i in range(30):                                         # ejecta: dirt thrown up and out
        az = random.uniform(0, math.tau); el = math.radians(random.uniform(14, 82))
        d = (math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))
        jet("E_j%02d" % i, (0.4 * d[0], 0.4 * d[1], 0.35), d, random.uniform(22, 52), random.uniform(3.2, 6.0), random.randint(14, 34),
            random.uniform(0.24, 0.44), random.choice(DIRT + DARK + DARK[:2]), dens=2.0)
    # dust and pulverised brick thrown out behind the near wall where the blast breaks through it
    wd = ico("E_walldust", 0.55, (-0.1, 3.05, 0.9), rough=0.4, scale=(1.6, 0.5, 1.0))
    flow(wd, 'SMOKE', 2, 6, dens=1.8, temp=0.15, color=(0.50, 0.40, 0.32), vn=3.0, vinit=(0, 7.0, 2.0))

def build_launch():
    A = Vector(C.BORE); M = Vector(C.MUZZLE)
    flash = ico("E_mflash", 0.15, M + A * 0.30, rough=0.3)
    flow(flash, 'BOTH', 1, 2, dens=1.2, temp=2.0, fuel=0.85, color=(0.55, 0.54, 0.52), vn=9.0, vinit=A * 52)
    smoke = ico("E_msmoke", 0.21, M + A * 0.45, rough=0.35)
    flow(smoke, 'SMOKE', 2, 9, dens=2.3, temp=0.6, color=(0.62, 0.61, 0.58), vn=6.0, vinit=A * 24)
    q = A.to_track_quat('Z', 'Y').to_euler()
    ring = torus("E_mring", 0.20, 0.075, M + A * 0.05, rot=q, lobes=0.15)
    flow(ring, 'SMOKE', 1, 3, dens=1.5, temp=0.4, color=(0.66, 0.65, 0.62), vn=11.0, vinit=A * 4)
    dust = torus("E_gring", 0.75, 0.13, (C.MX, 0, 0.10), lobes=0.25)
    flow(dust, 'SMOKE', 2, 6, dens=1.5, temp=0.2, color=DIRT[2], vn=6.0, vinit=(0, 0, 1.4))
    sheet = ico("E_gsheet", 1.0, (C.MX + 0.4, 0, 0.10), rough=0.25, scale=(2.4, 2.2, 0.06))
    flow(sheet, 'SMOKE', 3, 8, dens=0.6, temp=0.15, color=DIRT[0], vn=1.0, vinit=(0, 0, 1.2))

if __name__ == "__main__":
    kind, cache_dir, res, frames = sys.argv[1], os.path.abspath(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    noise = len(sys.argv) > 5 and sys.argv[5] == "1"
    random.seed(17 if kind == "impact" else 29)
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
