import { makeBody, boxOf, moveAndCollide, applyGravity } from './physics.js';
import { Animator } from '../gfx/anim.js';
import { damp } from '../core/rng.js';

export const WALK_SPEED = 46;
export const RUN_SPEED = 82;
export const CROUCH_SPEED = 24;
export const CLIMB_SPEED = 40;
export const JUMP_VELOCITY = -260;

const COYOTE_TIME = 0.10;   // grace after walking off an edge
const JUMP_BUFFER = 0.12;   // grace for pressing jump just before landing

/**
 * The protagonist. Deliberately grounded: he walks, he does not vault around.
 * Jumping exists for scenes that need it but is off unless the scene opts in,
 * because a scientist bouncing through a corridor undercuts the tone.
 */
export class Player {
  constructor(sprite, x, y) {
    // The collision box is narrower than the sprite: the lab coat flares out,
    // and colliding on its silhouette would leave him wedged in doorways.
    this.body = makeBody(x, y, 16, 46);
    this.sprite = sprite;
    this.anim = new Animator(sprite);
    this.anim.play('idle');
    this.facing = 1;
    this.state = 'idle';
    this.allowJump = false;
    this.frozen = false;
    this.speedScale = 1;
    this._coyote = 0;
    this._jumpBuffer = 0;
    this._footClock = 0;
    this.onFootstep = null;
  }

  get x() { return this.body.x; }
  get y() { return this.body.y; }
  get box() { return boxOf(this.body); }

  /** Where an interaction prompt should hover, and roughly where his eyes are. */
  get head() { return { x: this.body.x, y: this.body.y - this.body.h - 6 }; }

  setPosition(x, y) {
    this.body.x = x;
    this.body.y = y;
    this.body.vx = 0;
    this.body.vy = 0;
  }

  update(dt, input, world) {
    const body = this.body;

    if (this.frozen) {
      body.vx = 0;
      applyGravity(body, dt);
      moveAndCollide(body, world, dt);
      this._setState(body.onGround ? 'idle' : 'fall');
      this.anim.update(dt);
      return;
    }

    const onLadder = world.anyOverlap(this.box, 'ladder');
    body.onLadder = onLadder;

    const moveX = input.axis('left', 'right');
    if (moveX !== 0) this.facing = moveX;

    // ---- climbing
    if (onLadder && (input.held('up') || input.held('down') || body.climbing)) {
      const moveY = input.axis('up', 'down');
      body.climbing = true;
      body.vy = moveY * CLIMB_SPEED;
      body.vx = moveX * CROUCH_SPEED;
      moveAndCollide(body, world, dt);
      if (!world.anyOverlap(this.box, 'ladder') || body.onGround && moveY > 0) {
        body.climbing = false;
      }
      this._setState(moveY !== 0 ? 'climb' : 'climb_idle');
      this.anim.update(dt);
      return;
    }
    body.climbing = false;

    // ---- grounded movement
    const crouching = input.held('crouch') && body.onGround;
    const running = input.held('run') && !crouching;
    const speed = (crouching ? CROUCH_SPEED : running ? RUN_SPEED : WALK_SPEED) * this.speedScale;

    // Ease into and out of the target speed so starting and stopping have
    // weight instead of snapping.
    const target = moveX * speed;
    body.vx = damp(body.vx, target, body.onGround ? 16 : 6, dt);
    if (Math.abs(body.vx) < 1 && moveX === 0) body.vx = 0;

    // ---- jumping
    this._coyote = body.onGround ? COYOTE_TIME : Math.max(0, this._coyote - dt);
    this._jumpBuffer = input.justPressed('jump') ? JUMP_BUFFER : Math.max(0, this._jumpBuffer - dt);
    if (this.allowJump && this._jumpBuffer > 0 && this._coyote > 0 && !crouching) {
      body.vy = JUMP_VELOCITY;
      this._jumpBuffer = 0;
      this._coyote = 0;
    }
    // Releasing early cuts the rise, giving a variable-height jump.
    if (this.allowJump && input.justReleased('jump') && body.vy < 0) body.vy *= 0.45;

    applyGravity(body, dt);
    const hit = moveAndCollide(body, world, dt);

    // ---- state and footsteps
    let state;
    if (!body.onGround) state = body.vy < 0 ? 'jump' : 'fall';
    else if (crouching) state = Math.abs(body.vx) > 4 ? 'crouch_walk' : 'crouch';
    else if (Math.abs(body.vx) > 4) state = running ? 'run' : 'walk';
    else state = 'idle';
    this._setState(state);

    const moving = body.onGround && Math.abs(body.vx) > 6;
    if (moving) {
      this._footClock += Math.abs(body.vx) * dt;
      const stride = crouching ? 34 : running ? 26 : 22;
      if (this._footClock >= stride) {
        this._footClock = 0;
        if (this.onFootstep) this.onFootstep(running ? 'run' : 'walk');
      }
    } else {
      this._footClock = 0;
    }
    if (hit.landed && this.onFootstep) this.onFootstep('land');

    this.anim.update(dt);
  }

  /** Map a movement state onto whichever clip the sprite actually provides. */
  _setState(state) {
    this.state = state;
    const preferred = {
      idle: ['idle'],
      walk: ['walk', 'idle'],
      run: ['run', 'walk', 'idle'],
      crouch: ['crouch', 'idle'],
      crouch_walk: ['crouch_walk', 'crouch', 'walk', 'idle'],
      jump: ['jump', 'idle'],
      fall: ['fall', 'jump', 'idle'],
      climb: ['climb', 'idle_back', 'idle'],
      climb_idle: ['climb_idle', 'climb', 'idle_back', 'idle'],
    }[state] || ['idle'];

    for (const name of preferred) {
      if (this.sprite.clip(name)) {
        this.anim.play(name);
        return;
      }
    }
  }

  draw(ctx, camera) {
    const off = this.anim.offset(this.facing);

    // A contact shadow is what actually seats a sprite in a painted room --
    // without one he reads as a cut-out laid over the artwork. It shrinks and
    // fades as he leaves the ground so a step down still feels connected.
    const airborne = this.body.onGround ? 0 : Math.min(1, Math.abs(this.body.vy) / 260);
    const sx = this.body.x - camera.drawX;
    const sy = this.body.y - camera.drawY;
    ctx.save();
    ctx.globalAlpha = 0.34 * (1 - airborne * 0.7);
    ctx.fillStyle = '#000';
    ctx.beginPath();
    ctx.ellipse(sx, sy - 1, 11 * (1 - airborne * 0.35), 3.2, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    this.sprite.draw(
      ctx,
      this.anim.frameName,
      this.body.x - camera.drawX,
      this.body.y - camera.drawY,
      { flip: this.facing < 0, offsetX: off.x, offsetY: off.y },
    );
  }
}
