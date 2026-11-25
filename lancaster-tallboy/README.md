# Explosion Comparison · 11 — Tallboy from an Avro Lancaster on a German army depot

Eleventh segment of the series, and the first set in the Second World War. An Avro Lancaster of
1944, 18,000 ft up at 200 mph, opens its bulged bomb doors and releases one Tallboy, Barnes Wallis's
12,000 lb "earthquake" bomb. The bomb falls for 34 seconds, spinning on its offset fins, and reaches
the yard of a German army depot at about 329 m/s, just under the speed of sound. It goes some 16 m
into the ground and stops; half a second later its fuze fires 2,360 kg of Torpex under the yard. The
film shows the burst from just above the ground and from the air with its radii, as the other bomb
segments do, and then the crater. Everything is procedural (Blender as a Python module, Cycles) and shares
the render setup, effects and post tools with the earlier segments. Nobody is modelled anywhere, and
there are no flags or insignia on the depot.

**Status: draft only.** The code is complete and has been rendered end to end as a low-resolution
draft on a CPU (640×360, 6 samples, a coarse simulation). The 1080p render on a GPU is still to do,
so there is no `renders/` folder here yet.

**The depot and the strike are invented.** How deep the bomb goes is calculated; the crater's width
and the radius for brick buildings are published ones; the 5 psi radius is scaled from the Mk 82's,
as in segment 07.

| # | Shot | What it shows | Speed |
|---|------|---------------|-------|
| 1 | `card`     | The bomb turning on a studio backdrop + spec panel | – |
| 2 | `approach` | The Lancaster on its run-up; the bomb doors open on the bomb | real time |
| 3 | `intro`    | The bomb with its dimensions, a 6 m lorry beside it for scale | – |
| 4 | `release`  | The links let go; the bomb drops and begins to turn | real time, then half speed |
| 5 | `fall`     | Riding down behind the bomb through its last 3.5 s | real time |
| 6 | `impact`   | From a watch tower's height, 220 m off: into the yard; half a second later the yard is thrown into the air | 2.5× slow, then 1.25× |
| 7 | `radius`   | From the air: the burst and its circles, with a Mk 84's for comparison | about 1.5× slow |
| 8 | `after`    | Half a minute later: the crater and the wrecked buildings round it | real time |
| 9 | summary    | Table of the numbers (made in post) | – |

## The numbers in the film

Release: level at 200 mph (89 m/s), 18,000 ft (5,486 m) above the target. The bomb falls 33.7 s
and travels about 3 km forward. It arrives at **329 m/s (1,081 ft/s, about 1,190 km/h, Mach 0.97)**
on a path 75° below the horizontal, turning at about 300 rpm. Published for the same release:
1,097 ft/s (334 m/s) and 300 rpm; one source gives 37 s for the fall, which does not agree with that
speed (a fall that slow would arrive slower).

In the ground (moist clay and loam): about 17 m along its path, 16 m down, in about 0.1 s. The fuze
fires at 0.5 s with the middle of the charge about 14 m down. For 2,360 kg of Torpex that is close
to the depth at which a buried charge throws out the widest crater.

| Circle in the radius shot | Radius | Basis |
|---|---|---|
| Crater | 15 m (100 ft across) | published |
| Brick wall-bearing buildings demolished | about 37 m (120 ft) | published as a rough estimate, for a burst at ground level |
| 5 psi (34 kPa) blast | about 93 m | the Mk 82's 31 m × cube root of the fillings' ratio; for a burst at the surface |
| Mk 84, 5 psi, for comparison | about 53 m | as in segment 07 |

## What is sourced and what is not

**From sources**

| Item | Value | Source |
|------|-------|--------|
| Tallboy | 21 ft over all: body 10 ft 4 in, tail 10 ft 8 in; 38 in across the body and 3 ft 6 in across the fins; total weight 11,885 lb; "green over-all; red band near nose"; "about 12,000 lb"; 5,200 lb of Torpex topped with TNT; one-piece cast steel case with a solid nose; No. 78 tail of light alloy with four fins set at 5° for a right-hand spin; three No. 58 tail pistols in the base plate; no lug: twin suspension links coupled beneath the bomb by a release clip | US Navy OP 1665, *British Explosive Ordnance* (1946); Bomber Command Museum of Canada; Australian War Memorial |
| Fall | released at 18,000 ft and 200 mph: striking velocity 1,097 ft/s, spin 300 rpm; 37 s of fall | OP 1665; Bomber Command Museum of Canada |
| Fuze delays | 0.5 s and 11 s on the Tallboys that hit the Brest U-boat bunker | US Strategic Bombing Survey, Physical Damage Division |
| Crater | 100 ft across and 80 ft deep | Wikipedia, "Tallboy (bomb)" (not traced further) |
| Damage to buildings | "rough estimates of the distance from detonations at ground level ... at which brick wall-bearing buildings will be demolished": about 120 ft for the 12,000 lb bomb, about 150 ft for the 22,000 lb bomb; also a crater 88 ft across for a 12,000 lb bomb burst 16.5 ft down | Th. von Kármán, *Explosives and Terminal Ballistics* (1946) |
| Against concrete | 5 ft 7 in (1.7 m) into reinforced concrete at maximum striking velocity (Farge, 1946); at Brest nine direct hits, none through the roof before bursting | Project Ruby report (quoted second-hand); US Strategic Bombing Survey |
| Lancaster | span 102 ft; length 69 ft 6 in; wing area about 1,300 sq ft; root chord 16 ft, chord at the tip joint 9 ft 2 9/16 in; NACA 23018 to 23012; outer panels at 7° dihedral; tailplane 33 ft; track 23 ft 9 in; bomb bay 33 ft; three-blade propellers 13 ft across; bulged doors for the Tallboy; mid-upper turret still fitted in August 1944; code KC for No. 617 Squadron | lancaster-archive.com; Wikipedia, "Avro Lancaster"; avrolancaster.co.uk; IBCC Digital Archive |
| Penetration equations | Young, *Penetration Equations*, Sandia report SAND97-2426 (1997) | the report |
| Mk 82 radii | 16 m (buildings), 31 m (5 psi) | as in segment 07 (GICHD / Ordtech) |

**Not from sources (calculated or illustration)**

* **The depot.** Barrack blocks, garages, stores, a headquarters block, watch towers, a fence and
  a dozen 3-ton lorries round a gravel yard. It is a stand-in for "a German army base of 1944", not
  a real place. Tallboys were in fact kept for targets that ordinary bombs could not break: railway
  tunnels and viaducts, U-boat and E-boat bunkers, V-weapon sites, the battleship *Tirpitz*. None
  was spent on a depot like this one.
* **How deep the bomb goes.** Calculated with Young's equation for soil. Guesses: the soil number
  (S = 7, moist clay and loam) and that the bomb stays whole and straight; the length of the nose
  (1.65 m) is measured off the photographs. For reinforced concrete at 1,150 ft/s the same equation
  gives 1.8 m, close to the 1.7 m of the 1946 trials.
* **The 5 psi circle.** Scaled from the Mk 82's published radius by the cube root of the
  fillings' weights, exactly as segment 07 does for the Mk 83 and Mk 84. It takes no account of
  Torpex being stronger than tritonal. Like the published radius for brick buildings, it is for a
  burst at the surface: a charge 14 m down sends less of its force into the air and more into the
  ground. The film says so on screen.
* **The burst.** That a charge at this depth throws up earth rather than flame, and leaves a crater
  about 30 m across, follows the published crater and the general behaviour of buried charges. The
  height and speed of the column, how long the earth takes to fall, which buildings come down (those
  within about 53 m) and how the lorries are thrown are staging. The simulation is driven by
  hand-placed sources. The crater is drawn 9 m deep; the published 80 ft would include the broken
  ground beneath it.
* **The fall.** A point mass with an estimated drag curve (0.10, rising towards Mach 1). It gives
  1,081 ft/s against the published 1,097.
* **The bomb model.** Lengths, widths and weight are OP 1665's. The outline between them is drawn
  to two wartime photographs (IWM CH 15363, a Tallboy being slung; IWM CH 15369, a Grand Slam, the
  same design made larger): the pointed ogival nose about 1.7 body widths long, the body narrowing
  to about four fifths of its width at the joint, a dark band at the joint, a light-coloured tail
  that swells slightly and runs out nearly to a point, and four short swept fins set a little
  forward of that point. "TORPEX D1" is stencilled round the body as in the Tallboy photograph; the
  red band is put where that photograph shows a light ring round the point of the nose. The exact
  greens and the grey of the tail are guesses (the photographs are black and white), as are the
  place of the three hand-holes and of the tail's number, which are taken from the Grand Slam.
* **The Lancaster model.** Section shapes, the outlines of nose, canopy, nacelles and fins, the
  place of the outer engines (7.55 m from the centre line) and of the turrets are proportioned
  from drawings and photographs. Camouflage (Dark Green and Dark Earth over Night), roundels (Type
  C1 on the fuselage, Type B above the wings), fin flash and red codes follow the usual Bomber
  Command scheme and were not checked against a particular aircraft; "KC-A" is not meant as one.
  The landing gear is up; there are no panel lines, aerials, exhaust flames or crew. The shape and
  swing of the suspension links are a guess from the one-line description in OP 1665.
* **The sound** is synthesized.

## Files

- `lconst.py` — published figures, the fall, Young's equation, the radii (no bpy; `python3 lconst.py` prints the numbers above).
  With `LANC_BOMB=grandslam` in the environment these modules draw segment 12 instead (see `../lancaster-grandslam`).
- `lbomb.py` — the Tallboy: steel case, light-alloy tail, four offset fins.
- `llanc.py` — the Lancaster with bulged bomb doors, the bomb and its links.
- `lsite.py` — the depot, the crater, the wrecked buildings, the thrown lorries and earth.
- `lsim.py` — the Mantaflow bake of the burst.
- `lshots.py` — the eight render shots and the frame renderer.
- `lpost.py` — title card, captions, radius circles, closing table, sound, encode.
- `render_all.py` — bakes if needed, renders every shot (resumable) and runs post.

```
pip install bpy numpy pillow scipy    # Blender as a Python module (Python 3.13), plus ffmpeg on the PATH
RENDER_DEVICE=GPU python3 lancaster-tallboy/render_all.py <frames_root> <sim_root> [out.mp4]
```
