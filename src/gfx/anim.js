/**
 * Plays a named clip from a Sprite and reports the current frame.
 *
 * Clips may carry `bob` (a per-frame vertical offset) and `lean` (a per-frame
 * horizontal offset in the facing direction). Those exist so a single static
 * frame can be given a sense of motion while real hand-drawn walk cycles are
 * still outstanding -- once a clip has genuine frames, simply omit them.
 */
export class Animator {
  constructor(sprite) {
    this.sprite = sprite;
    this.clipName = null;
    this.clip = null;
    this.index = 0;
    this.time = 0;
    this.finished = false;
    this.onEvent = null;
  }

  play(name, { restart = false } = {}) {
    if (this.clipName === name && !restart) return;
    const clip = this.sprite.clip(name);
    if (!clip) throw new Error(`Unknown clip "${name}"`);
    this.clipName = name;
    this.clip = clip;
    this.index = 0;
    this.time = 0;
    this.finished = false;
  }

  update(dt) {
    if (!this.clip || this.finished) return;
    const { frames, fps = 8, loop = true } = this.clip;
    if (frames.length <= 1 && !this.clip.bob) return;

    this.time += dt;
    const step = 1 / fps;
    while (this.time >= step) {
      this.time -= step;
      const next = this.index + 1;
      // bob/lean cycles can be longer than the frame list, so advance over
      // whichever is longer and let both wrap independently.
      const length = Math.max(frames.length, this.clip.bob ? this.clip.bob.length : 0);
      if (next >= length) {
        if (loop) {
          this.index = 0;
        } else {
          this.index = length - 1;
          this.finished = true;
          break;
        }
      } else {
        this.index = next;
      }
      const event = this.clip.events && this.clip.events[String(this.index)];
      if (event && this.onEvent) this.onEvent(event);
    }
  }

  get frameName() {
    if (!this.clip) return null;
    const { frames } = this.clip;
    return frames[this.index % frames.length];
  }

  /** Extra draw offset for the current frame, in pixels. */
  offset(facing = 1) {
    if (!this.clip) return { x: 0, y: 0 };
    const bob = this.clip.bob;
    const y = bob ? bob[this.index % bob.length] : 0;
    // Lean forward on the rise of the bob, which reads as pushing off a step.
    const lean = this.clip.lean || 0;
    const x = lean && y < 0 ? facing * lean : 0;
    return { x, y };
  }
}
