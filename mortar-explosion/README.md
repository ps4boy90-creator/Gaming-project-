# Explosion Comparison · 03 — M120 120 mm mortar (M934A1 HE) next to ruined buildings

Third segment of the series: "Ghost Man" (the transparent figure) is the assistant gunner of a US Army
M120 mortar. He hangs an M934A1 high-explosive round in the muzzle, lets it go, and the round comes
down beside a group of old, broken-down masonry buildings 2,000 m away. Everything is procedural
(Blender as a Python module, Cycles) and shares the terrain, figure, render setup and post tools with
[`../grenade-explosion`](../grenade-explosion) and [`../rpg7-explosion`](../rpg7-explosion).

| # | Shot | What it shows | Speed |
|---|------|---------------|-------|
| 1 | `card`   | The mortar and a round on a studio backdrop + spec panel | – |
| 2 | `load`   | Ghost Man lifts the round to the muzzle, lowers the tail in and holds it ("hanging") | real time |
| 3 | `fire`   | Release, the slide down the tube, then flash, smoke jet and ground dust | real time, then 5× slow |
| 4 | `fall`   | Chase camera riding down behind the round for its last three seconds | real time |
| 5 | `impact` | Ground-level view of the burst beside the ruins | 5× slow, then 2.5× |
| 6 | `radius` | From the air: fragment strikes race outwards, the 75 m bursting radius is drawn | 5× slow, then 2.5× |
| 7 | `after`  | Crater, pock-marked walls, the knocked-down wall; crane up over the ruins | – |

## What is sourced and what is not

**From sources**

| Item | Value | Source |
|------|-------|--------|
| Cannon M298 | 120 mm smooth bore, 69 in (1.753 m), 110 lb | FM 23-90 ch. 7; PM mortar systems data |
| Bipod M190 / baseplate M9 / sight M67 | 70 lb / 136 lb / 2.5 lb; baseplate 36.25 × 35.62 in "rounded triangle" | FM 23-90 ch. 7; US Army sources-sought notice |
| Elevation | 0710–1510 mils (the model is laid at 1100 mils = 61.9°) | FM 23-90 table 7-1 |
| Range | 200–7,200 m | FM 23-90 table 7-1 |
| Rate of fire | 16 rds/min first minute, 4 sustained | FM 23-90 table 7-1 |
| **Bursting radius** | **75 m** (M933/M934 HE; 60 m for the older M57) | FM 23-90 table 7-1 and ammunition table |
| Round M934A1 | 27.99 in (711 mm), 31.2 lb (14.2 kg), Comp B, M734A1 multi-option fuze, olive drab with yellow markings | manufacturer data sheet; FM 23-90 |
| Loading drill | round held with two hands, lowered tail-first until the narrow tail is inside, released on "fire"; it slides down and strikes the fixed firing pin | FM 23-90 ch. 7 |
| M67 grenade (scale ring) | 15 m casualty radius | segment 01 |

Wikipedia quotes a lethal radius of 225 ft (69 m) for the same round; the video uses the field manual's
75 m.

Shapes (collars on the tube, white alignment line, buffer clamp, traversing handwheel, elevating
column, leg chain, dished baseplate with handles, horseshoe charges on the tail boom) are modelled
from public photos of the weapon in US Army use.

**Not from sources (illustration)**

* The trajectory is drag-free arithmetic for 1100 mils and 2,000 m: 154 m/s at the muzzle, about 28 s
  of flight, apex about 935 m. It is not a firing-table solution.
* The size of the smoke/dust cloud, the crater, the wall that falls and where each fragment mark lands
  come from this simulation, not from test data. Only the 75 m radius itself is the published figure;
  the dust spurts inside it show *that* fragments strike out to that distance, not a measured pattern.
* The ruins are invented.

## Files

- `mconst.py` — shared geometry, timing and the ballistic helpers (no bpy).
- `m120.py` — the mortar (cannon, bipod, baseplate, sight) and the M934A1 round.
- `ruins.py` — the target set: brick-course ruins with a plaster/brick shader, rubble, timbers, the
  wall that is knocked down, crater, blast marks.
- `msim.py` — the two Mantaflow gas sims (muzzle blast, detonation).
- `mshots.py` — Ghost Man's loading drill, burst effects (ejecta, sparks, fragment strikes, radius
  rings), the seven shots, frame renderer.
- `mpost.py` — title card, HUD, sound, encode.
- `render_all.sh` — bakes the sims if needed, renders every shot (resumable) and runs post.

```
./render_all.sh <frames_root> <sim_root> [out.mp4]
```
