# Explosion Comparison · 06 — Mk 77 fire bomb from a UH-60 Black Hawk on a ruined town

Sixth segment of the series. A UH-60L Black Hawk with stub wings (the External Stores Support
System, ESSS) runs in at 200 ft and 100 kt over the ruined desert town of segment 04 and releases one
Mk 77 Mod 5 fire bomb. The unfinned canister tumbles for 3.6 seconds, bursts in a street, and its
burning fuel gel runs down the street between the house fronts. Everything is procedural (Blender as
a Python module, Cycles) and shares the town, render setup and post tools with the earlier segments.
Nobody is modelled in the town or the aircraft.

**The pairing is hypothetical.** The Mk 77 is a jet-delivered weapon: US Marine Corps doctrine
lists the F/A-18 and AV-8B for it, and no source found gives any H-60 a clearance to carry it. The
only helicopter precedent is different: in Vietnam, CH-47s dropped nets of napalm-filled drums. The
helicopter and the bomb are each modelled to their real dimensions; putting one under the other is
this film's invention, and the film says so on its title card.

| # | Shot | What it shows | Speed |
|---|------|---------------|-------|
| 1 | `card`     | The Black Hawk with four Mk 77s on a studio backdrop + spec panel | – |
| 2 | `approach` | Air to air: the helicopter running in towards the ruins | real time |
| 3 | `release`  | Beside the right stub wing: the rack lets go, the canister drops and starts to tumble | real time, then 4× slow |
| 4 | `fall`     | The camera follows the tumbling canister down onto the street | real time |
| 5 | `impact`   | From the far end of the street: the burst, and the fire rolling down the street | half speed, then real time |
| 6 | `radius`   | From the air: the burning area, and the published footprint of a jet-delivered Mk 77 | real time |
| 7 | `after`    | Forty seconds later: the street burnt black, fuel still burning, smoke over the ruins | real time |

## What is sourced and what is not

**From sources**

| Item | Value | Source |
|------|-------|--------|
| Mk 77 Mod 4/5 | length 81.2 in (2.06 m), diameter 18.6 in (0.47 m); 75 US gal (284 L) of kerosene-based fuel gel; about 520 lb (236 kg) filled; thin aluminium, no fins; two suspension lugs 14 in apart; two filler holes 31° from the top that take the igniters; unpainted with red stencilling | NAVAIR 11-5A-17 excerpt; NAVEDTRA aviation ordnance manual; USMC Basic School handout; CAT-UXO |
| Behaviour | unstabilised, tumbles end over end, ruptures on impact, igniters light the scattered gel | NAVEDTRA; GlobalSecurity |
| Fire | burns at 800–1,200 °C | Wikipedia "Napalm" |
| **Footprint** | **ellipse about 215 × 75 ft (65 × 23 m)** from a jet; other figures: 150 × 50 ft, 2,500 sq yd | USMC Basic School handout; HistoryNet; Wikipedia |
| Aircraft that carry it | F/A-18, AV-8B | USMC doctrine |
| UH-60L | fuselage 15.27 m, overall 19.76 m, main rotor 16.36 m, tail rotor 3.35 m, height 5.13 m, fuselage width 2.36 m, stabilator span 4.37 m, wheel track 2.71 m, wheelbase 8.82 m | Wikipedia "Sikorsky UH-60 Black Hawk"; Sikorsky S-70A data sheet |
| Rotors | four main and four tail blades; main rotor 258 rpm, anticlockwise from above, chord 1.73 ft, tips swept 20°; tail rotor on the right of the pylon, canted 20°, about 1,214 rpm | Sikorsky Archives; Vertical magazine |
| ESSS | stub wing each side at the cabin roof line, two brace struts, two pylons with ejector racks; normally fuel tanks, Hellfire, rockets or gun pods | FM 3-04.500; service photographs |

Shapes and proportions follow US Army photographs on Wikimedia Commons (a UH-60L in side view; a
front view with ESSS and four tanks; an ESSS aircraft from below) and a photograph of a Mk 77 on an
F/A-18 pylon. The fire is matched by eye to a US Marine Corps photograph of a Mk 77 burning in the
desert: an orange-yellow fireball several times longer than it is high, lying along the line of
flight, with dark sooty edges.

**Not from sources (illustration)**

* The load itself (see above). Rack position, sway bracing and release are generic.
* The fuselage sections, engine fairings, landing gear, ESSS span (about 6.4 m) and pylon positions
  are estimated from the photographs. Fine detail (doors, rivets, antennas, markings, the rotor head
  mechanism, blade twist) is simplified or omitted; there is no crew.
* 200 ft and 100 kt are one plausible low-level run, not a quoted delivery profile.
* The fall is a point mass with the drag of a tumbling blunt cylinder (drag area 0.42 m² and a tumble
  rate of 1.25 rev/s are estimates). It gives 170 m of forward throw in 3.64 s, arriving at 53 m/s
  and 37°. It is not a ballistic table.
* The fire is a gas simulation driven by hand-placed fuel sources along the street. Its size
  (about 34 × 9 m here, held in by the house fronts), how fast it runs, how high it stands and how
  long it burns come from that simulation and from general footage. A slow helicopter release giving
  a shorter smear than a jet is an inference, not a measured figure.
* The later smoke columns and the scorched ground are procedural.
* The town is invented; it is not a real place or a real strike.

## Files

- `nconst.py` — heights, speeds, the canister's fall (no bpy).
- `nuh60.py` — the Black Hawk (fuselage, glazing, engines, rotors, tail, gear), the ESSS and the Mk 77.
- `nsim.py` — the Mantaflow fire in the street.
- `nshots.py` — the seven shots and the frame renderer.
- `npost.py` — title card, HUD, sound, encode.
- `nlook.py` — renders the helicopter and a canister from several directions (model check).
- `render_all.py` — bakes the fire if needed, renders every shot (resumable) and runs post.

Mesh helpers (`qgeo.py`) and the smoke-column effect come from `../reaper-hellfire/`; the town from
`../howitzer-explosion/`.

```
pip install bpy numpy pillow          # Blender as a Python module (Python 3.13), plus ffmpeg on the PATH
RENDER_DEVICE=GPU python3 blackhawk-mk77/render_all.py <frames_root> <sim_root> [out.mp4]
```
