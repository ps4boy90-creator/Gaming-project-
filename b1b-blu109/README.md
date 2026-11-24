# Explosion Comparison · 09 — BLU-109 penetrator bomb from a B-1B into a mountain bunker

Ninth segment of the series. A B-1B Lancer at about 8,200 m opens its forward weapons bay and drops one
GBU-31(V)3/B — a 2,000 lb BLU-109 penetrator with a JDAM guidance tail. The bomb falls for about 36
seconds, steers itself steep on to a mountainside and goes in. The film then cuts the ground open along
the bomb's path and shows, half a millisecond per frame, how far it gets: through the earth cover, through
the concrete roof, across the room and into the floor, where its fuze fires it 60 thousandths of a second
after the impact. Everything is procedural (Blender as a Python module, Cycles) and shares the render
setup, effects and post tools with the earlier segments. Nobody is modelled anywhere.

**Status: not rendered at full quality yet.** The code is complete and has been checked end to end with a
low-resolution draft rendered on a CPU (640 × 360, a few samples a pixel); the 1080p render on a GPU is still
to do, so there is no `renders/` folder here yet.

**The bunker, the mountain and the strike are invented, and the depths are calculated, not measured.**
The film says so on its title card, on the section and in the closing table.

| # | Shot | What it shows | Speed |
|---|------|---------------|-------|
| 1 | `card`     | The B-1B on a studio backdrop, wings swinging from 15° to 67.5°, + spec panel | – |
| 2 | `approach` | The aircraft at release height, wings swept | real time |
| 3 | `intro`    | The bomb as dropped, and the BLU-109 warhead cut open: case, filling, fuze | – |
| 4 | `bay`      | The bay opens on its rotary launcher; one bomb is ejected; the launcher turns | real time, then half speed |
| 5 | `fall`     | Riding down behind the bomb through its last 3.5 s | real time |
| 6 | `strike`   | From across the slope: the bomb goes in; the burst comes out of the ground and the tunnel | 2.5× slow, then 1.25× |
| 7 | `cutaway`  | The section: penetration with a depth scale, speed and time; then the burst in the room | 0.5 ms per frame; then 10× and 3× slow |
| 8 | `after`    | Twenty seconds later, from outside | real time |
| 9 | summary    | How deep the same bomb goes in four kinds of ground (made in post) | – |

## The numbers in the film

Release: level at Mach 0.85 (261 m/s), 6,000 m above a target that lies 2,200 m above sea level.
The bomb falls 35.6 s and travels about 8 km; in the last 3 km of height its tail steers it to a 66°
path, about square to the 25° slope. It arrives at **352 m/s (about 1,270 km/h)**.

| Layer on the bomb's path | Thickness along the path | Speed in → out | Time |
|---|---|---|---|
| Cover: compacted earth and broken rock | 3.6 m | 352 → 264 m/s | 11.7 ms |
| Roof: reinforced concrete, 0.9 m thick (35 MPa, 2 % steel) | 0.98 m | 264 → 150 m/s | 4.8 ms |
| The room, 3 m high | 3.28 m | 150 m/s | 21.9 ms |
| Floor: 0.6 m of concrete on weathered rock | stops after 0.72 m | 150 → 0 m/s | 8.6 ms |

It comes to rest 47 ms after the impact, its nose about 0.7 m into the floor and **7.8 m below the
point where it went in**; the fuze fires at 60 ms. With nearly the whole bomb still inside the room,
243 kg of explosive goes off in a closed space of 180 m³.

The same bomb at the same speed in uniform ground (closing table): about 8 m of compacted fill, about
1.9 m of reinforced concrete (published: 1.2 to 2.4 m), about 0.9 m of weathered rock, about 0.5 m of
sound limestone.

## What is sourced and what is not

**From sources**

| Item | Value | Source |
|------|-------|--------|
| B-1B | 44.5 m long, 10.4 m high; span 41.8 m with the wings forward, 24.1 m swept (15° to 67.5°); four F101-GE-102 turbofans; crew of four; three weapons bays; up to 24 GBU-31 | USAF fact sheet |
| B-1B layout | blended wing and body; two engines in each of two nacelles under the wing roots; all-moving tailplanes part-way up the fin; small vanes beside the nose; eight 2,000 lb bombs on a rotary launcher in each bay | USAF fact sheet; flight-manual description; photographs |
| BLU-109/B | 2.40 m long, 368 mm (14.5 in) across, about 874 kg (1,927 lb); 243 kg (535 lb) of tritonal (PBXN-109 in later bombs); one-piece forged steel case at least 27 mm (1.06 in) thick; fuze in the tail (FMU-143), which fires 0.060 s after impact | USAF Weapons File; ordnance data sheet |
| BLU-109 against concrete | 1.2 to 1.8 m of reinforced concrete (ordnance data); 1.8 to 2.4 m (Jane's, cited by Hansson, FOI 2011) | as given |
| GBU-31(V)3/B | 3.77 m long, 961 kg, 0.635 m across the fins; tail kit with GPS and inertial guidance; strakes strapped round the body; within 5 m when GPS is available; released up to about 24 km from the target | USAF JDAM fact sheet |
| In Afghanistan | in the first six months of Operation Enduring Freedom B-1Bs dropped nearly 3,900 JDAMs | USAF fact sheet |
| Penetration equations | Young, *Penetration Equations*, Sandia report SAND97-2426 (1997): depth in soil, rock and concrete from weight, diameter, nose shape, speed and a number for the target; layered targets by the speed left over | the report |

**Not from sources (calculated or illustration)**

* **How deep the bomb goes.** Calculated with Young's equations for an invented target. The inputs
  that are guesses: the nose length (0.62 m, from photographs), the target numbers (S = 3.0 for the
  cover, 0.73 for the roof slab, 0.32 for weathered rock, 0.19 for sound limestone), and the impact
  speed. The equations themselves scatter by 15 to 20 % against tests. The check that they are in the
  right region: for thick reinforced concrete they give 1.9 m, inside the published 1.2 to 2.4 m.
  The calculation assumes the bomb stays whole and straight; a real one can bend its path in layered
  ground, and against rock or very thick concrete it can break up.
* **The release and the fall.** Height, speed, the 66° impact angle and the 352 m/s are a plausible
  profile from a point-mass fall with drag and a 1 g turn at the end. JDAM can be given an impact
  angle; the actual limits and profiles are not in the film.
* **The bunker and the mountain.** A cut-and-cover room 10 × 6 × 3 m, 0.9 m roof, 0.6 m walls and
  floor, under 2.6 to 7.5 m of cover on a 25° slope, with a 7 m tunnel to a portal. Its contents are
  stand-in boxes and drums.
* **What the burst does.** That the gas vents down the tunnel and back up the hole, throws the doors
  out, lifts the roof and its cover and drops them into the room, leaving a hollow, follows from the
  charge: 243 kg in 180 m³ gives a gas pressure of a few megapascals, against one or two hundred
  kilopascals of roof and earth resting on it (an estimate from charge weight and room volume). How fast and how
  far — the roof thrown up about 1.5 m, down again after about 1.4 s, a 1.9 m hollow — is staging.
  The two gas simulations are driven by hand-placed sources; they show where the gas goes, not a
  measured blast.
* **The tail kit** and strakes are shown torn off and crumpled at the surface while the steel
  warhead goes on alone, which is what happens; exactly how they come off is staging.
* **The B-1B model.** Proportioned from the published dimensions and photographs: fuselage sections,
  the glove, nacelles, fin and tailplanes are estimates; there are no panel lines, markings or
  landing gear, and the paint is plain dark grey. The bay's position and length, the doors (two
  simple leaves) and the launcher are simplified. Only the forward bay opens.
* **Under the aircraft** the ground is the open desert of the earlier air segments, not mountains.
* The cut-open warhead's inside (how far the nose is solid, the shape of the cavity, the fuze well)
  is drawn from the published wall thickness and photographs, not from a drawing.
* The sound is synthesized.

## Files

- `pconst.py` — published figures, the fall, Young's equations and the layer-by-layer result (no bpy;
  `python3 pconst.py` prints the numbers above).
- `pbomb.py` — GBU-31(V)3/B and the cut-open BLU-109.
- `pb1b.py` — the B-1B: swing wings, bay doors, rotary launcher with eight bombs.
- `psite.py` — the mountainside from outside, and the same ground cut along the bomb's path.
- `psim.py` — the two Mantaflow bakes (`out`: seen from outside; `in`: the section).
- `pshots.py` — the eight render shots and the frame renderer.
- `ppost.py` — title card, captions, depth scale, closing table, sound, encode.
- `plook.py` — renders the aircraft and the bomb from several directions (model check).
- `render_all.py` — bakes if needed, renders every shot (resumable) and runs post.

Mesh helpers and the puff-cloud effect come from `../reaper-hellfire/`; terrain material from
`../tomahawk-sub/`; overlay and sound helpers from `../grenade-explosion/` and `../blackhawk-mk77/`.

```
pip install bpy numpy pillow scipy    # Blender as a Python module (Python 3.13), plus ffmpeg on the PATH
RENDER_DEVICE=GPU python3 b1b-blu109/render_all.py <frames_root> <sim_root> [out.mp4]
```
