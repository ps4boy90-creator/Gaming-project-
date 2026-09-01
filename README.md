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
