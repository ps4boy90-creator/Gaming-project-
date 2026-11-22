# Explosion Comparison · 08 — Tomahawk cruise missile from a submarine onto a factory in the desert

Eighth segment of the series. A Los Angeles-class attack submarine in the Arabian Sea opens one of the
twelve launch tubes in its bow and fires a UGM-109E Tomahawk Block IV. Gas throws the missile out of the
tube, its rocket booster lights under water and drives it through the surface; the tail shrouds come off,
three fins and then the wings swing out, the booster burns out and falls away, and a small turbofan takes
over. The missile crosses the coast thirty metres up, follows the desert hills, climbs, dives on a small
factory and bursts inside it. Everything is procedural (Blender as a Python module, Cycles) and shares the
render setup, burst effects and post tools with the earlier segments. Nobody is modelled anywhere.

**Afghanistan has no coast.** Tomahawks reach it from the Arabian Sea across Pakistan, as they did on
20 August 1998 and from 7 October 2001. The film says so; the factory, the country round it and the strike
itself are invented.

| # | Shot | What it shows | Speed |
|---|------|---------------|-------|
| 1 | `card`     | The missile in cruise trim on a studio backdrop + spec panel | – |
| 2 | `depth`    | The submarine under water, seen from off its bow | real time |
| 3 | `hatch`    | Close over the bow: one of the twelve tube doors opens | real time |
| 4 | `eject`    | The missile is thrown out by gas; the booster lights; it climbs to the surface | about 3× slow |
| 5 | `broach`   | From the surface: it bursts out of the sea, sheds its shrouds, fins out, climbs away | half speed, then real time |
| 6 | `wings`    | Alongside: the inlet cover drops and the wings swing out | real time |
| 7 | `boost`    | Burn-out, the booster dropped, the turbofan takes over | real time |
| 8 | `landfall` | Thirty metres over the sea, the coast ahead | real time |
| 9 | `cruise`   | Following the ground over desert hills | real time |
| 10 | `terminal` | Riding down behind it in the dive on to the factory | real time |
| 11 | `impact`  | Through the roof; the warhead fires inside | 2.5× slow, then 1.25× |
| 12 | `radius`  | From the air, with the two radii | about 1.5× slow |
| 13 | `after`   | Half a minute later | real time |
| 14 | summary   | The missile's figures (made in post) | – |

## What is sourced and what is not

**From sources**

| Item | Value | Source |
|------|-------|--------|
| Tomahawk Block IV | 5.56 m long, 6.25 m with the booster; 0.52 m diameter; 2.67 m span; 1,315 kg, 1,588 kg with the booster | US Navy fact file; NAVAIR; GlobalSecurity; Wikipedia |
| Flight | about 880 km/h; 30–50 m above the ground; range about 1,600 km; INS, GPS, terrain matching (TERCOM) and scene matching (DSMAC); about 10 m accuracy | same |
| Propulsion | Williams F415 turbofan (the earlier F107 gave about 3.1 kN); Mk 135 solid rocket motor; booster about 26.7 kN for about 12 s | NAVAIR; designation-systems.net |
| Airframe details | three tail fins (earlier blocks had four) that swing out in about a quarter of a second; a flush engine inlet with a cover that is thrown off; for submarine launch, plugs in the wing slots and "continuity shrouds" between missile and rocket motor | TACTOM system manual SW820-AP-MMI-010 |
| Launch sequence | gas generator in the capsule → first motion → the booster lights once the missile has left the tube → thrust-vector steering to the surface → at broach the wing-slot plugs go, the shrouds separate and the fins deploy → after a speed check the inlet cover goes and the wings deploy → about 14 s after first motion the thrust decays, the rocket motor is dropped and the engine starts | same manual |
| Warhead | WDU-36/B, about 310 kg (some sources 340 kg), about 120 kg of PBXN-107, FMU-148 fuze; the Navy calls it "1,000 lb class" | Wikipedia; ARES / OSMP; FAS |
| Dive | a 60° commanded dive on the target in a 2007 Navy test | NAVAIR news release, 29 March 2007 |
| Submarine | Los Angeles class: 109.7 m long, 10.06 m beam; boats from SSN-719 on have twelve vertical launch tubes in the bow, two inner rows of four and two outer rows of two; Flight II boats keep the planes on the sail | US Navy fact file; Naval Encyclopedia; Wikipedia |
| History | 20 Aug 1998: about 73 Tomahawks at the Khost camps from ships and USS Columbia in the Arabian Sea. 7 Oct 2001: about 50 from US ships, USS Providence and HMS Triumph and Trafalgar | Naval History and Heritage Command; Wikipedia |
| **Mk 82 effects** (the yardstick) | 117 kPa at 16 m, 34 kPa at 31 m; reinforced-concrete buildings destroyed within 16 m (87 kg of filling) | GICHD, citing Ordtech |

Shapes follow a US Navy photograph of a Block IV in flight (straight wings just behind mid-length, one
fin up and two down, blunt rounded nose with a dark band) and a photograph of USS Santa Fe with her
launch-tube doors open.

**Not from sources (illustration)**

* **Blast radii (about 18 m and 35 m)** are the Mk 82's published figures scaled by the cube root of
  the filling (120 kg against 87 kg). They are estimates, the film marks them "≈" and says they are
  scaled. PBXN-107 and the Mk 82's tritonal are not the same explosive; no allowance is made for that.
* **What happens to the factory** — roof and walls blown out, the frames nearest the burst thrown down,
  the office, chimney and yard wall left standing — follows what a charge of this size does inside a
  light building, but which piece goes where is staging. The fuze delay (firing two metres above the
  floor) is assumed.
* **The launch numbers.** Launch depth is not published; the hull is drawn with its top about 11 m
  under. The speed out of the tube, the moment of ignition (0.62 s), the time to the surface (0.83 s),
  the times of fin and wing deployment and the climb to about 550 m are a plausible kinematic model
  built round the published 12 s burn and the manual's order of events, not telemetry.
* **The route** (about 1,200 km, about 80 minutes) and the terminal profile (a pop-up to 900 m, turns of
  about 3 g, a 55° dive) are illustrative. Real routes and profiles are planned per mission.
* **The missile model.** Body sections, wing chord, fin size and the fins' fold are proportioned by
  eye; the fins are drawn folding aft under the shroud. Paint is plain grey without stencils.
* **The submarine model.** Hull lines, the sail, control surfaces and the towed-array fairing are
  proportioned from photographs. The real propeller's shape is not public; a plain seven-bladed one
  stands in. No masts are raised.
* **Under water** the visibility is far better than in the real sea, so that the submarine can be seen
  whole. Bubbles, spray, foam and the booster's smoke are hand-built effects, not simulations.
* The desert and the coast are procedural and are not real places.
* The sound is synthesized.

## Files

- `tconst.py` — published figures, the launch model, the terminal dive, radii (no bpy).
- `ttlam.py` — the Tomahawk: body, folding wings and fins, booster, shrouds, plugs, inlet cover, flame.
- `tsub.py` — the Los Angeles-class submarine with its twelve tubes and one opening door.
- `tsea.py` — sea surface, the water from below, bubbles, spray, foam, smoke trail.
- `tland.py` — the desert hills, the terrain-following track, the coast.
- `tfac.py` — the factory, built from loose panels so that it can come apart.
- `tsim.py` — the Mantaflow burst inside the hall.
- `tshots.py` — the thirteen render shots and the frame renderer.
- `tpost.py` — title card, captions, closing table, sound, encode.
- `tlook.py` — renders the missile and the submarine from several directions (model check).
- `render_all.py` — bakes the burst if needed, renders every shot (resumable) and runs post.

Mesh helpers and the puff-cloud effect come from `../reaper-hellfire/`; overlay and sound helpers from
`../grenade-explosion/` and `../blackhawk-mk77/`.

```
pip install bpy numpy pillow scipy    # Blender as a Python module (Python 3.13), plus ffmpeg on the PATH
RENDER_DEVICE=GPU python3 tomahawk-sub/render_all.py <frames_root> <sim_root> [out.mp4]
```
