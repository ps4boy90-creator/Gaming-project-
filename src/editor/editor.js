import { Assets } from '../core/assets.js';
import { NATIVE_W, NATIVE_H } from '../core/screen.js';
import { Lighting } from '../gfx/lighting.js';
import { ENTITY_TYPES, makeEntity, entityBox, flagsUsed } from '../game/entities.js';
import { SCENES } from '../scenes/manifest.js';
import { Deductions } from '../game/deductions.js';
import { Audio } from '../game/audio.js';
import { Music } from '../game/music.js';
import { EditorDoc, blankScene } from './doc.js';
import { buildInspector, buildFields, el } from './inspector.js';

const HANDLE = 7;          // screen-space size of a drag handle
const KNOWN_IMAGES = [
  'backdrops/station_gate/room.png',
  'backdrops/station_lobby/room.png',
  'backdrops/office_wing/room.png',
  'backdrops/canteen/room.png',
  'backdrops/laboratory/room.png',
  'backdrops/security_room/room.png',
  'backdrops/stairwell/room.png',
  'backdrops/sublevel_3/room.png',
  'props/car_veridian/side.png',
  'props/car_veridian/front.png',
  'props/car_veridian/rear.png',
  'props/car_veridian/front_3q.png',
  'props/car_veridian/rear_3q.png',
  'props/car_veridian/top.png',
  'backdrops/cabin_bedroom/room.png',
  'backdrops/cabin_landing/far.png',
  'backdrops/cabin_landing/wall.png',
  'backdrops/cabin_landing/fore.png',
  'backdrops/cabin_drive/sky.png',
  'backdrops/cabin_drive/ground.png',
];

export class Editor {
  constructor(root) {
    this.root = root;
    this.canvas = root.querySelector('#canvas');
    this.ctx = this.canvas.getContext('2d');
    this.ctx.imageSmoothingEnabled = false;

    this.assets = new Assets();
    this.lighting = new Lighting(2048, 512);
    this.doc = new EditorDoc(EditorDoc.restore() || blankScene());
    this.doc.onChange = () => this.onDocChanged();

    this.zoom = 2;
    this.pan = { x: 0, y: 0 };
    this.tool = 'select';
    this.placeType = 'note';
    this.selection = null;
    this.showLighting = true;
    this.showGrid = false;
    this.drag = null;
    this.mouse = { x: 0, y: 0, down: false };

    this.bindUI();
    this.bindCanvas();
    this.reloadImages().then(() => this.onDocChanged());
    this.tick();
  }

  // ---------------------------------------------------------------- helpers

  get scene() { return this.doc.scene; }

  toWorld(clientX, clientY) {
    const r = this.canvas.getBoundingClientRect();
    return {
      x: (clientX - r.left) / this.zoom + this.pan.x,
      y: (clientY - r.top) / this.zoom + this.pan.y,
    };
  }

  toScreen(x, y) {
    return { x: (x - this.pan.x) * this.zoom, y: (y - this.pan.y) * this.zoom };
  }

  status(text) {
    this.root.querySelector('#status').textContent = text;
  }

  /** Load every image the scene references; missing ones are reported, not fatal. */
  async reloadImages() {
    const paths = new Set();
    for (const l of this.scene.layers || []) if (l.image) paths.add(l.image);
    for (const e of this.scene.entities || []) {
      if (e.type === 'prop' && e.props.image) paths.add(e.props.image);
    }
    const missing = [];
    await Promise.all([...paths].map((p) =>
      this.assets.loadImage(p).catch(() => missing.push(p))));
    if (missing.length) this.status(`Missing images: ${missing.join(', ')}`);
    return missing;
  }

  // ------------------------------------------------------------------- UI

  bindUI() {
    const q = (sel) => this.root.querySelector(sel);

    q('#tools').addEventListener('click', (e) => {
      const button = e.target.closest('button[data-tool]');
      if (!button) return;
      this.tool = button.dataset.tool;
      this.selection = null;
      this.refreshChrome();
    });

    const palette = q('#palette');
    for (const [type, def] of Object.entries(ENTITY_TYPES)) {
      palette.append(el('button', {
        class: 'chip', 'data-type': type, text: def.label,
        style: `border-color:${def.color}`,
        onclick: () => { this.tool = 'entity'; this.placeType = type; this.refreshChrome(); },
      }));
    }

    q('#btn-new').addEventListener('click', () => {
      if (!confirm('Discard the current scene and start a new one?')) return;
      this.doc.load(blankScene());
      this.selection = null;
      this.reloadImages();
    });
    q('#btn-import').addEventListener('click', () => q('#file').click());
    q('#file').addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      try {
        this.doc.load(JSON.parse(await file.text()));
        this.selection = null;
        await this.reloadImages();
        this.frameScene();
        this.status(`Loaded ${file.name}`);
      } catch (err) {
        this.status(`Could not read that file: ${err.message}`);
      }
      e.target.value = '';
    });
    q('#btn-export').addEventListener('click', () => this.exportFile());
    q('#btn-copy').addEventListener('click', () => this.copyJSON());
    q('#btn-test').addEventListener('click', () => this.testPlay());
    q('#btn-frame').addEventListener('click', () => this.frameScene());
    q('#btn-undo').addEventListener('click', () => this.doc.undo());
    q('#btn-redo').addEventListener('click', () => this.doc.redo());

    q('#opt-lighting').addEventListener('change', (e) => { this.showLighting = e.target.checked; });
    q('#opt-grid').addEventListener('change', (e) => { this.showGrid = e.target.checked; });

    q('#load-scene').addEventListener('change', async (e) => {
      const id = e.target.value;
      if (!id) return;
      try {
        const res = await fetch(SCENES[id]);
        this.doc.load(await res.json());
        this.selection = null;
        await this.reloadImages();
        this.frameScene();
        this.status(`Loaded ${id}`);
      } catch (err) {
        this.status(`Could not load ${id}: ${err.message}`);
      }
      e.target.value = '';
    });
    const loader = q('#load-scene');
    for (const id of Object.keys(SCENES)) loader.append(el('option', { value: id, text: id }));

    window.addEventListener('keydown', (e) => {
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        if (e.shiftKey) this.doc.redo(); else this.doc.undo();
      }
      if (e.key === 'Delete' || e.key === 'Backspace') { e.preventDefault(); this.deleteSelection(); }
      if (e.key === 'Escape') { this.selection = null; this.refreshChrome(); }
      const shortcut = { v: 'select', c: 'collision', e: 'entity', h: 'pan' }[e.key.toLowerCase()];
      if (shortcut) { this.tool = shortcut; this.refreshChrome(); }
    });

    window.addEventListener('resize', () => this.resize());
    window.addEventListener('beforeunload', (e) => {
      if (this.doc.dirty) { e.preventDefault(); e.returnValue = ''; }
    });
    this.resize();
  }

  resize() {
    const wrap = this.root.querySelector('#stage');
    this.canvas.width = wrap.clientWidth;
    this.canvas.height = wrap.clientHeight;
    this.ctx.imageSmoothingEnabled = false;
  }

  frameScene() {
    const { w, h } = this.scene.size;
    const zx = this.canvas.width / (w + 40);
    const zy = this.canvas.height / (h + 40);
    this.zoom = Math.max(0.5, Math.min(4, Math.min(zx, zy)));
    this.pan.x = w / 2 - this.canvas.width / (2 * this.zoom);
    this.pan.y = h / 2 - this.canvas.height / (2 * this.zoom);
  }

  onDocChanged() {
    this.refreshChrome();
  }

  refreshChrome() {
    const q = (s) => this.root.querySelector(s);
    for (const b of this.root.querySelectorAll('#tools button[data-tool]')) {
      b.classList.toggle('active', b.dataset.tool === this.tool);
    }
    for (const b of this.root.querySelectorAll('#palette .chip')) {
      b.classList.toggle('active', this.tool === 'entity' && b.dataset.type === this.placeType);
    }
    q('#btn-undo').disabled = !this.doc.undoStack.length;
    q('#btn-redo').disabled = !this.doc.redoStack.length;

    buildInspector(q('#inspector'), this.selection, this.doc, this.context(), {
      refresh: () => this.refreshChrome(),
      deleteSelection: () => this.deleteSelection(),
    });
    this.buildScenePanel();
    this.buildLayersPanel();
    this.buildFlagsPanel();
  }

  context() {
    return {
      scenes: Object.keys(SCENES),
      // Offer every clue flag a deduction listens for, not just the ones this
      // scene already uses -- that is how you wire a room into the chain.
      flags: [...new Set([...flagsUsed(this.scene), ...Deductions.allClueFlags()])].sort(),
      images: KNOWN_IMAGES,
    };
  }

  buildScenePanel() {
    const host = this.root.querySelector('#scene-panel');
    host.replaceChildren();
    const s = this.scene;
    const fields = {
      id: { type: 'string', help: 'Also the key to add to src/scenes/manifest.js.' },
      name: { type: 'string' },
      ambience: { type: 'select', options: Audio.ambienceNames() },
      music: { type: 'select', options: ['', ...Music.presetNames()],
        help: 'Leave empty to derive the score from the ambience.' },
      allowJump: { type: 'bool', help: 'Off suits a grounded, walking character.' },
    };
    host.append(buildFields(fields, s, (k, v) => {
      this.doc.begin(); s[k] = v; this.doc.commit();
    }, this.context()));

    host.append(buildFields(
      { w: { type: 'number', min: 64 }, h: { type: 'number', min: 64 } },
      s.size,
      (k, v) => { this.doc.begin(); s.size[k] = v; this.doc.commit(); },
    ));

    host.append(el('div', { class: 'divider' }));
    host.append(buildFields(
      {
        color: { type: 'color', help: 'The colour of the dark. Deep blue reads as night.' },
        strength: { type: 'number', min: 0, max: 1, step: 0.02, help: '0 is full daylight, 1 is pitch black.' },
      },
      s.ambient,
      (k, v) => { this.doc.begin(); s.ambient[k] = v; this.doc.commit(); },
    ));
  }

  buildLayersPanel() {
    const host = this.root.querySelector('#layers-panel');
    host.replaceChildren();
    const layers = this.scene.layers;

    layers.forEach((layer, i) => {
      const row = el('div', { class: 'layer' });
      row.append(el('div', { class: 'layer-name', text: layer.image || '(no image)' }));
      const controls = el('div', { class: 'layer-controls' });

      const px = el('input', { type: 'number', step: 0.05, title: 'parallax' });
      px.value = layer.parallax === undefined ? 1 : layer.parallax;
      px.addEventListener('input', () => { this.doc.begin(); layer.parallax = Number(px.value); this.doc.commit(); });

      const over = el('input', { type: 'checkbox', title: 'draw in front of the player' });
      over.checked = !!layer.overPlayer;
      over.addEventListener('change', () => { this.doc.begin(); layer.overPlayer = over.checked; this.doc.commit(); });

      const rep = el('input', { type: 'checkbox', title: 'tile horizontally' });
      rep.checked = !!layer.repeat;
      rep.addEventListener('change', () => { this.doc.begin(); layer.repeat = rep.checked; this.doc.commit(); });

      controls.append(el('span', { text: 'px' }), px,
        el('span', { text: 'front' }), over,
        el('span', { text: 'tile' }), rep,
        el('button', { class: 'mini', text: '↑', onclick: () => this.moveLayer(i, -1) }),
        el('button', { class: 'mini', text: '↓', onclick: () => this.moveLayer(i, 1) }),
        el('button', { class: 'mini danger', text: '✕', onclick: () => {
          this.doc.begin(); layers.splice(i, 1); this.doc.commit();
        } }));
      row.append(controls);
      host.append(row);
    });

    const add = el('div', { class: 'layer-add' });
    const input = el('input', { type: 'text', list: 'all-images', placeholder: 'backdrops/…/room.png' });
    add.append(input, el('button', {
      text: 'Add layer',
      onclick: async () => {
        const path = input.value.trim();
        if (!path) return;
        try {
          await this.assets.loadImage(path);
        } catch (err) {
          this.status(`Could not load ${path}`);
          return;
        }
        this.doc.begin();
        layers.push({ image: path, parallax: 1 });
        this.doc.commit();
        input.value = '';
      },
    }));
    host.append(add);
  }

  moveLayer(i, delta) {
    const layers = this.scene.layers;
    const j = i + delta;
    if (j < 0 || j >= layers.length) return;
    this.doc.begin();
    [layers[i], layers[j]] = [layers[j], layers[i]];
    this.doc.commit();
  }

  buildFlagsPanel() {
    const host = this.root.querySelector('#flags-panel');
    host.replaceChildren();
    const set = new Map();
    for (const e of this.scene.entities) {
      const req = e.props.requiresFlag;
      const sets = e.props.setsFlag;
      if (req) {
        if (!set.has(req)) set.set(req, { reads: 0, writes: 0 });
        set.get(req).reads++;
      }
      if (sets) {
        if (!set.has(sets)) set.set(sets, { reads: 0, writes: 0 });
        set.get(sets).writes++;
      }
    }
    if (!set.size) {
      host.append(el('p', { class: 'muted', text: 'No flags used in this scene yet.' }));
      return;
    }
    for (const [name, use] of [...set].sort()) {
      // A flag that is read but never written here is not necessarily wrong --
      // another scene may set it -- but a typo looks exactly like this.
      const orphan = use.writes === 0;
      // Naming which realization a clue feeds turns the panel into a check on
      // the mystery itself: a clue flag that feeds nothing is dead weight.
      const feeds = Deductions.feeds(name);
      const suffix = feeds.length ? `   -> ${feeds.join(', ')}`
        : (name.startsWith('clue_') ? '   (feeds no deduction)' : '');
      host.append(el('div', {
        class: `flag${orphan ? ' orphan' : ''}`,
        text: `${name}   ${use.writes} set · ${use.reads} read${orphan ? '   (never set here)' : ''}${suffix}`,
      }));
    }
  }

  // -------------------------------------------------------------- canvas io

  bindCanvas() {
    const c = this.canvas;

    c.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      const w = this.toWorld(e.clientX, e.clientY);
      const hit = this.hitTest(w);
      if (hit) { this.selection = hit; this.deleteSelection(); }
    });

    c.addEventListener('pointerdown', (e) => {
      if (e.button === 2) return;
      c.setPointerCapture(e.pointerId);
      const w = this.toWorld(e.clientX, e.clientY);
      this.mouse.down = true;

      if (this.tool === 'pan' || e.button === 1 || e.shiftKey) {
        this.drag = { mode: 'pan', startX: e.clientX, startY: e.clientY, panX: this.pan.x, panY: this.pan.y };
        return;
      }

      if (this.tool === 'entity') {
        this.doc.begin();
        const entity = makeEntity(this.placeType, Math.round(w.x), Math.round(w.y));
        entity.id = this.uniqueId(this.placeType);
        this.scene.entities.push(entity);
        this.doc.commit();
        this.selection = { kind: 'entity', index: this.scene.entities.length - 1 };
        this.drag = { mode: 'move-entity', index: this.selection.index, dx: 0, dy: 0 };
        this.refreshChrome();
        return;
      }

      if (this.tool === 'collision') {
        this.doc.begin();
        this.scene.collision.push({ x: Math.round(w.x), y: Math.round(w.y), w: 1, h: 1, type: 'solid' });
        this.doc.commit();
        this.selection = { kind: 'rect', index: this.scene.collision.length - 1 };
        this.drag = { mode: 'draw-rect', index: this.selection.index, originX: Math.round(w.x), originY: Math.round(w.y) };
        this.refreshChrome();
        return;
      }

      // select tool
      const handle = this.handleAt(w);
      if (handle) { this.drag = handle; return; }

      const hit = this.hitTest(w);
      this.selection = hit;
      if (hit) {
        this.doc.begin();
        if (hit.kind === 'entity') {
          const en = this.scene.entities[hit.index];
          this.drag = { mode: 'move-entity', index: hit.index, dx: w.x - en.x, dy: w.y - en.y };
        } else {
          const r = this.scene.collision[hit.index];
          this.drag = { mode: 'move-rect', index: hit.index, dx: w.x - r.x, dy: w.y - r.y };
        }
      }
      this.refreshChrome();
    });

    c.addEventListener('pointermove', (e) => {
      const w = this.toWorld(e.clientX, e.clientY);
      this.mouse.x = w.x;
      this.mouse.y = w.y;
      if (!this.drag) {
        c.style.cursor = this.tool === 'pan' ? 'grab' : (this.handleAt(w) ? 'nwse-resize' : 'crosshair');
        return;
      }

      switch (this.drag.mode) {
        case 'pan':
          this.pan.x = this.drag.panX - (e.clientX - this.drag.startX) / this.zoom;
          this.pan.y = this.drag.panY - (e.clientY - this.drag.startY) / this.zoom;
          break;
        case 'move-entity': {
          const en = this.scene.entities[this.drag.index];
          en.x = Math.round(w.x - this.drag.dx);
          en.y = Math.round(w.y - this.drag.dy);
          break;
        }
        case 'move-rect': {
          const r = this.scene.collision[this.drag.index];
          r.x = Math.round(w.x - this.drag.dx);
          r.y = Math.round(w.y - this.drag.dy);
          break;
        }
        case 'draw-rect': {
          const r = this.scene.collision[this.drag.index];
          r.x = Math.round(Math.min(this.drag.originX, w.x));
          r.y = Math.round(Math.min(this.drag.originY, w.y));
          r.w = Math.max(1, Math.round(Math.abs(w.x - this.drag.originX)));
          r.h = Math.max(1, Math.round(Math.abs(w.y - this.drag.originY)));
          break;
        }
        case 'resize-rect': {
          const r = this.scene.collision[this.drag.index];
          r.w = Math.max(1, Math.round(w.x - r.x));
          r.h = Math.max(1, Math.round(w.y - r.y));
          break;
        }
        case 'resize-zone': {
          const en = this.scene.entities[this.drag.index];
          en.w = Math.max(4, Math.round((w.x - en.x) * 2));
          en.h = Math.max(4, Math.round(en.y - w.y));
          break;
        }
        case 'resize-light': {
          const en = this.scene.entities[this.drag.index];
          en.props.radius = Math.max(4, Math.round(Math.hypot(w.x - en.x, w.y - en.y)));
          break;
        }
        default:
          break;
      }
      if (this.drag.mode !== 'pan') this.doc.dirty = true;
    });

    const end = () => {
      if (this.drag && this.drag.mode !== 'pan') { this.doc.commit(); }
      this.drag = null;
      this.mouse.down = false;
    };
    c.addEventListener('pointerup', end);
    c.addEventListener('pointercancel', end);

    c.addEventListener('wheel', (e) => {
      e.preventDefault();
      const before = this.toWorld(e.clientX, e.clientY);
      const next = e.deltaY < 0 ? this.zoom * 1.15 : this.zoom / 1.15;
      this.zoom = Math.max(0.4, Math.min(8, next));
      const after = this.toWorld(e.clientX, e.clientY);
      // Keep the point under the cursor fixed while zooming.
      this.pan.x += before.x - after.x;
      this.pan.y += before.y - after.y;
    }, { passive: false });
  }

  uniqueId(type) {
    const used = new Set(this.scene.entities.map((e) => e.id));
    let n = 1;
    while (used.has(`${type}_${n}`)) n++;
    return `${type}_${n}`;
  }

  hitTest(w) {
    // Entities first: they are smaller and sit on top of collision boxes.
    for (let i = this.scene.entities.length - 1; i >= 0; i--) {
      const b = entityBox(this.scene.entities[i]);
      if (w.x >= b.x && w.x <= b.x + b.w && w.y >= b.y && w.y <= b.y + b.h) {
        return { kind: 'entity', index: i };
      }
    }
    for (let i = this.scene.collision.length - 1; i >= 0; i--) {
      const r = this.scene.collision[i];
      if (w.x >= r.x && w.x <= r.x + r.w && w.y >= r.y && w.y <= r.y + r.h) {
        return { kind: 'rect', index: i };
      }
    }
    return null;
  }

  handleAt(w) {
    if (!this.selection) return null;
    const near = (hx, hy) => Math.abs(w.x - hx) < HANDLE / this.zoom && Math.abs(w.y - hy) < HANDLE / this.zoom;

    if (this.selection.kind === 'rect') {
      const r = this.scene.collision[this.selection.index];
      if (r && near(r.x + r.w, r.y + r.h)) return { mode: 'resize-rect', index: this.selection.index };
      return null;
    }
    const en = this.scene.entities[this.selection.index];
    if (!en) return null;
    if (en.type === 'light' && near(en.x + en.props.radius, en.y)) {
      return { mode: 'resize-light', index: this.selection.index };
    }
    const def = ENTITY_TYPES[en.type];
    if (def && def.resizable) {
      const b = entityBox(en);
      if (near(b.x + b.w, b.y)) return { mode: 'resize-zone', index: this.selection.index };
    }
    return null;
  }

  deleteSelection() {
    if (!this.selection) return;
    this.doc.begin();
    if (this.selection.kind === 'entity') this.scene.entities.splice(this.selection.index, 1);
    else this.scene.collision.splice(this.selection.index, 1);
    this.selection = null;
    this.doc.commit();
  }

  // ----------------------------------------------------------------- output

  exportFile() {
    const data = JSON.stringify(this.doc.export(), null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${this.scene.id || 'scene'}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
    this.doc.dirty = false;
    this.status(`Exported ${a.download} — put it in src/scenes/ and add it to manifest.js`);
  }

  async copyJSON() {
    const data = JSON.stringify(this.doc.export(), null, 2);
    try {
      await navigator.clipboard.writeText(data);
      this.status('Scene JSON copied to the clipboard.');
    } catch (err) {
      // Clipboard access is blocked in plenty of contexts; show it instead.
      const box = this.root.querySelector('#json-out');
      box.value = data;
      box.hidden = false;
      box.select();
      this.status('Clipboard blocked — the JSON is selected below, copy it manually.');
    }
  }

  testPlay() {
    try {
      sessionStorage.setItem('veridian.testScene', JSON.stringify(this.doc.export()));
    } catch (err) {
      this.status(`Could not hand the scene to the game: ${err.message}`);
      return;
    }
    const frame = this.root.querySelector('#play');
    const wrap = this.root.querySelector('#play-wrap');
    wrap.hidden = false;
    frame.src = `index.html?test=1&t=${Date.now()}`;
    this.status('Test playing. Close the panel to return to the editor.');
  }

  // ----------------------------------------------------------------- render

  tick() {
    this.lighting.update(1 / 60);
    this.draw();
    requestAnimationFrame(() => this.tick());
  }

  draw() {
    const ctx = this.ctx;
    const { width: cw, height: ch } = this.canvas;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = '#0d0e12';
    ctx.fillRect(0, 0, cw, ch);

    ctx.save();
    ctx.scale(this.zoom, this.zoom);
    ctx.translate(-this.pan.x, -this.pan.y);

    const { w, h } = this.scene.size;

    // Scene bounds
    ctx.fillStyle = '#15161d';
    ctx.fillRect(0, 0, w, h);

    for (const layer of this.scene.layers) {
      if (layer.overPlayer) continue;
      this.drawLayer(ctx, layer, w);
    }
    for (const e of this.scene.entities) {
      if (e.type === 'prop' && e.props.image && !e.props.overPlayer) this.drawProp(ctx, e);
    }
    for (const e of this.scene.entities) {
      if (e.type === 'prop' && e.props.image && e.props.overPlayer) this.drawProp(ctx, e);
    }
    for (const layer of this.scene.layers) {
      if (layer.overPlayer) this.drawLayer(ctx, layer, w);
    }

    if (this.showLighting) {
      // Render the lighting through a scratch context clipped to the scene so
      // the preview matches what the game will actually show.
      ctx.save();
      ctx.beginPath();
      ctx.rect(0, 0, w, h);
      ctx.clip();
      const fakeCamera = { drawX: 0, drawY: 0 };
      this.lighting.w = w;
      this.lighting.h = h;
      this.lighting.dark.canvas.width = w;
      this.lighting.dark.canvas.height = h;
      this.lighting.glow.canvas.width = w;
      this.lighting.glow.canvas.height = h;
      this.lighting.dark.ctx.imageSmoothingEnabled = false;
      this.lighting.glow.ctx.imageSmoothingEnabled = false;
      const lights = this.scene.entities
        .filter((e) => e.type === 'light')
        .map((e) => ({ x: e.x, y: e.y, ...e.props }));
      this.lighting.render(ctx, this.scene.ambient, lights, fakeCamera);
      ctx.restore();
    }

    if (this.showGrid) {
      ctx.strokeStyle = 'rgba(255,255,255,0.06)';
      ctx.lineWidth = 1 / this.zoom;
      for (let x = 0; x <= w; x += 16) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
      for (let y = 0; y <= h; y += 16) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
    }

    // Camera framing guide: what fits on screen at one time.
    ctx.strokeStyle = 'rgba(120,190,255,0.35)';
    ctx.lineWidth = 1 / this.zoom;
    ctx.strokeRect(0.5, 0.5, NATIVE_W, NATIVE_H);

    this.drawCollision(ctx);
    this.drawEntities(ctx);

    ctx.strokeStyle = '#3a3c48';
    ctx.lineWidth = 1 / this.zoom;
    ctx.strokeRect(0.5, 0.5, w - 1, h - 1);

    ctx.restore();
    this.drawReadout();
  }

  drawLayer(ctx, layer, sceneW) {
    const img = this.assets.images.get(layer.image);
    if (!img) return;
    if (layer.repeat) {
      for (let x = 0; x < sceneW; x += img.width) ctx.drawImage(img, x, layer.offsetY || 0);
    } else {
      ctx.drawImage(img, layer.offsetX || 0, layer.offsetY || 0);
    }
  }

  drawProp(ctx, e) {
    const img = this.assets.images.get(e.props.image);
    if (!img) return;
    ctx.drawImage(img, Math.round(e.x - img.width / 2), Math.round(e.y - img.height));
  }

  drawCollision(ctx) {
    const colours = { solid: '#4ad06a', oneway: '#d8c14a', ladder: '#4ab8d0', block: '#d0674a' };
    this.scene.collision.forEach((r, i) => {
      const selected = this.selection && this.selection.kind === 'rect' && this.selection.index === i;
      const c = colours[r.type] || colours.solid;
      ctx.fillStyle = `${c}22`;
      ctx.fillRect(r.x, r.y, r.w, r.h);
      ctx.strokeStyle = selected ? '#ffffff' : c;
      ctx.lineWidth = (selected ? 2 : 1) / this.zoom;
      ctx.strokeRect(r.x + 0.5 / this.zoom, r.y + 0.5 / this.zoom, r.w, r.h);
      if (r.type === 'oneway') {
        ctx.fillStyle = c;
        ctx.fillRect(r.x, r.y, r.w, Math.max(1, 2 / this.zoom));
      }
      if (selected) this.drawHandle(ctx, r.x + r.w, r.y + r.h);
    });
  }

  drawEntities(ctx) {
    this.scene.entities.forEach((e, i) => {
      const def = ENTITY_TYPES[e.type];
      const colour = def ? def.color : '#ffffff';
      const b = entityBox(e);
      const selected = this.selection && this.selection.kind === 'entity' && this.selection.index === i;

      if (e.type === 'light') {
        ctx.strokeStyle = `${e.props.color}66`;
        ctx.lineWidth = 1 / this.zoom;
        ctx.beginPath();
        ctx.arc(e.x, e.y, e.props.radius || 8, 0, Math.PI * 2);
        ctx.stroke();
        if (selected) this.drawHandle(ctx, e.x + (e.props.radius || 8), e.y);
      }

      ctx.fillStyle = `${colour}2a`;
      ctx.fillRect(b.x, b.y, b.w, b.h);
      ctx.strokeStyle = selected ? '#ffffff' : colour;
      ctx.lineWidth = (selected ? 2 : 1) / this.zoom;
      ctx.strokeRect(b.x + 0.5 / this.zoom, b.y + 0.5 / this.zoom, b.w, b.h);

      // Anchor pip: entities are positioned by their feet.
      ctx.fillStyle = colour;
      ctx.fillRect(e.x - 1, e.y - 1, 2, 2);

      if (this.zoom >= 1.4) {
        ctx.save();
        ctx.scale(1 / this.zoom, 1 / this.zoom);
        ctx.font = '10px ui-monospace, monospace';
        ctx.fillStyle = colour;
        ctx.fillText(e.id, (b.x) * this.zoom + 2, (b.y) * this.zoom - 3);
        ctx.restore();
      }
      if (selected && def && def.resizable) this.drawHandle(ctx, b.x + b.w, b.y);
    });
  }

  drawHandle(ctx, x, y) {
    const s = HANDLE / this.zoom;
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(x - s / 2, y - s / 2, s, s);
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 1 / this.zoom;
    ctx.strokeRect(x - s / 2, y - s / 2, s, s);
  }

  drawReadout() {
    const ctx = this.ctx;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.font = '11px ui-monospace, monospace';
    ctx.fillStyle = 'rgba(0,0,0,0.6)';
    ctx.fillRect(0, this.canvas.height - 20, 260, 20);
    ctx.fillStyle = '#9aa0ae';
    const label = this.tool === 'entity' ? `${this.tool}: ${this.placeType}` : this.tool;
    ctx.fillText(`${label}   ${Math.round(this.mouse.x)}, ${Math.round(this.mouse.y)}   ${this.zoom.toFixed(1)}x`, 8, this.canvas.height - 6);
  }
}
