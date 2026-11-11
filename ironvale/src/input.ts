import * as THREE from 'three';
import { DOORS, FLOORS, OBJ, ROOMS, WALLS, WALL_CONCRETE } from './data/defs';
import { fmtMoney } from './core/util';
import { sfx } from './core/sfx';
import { footprint } from './world/world';
import type { Game } from './game';

interface Pt {
  x: number;
  y: number;
}

/** Mouse, touch and keyboard: camera control plus the build tools. */
export class Input {
  private keys = new Set<string>();
  private pointers = new Map<number, Pt>();
  private primary: { id: number; sx: number; sy: number; lx: number; ly: number; moved: number; startTile: Pt | null; mode: 'tool' | 'pan' | 'none' } | null = null;
  private pinch: { dist: number; cx: number; cy: number } | null = null;
  private hover: Pt | null = null;
  private mouse: Pt = { x: 0, y: 0 };
  objRot = 0;
  private v = new THREE.Vector3();

  constructor(private game: Game) {
    const c = game.gfx.canvas;
    c.addEventListener('pointerdown', (e) => this.down(e));
    c.addEventListener('pointermove', (e) => this.move(e));
    c.addEventListener('pointerup', (e) => this.up(e));
    c.addEventListener('pointercancel', (e) => this.up(e, true));
    c.addEventListener('pointerleave', () => {
      if (!this.primary) {
        this.hover = null;
        this.refreshPreview();
      }
    });
    c.addEventListener('wheel', (e) => this.wheel(e), { passive: false });
    c.addEventListener('contextmenu', (e) => e.preventDefault());
    window.addEventListener('keydown', (e) => this.keydown(e));
    window.addEventListener('keyup', (e) => this.keys.delete(e.key.toLowerCase()));
    window.addEventListener('blur', () => this.keys.clear());
  }

  private pos(e: PointerEvent | WheelEvent): Pt {
    const r = this.game.gfx.canvas.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }
  private tileAt(p: Pt): Pt | null {
    const g = this.game.gfx.screenToGround(p.x, p.y, this.v);
    if (!g) return null;
    const x = Math.floor(g.x), y = Math.floor(g.z);
    const w = this.game.world;
    if (!w.inb(x, y)) return null;
    return { x, y };
  }

  onToolChange() {
    this.primary = null;
    this.refreshPreview();
  }

  // ------------------------------------------------------------ pointer
  private down(e: PointerEvent) {
    if (this.game.inMenu) return;
    const p = this.pos(e);
    this.pointers.set(e.pointerId, p);
    try {
      this.game.gfx.canvas.setPointerCapture(e.pointerId);
    } catch { /* ignore */ }
    if (this.pointers.size === 2) {
      // two fingers: pinch-zoom and pan; abandon any drag in progress
      this.primary = null;
      const [a, b] = [...this.pointers.values()];
      this.pinch = { dist: Math.hypot(a.x - b.x, a.y - b.y), cx: (a.x + b.x) / 2, cy: (a.y + b.y) / 2 };
      this.refreshPreview();
      return;
    }
    if (this.pointers.size > 2) return;
    const tool = this.game.tool;
    let mode: 'tool' | 'pan' | 'none' = 'pan';
    if (e.pointerType === 'mouse' && e.button === 2) {
      // right click cancels a tool, otherwise pans
      if (tool.kind !== 'select') {
        this.game.setTool({ kind: 'select' });
        mode = 'none';
      }
    } else if (e.pointerType === 'mouse' && e.button === 1) mode = 'pan';
    else if (tool.kind !== 'select') mode = 'tool';
    this.primary = { id: e.pointerId, sx: p.x, sy: p.y, lx: p.x, ly: p.y, moved: 0, startTile: mode === 'tool' ? this.tileAt(p) : null, mode };
    this.hover = this.tileAt(p);
    this.refreshPreview();
  }

  private move(e: PointerEvent) {
    const p = this.pos(e);
    this.mouse = p;
    if (this.pointers.has(e.pointerId)) this.pointers.set(e.pointerId, p);
    if (this.pinch && this.pointers.size >= 2) {
      const [a, b] = [...this.pointers.values()];
      const dist = Math.hypot(a.x - b.x, a.y - b.y), cx = (a.x + b.x) / 2, cy = (a.y + b.y) / 2;
      const gfx = this.game.gfx;
      if (dist > 10 && this.pinch.dist > 10) {
        gfx.zoomBy(this.pinch.dist / dist);
        gfx.zoom = gfx.zoomTarget;
      }
      gfx.panPixels(cx - this.pinch.cx, cy - this.pinch.cy);
      this.pinch = { dist, cx, cy };
      this.game.follow = false;
      return;
    }
    const pr = this.primary;
    if (pr && pr.id === e.pointerId) {
      const dx = p.x - pr.lx, dy = p.y - pr.ly;
      pr.moved += Math.abs(dx) + Math.abs(dy);
      pr.lx = p.x;
      pr.ly = p.y;
      if (pr.mode === 'pan' && pr.moved > 5) {
        this.game.gfx.panPixels(dx, dy);
        this.game.follow = false;
      }
    }
    if (this.game.inMenu) return;
    this.hover = this.tileAt(p);
    this.refreshPreview();
  }

  private up(e: PointerEvent, cancel = false) {
    const p = this.pos(e);
    this.pointers.delete(e.pointerId);
    if (this.pointers.size < 2) this.pinch = null;
    const pr = this.primary;
    if (!pr || pr.id !== e.pointerId) return;
    this.primary = null;
    if (cancel || this.game.inMenu) {
      this.refreshPreview();
      return;
    }
    if (pr.mode === 'tool') this.commit(pr.startTile, this.tileAt(p));
    else if (pr.mode === 'pan' && pr.moved <= 6) this.click(p);
    if (e.pointerType !== 'mouse') this.hover = null;
    this.refreshPreview();
  }

  private wheel(e: WheelEvent) {
    e.preventDefault();
    if (this.game.inMenu) return;
    const gfx = this.game.gfx, p = this.pos(e);
    const before = gfx.screenToGround(p.x, p.y, new THREE.Vector3());
    gfx.zoomBy(Math.exp(Math.sign(e.deltaY) * Math.min(0.25, Math.abs(e.deltaY) * 0.0016)));
    gfx.zoom = gfx.zoomTarget;
    gfx.updateCamera();
    const after = gfx.screenToGround(p.x, p.y, new THREE.Vector3());
    if (before && after) {
      gfx.target.x += before.x - after.x;
      gfx.target.z += before.z - after.z;
    }
  }

  private click(p: Pt) {
    const g = this.game, sim = g.sim, w = g.world;
    const a = g.chars.pick(sim.agents, p.x, p.y);
    if (a) {
      g.select({ kind: 'agent', id: a.id });
      sfx.click();
      return;
    }
    const t = this.tileAt(p);
    if (!t) return g.select(null);
    const i = w.idx(t.x, t.y);
    if (w.objAt[i]) return g.select({ kind: 'object', id: w.objAt[i] });
    if (w.roomAt[i]) return g.select({ kind: 'room', tile: i });
    g.select(null);
  }

  // ------------------------------------------------------------ keyboard
  private keydown(e: KeyboardEvent) {
    const tag = (e.target as HTMLElement)?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    const k = e.key.toLowerCase();
    this.keys.add(k);
    const g = this.game;
    if (g.inMenu) return;
    switch (k) {
      case 'q': g.gfx.rotate(-1); break;
      case 'e': g.gfx.rotate(1); break;
      case 'r': this.objRot = (this.objRot + 1) & 3; this.refreshPreview(); break;
      case 'escape':
        if (g.ui.closeModal()) break;
        if (g.tool.kind !== 'select') g.setTool({ kind: 'select' });
        else g.select(null);
        break;
      case ' ':
        e.preventDefault();
        g.sim.paused = !g.sim.paused;
        break;
      case '1': g.sim.paused = false; g.sim.speed = 1; break;
      case '2': g.sim.paused = false; g.sim.speed = 2; break;
      case '3': g.sim.paused = false; g.sim.speed = 5; break;
      case 'tab':
        e.preventDefault();
        g.showZones = !g.showZones;
        break;
      case 'delete':
      case 'backspace':
        g.setTool({ kind: 'bulldoze' });
        break;
    }
  }

  update(dt: number) {
    if (this.game.inMenu) return;
    const k = this.keys, gfx = this.game.gfx;
    let r = 0, f = 0;
    if (k.has('a') || k.has('arrowleft')) r -= 1;
    if (k.has('d') || k.has('arrowright')) r += 1;
    if (k.has('w') || k.has('arrowup')) f += 1;
    if (k.has('s') || k.has('arrowdown')) f -= 1;
    if (r || f) {
      const sp = gfx.zoom * 0.9 * dt;
      gfx.panUnits(r * sp, f * sp * 1.3);
      this.game.follow = false;
    }
  }

  // ------------------------------------------------------------ tool geometry
  private rect(a: Pt, b: Pt): number[] {
    const w = this.game.world, out: number[] = [];
    for (let y = Math.min(a.y, b.y); y <= Math.max(a.y, b.y); y++) for (let x = Math.min(a.x, b.x); x <= Math.max(a.x, b.x); x++) out.push(w.idx(x, y));
    return out;
  }
  private outline(a: Pt, b: Pt): number[] {
    const w = this.game.world, out: number[] = [];
    const x0 = Math.min(a.x, b.x), x1 = Math.max(a.x, b.x), y0 = Math.min(a.y, b.y), y1 = Math.max(a.y, b.y);
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) if (x === x0 || x === x1 || y === y0 || y === y1) out.push(w.idx(x, y));
    return out;
  }
  private line(a: Pt, b: Pt): number[] {
    return Math.abs(b.x - a.x) >= Math.abs(b.y - a.y) ? this.rect(a, { x: b.x, y: a.y }) : this.rect(a, { x: a.x, y: b.y });
  }
  private buildable(i: number) {
    const w = this.game.world, x = i % w.w, y = Math.floor(i / w.w);
    return x >= 1 && y >= 1 && x < w.w - 1 && y < w.h - 1;
  }

  /** work out the tiles and price for the current tool between two tiles */
  private plan(a: Pt, b: Pt) {
    const g = this.game, w = g.world, tool = g.tool;
    let boxes: number[] = [], flats: number[] = [], cost = 0, label = '', color = 0x58b7ff, h = 1.3;
    switch (tool.kind) {
      case 'foundation': {
        const all = this.rect(a, b).filter((i) => this.buildable(i));
        boxes = this.outline(a, b).filter((i) => this.buildable(i) && !w.objAt[i]);
        const edge = new Set(boxes);
        flats = all.filter((i) => !edge.has(i));
        for (const i of boxes) if (w.wall[i] !== WALL_CONCRETE && w.planWall[i] !== WALL_CONCRETE) cost += WALLS[WALL_CONCRETE].cost;
        for (const i of all) if (w.floor[i] !== 2 && w.planFloor[i] !== 3) cost += FLOORS[2].cost;
        const bw = Math.abs(b.x - a.x) + 1, bh = Math.abs(b.y - a.y) + 1;
        label = `Building ${bw} x ${bh}`;
        break;
      }
      case 'wall': {
        boxes = this.line(a, b).filter((i) => this.buildable(i) && !w.objAt[i]);
        for (const i of boxes) if (w.wall[i] !== tool.id && w.planWall[i] !== tool.id) cost += WALLS[tool.id].cost;
        label = `${boxes.length} x ${WALLS[tool.id].name}`;
        h = WALLS[tool.id].height;
        break;
      }
      case 'door': {
        const i = w.idx(b.x, b.y);
        if (this.buildable(i) && !w.objAt[i]) {
          boxes = [i];
          cost = DOORS[tool.id].cost;
        }
        label = DOORS[tool.id].name;
        break;
      }
      case 'floor': {
        flats = this.rect(a, b).filter((i) => w.floor[i] !== tool.id || w.planFloor[i]);
        cost = flats.length * FLOORS[tool.id].cost;
        label = `${flats.length} x ${FLOORS[tool.id].name}`;
        color = 0x9be0ff;
        break;
      }
      case 'zone': {
        flats = this.rect(a, b).filter((i) => !w.wall[i] && !w.door[i]);
        label = tool.id ? `${ROOMS[tool.id].name} (${flats.length} tiles)` : 'Clear room';
        color = tool.id ? ROOMS[tool.id].color : 0xff6a5a;
        break;
      }
      case 'bulldoze': {
        flats = this.rect(a, b);
        label = 'Demolish';
        color = 0xff5040;
        break;
      }
    }
    return { boxes, flats, cost, label, color, h };
  }

  private refreshPreview() {
    const g = this.game, ov = g.overlays, tool = g.tool;
    ov.clearPreview();
    g.objects.setCursor(null);
    g.ui.setCostTag(null);
    const hover = this.hover;
    ov.setHover(hover?.x ?? 0, hover?.y ?? 0, !!hover && tool.kind !== 'object' && !g.inMenu && (tool.kind !== 'select' || false));
    if (!hover || tool.kind === 'select' || g.inMenu) return;
    if (tool.kind === 'station') {
      g.ui.setCostTag('Click a room to post the guard there', this.mouse.x, this.mouse.y, true);
      return;
    }
    if (tool.kind === 'object') {
      const def = OBJ[tool.id];
      const [fw, fd] = footprint(def, this.objRot);
      const x = hover.x - Math.floor((fw - 1) / 2), y = hover.y - Math.floor((fd - 1) / 2);
      const ok = g.world.canPlace(tool.id, x, y, this.objRot) && g.sim.canAfford(def.cost);
      g.objects.setCursor(tool.id, x, y, this.objRot, ok);
      const tiles: number[] = [];
      for (let yy = y; yy < y + fd; yy++) for (let xx = x; xx < x + fw; xx++) if (g.world.inb(xx, yy)) tiles.push(g.world.idx(xx, yy));
      ov.setTiles(tiles, ok ? 0x6dff8a : 0xff5a4a);
      g.ui.setCostTag(`${def.name}  ${fmtMoney(def.cost)}`, this.mouse.x, this.mouse.y, g.sim.canAfford(def.cost));
      return;
    }
    const start = this.primary?.mode === 'tool' && this.primary.startTile ? this.primary.startTile : hover;
    const pl = this.plan(start, hover);
    const afford = g.sim.canAfford(pl.cost);
    if (pl.boxes.length) ov.setBoxes(pl.boxes, afford ? 0x58b7ff : 0xff5a4a, pl.h);
    if (pl.flats.length) ov.setTiles(pl.flats, afford ? pl.color : 0xff5a4a);
    g.ui.setCostTag(pl.cost ? `${pl.label}  ${fmtMoney(pl.cost)}` : pl.label, this.mouse.x, this.mouse.y, afford);
  }

  private commit(a: Pt | null, b: Pt | null) {
    const g = this.game, sim = g.sim, w = g.world, tool = g.tool;
    if (!b) return;
    if (!a) a = b;
    if (tool.kind === 'station') {
      const guard = sim.byId.get(tool.guard);
      const i = w.idx(b.x, b.y);
      if (guard?.s && w.roomAt[i]) {
        guard.s.station = i;
        sim.clearPlan(guard);
        sim.toast(`${guard.name} is now posted to the ${ROOMS[w.zone[i]].name}.`, 'info');
        sfx.click();
      }
      g.setTool({ kind: 'select' });
      return;
    }
    if (tool.kind === 'object') {
      const def = OBJ[tool.id];
      const [fw, fd] = footprint(def, this.objRot);
      const x = b.x - Math.floor((fw - 1) / 2), y = b.y - Math.floor((fd - 1) / 2);
      if (!w.canPlace(tool.id, x, y, this.objRot)) {
        sfx.error();
        return;
      }
      if (!sim.placeObject(tool.id, x, y, this.objRot)) {
        sim.warn('funds', 'Not enough money for that.', 3, 'bad');
        sfx.error();
        return;
      }
      sfx.place();
      return;
    }
    const pl = this.plan(a, b);
    let done = 0, broke = false;
    const tryDo = (ok: boolean) => {
      if (ok) done++;
    };
    switch (tool.kind) {
      case 'foundation': {
        if (!sim.canAfford(pl.cost)) { broke = true; break; }
        for (const i of pl.boxes) tryDo(sim.planWall(i, WALL_CONCRETE));
        for (const i of [...pl.boxes, ...pl.flats]) tryDo(sim.planFloor(i, 2));
        break;
      }
      case 'wall':
        for (const i of pl.boxes) {
          if (!sim.canAfford(WALLS[tool.id].cost)) { broke = true; break; }
          tryDo(sim.planWall(i, tool.id));
        }
        break;
      case 'door':
        for (const i of pl.boxes) {
          if (!sim.canAfford(DOORS[tool.id].cost)) { broke = true; break; }
          tryDo(sim.planDoor(i, tool.id));
        }
        break;
      case 'floor':
        for (const i of pl.flats) {
          if (!sim.canAfford(FLOORS[tool.id].cost)) { broke = true; break; }
          tryDo(sim.planFloor(i, tool.id));
        }
        break;
      case 'zone':
        for (const i of pl.flats) sim.setZone(i, tool.id);
        done = pl.flats.length;
        break;
      case 'bulldoze':
        for (const i of pl.flats) sim.bulldoze(i);
        done = pl.flats.length;
        if (done) sfx.demolish();
        break;
    }
    if (broke) {
      sim.warn('funds', 'Not enough money for that.', 3, 'bad');
      sfx.error();
    } else if (done && tool.kind !== 'bulldoze') sfx.place();
  }
}
