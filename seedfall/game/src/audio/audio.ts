import { Ambience } from '../world/ship/kit';

/* Procedural sound: ship hum, vents, footsteps, doors, the lift, VESTA's chime, the lounge's
 * generative music, and the humming voice on the signal. Nothing is downloaded. */

type Vec3 = { x: number; y: number; z: number };

interface Layer {
  gain: GainNode;
  levels: Partial<Record<Ambience, number>>;
}

export class AudioEngine {
  ctx: AudioContext | null = null;
  private master!: GainNode;
  private sfx!: GainNode;
  private amb!: GainNode;
  private musicBus!: GainNode;
  private reverb!: ConvolverNode;
  private send!: GainNode;
  private white!: AudioBuffer;
  private brown!: AudioBuffer;
  private layers: Layer[] = [];
  private listener = { x: 0, y: 0, z: 0, yaw: 0 };
  private volume = 0.8;
  private ambience: Ambience = 'hab';
  private musicOn = false;
  private musicTimer = 0;
  private musicPos: Vec3 = { x: 0, y: 0, z: 0 };
  private musicGain!: GainNode;
  private chord = 0;
  private signal: { stop: () => void } | null = null;
  private loops = new Map<string, { gain: GainNode; pos: Vec3; stop: () => void }>();
  private helmet = 1;

  start(): void {
    if (this.ctx) {
      void this.ctx.resume();
      return;
    }
    const Ctor = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return;
    const ctx = new Ctor();
    this.ctx = ctx;
    this.master = ctx.createGain();
    this.master.gain.value = this.volume;
    this.master.connect(ctx.destination);
    this.sfx = ctx.createGain();
    this.amb = ctx.createGain();
    this.musicBus = ctx.createGain();
    this.sfx.connect(this.master);
    this.amb.connect(this.master);
    this.musicBus.connect(this.master);
    this.reverb = ctx.createConvolver();
    this.reverb.buffer = this.impulse(2.6, 2.2);
    this.send = ctx.createGain();
    this.send.gain.value = 0.35;
    this.send.connect(this.reverb);
    this.reverb.connect(this.master);
    this.white = this.noise('white', 2);
    this.brown = this.noise('brown', 4);
    this.musicGain = ctx.createGain();
    this.musicGain.gain.value = 0;
    this.musicGain.connect(this.musicBus);
    this.musicGain.connect(this.send);
    this.buildAmbience();
  }

  setVolume(v: number): void {
    this.volume = v;
    if (this.ctx) this.master.gain.setTargetAtTime(v, this.ctx.currentTime, 0.05);
  }

  private noise(kind: 'white' | 'brown', seconds: number): AudioBuffer {
    const ctx = this.ctx!;
    const buf = ctx.createBuffer(1, ctx.sampleRate * seconds, ctx.sampleRate);
    const d = buf.getChannelData(0);
    let last = 0;
    for (let i = 0; i < d.length; i++) {
      const w = Math.random() * 2 - 1;
      if (kind === 'white') d[i] = w;
      else {
        last = (last + 0.02 * w) / 1.02;
        d[i] = last * 3.5;
      }
    }
    return buf;
  }

  private impulse(seconds: number, decay: number): AudioBuffer {
    const ctx = this.ctx!;
    const len = ctx.sampleRate * seconds;
    const buf = ctx.createBuffer(2, len, ctx.sampleRate);
    for (let c = 0; c < 2; c++) {
      const d = buf.getChannelData(c);
      for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, decay);
    }
    return buf;
  }

  private loopSource(buf: AudioBuffer): AudioBufferSourceNode {
    const s = this.ctx!.createBufferSource();
    s.buffer = buf;
    s.loop = true;
    s.loopStart = Math.random() * 0.5;
    s.start(0, Math.random() * buf.duration);
    return s;
  }

  private layer(levels: Layer['levels'], build: (out: GainNode) => void): void {
    const g = this.ctx!.createGain();
    g.gain.value = 0;
    g.connect(this.amb);
    build(g);
    this.layers.push({ gain: g, levels });
  }

  private buildAmbience(): void {
    const ctx = this.ctx!;
    // deep hull hum
    this.layer({ hab: 0.5, lift: 0.6, spine: 0.6, vault: 0.45, hangar: 0.7, machine: 0.8, garden: 0.4 }, (out) => {
      const src = this.loopSource(this.brown);
      const lp = ctx.createBiquadFilter();
      lp.type = 'lowpass';
      lp.frequency.value = 140;
      src.connect(lp).connect(out);
      for (const [f, g] of [[52, 0.05], [104.5, 0.022], [156.3, 0.008]] as const) {
        const o = ctx.createOscillator();
        o.frequency.value = f;
        const og = ctx.createGain();
        og.gain.value = g;
        o.connect(og).connect(out);
        o.start();
      }
    });
    // air vents
    this.layer({ hab: 0.05, lift: 0.02, spine: 0.06, vault: 0.03, hangar: 0.04, machine: 0.05, garden: 0.07 }, (out) => {
      const src = this.loopSource(this.white);
      const bp = ctx.createBiquadFilter();
      bp.type = 'bandpass';
      bp.frequency.value = 900;
      bp.Q.value = 0.6;
      src.connect(bp).connect(out);
    });
    // machinery whine
    this.layer({ machine: 0.12, hangar: 0.03, lift: 0.02 }, (out) => {
      const o = ctx.createOscillator();
      o.type = 'sawtooth';
      o.frequency.value = 118;
      const lp = ctx.createBiquadFilter();
      lp.type = 'lowpass';
      lp.frequency.value = 320;
      const g = ctx.createGain();
      g.gain.value = 0.25;
      o.connect(lp).connect(g).connect(out);
      o.start();
    });
    // cryo cold: low drone + icy hiss
    this.layer({ vault: 0.5, spine: 0.08 }, (out) => {
      const o = ctx.createOscillator();
      o.frequency.value = 38;
      const og = ctx.createGain();
      og.gain.value = 0.12;
      o.connect(og).connect(out);
      o.start();
      const o2 = ctx.createOscillator();
      o2.frequency.value = 57.2;
      const og2 = ctx.createGain();
      og2.gain.value = 0.05;
      o2.connect(og2).connect(out);
      o2.start();
      const src = this.loopSource(this.white);
      const hp = ctx.createBiquadFilter();
      hp.type = 'highpass';
      hp.frequency.value = 5200;
      const hg = ctx.createGain();
      hg.gain.value = 0.03;
      src.connect(hp).connect(hg).connect(out);
    });
    // big-room rumble
    this.layer({ hangar: 0.5 }, (out) => {
      const src = this.loopSource(this.brown);
      const lp = ctx.createBiquadFilter();
      lp.type = 'lowpass';
      lp.frequency.value = 70;
      const g = ctx.createGain();
      g.gain.value = 1.4;
      src.connect(lp).connect(g).connect(out);
      g.connect(this.send);
    });
    // garden: trickling irrigation
    this.layer({ garden: 0.25 }, (out) => {
      const src = this.loopSource(this.white);
      const bp = ctx.createBiquadFilter();
      bp.type = 'bandpass';
      bp.frequency.value = 2400;
      bp.Q.value = 3;
      const am = ctx.createGain();
      am.gain.value = 0.05;
      const lfo = ctx.createOscillator();
      lfo.frequency.value = 6.3;
      const lfoG = ctx.createGain();
      lfoG.gain.value = 0.04;
      lfo.connect(lfoG).connect(am.gain);
      lfo.start();
      src.connect(bp).connect(am).connect(out);
    });
    this.setAmbience('hab');
  }

  setAmbience(a: Ambience): void {
    this.ambience = a;
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    for (const l of this.layers) l.gain.gain.setTargetAtTime((l.levels[a] ?? 0) * this.helmet, t, 0.8);
    this.send.gain.setTargetAtTime(a === 'hangar' ? 0.7 : a === 'vault' ? 0.55 : a === 'spine' ? 0.45 : 0.28, t, 0.5);
  }

  setListener(pos: Vec3, yaw: number): void {
    this.listener.x = pos.x;
    this.listener.y = pos.y;
    this.listener.z = pos.z;
    this.listener.yaw = yaw;
  }

  /** Distance gain and stereo pan for a world position. */
  private spatial(pos?: Vec3): { gain: number; pan: number } {
    if (!pos) return { gain: 1, pan: 0 };
    const dx = pos.x - this.listener.x;
    const dy = (pos.y - this.listener.y) * 2.5;
    const dz = pos.z - this.listener.z;
    const d = Math.hypot(dx, dy, dz);
    const gain = 1 / (1 + d * 0.35) * (d > 30 ? Math.max(0, 1 - (d - 30) / 20) : 1);
    const rx = Math.cos(this.listener.yaw);
    const rz = -Math.sin(this.listener.yaw);
    const pan = d > 0.3 ? Math.max(-0.85, Math.min(0.85, (dx * rx + dz * rz) / d)) : 0;
    return { gain, pan };
  }

  private out(pos?: Vec3, wet = 0.25): { node: AudioNode; gain: number } {
    const ctx = this.ctx!;
    const { gain, pan } = this.spatial(pos);
    const p = ctx.createStereoPanner();
    p.pan.value = pan;
    p.connect(this.sfx);
    const w = ctx.createGain();
    w.gain.value = wet;
    p.connect(w).connect(this.send);
    return { node: p, gain };
  }

  private burst(dest: AudioNode, t: number, dur: number, peak: number, filter: BiquadFilterType, freq: number, q = 1, sweepTo?: number): void {
    const ctx = this.ctx!;
    const s = ctx.createBufferSource();
    s.buffer = this.white;
    const f = ctx.createBiquadFilter();
    f.type = filter;
    f.frequency.setValueAtTime(freq, t);
    if (sweepTo) f.frequency.exponentialRampToValueAtTime(sweepTo, t + dur);
    f.Q.value = q;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(peak, t + Math.min(0.02, dur * 0.2));
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    s.connect(f).connect(g).connect(dest);
    s.start(t, Math.random() * 1.5);
    s.stop(t + dur + 0.05);
  }

  private tone(dest: AudioNode, t: number, freq: number, dur: number, peak: number, type: OscillatorType = 'sine', endFreq?: number): void {
    const ctx = this.ctx!;
    const o = ctx.createOscillator();
    o.type = type;
    o.frequency.setValueAtTime(freq, t);
    if (endFreq) o.frequency.exponentialRampToValueAtTime(endFreq, t + dur);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(peak, t + 0.008);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g).connect(dest);
    o.start(t);
    o.stop(t + dur + 0.05);
  }

  play(kind: string, opts: { x?: number; y?: number; z?: number; speed?: number; crouch?: boolean; heavy?: boolean; strength?: number } = {}): void {
    if (!this.ctx || this.ctx.state !== 'running') return;
    const t = this.ctx.currentTime;
    const pos = opts.x !== undefined ? { x: opts.x, y: opts.y ?? 0, z: opts.z ?? 0 } : undefined;
    switch (kind) {
      case 'step': {
        const { node, gain } = this.out(undefined, this.ambience === 'hangar' ? 0.5 : 0.18);
        const loud = (opts.crouch ? 0.25 : 0.55 + Math.min(0.5, (opts.speed ?? 2) / 9)) * gain;
        this.burst(node, t, 0.09, 0.28 * loud, 'bandpass', 1500 + Math.random() * 900, 1.4);
        this.burst(node, t, 0.05, 0.14 * loud, 'highpass', 4500, 0.7);
        this.tone(node, t, 80 + Math.random() * 25, 0.08, 0.35 * loud, 'sine');
        break;
      }
      case 'land': {
        const { node } = this.out(undefined, 0.3);
        this.tone(node, t, 70, 0.18, 0.6, 'sine', 45);
        this.burst(node, t, 0.15, 0.3, 'bandpass', 1200, 1.2);
        break;
      }
      case 'jump': {
        const { node } = this.out(undefined, 0.2);
        this.burst(node, t, 0.08, 0.12, 'bandpass', 900, 1);
        break;
      }
      case 'door-open':
      case 'door-close': {
        const { node, gain } = this.out(pos, 0.35);
        if (gain < 0.03) break;
        const heavy = !!opts.heavy;
        const dur = heavy ? 0.85 : 0.5;
        const up = kind === 'door-open';
        this.burst(node, t, 0.12, 0.45 * gain, 'highpass', 3500, 0.7);
        this.burst(node, t + 0.03, dur, 0.35 * gain, 'bandpass', up ? 350 : 1300, 1.3, up ? 1400 : 380);
        this.tone(node, t + dur, heavy ? 48 : 70, 0.22, 0.5 * gain, 'sine', 35);
        this.burst(node, t + dur, 0.06, 0.25 * gain, 'bandpass', 700, 2);
        break;
      }
      case 'vesta': {
        const { node } = this.out(undefined, 0.6);
        this.tone(node, t, 783.99, 0.9, 0.08, 'sine');
        this.tone(node, t + 0.14, 1174.66, 1.1, 0.07, 'sine');
        this.tone(node, t, 1567.98, 0.5, 0.015, 'sine');
        break;
      }
      case 'ui': {
        const { node } = this.out(undefined, 0.05);
        this.tone(node, t, 1400, 0.05, 0.05, 'square');
        break;
      }
      case 'sit':
      case 'stand': {
        const { node } = this.out(undefined, 0.15);
        this.burst(node, t, 0.22, 0.12, 'lowpass', kind === 'sit' ? 1400 : 1800, 0.8);
        if (kind === 'sit') this.tone(node, t + 0.05, 95, 0.12, 0.15);
        break;
      }
      case 'lift': {
        const { node } = this.out(undefined, 0.3);
        const o = this.ctx.createOscillator();
        o.type = 'sawtooth';
        o.frequency.setValueAtTime(40, t);
        o.frequency.linearRampToValueAtTime(70, t + 1.0);
        o.frequency.linearRampToValueAtTime(42, t + 2.4);
        const lp = this.ctx.createBiquadFilter();
        lp.type = 'lowpass';
        lp.frequency.value = 220;
        const g = this.ctx.createGain();
        g.gain.setValueAtTime(0.0001, t);
        g.gain.exponentialRampToValueAtTime(0.25, t + 0.5);
        g.gain.setValueAtTime(0.25, t + 1.9);
        g.gain.exponentialRampToValueAtTime(0.0001, t + 2.6);
        o.connect(lp).connect(g).connect(node);
        o.start(t);
        o.stop(t + 2.7);
        this.tone(node, t + 0.05, 60, 0.2, 0.4);
        this.tone(node, t + 2.45, 55, 0.25, 0.45);
        this.tone(node, t + 2.55, 880, 0.4, 0.04);
        break;
      }
      case 'coffee': {
        const { node } = this.out(pos, 0.2);
        const s = this.ctx.createBufferSource();
        s.buffer = this.white;
        const bp = this.ctx.createBiquadFilter();
        bp.type = 'bandpass';
        bp.frequency.value = 650;
        bp.Q.value = 2.5;
        const g = this.ctx.createGain();
        g.gain.value = 0;
        const lfo = this.ctx.createOscillator();
        lfo.frequency.value = 11;
        const lg = this.ctx.createGain();
        lg.gain.value = 0.25;
        lfo.connect(lg).connect(g.gain);
        s.connect(bp).connect(g).connect(node);
        s.start(t);
        lfo.start(t);
        s.stop(t + 2.6);
        lfo.stop(t + 2.6);
        this.tone(node, t, 140, 0.3, 0.2, 'triangle', 90);
        this.tone(node, t + 2.6, 1760, 0.2, 0.05);
        break;
      }
      case 'dispense': {
        const { node } = this.out(pos, 0.2);
        this.tone(node, t, 180, 0.9, 0.12, 'sawtooth', 120);
        this.tone(node, t + 0.95, 65, 0.25, 0.5);
        this.tone(node, t + 1.1, 1320, 0.15, 0.04);
        break;
      }
      case 'scope': {
        const { node } = this.out(undefined, 0.1);
        this.tone(node, t, 300, 0.8, 0.06, 'sawtooth', 520);
        break;
      }
      case 'beep': {
        const { node } = this.out(undefined, 0.1);
        this.tone(node, t, 1046.5, 0.12, 0.05, 'sine');
        break;
      }
      case 'success': {
        const { node } = this.out(undefined, 0.3);
        [659.25, 783.99, 1046.5].forEach((f, i) => this.tone(node, t + i * 0.12, f, 0.35, 0.05));
        break;
      }
      case 'denied': {
        const { node } = this.out(pos, 0.1);
        this.tone(node, t, 220, 0.18, 0.12, 'square');
        this.tone(node, t + 0.2, 180, 0.25, 0.12, 'square');
        break;
      }
      case 'flashlight': {
        const { node } = this.out(undefined, 0.05);
        this.burst(node, t, 0.03, 0.2, 'highpass', 3000, 1);
        this.tone(node, t, 2200, 0.02, 0.05, 'square');
        break;
      }
      case 'decon': {
        const { node } = this.out(pos, 0.4);
        this.burst(node, t, 3.5, 0.3, 'highpass', 2000, 0.5);
        this.burst(node, t + 0.5, 2.5, 0.15, 'bandpass', 500, 0.8, 250);
        this.tone(node, t + 3.6, 880, 0.3, 0.05);
        this.tone(node, t + 3.75, 1318.5, 0.4, 0.05);
        break;
      }
      case 'breath': {
        const { node } = this.out(undefined, 0.1);
        this.burst(node, t, 1.6, 0.08, 'bandpass', 600, 0.7, 380);
        this.burst(node, t + 1.9, 2.0, 0.06, 'bandpass', 450, 0.7, 300);
        break;
      }
    }
  }

  // --------------------------------------------------------------- looping positional sources

  toggleLoop(id: string, kind: 'shower' | 'treadmill', pos: Vec3): boolean {
    if (!this.ctx) return false;
    const existing = this.loops.get(id);
    if (existing) {
      existing.stop();
      this.loops.delete(id);
      return false;
    }
    const ctx = this.ctx;
    const gain = ctx.createGain();
    gain.gain.value = 0;
    gain.connect(this.sfx);
    gain.connect(this.send);
    const src = this.loopSource(this.white);
    const f = ctx.createBiquadFilter();
    f.type = kind === 'shower' ? 'highpass' : 'bandpass';
    f.frequency.value = kind === 'shower' ? 1200 : 300;
    const g2 = ctx.createGain();
    g2.gain.value = kind === 'shower' ? 0.3 : 0.15;
    src.connect(f).connect(g2).connect(gain);
    this.loops.set(id, { gain, pos, stop: () => { src.stop(); gain.disconnect(); } });
    return true;
  }

  // --------------------------------------------------------------- lounge music

  setMusic(on: boolean, pos: Vec3): void {
    this.musicOn = on;
    this.musicPos = pos;
    if (!on && this.ctx) this.musicGain.gain.setTargetAtTime(0, this.ctx.currentTime, 0.6);
    this.musicTimer = 0;
  }

  get musicPlaying(): boolean {
    return this.musicOn;
  }

  private playChord(): void {
    const ctx = this.ctx!;
    const t = ctx.currentTime + 0.05;
    const chords = [
      [45, 52, 55, 59, 60],
      [41, 48, 52, 57, 64],
      [48, 55, 59, 64, 67],
      [43, 50, 52, 59, 62],
    ];
    const notes = chords[this.chord % chords.length];
    this.chord++;
    const dur = 8.2;
    const lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.setValueAtTime(500, t);
    lp.frequency.linearRampToValueAtTime(1100, t + dur * 0.5);
    lp.frequency.linearRampToValueAtTime(600, t + dur);
    lp.connect(this.musicGain);
    for (const n of notes) {
      const f = 440 * Math.pow(2, (n - 69) / 12);
      for (const det of [-6, 7]) {
        const o = ctx.createOscillator();
        o.type = 'sawtooth';
        o.frequency.value = f;
        o.detune.value = det;
        const g = ctx.createGain();
        g.gain.setValueAtTime(0.0001, t);
        g.gain.linearRampToValueAtTime(0.018, t + 2.2);
        g.gain.setValueAtTime(0.018, t + dur - 2);
        g.gain.linearRampToValueAtTime(0.0001, t + dur + 0.8);
        o.connect(g).connect(lp);
        o.start(t);
        o.stop(t + dur + 1);
      }
    }
    // a slow, sparse melody over the chord
    let tt = t + 0.6;
    while (tt < t + dur - 0.8) {
      const n = notes[1 + Math.floor(Math.random() * 4)] + 12 + (Math.random() < 0.3 ? 12 : 0);
      const f = 440 * Math.pow(2, (n - 69) / 12);
      const o = ctx.createOscillator();
      o.type = 'triangle';
      o.frequency.value = f;
      const g = ctx.createGain();
      g.gain.setValueAtTime(0.0001, tt);
      g.gain.exponentialRampToValueAtTime(0.05, tt + 0.01);
      g.gain.exponentialRampToValueAtTime(0.0001, tt + 1.6);
      o.connect(g).connect(this.musicGain);
      o.start(tt);
      o.stop(tt + 1.7);
      tt += [0.5, 0.75, 1, 1.5][Math.floor(Math.random() * 4)];
    }
  }

  // --------------------------------------------------------------- the signal

  startSignal(): void {
    if (!this.ctx || this.signal) return;
    const ctx = this.ctx;
    const out = ctx.createGain();
    out.gain.value = 0.9;
    out.connect(this.sfx);
    // radio chain
    const hp = ctx.createBiquadFilter();
    hp.type = 'highpass';
    hp.frequency.value = 320;
    const lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = 2600;
    const shaper = ctx.createWaveShaper();
    const curve = new Float32Array(1024);
    for (let i = 0; i < 1024; i++) {
      const x = (i / 1023) * 2 - 1;
      curve[i] = Math.tanh(x * 2.2);
    }
    shaper.curve = curve;
    const drop = ctx.createGain();
    hp.connect(lp).connect(shaper).connect(drop).connect(out);
    // voice: sawtooth through a closed-mouth formant
    const voice = ctx.createOscillator();
    voice.type = 'sawtooth';
    const vib = ctx.createOscillator();
    vib.frequency.value = 5.3;
    const vibG = ctx.createGain();
    vibG.gain.value = 3.5;
    vib.connect(vibG).connect(voice.frequency);
    const f1 = ctx.createBiquadFilter();
    f1.type = 'lowpass';
    f1.frequency.value = 520;
    f1.Q.value = 3;
    const f2 = ctx.createBiquadFilter();
    f2.type = 'peaking';
    f2.frequency.value = 260;
    f2.gain.value = 9;
    const env = ctx.createGain();
    env.gain.value = 0;
    voice.connect(f1).connect(f2).connect(env).connect(hp);
    // hiss and crackle
    const hiss = this.loopSource(this.white);
    const hissF = ctx.createBiquadFilter();
    hissF.type = 'bandpass';
    hissF.frequency.value = 3000;
    hissF.Q.value = 0.5;
    const hissG = ctx.createGain();
    hissG.gain.value = 0.05;
    hiss.connect(hissF).connect(hissG).connect(out);
    voice.start();
    vib.start();
    // an old lullaby, in a minor key; beats of 0.55 s
    const melody: [number, number][] = [
      [64, 1], [64, 0.5], [67, 0.5], [64, 1], [62, 1], [60, 1.5], [62, 0.5], [64, 2], [0, 0.6],
      [64, 1], [67, 1], [69, 1], [67, 0.5], [64, 0.5], [62, 1.5], [60, 0.5], [62, 2], [0, 0.6],
      [60, 1], [64, 1], [62, 1], [59, 1], [57, 3], [0, 1.6],
    ];
    const beat = 0.58;
    let t = ctx.currentTime + 0.4;
    const total = melody.reduce((a, [, d]) => a + d, 0) * beat;
    const schedule = (start: number) => {
      let tt = start;
      for (const [n, d] of melody) {
        const len = d * beat;
        if (n > 0) {
          const f = 440 * Math.pow(2, (n - 69 - 12) / 12) * 2;
          voice.frequency.setTargetAtTime(f, tt, 0.04);
          env.gain.setTargetAtTime(0.5, tt, 0.06);
          env.gain.setTargetAtTime(0.0, tt + len * 0.9, 0.08);
        }
        tt += len;
      }
      // signal dropouts
      for (let i = 0; i < 4; i++) {
        const dt = start + Math.random() * total;
        drop.gain.setValueAtTime(1, dt);
        drop.gain.linearRampToValueAtTime(0.1, dt + 0.05);
        drop.gain.linearRampToValueAtTime(1, dt + 0.25 + Math.random() * 0.3);
      }
    };
    schedule(t);
    t += total;
    let next = t;
    const timer = window.setInterval(() => {
      if (ctx.currentTime > next - 2) {
        schedule(next);
        next += total;
      }
    }, 500);
    this.signal = {
      stop: () => {
        window.clearInterval(timer);
        const now = ctx.currentTime;
        out.gain.setTargetAtTime(0, now, 0.15);
        setTimeout(() => {
          voice.stop();
          vib.stop();
          hiss.stop();
          out.disconnect();
        }, 800);
      },
    };
  }

  stopSignal(): void {
    this.signal?.stop();
    this.signal = null;
  }

  // --------------------------------------------------------------- per frame

  update(dt: number): void {
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    if (this.musicOn) {
      this.musicTimer -= dt;
      if (this.musicTimer <= 0) {
        this.playChord();
        this.musicTimer = 8;
      }
      const { gain } = this.spatial(this.musicPos);
      this.musicGain.gain.setTargetAtTime(Math.min(1, gain * 1.8) * 0.9, t, 0.3);
    }
    for (const l of this.loops.values()) {
      const { gain } = this.spatial(l.pos);
      l.gain.gain.setTargetAtTime(gain, t, 0.2);
    }
  }
}
