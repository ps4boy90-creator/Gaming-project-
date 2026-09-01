import { makeRng, clamp, lerp } from '../core/rng.js';

/**
 * Everything the game makes is played through a 1950s tabletop radio.
 *
 * The scheduled imperfections all take an optional explicit time, so the whole
 * chain can be rendered through an OfflineAudioContext for inspection --
 * `tools/render_audio.cjs` uses that to produce listenable captures.
 *
 * The whole mix -- score, room tone, footsteps, doors -- runs through this one
 * chain before it reaches the speakers, so the game does not sound like a game
 * with a filter on it; it sounds like a transmission. The contrast that makes
 * that work is the *absence* of bass and air, not the hiss on top: a period set
 * reproduces roughly 300 Hz to 3.5 kHz and nothing outside it.
 *
 *   input ─→ station ─→ band limit ─→ cabinet ─→ valve ─→ wow ─→ wet ─┐
 *         └─────────────────────── dry ─────────────────────────────┬─┴─→ output
 *   hiss · mains hum · crackle · whistle ────────────────→ bits ────┘
 *
 * `amount` crossfades wet against dry and scales the added noise, so 0 is a
 * true bypass and the game sounds modern and full-range. That matters: band
 * limiting an entire game is a mood for most players and an accessibility
 * problem for some.
 */

const HP_HZ = 300;          // nothing below this survives a paper cone
const LP_CLEAR = 3500;      // a well tuned station
const LP_DEGRADED = 2600;   // one drifting off
const HUM_HZ = 120;         // rectifier ripple, not the 60 Hz mains itself

/** Soft asymmetric saturation. The asymmetry is what makes it read as valve. */
function valveCurve(drive = 0.7, n = 2048) {
  const curve = new Float32Array(n);
  const k = 1 + drive * 2;
  const norm = Math.tanh(k);
  for (let i = 0; i < n; i++) {
    const x = (i * 2) / n - 1;
    // The negative half clips harder, which adds even harmonics.
    const bias = x >= 0 ? 1 : 1.35;
    curve[i] = Math.tanh(x * bias * k) / norm;
  }
  return curve;
}

export class Radio {
  constructor(ctx, noiseBuffer) {
    this.ctx = ctx;
    this.noise = noiseBuffer;
    this.rng = makeRng(19540614);
    this.amount = 1;
    this.tension = 0;
    this.sources = [];

    this.input = ctx.createGain();

    // Everything -- wet, dry and the radio's own noise -- meets at `sum`, and
    // a limiter sits between that and the output. The valve stage bounds the
    // wet path, but the convolution reverb in the score has real gain and the
    // hiss, hum and crackle are summed after the valve, so the total can and
    // did exceed full scale. A limiter here means no scene can overload the
    // output no matter what it stacks up.
    this.sum = ctx.createGain();
    this.sum.gain.value = 0.8;

    this.limiter = ctx.createDynamicsCompressor();
    this.limiter.threshold.value = -6;
    this.limiter.knee.value = 3;
    this.limiter.ratio.value = 12;
    this.limiter.attack.value = 0.003;
    this.limiter.release.value = 0.25;

    this.output = ctx.createGain();
    this.sum.connect(this.limiter).connect(this.output);

    // --- dry path, for the bypass end of the crossfade
    this.dry = ctx.createGain();
    this.dry.gain.value = 0;
    this.input.connect(this.dry).connect(this.sum);

    // --- station strength: the whole wet path breathes as if the aerial moves
    this.station = ctx.createGain();
    this.station.gain.value = 1;
    this.input.connect(this.station);

    // --- band limit. Two stages each, because one 12 dB/oct slope still lets
    // through enough bottom end to spoil the illusion.
    const hp1 = ctx.createBiquadFilter();
    const hp2 = ctx.createBiquadFilter();
    hp1.type = hp2.type = 'highpass';
    hp1.frequency.value = hp2.frequency.value = HP_HZ;
    hp1.Q.value = hp2.Q.value = 0.6;

    this.lp1 = ctx.createBiquadFilter();
    this.lp2 = ctx.createBiquadFilter();
    this.lp1.type = this.lp2.type = 'lowpass';
    this.lp1.frequency.value = this.lp2.frequency.value = LP_CLEAR;
    this.lp1.Q.value = this.lp2.Q.value = 0.7;

    // --- cabinet: a small paper cone in a wooden box has a voice
    const cone = ctx.createBiquadFilter();
    cone.type = 'peaking';
    cone.frequency.value = 1500;
    cone.Q.value = 1.1;
    cone.gain.value = 6.5;

    const body = ctx.createBiquadFilter();
    body.type = 'peaking';
    body.frequency.value = 700;
    body.Q.value = 0.9;
    body.gain.value = 3.0;

    const valve = ctx.createWaveShaper();
    valve.curve = valveCurve(0.65);
    valve.oversample = '2x';

    // A second band limit after the valve stage. Saturation fed a band-limited
    // signal generates intermodulation products, and the difference tones land
    // *below* the passband -- measurably, about 12 dB of bass the first
    // high-pass had already removed. A real set band-limits after its output
    // stage too, not least because the speaker cannot reproduce it either.
    const postHp = ctx.createBiquadFilter();
    postHp.type = 'highpass';
    postHp.frequency.value = HP_HZ;
    postHp.Q.value = 0.6;
    this.postLp = ctx.createBiquadFilter();
    this.postLp.type = 'lowpass';
    this.postLp.frequency.value = LP_CLEAR;
    this.postLp.Q.value = 0.7;

    // --- wow and flutter. Modulating a very short delay is how you get real
    // pitch instability; nothing else makes it sound mechanical.
    this.wow = ctx.createDelay(0.05);
    this.wow.delayTime.value = 0.004;

    this.wet = ctx.createGain();
    this.wet.gain.value = 1;

    this.station.connect(hp1);
    hp1.connect(hp2);
    hp2.connect(this.lp1);
    this.lp1.connect(this.lp2);
    this.lp2.connect(cone);
    cone.connect(body);
    body.connect(valve);
    valve.connect(postHp);
    postHp.connect(this.postLp);
    this.postLp.connect(this.wow);
    this.wow.connect(this.wet);
    this.wet.connect(this.sum);

    // --- the radio's own noise, added after the filter because it belongs to
    // the set rather than to the signal.
    this.bits = ctx.createGain();
    this.bits.gain.value = 1;
    this.bits.connect(this.sum);

    this._buildWowLfo();
    this._buildStationDrift();
    this._buildHiss();
    this._buildHum();

    this._crackleIn = 3;
    this._dropoutIn = 12;
    this._whistleIn = 40;

    this.setAmount(1);
  }

  _osc(type, freq) {
    const o = this.ctx.createOscillator();
    o.type = type;
    o.frequency.value = freq;
    o.start();
    this.sources.push(o);
    return o;
  }

  _buildWowLfo() {
    const lfo = this._osc('sine', 0.7);
    this.wowDepth = this.ctx.createGain();
    this.wowDepth.gain.value = 0.0005;
    lfo.connect(this.wowDepth).connect(this.wow.delayTime);
    // A second, faster and shallower wobble stops the drift sounding periodic.
    const flutter = this._osc('sine', 5.3);
    const fd = this.ctx.createGain();
    fd.gain.value = 0.00012;
    flutter.connect(fd).connect(this.wow.delayTime);
    this.wowLfo = lfo;
  }

  _buildStationDrift() {
    const lfo = this._osc('sine', 0.06);
    const depth = this.ctx.createGain();
    depth.gain.value = 0.10;
    lfo.connect(depth).connect(this.station.gain);
    const lfo2 = this._osc('sine', 0.017);
    const depth2 = this.ctx.createGain();
    depth2.gain.value = 0.06;
    lfo2.connect(depth2).connect(this.station.gain);
  }

  _buildHiss() {
    const src = this.ctx.createBufferSource();
    src.buffer = this.noise;
    src.loop = true;
    // Brown noise is too dark on its own for hiss; lift the top of the band.
    const tilt = this.ctx.createBiquadFilter();
    tilt.type = 'highpass';
    tilt.frequency.value = 900;
    const cap = this.ctx.createBiquadFilter();
    cap.type = 'lowpass';
    cap.frequency.value = 3200;
    this.hissGain = this.ctx.createGain();
    this.hissGain.gain.value = 0.045;
    src.connect(tilt).connect(cap).connect(this.hissGain).connect(this.bits);
    src.start();
    this.sources.push(src);
  }

  _buildHum() {
    this.humGain = this.ctx.createGain();
    this.humGain.gain.value = 0.005;
    this.humGain.connect(this.bits);
    // 120 Hz and its harmonics. Injected here, past the high-pass, on purpose:
    // filtering out the hum would remove the thing that says "valve set".
    for (const [hz, level] of [[HUM_HZ, 1], [HUM_HZ * 2, 0.4], [HUM_HZ * 3, 0.18]]) {
      const o = this._osc('sine', hz);
      const g = this.ctx.createGain();
      g.gain.value = level;
      o.connect(g).connect(this.humGain);
    }
  }

  /** 0 bypasses the radio entirely; 1 is the full set. */
  setAmount(a) {
    this.amount = clamp(a, 0, 1);
    const now = this.ctx.currentTime;
    this.wet.gain.setTargetAtTime(this.amount, now, 0.08);
    this.dry.gain.setTargetAtTime(1 - this.amount, now, 0.08);
    this.bits.gain.setTargetAtTime(this.amount, now, 0.08);
  }

  /**
   * 0 is a clean station, 1 is one barely holding. Driven by how much of the
   * mystery the player has worked out, so the reception degrades as they close
   * in without any single step being noticeable.
   */
  setTension(t) {
    this.tension = clamp(t, 0, 1);
    const now = this.ctx.currentTime;
    const lp = lerp(LP_CLEAR, LP_DEGRADED, this.tension);
    this.lp1.frequency.setTargetAtTime(lp, now, 2.5);
    this.lp2.frequency.setTargetAtTime(lp, now, 2.5);
    this.postLp.frequency.setTargetAtTime(lp, now, 2.5);
    this.hissGain.gain.setTargetAtTime(lerp(0.045, 0.115, this.tension), now, 2.5);
    this.humGain.gain.setTargetAtTime(lerp(0.005, 0.010, this.tension), now, 2.5);
    this.wowDepth.gain.setTargetAtTime(lerp(0.0005, 0.0016, this.tension), now, 2.5);
    this.wowLfo.frequency.setTargetAtTime(lerp(0.7, 0.4, this.tension), now, 2.5);
  }

  /** Scheduled imperfections. Called from the game's fixed update. */
  update(dt) {
    if (this.amount <= 0.01) return;

    this._crackleIn -= dt;
    if (this._crackleIn <= 0) {
      this._crackle();
      this._crackleIn = lerp(9, 2.5, this.tension) * (0.4 + this.rng() * 1.2);
    }

    this._dropoutIn -= dt;
    if (this._dropoutIn <= 0) {
      this._dropout();
      this._dropoutIn = lerp(26, 8, this.tension) * (0.5 + this.rng());
    }

    if (this.tension > 0.45) {
      this._whistleIn -= dt;
      if (this._whistleIn <= 0) {
        this._whistle();
        this._whistleIn = lerp(50, 18, this.tension) * (0.6 + this.rng());
      }
    }
  }

  _crackle(when) {
    const t = when === undefined ? this.ctx.currentTime : when;
    const count = 1 + Math.floor(this.rng() * 3);
    for (let i = 0; i < count; i++) {
      const at = t + i * (0.01 + this.rng() * 0.05);
      const dur = 0.006 + this.rng() * 0.02;
      const src = this.ctx.createBufferSource();
      src.buffer = this.noise;
      src.playbackRate.value = 2 + this.rng() * 2;
      const bp = this.ctx.createBiquadFilter();
      bp.type = 'bandpass';
      bp.frequency.value = 1200 + this.rng() * 1800;
      bp.Q.value = 0.8;
      const g = this.ctx.createGain();
      const peak = (0.05 + this.rng() * 0.09) * lerp(0.6, 1.4, this.tension);
      g.gain.setValueAtTime(0.0001, at);
      g.gain.exponentialRampToValueAtTime(peak, at + 0.002);
      g.gain.exponentialRampToValueAtTime(0.0001, at + dur);
      src.connect(bp).connect(g).connect(this.bits);
      src.start(at);
      src.stop(at + dur + 0.02);
    }
  }

  _dropout(when) {
    const t = when === undefined ? this.ctx.currentTime : when;
    const depth = lerp(0.55, 0.12, this.tension);
    this.station.gain.setTargetAtTime(depth, t, 0.02);
    this.station.gain.setTargetAtTime(1, t + 0.06 + this.rng() * 0.16, 0.08);
  }

  /** A heterodyne whistle sliding through the top of the band. */
  _whistle(when) {
    const t = when === undefined ? this.ctx.currentTime : when;
    const dur = 1.2 + this.rng() * 1.6;
    const o = this.ctx.createOscillator();
    o.type = 'sine';
    const from = 2100 + this.rng() * 500;
    o.frequency.setValueAtTime(from, t);
    o.frequency.linearRampToValueAtTime(from + (this.rng() * 900 - 300), t + dur);
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.012 * lerp(0.5, 1.5, this.tension), t + dur * 0.4);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g).connect(this.bits);
    o.start(t);
    o.stop(t + dur + 0.05);
  }

  dispose() {
    for (const s of this.sources) {
      try { s.stop(); } catch (e) { /* already stopped */ }
    }
    this.sources.length = 0;
  }
}
