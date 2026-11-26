# Explosion Comparison · 13 — GBU-43/B MOAB from an MC-130 over a mountain valley

Thirteenth segment of the series. An MC-130 Hercules, ramp open, lets out a parachute that drags a platform
with a 9.2 m bomb on a cradle back along the cargo floor and off the ramp. The GBU-43/B "Massive Ordnance
Air Blast" is freed from its cradle at once, swings out four lattice fins and falls for 33 seconds, guided,
into a dry mountain valley, where it bursts about two metres above the ground. The film shows the burst
from a slope 650 m off, then again from high above with the calculated pressure of the blast drawn on the
ground, then the valley a minute later. Everything is procedural (Blender as a Python module, Cycles).
The aircraft, the parachute and the way the shots and the post-production are built come from segment 11
(BLU-82 from a C-130); the bomb, its cradle, the valley and the blast calculation are new. Nobody is
modelled anywhere.

**Rendered** on 26 November 2026 on a rented Runpod pod (one NVIDIA RTX PRO 4500 Blackwell, Cycles with OptiX;
the simulation baked on the pod's CPU): frames at 1280 × 720, finished at 1920 × 1080. The pod existed for
83 minutes, about 1.00 US dollar at 0.72 dollars an hour. That includes three bakes of the blast: the first,
at a finer grid, was far too slow and was stopped; the second showed the dust behind the blast front as
hard-edged flat discs, and those sources were taken out. The film (mc130_moab.mp4, 55 s) and stills from it
are in `renders/`.

**Known flaws.** The simulation's cells are 2.8 m, so the cloud is coarse close up. The thin dust that a
blast front raises from dry ground as it passes is not shown (only the dust thrown out from the burst).
The fireball is pale. The country seen from the aircraft is nearly featureless. Nobody has listened to the
sound on loudspeakers.

**The valley, its buildings and this drop are invented. The blast distances are calculated, not measured.**

| # | Shot | What it shows | Speed |
|---|------|---------------|-------|
| 1 | `card`     | The bomb on its cradle, fins folded, + spec panel | – |
| 2 | `approach` | The MC-130 on its run-in; the parachute is let out | real time |
| 3 | `intro`    | The bomb with its fins out, and cut open (a diagram) | – |
| 4 | `release`  | The load is pulled out; the bomb leaves its cradle; the fins open | real time, then half speed |
| 5 | `fall`     | Riding down behind the bomb through its last 3.5 s | real time |
| 6 | `strike`   | From the southern slope: the burst, the dust, the cloud | 1.7× slow, then 1.8× fast |
| 7 | `reach`    | The same burst from above, with the blast front and the 10, 5, 2 and 1 psi lines drawn on the ground | 1.7× slow, then 1.2× fast |
| 8 | `after`    | A minute later, circling | real time |
| 9 | summary    | The numbers (made in post) | – |

## The numbers in the film

**Published** (Air Force Armament Museum; Air & Space Forces Magazine; af.mil; the Air Force's 2003 legal
review of the weapon; Wikipedia for the exact length): 21,600 lb (9,800 kg); 30 ft 1.75 in (9.19 m) long,
40.5 in (1.03 m) across, 5 ft wide with the fins folded and 10 ft with them out; 18,700 lb (8,500 kg) of H6
in a thin aluminium case (the BLU-120/B warhead; the case weighs about 2,900 lb); GPS and inertial guidance
(KMU-593/B) working four lattice fins, with fixed wings on the body; carried on a cradle on an airdrop
platform in an MC-130 or C-130, pulled out by a drogue parachute, freed from the cradle at once and then
falling without a parachute; guided over about 3 nautical miles. Yield about 11 tons of TNT. Fifteen built.
Used once: at 7.32 pm local time on 13 April 2017, on a tunnel complex of the Islamic State's Khorasan
branch at the mouth of the Mamand valley, Achin district, Nangarhar, Afghanistan.

**Reported, not official:** that it bursts about 6 ft above the ground (the film uses this).

**What the 2017 strike left** (satellite pictures analysed by Alcis, published by Defense Update; Reuters
photographs from the site): about twenty compounds and the trees round them destroyed in the immediate
area, buildings further out standing, hardly any crater, and leaves still on trees within a few hundred
feet. The Air Force published no damage assessment, and what happened inside the tunnels is not public.

**The blast (calculated).** Peak overpressure from Kinney and Graham's fit for a TNT charge, for 11,000 kg,
with the charge counted 1.8 times because the burst is at the ground, scaled to the air pressure 1,200 m
up:

| Peak overpressure | Distance | What that pressure generally does to buildings |
|---|---|---|
| 10 psi (69 kPa) | about 86 m | heavy concrete buildings badly damaged |
| 5 psi (34 kPa) | about 121 m | most ordinary buildings collapse |
| 2 psi (14 kPa) | about 204 m | roofs and walls badly damaged |
| 1 psi (7 kPa) | about 339 m | windows broken, light damage |
| – | one mile (1,609 m) | about 0.2 psi |

These are for open, level ground; walls, folds in the ground and the valley's sides shelter some places and
focus the blast on others, and none of that is worked out. The right-hand column is general published
guidance for blast on buildings, not a measurement of this bomb. The figures agree with what was seen in
2017 (destruction within a hundred metres or so, buildings standing beyond) and do not agree with the
"one-mile blast radius" that many reports gave: a mile away the calculation gives a bang and perhaps
cracked glass.

In the film each compound and tree is treated by the pressure calculated for its distance: flattened at
5 psi and more; roofs gone and walls breached from 2 to 5 psi; standing below that. Trees go down inside
the 5 psi line and are stripped and left leaning out to about 2.6 psi.

**The drop (illustrative).** Release at 20,000 ft above sea level (4,900 m above a valley floor at
1,200 m), 95 m/s true air speed. None of that is published; the bomb is described (GlobalSecurity) as
meant for release from high up. A 28 ft extraction parachute (a usual size for heavy platforms; the one
used is not published) pulls the 10.9 tonne load out at about 0.87 g. The bomb is a point mass with drag
(drag area 0.95 m², an estimate): it falls 32.7 s, travels 2.4 km and arrives at **284 m/s (about
1,020 km/h, Mach 0.85), 77° down**. Its guidance is not simulated; the fins are moved a little for the eye.

**Staging, not measurement**: the size of the fireball (about 70 m, the usual rule of thumb for a charge
of this weight), how the dust is driven out and how high and fast the cloud climbs (the film released of
the 2017 strike shows a cloud of this kind), the burnt patch on the ground, how the compounds and trees
go down, the fall of rock over the three nearest tunnel mouths (whether real mouths were closed in 2017
was not published), the brightness of everything. The real strike was after dark; this one is shown in
the late afternoon so that it can be seen.

**The models.** GBU-43/B: length and diameter published; the rod and cone of the nose, the narrower tail
section with its eight-sided housing, the outline and place of the two wings, the raceways, the size and
cells of the lattice fins, the cradle and the platform are estimated from photographs of the Air Force
Armament Museum's example and of the 2003 prototype. The colour is the museum example's (green, yellow
nose); the 2003 test bomb was orange, and the colour of the one used in 2017 is not known to me. **The
cut-open view is a diagram** (thin case, filling, fuze behind the nose, guidance in the tail), not a
drawing of the real bomb. MC-130: the C-130 of segment 11 painted grey; the special-operations aircraft's
nose radar, refuelling probe and other fittings are not modelled.

## A second version: the same bomb on a ruined city district (hypothetical)

`MOAB_SITE=city` swaps the valley for an invented city district (`acity.py`) and writes
`renders/mc130_moab_city.mp4`. **This is hypothetical: the bomb has never been used on a city.** The
district is no real place and nobody is modelled: a street grid 1.8 km across with five- and nine-storey
apartment slabs of the Soviet large-panel kind, already burnt out and partly fallen in, as in the towns
fought over in eastern Ukraine. The aircraft, the bomb and the drop are the same; the ground is 150 m above
sea level instead of 1,200 m, which changes the numbers a little (fall 36 s, arrival at about 300 m/s; 10,
5, 2 and 1 psi at about 88, 123, 213 and 361 m).

Each building is treated by the pressure calculated for its nearest part: at 10 psi and more it comes
down; from 5 to 10 psi about half of it comes down; from 2 to 5 psi it loses a floor here and there; below
that the shell stands. Those thresholds are general published guidance for concrete buildings, and they
come from much longer blasts than this one: a blast as short as a conventional bomb's does less at the
same peak pressure, so the film is if anything too severe. The shelter that buildings give one another
and the channelling of the blast along streets are not worked out, the buildings are not in the gas
simulation (the dust passes through them), and the dust of the buildings' own fall is not shown. What the
film does show correctly is the scale: the heavy damage is a circle about 250 m across in a district
1.8 km across.

## Sound

Recorded effects from `../c130-blu82/sfx` (licensed, not in the repository), put together in `apost.py`;
without them a synthesized track is used. In the `strike` shot the main report is placed when the blast
front reaches the camera, 1.7 s after the flash. Nobody has listened to the mix on loudspeakers.

## Files

- `aconst.py` – published numbers, the release and the fall, the blast calculation
- `abomb.py` – the bomb, whole and cut open, its folding lattice fins, the cradle and platform
- `asite.py` – the valley, its compounds, trees and tunnel mouths, and what the blast does to them
- `acity.py` – the invented ruined city district of the second version
- `asim.py` – the Mantaflow simulation of fireball, dust and cloud
- `ashots.py` – the shots (adapted from segment 11's `dshots`)
- `apost.py` – captions, pressure rings, closing table and sound, on top of segment 11's `dpost`
- `alook.py` – model check renders
- `render_all.py` – bakes, renders every shot and builds the video

## Running it

```bash
pip install bpy numpy pillow scipy
```

```bash
RENDER_DEVICE=GPU python render_all.py frames sims mc130_moab.mp4
```

A quick draft on a CPU:

```bash
VOL_STEP=3 python render_all.py frames sims draft.mp4 --res 640x360 --spp 6 --bake out:112:400
```

Frames and simulation caches are not kept in the repository.
