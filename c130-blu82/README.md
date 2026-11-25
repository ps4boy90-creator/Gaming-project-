# Explosion Comparison · 13 — BLU-82/B "Daisy Cutter" from a C-130 on jungle

Thirteenth segment of the series. A Lockheed C-130B Hercules of 1970, 6,000 ft above the forest at
150 knots, opens its ramp and streams a parachute behind it. On the mark the parachute drags a
platform down the rollers and off the ramp. On the platform is a BLU-82/B: a thin steel tank
holding 12,600 lb of slurry explosive, 15,000 lb in all. Its own parachute pulls it off its cradle
and swings it nose down. It falls for 25 seconds and reaches the forest floor at about 103 m/s. A
three-foot rod on its nose touches first and fires it above the ground. There is no crater: the
blast goes outwards and takes the forest with it, leaving bare ground about 80 m across for
helicopters to land on. That is what the bomb was made for (Operation Commando Vault, South Vietnam,
1970 to 1972). The film shows the burst from above the canopy and from the air with its radii, as
the other bomb segments do, and then the clearing. Everything is procedural (Blender as a Python
module, Cycles) and shares the render setup, effects and post tools with the earlier segments.
Nobody is modelled anywhere.

**Status: draft only.** The code is complete and has been rendered end to end as a low-resolution
draft on a CPU (640×360, 6 samples, a coarse simulation). The 1080p render on a GPU is still to do,
so there is no `renders/` folder here yet.

**The place and the drop are invented.** The fall is calculated from the published rate of fall; the
size of the clearing and of the ring of burnt foliage are published; the 5 psi radius is scaled
from the Mk 82's, as in segment 07.

| # | Shot | What it shows | Speed |
|---|------|---------------|-------|
| 1 | `card`     | The bomb on its cradle and platform + spec panel | – |
| 2 | `approach` | The C-130 on its run-in; ramp and door open, the extraction parachute streamed | real time |
| 3 | `intro`    | The bomb with its dimensions and fuze extender, a jeep behind it for scale | – |
| 4 | `release`  | The load pulled out; the bomb leaves its cradle and swings nose down | real time |
| 5 | `fall`     | Beside the bomb through three and a half of its last seconds | real time |
| 6 | `impact`   | From above the canopy, 400 m off: the burst in the trees, the cloud | 2.5× slow, then faster |
| 7 | `radius`   | From the air: the burst and its circles, a helicopter's rotor for scale | about 1.4× slow |
| 8 | `after`    | A minute later: the clearing | real time |
| 9 | summary    | Table of the numbers (made in post) | – |

## The numbers in the film

Release: level at 150 knots (77 m/s), 6,000 ft (1,829 m) above the ground. The extraction parachute
gives the 20,000 lb load about 2.9 m/s² along the floor, so it is off the ramp 2.5 s after the locks
are released. From the ramp the bomb falls **25.1 s** and travels about 900 m forward; it arrives at
**103 m/s (337 ft/s, about 370 km/h)**, nearly straight down. From release that is 27.6 s
(published: 26 to 27 s; rate of fall 338 ft/s). When it bursts the aircraft is about a kilometre
further on and 1.3 miles away (published: "a little more than a mile").

| Circle in the radius shot | Radius | Basis |
|---|---|---|
| Ground cleared | 40 m (about 80 m, 260 ft, across) | published |
| Foliage burnt off | about 80 m | published: "about twice the usable radius" |
| 5 psi (34 kPa) blast | about 117 m | the Mk 82's 31 m × cube root of the fillings' ratio, with the slurry taken as 82% as strong as TNT; for a burst in the open |
| A UH-1's rotor | 14.6 m across | for scale |

## What is sourced and what is not

**From sources**

| Item | Value | Source |
|------|-------|--------|
| BLU-82/B | 141.6 in long (11 ft 6 in in the 1970 report), 54 in across, 15,000 lb; a thin-walled tank of 1/4 in steel plate with a formed steel nose; 12,600 lb of DBA-22M slurry of ammonium nitrate and powdered aluminium, "roughly 82% as powerful as TNT"; 225 built | Project CHECO report *Commando Vault* (HQ PACAF, 12 Oct 1970); National Museum of the USAF; Air Force Armament Museum |
| Fuzing | M904 nose fuze on an M1A1 fuze extender, a three-foot rod; M905 tail fuze as back-up; the bomb bursts "three feet above the ground" and leaves "little or no crater" (in a test: a depression 6 to 12 in deep and 20 to 30 ft across) | CHECO report; National Museum of the USAF; Sandia test report quoted by the Armament Museum |
| Airdrop | the bomb on a wooden cradle on an airdrop platform, 20,000 lb rigged; a 15 ft extraction parachute; a single 24 ft slotted stabilising parachute that pulls the bomb off the cradle, so that cradle and platform fall separately; the bomb falls nose down | CHECO report; S. McGowan (a loadmaster on these drops), *Air Force Magazine*, April 2016; Armament Museum diagram |
| Delivery | C-130B of the 463rd Tactical Airlift Wing; normally 6,000 ft above the ground at 150 knots; aimed by MSQ-77 ground radar; average miss 58 m; one bomb per aircraft; friendly troops no nearer than 1,500 m | CHECO report |
| Fall | rate of fall 338 ft/s; "impact at ~27 seconds and 340 FPS", about 2,700 ft of forward travel; about 26 s from 6,000 ft | AFI 11-231 (1998); Armament Museum diagram; CHECO report |
| Effect | an area about 80 m across (over 5,000 m², about 260 ft) cleared; stumps "invariably" remain; trees a yard thick torn out near the burst; the flash burns foliage out to about twice the usable radius; of 107 drops counted by 1 October 1970, 17 left no usable zone, 44 room for one helicopter, 36 for two, 8 for three and 2 for four | CHECO report; National Museum of the USAF |
| History | first production bomb dropped 23 March 1970; last one 15 July 2008 | CHECO report; af.mil |
| C-130 | span 132 ft 7 in; length 97 ft 9 in; height 38 ft 3 in; wing area 1,745 sq ft; tailplane 52.7 ft; main-gear track 14.3 ft; four Allison T56-A-7; four-blade Hamilton Standard propellers 13 ft 6 in across turning at a constant 1,020 rpm; cargo compartment about 10 ft wide and 9 ft high | USAF fact sheet; aero-web.org; Lockheed Martin *Service News*; a flight-manual three-view |
| Forest | canopies at two or three levels; trees 25 to 35 m tall with crowns about 10 m across and trunks 40 to 50 cm thick; the largest to 4 ft thick and 150 ft tall | US Army FM 90-5; National Academy of Sciences (1974); Sandia report quoted by the Armament Museum |
| Mk 82 radius | 31 m (5 psi) | as in segment 07 (GICHD / Ordtech) |

**Where the sources disagree**

* **Fuze extender.** 36 in (the 1970 report and the Armament Museum) or 38 in (later accounts). The film uses 36 in.
* **Width.** 54 in in the official sources; 56 in in one later book.
* **The stabilising parachute.** "24-foot slotted chute" in the 1970 report; "triangular" in a loadmaster's memoir. The film draws a round slotted canopy.
* **Aircraft model.** These drops were flown by C-130Bs; later ones by C-130E and MC-130E. The B has no underwing tanks.

**Not from sources (calculated or illustration)**

* **The place.** Rain forest on low hills, invented. No village, road or people.
* **The fall.** A point mass with drag. The stabilising parachute's drag area is not published: it is
  set so that the bomb ends at the published 338 ft/s, which needs a drag coefficient of only 0.23
  on a 24 ft canopy, so the canopy must be very open. The time on the rollers (2.5 s) comes from an
  estimated drag coefficient for the extraction parachute and an estimated 9 m run to the ramp's
  edge. With those the film's 27.6 s from release is a second longer than the published 26 to 27 s,
  and its 900 m of forward travel is more than the diagram's 2,700 ft (820 m).
* **How the bomb turns over.** It rides out nose aft (as the 10,000 lb M121 does in the report's
  photograph); that the parachute then swings it tail to the wind and nose down within three
  seconds is staging.
* **The 5 psi circle.** Scaled, not published, and for open ground: forest takes the blast's energy.
* **The burst.** A fireball about 50 m across, the ring of dust and torn wood, the pale cloud and how
  fast it climbs are staging (the simulation is driven by hand-placed sources). That the cloud is
  pale and mushrooms above the trees is from the report's photographs.
* **The clearing.** Which trees go, fall or stand is decided by distance alone: gone inside 40 m
  (stumps left, none within 9 m of the burst), thrown down pointing outwards to 54 m, leaves burnt
  off and trunks left leaning to 80 m. The 54 m is a guess from the report's photograph of a
  landing zone. Real results varied a great deal with slope and the size of the trees, as the
  counts above show; the film shows a good one.
* **The forest model.** About 2,500 trees stand within 300 m (95 to the hectare, crowns touching);
  one in twelve is an emergent 42 to 52 m tall. Beyond that the canopy is a single surface. Crowns
  are rounded masses, not leaves and branches.
* **The bomb model.** Lengths and width are published. The length of the cone, the blunt front,
  the domed rear, the three bands with lifting lugs, the parachute pack and the yellow band round
  the nose are from photographs of a Vietnam-era bomb and of the museum examples (which are inert
  and carry a blue band instead). The stencilling is illustrative. Cradle and platform are plain
  shapes of about the size seen in photographs (the platform is drawn 12 ft by 9 ft).
* **The C-130 model.** Section shapes, the nose, nacelles, gear fairings and fin are proportioned
  from a three-view drawing and photographs. The tan and two greens over light grey follow the
  Southeast Asia scheme; the pattern itself is not copied from an aircraft. The tail code QB and
  "969" follow C-130B 61-0969 of the 29th Tactical Airlift Squadron, 463rd TAW, as photographed
  at Cam Ranh Bay in 1969; it is not known whether that aircraft flew these drops. The landing
  gear is up; there are no panel lines, aerials, paratroop doors or crew. The hold is a dark
  recess with nothing in it but the load.
* **The parachutes.** Round ring-slot canopies of the published sizes; the number of gores and
  rings and the lengths of the lines are guesses.
* **The sound** is synthesized.

## Files

- `dconst.py` — published figures, the extraction and the fall, the radii (no bpy; `python3 dconst.py` prints the numbers above).
- `dbomb.py` — the bomb, its fuze extender, cradle and platform, the parachutes, a jeep for scale.
- `dherc.py` — the C-130B with its ramp and cargo door.
- `djungle.py` — the forest and what the burst leaves of it.
- `dsim.py` — the Mantaflow bake of the burst.
- `dshots.py` — the eight render shots and the frame renderer.
- `dpost.py` — title card, captions, circles, closing table, sound (the encode is `../lancaster-tallboy/lpost.py`).
- `render_all.py` — bakes if needed, renders every shot (resumable) and runs post.

```
pip install bpy numpy pillow scipy    # Blender as a Python module (Python 3.13), plus ffmpeg on the PATH
RENDER_DEVICE=GPU python3 c130-blu82/render_all.py <frames_root> <sim_root> [out.mp4]
```
