# Art pipeline

Nothing under `assets/` is edited by hand. It is all derived from `art/refs/` by
scripts, so the process is repeatable and new reference art goes through the same
path as the original four images.

```bash
pip install pillow
python3 tools/slice_refs.py      # everything derived from art/refs/
python3 tools/make_corridor.py   # the two procedural starter backdrops
```

## Why the references are downscaled

The reference images are 2688×1520 upscales. Measuring the run lengths of colour
changes across them shows a repeating period of 7 pixels, which means their true
grid is **384×216** — and that is the resolution the game renders at. It also
multiplies to exactly 1920×1080 at 5×, so the game is pixel-exact on a 1080p
display.

Reduction uses Lanczos rather than nearest-neighbour: the source art is already
finely shaded and dithered, and point-sampling it turns that dithering into
noise. The result is then quantised to a small adaptive palette with dithering
off, which brings the crisp flat areas back.

## What comes out

| Output | Source |
|---|---|
| `assets/backdrops/cabin_bedroom/room.png` | the bedroom reference at 384×216 |
| `assets/stills/facility_exterior_night.png` | the facility at 768×432, the cutscene surface's size, so a pan can push in without going soft |
| `assets/stills/cabin_prologue.png` | the bedroom again, framed wide and dark, for the opening narration |
| `assets/stills/drive_night.png` | built by `make_stills.py`: the Veridian cut from its spec sheet, on a procedural night road. The drive beat animates instead, so this is now its fallback |
| `assets/stills/parts/car_side.png` | the same cut-out with nothing behind it, for the animated drive to move against |
| `assets/stills/aperture_reveal.png`, `aperture_empty.png` | built by `make_stills.py`: the containment chamber, with Hale at the threshold and then without him |
| `assets/sprites/scientist/scientist.png` + `.json` | the front, side and back views packed into one atlas |
| `assets/portraits/scientist/*.png` | the five expressions: `neutral`, `stern`, `worried`, `resolute`, `smile` |
| `assets/props/car_veridian/*.png` | six orthographic views of the Veridian 2400 |
| `assets/palette.json` | dominant colours per reference, for keeping new art in family |

The crop boxes in `slice_refs.py` were measured from the references by projection
analysis rather than by eye, and the flat grey plate behind each sheet is removed
by a flood fill from the border — so shadows inside the lab coat that happen to
sit close to the plate's tone survive.

Two constants at the top of the script set the scale of everything:

```python
PLAYER_H = 88      # how tall the protagonist stands, in native pixels
PORTRAIT_H = 56    # portrait height in the dialogue box
```

## Monochrome

`tools/monochrome.py`, shared by all three generators so they cannot drift.

Three steps, each answering a specific failure:

1. **Weighted mix, not luma.** Blue at 0.06 against the standard 0.114, red at
   0.34 against 0.299. Cold light darkens, warm light holds, and the two
   separate by brightness once hue is gone. Measured on the bedroom's two
   lights this widens the gap from 25.5 to 39.1 out of 255.
2. **A tone curve pivoted on the image's median.** Not on mid-grey: these are
   night scenes living in the bottom tenth of the range, and an S-curve about
   0.5 took the bedroom from a mean of 18/255 to 8/255 and destroyed it.
3. **A quantised ramp with a 4×4 ordered dither**, in perceptual space. A linear
   ramp spends its steps on highlights these scenes never reach — a 20-step
   linear ramp resolved to eight actual greys on the bedroom.

`MONO = False` at the top of `slice_refs.py` derives the colour assets instead;
the engine and the scene files are identical either way, so the two can be
compared directly.

Set the runtime filter off with `O` → **Black and white** to see the colour
beneath, which is also how to check that a scene's lighting is doing the work
rather than its palette.

## The animation placeholder

The character reference is a **turnaround, not a walk cycle** — there are no
motion frames in it. `scientist.json` is therefore marked `"placeholder": true`
and fakes movement with a per-frame vertical `bob` and a forward `lean`.

To replace it, drop in a real sheet and a matching JSON with the same clip names:

```json
{
  "image": "sprites/scientist/scientist.png",
  "origin": "bottom-center",
  "frames": { "walk_0": { "x": 0, "y": 0, "w": 32, "h": 88 }, … },
  "clips": {
    "walk": { "frames": ["walk_0","walk_1","walk_2","walk_3"], "fps": 10, "loop": true,
              "events": { "0": "step", "2": "step" } }
  }
}
```

Drop the `bob` and `lean` fields once there are real frames. The player asks for
clips by name and falls back gracefully, so a sheet with only `idle` and `walk`
works — `run` will reuse `walk`, and `crouch` will reuse `idle`, until you add them.

## The two procedural backdrops

`cabin_landing` and `cabin_drive` are generated by `tools/make_corridor.py`
rather than painted. They exist so the engine ships with scenes that are *wider
than the screen*, which is what proves camera scrolling, parallax and travel
between scenes. They are deliberately plain — replace the folders under
`assets/backdrops/` with painted art and the scene JSON keeps working unchanged.
