# Explosion Comparison · 12 — GBU-57 Massive Ordnance Penetrator from a B-2 into a mountain bunker

Twelfth segment of the series. A B-2 Spirit, about 15,200 m (50,000 ft) up, opens its two weapons bays and
releases one of its two GBU-57s, the 30,000 lb "Massive Ordnance Penetrator". Clear of the bay the bomb's
lattice fins swing out; it falls for 53 seconds, goes supersonic and is steered on to a steep path into a
mountainside. The film then cuts the ground open along its path and goes down with it: through 55 m of
earth and a 2.5 m reinforced-concrete roof into a hall **61 m (200 ft) below the point of impact**, where
its fuze fires it. The gas goes out along 130 m of tunnel and back up the bomb's own hole; the broken roof
and the earth on it come down into the hall; at the surface nothing breaks. Everything is procedural
(Blender as a Python module, Cycles). The site, the simulation, the shots and the post-production are
adapted from segment 09 (BLU-109 into a mountain bunker); the aircraft and the bomb are new. Nobody is
modelled anywhere.

**Rendered** on 26 November 2026 on a rented Runpod pod (one NVIDIA RTX PRO 4500 Blackwell, Cycles with OptiX;
the simulations baked on the pod's CPU): frames at 1280 × 720, finished at 1920 × 1080. The pod existed for
89 minutes, about 1.07 US dollars at 0.72 dollars an hour; that includes a second bake of the section's smoke
and a second render of its last 216 frames, after the first pass showed the flame in the tunnel as a row of
separate balls. The film (b2_gbu57.mp4, 65 s) and stills from it are in `renders/`.

**Known flaws.** At its peak the flame in the section is drawn a metre or two past the walls of the hall
and the tunnel (the simulation's cells are 0.42 m). The fireball is a flat pale orange. Nobody has listened
to the sound on loudspeakers.

**The bunker and the strike are invented. The depth is the U.S. Air Force's published figure; the speeds
on the way down are calculated, not measured.**

| # | Shot | What it shows | Speed |
|---|------|---------------|-------|
| 1 | `card`     | The bomb on a studio backdrop, + spec panel | – |
| 2 | `approach` | The B-2 at release height | real time |
| 3 | `intro`    | The bomb as dropped, and its body cut open (a diagram) | – |
| 4 | `bay`      | The bays open; one bomb is released; its lattice fins swing out | real time, then half speed |
| 5 | `fall`     | Riding down behind the bomb through its last 3.5 s | real time |
| 6 | `strike`   | From down the slope: the bomb goes in; later flame from the tunnel mouth, smoke from the hole | 2.5× slow, then 1.25× |
| 7 | `cutaway`  | The section: the whole 61 m, then down with the bomb beside a depth gauge in metres and feet; the burst; the roof coming down | 1.25 ms, then 0.5 ms per frame; then 10× and 3× slow |
| 8 | `after`    | Twenty seconds later, from outside | real time |
| 9 | summary    | The Air Force's figure, and how deep the same bomb goes in five kinds of ground by calculation (made in post) | – |

## The numbers in the film

**Published** (USAF fact sheet; Air & Space Forces Magazine; DOT&E annual reports; Wikipedia for the fill):
30,000 lb class (13,600 kg; another published weight is 27,125 lb / 12,304 kg); 20.5 ft (6.2 m) long, 31.5 in
(0.80 m) across; 4,590 lb of AFX-757 and 752 lb of PBXN-114, 2,423 kg of explosive together; a case of
high-strength steel; GPS and inertial guidance; short wings and lattice ("grid") tail fins that are stowed
for carriage; a fuze that can count the layers it passes (the Large Penetrator Smart Fuze); two carried by
a B-2 and by nothing else. First used on 22 June 2025: 14 dropped by seven B-2s, 12 of them on Fordow, six
down each of two ventilation shafts, and two on Natanz.

**How deep it goes.** The Air Force's own words (the caption to its photographs of the bomb) are that it is
"designed to penetrate up to 200 feet underground before exploding". That is the depth this film shows:
the hall's roof is 54.5 m and the burst 60.6 m (199 ft) below the point where the bomb goes in. The first
version of this film put the hall only 18.5 m down and mentioned the 200 ft in its closing table; that was
wrong for a film about this bomb and has been replaced.

What the 200 ft are made of is not stated, and the other published figures disagree with each other: the
2004 proposal for the weapon claimed 200 ft (61 m) of 5,000 psi reinforced concrete, 26 ft (8 m) of
10,000 psi concrete and 130 ft (40 m) of moderately hard rock (GlobalSecurity, which reproduces the
diagram, doubts those numbers); Janes is quoted for about 200 ft (61 m) of earth or 60 ft (18 m) of
concrete; an independent calculation quoted by NPR got about 8 m in medium-strength rock.

The film's own calculation uses the Young / Sandia penetration equations (SAND97-2426, the same as in
segments 09 and 10), with the lower published weight for what goes into the ground and an estimated nose
shape. **By these equations the bomb reaches 61 m only in earth**, so the film's mountainside is earth,
and soft earth at that (S-number 9), which leaves the bomb enough speed at 55 m to go through the roof:

| Ground (bomb arriving at 525 m/s) | Calculated | Published |
|---|---|---|
| Soft earth (as in the film) | about 84 m | – |
| Ordinary soil | about 56 m | 61 m (200 ft) of earth |
| Reinforced concrete, 5,000 psi | about 6 m | 18 m (60 ft); the 2004 proposal: 61 m |
| Reinforced concrete, 10,000 psi | about 5 m | 2.4 m (8 ft) and 8 m (26 ft) are both quoted |
| Weathered rock | about 3 m | the 2004 proposal: 40 m of moderately hard rock |
| Sound limestone | about 2 m | – |

For earth the calculation and the published figure agree; for concrete and rock the open equations give
far less than the claims, and the film says so in its closing table. A consequence the film also states:
one bomb does not reach a hall under tens of metres of hard rock, which is why at Fordow six were sent
down each shaft.

**The drop (illustrative).** Level release at Mach 0.80 (236 m/s), 13,540 m above a target that lies at
1,700 m, that is at 15,240 m (50,000 ft), the B-2's ceiling: the highest release gives the most speed.
A point mass with drag; from 5 km up the fins steer it to a 70° path. It falls 53.0 s, travels about
12 km and arrives at **525 m/s (about 1,890 km/h, Mach 1.6), 70° down**. No release profile or impact
speed is published.

**The bunker (invented).** A reinforced-concrete hall 30 m by 16 m by 7 m with a 2.5 m roof, 54.5 m of soft
earth over it (58 m along the bomb's path) in a 25° slope, and a 6 m tunnel 130 m long out to a portal.
A hall that deep under earth, not rock, is not how such places are built; it is what lets one bomb reach
it. By the calculation the bomb leaves the earth at about 290 m/s and the roof at about 145 m/s; the fuze
is set to fire in the middle of the hall, 181 thousandths of a second after the impact.

**Staging, not measurement**: how the gas moves (the sources are placed by hand along its way, in relays
along the tunnel and up the bomb's hole), when it reaches the doors and the top of the hole
(`wsite.T_DOOR`, `wsim.T_UP`), whether the hole stays open at all in soft earth, how the roof breaks and
falls (`wsite.V_HEAVE`, `ROOF_DROP`), the size of the ring of earth thrown out where the bomb goes in, the
brightness of everything. That the surface does not break follows from the depth: a charge of this size
61 m down is far below the depth at which a burst still makes a crater.

**The models.** B-2: span 52.4 m, length 21.0 m, leading edges swept 33° and every trailing edge parallel
to one of them (the planform's area comes out at 480 m² against the published 478); the break points of
the trailing edge, the thickness, the humps over crew and engines, the intakes, exhausts and windows and
the size and place of the bays are estimated from photographs and drawings. GBU-57: length and diameter
published; the nose, the wings, the lattice fins, the tail section and the colour are estimated from
photographs; **the cut-open view is a diagram** (solid nose, a 60 mm wall worked out from the weights, the
two fills, a fuze well), not a drawing of the real bomb, whose inside is not published.

## Sound

The soundtrack is put together in `wpost.py` from the recorded effects in `../b1b-gbu28/sfx` (licensed, not
in the repository; see `../b1b-gbu28/gsfx.py`); without them segment 09's synthesized track is used.
Nobody has listened to the mix on loudspeakers.

## Files

- `wconst.py` – published numbers, the fall, the penetration calculation
- `wbomb.py` – the GBU-57, whole and cut open; folding lattice fins
- `wb2.py` – the B-2
- `wsite.py`, `wsim.py`, `wshots.py` – site, simulations and shots, adapted from segment 09's `psite`, `psim`, `pshots`
- `wpost.py` – this film's captions, drawings and soundtrack on top of segment 09's `ppost`
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
VOL_STEP=3 python render_all.py frames sims draft.mp4 --res 640x360 --spp 6 --bake out:104:260,in:150:470
```

Frames and simulation caches are not kept in the repository.
