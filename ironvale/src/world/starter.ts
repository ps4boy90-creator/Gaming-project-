import {
  DOOR_CELL, DOOR_GATE, DOOR_STAFF, DOOR_STANDARD, R, WALL_BRICK, WALL_CONCRETE, WALL_FENCE, WALL_WINDOW,
} from '../data/defs';
import { rng } from '../core/util';
import type { Sim } from '../sim/sim';
import { ENTRY_X } from '../sim/sim';

const F = { grass: 0, dirt: 1, concrete: 2, polished: 3, tile: 4, checker: 5, wood: 6, carpet: 7, asphalt: 8, paving: 9, court: 10 };

/** A bare plot with an entrance path and a few workmen. */
export function buildEmptyPlot(sim: Sim) {
  const w = sim.world;
  for (let y = w.h - 6; y < w.h; y++) for (let x = ENTRY_X - 1; x <= ENTRY_X + 1; x++) w.setFloor(w.idx(x, y), F.paving);
  sim.money = 80000;
  sim.intake = 2;
  for (let i = 0; i < 4; i++) sim.hire('workman', true);
  sim.sync();
}

/** A small working prison so a new player can watch the simulation straight away. */
export function buildStarterPrison(sim: Sim) {
  const w = sim.world;
  const I = (x: number, y: number) => w.idx(x, y);
  const floor = (x0: number, y0: number, x1: number, y1: number, id: number) => {
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) w.setFloor(I(x, y), id);
  };
  const walls = (x0: number, y0: number, x1: number, y1: number, type = WALL_CONCRETE) => {
    for (let x = x0; x <= x1; x++) { w.setWall(I(x, y0), type); w.setWall(I(x, y1), type); }
    for (let y = y0; y <= y1; y++) { w.setWall(I(x0, y), type); w.setWall(I(x1, y), type); }
  };
  const hline = (x0: number, x1: number, y: number, type = WALL_CONCRETE) => { for (let x = x0; x <= x1; x++) w.setWall(I(x, y), type); };
  const vline = (x: number, y0: number, y1: number, type = WALL_CONCRETE) => { for (let y = y0; y <= y1; y++) w.setWall(I(x, y), type); };
  const door = (x: number, y: number, type: number) => w.setDoor(I(x, y), type);
  const zone = (x0: number, y0: number, x1: number, y1: number, type: number) => {
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) w.setZone(I(x, y), type);
  };
  const obj = (type: string, x: number, y: number, rot = 0) => {
    if (!w.addObject(type, x, y, rot, true)) console.warn('starter: could not place', type, x, y, rot);
  };
  /** building shell: walls, floor and room zone */
  const building = (x0: number, y0: number, x1: number, y1: number, fl: number, wall = WALL_CONCRETE) => {
    floor(x0, y0, x1, y1, fl);
    walls(x0, y0, x1, y1, wall);
  };

  // ---------------------------------------------------------------- grounds
  walls(14, 10, 70, 58, WALL_FENCE);
  door(ENTRY_X, 58, DOOR_GATE);
  floor(ENTRY_X - 1, 57, ENTRY_X + 1, 63, F.paving);
  // paths
  floor(41, 27, 43, 49, F.paving);
  floor(40, 19, 45, 21, F.paving);
  floor(41, 22, 43, 26, F.paving);
  floor(31, 33, 45, 34, F.paving);
  floor(29, 43, 40, 44, F.paving);
  floor(44, 40, 53, 41, F.paving);
  floor(44, 44, 53, 45, F.paving);
  floor(44, 29, 45, 31, F.paving);
  floor(41, 19, 49, 22, F.paving);
  floor(49, 19, 56, 21, F.paving);
  floor(24, 47, 60, 49, F.paving);

  // ---------------------------------------------------------------- cell block (14 cells)
  building(18, 14, 39, 26, F.polished, WALL_BRICK);
  hline(18, 39, 18, WALL_BRICK);
  hline(18, 39, 22, WALL_BRICK);
  for (let k = 0; k < 7; k++) {
    const a = 19 + k * 3;
    if (k > 0) { vline(a - 1, 14, 18, WALL_BRICK); vline(a - 1, 22, 26, WALL_BRICK); }
    // north cell
    door(a + 1, 18, DOOR_CELL);
    w.setWall(I(a, 14), WALL_WINDOW);
    obj('bed', a, 15, 0);
    obj('toilet', a + 1, 15, 0);
    zone(a, 15, a + 1, 17, R.cell);
    // south cell
    door(a + 1, 22, DOOR_CELL);
    w.setWall(I(a, 26), WALL_WINDOW);
    obj('bed', a, 24, 0);
    obj('toilet', a + 1, 25, 2);
    zone(a, 23, a + 1, 25, R.cell);
  }
  door(39, 20, DOOR_STANDARD);
  obj('cctv', 38, 19, 0);
  obj('metal_detector', 40, 20, 1);

  // ---------------------------------------------------------------- showers
  building(42, 13, 48, 18, F.tile);
  for (let x = 43; x <= 47; x++) obj('shower', x, 14, 0);
  obj('toilet', 43, 17, 2);
  obj('sink', 47, 17, 2);
  door(45, 18, DOOR_STANDARD);
  zone(43, 14, 47, 17, R.showers);

  // ---------------------------------------------------------------- solitary
  building(50, 13, 56, 18, F.concrete);
  vline(53, 13, 18);
  door(51, 18, DOOR_CELL);
  door(54, 18, DOOR_CELL);
  zone(51, 14, 52, 17, R.solitary);
  zone(54, 14, 55, 17, R.solitary);

  // ---------------------------------------------------------------- canteen + kitchen
  building(46, 24, 64, 36, F.checker);
  vline(57, 24, 36);
  door(46, 30, DOOR_STANDARD);
  door(46, 33, DOOR_STANDARD);
  door(57, 34, DOOR_STAFF);
  door(64, 30, DOOR_STAFF);
  for (const x of [48, 51]) {
    for (const y of [26, 30]) {
      obj('bench', x, y, 0);
      obj('table', x, y + 1, 0);
      obj('bench', x, y + 2, 2);
    }
  }
  obj('bench', 54, 26, 0);
  obj('table', 54, 27, 0);
  obj('bench', 54, 28, 2);
  obj('bin', 47, 35, 0);
  obj('bin', 56, 35, 0);
  obj('serving_counter', 56, 30, 1);
  obj('serving_counter', 56, 32, 1);
  zone(47, 25, 56, 35, R.canteen);
  for (const y of [25, 27, 29]) obj('cooker', 63, y, 1);
  obj('fridge', 58, 25, 0);
  obj('fridge', 59, 25, 0);
  obj('kitchen_counter', 60, 28, 0);
  obj('kitchen_counter', 60, 31, 0);
  obj('sink', 63, 33, 1);
  obj('bin', 63, 35, 0);
  w.setWall(I(61, 24), WALL_WINDOW);
  w.setWall(I(50, 24), WALL_WINDOW);
  w.setWall(I(53, 24), WALL_WINDOW);
  zone(58, 25, 63, 35, R.kitchen);

  // ---------------------------------------------------------------- common room
  building(18, 30, 30, 38, F.wood);
  door(30, 34, DOOR_STANDARD);
  obj('tv', 24, 31, 0);
  obj('sofa', 23, 34, 2);
  obj('sofa', 26, 34, 2);
  obj('pool_table', 20, 36, 0);
  obj('bookshelf', 19, 31, 0);
  obj('bookshelf', 20, 31, 0);
  obj('phone', 28, 31, 0);
  obj('phone', 29, 31, 0);
  obj('chair', 27, 37, 2);
  obj('chair', 28, 37, 2);
  obj('plant', 29, 37, 0);
  w.setWall(I(22, 30), WALL_WINDOW);
  w.setWall(I(26, 30), WALL_WINDOW);
  zone(19, 31, 29, 37, R.common);

  // ---------------------------------------------------------------- classroom
  building(32, 28, 40, 32, F.wood);
  door(36, 32, DOOR_STANDARD);
  obj('blackboard', 35, 29, 0);
  for (const x of [33, 35, 37, 39]) obj('school_desk', x, 31, 2);
  zone(33, 29, 39, 31, R.classroom);

  // ---------------------------------------------------------------- infirmary
  building(18, 40, 28, 47, F.tile);
  door(28, 43, DOOR_STANDARD);
  obj('medical_bed', 19, 41, 0);
  obj('medical_bed', 21, 41, 0);
  obj('medical_bed', 23, 41, 0);
  obj('medicine_cabinet', 27, 41, 0);
  obj('office_desk', 25, 45, 2);
  obj('sink', 19, 46, 2);
  w.setWall(I(20, 47), WALL_WINDOW);
  w.setWall(I(23, 47), WALL_WINDOW);
  zone(19, 41, 27, 46, R.infirmary);

  // ---------------------------------------------------------------- workshop + laundry
  building(54, 38, 64, 47, F.concrete);
  hline(54, 64, 43);
  door(54, 40, DOOR_STANDARD);
  door(54, 45, DOOR_STANDARD);
  obj('workshop_saw', 56, 39, 0);
  obj('workshop_saw', 59, 39, 0);
  obj('workshop_press', 62, 39, 0);
  obj('crates', 63, 42, 0);
  obj('crates', 62, 42, 0);
  zone(55, 39, 63, 42, R.workshop);
  obj('laundry_machine', 56, 44, 0);
  obj('laundry_machine', 58, 44, 0);
  obj('laundry_machine', 60, 44, 0);
  obj('laundry_basket', 62, 46, 0);
  obj('laundry_basket', 63, 46, 0);
  zone(55, 44, 63, 46, R.laundry);

  // ---------------------------------------------------------------- admin building
  building(24, 50, 60, 56, F.carpet, WALL_BRICK);
  for (const x of [31, 38, 46, 53]) vline(x, 50, 56, WALL_BRICK);
  // warden
  floor(25, 51, 30, 55, F.wood);
  door(28, 50, DOOR_STAFF);
  obj('office_desk', 26, 53, 0);
  obj('filing_cabinet', 30, 51, 0);
  obj('plant', 25, 51, 0);
  obj('sofa', 29, 55, 2);
  w.setWall(I(27, 56), WALL_WINDOW);
  zone(25, 51, 30, 55, R.warden);
  // security
  door(35, 50, DOOR_STAFF);
  obj('cctv_monitor', 32, 54, 2);
  obj('office_desk', 35, 53, 0);
  obj('locker', 37, 51, 0);
  obj('locker', 37, 52, 0);
  w.setWall(I(34, 56), WALL_WINDOW);
  zone(32, 51, 37, 55, R.security);
  // reception
  floor(39, 51, 45, 55, F.polished);
  door(ENTRY_X, 56, DOOR_STAFF);
  door(ENTRY_X, 50, DOOR_STAFF);
  obj('office_desk', 39, 52, 1);
  obj('chair', 45, 52, 3);
  obj('chair', 45, 54, 3);
  obj('plant', 45, 55, 0);
  zone(39, 51, 45, 55, R.reception);
  // visitation
  floor(47, 51, 52, 55, F.tile);
  door(50, 50, DOOR_STANDARD);
  door(46, 53, DOOR_STAFF);
  obj('visit_table', 48, 52, 0);
  obj('visit_table', 50, 52, 0);
  obj('visit_table', 52, 52, 0);
  zone(47, 51, 52, 55, R.visitation);
  // staff room
  door(57, 50, DOOR_STAFF);
  obj('sofa', 54, 55, 2);
  obj('sofa', 57, 55, 2);
  obj('vending', 59, 51, 3);
  obj('table', 55, 52, 0);
  obj('chair', 55, 51, 0);
  obj('chair', 56, 51, 0);
  w.setWall(I(56, 56), WALL_WINDOW);
  zone(54, 51, 59, 55, R.staffroom);

  // ---------------------------------------------------------------- storage shed
  building(62, 50, 68, 55, F.concrete);
  door(62, 52, DOOR_STAFF);
  obj('shelving', 63, 51, 0);
  obj('shelving', 66, 51, 0);
  obj('crates', 67, 54, 0);
  obj('crates', 66, 54, 0);
  zone(63, 51, 67, 54, R.storage);

  // ---------------------------------------------------------------- yard
  floor(31, 37, 52, 46, F.dirt);
  floor(33, 39, 40, 45, F.court);
  floor(41, 37, 43, 46, F.paving);
  zone(31, 37, 52, 46, R.yard);
  obj('basketball_hoop', 36, 39, 0);
  obj('weight_bench', 46, 38, 0);
  obj('weight_bench', 48, 38, 0);
  obj('punching_bag', 50, 38, 0);
  obj('outdoor_bench', 46, 46, 2);
  obj('outdoor_bench', 49, 46, 2);
  obj('phone', 52, 43, 3);
  obj('lamp_post', 31, 37, 0);
  obj('lamp_post', 52, 37, 0);
  obj('lamp_post', 31, 46, 0);
  obj('lamp_post', 52, 46, 0);
  obj('cctv', 44, 37, 0);
  obj('cctv', 47, 34, 0);

  // ---------------------------------------------------------------- grounds dressing
  obj('guard_tower', 67, 11, 0);
  obj('guard_tower', 15, 55, 0);
  obj('lamp_post', 16, 12, 0);
  obj('lamp_post', 40, 12, 0);
  obj('lamp_post', 68, 30, 0);
  obj('lamp_post', 16, 34, 0);
  obj('lamp_post', 40, 57, 0);
  obj('lamp_post', 44, 57, 0);
  obj('flagpole', 44, 60, 0);
  obj('dumpster', 66, 33, 0);
  for (const [x, y] of [[38, 60], [46, 61], [36, 61], [48, 60], [22, 60], [62, 60], [16, 28], [16, 44], [66, 22], [66, 44], [34, 12], [58, 12], [60, 22]]) obj('tree', x, y, rng.int(0, 3));
  for (const [x, y] of [[39, 59], [45, 59], [26, 57], [29, 57], [33, 57], [51, 57], [55, 57], [58, 57]]) obj('bush', x, y, 0);
  for (const [x, y] of [[40, 59], [44, 59], [40, 60]]) obj('flower_bed', x, y, 0);

  // ---------------------------------------------------------------- people and state
  sim.sync();
  sim.money = 25000;
  sim.meals = 24;
  sim.intake = 2;
  const place = (role: Parameters<Sim['hire']>[0], roomType: number) => {
    const a = sim.hire(role, true);
    const rooms = w.roomsOf(roomType);
    if (a && rooms.length) {
      const r = rng.pick(rooms);
      const t = rng.pick(r.tiles);
      a.x = (t % w.w) + 0.5;
      a.z = Math.floor(t / w.w) + 0.5;
    }
    return a;
  };
  place('warden', R.warden);
  place('guard', R.yard);
  place('guard', R.canteen);
  place('guard', R.security);
  place('guard', R.yard);
  place('guard', R.common);
  place('cook', R.kitchen);
  place('cook', R.kitchen);
  place('doctor', R.infirmary);
  place('janitor', R.staffroom);
  place('teacher', R.classroom);
  place('workman', R.storage);
  place('workman', R.storage);
  // the first inmates are already inside
  const cells = w.validRoomsOf(R.cell);
  for (let i = 0; i < 9; i++) {
    const a = sim.spawnPrisoner();
    a.p!.processed = true;
    a.p!.mode = 'normal';
    a.pass = 1;
    sim.assignBed(a);
    const r = cells[i % Math.max(1, cells.length)];
    if (r) {
      a.x = r.cx + 0.5;
      a.z = r.cy + 0.5;
    }
    a.p!.served = rng.range(0, 1.5);
  }
  sim.stats.intake = 9;
  sim.primeObjectives();
}
