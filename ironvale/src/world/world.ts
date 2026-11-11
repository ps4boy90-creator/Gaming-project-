import {
  MAP_W, MAP_H, OBJ, ROOMS, FLOORS, WALLS, DOORS, WALL_FENCE, WALL_PERIMETER, DOOR_STAFF, DOOR_GATE,
  type ObjectDef,
} from '../data/defs';
import { b64decode, b64encode } from '../core/util';

export interface WorldObject {
  id: number;
  type: string;
  /** min-corner tile of the (rotated) footprint */
  x: number;
  y: number;
  /** 0..3 quarter turns clockwise seen from above */
  rot: number;
  built: boolean;
  /** agent ids currently using / reserving this object */
  users: number[];
  /** construction progress 0..1 while !built */
  progress: number;
}

export interface Room {
  id: number;
  type: number;
  tiles: number[];
  objects: number[];
  valid: boolean;
  missing: string[];
  capacity: number;
  /** centre tile for labels */
  cx: number;
  cy: number;
  minX: number; minY: number; maxX: number; maxY: number;
  dirt: number;
  outdoor: boolean;
}

export const PASS_STAFF = 0;
export const PASS_PRISONER = 1;

/** footprint size after rotation */
export function footprint(def: ObjectDef, rot: number): [number, number] {
  return rot % 2 === 0 ? [def.w, def.d] : [def.d, def.w];
}

/**
 * Convert a local model-space offset (lx, lz) (model centred on footprint, front = +Z)
 * to world space for an object.
 */
export function objLocalToWorld(o: WorldObject, lx: number, lz: number): [number, number] {
  const def = OBJ[o.type];
  const [fw, fd] = footprint(def, o.rot);
  const cx = o.x + fw / 2;
  const cz = o.y + fd / 2;
  // rot quarter-turns: yaw = -rot * 90deg (clockwise from above)
  switch (o.rot & 3) {
    case 0: return [cx + lx, cz + lz];
    case 1: return [cx - lz, cz + lx];
    case 2: return [cx - lx, cz - lz];
    default: return [cx + lz, cz - lx];
  }
}
/** yaw (radians, three.js Y rotation) for an object rotation */
export function rotYaw(rot: number): number {
  return -(rot & 3) * Math.PI / 2;
}

export class World {
  readonly w = MAP_W;
  readonly h = MAP_H;
  readonly n = MAP_W * MAP_H;
  floor = new Uint8Array(this.n);
  wall = new Uint8Array(this.n);
  door = new Uint8Array(this.n);
  zone = new Uint8Array(this.n);
  /** planned (blueprint) layers; 0 = nothing planned. planFloor uses id+1 so that grass can be planned. */
  planWall = new Uint8Array(this.n);
  planDoor = new Uint8Array(this.n);
  planFloor = new Uint8Array(this.n);
  /** object id occupying each tile (0 = none) */
  objAt = new Int32Array(this.n);
  /** room id per tile (0 = none) */
  roomAt = new Int32Array(this.n);
  /** path cost per tile for each pass class (0 = blocked) */
  cost: Uint8Array[] = [new Uint8Array(this.n), new Uint8Array(this.n)];
  /** BFS distance to the map edge for prisoners; 65535 = sealed in */
  escapeDist = new Uint16Array(this.n);
  /** true where the tile is indoors (has a non-outdoor floor) */
  objects = new Map<number, WorldObject>();
  rooms = new Map<number, Room>();
  roomsByType = new Map<number, Room[]>();
  nextObjId = 1;
  nextRoomId = 1;

  // dirty flags consumed by renderers / sim
  dirtyFloor = true;
  dirtyWalls = true;
  dirtyObjects = true;
  dirtyZones = true;
  dirtyPlans = true;
  /** topology changed: costs / rooms / escape map need recomputing */
  dirtyTopo = true;
  /** increments every time the walkable topology is rebuilt */
  topoVersion = 0;
  /** persisted dirt per room keyed by first tile, used to carry dirt across room rebuilds */
  private dirtByTile = new Map<number, number>();

  idx(x: number, y: number) {
    return y * this.w + x;
  }
  inb(x: number, y: number) {
    return x >= 0 && y >= 0 && x < this.w && y < this.h;
  }
  tx(i: number) {
    return i % this.w;
  }
  ty(i: number) {
    return (i / this.w) | 0;
  }

  /** wipe everything back to an empty plot */
  reset() {
    for (const a of [this.floor, this.wall, this.door, this.zone, this.planWall, this.planDoor, this.planFloor]) a.fill(0);
    this.objAt.fill(0);
    this.roomAt.fill(0);
    this.objects.clear();
    this.rooms.clear();
    this.roomsByType.clear();
    this.nextObjId = 1;
    this.dirtyFloor = this.dirtyWalls = this.dirtyObjects = this.dirtyZones = this.dirtyPlans = this.dirtyTopo = true;
    this.rebuildTopology();
  }

  // ------------------------------------------------------------ mutation
  setFloor(i: number, id: number) {
    if (this.floor[i] !== id) {
      this.floor[i] = id;
      this.dirtyFloor = true;
      this.dirtyTopo = true;
    }
  }
  setWall(i: number, id: number) {
    if (this.wall[i] === id && this.door[i] === 0) return;
    this.wall[i] = id;
    this.door[i] = 0;
    if (id) {
      this.zone[i] = 0;
      this.dirtyZones = true;
    }
    this.dirtyWalls = true;
    this.dirtyTopo = true;
  }
  setDoor(i: number, id: number) {
    if (this.door[i] === id && this.wall[i] === 0) return;
    this.door[i] = id;
    this.wall[i] = 0;
    if (id) {
      this.zone[i] = 0;
      this.dirtyZones = true;
    }
    this.dirtyWalls = true;
    this.dirtyTopo = true;
  }
  setZone(i: number, id: number) {
    if (this.wall[i] || this.door[i]) id = 0;
    if (this.zone[i] !== id) {
      this.zone[i] = id;
      this.dirtyZones = true;
      this.dirtyTopo = true;
    }
  }

  /** can an object of this type be placed here? */
  canPlace(type: string, x: number, y: number, rot: number, ignoreId = 0): boolean {
    const def = OBJ[type];
    const [fw, fd] = footprint(def, rot);
    if (x < 1 || y < 1 || x + fw > this.w - 1 || y + fd > this.h - 1) return false;
    for (let yy = y; yy < y + fd; yy++)
      for (let xx = x; xx < x + fw; xx++) {
        const i = this.idx(xx, yy);
        if (this.wall[i] || this.door[i] || this.planWall[i] || this.planDoor[i]) return false;
        if (this.objAt[i] && this.objAt[i] !== ignoreId) return false;
      }
    return true;
  }
  addObject(type: string, x: number, y: number, rot: number, built: boolean): WorldObject | null {
    if (!this.canPlace(type, x, y, rot)) return null;
    const o: WorldObject = { id: this.nextObjId++, type, x, y, rot: rot & 3, built, users: [], progress: built ? 1 : 0 };
    this.objects.set(o.id, o);
    this.stampObject(o, o.id);
    this.dirtyObjects = true;
    this.dirtyTopo = true;
    return o;
  }
  removeObject(id: number) {
    const o = this.objects.get(id);
    if (!o) return;
    this.stampObject(o, 0);
    this.objects.delete(id);
    this.dirtyObjects = true;
    this.dirtyTopo = true;
  }
  private stampObject(o: WorldObject, v: number) {
    const [fw, fd] = footprint(OBJ[o.type], o.rot);
    for (let yy = o.y; yy < o.y + fd; yy++) for (let xx = o.x; xx < o.x + fw; xx++) this.objAt[this.idx(xx, yy)] = v;
  }
  objectTiles(o: WorldObject): number[] {
    const [fw, fd] = footprint(OBJ[o.type], o.rot);
    const out: number[] = [];
    for (let yy = o.y; yy < o.y + fd; yy++) for (let xx = o.x; xx < o.x + fw; xx++) out.push(this.idx(xx, yy));
    return out;
  }

  // ------------------------------------------------------------ queries
  isBlocked(i: number) {
    return this.wall[i] !== 0;
  }
  isIndoor(i: number) {
    return !FLOORS[this.floor[i]].outdoor;
  }
  /** nearest tile to (x,y) walkable for a pass class */
  nearestWalkable(x: number, y: number, pass: number, maxR = 6): number {
    const c = this.cost[pass];
    x = Math.max(0, Math.min(this.w - 1, x));
    y = Math.max(0, Math.min(this.h - 1, y));
    if (c[this.idx(x, y)]) return this.idx(x, y);
    for (let r = 1; r <= maxR; r++)
      for (let dy = -r; dy <= r; dy++)
        for (let dx = -r; dx <= r; dx++) {
          if (Math.max(Math.abs(dx), Math.abs(dy)) !== r) continue;
          const xx = x + dx, yy = y + dy;
          if (this.inb(xx, yy) && c[this.idx(xx, yy)]) return this.idx(xx, yy);
        }
    return -1;
  }

  // ------------------------------------------------------------ topology
  /** Recompute path costs, rooms and the escape map. Call when dirtyTopo. */
  rebuildTopology() {
    this.dirtyTopo = false;
    this.topoVersion++;
    const cs = this.cost[PASS_STAFF];
    const cp = this.cost[PASS_PRISONER];
    for (let i = 0; i < this.n; i++) {
      let c = 2;
      if (this.wall[i]) c = 0;
      else {
        const oid = this.objAt[i];
        if (oid) {
          const o = this.objects.get(oid);
          if (o && o.built && OBJ[o.type].solid) c = 40;
        }
        if (this.door[i]) c = 4;
      }
      cs[i] = c;
      const d = this.door[i];
      cp[i] = d === DOOR_STAFF || d === DOOR_GATE ? 0 : c;
    }
    this.rebuildRooms();
    this.rebuildEscape();
  }

  private rebuildEscape() {
    const dist = this.escapeDist;
    dist.fill(65535);
    const cp = this.cost[PASS_PRISONER];
    const q = new Int32Array(this.n);
    let qh = 0, qt = 0;
    for (let x = 0; x < this.w; x++) {
      for (const y of [0, this.h - 1]) {
        const i = this.idx(x, y);
        if (cp[i] && dist[i] === 65535) { dist[i] = 0; q[qt++] = i; }
      }
    }
    for (let y = 0; y < this.h; y++) {
      for (const x of [0, this.w - 1]) {
        const i = this.idx(x, y);
        if (cp[i] && dist[i] === 65535) { dist[i] = 0; q[qt++] = i; }
      }
    }
    while (qh < qt) {
      const i = q[qh++];
      const x = i % this.w, y = (i / this.w) | 0;
      const d = dist[i] + 1;
      if (x > 0 && cp[i - 1] && dist[i - 1] > d) { dist[i - 1] = d; q[qt++] = i - 1; }
      if (x < this.w - 1 && cp[i + 1] && dist[i + 1] > d) { dist[i + 1] = d; q[qt++] = i + 1; }
      if (y > 0 && cp[i - this.w] && dist[i - this.w] > d) { dist[i - this.w] = d; q[qt++] = i - this.w; }
      if (y < this.h - 1 && cp[i + this.w] && dist[i + this.w] > d) { dist[i + this.w] = d; q[qt++] = i + this.w; }
    }
  }

  private rebuildRooms() {
    // remember dirt
    this.dirtByTile.clear();
    for (const r of this.rooms.values()) for (const t of r.tiles) this.dirtByTile.set(t, r.dirt);
    this.rooms.clear();
    this.roomsByType.clear();
    this.roomAt.fill(0);
    const stack: number[] = [];
    for (let s = 0; s < this.n; s++) {
      const type = this.zone[s];
      if (!type || this.roomAt[s]) continue;
      const room: Room = {
        id: this.nextRoomId++, type, tiles: [], objects: [], valid: false, missing: [], capacity: 0,
        cx: 0, cy: 0, minX: 1e9, minY: 1e9, maxX: -1, maxY: -1, dirt: 0, outdoor: false,
      };
      stack.length = 0;
      stack.push(s);
      this.roomAt[s] = room.id;
      let sx = 0, sy = 0, dirtSum = 0, outdoorN = 0;
      while (stack.length) {
        const i = stack.pop()!;
        room.tiles.push(i);
        const x = i % this.w, y = (i / this.w) | 0;
        sx += x; sy += y;
        dirtSum += this.dirtByTile.get(i) ?? 0;
        if (FLOORS[this.floor[i]].outdoor) outdoorN++;
        if (x < room.minX) room.minX = x;
        if (y < room.minY) room.minY = y;
        if (x > room.maxX) room.maxX = x;
        if (y > room.maxY) room.maxY = y;
        const nb = [x > 0 ? i - 1 : -1, x < this.w - 1 ? i + 1 : -1, y > 0 ? i - this.w : -1, y < this.h - 1 ? i + this.w : -1];
        for (const j of nb) {
          if (j >= 0 && this.zone[j] === type && !this.roomAt[j]) {
            this.roomAt[j] = room.id;
            stack.push(j);
          }
        }
      }
      const cnt = room.tiles.length;
      room.dirt = dirtSum / cnt;
      room.outdoor = outdoorN > cnt / 2;
      // label position: tile of the room closest to the centroid
      const mx = sx / cnt, my = sy / cnt;
      let best = 1e9;
      for (const t of room.tiles) {
        const dx = (t % this.w) - mx, dy = ((t / this.w) | 0) - my;
        const d = dx * dx + dy * dy;
        if (d < best) { best = d; room.cx = t % this.w; room.cy = (t / this.w) | 0; }
      }
      // objects
      const seen = new Set<number>();
      for (const t of room.tiles) {
        const oid = this.objAt[t];
        if (oid && !seen.has(oid)) {
          seen.add(oid);
          const o = this.objects.get(oid);
          if (o && o.built) room.objects.push(oid);
        }
      }
      this.validateRoom(room);
      this.rooms.set(room.id, room);
      let l = this.roomsByType.get(type);
      if (!l) this.roomsByType.set(type, (l = []));
      l.push(room);
    }
  }

  private validateRoom(room: Room) {
    const def = ROOMS[room.type];
    room.missing = [];
    const have = new Map<string, number>();
    for (const oid of room.objects) {
      const o = this.objects.get(oid)!;
      have.set(o.type, (have.get(o.type) ?? 0) + 1);
    }
    for (const alt of def.needs) {
      if (!alt.some((t) => have.has(t))) room.missing.push(alt.map((t) => OBJ[t].name).join(' or '));
    }
    if (room.tiles.length < def.minTiles) room.missing.push(`At least ${def.minTiles} tiles (has ${room.tiles.length})`);
    if (def.enclosed && !this.isEnclosed(room)) room.missing.push('Must be enclosed by walls with a door');
    room.valid = room.missing.length === 0;
    // capacity
    let cap = 0;
    if (def.key === 'cell' || def.key === 'dorm') {
      for (const oid of room.objects) {
        const o = this.objects.get(oid)!;
        if (o.type === 'bed') cap += 1;
        else if (o.type === 'bunk') cap += 2;
      }
    } else if (def.key === 'holding') cap = Math.floor(room.tiles.length / 2);
    else if (def.key === 'solitary') cap = 1;
    room.capacity = room.valid ? cap : 0;
  }

  /** A room is enclosed if every zone-tile neighbour is a wall, a door or part of the same room. */
  private isEnclosed(room: Room): boolean {
    let hasDoor = false;
    for (const i of room.tiles) {
      const x = i % this.w, y = (i / this.w) | 0;
      if (x === 0 || y === 0 || x === this.w - 1 || y === this.h - 1) return false;
      for (const j of [i - 1, i + 1, i - this.w, i + this.w]) {
        if (this.roomAt[j] === room.id) continue;
        if (this.door[j]) { hasDoor = true; continue; }
        if (this.wall[j] && this.wall[j] !== WALL_FENCE) continue;
        return false;
      }
    }
    return hasDoor;
  }

  roomsOf(type: number): Room[] {
    return this.roomsByType.get(type) ?? [];
  }
  validRoomsOf(type: number): Room[] {
    return this.roomsOf(type).filter((r) => r.valid);
  }
  roomAtTile(i: number): Room | undefined {
    const id = this.roomAt[i];
    return id ? this.rooms.get(id) : undefined;
  }

  // ------------------------------------------------------------ serialisation
  serialize() {
    return {
      w: this.w, h: this.h,
      floor: b64encode(this.floor), wall: b64encode(this.wall), door: b64encode(this.door), zone: b64encode(this.zone),
      planWall: b64encode(this.planWall), planDoor: b64encode(this.planDoor), planFloor: b64encode(this.planFloor),
      objects: [...this.objects.values()].map((o) => [o.id, o.type, o.x, o.y, o.rot, o.built ? 1 : 0]),
      nextObjId: this.nextObjId,
      dirt: [...this.rooms.values()].map((r) => [r.tiles[0], Math.round(r.dirt * 100) / 100]),
    };
  }
  load(d: any): boolean {
    if (d.w !== this.w || d.h !== this.h) return false;
    this.floor.set(b64decode(d.floor));
    this.wall.set(b64decode(d.wall));
    this.door.set(b64decode(d.door));
    this.zone.set(b64decode(d.zone));
    this.planWall.set(b64decode(d.planWall));
    this.planDoor.set(b64decode(d.planDoor));
    this.planFloor.set(b64decode(d.planFloor));
    this.objects.clear();
    this.objAt.fill(0);
    for (const [id, type, x, y, rot, built] of d.objects as any[]) {
      if (!OBJ[type]) continue;
      const o: WorldObject = { id, type, x, y, rot, built: !!built, users: [], progress: built ? 1 : 0 };
      this.objects.set(id, o);
      this.stampObject(o, id);
    }
    this.nextObjId = d.nextObjId;
    this.dirtyFloor = this.dirtyWalls = this.dirtyObjects = this.dirtyZones = this.dirtyPlans = this.dirtyTopo = true;
    this.rebuildTopology();
    for (const [tile, dirt] of (d.dirt ?? []) as [number, number][]) {
      const r = this.roomAtTile(tile);
      if (r) r.dirt = dirt;
    }
    return true;
  }
}

export { OBJ, ROOMS, FLOORS, WALLS, DOORS, WALL_PERIMETER };
