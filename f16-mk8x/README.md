# Explosion Comparison · 07 — F-16 with a Mk 82, a Mk 83 and a Mk 84 on three bunkers

Seventh segment of the series. An F-16C runs in level at 450 kt and 1,500 m over a desert and
releases three bombs of the same family, 0.6 seconds apart: a Mk 82 (500 lb class) from under its
left wing, a Mk 83 (1,000 lb class) from under its right wing and a Mk 84 (2,000 lb class) from the
centre line. They fall for 17.5 seconds and land on three reinforced-concrete bunkers about 155 m
apart.

The bombs are shown **one at a time**. Each has its own chapter — an introduction with its
dimensions and what sets it apart, its impact, and its radii seen from the air — and the film ends
with a table of the three. The three radius shots use exactly the same camera, so each burst can be
judged against the one before it. Everything is procedural (Blender as a Python module, Cycles) and
shares the terrain, render setup, burst effects and post tools with the earlier segments. Nobody is
modelled in the bunkers.

| # | Shot | What it shows | Speed |
|---|------|---------------|-------|
| 1 | `card`      | The F-16 with its load on a studio backdrop + spec panel | – |
| 2 | `approach`  | Air to air: the jet running in | real time |
| 3 | `release`   | From ahead and below: the three bombs leave in turn | real time, then 3× slow |
| 4 | `intro82`   | The Mk 82 alone, with its length, diameter, weight and filling, beside a 1.8 m figure | – |
| 5 | `fall`      | The camera rides down behind the Mk 82 for its last 2.6 seconds | real time |
| 6 | `impact82`  | The Mk 82 on the roof of the first bunker | 2.5× slow, then 1.25× |
| 7 | `radius82`  | From the air: the burst and its two radii | about 1.5× slow |
| 8–10 | `intro83`, `impact83`, `radius83` | The same for the Mk 83 (the Mk 82's blast circle stays on screen, faintly) | |
| 11–13 | `intro84`, `impact84`, `radius84` | The same for the Mk 84 (both earlier circles stay on screen) | |
| 14 | `after`    | Half a minute later: the camera travels from bunker to bunker | real time |
| 15 | summary    | Table of the three (made in post) | – |

The three introductions share one camera, lens and distance, so the bombs appear at their true size
relative to each other. For the impact shots the camera stands back in proportion to each bomb's
radius (1.3× and 1.7× further for the Mk 83 and Mk 84); the film says so on screen.

## What is sourced and what is not

**From sources**

| Item | Value | Source |
|------|-------|--------|
| F-16C | length 15.03 m; span 9.45 m over the tip launchers (9.14 m theoretical); height 5.09 m; wing area 27.87 m² | aerospaceweb; USAF TO 00-105E-9 |
| Wing | leading-edge sweep 40°, trailing edge unswept, no dihedral, taper 0.2275, NACA 64A204 (4 % thick); centre-line root chord 4.97 m, tip 1.13 m | NASA TP; JSBSim model data |
| Tail | stabilator span 5.58 m, 40° sweep, 10° anhedral; fin 2.57 m exposed height, 47.5° sweep; two ventral fins canted 15° | same |
| Stations | nine; limits 1/9 193 kg, 2/8 318 kg, 3/7 1,588 kg, 4/6 2,041 kg, 5 998 kg; 370-gal tanks on 4/6, bombs on 3/7, missiles on 1/9 and 2/8 | published station data |
| Mk 82 | 2.22 m long, 273 mm diameter, 227–241 kg, 87–89 kg of tritonal / H-6 / PBXN-109; conical fin (MAU-93/B or BSU-33) | Wikipedia "Mark 82 bomb"; ordnance manuals |
| Mk 83 | 3.00 m long, 357 mm diameter, 447–460 kg, 202 kg of filling | Hellenic Air Force; Wikipedia "Mark 83 bomb" |
| Mk 84 | 3.28 m long, 458 mm diameter, 925 kg, 429 kg of tritonal; 30-inch lug spacing | Wikipedia "Mark 84 bomb" |
| **Mk 82 effects** | crater 4.6–10.7 m wide; 117 kPa at 16 m, 34 kPa at 31 m; destroys reinforced-concrete buildings within 16 m | GICHD, citing Ordtech |
| **Mk 84 crater** | 15 m wide, 11 m deep | Wikipedia "Mark 84 bomb" |

Shapes and proportions follow photographs on Wikimedia Commons (an F-16C in flight from above and
from below, Mk 82s on an F-16 pylon, a Mk 82 in profile, Mk 83s on a trolley).

**Not from sources (illustration)**

* **The load.** One of each is carried for the comparison; a real sortie carries pairs or multiples
  of one type. A Mk 84 fits the centre-line station's 998 kg limit on paper, but F-16s carry their
  Mk 84s on the wing stations (3 and 7); the centre line normally takes a tank or a pod. The Mk 83
  is cleared for the F-16 but is mainly a Navy / Marine Corps bomb.
* **Mk 83 and Mk 84 radii** (21 m / 41 m and 27 m / 53 m) are the Mk 82's published 16 m and 31 m
  scaled by the cube root of the filling. They are estimates, and the film marks them "≈" and says
  they are scaled. The Mk 83 crater range in the closing table is an estimate too.
* The aircraft model: the blended wing-body, canopy, intake, nozzle, pylons and tanks are
  proportioned by eye from the photographs. It has a pilot's helmet and seat under a tinted canopy,
  a gun port, formation-light strips, hinge lines for the flaps, flaperons and rudder, low-visibility
  insignia and a made-up tail number — but no landing gear (retracted), no panel lines, no airbrake
  or nozzle petal detail, and a simplified three-tone grey paint scheme. Station positions (1.80 m,
  3.05 m and 3.99 m from the centre line) are estimates.
* Level release at 450 kt and 1,500 m is one plausible unguided delivery, not a quoted profile; real
  ripple intervals are usually 0.1–0.3 s — 0.6 s is used here to put the bombs on separate bunkers.
* The fall is a point mass with a small constant drag (17.5 s, 3.9 km of throw, about 272 m/s and 38°
  at impact for all three). It is not a bombing table.
* What each bomb does to its bunker follows the general published picture — general-purpose bombs
  crater, spall and hole hardened structures — but which roof bays fail and where the pieces go is
  staging: a holed roof for the Mk 82, a roof broken open for the Mk 83, the whole roof gone for the
  Mk 84. No penetration figure is from a test.
* Fireball size and duration, cloud size and colour come from the simulation (scaled by the cube
  root of the filling) and general footage. The 1.8 m figure in the introductions is a drawn
  pictogram for scale.
* The bunkers and the place are invented.

## Files

- `vconst.py` — speeds, heights, the three bomb trajectories, published and scaled radii (no bpy).
- `vf16.py` — the F-16 (fuselage, blended strakes, intake, canopy and cockpit, wing, tail, nozzle,
  pylons, tanks, AIM-120s, AIM-9s, markings) and the three bombs.
- `vsim.py` — the Mantaflow burst, sized for each bomb.
- `vshots.py` — the bunkers, the studio and scene shots and the frame renderer.
- `vpost.py` — title card, HUD, the per-bomb chapters, the closing table, sound, encode.
- `vlook.py` — renders the jet and the bombs from several directions (model check).
- `render_all.py` — bakes the three bursts if needed, renders every shot (resumable) and runs post.

Mesh helpers and the smoke-column effect come from `../reaper-hellfire/`; overlay and sound helpers
from `../grenade-explosion/` and `../blackhawk-mk77/`.

```
pip install bpy numpy pillow scipy    # Blender as a Python module (Python 3.13), plus ffmpeg on the PATH
RENDER_DEVICE=GPU python3 f16-mk8x/render_all.py <frames_root> <sim_root> [out.mp4]
```
