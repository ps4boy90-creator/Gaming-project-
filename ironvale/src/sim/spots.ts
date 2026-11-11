import { OBJ } from '../data/defs';
import { objLocalToWorld, rotYaw, type World, type WorldObject } from '../world/world';
import type { AnimPose } from './agent';

export interface Spot {
  /** tile to walk to */
  tile: number;
  /** exact position and pose while using */
  px: number;
  pz: number;
  y: number;
  yaw: number;
  pose: AnimPose;
}

/** local (x, z, facing) per slot. facing: 0 = same as object front (+Z), 1 = towards the object (-Z) */
const FRONT: Record<string, [number, number, number][]> = {
  serving_counter: [[-0.6, 0.95, 1], [0, 0.95, 1], [0.6, 0.95, 1]],
  cooker: [[0, 0.85, 1]],
  kitchen_counter: [[0, 0.85, 1]],
  laundry_machine: [[0, 0.85, 1]],
  workshop_press: [[0, 0.85, 1]],
  workshop_saw: [[0, 0.85, 1]],
  bookshelf: [[0, 0.8, 1]],
  phone: [[0, 0.75, 1]],
  punching_bag: [[0, 0.75, 1]],
  tv: [[-0.8, 1.2, 1], [0, 1.5, 1], [0.8, 1.2, 1], [0.1, 2.3, 1]],
  pool_table: [[-0.5, 0.95, 1], [0.5, -0.95, 0]],
  basketball_hoop: [[-0.9, 1.4, 1], [0.8, 1.9, 1], [0, 2.7, 1], [-0.4, 0.9, 1]],
  blackboard: [[0, 0.85, 0]],
  altar: [[0, 0.9, 0]],
  cctv_monitor: [[0, 0.32, 1]],
  medicine_cabinet: [[0, 0.8, 1]],
};
const SEATS: Record<string, [number, number][]> = {
  toilet: [[0, 0.08]],
  chair: [[0, 0.02]],
  school_desk: [[0, -0.16]],
  bench: [[-0.5, 0], [0.5, 0]],
  pew: [[-0.5, 0.02], [0.5, 0.02]],
  sofa: [[-0.48, 0.05], [0.48, 0.05]],
  outdoor_bench: [[-0.5, 0.03], [0.5, 0.03]],
  office_desk: [[0.5, -0.5]],
  visit_table: [[0, -1]],
};

/** Where an agent stands / sits / lies to use slot `slot` of object `o`. */
export function useSpot(world: World, o: WorldObject, slot: number): Spot {
  const def = OBJ[o.type];
  const yaw = rotYaw(o.rot);
  const tileOf = (wx: number, wz: number) => {
    const tx = Math.floor(wx), tz = Math.floor(wz);
    if (world.inb(tx, tz) && world.cost[0][world.idx(tx, tz)]) return world.idx(tx, tz);
    return world.idx(o.x, o.y);
  };
  if (def.pose === 'lie' || o.type === 'weight_bench') {
    const [px, pz] = objLocalToWorld(o, 0, 0);
    const y = (def.seatH ?? 0.34) + (o.type === 'bunk' && slot === 1 ? 0.62 : 0);
    return { tile: world.idx(o.x, o.y), px, pz, y, yaw, pose: 'lie' };
  }
  const seat = SEATS[o.type];
  if (seat) {
    const s = seat[Math.min(slot, seat.length - 1)];
    const [px, pz] = objLocalToWorld(o, s[0], s[1]);
    const facing = o.type === 'cctv_monitor' ? yaw + Math.PI : yaw;
    return { tile: tileOf(px, pz), px, pz, y: def.seatH ?? 0.26, yaw: facing, pose: 'sit' };
  }
  const front = FRONT[o.type];
  if (front) {
    const s = front[Math.min(slot, front.length - 1)];
    const [px, pz] = objLocalToWorld(o, s[0] * (def.w > 1 || Math.abs(s[0]) > 0.7 ? 1 : 1), s[1] + (def.d - 1) / 2);
    const tx = Math.floor(px), tz = Math.floor(pz);
    const ok = world.inb(tx, tz) && world.cost[0][world.idx(tx, tz)] !== 0;
    const pose: AnimPose = o.type === 'cctv_monitor' ? 'sit' : def.pose === 'work' ? 'work' : o.type === 'punching_bag' ? 'fight' : def.pose === 'exercise' ? 'exercise' : 'stand';
    if (!ok) {
      const [cx, cz] = objLocalToWorld(o, 0, 0);
      return { tile: world.idx(o.x, o.y), px: cx, pz: cz, y: 0, yaw, pose };
    }
    return { tile: world.idx(tx, tz), px, pz, y: o.type === 'cctv_monitor' ? 0.26 : 0, yaw: s[2] ? yaw + Math.PI : yaw, pose };
  }
  if (o.type === 'guard_tower') {
    const [px, pz] = objLocalToWorld(o, 0, 0);
    return { tile: world.idx(o.x, o.y), px, pz, y: 1.9, yaw, pose: 'stand' };
  }
  const [px, pz] = objLocalToWorld(o, 0, 0);
  return { tile: world.idx(o.x, o.y), px, pz, y: 0, yaw, pose: 'stand' };
}

/** the visitor's seat on the far side of a visiting table */
export function visitorSpot(world: World, o: WorldObject): Spot {
  const yaw = rotYaw(o.rot);
  const [px, pz] = objLocalToWorld(o, 0, 1);
  const tx = Math.floor(px), tz = Math.floor(pz);
  return { tile: world.idx(tx, tz), px, pz, y: 0.26, yaw: yaw + Math.PI, pose: 'sit' };
}
