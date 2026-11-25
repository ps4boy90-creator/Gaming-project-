# Explosion Comparison · 11 — BLU-82 "Daisy Cutter" from a C-130 on to dense jungle

Eleventh segment of the series. A C-130 Hercules, 1,830 m (6,000 ft) above rain forest, has its ramp down
and an extraction parachute already trailing. The loadmaster frees the locks; the parachute pulls a
15,000 lb BLU-82/B out of the hold on its wooden cradle and airdrop platform. Clear of the ramp the
webbing is cut, the bomb leaves the cradle and its own stabilising parachute opens. It falls for 26
seconds, nearly upright, and its nose fuze, on a 0.97 m extender, touches the ground first: the bomb
bursts above the ground, the blast spreads sideways through the trees, and a circle of forest about 79 m
(260 ft) across is gone, with almost no crater. That is what the bomb was built for in 1970: an instant
helicopter landing zone. Everything is procedural (Blender as a Python module, Cycles) and shares render
setup, effects and post tools with the earlier segments. Nobody is modelled anywhere; the forest is empty.

**Status: not rendered at full quality yet.** The code is complete and has been checked end to end with a
low-resolution draft rendered on a CPU; the 1080p render on a GPU is still to do, so there is no
`renders/` folder here yet.

| # | Shot | What it shows | Speed |
|---|------|---------------|-------|
| 1 | `card`     | The bomb on its cradle and platform, + spec panel | – |
| 2 | `approach` | The C-130 on its run-in: ramp down, extraction parachute out | real time |
| 3 | `intro`    | The bomb whole, and cut open: 6 mm wall, filling, booster, fuze extender | – |
| 4 | `release`  | The load runs out along the rollers and off the ramp; the bomb leaves its cradle; its parachute fills | real time, then half speed |
| 5 | `fall`     | Beside the bomb through its last 3.5 s above the canopy | real time |
| 6 | `strike`   | From the air, 300 m off: the burst, the cloud | 1.7× slow, then 1.2× fast |
| 7 | `cutaway`  | The forest cut through the burst point, seen square on: the fuze touches, the blast front, the trees going down | 10× slow, then 5× |
| 8 | `after`    | A minute later, circling the clearing, with its measured ring | real time |
| 9 | summary    | What the bomb does, in a table (made in post) | – |

## The numbers in the film

**Published** (National Museum of the USAF; Air Force Armament Museum; *Air & Space Forces Magazine*,
"Herculean Bombers", 2016; AFI 11-231; USAF news release on the last drop, 2008):

| | |
|---|---|
| Weight | 15,000 lb (6,800 kg), of which 12,600 lb (5,700 kg) is slurry explosive |
| Size | 141.6 in (3.60 m) long, 54 in (1.37 m) across (some lists give 56 in) |
| Case | a tank of 1/4-inch (6 mm) steel plate |
| Fuze | a nose fuze on an extender (36 in extender, 38 in to the tip): the burst is above the ground |
| Delivery | cargo extraction from a C-130, 6,000 ft above the ground or more; a 15 ft extraction parachute, deployed before the release; webbing cut by blades on static lines as the load leaves; a stabilising parachute on the bomb |
| Fall | 26 seconds for 6,000 ft |
| Result | a clearing about 260 ft (79 m) across, for one to three UH-1s; trees up to 4 ft thick and 150 ft tall; almost no debris at the edge |
| Crater | a dish 20 to 30 ft across and 6 to 12 in deep (1969 test, Tonopah) |
| Pressure | about 1,000 lb per square inch near the centre |
| History | 225 built; first used 23 March 1970; Vietnam ("Commando Vault"), Gulf 1991, Afghanistan 2001; last one dropped 15 July 2008 |

**Worked out here from those figures** (`dconst.py`): the extraction parachute pulls the 7.3 t load along
the floor at about 3.6 m/s², so it leaves the ramp 2.2 s after release at 8 m/s relative to the aircraft.
For the fall to take the published 26 s the stabilising parachute needs a drag area of about 11.5 m²,
which for a ribbon canopy means about 4.9 m across; the bomb then arrives at about **96 m/s (345 km/h),
85° from level**, having travelled about 860 m forward.

**Assumed or estimated**: the release speed (77 m/s true, about 140 knots indicated, a usual speed for a
heavy drop); the platform (12 ft by 108 in) and the shape of the cradle and webbing; the cut and size of
both parachutes; the cone of the bomb's nose and the look of its rear end; the inside of the bomb in the
cut-open view (a diagram: wall, filling, a booster behind the nose); everything about the forest.

**Staging, not measurement**: how fast the blast front travels (`dconst.t_front`), how the trees go down
and how long that takes, the radii of the zones other than the clearing itself (trees broken up
altogether within 16 m, stripped and leaning out to 75 m, shaken out to 260 m), the size and brightness of
the fireball and the cloud. In the section the dust is drawn thinner than in the view from the air so
that the trees can be seen. The trees are not part of the gas simulation.

**The aircraft.** A C-130E in the three-colour camouflage of the tactical airlift wings in South-East
Asia. Overall sizes are published (29.79 m long, 40.41 m span, 11.66 m high, propellers 4.11 m,
tailplane 16.05 m, hold 3.02 m wide and 2.74 m high, ramp 3.1 m); section shapes and the stations of
wing, tail and engines are estimated from photographs and three-view drawings. No markings, no crew,
landing gear up. The Commando Vault drops of 1970 were flown mostly by C-130Bs of the 463rd Tactical
Airlift Wing, which look the same but for the E model's underwing tanks; later drops were made from
C-130Es and, after the war, MC-130Es.

**"Daisy cutter"** was first the name of the fuze extender, on any bomb; in Vietnam it became the name of
this bomb. It is not a fuel-air bomb: the explosive carries its own oxidiser.

## Sound

Recorded effects from the Epidemic Sound catalogue (reached through Higgsfield): a propeller aircraft
(played lower, for four big turboprops), cargo rollers, a metal latch, cloth filling in the wind, rushing
air, a rain forest, a large explosion with a long tail, trees cracking and falling, debris, and a low
tonal bed under the title and the tables. They are licensed, not ours to redistribute, so they are **not
in the repository**; `dpost.py` lists the catalogue titles (`SFX`) and looks for 48 kHz stereo WAV files
with those names in `sfx/` here or in `$SFX_DIR`. Without them it falls back to a plain synthesized
track. Nobody has listened to the mix on loudspeakers; it has only been measured.

## Files

- `dconst.py` – published numbers, the slide along the floor, the fall, the staging of the blast
- `dbomb.py` – the bomb, whole and cut open; cradle, platform and webbing; the parachutes
- `dc130.py` – the C-130E
- `djungle.py` – the forest, the ground, what the burst does to the trees, the forest from the air
- `dsim.py` – the two Mantaflow bakes (`out` for the view from the air, `sec` for the section)
- `dshots.py` – the sets, the cameras, the renderer
- `dpost.py` – captions, drawings, closing table, sound, encode
- `dlook.py` – model check renders
- `render_all.py` – bakes, renders every shot and builds the video

## Running it

```bash
pip install bpy numpy pillow scipy
```

```bash
python render_all.py frames sims c130_blu82.mp4
```

A quick draft on a CPU (about an hour on four cores):

```bash
VOL_STEP=3 NO_PLUMES=1 python render_all.py frames sims draft.mp4 --res 640x360 --spp 5 --bake out:96:300,sec:96:260
```

Set `RENDER_DEVICE=GPU` to render with Cycles on a graphics card. Frames and simulation caches are not
kept in the repository.
