# Ironvale: research and design notes

## Research

**Real prisons.** State inspection reports (Virginia OSIG, 2025-2026) list the same functional areas in almost every facility: housing units of cells and dormitories, intake and release, a medical unit, kitchen and dining hall, showers, laundry, recreation yards and a gym, visitation, classrooms and vocational workshops, a library, a chapel, restrictive housing, a control room with CCTV, perimeter fencing with towers, and administration. Staffing covers a warden, correctional officers, medical staff, cooks, maintenance, teachers, a chaplain and counsellors. Daily life follows a fixed timetable, broken by lockdowns and searches. Each of these became a room type, a staff role or a mechanic.

**The genre.** Prison management games work when unmet needs turn into behaviour. Inmates have Maslow-style needs; a timetable decides where they may go; rooms only function with the right equipment; frustration becomes fights, escapes and riots. Ironvale uses that loop with its own art, names, numbers and rules.

**Technology.** three.js r187 with the WebGL 2 renderer (the WebGPU renderer is still labelled experimental). Instanced meshes keep draw calls low: one per object type and one per body part for all people. Post-processing is ground-truth ambient occlusion, bloom and filmic tone mapping.

## Design

- **Grid.** 84 x 64 tiles. Walls occupy a tile but are drawn thin and join their neighbours. No roofs: the view is a cutaway.
- **Rooms** are painted zones. Connected tiles of one type form a room, which is valid when it has its required objects, enough floor and, for cells, sealed walls with a door.
- **Agents** run short plans (walk, use, follow). Regime changes interrupt them. Paths use A* with separate passability for inmates and staff, so Staff Doors and Gates are real security.
- **Escape** uses a distance field from the map edge over inmate-passable tiles. If a room can reach the edge, inmates will eventually run for it.
- **Anger** follows a weighted sum of unmet needs. Above a threshold it causes fights; prison-wide it causes a riot.
- **Economy.** Daily state grant per inmate by security level, workshop income, release bonuses and milestone grants, against wages, food and construction.

## Not in this version

Power and water networks, gangs, multi-storey buildings, parole hearings and guard dogs.
