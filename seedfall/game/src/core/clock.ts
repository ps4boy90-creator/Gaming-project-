/** Ship time. Day 2,214 of transit; 1 real minute = 15 ship minutes. */
export class ShipClock {
  minutes: number;
  rate = 0.25; // ship minutes per real second

  constructor(start = 2214 * 1440 + 6 * 60 + 40) {
    this.minutes = start;
  }

  update(dt: number): void {
    this.minutes += dt * this.rate;
  }

  get day(): number {
    return Math.floor(this.minutes / 1440);
  }

  get hour(): number {
    return (this.minutes % 1440) / 60;
  }

  /** 0 = day shift lighting, 1 = full night shift. Smooth ramps at dusk/dawn. */
  nightFactor(): number {
    const h = this.hour;
    const ramp = (a: number, b: number, x: number) => Math.min(1, Math.max(0, (x - a) / (b - a)));
    if (h >= 12) return ramp(20, 21.5, h);
    return 1 - ramp(5, 6.5, h);
  }

  format(): string {
    const h = Math.floor(this.hour);
    const m = Math.floor(this.minutes % 60);
    return `DAY ${this.day.toLocaleString('en-US')} · ${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
  }

  /** Advance to 06:30 of the next morning (at least six hours). */
  sleepUntilMorning(): number {
    const before = this.minutes;
    let target = this.day * 1440 + 6.5 * 60;
    while (target - this.minutes < 360) target += 1440;
    this.minutes = target;
    return (this.minutes - before) / 60;
  }
}
