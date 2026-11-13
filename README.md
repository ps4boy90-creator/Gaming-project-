# Veridian

A 2D side-scrolling engine and scene editor for a pixel-art thriller: a scientist
wakes in his cabin, drives up into the Appalachians to a secret facility, finds it
deserted, and works out why.

**This repository is the engine and the authoring tools, not the finished story.**
Three scenes ship as a working demonstration; the rest is authored in the editor.

- Pure atmosphere and investigation — no enemies, no combat, no death, no fail state
- **Monochrome** high-detail pixel art at a native **384×216**, integer-scaled (5× is exactly 1080p)
- Vanilla JavaScript, **zero dependencies, no build step**
- Scenes are painted backdrop layers plus collision boxes you draw over the art
- Real coloured lighting: warm lamps against cold moonlight, with named flicker profiles
- All sound is synthesised at runtime; there are no audio files
- A generative score and a 1950s radio the whole mix plays through
- A 1960s anthology-broadcast presentation: narration, scanlines, vertical roll, signal tearing

## Running it

There is no build. Serve the folder over HTTP — ES modules will not load from
`file://`:

```bash
python3 -m http.server 8000
```

Then open:

- <http://localhost:8000/index.html> — the game
- <http://localhost:8000/editor.html> — the scene editor
- <http://localhost:8000/farm/index.html> — the farm, a separate 3D night scene (see below)

It deploys to GitHub Pages as-is.

### Controls

| | |
|---|---|
| Arrows / WASD | walk |
| Shift | run |
| Ctrl / C | crouch |
| Up / Down | climb ladders |
| E or Enter | interact, turn pages |
| Tab | journal |
| Esc | close, skip a cutscene |
| Digits | enter a keypad code |
| O | options (volume, radio amount, post-processing) |
| F3 | debug overlay (collision boxes, fps, position) |

## What's here

```
index.html          the game
editor.html         the scene editor
art/refs/           the original reference art, untouched
tools/              asset pipeline, scene validation, end-to-end verification
assets/             everything the game loads, all derived by tools/
src/core/           screen, loop, input, asset loading
src/gfx/            backdrops, camera, sprites, lighting, post-processing, text
src/game/           physics, player, entities, flags, deductions, dialogue, cutscenes, saves
src/scenes/         scene JSON + the manifest
src/editor/         the editor
docs/               scene format, art pipeline, how to extend
farm/               a first-person 3D night scene in WebGL 2, independent of the engine above
```

### The game

Eleven scenes, 160 entities, playable end to end: wake in the cabin, read the
memo, take the keys, play the answering machine, drive up, and then search
Blackridge Station — gate, lobby, offices, canteen, laboratory, security,
stairwell, and the aperture chamber on Sublevel 3.

**What happened:** at 06:14 on Thursday, fourteen minutes into a scheduled
shutdown of the Sublevel 3 aperture, containment failed and everyone in the
building was pulled through. One person was behind a blast door and survived.
Every clue in the building points at that, and the player has to assemble it.

### Investigation: clues become realizations

Reading or examining enough **related** evidence fires a **realization** —
Hale says it aloud, it is filed in the journal's Deductions tab, and it unlocks
the next part of the building. Each of the seven deductions lists more clues
than it needs, so no single missable object can wedge the game.

The chain: nobody left → everything stopped at 06:14 → it happened mid-shift →
the shutdown test caused it → they were pulled through → someone was left
behind → she went in after them.

Two nice consequences fall out of this: the code for the sealed stairwell door
is `0614`, which you can only know by working out when everything stopped; and
the last realization is personal — the message that told him to come in early
is the only reason he wasn't there at 06:14.

## Look

Black and white, after Midnight Scenes — Octavi Navarro's Twilight Zone
pastiches, whose early episodes are monochrome.

The conversion is deliberately not a desaturation. Desaturating maps hue to
nothing, so two colours that differ only in hue collapse to the same grey: the
bedroom's warm lamp and its cold moonlight sit at almost the same luminance and
the room would go from two light sources to one flat wash. Instead
`tools/monochrome.py` weights blue well below the standard luma coefficient and
red slightly above, so cold light darkens and warm light holds — roughly
doubling the gap between them — then applies a tone curve pivoted on each
image's own median (these are night scenes; an S-curve about mid-grey crushes
them) and quantises onto a grey ramp with an ordered dither.

The ten procedurally generated backdrops skip the conversion entirely and are
drawn from a grey palette chosen for separation. There is no reason to convert
colours and hope they do not collide when you can pick the values.

The lights keep their colours in the scene files, and convert at render time,
so the warm/cold relationship survives as brightness. `O` → **Black and white**
turns the filter off and shows the colour underneath.

**Broadcast treatment.** Scanlines, vignette, a vertical roll and occasional
signal tearing, all driven by the same tension value as the radio — so as the
player works more out, the picture degrades in step with the sound.

**Narration.** The story opens and closes on a third-person narrator, in the
register of a 1960s anthology show.

## The farm (3D)

`farm/` is a different kind of thing from the rest of this repository: a
first-person 3D scene, not part of the 2D engine or its story. A clapboard
farmhouse and a gambrel barn in a fenced yard, a paddock, a dirt road, and
conifer forest on every side, at night. It is a study in a particular look —
the photo-textured, low-poly, VHS-filtered style of first-person indie horror —
built to the same rules as everything else here: vanilla JavaScript, no
dependencies, no build step, no asset files.

| | |
|---|---|
| Click | start, capture the mouse |
| WASD / arrows | walk (left and right arrows turn) |
| Mouse | look |
| Shift | run |
| E, or click | use what you are looking at |
| F | torch |
| V | tape filter on / off |
| Touch | left thumb walks, right thumb looks; USE, TORCH, RUN and TAPE buttons appear |

Where a browser will not capture the mouse, hold a button and drag to look.
On a phone held upright the view widens so it is never a keyhole.

Walk up the drive through the open gate. The porch steps take you onto the
deck, and the front door is shut but not locked. Inside are a hall, a dining
room laid for a meal, a kitchen in the lean-to at the back, and a living room
where the television has been left on with nothing on it. A door in the hall
opens on a steep boxed stair; at the top are a landing, two bedrooms — one
with a lamp left on, one a child's and dark — and a bathroom over the porch.
The barn's right-hand door has been rolled back far enough to get in, and
inside it is black without the torch.

**Using things.** There is no cursor. Whatever is nearest the middle of the
screen and within arm's reach is the thing, and a line of text says what will
happen if you use it. Every door opens and closes, all ten of them: front,
back, the one to the stairs, both bedrooms and the bathroom, both sliding
leaves of the barn, and both doors of the pickup, which show a bench seat, a
dashboard and a steering wheel. Each lamp, the ceiling lights and the
television switch off and on, taking with them the glow in the windows and the
light they throw on the grass outside. The telephone and the clock answer
back.

**How the look is made.** The reference style is not pixel art. It is
recognisably real materials on boxy geometry, lit by almost nothing, then
degraded as if recorded to tape. So:

- *Geometry is primitive on purpose* — boxes, quads and cylinders, hard edges,
  no bevels — but the trim is real: window frames and sills, corner boards,
  porch balusters, X-braced barn doors. About 590,000 vertices, drawn in one
  call; three quarters of them are furniture.
- *Textures are painted at load time*, thirty-three 512×512 layers in one
  texture array, and filtered smoothly. Every face is mapped in metres from its own
  plane, so a clapboard is the same height on the house as on the porch gable.
- *There are no shadow maps.* Each vertex carries how much sky it can see,
  which is what keeps moonlight out of the barn and off the porch ceiling.
  Moon shadows come from eight boxes instead — the house, the barn and the
  pickup, each fitted just inside its walls — and a ray test per pixel.
- *Every light knows where it is allowed to fall.* With no shadows, a lamp in
  the dining room would light the lawn and the room next door straight through
  the walls. So the outdoor lights ignore anything inside the house, and each
  indoor one lights only its own room's rectangle on its own storey, fading
  out over a short margin so that it spills a little way through a doorway and
  no further. Fifteen lights in all, of the sixteen the shader will take.
- *Two floors share one footprint.* The player is on whichever floor they were
  already nearest, the stair is a ramp between the two, and every collider
  says which storey it belongs to — so the dining table is not in the way of
  somebody crossing the bedroom above it. The hole in the upper floor starts
  three steps up the flight, where there is first a head's height to spare,
  which is what leaves room for a landing at the top.
- *The house is cut open for real.* Outside walls are built round their door
  and window openings, with the thickness of the wall showing in the reveals,
  so the lit rooms are visible from the yard through the curtains. There is no
  glass; it would need a blended pass of its own, and at night it is not
  missed.
- *Indoors, nothing is a box standing in for a thing.* `detail.js` adds what
  the buildings never needed: profiles turned on a lathe, boxes with properly
  rounded edges, tubes swept along a path, cloth hanging in folds, each with a
  normal at every vertex so it shades as a curve, and a gloss for china, chrome
  and varnish. Chair legs are turned, the telephone has a coiled cord, the
  bookcase holds ninety separate books, the cooker has four ring elements and
  a kettle. The rooms themselves stay flat-walled, because walls are flat.
- *Night is navy, not black*, and the fog is darker than the horizon it fades
  toward — otherwise a distant tree line dissolves into the sky instead of
  standing against it. That one inequality is most of the forest.
- *The pickup is where the polygons go.* A wall is recognised by its texture
  and a vehicle by its outline, so `truck.js` spends on outline: wheel arches
  cut into the flanks, a crease from nose to tail, a hood that crowns, a cab
  that leans in, a raked screen. Seams, handles, mirrors and wipers are trim
  laid over the top, and it has its own paint, glass, tread, grille and plate.
- *A door is a part, not a prop.* Almost everything is one fixed mesh in one
  draw call. Anything that moves or switches — a door leaf, a lampshade, the
  television screen, curtains lit from behind — is built apart, after it, with
  its own transform, glow and tint, and drawn in one more call each: thirty-five in
  all. A door also owns a collider that swings with it, so shut stops you and
  open does not; it hangs in the outer face of its wall, which is what lets
  the porch light fall on one side of it and the hall lamp on the other.
- *Trees are flat crossed cards*, each mirrored at random, thinned by a slow
  noise into stands and gaps, with a long tail on their heights.
- *The tape pass* resolves colour far more coarsely than brightness and drags
  it sideways, adds edge ringing, grain in both channels, a vignette and a
  wandering band of mistracking. The scene is drawn at 540 lines, multisampled:
  stair-stepped roof lines are the quickest way for this to read as a render
  rather than footage.

**It is tuned against measurements, not by eye.** Night exteriors in the
reference games average 4–8% brightness with 80–99% of the frame under 10%,
blue overall (hue 190–220°), and orange (20–30°) wherever a lamp is doing the
work. The arrival view here measures 7.9%, 85%, hue 215°; the porch, 29°.
`farm.measure()` in the console returns those numbers for the current frame.

```bash
node tools/verify/farm.cjs       # 72 checks; screenshots in tools/verify/shots/
```

The suite checks the picture against those targets and then walks into things:
the gate is open and the fence is not, the steps lead onto the porch and the
rail keeps you off it, one barn door admits you and the other does not, and
the forest closes in before the map runs out. Indoors it goes room to room —
hall to dining room to kitchen, hall to living room — and checks that the
table, the counter and the walls are solid. Then it uses things: the front
door is shut until it is opened, the back door leads out onto its step, the
barn can be slid shut, and switching off a light makes its room measurably
dark. Routes that matter are walked from waypoint to waypoint rather than
teleported to: from the hall round the sofa and out of the back door, up the
stairs to the landing, into each upstairs room once its door has been opened,
and down again. Every one of the ten doors is operated the way a player would
— stand within reach, look at the handle, use it — and has to move. It
finishes on an emulated phone, walking and turning by touch alone.

**What it is not.** The textures are procedural, not photographs, so up close
under the torch they are plainer than the real thing. There are no people in
it. You cannot climb into the pickup or up the barn's ladder. The stair is
steeper than a modern one would be allowed to be, because the house is only
seven metres deep and the flight has to fit in it.
`?pose=x,z,yaw,pitch`, `?time=`, `?torch=1` and `?tape=0` pin the
camera, the clock and the filters for repeatable captures, and `?lines=270`
draws at half the usual 540 lines for a machine that is struggling.

## Cutscenes

Five beats: the **prologue** in the cabin, the **drive** up the mountain,
**arrival** at the gate, the **aperture** the first time he reaches it, and the
**epilogue**.

**Two of them are animated rather than panned.** In the prologue Hale is asleep
in the bed, the clock goes off, he sits up, gets out and crosses to the window —
played with his own sprite, rotated about the hip for the sit-up, because the
character sheet is a turnaround with no lying-down frame and never will have
one. The drive is a side-on night road: five bands at five speeds, from a ridge
that barely moves to trunks that cross the frame in a third of a second, with
the centre line streaming past, a headlight beam on the tarmac and a sign that
goes by once. Parallax is the only depth cue a flat side view gets, so it does
all the work.

Painters live in `src/game/cutscene_fx.js` and repaint the whole frame every
tick; a step names one with `fx` and which beat of it with `phase`. The pan,
the letterbox, the text and the broadcast treatment all apply over the top, so
an animated beat and a painted one are the same kind of thing to everything
else.

They render to their own surface at **768×432** — twice the game's linear
resolution, four times the pixels — while gameplay keeps its 384×216 backbuffer
untouched. The gameplay grid exists so a walk cycle stays crisp; a full-screen
still has no such constraint, and holding one at 384×216 was throwing away most
of the detail in source art that is 2688×1520.

One honest trade: 768×432 does not land on an integer multiple of a 1080p
display (it is 2.5×), so cutscene stills are smoothed on the way out while
gameplay stays nearest-neighbour and exact. On a slow pan that reads as film
rather than as a mistake, but it is a real difference — `O` → **Soft cutscenes**
turns it off.

That smoothing is bilinear, not the browser's `high` setting. `high` is a
multi-pass resample built for *downscaling*; on a 2.5× upscale it halved the
frame rate — 32fps in any cutscene — while differing from bilinear by an
average of 0.3 of one grey level. The suite now measures frames during a
cutscene, which is the only reason that was ever found.

Cutscenes are also the only place the frame changes shape: 2.39:1 letterbox
bars, which is most of what tells the player they are not in control. A beat can
cut between stills, cross-fading rather than snapping — the epilogue does, from
the threshold with Hale standing in it to the same room without him.

```bash
python3 tools/make_stills.py     # the drive composite and the aperture chamber
```

## Sound

There are no audio files. Everything is synthesised at runtime, including the
music.

**The score** is generative: a low drone, a pad that never quite arrives, and
single struck notes that ring out and decay, minutes apart. It is re-rolled from
a weighted minor scale each time rather than looped, and each scene picks a bed
(`cabin`, `road`, `facility`, `deep`, `aperture`).

**The whole mix plays through a 1950s tabletop radio.** Band-limited to roughly
300 Hz – 3.5 kHz, with valve saturation, cabinet resonance, mains hum, hiss,
crackle and wow. Not a filter over a score — the game *is* the transmission,
footsteps and all.

**Both degrade as you work things out.** A hidden tension value rises with each
realization: the root sags, the flattened second creeps into the scale, the
low-pass closes, hiss and dropouts increase, and a heterodyne whistle starts
sliding through the top of the band. By the aperture the station is barely
holding. You should never notice a single step of it.

`O` opens options, where **Radio** can be turned down to 0 — a full bypass, in
case band-limiting the entire game is a problem rather than a mood.

```bash
node tools/render_audio.cjs      # renders .wav captures you can listen to
```

## Authoring a scene

1. Open `editor.html`.
2. **Load scene…** to edit an existing one, or **New** to start fresh.
3. Add a backdrop image under *Backdrop layers*.
4. **Collision** tool: drag rectangles over the floor and anything solid.
5. **Place** tool: drop doors, notes, terminals, items, triggers and lights, then
   fill in their properties on the right. Drag the handle on a light to set its radius.
6. **▶ Test play** runs the scene you are looking at, immediately.
7. **Export JSON**, drop the file in `src/scenes/`, and add one line to
   `src/scenes/manifest.js`.

The *Flags in this scene* panel lists every flag name referenced, and marks any
that are read but never set — which is what a typo looks like.

See [docs/SCENE_FORMAT.md](docs/SCENE_FORMAT.md) for the file format and
[docs/EXTENDING.md](docs/EXTENDING.md) for adding new entity types, sprites and cutscenes.

## Art

The four reference images live in `art/refs/` and are never edited in place.
`tools/slice_refs.py` derives everything the game loads from them — the character
frames, the five portrait expressions, the car views, the backdrop, the facility
still — so the pipeline is reproducible and new reference art goes through the
same path. See [docs/ART_PIPELINE.md](docs/ART_PIPELINE.md).

```bash
pip install pillow
python3 tools/slice_refs.py      # assets from art/refs/
python3 tools/make_corridor.py   # the two procedural starter backdrops
```

**The character animation is a placeholder.** The reference sheet is a turnaround,
not a walk cycle, so `assets/sprites/scientist/scientist.json` fakes motion with a
vertical bob. Drop in a real sheet plus a matching JSON keeping the clip names
(`idle`, `walk`, `run`, …) and nothing else needs to change.

## Verifying

The checks drive a real browser and assert what a player sees:

```bash
python3 tools/check_scenes.py          # no browser needed

python3 -m http.server 8000 &
npm install playwright-core
node tools/verify/game.cjs             # engine: movement, lighting, doors, saves
node tools/verify/investigation.cjs    # the whole mystery, cabin to aperture
node tools/verify/editor.cjs           # the editor round-trips
node tools/verify/audio.cjs            # the score and the radio, measured
node tools/verify/mono.cjs             # the conversion, measured off the frame
node tools/verify/cutscenes.cjs        # the five beats, and gameplay pixel-for-pixel
```

`check_scenes.py` validates the scene graph without a browser: doors pointing
at scenes and spawns that exist, gates nothing can open, clues no deduction
listens for, and deductions whose evidence is locked behind their own flag.

`audio.cjs` measures the sound rather than inspecting the graph: that there is
real output, that the spectrum is genuinely band-limited where a period set
band-limits it, that bypassing restores both ends, that no ambience preset or
effect was filtered into silence, and that the output never clips under load.

`investigation.cjs` plays the game: it asserts each realization fires on its
own evidence and *not* one clue short, that the keypad refuses `0000` and
accepts `0614`, that containers empty exactly once, and that all seven
realizations survive a reload.

`cutscenes.cjs` checks the beats fire once each in order, that the cutscene
surface really is 768×432 and carries a still intact where 384×216 could not,
and — the check that matters — that gameplay frames are **pixel-identical** to
`tools/verify/baseline/`, captured with `tools/verify/frames.cjs` against the
commit before the cutscene work began. Raising the cutscenes was supposed to
leave gameplay alone, and that is a claim about pixels, so it is tested as one.

Almost everything on screen moves by itself — grain cycles, the vertical roll
creeps, the lamps flicker off a running PRNG, the idle animation breathes — so
two captures of the *same unchanged build* differ in tens of thousands of pixels
unless every one of those clocks is pinned first. `frames.cjs` is the only place
that knows how to pin them, and both sides of the comparison go through it.

Screenshots are written to `tools/verify/shots/`.
