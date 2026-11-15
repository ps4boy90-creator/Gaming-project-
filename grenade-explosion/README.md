# Explosion Comparison · 01 — M67 fragmentation grenade

A ~20 s, 1080p "explosion comparison" segment built entirely in code with Blender
(Cycles) — no stock footage, no downloaded 3D assets, no generated video. A transparent
glass-silhouette figure throws an M67; the camera follows the grenade through the air,
watches it land and settle, replays the detonation in slow motion, and finishes on a
top-down view of the 5 m kill radius and 15 m casualty radius.

| # | Shot | What the camera does | Speed |
|---|------|----------------------|-------|
| 1 | `card`   | Studio turntable of the grenade + spec panel | — |
| 2 | `throw`  | Three-quarter rear view of the silhouette thrower in a sandbag pit | ~0.75× |
| 3 | `follow` | Flies alongside the grenade, close up, through landing and first bounce (motion-blurred background) | ~0.6× |
| 4 | `macro`  | Ground-level beauty shot: grenade rolls past the lens and settles; fuze countdown runs out → white flash | real time |
| 5 | `blast`  | Low wide shot of the detonation: fireball, dirt jets, debris, dust cloud | 5× → 2.5× slow motion |
| 6 | `top`    | Straight down: tight on the 5 m ring for the blast, pull-back reveals the 15 m ring | 2.5× slow motion |

## What is in the scene

- **Grenade** (`grenade.py`) — own model from public dimensions: 63.5 mm sphere body with
  seam, fuze, safety lever, pull ring, stencilled markings. The lever flies off at release.
- **Thrower** (`figure.py`) — a procedural mannequin rebuilt every frame from key poses
  (2-bone IK limbs, lofted tubes fused by a voxel remesh) and shaded as refractive glass
  with a fresnel rim, so it reads as a person without pulling focus.
- **Range** (`env.py`) — physical sky + sun, procedural cloud deck, cracked dirt, ~15k dry
  grass tufts, stones, sandbag throwing pit, crates, drums, fence, tree line, hills.
- **Detonation** (`sim_bake.py`, `smoke_mat.py`) — Mantaflow gas sim (128³ + wavelet
  up-res): a fuel core that burns out in a few frames, a ground dust skirt, and ~22
  ballistic "dirt jet" emitters that give the spiky high-explosive silhouette.
- **Extras** (`fx.py`) — analytic dirt clods and glowing fragments (drag + gravity,
  stretched along velocity as cheap motion blur), flash light, landing dust puffs, scorch
  mark + crater, and the emissive radius rings that sit *in* the scene.
- **Finishing** (`post.py`) — 1080p master, title card, fuze countdown / callouts, grade,
  grain, and a fully synthesized soundtrack (numpy: boom, debris, whooshes, ambience).

## Timeline facts used on screen

M67: 63.5 mm steel body, 400 g, 180 g Composition B, M213 fuze with a 4–5.5 s delay,
5 m kill radius, 15 m casualty radius, fragments out to ~230 m, average throw 30–35 m,
in service since 1968 (US Army TC 3-23.30 / FM 3-23.30). In the animation the throw
lands at 26 m, rolls to rest at ~31 m and the fuze fires 4.39 s after release.

## Rebuilding

```bash
pip install bpy numpy pillow          # Blender 5.3 as a Python module (Cycles, CPU)
./render_all.sh <frames_dir> <sim_cache_dir> out.mp4
```

`render_all.sh` bakes the sim if needed (~18 min on 4 cores), renders every shot
(resumable — existing frames are skipped) and runs `post.py`. Single shots / frames:

```bash
python3 shots.py blast <frames_dir>/blast --sim <sim_cache_dir> --res 1280x720 --frames 0-87
python3 shots.py follow <frames_dir>/follow --res 640x360 --spp 8 --frames 10,40,80   # quick look
python3 post.py <frames_dir> out.mp4
```

Frames are rendered at 1280×720 (8–16 samples + OpenImageDenoise) and mastered to
1920×1080; on a 4-vCPU machine the full render is about 3 hours. Pass `--res 1920x1080`
for a native 1080p render if you have the CPU time.

`manta_fix.py` works around a bug in the pip `bpy` module where the embedded Mantaflow
classes lose their base-class links (every fluid bake aborts with
`'LevelsetGrid' object has no attribute 'setConst'`); it re-links the types at import.

## Adding the next explosion

Each shot is a small function in `shots.py` that maps an output frame to a time and a
camera; `Stage.set_time()` places everything. For a new device: add a model module,
adjust the emitters in `sim_bake.py` (scale, fuel, jets), change the ring radii in
`fx.Rings.SPEC` and the card text in `post.py`.

Fonts: Anton, Barlow Condensed, Saira Stencil One (SIL OFL, licences in `assets/`).
