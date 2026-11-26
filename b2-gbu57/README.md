# Explosion Comparison · 12 — GBU-57 Massive Ordnance Penetrator from a B-2 into a mountain bunker

Twelfth segment of the series. A B-2 Spirit, about 12,200 m (40,000 ft) up, opens its two weapons bays and
releases one of its two GBU-57s, the 30,000 lb "Massive Ordnance Penetrator". Clear of the bay the bomb's
lattice fins swing out; it falls for 46 seconds, goes supersonic and is steered on to a steep path into a
mountainside. The film then cuts the ground open along its path and follows it, half a millisecond per
frame: through 12 m of earth and broken rock and a 2.5 m reinforced-concrete roof into a buried hall, where
its fuze fires it. The gas goes down the access tunnel and back up the bomb's own hole and lifts the roof,
which then comes down into the hall with the cover on it. Everything is procedural (Blender as a Python
module, Cycles). The site, the simulation, the shots and the post-production are adapted from segment 09
(BLU-109 into a mountain bunker), scaled up three times; the aircraft and the bomb are new. Nobody is
modelled anywhere.

**Rendered** on 26 November 2026 on a rented Runpod pod (one NVIDIA RTX PRO 4500 Blackwell, Cycles with OptiX;
the simulations baked on the pod's CPU): frames at 1280 × 720, finished at 1920 × 1080. About 1 hour 10 minutes
from start to finished film, under 1 US dollar of pod time. The film (b2_gbu57.mp4, 58 s) and stills from it are
in `renders/`.

**The bunker and the strike are invented, and the depths are calculated, not measured.**

| # | Shot | What it shows | Speed |
|---|------|---------------|-------|
| 1 | `card`     | The bomb on a studio backdrop, + spec panel | – |
| 2 | `approach` | The B-2 at release height | real time |
| 3 | `intro`    | The bomb as dropped, and its body cut open (a diagram) | – |
| 4 | `bay`      | The bays open; one bomb is released; its lattice fins swing out | real time, then half speed |
| 5 | `fall`     | Riding down behind the bomb through its last 3.5 s | real time |
| 6 | `strike`   | From across the slope: the bomb goes in; dust through the cover, flame from the tunnel | 2.5× slow, then 1.25× |
| 7 | `cutaway`  | The section: penetration with a depth scale, speed and time; the burst; the roof coming down | 0.5 ms per frame; then 10× and 3× slow |
| 8 | `after`    | Twenty seconds later, from outside | real time |
| 9 | summary    | How deep the same bomb goes in five kinds of ground, with the published claims (made in post) | – |

## The numbers in the film

**Published** (USAF fact sheet; Air & Space Forces Magazine; DOT&E annual reports; Wikipedia for the fill):
30,000 lb class (13,600 kg; another published weight is 27,125 lb / 12,304 kg); 20.5 ft (6.2 m) long, 31.5 in
(0.80 m) across; 4,590 lb of AFX-757 and 752 lb of PBXN-114, 2,423 kg of explosive together; a case of
high-strength steel; GPS and inertial guidance; short wings and lattice ("grid") tail fins that are stowed
for carriage; a fuze that can count the layers it passes (the Large Penetrator Smart Fuze); two carried by
a B-2 and by nothing else. First used on 22 June 2025: 14 dropped by seven B-2s, 12 of them on Fordow, six
down each of two ventilation shafts, and two on Natanz.

**How deep it goes is not settled in public.** The Air Force has said "up to 200 ft of unspecified
material"; analysts quote about 200 ft (60 m) of earth or 60 ft (18 m) of 5,000 psi reinforced concrete;
another figure is 8 ft (2.4 m) of 10,000 psi concrete. The film therefore calculates, with the Young /
Sandia penetration equations (SAND97-2426, the same as in segments 09 and 10), using the lower published
weight for what goes into the ground and an estimated nose shape:

| Ground (bomb arriving at 476 m/s) | Calculated | Published |
|---|---|---|
| Ordinary soil | about 50 m | about 60 m |
| Reinforced concrete, 5,000 psi | about 5.8 m | claims up to 18 m |
| Reinforced concrete, 10,000 psi | about 4.7 m | 2.4 m |
| Weathered rock | about 2.7 m | – |
| Sound limestone | about 1.6 m | – |

For soil the calculation and the published figure agree; for concrete they do not, in both directions,
and the film says so in its closing table. A consequence the film also states: one bomb does not reach a
hall under tens of metres of rock, which is why at Fordow six were sent down each shaft.

**The drop (illustrative).** Level release at Mach 0.80 (236 m/s), 10,500 m above a target that lies at
1,700 m. A point mass with drag; from 5 km up the fins steer it to a 68° path. It falls 46.4 s, travels
about 10 km and arrives at **476 m/s (about 1,710 km/h, Mach 1.4), 69° down**. No release profile or
impact speed is published.

**The bunker (invented).** A reinforced-concrete hall 30 m by 16 m by 7 m with a 2.5 m roof, cut and covered
in a 25° slope under about 12 m of compacted earth and broken rock (13 m along the bomb's path), with a
6 m tunnel out to a portal. By the calculation the bomb leaves the cover at about 330 m/s and the roof at
about 190 m/s; the fuze is set to fire a little past the middle of the hall, 64 thousandths of a second
after the impact, 18.5 m below the point of impact.

**Staging, not measurement**: how the gas moves (the sources are placed by hand along its way), how far
the roof is lifted and how it falls (`wsite.V_HEAVE`, `ROOF_DROP`, `SURF_DROP`), the size of the hollow
left in the slope, the brightness of everything.

**The models.** B-2: span 52.4 m, length 21.0 m, leading edges swept 33° and every trailing edge parallel
to one of them (the planform's area comes out at 480 m² against the published 478); the break points of
the trailing edge, the thickness, the humps over crew and engines, the intakes, exhausts and windows and
the size and place of the bays are estimated from photographs and drawings. GBU-57: length and diameter
published; the nose, the wings, the lattice fins, the tail section and the colour are estimated from
photographs; **the cut-open view is a diagram** (solid nose, a 60 mm wall worked out from the weights, the
two fills, a fuze well), not a drawing of the real bomb, whose inside is not published.

## Sound

The soundtrack is put together by segment 09's `ppost.py` from the recorded effects in `../b1b-gbu28/sfx`
(licensed, not in the repository; see `../b1b-gbu28/gsfx.py`), or synthesized without them. Nobody has
listened to the mix on loudspeakers.

## Files

- `wconst.py` – published numbers, the fall, the penetration calculation
- `wbomb.py` – the GBU-57, whole and cut open; folding lattice fins
- `wb2.py` – the B-2
- `wsite.py`, `wsim.py`, `wshots.py` – site, simulations and shots, adapted from segment 09's `psite`, `psim`, `pshots`
- `wpost.py` – this film's captions and drawings on top of segment 09's `ppost`
- `wlook.py` – model check renders
- `render_all.py` – bakes, renders every shot and builds the video

## Running it

```bash
pip install bpy numpy pillow scipy
```

```bash
RENDER_DEVICE=GPU python render_all.py frames sims b2_gbu57.mp4
```

A quick draft on a CPU:

```bash
VOL_STEP=3 python render_all.py frames sims draft.mp4 --res 640x360 --spp 6 --bake out:96:260,in:112:420
```

Frames and simulation caches are not kept in the repository.
