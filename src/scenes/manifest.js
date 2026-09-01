/**
 * Every scene the game can travel to, and every cutscene it can play.
 *
 * Add a scene by dropping its JSON in this folder and adding one line here.
 * The editor reads this list too, so a new scene shows up in the door
 * inspector's target dropdown without any further wiring.
 */
export const SCENES = {
  cabin_bedroom: 'src/scenes/cabin_bedroom.json',
  cabin_landing: 'src/scenes/cabin_landing.json',
  cabin_drive: 'src/scenes/cabin_drive.json',
  station_gate: 'src/scenes/station_gate.json',
  station_lobby: 'src/scenes/station_lobby.json',
  office_wing: 'src/scenes/office_wing.json',
  canteen: 'src/scenes/canteen.json',
  laboratory: 'src/scenes/laboratory.json',
  security_room: 'src/scenes/security_room.json',
  stairwell: 'src/scenes/stairwell.json',
  sublevel_3: 'src/scenes/sublevel_3.json',
};

export const START_SCENE = 'cabin_bedroom';
export const START_SPAWN = 'wake';

/**
 * Cutscenes are scripted passes over a single still. See game/cutscene.js for
 * the step vocabulary.
 */
export const CUTSCENES = {
  arrival: {
    id: 'arrival',
    image: 'stills/facility_exterior_night.png',
    ambience: 'forest_night',
    fadeFrom: 1,
    // The still is 768x434; the window below is 384x216, so a view of that
    // size is a 1:1 crop and anything larger is zoomed out.
    view: { x: 40, y: 150, w: 384, h: 216 },
    steps: [
      { fadeTo: 0, duration: 2.2 },
      { text: 'BLACKRIDGE STATION', style: 'title', duration: 2.6 },
      { text: null, duration: 0.4 },
      { view: { x: 190, y: 96, w: 520, h: 293 }, duration: 7.0 },
      { text: 'Forty minutes up the ridge. Same gate, same wire.', duration: 3.4 },
      { view: { x: 300, y: 150, w: 300, h: 169 }, duration: 5.0,
        text: "The barrier's up. Nobody's in the booth." },
      { text: null, duration: 0.6 },
      { fadeTo: 1, duration: 1.8 },
    ],
    // The pan hands off to the gate rather than returning to the drive, so the
    // drive up the mountain actually arrives somewhere.
    then: { scene: 'station_gate', spawn: 'from_road' },
  },
};
