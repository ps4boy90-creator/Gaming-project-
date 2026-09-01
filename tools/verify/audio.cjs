const { chromium } = require('playwright-core');
/**
 * Verifies the score and the 1950s radio by measuring the signal.
 *
 * Asserting that audio nodes exist proves nothing about sound. These checks tap
 * an AnalyserNode onto the output and look at the actual spectrum: that there
 * is energy at all, that it is band-limited where a period set band-limits it,
 * that bypassing the radio restores both ends, and -- the one most likely to
 * catch a real regression -- that no ambience preset or effect has been
 * filtered into silence.
 *
 *   python3 -m http.server 8000 &
 *   npm install playwright-core
 *   node tools/verify/audio.cjs
 */
const CHROME = process.env.CHROME || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const BASE = process.env.BASE || 'http://127.0.0.1:8000';

const fail = [];
const check = (name, cond, extra = '') => {
  console.log(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? '  ' + extra : ''}`);
  if (!cond) fail.push(name);
};

(async () => {
  const browser = await chromium.launch({
    executablePath: CHROME,
    args: ['--no-sandbox', '--autoplay-policy=no-user-gesture-required',
      '--mute-audio=false', '--use-fake-device-for-media-stream'],
  });
  const page = await browser.newPage({ viewport: { width: 1152, height: 648 } });
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push('PAGEERROR: ' + e.message));

  const G = (fn, arg) => page.evaluate(fn, arg);
  const settle = (ms = 300) => page.waitForTimeout(ms);

  await page.goto(`${BASE}/index.html`);
  await G(() => localStorage.clear());
  await page.reload();
  await page.waitForFunction(() => window.game && ['playing', 'cutscene', 'error'].includes(window.game.state),
    null, { timeout: 15000 });

  /** A new game now opens on the prologue narration; skip past it. */
  const skipPrologue = async () => {
    for (let i = 0; i < 14; i++) {
      if (await page.evaluate(() => window.game.state) !== 'cutscene') return;
      await page.keyboard.press('Escape');
      await page.waitForTimeout(260);
    }
  };
  check('context is not created before a gesture', await G(() => window.game.audio.ctx === null));

  await skipPrologue();


  // A real key event is the gesture that unlocks the context.
  await page.keyboard.press('KeyE');
  await settle(600);
  check('context runs after a gesture', await G(() => !!window.game.audio.ctx));
  check('music graph is built', await G(() => !!window.game.music && !!window.game.music.voice));

  // ---- install a spectrum tap on the final output
  await G(() => {
    const a = window.game.audio;
    const an = a.ctx.createAnalyser();
    an.fftSize = 4096;
    an.smoothingTimeConstant = 0.2;
    a.master.connect(an);
    window.__an = an;
    window.__bins = new Float32Array(an.frequencyBinCount);
    window.__time = new Float32Array(an.fftSize);
    // Average magnitude, in dB, across a frequency window.
    window.__band = (lo, hi) => {
      window.__an.getFloatFrequencyData(window.__bins);
      const nyq = window.game.audio.ctx.sampleRate / 2;
      const per = nyq / window.__bins.length;
      let sum = 0; let n = 0;
      for (let i = 0; i < window.__bins.length; i++) {
        const f = i * per;
        if (f >= lo && f <= hi) { sum += window.__bins[i]; n++; }
      }
      return n ? sum / n : -200;
    };
    window.__rms = () => {
      window.__an.getFloatTimeDomainData(window.__time);
      let s = 0;
      for (let i = 0; i < window.__time.length; i++) s += window.__time[i] * window.__time[i];
      return Math.sqrt(s / window.__time.length);
    };
  });

  // Give the score a moment, and strike notes so there is definitely signal.
  await G(() => { for (let i = 0; i < 3; i++) window.game.music.strike(i * 3, 2, 1); });
  await settle(700);

  const rmsOn = await G(() => window.__rms());
  check('it actually makes sound', rmsOn > 0.0005, `rms ${rmsOn.toExponential(2)}`);

  // Level, not just spectrum. The reverb has real gain and the radio's hiss and
  // crackle are summed after the valve stage, so the total can overload the
  // output -- it did, at 1.35 full scale, until a limiter went in. A clean FFT
  // says nothing about this.
  const peak = await G(async () => {
    let p = 0;
    for (let i = 0; i < 90; i++) {
      window.game.music.strike(i % 7, 2, 1);
      window.game.audio.play('save');
      await new Promise((r) => setTimeout(r, 22));
      window.__an.getFloatTimeDomainData(window.__time);
      for (let k = 0; k < window.__time.length; k++) {
        const a = Math.abs(window.__time[k]);
        if (a > p) p = a;
      }
    }
    return p;
  });
  check('output never clips, even under load', peak < 0.99, `peak ${peak.toFixed(3)}`);

  // ---- the decisive test: is it band-limited like a period set?
  //
  // Measured with a controlled broadband probe injected at preMaster rather
  // than with whatever the score happens to be playing. The score is sines and
  // sawtooths under 700 Hz and simply has no energy above 6 kHz to lose, so
  // measuring it would say nothing about the filter. White noise has energy
  // everywhere, which makes the shape of the chain unambiguous.
  //
  // The low window stops at 100 Hz on purpose: the 120 Hz mains hum is injected
  // *after* the filter by design, and including it would measure the artifact
  // rather than the high-pass.
  const probe = async (radioAmount) => G(async (amount) => {
    const a = window.game.audio;
    a.setRadioAmount(amount);
    a.setAmbience('none');
    window.game.music.setPreset('silent');
    await new Promise((r) => setTimeout(r, 700));

    const buf = a.ctx.createBuffer(1, a.ctx.sampleRate * 2, a.ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    const src = a.ctx.createBufferSource();
    src.buffer = buf;
    src.loop = true;
    const g = a.ctx.createGain();
    g.gain.value = 0.25;
    src.connect(g).connect(a.preMaster);
    src.start();

    await new Promise((r) => setTimeout(r, 900));
    const out = {
      low: window.__band(40, 100),
      mid: window.__band(600, 2500),
      high: window.__band(8000, 16000),
    };
    src.stop();
    g.disconnect();
    return out;
  }, radioAmount);

  const on = await probe(1);
  check('mid band passes', on.mid > -95, `${on.mid.toFixed(1)} dB`);
  check('bass is gone (radio on)', on.low < on.mid - 24,
    `low ${on.low.toFixed(1)} vs mid ${on.mid.toFixed(1)} dB`);
  check('air is gone (radio on)', on.high < on.mid - 24,
    `high ${on.high.toFixed(1)} vs mid ${on.mid.toFixed(1)} dB`);

  const off = await probe(0);
  check('bypass restores the bass', off.low > on.low + 15,
    `${on.low.toFixed(1)} -> ${off.low.toFixed(1)} dB`);
  check('bypass restores the air', off.high > on.high + 15,
    `${on.high.toFixed(1)} -> ${off.high.toFixed(1)} dB`);
  check('bypass is roughly flat', Math.abs(off.low - off.high) < 14,
    `low ${off.low.toFixed(1)} high ${off.high.toFixed(1)} dB`);

  await G(() => window.game.audio.setRadioAmount(1));
  await settle(400);

  // ---- nothing was filtered into silence
  const floor = await G(async () => {
    const out = {};
    const quiet = () => {
      window.game.audio.setAmbience('none');
      return new Promise((r) => setTimeout(r, 500));
    };
    for (const name of ['night_cabin', 'forest_night', 'facility_hum', 'basement']) {
      await quiet();
      window.game.music.setPreset('silent');
      window.game.audio.setAmbience(name);
      await new Promise((r) => setTimeout(r, 1400));
      out[name] = window.__rms();
    }
    return out;
  });
  for (const [name, rms] of Object.entries(floor)) {
    check(`ambience "${name}" survives the radio`, rms > 0.0002, `rms ${rms.toExponential(2)}`);
  }

  const effects = await G(async () => {
    const out = {};
    window.game.audio.setAmbience('none');
    window.game.music.setPreset('silent');
    await new Promise((r) => setTimeout(r, 700));
    for (const name of ['walk', 'land', 'door', 'metal', 'locked', 'paper', 'pickup', 'save', 'blip']) {
      let peak = 0;
      window.game.audio.play(name);
      for (let i = 0; i < 24; i++) {
        await new Promise((r) => setTimeout(r, 12));
        peak = Math.max(peak, window.__rms());
      }
      out[name] = peak;
      await new Promise((r) => setTimeout(r, 120));
    }
    return out;
  });
  const dead = Object.entries(effects).filter(([, v]) => v < 0.0002).map(([k]) => k);
  check('no effect was filtered into silence', dead.length === 0,
    dead.length ? `silent: ${dead.join(', ')}` : Object.entries(effects)
      .map(([k, v]) => `${k}:${v.toFixed(4)}`).join(' '));

  // ---- tension narrows the band and sags the score
  await G(() => { window.game.music.setPreset('deep'); window.game.audio.setAmbience('basement'); });
  await settle(600);
  const calm = await G(() => ({
    lp: window.game.audio.radio.lp1.frequency.value,
    hiss: window.game.audio.radio.hissGain.gain.value,
    tension: window.game.audio.radio.tension,
  }));
  await G(() => {
    for (const d of window.game.deductions.all) {
      window.game.journal.addDeduction({ id: d.id, title: d.title, pages: d.note });
    }
    window.game.pushTension();
  });
  await settle(3000);
  const tense = await G(() => ({
    lp: window.game.audio.radio.lp1.frequency.value,
    hiss: window.game.audio.radio.hissGain.gain.value,
    tension: window.game.audio.radio.tension,
  }));
  check('tension reaches 1 with every realization', tense.tension === 1,
    `${calm.tension} -> ${tense.tension}`);
  check('the station gets duller', tense.lp < calm.lp - 200,
    `${Math.round(calm.lp)} -> ${Math.round(tense.lp)} Hz`);
  check('hiss rises', tense.hiss > calm.hiss + 0.02,
    `${calm.hiss.toFixed(3)} -> ${tense.hiss.toFixed(3)}`);
  check('the score is in Phrygian under tension',
    await G(() => { const s = new Set(); for (let i = 0; i < 60; i++) s.add(window.game.music._pickDegree()); return s.has(1); }));

  // ---- no node leak across scene changes
  const before = await G(() => window.game.music.voice.sources.length);
  await G(async () => {
    const ids = ['cabin_bedroom', 'station_lobby', 'laboratory', 'sublevel_3', 'canteen'];
    for (let i = 0; i < 10; i++) {
      await window.game.travel(ids[i % ids.length], undefined, { instant: true });
    }
  });
  await settle(800);
  const after = await G(() => window.game.music.voice.sources.length);
  check('no voice leak across ten scene changes', after === before, `${before} -> ${after}`);

  // ---- options persist
  await page.keyboard.press('KeyO');
  await settle(250);
  check('options overlay opens', await G(() => window.game.options.open));
  await page.keyboard.press('ArrowDown');
  await page.keyboard.press('ArrowLeft');
  await page.keyboard.press('ArrowLeft');
  await settle(250);
  const musicVol = await G(() => window.game.options.values.music);
  check('music volume changed', musicVol < 0.8, `music ${musicVol}`);
  await page.screenshot({ path: require('path').join(__dirname, 'shots', '40-options.png') });
  await page.keyboard.press('Escape');
  await settle(250);
  await page.reload();
  await page.waitForFunction(() => window.game && ['playing', 'cutscene'].includes(window.game.state), null, { timeout: 15000 });
  await skipPrologue();
  await settle(400);
  check('options survive a reload', await G(() => window.game.options.values.music) === musicVol,
    `${musicVol} -> ${await G(() => window.game.options.values.music)}`);

  check('no console errors', errors.length === 0, errors.slice(0, 3).join(' | '));
  await settle(1200);
  check('frame rate healthy with the score running',
    await G(() => window.game.loop.fps) >= 50, `${await G(() => window.game.loop.fps)} fps`);

  await browser.close();
  console.log(fail.length ? `\n${fail.length} FAILED: ${fail.join(', ')}` : '\nIt sounds like a radio.');
  process.exit(fail.length ? 1 : 0);
})();
