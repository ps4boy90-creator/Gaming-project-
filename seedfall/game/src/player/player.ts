import * as THREE from 'three';
import { Input } from '../core/input';
import { CollisionWorld } from '../world/collision';
import { Seat } from '../world/ship/kit';
import { bus } from '../core/events';

export type PlayerMode = 'walk' | 'seated' | 'lying' | 'locked';

const STAND = 1.78;
const CROUCH = 1.15;
const RADIUS = 0.3;
const STEP = 0.36;
const GRAVITY = 9.81;

/** First-person body: walking, crouching, leaning, sitting and lying down. */
export class Player {
  pos = new THREE.Vector3();
  vel = new THREE.Vector3();
  yaw = 0;
  pitch = 0;
  roll = 0;
  height = STAND;
  crouching = false;
  onGround = true;
  mode: PlayerMode = 'walk';
  seat: Seat | null = null;
  sensitivity = 1;
  headBob = true;
  eye = new THREE.Vector3();
  private eyeY = 0;
  private lean = 0;
  private bob = 0;
  private bobAmt = 0;
  private stride = 0;
  private seatBlend = 0;
  private seatFrom = new THREE.Vector3();
  private seatYawBase = 0;
  private lookYaw = 0;
  private flashOn = false;
  readonly flashlight: THREE.SpotLight;

  constructor(public camera: THREE.PerspectiveCamera, private world: CollisionWorld) {
    camera.rotation.order = 'YXZ';
    this.flashlight = new THREE.SpotLight(0xfff2e0, 0, 28, 0.42, 0.55, 2);
    this.flashlight.position.set(0.18, -0.2, 0);
    camera.add(this.flashlight);
    camera.add(this.flashlight.target);
    this.flashlight.target.position.set(0, -0.2, -5);
  }

  teleport(x: number, y: number, z: number, yaw?: number, pitch = 0): void {
    this.pos.set(x, y, z);
    this.vel.set(0, 0, 0);
    if (yaw !== undefined) this.yaw = yaw;
    this.pitch = pitch;
    this.eyeY = y + this.height - 0.12;
    this.mode = 'walk';
    this.seat = null;
    this.seatBlend = 0;
  }

  toggleFlashlight(): boolean {
    this.flashOn = !this.flashOn;
    this.flashlight.intensity = this.flashOn ? 40 : 0;
    return this.flashOn;
  }

  sitAt(seat: Seat): void {
    this.seat = seat;
    this.mode = seat.kind === 'lie' ? 'lying' : 'seated';
    this.seatFrom.copy(this.eye);
    this.seatBlend = 0;
    this.seatYawBase = seat.yaw;
    this.lookYaw = 0;
    this.yaw = seat.yaw;
    this.pitch = seat.kind === 'lie' ? 0.35 : -0.05;
    this.vel.set(0, 0, 0);
    bus.emit('sfx', { kind: 'sit' });
  }

  standUp(): void {
    if (!this.seat) return;
    const s = this.seat;
    this.pos.set(s.exitX, s.y - (s.kind === 'lie' ? 0.55 : 0.5) + 0.0, s.exitZ);
    // drop to the floor below the exit point
    const g = this.world.groundAt(this.pos.x, this.pos.z, RADIUS * 0.8, s.y + 0.5);
    if (g > -Infinity) this.pos.y = g;
    this.world.pushOut(this.pos, RADIUS, this.pos.y + STEP, this.pos.y + STAND);
    this.yaw = this.seatYawBase + this.lookYaw;
    this.mode = 'walk';
    this.seat = null;
    this.eyeY = this.eye.y;
    bus.emit('sfx', { kind: 'stand' });
  }

  /** Move the body (and the camera) vertically, e.g. a lift ride between decks. */
  shiftY(dy: number): void {
    this.pos.y += dy;
    this.eyeY += dy;
    this.eye.y += dy;
  }

  update(dt: number, input: Input, canLook: boolean, canMove: boolean, useStands = true): void {
    const look = input.takeLook();
    const k = 0.0022 * this.sensitivity;
    const controlsEnabled = canMove;
    if (canLook && this.mode !== 'locked') {
      if (this.mode === 'walk') {
        this.yaw -= look.dx * k;
      } else {
        this.lookYaw = THREE.MathUtils.clamp(this.lookYaw - look.dx * k, -1.9, 1.9);
        this.yaw = this.seatYawBase + this.lookYaw;
      }
      const maxPitch = this.mode === 'lying' ? 1.3 : 1.45;
      this.pitch = THREE.MathUtils.clamp(this.pitch - look.dy * k, -1.45, maxPitch);
    }

    if (this.mode === 'walk') this.walk(dt, input, controlsEnabled);
    else if (this.mode === 'seated' || this.mode === 'lying') this.sitting(dt, input, controlsEnabled, useStands);

    this.camera.position.copy(this.eye);
    this.camera.rotation.set(this.pitch, this.yaw, this.roll);
  }

  private sitting(dt: number, input: Input, enabled: boolean, useStands: boolean): void {
    const s = this.seat!;
    this.seatBlend = Math.min(1, this.seatBlend + dt * 2.5);
    const t = this.seatBlend * this.seatBlend * (3 - 2 * this.seatBlend);
    const target = new THREE.Vector3(s.x, s.y + (s.kind === 'lie' ? 0.28 : 0.74), s.z);
    if (s.kind === 'sit') {
      // sit slightly back in the seat
      target.x += Math.sin(s.yaw) * 0.08;
      target.z += Math.cos(s.yaw) * 0.08;
    }
    this.eye.lerpVectors(this.seatFrom, target, t);
    this.roll *= 0.9;
    if (enabled && this.seatBlend > 0.6) {
      const ax = input.axis();
      if (input.pressed('jump') || (useStands && input.pressed('use')) || ax.y > 0.6 || ax.y < -0.6) this.standUp();
    }
  }

  private walk(dt: number, input: Input, enabled: boolean): void {
    const ax = enabled ? input.axis() : { x: 0, y: 0 };
    const wantCrouch = enabled && input.held('crouch');
    if (wantCrouch) this.crouching = true;
    else if (this.crouching) {
      const ceil = this.world.ceilingAt(this.pos.x, this.pos.z, RADIUS, this.pos.y + CROUCH);
      if (ceil - this.pos.y >= STAND + 0.02) this.crouching = false;
    }
    this.height += ((this.crouching ? CROUCH : STAND) - this.height) * Math.min(1, dt * 10);

    const sprint = enabled && input.held('sprint') && !this.crouching && ax.y > 0.3;
    const speed = this.crouching ? 1.35 : sprint ? 4.6 : 2.7;
    const fx = -Math.sin(this.yaw);
    const fz = -Math.cos(this.yaw);
    const rx = Math.cos(this.yaw);
    const rz = -Math.sin(this.yaw);
    const wx = (fx * ax.y + rx * ax.x) * speed;
    const wz = (fz * ax.y + rz * ax.x) * speed;
    const accel = this.onGround ? 11 : 2;
    this.vel.x += (wx - this.vel.x) * Math.min(1, dt * accel);
    this.vel.z += (wz - this.vel.z) * Math.min(1, dt * accel);

    if (enabled && this.onGround && input.pressed('jump') && !this.crouching) {
      this.vel.y = 3.4;
      this.onGround = false;
      bus.emit('sfx', { kind: 'jump' });
    }
    this.vel.y -= GRAVITY * dt;

    // horizontal move with sub-steps, then resolve
    const steps = Math.max(1, Math.ceil((Math.hypot(this.vel.x, this.vel.z) * dt) / 0.12));
    for (let i = 0; i < steps; i++) {
      this.pos.x += (this.vel.x * dt) / steps;
      this.pos.z += (this.vel.z * dt) / steps;
      this.world.pushOut(this.pos, RADIUS, this.pos.y + STEP, this.pos.y + this.height);
    }
    // vertical
    const prevY = this.pos.y;
    this.pos.y += this.vel.y * dt;
    const ground = this.world.groundAt(this.pos.x, this.pos.z, RADIUS * 0.75, Math.max(prevY, this.pos.y) + STEP);
    const wasGround = this.onGround;
    if (this.pos.y <= ground + 0.001) {
      if (!wasGround && this.vel.y < -2.5) bus.emit('sfx', { kind: 'land', strength: -this.vel.y });
      this.pos.y = ground;
      this.vel.y = 0;
      this.onGround = true;
    } else if (this.pos.y - ground < 0.06 && this.vel.y <= 0) {
      this.pos.y = ground;
      this.vel.y = 0;
      this.onGround = true;
    } else this.onGround = false;
    const ceil = this.world.ceilingAt(this.pos.x, this.pos.z, RADIUS * 0.8, prevY + 0.5);
    if (this.pos.y + this.height > ceil) {
      this.pos.y = Math.min(this.pos.y, ceil - this.height);
      if (this.vel.y > 0) this.vel.y = 0;
    }
    if (ground === -Infinity && this.pos.y < -50) bus.emit('fell');

    // lean
    const leanT = enabled ? (input.held('leanL') ? -1 : 0) + (input.held('leanR') ? 1 : 0) : 0;
    this.lean += (leanT - this.lean) * Math.min(1, dt * 8);
    this.roll = -this.lean * 0.11;

    // head bob + footsteps
    const hs = Math.hypot(this.vel.x, this.vel.z);
    const moving = this.onGround && hs > 0.4;
    this.bobAmt += ((moving ? Math.min(1, hs / 4.6) : 0) - this.bobAmt) * Math.min(1, dt * 6);
    if (moving) {
      this.bob += dt * (hs * 2.15);
      this.stride += hs * dt;
      const strideLen = sprint ? 1.05 : this.crouching ? 0.55 : 0.78;
      if (this.stride >= strideLen) {
        this.stride = 0;
        bus.emit('sfx', { kind: 'step', speed: hs, crouch: this.crouching, x: this.pos.x, y: this.pos.y, z: this.pos.z });
      }
    }
    const targetEye = this.pos.y + this.height - 0.12;
    this.eyeY += (targetEye - this.eyeY) * Math.min(1, dt * 14);
    if (Math.abs(targetEye - this.eyeY) > 1.2) this.eyeY = targetEye;
    const bobY = this.headBob ? Math.sin(this.bob * 2) * 0.032 * this.bobAmt : 0;
    const bobX = this.headBob ? Math.cos(this.bob) * 0.022 * this.bobAmt : 0;
    const lean = this.lean * 0.32;
    this.eye.set(this.pos.x + rx * (lean + bobX), this.eyeY + bobY - Math.abs(this.lean) * 0.04, this.pos.z + rz * (lean + bobX));
  }

  /** Forward look direction. */
  forward(out = new THREE.Vector3()): THREE.Vector3 {
    return out.set(0, 0, -1).applyEuler(this.camera.rotation);
  }
}
