# Veridian

A 2D side-scrolling engine and scene editor for a pixel-art thriller: a scientist
wakes in his cabin, drives up into the Appalachians to a secret facility, finds it
deserted, and works out why.

**This repository is the engine and the authoring tools, not the finished story.**
Three scenes ship as a working demonstration; the rest is authored in the editor.

- Pure atmosphere and investigation — no enemies, no combat, no death, no fail state
- Full-colour high-detail pixel art at a native **384×216**, integer-scaled (5× is exactly 1080p)
- Vanilla JavaScript, **zero dependencies, no build step**
- Scenes are painted backdrop layers plus collision boxes you draw over the art
- Real coloured lighting: warm lamps against cold moonlight, with named flicker profiles
- All sound is synthesised at runtime; there are no audio files

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
```

`check_scenes.py` validates the scene graph without a browser: doors pointing
at scenes and spawns that exist, gates nothing can open, clues no deduction
listens for, and deductions whose evidence is locked behind their own flag.

`investigation.cjs` plays the game: it asserts each realization fires on its
own evidence and *not* one clue short, that the keypad refuses `0000` and
accepts `0614`, that containers empty exactly once, and that all seven
realizations survive a reload.

Screenshots are written to `tools/verify/shots/`.
