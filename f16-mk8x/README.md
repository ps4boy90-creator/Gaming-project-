# Explosion Comparison · 07 — F-16 with a Mk 82 and a Mk 83 on two bunkers

Seventh segment of the series. An F-16C runs in level at 450 kt and 1,500 m over a desert, releases
a Mk 82 (500 lb class) from under its left wing and, 0.6 seconds later, a Mk 83 (1,000 lb class) from
under its right wing. The bombs fall for 17.5 seconds and land on two reinforced-concrete bunkers
153 m apart. The two bursts are then shown side by side at the same scale. Everything is procedural
(Blender as a Python module, Cycles) and shares the terrain, render setup, burst effects and post
tools with the earlier segments. Nobody is modelled in the aircraft or the bunkers.

| # | Shot | What it shows | Speed |
|---|------|---------------|-------|
| 1 | `card`      | The F-16 with its load on a studio backdrop + spec panel | – |
| 2 | `approach`  | Air to air: the jet running in | real time |
| 3 | `release`   | From ahead and below: the Mk 82 leaves the left wing, then the Mk 83 the right | real time, then 4× slow |
| 4 | `fall`      | The camera rides down behind the Mk 82 for its last 2.6 seconds | real time |
| 5 | `impact82`  | The Mk 82 on the roof of the first bunker | 2.5× slow, then 1.25× |
| 6 | `impact83`  | The Mk 83 on the second bunker (camera further back in proportion) | 2.5× slow, then 1.25× |
| 7 | `radius82` + `radius83` | Both bursts from the air, same camera and scale, shown side by side with their radii | about 1.5× slow |
| 8 | `after`     | Half a minute later: both bunkers in one view | real time |

## What is sourced and what is not

**From sources**

| Item | Value | Source |
|------|-------|--------|
| F-16C | length 15.03 m; span 9.45 m over the tip launchers (9.14 m theoretical); height 5.09 m; wing area 27.87 m² | aerospaceweb; USAF TO 00-105E-9 |
| Wing | leading-edge sweep 40°, trailing edge unswept, no dihedral, taper 0.2275, NACA 64A204 (4 % thick); centre-line root chord 4.97 m, tip 1.13 m | NASA TP; JSBSim model data |
| Tail | stabilator span 5.58 m, 40° sweep, 10° anhedral; fin 2.57 m exposed height, 47.5° sweep; two ventral fins canted 15° | same |
| Stations | nine; limits 1/9 193 kg, 2/8 318 kg, 3/7 1,588 kg, 4/6 2,041 kg, 5 998 kg; 370-gal tanks on 4/6, bombs on 3/7, missiles on the tips | published station data |
| Mk 82 | 2.22 m long, 273 mm diameter, 227–241 kg, 87–89 kg of tritonal / H-6 / PBXN-109; conical fin (MAU-93/B or BSU-33) | Wikipedia "Mark 82 bomb"; ordnance manuals |
| Mk 83 | 3.00 m long, 357 mm diameter, 447–460 kg, 202 kg of filling | Hellenic Air Force; Wikipedia "Mark 83 bomb" |
| Mk 83 on the F-16 | cleared, but rare on US Air Force F-16s (the Mk 83 is mainly a Navy / Marine Corps bomb; the Hellenic Air Force lists it for its F-16s) | Wikipedia; aerospaceweb |
| **Mk 82 effects** | crater 4.6–10.7 m wide; 117 kPa at 16 m, 34 kPa at 31 m; destroys reinforced-concrete buildings within 16 m | GICHD, citing Ordtech |
| Risk distance | Mk 82 425 m, Mk 83 475 m (0.1 % chance of incapacitation by fragments) | GICHD; Article 36 / PAX |

Shapes and proportions follow photographs on Wikimedia Commons (an F-16C in flight from above and
from below, Mk 82s on an F-16 pylon, a Mk 82 in profile, Mk 83s on a trolley).

**Not from sources (illustration)**

* The one-of-each load is for the comparison; a real sortie would carry pairs or multiples of one type.
* Fuselage sections, the canopy, intake, nozzle, pylons and tanks are proportioned by eye from the
  photographs. The landing gear is retracted and not modelled; there is no pilot, gun port, panel
  lines, lights or markings; the paint is a simplified two-tone grey.
* Station positions (1.80 m and 3.05 m from the centre line) are estimates.
* Level release at 450 kt and 1,500 m is one plausible unguided delivery, not a quoted profile; real
  ripple intervals are usually 0.1–0.3 s — 0.6 s is used here to put the bombs on separate bunkers.
* The fall is a point mass with a small constant drag (17.5 s, 3.9 km of throw, about 272 m/s and 38°
  at impact). It is not a bombing table.
* **Mk 83 radii (21 m and 41 m) are the Mk 82's published 16 m and 31 m scaled by the cube root of
  the filling.** They are estimates, and the film labels them as scaled.
* What each bomb does to its bunker follows the general published picture — general-purpose bombs
  crater, spall and hole hardened structures and rarely destroy them — but which roof bays fail and
  where the pieces go is staging. No penetration figure is from a test.
* Fireball size and duration, cloud size and colour come from the simulation and general footage.
* The bunkers and the place are invented.

## Files

- `vconst.py` — speeds, heights, the two bomb trajectories, published and scaled radii (no bpy).
- `vf16.py` — the F-16 (fuselage, intake, canopy, wing, strakes, tail, nozzle, pylons, tanks, AIM-120s) and the two bombs.
- `vsim.py` — the Mantaflow burst, sized for either bomb.
- `vshots.py` — the bunkers, the nine render shots and the frame renderer.
- `vpost.py` — title card, HUD, the side-by-side comparison, sound, encode.
- `vlook.py` — renders the jet and the bombs from several directions (model check).
- `render_all.py` — bakes the two bursts if needed, renders every shot (resumable) and runs post.

Mesh helpers and the smoke-column effect come from `../reaper-hellfire/`; overlay and sound helpers
from `../grenade-explosion/` and `../blackhawk-mk77/`.

```
pip install bpy numpy pillow scipy    # Blender as a Python module (Python 3.13), plus ffmpeg on the PATH
RENDER_DEVICE=GPU python3 f16-mk8x/render_all.py <frames_root> <sim_root> [out.mp4]
```
