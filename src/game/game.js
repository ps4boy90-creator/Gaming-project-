import { Screen, NATIVE_W, NATIVE_H } from '../core/screen.js';
import { Loop } from '../core/loop.js';
import { Input } from '../core/input.js';
import { Assets } from '../core/assets.js';
import { Camera } from '../gfx/camera.js';
import { Lighting } from '../gfx/lighting.js';
import { PostFX } from '../gfx/postfx.js';
import { Sprite, flipped } from '../gfx/sprite.js';
import { drawText, measure, lineHeight } from '../gfx/text.js';
import { Player } from './player.js';
import { Scene } from './scene.js';
import { Flags } from './flags.js';
import { Journal } from './journal.js';
import { Dialogue } from './dialogue.js';
import { Reader } from './reader.js';
import { Audio } from './audio.js';
import { Cutscene } from './cutscene.js';
import { Keypad } from './keypad.js';
import { Realization } from './realization.js';
import { Deductions } from './deductions.js';
import { Save } from './save.js';
import { Interaction, updateTriggers } from './interaction.js';
import { drawJournal, journalRows, JOURNAL_TABS, INK, INK_DIM, ACCENT, panel } from './ui.js';
import { CUTSCENES, START_SCENE, START_SPAWN } from '../scenes/manifest.js';

const PORTRAIT_NAMES = ['neutral', 'stern', 'worried', 'resolute', 'smile'];

export class Game {
  constructor(canvas) {
    this.screen = new Screen(canvas, NATIVE_W, NATIVE_H);
    this.ctx = this.screen.ctx;
    this.input = new Input();
    this.assets = new Assets();
    this.camera = new Camera(NATIVE_W, NATIVE_H);
    this.lighting = new Lighting(NATIVE_W, NATIVE_H);
    this.postfx = new PostFX(NATIVE_W, NATIVE_H);
    this.audio = new Audio();
    this.flags = new Flags();
    this.journal = new Journal();
    this.interaction = new Interaction();

    this.portraits = {};
    this.dialogue = new Dialogue(this.portraits);
    this.reader = new Reader(this.portraits);
    this.cutscene = new Cutscene(this.assets, this.audio, this.postfx);
    this.cutscene.onShake = (n) => this.camera.shake(n);
    this.keypad = new Keypad(this.audio);
    this.realization = new Realization(this.audio);
    this.deductions = new Deductions();
    this.deductions.watch(this.flags);

    this.state = 'boot';
    this.scene = null;
    this.player = null;
    this.firedTriggers = new Set();
    this.journalState = { tab: 0, index: 0 };
    this.progress = 0;
    this.error = null;
    this.showDebug = false;
    this._transition = null;

    this.loop = new Loop({
      update: (dt) => this.update(dt),
      render: () => this.render(),
    });

    // Any gesture unlocks audio; browsers will not start a context otherwise.
    const unlock = () => this.audio.resume();
    window.addEventListener('pointerdown', unlock);
    window.addEventListener('keydown', unlock);
  }

  readTestScene() {
    try {
      if (!new URLSearchParams(location.search).has('test')) return null;
      const raw = sessionStorage.getItem('veridian.testScene');
      return raw ? JSON.parse(raw) : null;
    } catch (err) {
      console.warn('Could not read the test scene:', err);
      return null;
    }
  }

  /** The systems an entity behaviour is allowed to reach. */
  get api() {
    return {
      flags: this.flags,
      journal: this.journal,
      dialogue: this.dialogue,
      reader: this.reader,
      audio: this.audio,
      camera: this.camera,
      keypad: this.keypad,
      game: this,
    };
  }

  async boot() {
    this.assets.onProgress = (p) => { this.progress = p; };
    this.loop.start();

    try {
      await this.assets.load({
        images: [
          'sprites/scientist/scientist.png',
          ...PORTRAIT_NAMES.map((n) => `portraits/scientist/${n}.png`),
          // Cutscene stills load up front: a cutscene fires mid-step from a
          // trigger, with no opportunity to await anything.
          ...Object.values(CUTSCENES).map((c) => c.image).filter(Boolean),
        ],
        json: ['sprites/scientist/scientist.json'],
      });

      for (const name of PORTRAIT_NAMES) {
        this.portraits[name] = this.assets.image(`portraits/scientist/${name}.png`);
      }

      const spec = this.assets.data('sprites/scientist/scientist.json');
      this.playerSprite = new Sprite(this.assets.image(spec.image), spec);

      // Test-play from the editor: the scene arrives through sessionStorage
      // rather than the manifest, and starts fresh with no saved progress.
      const test = this.readTestScene();
      if (test) {
        Scene.overrides.set(test.id, test);
        await this.travel(test.id, this.testSpawn || 'start', { instant: true });
        this.state = 'playing';
        return;
      }

      const save = Save.read();
      if (save) {
        this.journal.load(save.journal);
        // Load the journal first: restoring flags re-arms the deduction watcher,
        // and a realization already recorded must not be announced again.
        this.flags.load(save.flags);
        await this.travel(save.scene || START_SCENE, save.spawn || START_SPAWN, { instant: true });
        if (save.x !== undefined) this.player.setPosition(save.x, save.y);
        this.camera.snapTo(this.player.x, this.player.y - 20);
        this.dialogue.say('Where I left off.', { portrait: 'neutral' });
      } else {
        await this.travel(START_SCENE, START_SPAWN, { instant: true });
        this.dialogue.say('Four-forty. The alarm never got the chance.', { portrait: 'worried' });
      }

      this.state = 'playing';
    } catch (err) {
      console.error(err);
      this.error = err.message || String(err);
      this.state = 'error';
    }
  }

  async travel(sceneId, spawnId = 'start', { instant = false } = {}) {
    if (this._transition) return;
    const go = async () => {
      const data = await Scene.loadData(sceneId);
      await this.assets.load({ images: Scene.assetsFor(data) });
      const scene = new Scene(data, this.assets);

      this.scene = scene;
      this.firedTriggers.clear();
      const spawn = scene.spawn(spawnId);

      if (!this.player) {
        this.player = new Player(this.playerSprite, spawn.x, spawn.y);
        this.player.onFootstep = (kind) => this.audio.play(kind);
      } else {
        this.player.setPosition(spawn.x, spawn.y);
      }
      this.player.facing = spawn.facing;
      this.player.allowJump = scene.allowJump;

      this.camera.setBounds(scene.size.w, scene.size.h);
      this.camera.snapTo(spawn.x, spawn.y - 20);
      this.audio.setAmbience(scene.ambience);
    };

    if (instant) {
      await go();
      this.postfx.setFade('#000000', 0);
      return;
    }

    // Fade out, swap, fade in -- so a door never shows a hitch on a slow load.
    this._transition = { phase: 'out', t: 0 };
    this.state = 'transition';
    await new Promise((resolve) => { this._transition.resolve = resolve; });
    await go();
    this._transition = { phase: 'in', t: 0 };
    await new Promise((resolve) => { this._transition.resolve = resolve; });
    this._transition = null;
    this.state = 'playing';
  }

  playCutscene(id) {
    const def = CUTSCENES[id];
    if (!def) {
      console.warn(`Unknown cutscene "${id}"`);
      return;
    }
    const returnAmbience = this.scene ? this.scene.ambience : 'none';
    this.state = 'cutscene';
    this.cutscene.play(def, () => {
      // A cutscene may hand off to a scene rather than returning to the one it
      // played over -- that is how the drive up the mountain arrives at the gate.
      if (def.then && def.then.scene) {
        this.travel(def.then.scene, def.then.spawn || 'start', { instant: true })
          .then(() => { this.state = 'playing'; this.postfx.setFade('#000000', 0); });
        return;
      }
      this.state = 'playing';
      this.audio.setAmbience(returnAmbience);
      this.postfx.setFade('#000000', 0);
    });
  }

  save() {
    Save.write({
      scene: this.scene ? this.scene.id : START_SCENE,
      spawn: START_SPAWN,
      x: this.player ? Math.round(this.player.x) : undefined,
      y: this.player ? Math.round(this.player.y) : undefined,
      flags: this.flags.toJSON(),
      journal: this.journal.toJSON(),
    });
  }

  update(dt) {
    this.lighting.update(dt);
    this.postfx.update(dt);
    this.camera.update(dt);

    switch (this.state) {
      case 'boot':
      case 'error':
        break;

      case 'transition': {
        const tr = this._transition;
        if (tr) {
          tr.t += dt;
          const d = 0.28;
          const k = Math.min(1, tr.t / d);
          this.postfx.setFade('#000000', tr.phase === 'out' ? k : 1 - k);
          if (k >= 1 && tr.resolve) {
            const resolve = tr.resolve;
            tr.resolve = null;
            resolve();
          }
        }
        break;
      }

      case 'cutscene':
        this.cutscene.update(dt, this.input);
        break;

      case 'journal': {
        if (this.input.justPressed('cancel') || this.input.justPressed('journal')) {
          this.state = 'playing';
          break;
        }
        // Derived from the just-pressed set rather than from held state: a
        // quick tap can have its keyup land in the same tick as its keydown.
        const tabDelta = (this.input.justPressed('right') ? 1 : 0)
          - (this.input.justPressed('left') ? 1 : 0);
        if (tabDelta !== 0) {
          this.journalState.tab = (this.journalState.tab + tabDelta + JOURNAL_TABS.length) % JOURNAL_TABS.length;
          this.journalState.index = 0;
          this.audio.play('blip');
        }
        const rows = journalRows(this.journal, this.journalState.tab).length;
        if (this.input.justPressed('up')) {
          this.journalState.index = Math.max(0, this.journalState.index - 1);
          this.audio.play('blip');
        }
        if (this.input.justPressed('down')) {
          this.journalState.index = Math.min(Math.max(0, rows - 1), this.journalState.index + 1);
          this.audio.play('blip');
        }
        break;
      }

      case 'keypad':
        this.keypad.update(dt, this.input, this.api);
        if (!this.keypad.open) this.state = 'playing';
        break;

      case 'realization':
        this.realization.update(dt, this.input);
        if (!this.realization.open) this.state = 'playing';
        break;

      case 'reading':
        this.reader.update(dt, this.input);
        if (!this.reader.open) this.state = 'playing';
        break;

      case 'playing':
        this.updatePlaying(dt);
        break;
      default:
        break;
    }

    // A realization waits for a clear screen. Its flag is set by a note or a
    // clue closing, so without this the card would land on top of the page the
    // player is still reading.
    if (this.state === 'playing' && this.deductions.waiting && !this.reader.open) {
      const next = this.deductions.take();
      if (next) {
        this.dialogue.clear();
        this.journal.addDeduction({ id: next.id, title: next.title, pages: next.note });
        this.realization.show(next, () => {
          if (next.setsFlag) this.flags.set(next.setsFlag);
        });
        this.state = 'realization';
      }
    }

    this.dialogue.update(dt, this.state === 'playing' ? this.input : null);

    if (this.input.justPressed('cancel') && this.state === 'playing') {
      this.dialogue.clear();
    }
    if (this.input.down.has('F3') || this.input.justPressed('debug')) this.showDebug = !this.showDebug;

    this.input.endFrame();
  }

  updatePlaying(dt) {
    if (!this.scene || !this.player) return;

    this.player.update(dt, this.input, this.scene.world);
    this.camera.follow(this.player.x, this.player.y - this.player.body.h * 0.6, dt);

    const live = this.scene.entities.filter((e) => !e.removed);
    updateTriggers(this.player, live, this.flags, this.api, this.firedTriggers);

    this.interaction.update(this.player, live, this.flags);
    if (this.input.justPressed('interact') && this.interaction.target) {
      this.interaction.fire(this.api);
      if (this.reader.open) this.state = 'reading';
      else if (this.keypad.open) this.state = 'keypad';
    }

    if (this.input.justPressed('journal')) {
      this.journal.markRead();
      this.journalState.index = Math.min(this.journalState.index, Math.max(0, this.journal.notes.length - 1));
      this.state = 'journal';
      this.audio.play('blip');
    }
  }

  render() {
    const ctx = this.ctx;
    ctx.imageSmoothingEnabled = false;
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'source-over';
    ctx.fillStyle = '#05060a';
    ctx.fillRect(0, 0, NATIVE_W, NATIVE_H);

    if (this.state === 'boot') this.renderBoot();
    else if (this.state === 'error') this.renderError();
    else if (this.state === 'cutscene') this.cutscene.draw(ctx, NATIVE_W, NATIVE_H);
    else this.renderWorld();

    if (this.state === 'journal') drawJournal(ctx, this.journal, this.journalState, NATIVE_W, NATIVE_H);
    if (this.reader.open) this.reader.draw(ctx, NATIVE_W, NATIVE_H);
    if (this.keypad.open) this.keypad.draw(ctx, NATIVE_W, NATIVE_H);
    this.realization.draw(ctx, NATIVE_W, NATIVE_H, this.portraits);
    // Each overlay owns the screen while it is open.
    if (this.state !== 'journal' && !this.reader.open
      && !this.keypad.open && !this.realization.open) {
      this.dialogue.draw(ctx, NATIVE_W, NATIVE_H);
    }

    this.postfx.render(ctx);
    if (this.showDebug) this.renderDebug();

    this.screen.present();
  }

  renderWorld() {
    const ctx = this.ctx;
    if (!this.scene || !this.player) return;

    this.scene.backdrop.drawBehind(ctx, this.camera);

    for (const p of this.scene.props(this.flags, false)) this.drawProp(ctx, p);
    this.player.draw(ctx, this.camera);
    for (const p of this.scene.props(this.flags, true)) this.drawProp(ctx, p);

    this.scene.backdrop.drawFront(ctx, this.camera);

    this.lighting.render(ctx, this.scene.ambient, this.scene.lights(this.flags), this.camera);

    // The prompt sits above the lighting pass: a note in a dark corner still
    // has to be findable, or the room becomes a pixel hunt.
    if (this.state === 'playing') this.interaction.draw(ctx, this.camera);

    if (this.journal.unread > 0 && this.state === 'playing') {
      drawText(ctx, 'TAB', 6, 6, { color: ACCENT });
      drawText(ctx, 'journal', 6 + measure('TAB '), 6, { color: INK_DIM });
    }
  }

  drawProp(ctx, entity) {
    const img = this.assets.images.get(entity.props.image);
    if (!img) return;
    const src = entity.props.flip ? flipped(img) : img;
    const x = Math.round(entity.x - img.width / 2 - this.camera.drawX);
    const y = Math.round(entity.y - img.height - this.camera.drawY);
    ctx.drawImage(src, x, y);
  }

  renderBoot() {
    const ctx = this.ctx;
    const w = 140;
    const x = Math.round((NATIVE_W - w) / 2);
    const y = Math.round(NATIVE_H / 2);
    drawText(ctx, 'VERIDIAN', Math.round((NATIVE_W - measure('VERIDIAN')) / 2), y - 24, { color: ACCENT });
    ctx.fillStyle = '#23242e';
    ctx.fillRect(x, y, w, 3);
    ctx.fillStyle = INK;
    ctx.fillRect(x, y, Math.round(w * this.progress), 3);
    const label = `${Math.round(this.progress * 100)}%`;
    drawText(ctx, label, Math.round((NATIVE_W - measure(label)) / 2), y + 10, { color: INK_DIM });
  }

  renderError() {
    const ctx = this.ctx;
    panel(ctx, 16, 60, NATIVE_W - 32, 90);
    drawText(ctx, 'FAILED TO START', 24, 70, { color: '#e06a5a' });
    const words = String(this.error).match(/.{1,58}/g) || [];
    words.slice(0, 5).forEach((line, i) => {
      drawText(ctx, line, 24, 84 + i * lineHeight(), { color: INK });
    });
    drawText(ctx, 'Serve the folder over http, not file://', 24, 134, { color: INK_DIM });
  }

  renderDebug() {
    const ctx = this.ctx;
    const lines = [
      `fps ${this.loop.fps}  state ${this.state}`,
      this.player ? `x ${Math.round(this.player.x)} y ${Math.round(this.player.y)} ${this.player.state}` : '',
      this.scene ? `scene ${this.scene.id}  ents ${this.scene.entities.length}` : '',
    ].filter(Boolean);
    lines.forEach((line, i) => drawText(ctx, line, 4, 4 + i * lineHeight(), { color: '#7dd87d' }));

    if (this.scene && this.player) {
      ctx.strokeStyle = 'rgba(125,216,125,0.6)';
      ctx.lineWidth = 1;
      for (const r of this.scene.world.rects) {
        ctx.strokeRect(r.x - this.camera.drawX + 0.5, r.y - this.camera.drawY + 0.5, r.w - 1, r.h - 1);
      }
      ctx.strokeStyle = 'rgba(255,120,120,0.9)';
      const b = this.player.box;
      ctx.strokeRect(b.x - this.camera.drawX + 0.5, b.y - this.camera.drawY + 0.5, b.w - 1, b.h - 1);
    }
  }
}
