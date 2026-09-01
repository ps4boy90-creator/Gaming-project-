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
| F3 | debug overlay (collision boxes, fps, position) |

## What's here

```
index.html          the game
editor.html         the scene editor
art/refs/           the original reference art, untouched
tools/              asset pipeline + end-to-end verification
assets/             everything the game loads, all derived by tools/
src/core/           screen, loop, input, asset loading
src/gfx/            backdrops, camera, sprites, lighting, post-processing, text
src/game/           physics, player, entities, flags, dialogue, cutscenes, saves
src/scenes/         scene JSON + the manifest
src/editor/         the editor
docs/               scene format, art pipeline, how to extend
```

### The three demonstration scenes

| Scene | Demonstrates |
|---|---|
| `cabin_bedroom` | painted backdrop, coloured lighting, notes, an item, examinable props, a save point, a flag-locked door |
| `cabin_landing` | a scene wider than the screen: camera scrolling, parallax, a foreground layer, a failing light, a terminal that gates the way out |
| `cabin_drive` | parallax sky, an image prop (the Veridian), a trigger that fires a cutscene |

Together they run: wake → read the memo → take the keys → the hall → play the
answering machine → outside → drive up → the arrival cutscene over the facility.

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
python3 -m http.server 8000 &
npm install playwright-core
node tools/verify/game.cjs
node tools/verify/editor.cjs
```

Screenshots are written to `tools/verify/shots/`.
