# Explosion Comparison · 12 — Grand Slam from an Avro Lancaster on a German army depot

Twelfth segment of the series, and the companion to segment 11. An Avro Lancaster B.I (Special) of
March 1945, 12,000 ft up at 200 mph, releases one Grand Slam: Barnes Wallis's 22,000 lb bomb, the
Tallboy's design made larger and the heaviest bomb used in the war. It has no bomb doors to open;
the bomb is too big for them and hangs partly below the belly. The bomb falls for 27 seconds and
reaches the yard of a German army depot at about 279 m/s. It goes some 16 m into the ground and
stops; eleven seconds later its fuze fires 4,144 kg of Torpex under the yard. The film shows the
burst from just above the ground and from the air with its radii, as the other bomb segments do,
and then the crater. The depot is the one of segment 11, so the two films can be set side by side.
Nobody is modelled anywhere, and there are no flags or insignia on the depot.

**Status: draft only.** The code is complete and has been rendered end to end as a low-resolution
draft on a CPU (640×360, 6 samples, a coarse simulation). The 1080p render on a GPU is still to do,
so there is no `renders/` folder here yet.

**The depot and the strike are invented.** How deep the bomb goes is calculated; the crater's size
and the radius for brick buildings are published ones; the 5 psi radius is scaled from the Mk 82's,
as in segment 07.

| # | Shot | What it shows | Speed |
|---|------|---------------|-------|
| 1 | `card`     | The bomb turning on a studio backdrop + spec panel | – |
| 2 | `approach` | The Lancaster on its run-up, the bomb under its open belly | real time |
| 3 | `intro`    | The bomb with its dimensions, a 6 m lorry behind it for scale | – |
| 4 | `release`  | The links let go; the bomb drops and begins to turn | real time, then half speed |
| 5 | `fall`     | Riding down behind the bomb through its last 3.5 s | real time |
| 6 | `impact`   | From a watch tower's height, 260 m off: into the yard; a card for the 11 seconds left out; the yard thrown into the air | 2.5× slow, then 1.25× |
| 7 | `radius`   | From the air: the burst and its circles, with a Tallboy's for comparison | about 1.5× slow |
| 8 | `after`    | Half a minute later: the crater and the wrecked buildings round it | real time |
| 9 | summary    | Table of the numbers (made in post) | – |

## The numbers in the film

Release: level at 200 mph (89 m/s), 12,000 ft (3,658 m) above the target. The bomb falls 27.4 s
and travels about 2.4 km forward. It arrives at **279 m/s (915 ft/s, about 1,000 km/h, Mach 0.82)**
on a path 72° below the horizontal, turning at about 60 rpm.

In the ground (moist clay and loam): about 16.5 m along its path, nearly 16 m down, in just over
0.1 s. The fuze fires 11 s after impact with the middle of the charge about 14 m down. The film does not make
the viewer wait: the frames run on from the bomb going in to the burst half a second later, and a
card between them says "11 seconds later". The bomb has stopped long before either moment, so the
burst is the same.

| Circle in the radius shot | Radius | Basis |
|---|---|---|
| Crater | 19 m (124 ft across) | published, for the trial drop at Ashley Walk on 13 March 1945 |
| Brick wall-bearing buildings demolished | about 46 m (150 ft) | published as a rough estimate, for a burst at ground level |
| 5 psi (34 kPa) blast | about 112 m | the Mk 82's 31 m × cube root of the fillings' ratio; for a burst at the surface |
| Tallboy, brick buildings demolished, for comparison | about 37 m (120 ft) | published, as above |

## What is sourced and what is not

**From sources**

| Item | Value | Source |
|------|-------|--------|
| Grand Slam | over-all length 25 ft 5 in; body 12 ft 6 in long and 3 ft 10 in across; tail 13 ft 4 in long and 4 ft 4 in across the fins; total weight 22,400 lb; Torpex with a one-inch topping of TNT; cast steel case, 7.75 in thick near the nose; Tail No. 82 Mk I of light alloy with four fins set at 5° for a right-hand spin; three Tail Pistols No. 58 in the base plate; twin suspension links coupled beneath the bomb by a release clip; "green over-all; red band near nose" | US Navy OP 1665, *British Explosive Ordnance* (1946) |
| Filling | 9,135 lb of Torpex | RAF Memorial Flight Club (9,200 lb in S. Flower, quoted by Wikipedia; OP 1665 gives "42% approx.") |
| Spin | 60 rpm at impact | OP 1665 |
| Fuze delay | 11 s on the first drops (Bielefeld, Arnsberg); up to an hour on others | Wikipedia, "Grand Slam (bomb)", after Flower; OP 1665 ("delays up to 11 seconds") |
| Release | the first one, at Bielefeld on 14 March 1945, from 11,965 ft; others from 12,000 to 15,000 ft; 200 mph | Wikipedia, after Flower; Bomber Command Museum of Canada |
| Striking velocity | 1,049 ft/s (320 m/s), release height not stated | Wikipedia, after Webster and Frankland |
| Crater | 124 ft across and 34 ft deep at the trial of 13 March 1945 (a 1945 Air Ministry caption: 120 ft and "more than 35 ft") | Wikipedia, after Flower; Bomber Command Museum of Canada; IWM CH 15368 |
| Damage to buildings | "rough estimates of the distance from detonations at ground level ... at which brick wall-bearing buildings will be demolished": about 150 ft for the 22,000 lb bomb, about 120 ft for the 12,000 lb bomb | Th. von Kármán, *Explosives and Terminal Ballistics* (1946) |
| Against concrete | at Farge on 27 March 1945 two hits on the 4.5 m part of the roof went about 2 m in before bursting and brought part of it down; in the 1946 trials 7 ft 8 in at 1,150 ft/s, and no bomb could go through the 23 ft part | Wikipedia, "Valentin submarine pens"; Project Ruby report |
| Number | 42 released: 40 on targets, 2 jettisoned (41 in other accounts) | R. Owen, thesis on No. 617 Squadron |
| Lancaster B.I (Special) | bomb doors removed and the bay faired; front and mid-upper turrets removed; Merlin 24 engines; maximum weight 72,000 lb; code YZ; the first four delivered in the standard night finish | Wikipedia, after Flower; Bomber Command Museum of Canada; R. Owen; Profile Publications No. 65 |
| Lancaster | as in segment 11 | see `../lancaster-tallboy/README.md` |
| Penetration equations | Young, *Penetration Equations*, Sandia report SAND97-2426 (1997) | the report |
| Mk 82 radius | 31 m (5 psi) | as in segment 07 (GICHD / Ordtech) |

**Where the sources disagree**

* **Length.** OP 1665 and two other ordnance manuals give 25 ft 5 in (25 ft 6 in). 26 ft 6 in, often
  quoted, was found only in Wikipedia's summary box without a reference. The film uses 25 ft 5 in.
* **Striking velocity.** OP 1665 gives 1,097 ft/s for a release at 16,000 ft and 200 mph. A body
  falling 16,000 ft with no air at all reaches only about 1,056 ft/s, so that figure cannot be right;
  it is the Tallboy's (from 18,000 ft) repeated. The film's 915 ft/s is calculated for 12,000 ft,
  where the limit without air is 927 ft/s.
* **Time of fall.** 35 s is reported for the first drop from 11,965 ft. Without air the fall takes
  27.3 s and the bomb is too heavy for the air to add eight seconds; the film's 27.4 s is calculated.
* **Crater.** Local accounts of the Ashley Walk trial give 130 ft across and 70 ft deep.

**Not from sources (calculated or illustration)**

* **The depot.** As in segment 11: a stand-in for "a German army base", not a real place. Grand
  Slams were dropped on railway viaducts and bridges, U-boat shelters and coastal batteries. None was
  spent on a depot like this one.
* **How deep the bomb goes.** Calculated with Young's equation for soil. Guesses: the soil number
  (S = 7, moist clay and loam) and that the bomb stays whole and straight.
  For reinforced concrete at 1,150 ft/s the same equation gives 2.1 m, against 7 ft 8 in (2.3 m) in
  the 1946 trials.
* **The 5 psi circle.** Scaled from the Mk 82's published radius by the cube root of the
  fillings' weights. Like the published radius for brick buildings it is for a burst at the surface:
  a charge 14 m down sends less of its force into the air and more into the ground. The film says
  so on screen.
* **The burst.** That a charge at this depth throws up earth rather than flame, and leaves a crater
  about 38 m across, follows the published crater. The height and speed of the column, how long the
  earth takes to fall, which buildings come down (those within about 66 m) and how the lorries are
  thrown are staging. The simulation is the Tallboy's with every size and speed multiplied by 1.21,
  the cube root of the fillings' ratio.
* **The fall.** A point mass with an estimated drag curve, as in segment 11.
* **The bomb model.** Lengths, widths and weight are OP 1665's. The outline between them is drawn
  to a wartime photograph of a Grand Slam being slung at Woodhall Spa (IWM CH 15369): the pointed
  ogival nose, the dark body, a dark band at the joint, a light-coloured tail with its hand-holes
  and "No 82 Mk I" stencilled on it, running out nearly to a point, and four short swept fins set a
  little forward of that point. The body is modelled 12 ft 6 in long and the tail as the rest
  (12 ft 11 in); the published tail is 5 in longer because it overlaps the body. The red band is
  put where a photograph of the Tallboy shows a light ring round the point of the nose. The exact
  green and the grey of the tail are guesses (the photograph is black and white).
* **The Lancaster model.** Segment 11's, with the bomb doors left off, the opening closed in ahead
  of and behind the bomb, the nose turret's place faired over and no mid-upper turret. How far the
  bomb hangs below the belly (about 0.25 m here) is not from a source. The finish is the night
  scheme of segment 11 with the code YZ in dull red, which is what the first four aircraft are said
  to have worn; photographs could not be consulted, so the letter "C" and the look of the faired
  nose are not checked against one. Later aircraft had a day scheme. The four-gun tail turret is
  kept (accounts differ on whether two of its guns were removed). The propeller blades are made
  broader than segment 11's for the "paddle" blades these aircraft had; by how much is a guess.
* **The sound** is synthesized.

## Files

- `render_all.py` — sets `LANC_BOMB=grandslam` and runs segment 11's driver: bakes if needed, renders every shot (resumable), runs post.
- `spost.py` — this segment's title card, captions, the "11 seconds later" card and the closing table; the rest of the finishing is segment 11's `lpost.py`.
- Everything else is in `../lancaster-tallboy`: `lconst.py` (both bombs' figures; `LANC_BOMB=grandslam python3 lconst.py` prints the numbers above), `lbomb.py`, `llanc.py`, `lsite.py`, `lsim.py`, `lshots.py`.

```
pip install bpy numpy pillow scipy    # Blender as a Python module (Python 3.13), plus ffmpeg on the PATH
RENDER_DEVICE=GPU python3 lancaster-grandslam/render_all.py <frames_root> <sim_root> [out.mp4]
```
