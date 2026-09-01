const BASE = 'assets/';

/**
 * Loads every image and JSON file a scene needs before anything renders, so
 * the game never draws a half-decoded frame. Results are cached by path, which
 * makes re-entering a scene free.
 */
export class Assets {
  constructor(base = BASE) {
    this.base = base;
    this.images = new Map();
    this.json = new Map();
    this.onProgress = null;
  }

  url(path) {
    return /^(https?:|\/|\.)/.test(path) ? path : this.base + path;
  }

  image(path) {
    if (this.images.has(path)) return this.images.get(path);
    throw new Error(`Image not loaded: ${path} -- add it to the manifest`);
  }

  data(path) {
    if (this.json.has(path)) return this.json.get(path);
    throw new Error(`JSON not loaded: ${path} -- add it to the manifest`);
  }

  has(path) {
    return this.images.has(path) || this.json.has(path);
  }

  loadImage(path) {
    if (this.images.has(path)) return Promise.resolve(this.images.get(path));
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        this.images.set(path, img);
        resolve(img);
      };
      img.onerror = () => reject(new Error(`Failed to load image: ${this.url(path)}`));
      img.src = this.url(path);
    });
  }

  async loadJSON(path) {
    if (this.json.has(path)) return this.json.get(path);
    const res = await fetch(this.url(path));
    if (!res.ok) throw new Error(`Failed to load JSON: ${this.url(path)} (${res.status})`);
    const value = await res.json();
    this.json.set(path, value);
    return value;
  }

  /**
   * @param {{images?: string[], json?: string[]}} manifest
   * Loads in parallel and reports progress as a 0..1 fraction.
   */
  async load(manifest) {
    const images = manifest.images || [];
    const json = manifest.json || [];
    const total = images.length + json.length;
    let done = 0;

    const tick = () => {
      done++;
      if (this.onProgress) this.onProgress(total ? done / total : 1, done, total);
    };

    await Promise.all([
      ...images.map((p) => this.loadImage(p).then((v) => { tick(); return v; })),
      ...json.map((p) => this.loadJSON(p).then((v) => { tick(); return v; })),
    ]);
  }
}
