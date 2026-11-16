# Explosion Comparison · 04 — M777 155 mm howitzer (M795 HE) on a war-damaged town

Fourth segment of the series. Six "Ghost Men" (the transparent figures) serve a US M777 howitzer: they
load an M795 high-explosive shell and its propelling charge, the gunner lays the tube, the section
chief gives the signal and cannoneer 1 pulls the lanyard. Forty-eight seconds later the shell lands
in a street of a war-damaged Middle-Eastern town, 3 m from a house front. Everything is procedural
(Blender as a Python module, Cycles) and shares terrain, figure, render setup and post tools with the
earlier segments.

| # | Shot | What it shows | Speed |
|---|------|---------------|-------|
| 1 | `card`   | The howitzer and a shell on a studio backdrop + spec panel | – |
| 2 | `load`   | Breech opens, loading tray swings in, two cannoneers bring up the shell and slide it onto the tray | real time |
| 3 | `ram`    | The two cannoneers drive the shell home with the rammer staff | real time |
| 4 | `charge` | Five-increment propelling charge loaded, tray out, breech closed, lanyard hooked | real time |
| 5 | `fire`   | Tube laid from loading elevation to the firing data, chief's signal, lanyard pulled; muzzle blast and recoil | real time, then 5× slow |
| 6 | `fall`   | Chase camera riding down behind the shell for its last three seconds | real time |
| 7 | `impact` | Down the street: the burst, then the house front and floor slabs coming down | 5× slow, then 2.5× |
| 8 | `radius` | From the air: fragment strikes spreading, the published lethal and casualty radii drawn on the town | 5× slow, then 2.5× |
| 9 | `after`  | The crater and the opened house; crane up over the roofs | – |

## What is sourced and what is not

**From sources**

| Item | Value | Source |
|------|-------|--------|
| M777 | 155 mm, 4.2 t, crew 8 (5 minimum), split trail, titanium structure, loading tray | Wikipedia "M777 howitzer" (BAE / US Army data) |
| Muzzle velocity | 827 m/s at top charge | same |
| Carriage layout | cradle of four extruded titanium tubes with an accumulator, two recoil cylinders and balancing gear; body with two forward stabilisers and two split trails with self-digging spades and dampers; a hydrogas suspension unit with a road wheel on each side | Army Guide, "M777 (towed howitzer)" |
| M795 projectile | 103 lb (46.7 kg), 33.2 in (843 mm) with fuze, 23.8 lb (10.8 kg) TNT, max range 22.5 km | General Dynamics OTS brochure |
| Crew drill | cannoneer 1 opens the loading tray; cannoneer 2 opens the breech; cannoneers 4 and 5 load and ram the round; cannoneer 2 loads the charge and closes the breech; on the section chief's order cannoneer 1 hooks the lanyard and fires; gunner and assistant gunner lay the piece | DVIDS, "On the gun line with cannon cockers" (US Marine Corps) |
| **Effect radii** | expected **lethal radius 50–150 m**, expected **casualty radius 100–300 m** for a 155 mm HE projectile | Human Rights Watch (2007, 2009), repeated in UN reporting |
| M795 "kill radius" | about 50 m, fragments spreading significantly further | Article 36, explosive-weapons harm table |
| M67 grenade (scale ring) | 15 m casualty radius | segment 01 |

The rings in the aerial shot are drawn at the **lower bounds** (50 m and 100 m) of those ranges.

Shapes and proportions (low body, A-frame saddle, the four cradle tubes and their yokes, muzzle
brake with towing eye, swing-up breech, loading tray, flat stabilisers with pads, splayed trails
with their spades, the raised road wheels, sight and handwheels; the boat-tailed shell with its
rotating band, yellow markings and fuze) are modelled from six public photos of the gun in US
service. Where a part cannot be seen in them (the breech mechanism, the tray's mounting, the far
side of the carriage) it is a plausible stand-in, not a measured copy.

**Not from sources (illustration)**

* The trajectory is a point-mass model whose drag level is scaled to reproduce the published
  22.5 km maximum range at 827 m/s. For the 18 km shot it gives about 24° (427 mils) elevation,
  48 s of flight, a 3 km apex and an arrival at about 306 m/s and 43°. It is not a firing-table solution.
* Loading is shown with the tube at a low loading elevation and then laid to the firing elevation;
  the exact elevations, timings, positions of the crew members and which side each one stands on
  are staging. The lanyard side and the tray's swing direction are assumptions.
* The recoil length (1.25 m), the size of the cloud, the crater, how much of the house comes down
  and where each fragment mark lands come from this simulation, not from test data.
* The town is invented; it is not a real place.

## Files

- `hconst.py` — shared geometry, timing and the calibrated trajectory model (no bpy).
- `h777.py` — the howitzer with moving cradle, recoiling tube, breech and loading tray; the M795
  shell, the MACS charge and the rammer staff.
- `hcrew.py` — the six-man drill: every body pose, hand hold and handled object as a function of time.
- `htown.py` — the town generator (block-course houses, slabs, rubble, wrecks, poles, palms,
  minaret), the struck house with its collapse, and the gun position.
- `hsim.py` — the two Mantaflow gas sims (muzzle blast, detonation and collapse dust).
- `hshots.py` — the nine shots and the frame renderer.
- `hpost.py` — title card, HUD, sound, encode.
- `render_all.sh` — bakes the sims if needed, renders every shot (resumable) and runs post.

```
./render_all.sh <frames_root> <sim_root> [out.mp4]
```
