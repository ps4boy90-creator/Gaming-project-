# Explosion Comparison · 10 — GBU-28 bunker buster from a B-1B into a bunker under flat desert

Tenth segment of the series. A B-1B Lancer at about 9,300 m releases one GBU-28/B, the 5,000 lb class
laser-guided "bunker buster" of 1991, from a pylon under its forward fuselage. The bomb falls for 42
seconds, goes supersonic, and is steered almost straight down on to a flat plain. The film then cuts the
ground open along its path and shows, half a millisecond per frame, how far it gets: through 15 m of
soil, a concrete slab and the roof of a chamber, where its fuze fires it 60 thousandths of a second after
the impact, about 20 m down. The gas is followed along the corridors, up the stair and up the air shafts;
on the surface there is only a hole and, seconds later, smoke. Everything is procedural (Blender as a
Python module, Cycles) and shares the aircraft, render setup, effects and post tools with the earlier
segments. Nobody is modelled anywhere.

**Status: not rendered at full quality yet.** The code is complete and has been checked end to end with a
low-resolution draft rendered on a CPU; the 1080p render on a GPU is still to do, so there is no
`renders/` folder here yet.

**The GBU-28 is not a B-1B weapon.** In service it is dropped by the F-15E and the B-2, and first by the
F-111F. The B-1B was asked for; what it has really flown, in tests from 2024, is the GBU-28's 5,000 lb
successor, the GBU-72, on Boeing's Load Adaptable Modular pylon under the forward fuselage. The film
carries the GBU-28 the same way and says on its title card, in the approach shot and in the closing table
that this is not a service fit. **The bunker and the strike are invented, and the depths are calculated,
not measured.**

| # | Shot | What it shows | Speed |
|---|------|---------------|-------|
| 1 | `card`     | The bomb on a studio backdrop, tail wings opening, + spec panel | – |
| 2 | `approach` | The B-1B at release height with the bomb on its pylon | real time |
| 3 | `intro`    | The bomb as dropped, and the BLU-113 warhead cut open: 58 mm wall, filling, fuze | – |
| 4 | `release`  | The pylon lets go; the tail wings spring open | real time, then half speed |
| 5 | `fall`     | Riding down behind the bomb through its last 3.5 s | real time |
| 6 | `strike`   | From the ground: a spurt of soil; then smoke from the air shafts and the entrance | 2.5× slow, then 1.25× |
| 7 | `cutaway`  | The section: penetration with a depth scale, speed and time; the burst; where the gas goes | 0.5 ms per frame through the soil, 0.2 ms from the slab on; then 10× and 3× slow |
| 8 | `after`    | Twenty seconds later, from outside | real time |
| 9 | summary    | How deep the same bomb goes in four kinds of ground (made in post) | – |

## The numbers in the film

Release: level at Mach 0.9 (272 m/s), 9,000 m above a plain that lies 300 m above sea level. The bomb
falls 41.7 s and travels about 9 km; from 6 km up its wings steer it to a 78° path. It arrives at
**439 m/s (about 1,580 km/h, Mach 1.3)**. A published remark from the 1991 programme speaks of the bomb
"travelling at 1,400 feet per second" (427 m/s).

| Layer on the bomb's path | Thickness | Speed in → out | Time |
|---|---|---|---|
| Soil: sand and silt | 15 m | 439 → 320 m/s | 40.4 ms |
| Slab: reinforced concrete | 0.6 m | 320 → 288 m/s | 2.0 ms |
| Soil between slab and roof | 1.0 m | 288 → 281 m/s | 3.6 ms |
| Chamber roof: reinforced concrete | 0.5 m | 281 → 255 m/s | 1.9 ms |
| The chamber, 4 m high | – | 255 m/s | fuze fires 12 ms in |

The fuze fires at 60 ms with the nose 20.1 m below the surface, a metre above the chamber floor, and
the whole warhead inside the chamber: 286 kg of explosive in a closed space of about 280 m³.

The same bomb at the same speed in uniform ground (closing table): about 33 m of soil (published: more
than 30 m), about 4.3 m of reinforced concrete (published: more than 6 m), about 2.0 m of weathered rock,
about 1.2 m of sound limestone.

## What is sourced and what is not

**From sources**

| Item | Value | Source |
|------|-------|--------|
| GBU-28/B | 5.84 m (19 ft 2 in) long; about 2,130 kg (4,637 to 4,700 lb); wings 0.72 m across folded, 1.68 m open; Paveway III laser guidance unit WGU-36/B and airfoil group BSG-92/B; later versions add GPS / inertial guidance | FAS / GlobalSecurity; designation-systems.net; Air & Space Forces Magazine |
| BLU-113/B warhead | 153.5 in (3.90 m) long, 14.56 in (370 mm) across, wall 2.28 in (58 mm), 4,500 lb (2,041 kg), 625 to 647 lb of tritonal (286 kg used here); nose cone and fuze (FMU-143) of the BLU-109; fuze delays of 60 ms and 120 ms appear in test records | NDIA 2005 briefing on the BLU-122; FAS; designation-systems.net |
| How it was made | the first bodies were surplus 8-inch howitzer barrels, bored out to 10 inches; from go-ahead to combat in under four weeks; first drop 24 February 1991, first use 27 February 1991 by two F-111Fs | FAS; Kopp, *The GBU-28 Bunker Buster* |
| Penetration | more than 20 ft (6 m) of concrete, more than 100 ft (30 m) of earth; in a sled test the warhead went through 22 ft (6.7 m) of stacked reinforced-concrete slabs and flew on; the first test bomb was found about 150 ft down | FAS / GlobalSecurity; Kopp; Archer, *F-111* |
| The 1991 bunkers | about 50 ft of soil; a two-foot slab of reinforced concrete over concrete tubes and chambers; a stair down from a hardened entrance; air vents to the surface; after the hit, smoke from the vents and the entrance within seconds | Kopp; Davies, *F-111 & EF-111 Units in Combat* |
| Aircraft that carry it | F-111F (1991), F-15E, B-2A | Air & Space Forces Magazine; GlobalSecurity |
| B-1B and 5,000 lb bombs | weapons bays 180 in (4.57 m) long; six usable external hardpoints; the GBU-72 carried and released from a Load Adaptable Modular pylon in tests from 2024; the Sniper targeting pod sits on the forward right hardpoint | USAF / AFGSC releases, 2019 and 2024; The Aviationist |
| Penetration equations | Young, *Penetration Equations*, Sandia report SAND97-2426 (1997) | the report |

**Not from sources (calculated or illustration)**

* **The GBU-28 on a B-1B.** See above. The pylon is a plain fairing in the place of Boeing's, on the
  forward left hardpoint (the right one carries the targeting pod). Release speed and height are
  B-1B-like, not a cleared envelope.
* **How deep the bomb goes.** Calculated with Young's equations, layer by layer. Guesses: the nose
  length (0.62 m, from photographs), the soil number (S = 5.2, medium-dense sand and silt), the
  concrete numbers (S about 0.75 for the two thin slabs) and the impact speed. For soil the result
  (33 m) agrees with what is published. **For concrete it is lower than what is published** (4.3 m
  against "more than 6 m"); the film says so in its closing table. The calculation assumes the bomb
  stays whole and straight.
* **The fuze.** The 60 ms delay is a real setting of this fuze, and with this bunker it happens to
  fire in the chamber. A bunker 5 m deeper or shallower would need another setting or would be hit
  less well; later bombs use a fuze that senses the empty space instead of counting time.
* **The bunker.** Two chambers 14 m and 12 m long, 4 m high, with 0.5 m roofs, floors and walls, a
  2.6 m corridor, a stair at 45° and two air shafts, under a 0.6 m slab and 15 m of soil. It follows
  the published description of the Iraqi bunkers in outline only. Its contents are stand-in boxes.
* **What the burst does.** That the gas goes along the corridors into the next chamber, up the stair,
  up the shafts and back up the bomb's hole, and that from above there is little to see but smoke,
  follows the 1991 account. Timings (the door blown out 0.16 s after the burst, the roof coming down
  over about 1.5 s) and the roof's short lift are staging. The surface is drawn as not moving at all.
  The two gas simulations are driven by hand-placed sources along the gas's way; they show where it
  goes, not a measured blast.
* **Guidance unit and tail** are shown crushed and stripped at the surface while the steel warhead
  goes on alone, which is what happens; exactly how is staging. No laser spot or designator is shown.
* **The bomb model.** The lengths of the guidance unit and the tail, the canards, the wings' shape
  and the inside of the warhead (how far the nose is solid, the fuze well) are estimated from
  photographs.
* The B-1B is the model of segment 09, with the same limits. Under the aircraft the ground is the
  open desert of the earlier air segments.
* The sound is synthesized.

## Files

- `gconst.py` — published figures, the fall, Young's equations and the layer-by-layer result (no bpy;
  `python3 gconst.py` prints the numbers above).
- `gbomb.py` — the GBU-28/B in parts (warhead, guidance unit, tail with folding wings) and the cut-open BLU-113.
- `gcarry.py` — the B-1B of `../b1b-blu109/` with a pylon and the bomb.
- `gsite.py` — the plain from outside, and the same ground cut along the bomb's path.
- `gsim.py` — the two Mantaflow bakes (`out`: seen from the surface; `in`: the section).
- `gshots.py` — the eight render shots and the frame renderer.
- `gpost.py` — title card, captions, depth scale, closing table, sound, encode.
- `render_all.py` — bakes if needed, renders every shot (resumable) and runs post.

```
pip install bpy numpy pillow scipy    # Blender as a Python module (Python 3.13), plus ffmpeg on the PATH
RENDER_DEVICE=GPU python3 b1b-gbu28/render_all.py <frames_root> <sim_root> [out.mp4]
```
