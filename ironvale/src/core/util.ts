// Small shared helpers.

export class RNG {
  private s: number;
  constructor(seed = 1234567) {
    this.s = seed >>> 0 || 1;
  }
  /** float in [0,1) */
  next(): number {
    let t = (this.s += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }
  range(a: number, b: number) {
    return a + (b - a) * this.next();
  }
  int(a: number, b: number) {
    return Math.floor(this.range(a, b + 1));
  }
  pick<T>(arr: readonly T[]): T {
    return arr[Math.floor(this.next() * arr.length)];
  }
  chance(p: number) {
    return this.next() < p;
  }
}

export const rng = new RNG((Date.now() ^ 0x9e3779b9) >>> 0);

export const clamp = (v: number, a: number, b: number) => (v < a ? a : v > b ? b : v);
export const clamp01 = (v: number) => (v < 0 ? 0 : v > 1 ? 1 : v);
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
export const smooth = (t: number) => t * t * (3 - 2 * t);

export function fmtMoney(n: number): string {
  const neg = n < 0;
  const v = Math.abs(Math.round(n));
  return (neg ? '-$' : '$') + v.toLocaleString('en-US');
}

export function fmtTime(minutes: number): string {
  const m = Math.floor(minutes) % 1440;
  const h = Math.floor(m / 60);
  const mm = m % 60;
  return (h < 10 ? '0' : '') + h + ':' + (mm < 10 ? '0' : '') + mm;
}

type Handler = (payload?: any) => void;
/** Minimal event bus. */
export class Bus {
  private map = new Map<string, Handler[]>();
  on(ev: string, fn: Handler) {
    let l = this.map.get(ev);
    if (!l) this.map.set(ev, (l = []));
    l.push(fn);
  }
  emit(ev: string, payload?: any) {
    const l = this.map.get(ev);
    if (l) for (const fn of l) fn(payload);
  }
}

export function b64encode(bytes: Uint8Array): string {
  let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(s);
}
export function b64decode(str: string): Uint8Array {
  const s = atob(str);
  const out = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i);
  return out;
}
