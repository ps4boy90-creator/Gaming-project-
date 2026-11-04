import * as THREE from 'three';
import { Kit, Opening } from './kit';
import * as P from './props';
import { buildKestrel, buildMule } from './craft';
import { colonist } from '../../systems/manifest';

/*  CSV Meridian: walkable interior.
 *  Axes: +x toward the bow, +y up, +z starboard (the planet side).
 *  Habitat decks: 1 Command (y=8), 2 Crew (y=4), 3 Science (y=0).
 *  Lift lobby at the aft end of each deck; the spine leaves Deck 3 aft to the cryo vault,
 *  the suit room, the decon airlock and the hangar. */

export const DECK_Y = { command: 8, crew: 4, science: 0 } as const;
export const H = 3;
const CZ = 1.5;
const HULL = 9;

export const LIFT = { x0: -17.4, x1: -14.6, z0: -5.8, z1: -3.0 };

const door = (at: number, w: number, code: string, name: string, deck: string, side: 1 | -1, sub = ''): Opening => ({
  at,
  w,
  y0: 0,
  y1: 2.2,
  kind: 'door',
  sign: { code, name, deck, side, sub },
});
const win = (at: number, w: number, y0 = 0.9, y1 = 2.35): Opening => ({ at, w, y0, y1, kind: 'window' });

export interface ShipRefs {
  holoPos: THREE.Vector3;
  bedSeatId: string;
  startPos: THREE.Vector3;
}

export function buildLayout(k: Kit): ShipRefs {
  const refs: ShipRefs = { holoPos: new THREE.Vector3(), bedSeatId: '', startPos: new THREE.Vector3() };
  liftAndLobby(k, 'command', DECK_Y.command);
  liftAndLobby(k, 'crew', DECK_Y.crew);
  liftAndLobby(k, 'science', DECK_Y.science);
  deckCommand(k, refs);
  deckCrew(k, refs);
  deckScience(k);
  spineAndVault(k);
  hangar(k);
  k.finishShells();
  return refs;
}

// --------------------------------------------------------------------------- lift

function liftAndLobby(k: Kit, deck: string, y: number): void {
  const names: Record<string, string> = { command: 'Command', crew: 'Crew', science: 'Science' };
  const num = deck === 'command' ? 1 : deck === 'crew' ? 2 : 3;
  k.room({ id: `lobby-${deck}`, name: `Deck ${num} · Lift lobby`, deck, x0: -18, x1: -14, z0: -3, z1: 3, y0: y, ambience: 'hab' }, { spacing: 2.2, intensity: 5 });
  // aft wall: Deck 3 opens into the spine
  k.wallX(-18, -3, 3, y, {
    mat: 'wallDark',
    accent: deck,
    openings: deck === 'science' ? [{ at: 0, w: 2.2, y0: 0, y1: 2.1, kind: 'door', heavy: true, sign: { code: '3-00', name: 'Spine · Cryo · Hangar', deck: 'spine', side: 1 } }] : [],
  });
  k.wallZ(3, -18, -14, y, { mat: 'wallDark', accent: deck });
  k.wallZ(-3, -18, -14, y, {
    mat: 'wallDark',
    accent: deck,
    openings: [{ at: -16, w: 1.5, y0: 0, y1: 2.2, kind: 'door', id: `lift-${deck}`, sign: { code: `${num}-LIFT`, name: 'Lift', deck, side: 1 } }],
  });
  // deck banner on the lobby wall
  k.stencil(`DECK ${num} · ${names[deck].toUpperCase()}`, deck, new THREE.Vector3(-15.9, y + 1.85, 2.88), Math.PI, 0.36, num);
  // lift car
  k.room({ id: `lift-${deck}`, name: 'Lift', deck, x0: LIFT.x0, x1: LIFT.x1, z0: LIFT.z0, z1: LIFT.z1, y0: y, ambience: 'lift' }, { floor: 'deckPlate', lights: 'grid', spacing: 3, intensity: 3, lightMat: 'lightWarm', profile: 'none' });
  k.wallX(LIFT.x0, LIFT.z0, LIFT.z1, y, { mat: 'steel', skirting: false });
  k.wallX(LIFT.x1, LIFT.z0, LIFT.z1, y, { mat: 'steel', skirting: false });
  k.wallZ(LIFT.z0, LIFT.x0, LIFT.x1, y, { mat: 'steel', skirting: false });
  k.b.box(LIFT.x0 + 0.1, y + 0.95, LIFT.z0 + 0.1, LIFT.x0 + 0.14, y + 1.0, LIFT.z1 - 0.2, 'chrome', false);
  // panel on the inner starboard face of the car's forward wall
  const px = LIFT.x1 - 0.11;
  k.b.box(px - 0.03, y + 0.9, -3.9, px + 0.01, y + 1.5, -3.4, 'paintDark', false);
  k.screen('lift', new THREE.Vector3(px - 0.04, y + 1.62, -3.65), -Math.PI / 2, 0.36, 1, '', 0);
  const decks: [string, number, string][] = [
    ['command', 1.38, 'Deck 1 · Command'],
    ['crew', 1.22, 'Deck 2 · Crew'],
    ['science', 1.06, 'Deck 3 · Science & spine'],
  ];
  for (const [target, by, label] of decks) {
    k.b.box(px - 0.05, y + by - 0.04, -3.72, px - 0.02, y + by + 0.04, -3.58, target === deck ? 'statusAmber' : 'statusGreen', false);
    k.item({ id: k.uid('liftbtn'), min: [px - 0.2, y + by - 0.07, -3.8], max: [px, y + by + 0.07, -3.5], prompt: target === deck ? `${label} (here)` : `Go to ${label}`, action: 'lift', data: target, range: 1.6 });
  }
}

// --------------------------------------------------------------------------- Deck 1

function deckCommand(k: Kit, refs: ShipRefs): void {
  const y = DECK_Y.command;
  const d = 'command';
  k.room({ id: 'c-corridor', name: 'Deck 1 · Corridor', deck: d, x0: -14, x1: 8, z0: -CZ, z1: CZ, y0: y, ambience: 'hab' }, { profile: 'corridor', intensity: 6 });
  k.wallZ(CZ, -14, 8, y, { accent: d, openings: [door(-10, 1.4, '1-02', 'Comms & Nav', d, -1), door(0, 2.0, '1-03', 'Observation', d, -1)] });
  k.wallZ(-CZ, -14, 8, y, { accent: d, openings: [door(-9, 1.4, '1-04', 'Ready room', d, 1), door(2, 1.6, '1-05', 'Briefing', d, 1)] });
  k.wallX(-14, CZ, HULL, y, {});
  k.wallX(-14, -HULL, -CZ, y, {});
  k.wallX(-6, CZ, HULL, y, {});
  k.wallX(-4, -HULL, -CZ, y, {});
  k.wallZ(HULL, -14, -6, y, { t: 0.4, offset: 0.2, openings: [win(-10, 2.2)] });
  k.wallZ(-HULL, -14, 8, y, { t: 0.4, offset: -0.2, openings: [win(-9, 2.2), win(2, 3.2)] });
  // bridge aft bulkhead (also the forward walls of the dome and briefing room)
  k.wallX(8, -HULL, HULL, y, { accent: d, openings: [{ ...door(0, 2.0, '1-01', 'Bridge', d, -1), heavy: true, y1: 2.1 }] });

  // Comms & Nav
  k.room({ id: 'comms', name: 'Comms & Nav', deck: d, x0: -14, x1: -6, z0: CZ, z1: HULL, y0: y, ambience: 'hab' }, { intensity: 5 });
  P.consoleUnit(k, { x: -13.45, y, z: 5.2, rot: 1 }, 2.6, ['comms', 'nav'], 11);
  P.chair(k, { x: -12.45, y, z: 5.2, rot: 3 }, 'Comms chair');
  k.item({ id: 'signal', min: [-13.9, y + 0.8, 3.9], max: [-12.9, y + 1.7, 6.5], prompt: 'Listen to the signal', action: 'signal' });
  P.consoleUnit(k, { x: -7.5, y, z: 8.55, rot: 2 }, 2.4, ['telemetry', 'orbit'], 12);
  P.plant(k, { x: -6.6, y, z: 2.2 }, 1.1);

  // Observation dome: floor-to-ceiling glass, skylight
  const dome = k.room({ id: 'dome', name: 'Observation dome', deck: d, x0: -6, x1: 8, z0: CZ, z1: HULL, y0: y, ambience: 'hab' }, { ceil: null, lights: 'none', profile: 'none' });
  const domeGlass: Opening[] = [-4.6, -1.8, 1.0, 3.8, 6.6].map((x) => ({ at: x, w: 2.5, y0: 0.15, y1: 2.85, kind: 'window' as const }));
  k.wallZ(HULL, -6, 8, y, { t: 0.4, offset: 0.2, openings: domeGlass, skirting: false });
  // skylight: beams + glass
  for (let x = -6; x <= 8.01; x += 2.8) k.b.box(x - 0.1, y + 3.0, CZ, x + 0.1, y + 3.3, HULL + 0.4, 'metal', 'solid');
  k.b.box(-6, y + 3.0, CZ, 8, y + 3.3, CZ + 0.6, 'metal', 'solid');
  k.b.box(-6, y + 3.1, CZ + 0.6, 8, y + 3.12, HULL + 0.4, 'glass', 'solid');
  // floor-level lighting only: soft strips along the inner wall
  k.b.box(-5.9, y + 0.02, CZ + 0.15, 7.9, y + 0.06, CZ + 0.25, 'lightWarm', false);
  k.lights.add({ x: 1, y: y + 0.4, z: CZ + 0.6, color: new THREE.Color(1, 0.75, 0.5), intensity: 3, distance: 8 });
  k.lights.add({ x: -3.5, y: y + 0.4, z: CZ + 0.6, color: new THREE.Color(1, 0.75, 0.5), intensity: 2, distance: 7 });
  void dome;
  P.bench(k, { x: -3.2, y, z: 6.4, rot: 0 }, 2.4, 'Viewing bench', true);
  P.bench(k, { x: 1.0, y, z: 6.4, rot: 0 }, 2.4, 'Viewing bench', true);
  P.bench(k, { x: 5.0, y, z: 5.4, rot: 0 }, 1.8, 'Viewing bench', true);
  P.telescope(k, { x: 6.6, y, z: 7.8, rot: 0 });
  P.plant(k, { x: -5.4, y, z: 2.2 }, 1.2);
  P.plant(k, { x: 7.3, y, z: 2.2 }, 0.9);
  k.poster('Haven awaits', ['2,400 colonists', 'One new world', 'HAVEN COLONIAL TRUST'], 'crew', new THREE.Vector3(-2.5, y + 1.55, CZ + 0.12), 0);

  // Captain's ready room
  k.room({ id: 'ready', name: "Captain's ready room", deck: d, x0: -14, x1: -4, z0: -HULL, z1: -CZ, y0: y, ambience: 'hab' }, { intensity: 5, lightColor: 0xffe2c0 });
  P.desk(k, { x: -10.5, y, z: -7.6, rot: 2 }, 'orbit', 21, 1.8);
  P.chair(k, { x: -10.5, y, z: -8.35, rot: 0 }, "Captain's chair");
  P.chair(k, { x: -11.1, y, z: -6.6, rot: 2 }, 'Visitor chair');
  P.chair(k, { x: -9.9, y, z: -6.6, rot: 2 }, 'Visitor chair');
  P.couch(k, { x: -4.6, y, z: -5.0, rot: 3 }, 2.2, 'Couch');
  P.shelves(k, { x: -13.5, y, z: -5.2, rot: 1 }, 2.4, 4, 0.4);
  P.plant(k, { x: -4.7, y, z: -8.3 });
  k.item({ id: 'captainlog', min: [-11.2, y + 0.8, -8.0], max: [-9.8, y + 1.5, -7.2], prompt: "Captain's terminal", action: 'flavor', data: 'captainlog' });

  // Briefing
  k.room({ id: 'briefing', name: 'Briefing room', deck: d, x0: -4, x1: 8, z0: -HULL, z1: -CZ, y0: y, ambience: 'hab' }, { intensity: 5 });
  P.table(k, { x: 2, y, z: -5.4, rot: 0 }, 4.4, 1.6);
  for (const x of [0.4, 1.5, 2.6, 3.6]) {
    P.chair(k, { x, y, z: -6.6, rot: 0 }, 'Briefing chair');
    P.chair(k, { x, y, z: -4.2, rot: 2 }, 'Briefing chair');
  }
  k.screen('map', new THREE.Vector3(7.85, y + 1.6, -5.4), -Math.PI / 2, 2.2, 31, 'SURVEY PLAN · KX-7c', 0);

  // Bridge
  k.room({ id: 'bridge', name: 'Bridge', deck: d, x0: 8, x1: 17, z0: -6, z1: 6, y0: y, ambience: 'hab' }, { intensity: 4, lightColor: 0xdfe8ff, spacing: 3.5 });
  k.wallZ(6, 8, 17, y, { t: 0.4, offset: 0.2, openings: [win(11, 2.6, 0.75, 2.45), win(14.5, 2.6, 0.75, 2.45)] });
  k.wallZ(-6, 8, 17, y, { t: 0.4, offset: -0.2, openings: [win(12.5, 2.6, 0.75, 2.45)] });
  k.wallX(17, -6, 6, y, { t: 0.4, offset: 0.2, openings: [win(-3.7, 3.0, 0.7, 2.45), win(0, 3.0, 0.7, 2.45), win(3.7, 3.0, 0.7, 2.45)] });
  P.consoleUnit(k, { x: 16.5, y, z: -1.5, rot: 3 }, 2.2, ['telemetry', 'nav'], 41);
  P.consoleUnit(k, { x: 16.5, y, z: 1.5, rot: 3 }, 2.2, ['orbit', 'status'], 43);
  P.chair(k, { x: 15.2, y, z: -1.5, rot: 1 }, 'Pilot seat', 'fabricLight');
  P.chair(k, { x: 15.2, y, z: 1.5, rot: 1 }, 'Co-pilot seat', 'fabricLight');
  P.chair(k, { x: 12.6, y, z: 0, rot: 1 }, "Captain's chair", 'fabricAmber');
  P.consoleUnit(k, { x: 11.2, y, z: 5.55, rot: 2 }, 2.6, ['status', 'telemetry'], 45);
  P.consoleUnit(k, { x: 11.2, y, z: -5.55, rot: 0 }, 2.6, ['comms', 'orbit'], 47);
  refs.holoPos.copy(P.holoTable(k, { x: 10.0, y, z: 0 }));
}

// --------------------------------------------------------------------------- Deck 2

function deckCrew(k: Kit, refs: ShipRefs): void {
  const y = DECK_Y.crew;
  const d = 'crew';
  k.room({ id: 'r-corridor', name: 'Deck 2 · Corridor', deck: d, x0: -14, x1: 14, z0: -CZ, z1: CZ, y0: y, ambience: 'hab' }, { profile: 'corridor', intensity: 6 });
  k.wallZ(CZ, -14, 14, y, {
    accent: d,
    openings: [door(-11, 1.3, '2-01', 'Specialist', d, -1, 'Your quarters'), door(-3, 2.0, '2-03', 'Lounge', d, -1), door(5, 1.6, '2-04', 'Galley & mess', d, -1)],
  });
  k.wallZ(-CZ, -14, 14, y, {
    accent: d,
    openings: [
      { ...door(-12, 1.2, '2-05', 'A. Okonkwo', d, 1), locked: true, label: 'Locked · Capt. Okonkwo — do not disturb' },
      { ...door(-8, 1.2, '2-06', 'H. Brandt', d, 1), locked: true, label: 'Locked · Hollis Brandt — pre-flight, back at 1800' },
      door(-2, 2.0, '2-07', 'Medical', d, 1),
      door(5, 1.4, '2-08', 'Gym & showers', d, 1),
      door(11, 1.6, '2-09', 'Arboretum', d, 1),
    ],
  });
  for (const x of [-8, 2]) k.wallX(x, CZ, HULL, y, {});
  for (const x of [-10, -6, 2, 8]) k.wallX(x, -HULL, -CZ, y, {});
  k.wallX(-14, CZ, HULL, y, {});
  k.wallX(-14, -HULL, -CZ, y, {});
  k.wallX(14, -HULL, HULL, y, { t: 0.4, offset: 0.2, openings: [win(0, 1.4, 1.0, 2.2)] });
  k.wallZ(HULL, -14, 14, y, {
    t: 0.4,
    offset: 0.2,
    openings: [win(-9.8, 1.8, 1.0, 2.3), win(-6.0, 2.3, 0.55, 2.45), win(-3.0, 2.3, 0.55, 2.45), win(0.0, 2.3, 0.55, 2.45), win(6, 2.4), win(10.6, 2.4)],
  });
  k.wallZ(-HULL, -14, 14, y, { t: 0.4, offset: -0.2, openings: [win(-2, 1.6, 1.1, 2.2), win(5, 2.4), win(11, 4.2, 0.75, 2.45)] });
  k.poster('Protocol 7', ['Decontaminate.', 'Every time.', 'HCT SAFETY'], 'aft', new THREE.Vector3(1.0, y + 1.5, -CZ + 0.12), 0);
  k.poster('Haven awaits', ['2,400 colonists', 'One new world', 'HAVEN COLONIAL TRUST'], 'crew', new THREE.Vector3(8.5, y + 1.5, CZ - 0.12), Math.PI);

  // Your cabin
  k.room({ id: 'cabin', name: 'Your quarters', deck: d, x0: -14, x1: -8, z0: CZ, z1: HULL, y0: y, ambience: 'hab' }, { intensity: 4, lightColor: 0xffe4c4, lightMat: 'lightWarm', spacing: 3.6 });
  P.bed(k, { x: -12.78, y, z: 7.75, rot: 1 }, 'Your bunk', true);
  refs.bedSeatId = k.seats[k.seats.length - 1].id;
  // built-in sleeping alcove: padded back, canopy with a reading light, foot shelf
  k.b.box(-13.9, y + 0.55, 8.3, -11.55, y + 1.75, 9.0, 'wall', 'solid');
  k.b.box(-13.92, y + 1.72, 6.95, -11.5, y + 1.86, 9.0, 'rib', false, 0.02);
  k.b.box(-13.85, y + 1.69, 7.05, -11.6, y + 1.72, 7.15, 'lightWarm', false);
  k.b.box(-11.62, y, 6.95, -11.48, y + 1.86, 9.0, 'rib', 'solid', 0.02);
  k.b.box(-11.48, y + 0.55, 7.6, -11.2, y + 0.6, 8.9, 'steel', false);
  k.b.box(-11.48, y + 1.1, 7.6, -11.2, y + 1.15, 8.9, 'steel', false);
  P.desk(k, { x: -8.46, y, z: 4.4, rot: 3 }, 'mail', 5, 1.5);
  P.chair(k, { x: -9.3, y, z: 4.4, rot: 1 }, 'Desk chair');
  k.item({ id: 'mail', min: [-8.95, y + 0.75, 3.9], max: [-8.15, y + 1.45, 4.9], prompt: 'Read messages', action: 'mail' });
  P.locker(k, { x: -13.4, y, z: 2.4, rot: 1 }, 0.7, 'Your locker');
  P.locker(k, { x: -13.4, y, z: 3.15, rot: 1 }, 0.7);
  // trophy shelves: empty for now, the planet will fill them
  for (const sy of [1.25, 1.65]) k.b.box(-13.9, y + sy, 4.0, -13.6, y + sy + 0.03, 5.6, 'steel', false);
  k.item({ id: 'trophy', min: [-14, y + 1.0, 4.0], max: [-13.6, y + 1.9, 5.6], prompt: 'Specimen shelf', action: 'flavor', data: 'trophy' });
  P.plant(k, { x: -8.6, y, z: 8.4 }, 0.8);
  k.b.box(-12.4, y + 0.01, 3.3, -10.0, y + 0.02, 6.0, 'fabric', false);

  // Lounge
  k.room({ id: 'lounge', name: 'Recreation lounge', deck: d, x0: -8, x1: 2, z0: CZ, z1: HULL, y0: y, ambience: 'hab' }, { intensity: 4, lightColor: 0xffdcb0, lightMat: 'lightWarm' });
  P.couch(k, { x: -5.4, y, z: 6.9, rot: 0 }, 2.2, 'Couch');
  P.couch(k, { x: -0.8, y, z: 6.9, rot: 0 }, 2.2, 'Couch');
  P.table(k, { x: -3.1, y, z: 7.9, rot: 0 }, 1.0, 0.5, 0.42, 'paintDark');
  P.couch(k, { x: 1.35, y, z: 4.2, rot: 3 }, 2.0, 'Armchair', 'fabricAmber');
  k.screen('telemetry', new THREE.Vector3(-7.88, y + 1.6, 4.6), Math.PI / 2, 1.8, 61, 'FILM LIBRARY', 0);
  P.couch(k, { x: -5.6, y, z: 4.6, rot: 3 }, 1.8, 'Couch');
  P.table(k, { x: -2.4, y, z: 3.2, rot: 0 }, 1.1, 1.1);
  P.chair(k, { x: -2.4, y, z: 2.45, rot: 0 }, 'Card table');
  P.chair(k, { x: -2.4, y, z: 3.95, rot: 2 }, 'Card table');
  P.chair(k, { x: -3.15, y, z: 3.2, rot: 1 }, 'Card table');
  P.wallUnit(k, { x: 1.9, y, z: 2.6, rot: 3 }, 0.7, 0.9, 1.0, 'music', 'Music player', 'music');
  P.plant(k, { x: -7.4, y, z: 8.4 }, 1.2);

  // Galley & mess
  k.room({ id: 'galley', name: 'Galley & mess', deck: d, x0: 2, x1: 14, z0: CZ, z1: HULL, y0: y, ambience: 'hab' }, { intensity: 6 });
  P.counter(k, { x: 13.35, y, z: 5.2, rot: 3 }, 6.4);
  P.wallUnit(k, { x: 13.97, y: y + 0.92, z: 3.0, rot: 3 }, 0.45, 0.55, 0, 'status', 'Make coffee', 'coffee');
  P.wallUnit(k, { x: 13.97, y: y + 0.92, z: 4.0, rot: 3 }, 0.6, 0.55, 0, 'status', 'Food dispenser', 'food');
  for (const z of [4.6, 7.2]) {
    P.table(k, { x: 7.0, y, z, rot: 0 }, 4.0, 0.9);
    P.bench(k, { x: 7.0, y, z: z - 0.75, rot: 0 }, 3.6, 'Mess bench');
    P.bench(k, { x: 7.0, y, z: z + 0.75, rot: 2 }, 3.6, 'Mess bench');
  }
  P.plant(k, { x: 2.6, y, z: 8.4 }, 1.0);

  // Crew quarters (locked, empty)
  k.room({ id: 'q-okonkwo', name: 'Crew quarters', deck: d, x0: -14, x1: -10, z0: -HULL, z1: -CZ, y0: y, ambience: 'hab' }, { lights: 'none' });
  k.room({ id: 'q-brandt', name: 'Crew quarters', deck: d, x0: -10, x1: -6, z0: -HULL, z1: -CZ, y0: y, ambience: 'hab' }, { lights: 'none' });

  // Medical
  k.room({ id: 'med', name: 'Medical bay', deck: d, x0: -6, x1: 2, z0: -HULL, z1: -CZ, y0: y, ambience: 'hab' }, { intensity: 7, lightColor: 0xe8f4ff, lightMat: 'lightCold' });
  P.medBed(k, { x: -2.6, y, z: -5.6, rot: 0 });
  k.screen('vitals', new THREE.Vector3(-1.2, y + 1.7, -8.97), 0, 1.0, 51, '', 0);
  k.item({ id: 'medscan', min: [-1.8, y + 1.2, -9.0], max: [-0.6, y + 2.2, -8.6], prompt: 'Medical scanner', action: 'medscan' });
  for (const x of [-5.4, -4.7, -4.0]) P.locker(k, { x, y, z: -2.1, rot: 2 }, 0.65, '', 'paint');
  P.counter(k, { x: 1.25, y, z: -5.4, rot: 3 }, 4.2);
  P.chair(k, { x: -0.5, y, z: -3.0, rot: 2 }, 'Doctor\'s stool');

  // Gym & showers
  k.room({ id: 'gym', name: 'Gym & showers', deck: d, x0: 2, x1: 8, z0: -HULL, z1: -CZ, y0: y, ambience: 'hab' }, { intensity: 6 });
  P.treadmill(k, { x: 3.5, y, z: -7.2, rot: 2 });
  P.treadmill(k, { x: 4.7, y, z: -7.2, rot: 2 });
  P.weightBench(k, { x: 3.6, y, z: -3.8, rot: 1 });
  P.showerStall(k, { x: 7.35, y, z: -8.3, rot: 3 });
  P.showerStall(k, { x: 7.35, y, z: -7.2, rot: 3 });
  P.bench(k, { x: 6.2, y, z: -4.2, rot: 3 }, 1.6, 'Changing bench');
  for (const z of [-2.2, -2.9]) P.locker(k, { x: 7.4, y, z, rot: 3 }, 0.65);

  // Arboretum
  k.room({ id: 'arbor', name: 'Arboretum', deck: d, x0: 8, x1: 14, z0: -HULL, z1: -CZ, y0: y, ambience: 'garden' }, { intensity: 4, lightColor: 0xffb0e8, lightMat: 'growLight', spacing: 3.8 });
  for (const z of [-3.4, -5.4]) P.planter(k, { x: 11, y, z, rot: 0 }, 4.6);
  P.bench(k, { x: 11, y, z: -7.5, rot: 2 }, 2.2, 'Garden bench');
  P.plant(k, { x: 8.6, y, z: -8.4 }, 1.4);
  P.plant(k, { x: 13.4, y, z: -8.4 }, 1.3);

  refs.startPos.set(-12.78, y, 7.75);
}

// --------------------------------------------------------------------------- Deck 3

function deckScience(k: Kit): void {
  const y = DECK_Y.science;
  const d = 'science';
  k.room({ id: 's-corridor', name: 'Deck 3 · Corridor', deck: d, x0: -14, x1: 14, z0: -CZ, z1: CZ, y0: y, ambience: 'hab' }, { profile: 'corridor', intensity: 6 });
  k.wallZ(CZ, -14, 14, y, { accent: d, openings: [door(-10, 1.6, '3-01', 'Laboratory', d, -1), door(-3, 1.4, '3-02', 'Lab · east', d, -1), { ...door(3, 1.4, '3-03', 'Specimen vault', d, -1), heavy: true, y1: 2.1 }, door(10, 1.4, '3-04', 'Life support', d, -1)] });
  k.wallZ(-CZ, -14, 14, y, { accent: d, openings: [door(-8, 1.6, '3-05', 'Workshop & armory', d, 1), door(6, 1.6, '3-06', 'Stores', d, 1)] });
  for (const x of [0, 6]) k.wallX(x, CZ, HULL, y, { t: x === 0 || x === 6 ? 0.3 : 0.2 });
  k.wallX(-2, -HULL, -CZ, y, {});
  k.wallX(-14, CZ, HULL, y, {});
  k.wallX(-14, -HULL, -CZ, y, {});
  k.wallX(14, -HULL, HULL, y, { t: 0.4, offset: 0.2 });
  k.wallZ(HULL, -14, 14, y, { t: 0.4, offset: 0.2, openings: [win(-11.5, 2.4), win(-7.2, 2.4), win(-2.9, 2.4)] });
  k.wallZ(-HULL, -14, 14, y, { t: 0.4, offset: -0.2, openings: [win(-8, 2.4)] });

  // Laboratory
  k.room({ id: 'lab', name: 'Laboratory', deck: d, x0: -14, x1: 0, z0: CZ, z1: HULL, y0: y, ambience: 'hab' }, { intensity: 7, lightColor: 0xeaf6ff, lightMat: 'lightCold' });
  P.labIsland(k, { x: -7, y, z: 5.2, rot: 0 }, 6);
  P.counter(k, { x: -7.2, y, z: 8.35, rot: 2 }, 13, false);
  for (const x of [-10, -6, -3.5]) P.stool(k, { x, y, z: 6.3, rot: 2 }, 'Lab stool');
  P.consoleUnit(k, { x: -0.6, y, z: 4.6, rot: 3 }, 2.2, ['lab', 'dna'], 71);
  k.item({ id: 'archive', min: [-1.0, y + 0.8, 3.6], max: [-0.1, y + 1.7, 5.6], prompt: 'Research terminal', action: 'research' });
  P.machine(k, { x: -13.4, y, z: 3.0, rot: 1 }, 1.4, 1.0, 2.1, 3);
  k.item({ id: 'hood', min: [-14, y + 0.8, 2.3], max: [-12.9, y + 2.1, 3.7], prompt: 'Fume hood', action: 'flavor', data: 'hood' });
  k.screen('telemetry', new THREE.Vector3(-13.88, y + 1.7, 6.6), Math.PI / 2, 1.4, 73, 'SURFACE SPECTRA', 0);

  // Specimen vault
  k.room({ id: 'specimen', name: 'Specimen vault', deck: d, x0: 0, x1: 6, z0: CZ, z1: HULL, y0: y, ambience: 'vault' }, { intensity: 3, lightColor: 0xa8ffd8, lightMat: 'lightCold' });
  for (const [x, z] of [[1.1, 4.0], [4.9, 4.0], [1.1, 7.6], [4.9, 7.6]]) P.tank(k, { x, y, z }, 'Containment tank · empty');
  k.screen('status', new THREE.Vector3(3.0, y + 1.8, 8.97), Math.PI, 1.1, 81, 'CONTAINMENT', 0);

  // Life support
  k.room({ id: 'lifesupport', name: 'Life support', deck: d, x0: 6, x1: 14, z0: CZ, z1: HULL, y0: y, ambience: 'machine' }, { intensity: 4, lightColor: 0xfff0d0 });
  P.machine(k, { x: 8.2, y, z: 7.6, rot: 2 }, 2.4, 1.6, 2.4, 1);
  P.machine(k, { x: 12.0, y, z: 7.6, rot: 2 }, 2.6, 1.6, 2.2, 2);
  P.machine(k, { x: 13.1, y, z: 3.6, rot: 3 }, 1.6, 1.4, 1.8, 3);
  k.screen('status', new THREE.Vector3(6.17, y + 1.6, 4.0), Math.PI / 2, 1.0, 91, 'ATMOSPHERE', 0);

  // Workshop & armory
  k.room({ id: 'workshop', name: 'Workshop & armory', deck: d, x0: -14, x1: -2, z0: -HULL, z1: -CZ, y0: y, ambience: 'hab' }, { intensity: 6 });
  P.counter(k, { x: -9.5, y, z: -8.35, rot: 0 }, 5, false);
  P.weaponRack(k, { x: -13.45, y, z: -5.0, rot: 1 });
  P.shelves(k, { x: -2.7, y, z: -5.6, rot: 3 }, 3.0);
  P.table(k, { x: -7.0, y, z: -5.0, rot: 0 }, 2.4, 1.2, 0.9, 'steel');
  P.stool(k, { x: -7.0, y, z: -4.1, rot: 2 }, 'Workbench stool');
  for (const x of [-12.5, -11.7]) P.locker(k, { x, y, z: -2.1, rot: 2 }, 0.75);
  k.item({ id: 'bench', min: [-8.2, y + 0.8, -5.6], max: [-5.8, y + 1.2, -4.4], prompt: 'Workbench', action: 'flavor', data: 'workbench' });

  // Stores
  k.room({ id: 'stores', name: 'Stores', deck: d, x0: -2, x1: 14, z0: -HULL, z1: -CZ, y0: y, ambience: 'machine' }, { intensity: 4 });
  for (const z of [-4.2, -6.8]) {
    P.shelves(k, { x: 4.0, y, z, rot: 0 }, 6.0, 4, 0.55);
    P.shelves(k, { x: 4.0, y, z: z - 1.1, rot: 2 }, 6.0, 4, 0.55);
  }
  P.crate(k, 10.5, y, -6, 1.2, 1.0, 1.2);
  P.crate(k, 10.5, y + 1.0, -6, 1.0, 0.8, 1.0, 'paint');
  P.crate(k, 12.2, y, -7.5, 1.2, 1.2, 1.2);
  P.crate(k, 12.0, y, -3.6, 1.4, 0.9, 1.0, 'accent-spine');
}

// --------------------------------------------------------------------------- Spine & vault

function spineAndVault(k: Kit): void {
  const y = 0;
  const d = 'spine';
  k.room({ id: 'spine', name: 'Main spine', deck: d, x0: -70, x1: -18, z0: -2, z1: 2, y0: y, ambience: 'spine' }, { profile: 'corridor', intensity: 5, lightColor: 0xf0f4ff, rib: 3.0 });
  const starboard: Opening[] = [];
  for (let x = -66; x <= -22; x += 6) starboard.push(win(x, 1.8, 1.0, 2.3));
  k.wallZ(2, -70, -18, y, { mat: 'wallDark', accent: d, openings: starboard });
  k.wallZ(-2, -70, -18, y, {
    mat: 'wallDark',
    accent: d,
    h: 4.5,
    openings: [
      { at: -30, w: 2.2, y0: 0, y1: 2.25, kind: 'gap' },
      { at: -56, w: 2.2, y0: 0, y1: 2.25, kind: 'gap' },
      { at: -36.5, w: 3.4, y0: 0.9, y1: 2.35, kind: 'inner' },
      { at: -43, w: 3.4, y0: 0.9, y1: 2.35, kind: 'inner' },
      { at: -49.5, w: 3.4, y0: 0.9, y1: 2.35, kind: 'inner' },
    ],
  });
  k.stencil('CRYO VAULT 3 · PODS 0721–0792', 'spine', new THREE.Vector3(-30, y + 2.4, -1.88), 0, 0.2, 7);
  k.stencil('CRYO VAULT 3', 'spine', new THREE.Vector3(-56, y + 2.4, -1.88), 0, 0.2, 8);
  k.stencil('HANGAR · KESTREL · MULE  ▸', 'spine', new THREE.Vector3(-62, y + 1.7, 1.88), Math.PI, 0.3, 9);
  k.stencil('◂  HABITAT · LIFT', 'spine', new THREE.Vector3(-22.6, y + 1.7, -1.88), 0, 0.3, 10);

  // Cryo Vault 3
  k.room({ id: 'vault', name: 'Cryo Vault 3', deck: d, x0: -62, x1: -24, z0: -14, z1: -2, y0: y, h: 4.5, ambience: 'vault' }, { profile: 'hall', intensity: 3.5, lightColor: 0x9fd8ff, lightMat: 'lightCold' });
  k.wallZ(-14, -62, -24, y, { mat: 'wallDark', h: 4.5, accent: d });
  k.wallX(-24, -14, -2, y, { mat: 'wallDark', h: 4.5, accent: d });
  k.wallX(-62, -14, -2, y, {
    mat: 'wallDark',
    h: 4.5,
    accent: d,
    openings: [{ at: -8, w: 2.4, y0: 0, y1: 2.5, kind: 'door', heavy: true, locked: true, label: 'Seed Bank · "the Orchard" · authorised access only', sign: { code: 'SB-01', name: 'Seed Bank', deck: 'aft', side: 1, sub: 'The Orchard' } }],
  });
  let n = 721;
  const failedPods = new Set([734, 768]);
  const rows: { z: number; rot: number }[] = [
    { z: -5.3, rot: 0 },
    { z: -7.55, rot: 2 },
    { z: -11.7, rot: 0 },
  ];
  for (const row of rows) {
    for (let x = -59.5; x <= -26.5; x += 1.32) {
      if (Math.abs(x + 43) < 1.0) continue; // cross aisle
      const id = n++;
      const failed = failedPods.has(id);
      P.cryoPod(k, { x, y, z: row.z, rot: row.rot }, id, failed, colonist(id, failed));
    }
  }
  k.screen('cryo', new THREE.Vector3(-24.12, y + 1.7, -8), -Math.PI / 2, 1.3, 101, '', 0);
  k.screen('cryo', new THREE.Vector3(-61.88, y + 1.7, -4.2), Math.PI / 2, 1.0, 101, '', 0);
  P.pipeRun(k, new THREE.Vector3(-62, y + 4.0, -9.6), new THREE.Vector3(-24, y + 4.0, -9.6), 0.18, 'paintGrey');
  P.pipeRun(k, new THREE.Vector3(-62, y + 4.0, -3.4), new THREE.Vector3(-24, y + 4.0, -3.4), 0.12, 'steel');

  // Suit room
  k.room({ id: 'suitroom', name: 'Suit room', deck: 'aft', x0: -78, x1: -70, z0: -4, z1: 4, y0: y, ambience: 'hab' }, { intensity: 6 });
  k.wallX(-70, -4, 4, y, { mat: 'wallDark', accent: 'aft', openings: [{ at: 0, w: 1.8, y0: 0, y1: 2.1, kind: 'door', heavy: true, sign: { code: '0-10', name: 'Suit room', deck: 'aft', side: 1 } }] });
  k.wallZ(4, -78, -70, y, { mat: 'wallDark', accent: 'aft' });
  k.wallZ(-4, -78, -70, y, { mat: 'wallDark', accent: 'aft' });
  k.wallX(-78, -4, 4, y, { mat: 'wallDark', accent: 'aft', openings: [{ at: 0, w: 1.5, y0: 0, y1: 2.1, kind: 'door', heavy: true, sign: { code: '0-11', name: 'Decon airlock', deck: 'aft', side: 1, both: true } }] });
  const crew = ['Specialist', 'Tanabe', 'Brandt', 'Varga', 'Mensah', 'Okonkwo'];
  crew.slice(0, 3).forEach((name, i) => P.suitLocker(k, { x: -76.5 + i * 1.05, y, z: 3.35, rot: 2 }, name));
  crew.slice(3).forEach((name, i) => P.suitLocker(k, { x: -76.5 + i * 1.05, y, z: -3.35, rot: 0 }, name));
  P.bench(k, { x: -73.6, y, z: 1.9, rot: 2 }, 2.4, 'Suit-room bench');
  k.poster('Protocol 7', ['Decontaminate.', 'Every time.', 'HCT SAFETY'], 'aft', new THREE.Vector3(-71.2, y + 1.6, 3.88), Math.PI);

  // Decon airlock
  k.room({ id: 'decon', name: 'Decontamination airlock', deck: 'aft', x0: -82, x1: -78, z0: -1.5, z1: 1.5, y0: y, ambience: 'lift' }, { intensity: 3, lightColor: 0xffb060, lightMat: 'statusAmber', spacing: 2, lights: 'grid', profile: 'none', floor: 'grating' });
  k.wallZ(1.5, -82, -78, y, { mat: 'steel' });
  k.wallZ(-1.5, -82, -78, y, { mat: 'steel' });
  for (let x = -81.5; x <= -78.5; x += 0.75) {
    for (const z of [1.38, -1.38]) {
      k.b.box(x - 0.04, y + 0.5, z - 0.03, x + 0.04, y + 2.6, z + 0.03, 'metal', false);
    }
  }
  k.screen('decon', new THREE.Vector3(-80.375, y + 1.7, 1.37), Math.PI, 0.6, 111, '', 0);
  k.item({ id: 'decon', min: [-80.6, y + 1.3, 1.1], max: [-79.4, y + 2.1, 1.5], prompt: 'Run decontamination cycle', action: 'decon' });
}

// --------------------------------------------------------------------------- Hangar

function hangar(k: Kit): void {
  const y = 0;
  const d = 'aft';
  k.room({ id: 'hangar', name: 'Hangar bay', deck: d, x0: -112, x1: -82, z0: -15, z1: 15, y0: y, h: 12, ambience: 'hangar' }, { spacing: 7, intensity: 120, lightColor: 0xfff0dc, lights: 'grid', profile: 'hangar' });
  k.wallX(-82, -15, 15, y, { mat: 'wallDark', h: 12, accent: d, openings: [{ at: 0, w: 1.6, y0: 0, y1: 2.2, kind: 'door', heavy: true, sign: { code: '0-12', name: 'Hangar', deck: d, side: -1 } }] });
  k.wallX(-112, -15, 15, y, { mat: 'wallDark', h: 12 });
  k.wallZ(15, -112, -82, y, { mat: 'wallDark', h: 12, accent: d, openings: [win(-91, 4.0, 1.0, 3.6), win(-103, 4.0, 1.0, 3.6)] });
  k.wallZ(-15, -112, -82, y, { mat: 'wallDark', h: 12, accent: d });
  k.stencil('HANGAR · BAY 1', 'aft', new THREE.Vector3(-111.88, y + 7.5, 0), Math.PI / 2, 1.4, 21);
  k.stencil('LND-01 KESTREL', 'aft', new THREE.Vector3(-97, y + 9.5, -14.88), 0, 0.9, 22);
  // belly doors outline
  const bx0 = -108;
  const bx1 = -86;
  const bz0 = -8;
  const bz1 = 2;
  k.b.box(bx0, y + 0.001, bz0 - 0.4, bx1, y + 0.014, bz0, 'hazard', false);
  k.b.box(bx0, y + 0.001, bz1, bx1, y + 0.014, bz1 + 0.4, 'hazard', false);
  k.b.box(bx0 - 0.4, y + 0.001, bz0 - 0.4, bx0, y + 0.014, bz1 + 0.4, 'hazard', false);
  k.b.box(bx1, y + 0.001, bz0 - 0.4, bx1 + 0.4, y + 0.014, bz1 + 0.4, 'hazard', false);
  k.b.box(bx0, y + 0.001, (bz0 + bz1) / 2 - 0.02, bx1, y + 0.008, (bz0 + bz1) / 2 + 0.02, 'paintDark', false);
  // gantry crane
  for (const z of [-12, 12]) k.b.box(-111, y + 10.6, z - 0.3, -83, y + 11.2, z + 0.3, 'accent-aft', false);
  k.b.box(-99, y + 10.4, -12, -97.5, y + 10.6, 12, 'paintDark', false);
  // Kestrel and Mule
  buildKestrel(k, { x: -97, y, z: -3, rot: 1 });
  buildMule(k, { x: -96, y, z: 9.5, rot: 1 });
  k.screen('hangar', new THREE.Vector3(-82.12, y + 1.8, -4.0), -Math.PI / 2, 1.2, 121, '', 0);
  P.crate(k, -85, y, 12.5, 1.4, 1.2, 1.4);
  P.crate(k, -86.6, y, 12.8, 1.2, 0.9, 1.2, 'accent-spine');
  P.crate(k, -85.2, y + 1.2, 12.5, 1.1, 0.8, 1.1, 'paint');
  P.crate(k, -109, y, -12.5, 2.0, 1.6, 2.0);
  P.crate(k, -106.6, y, -12.8, 1.4, 1.0, 1.4, 'paint');
  P.shelves(k, { x: -111.2, y, z: 9, rot: 1 }, 4, 4, 0.7);
  P.locker(k, { x: -89, y, z: -14.4, rot: 0 }, 1.0, 'Tool locker');
  P.locker(k, { x: -90.1, y, z: -14.4, rot: 0 }, 1.0);
}
