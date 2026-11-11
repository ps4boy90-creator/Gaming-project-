# Ironvale

A 3D isometric prison building and management simulator that runs in the browser. Everything you see is generated in code: there are no image, model or audio files.

## Play

- **Quickest:** open `play.html` in a desktop or mobile browser. It is the whole game in one file and works offline.
- **Development:** `npm install`, then `npm run dev` and open the address it prints.
- **Rebuild `play.html`:** `npm run build:single`.

The game needs WebGL 2. Saves are kept in the browser's local storage.

## What is in it

- **Building:** one-drag buildings, 5 wall and fence types, 4 door types, 11 floors, 23 room types and 52 objects. Workmen construct whatever you plan.
- **People:** inmates in three security levels, plus a warden, guards, cooks, doctors, janitors, workmen, a teacher, a psychologist, a chaplain, visitors and a riot squad.
- **Simulation:** nine inmate needs, a 24-hour regime you can edit, a daily intake bus, sentences and release, work and education, contraband, fights, escapes, tunnelling, riots, lockdowns and shakedowns.
- **Management:** state grants, wages, a ledger, 17 milestone grants, a prison rating and reports.
- **Presentation:** soft shadows, ambient occlusion, bloom, a day and night cycle, and three quality levels that step down by themselves on slow hardware.

## Controls

| Input | Action |
|---|---|
| `W` `A` `S` `D` or drag | Move the camera |
| Mouse wheel or pinch | Zoom |
| `Q` `E` | Rotate the view |
| `R` | Rotate the object being placed |
| `Space`, `1` `2` `3` | Pause and game speed |
| `Tab` | Room overlay |
| `Esc` or right-click | Cancel the current tool |
| `Del` | Demolish tool |

## Code map

| Path | Purpose |
|---|---|
| `src/data/` | Static definitions: floors, walls, doors, objects, rooms, staff, regime |
| `src/world/` | Tile grid, room detection, pathfinding, the starter prison |
| `src/sim/` | Time, economy, inmates, staff, incidents, construction jobs |
| `src/render/` | three.js scene: terrain, walls, instanced objects and people, overlays, lighting |
| `src/ui/` | HUD, build dock, inspector and report panels |
| `src/input.ts`, `src/game.ts` | Camera and build tools; the main loop |
| `models-preview.html` | Dev page that shows every procedural model (`npm run dev`, then open `/models-preview.html`) |

See `DESIGN.md` for the research and design notes behind the game.
