# SEEDFALL (working title)

A first-person sci-fi survival-horror game inspired by the mood and structure of
*Alien: Covenant* (2017), with original names, creatures and story.

> A colony ark orbits a beautiful, silent planet. You take a lander down with a gun and a
> scanner to find out who is singing on the radio. Between trips you live aboard the big ship:
> you research what you brought back and hang out anywhere. The planet is trying to get inside.

**Status:** 📋 Planning. Nothing is built yet. Review the plan and answer the open decisions
in [the roadmap](docs/03-tech-and-roadmap.md#7-decisions-needed-before-building).

## Plan documents

| Doc | What's in it |
|---|---|
| [01 · Film research & analysis](docs/01-film-research.md) | *Alien: Covenant* beat by beat, the ship, the planet, creatures, themes, what critics said, **what we keep and what we make original**, sources |
| [02 · Game design](docs/02-game-design.md) | Pitch, pillars, setting, crew, **the *Meridian* ship and its deck plan**, the lander round trip, the planet's sites, core loop, systems (scanner, weapons, infection, research, quarantine), bestiary, story and endings, UI, audio, art, controls |
| [03 · Tech & roadmap](docs/03-tech-and-roadmap.md) | Engine options and recommendation, architecture, save data, project layout, **milestones M0–M9**, the vertical slice, risks, asset pipeline, open decisions |

## At a glance

- **Big ship:** CSV *Meridian*, about 1.1 km long. 2,400 colonists in cryo, a seed bank, and
  deployable solar collector sails. Three walkable habitat decks plus the spine, hangar and
  terraforming holds.
- **Between ships:** the **Kestrel** lander (undock, descent, landing, ascent, docking), plus
  the **Mule** heavy lifter for the Act II rescue.
- **Planet:** KX-7c "Verdance". Golden grass, fjords, fungal forests and dead alien ruins, with
  **no animal sounds at all.**
- **Loop:** hang out and research on the ship → prep → descend → explore, scan, sample and
  survive → extract → decontaminate → research → repeat.
- **Twist:** the voice on the radio is the planet itself, and what you bring back can infect
  the ship.
