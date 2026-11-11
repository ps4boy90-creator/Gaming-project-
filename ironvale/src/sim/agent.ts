import type { StaffRole } from '../data/defs';
import type { WorldObject } from '../world/world';

export type AgentKind = 'prisoner' | 'staff' | 'visitor';
export type Role = StaffRole | 'riot';
export type AnimPose = 'stand' | 'walk' | 'run' | 'sit' | 'lie' | 'work' | 'fight' | 'exercise' | 'down' | 'cuffed';

export interface Look {
  torso: number;
  legs: number;
  skin: number;
  hair: number;
  /** 0 none, 1 guard cap, 2 chef hat, 3 hard hat, 4 riot helmet */
  hat: number;
  bald: boolean;
}

export interface Step {
  t: 'walk' | 'do' | 'follow';
  /** walk: destination tile */
  tile?: number;
  run?: boolean;
  /** do: duration in sim minutes (default: until `until` returns true) */
  dur?: number;
  pose?: AnimPose;
  yaw?: number;
  /** exact position / height to hold while doing */
  px?: number;
  pz?: number;
  y?: number;
  tick?: (dtMin: number) => void;
  until?: () => boolean;
  done?: () => void;
  icon?: string | null;
  /** follow: target agent and stop distance */
  target?: Agent;
  range?: number;
  /** follow gives up when this returns true */
  abort?: () => boolean;
  /** cannot be interrupted by regime changes */
  hold?: boolean;
  status?: string;
}

export type PMode =
  | 'intake' | 'normal' | 'fight' | 'solitary' | 'punished' | 'escaping' | 'infirm' | 'down' | 'cuffed' | 'released' | 'riot';

export interface PrisonerData {
  sec: number;
  crime: string;
  age: number;
  sentence: number;
  served: number;
  needs: Float32Array;
  anger: number;
  health: number;
  temper: number;
  bedId: number;
  bedSlot: number;
  contraband: '' | 'weapon' | 'tools' | 'drugs' | 'phone';
  dig: number;
  mode: PMode;
  modeUntil: number;
  processed: boolean;
  ate: boolean;
  showered: boolean;
  edu: number;
  reform: number;
  misconduct: number;
  /** minute stamp of the last misbehaviour roll */
  nextRoll: number;
  escortedBy: number;
}

export interface StaffData {
  role: Role;
  energy: number;
  /** guards: tile index of the room they are stationed in, or -1 to patrol */
  station: number;
  mode: 'idle' | 'respond' | 'break' | 'job' | 'escort' | 'leave';
  targetId: number;
  health: number;
  jobId: number;
  wage: number;
}

let NEXT_ID = 1;
export function resetAgentIds(v = 1) {
  NEXT_ID = v;
}
export function peekAgentId() {
  return NEXT_ID;
}

export class Agent {
  id = NEXT_ID++;
  name = '';
  x = 0;
  z = 0;
  y = 0;
  yaw = 0;
  pose: AnimPose = 'stand';
  anim = Math.random() * 10;
  icon: string | null = null;
  hidden = false;
  /** tiles per sim minute */
  speed = 1.75;
  pass = 0;
  steps: Step[] = [];
  stepT = 0;
  stepInit = false;
  path: number[] | null = null;
  pathI = 0;
  repathT = 0;
  resv: number[] = [];
  status = '';
  thinkT = 0;
  offX = (Math.random() - 0.5) * 0.44;
  offZ = (Math.random() - 0.5) * 0.44;
  noPath = 0;
  dead = false;
  /** generic small state counter (visitors) */
  stage = 0;
  p?: PrisonerData;
  s?: StaffData;
  /** visitor: the prisoner being visited */
  visitFor = 0;

  constructor(public kind: AgentKind, public look: Look) {}

  get tx() {
    return Math.floor(this.x);
  }
  get tz() {
    return Math.floor(this.z);
  }
  distTo(o: { x: number; z: number }) {
    return Math.hypot(this.x - o.x, this.z - o.z);
  }
  get busy() {
    return this.steps.length > 0 && !!this.steps[0].hold;
  }
}

export type { WorldObject };
