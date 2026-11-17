# Explosion Comparison · 05 — MQ-9 Reaper and the AGM-114 Hellfire on an armed pickup

Fifth segment of the series. A US Air Force MQ-9A Reaper cruises at 20,000 ft over a Middle-Eastern
desert. Its sensor ball holds a laser on an armed pickup ("technical") coming up a track 7.6 km away;
one AGM-114R Hellfire leaves the launcher under the left wing, flies for about 23 seconds and strikes
the pickup. Everything is procedural (Blender as a Python module, Cycles) and shares the terrain,
render setup, burst effects and post tools with the earlier segments. Nobody is modelled in or
around the vehicle.

| # | Shot | What it shows | Speed |
|---|------|---------------|-------|
| 1 | `card`   | The Reaper on a studio backdrop + spec panel | – |
| 2 | `cruise` | The aircraft on station at 20,000 ft, camera drifting from the nose round to the beam | real time |
| 3 | `launch` | Under the left wing: the motor lights, the missile runs off the rail and pulls ahead | real time, then 5× and 2.5× slow |
| 4 | `target` | The sensor operator's picture (shown as a white-hot infra-red image): the pickup comes up the track and stops | real time |
| 5 | `fly`    | Chase camera riding down behind the missile for its last three seconds | real time |
| 6 | `impact` | Beside the track: the hit, the burst, the fuel fire, parts thrown clear | 5× slow, then 2.5× |
| 7 | `radius` | From the air: the published kill and wounding radii drawn on the sand | 5× slow, then 2.5× |
| 8 | `after`  | Half a minute later: the wreck burning under black smoke; crane up | real time |

## What is sourced and what is not

**From sources**

| Item | Value | Source |
|------|-------|--------|
| MQ-9A Reaper | wingspan 66 ft (20.1 m), length 36 ft (11 m), height 12.5 ft (3.8 m), Honeywell TPE331-10GD turboprop, 900 shp; armament includes AGM-114 Hellfire and GBU-12 Paveway II | US Air Force fact sheet "MQ-9 Reaper" |
| Cruise and altitude | cruise 169 kt; operational altitude 25,000 ft, ceiling 50,000 ft | Wikipedia "General Atomics MQ-9 Reaper" |
| Wing area | 25.35 m² (mean chord 1.26 m) | Reitsma et al., *Aerospace* (MDPI) – single source |
| Stores | six wing stations (seven with the centre line): inboard 1,500 lb, middle 600–750 lb, outboard 150–200 lb; typical load two GBU-12 inboard and two Hellfires on a dual-rail launcher on each middle station | NAVAIR "MQ-9A Reaper", Wikipedia |
| Sensor ball | MTS-B, 22 in (0.56 m) turret with electro-optical / infra-red cameras and laser designator | Raytheon data sheet |
| Propeller | three blades (four on the Extended Range version) | US Air Force fact sheet |
| AGM-114R Hellfire II | length 163 cm (64 in), diameter 178 mm (7 in), wingspan 0.33 m, 49 kg, 9 kg (20 lb) multi-purpose warhead, semi-active laser homing, Mach 1.3 (about 450 m/s), about 8 km reach | Lockheed Martin product card; CSIS Missile Threat; Wikipedia "AGM-114 Hellfire" |
| Accuracy | circular error probable under 3 ft (0.9 m) | Wikipedia "AGM-114 Hellfire" |
| **Effect radii** | **kill radius 15 m, wounding radius 20 m** | G. Chamayou, *A Theory of the Drone*; repeated by the BBC |
| Engagement | launch from about 20,000 ft at a slant range of 4–5 miles; flight time reported between about 25 s and "almost a minute" | Air University paper on Predator operations; broadcast reporting |
| Motor | minimum-smoke solid motor, single nozzle; burns for 2–3 s | manufacturer data sheet / secondary sources |

Shapes and proportions follow US Air Force photographs (Wikimedia Commons: an MQ-9 taxiing in
Afghanistan, 2007; front and rear views of armed aircraft) and the Lockheed Martin display model of
the Hellfire: the bulged nose over the satellite antenna and the darker lower nose; the slender
low-set straight wing with actuator fairings; the long V-tail (about 35° above horizontal in the
photographs) with a ventral fin; the engine air scoop on the rear spine and the oval exhaust duct
above the polished spinner; the sensor ball under the chin; pylons at about 1.3 m and 2.15 m from
the centre line (measured off the head-on photograph). The Hellfire has the hemispherical glass
seeker dome, four short forward strakes, four wide-chord wings with control fins at their trailing
edges, launch shoes, and the yellow (high explosive) and brown (rocket motor) bands on a black body.

**Not from sources (illustration)**

* Fuselage sections, chords, tail sizes and pylon shapes are estimated from the photographs; the
  landing gear is retracted and not modelled; fine detail (panel lines, antennas, markings, the
  launcher mechanism) is simplified. The GBU-12 bombs are simple shapes.
* The fly-out is a prescribed smooth path from the launcher to the target with the speed of a
  point-mass model (boost to about Mach 1.3, then drag and gravity). It gives 7.6 km in 22.7 s,
  arriving at about 295 m/s and 58°. It is not a guidance simulation and not a firing solution.
* 20,000 ft and 7.6 km are one plausible engagement, not a quoted one.
* The pickup, its gun, how it breaks up, the size and colour of the fireball and cloud, how far the
  parts fly and how the wreck burns come from this simulation and from general footage of such
  strikes, not from test data. The smoke trail and the later smoke column are procedural.
* The sensor picture is the ordinary render shown in monochrome with a reticle; it is not a
  simulated infra-red image, and the symbology is invented.
* The place is invented; it is not a real location or a real strike.

## Files

- `qconst.py` — engagement geometry, timing, the missile path and speed model (no bpy).
- `qgeo.py` — mesh helpers: lofts, airfoil surfaces, bodies of revolution, plates.
- `qmq9.py` — the Reaper: fuselage, wing, V-tail, engine fairing, propeller, sensor ball, pylons, launchers, GBU-12s.
- `qhell.py` — the Hellfire and its motor flame.
- `qtruck.py` — the pickup, its wreck and the parts thrown clear.
- `qenv.py` — the desert at ground level with the vehicle track, and the same desert from altitude.
- `qsim.py` — the Mantaflow gas sim of the strike (burst, fuel fire, sand, burning wreck).
- `qshots.py` — the eight shots, the smoke trail and smoke column, and the frame renderer.
- `qpost.py` — title card, HUD, sensor picture, sound, encode.
- `qlook.py` — renders the aircraft from several directions on a plain background (model check).
- `render_all.py` — bakes the sim if needed, renders every shot (resumable) and runs post.

```
pip install bpy numpy pillow          # Blender as a Python module (Python 3.13), plus ffmpeg on the PATH
RENDER_DEVICE=GPU python3 reaper-hellfire/render_all.py <frames_root> <sim_root> [out.mp4]
```

Without `RENDER_DEVICE=GPU` the shots render on the CPU. Each render process prints the device it
picked (`RENDER_DEVICE: OPTIX on ...`). The frames and the simulation cache are a couple of GB; keep
them outside the repository.
