// Static game data: floors, walls, doors, objects, rooms, staff, needs.

export const MAP_W = 84;
export const MAP_H = 64;

// ---------------------------------------------------------------- needs
export const NEEDS = ['hunger', 'sleep', 'bladder', 'hygiene', 'recreation', 'exercise', 'family', 'safety', 'freedom'] as const;
export type NeedId = (typeof NEEDS)[number];
export const NEED_LABEL: Record<NeedId, string> = {
  hunger: 'Food',
  sleep: 'Sleep',
  bladder: 'Toilet',
  hygiene: 'Hygiene',
  recreation: 'Recreation',
  exercise: 'Exercise',
  family: 'Family',
  safety: 'Safety',
  freedom: 'Freedom',
};
/** How strongly an unmet need feeds anger. */
export const NEED_WEIGHT: Record<NeedId, number> = {
  hunger: 1.6,
  sleep: 1.3,
  bladder: 1.0,
  hygiene: 0.8,
  recreation: 0.7,
  exercise: 0.5,
  family: 0.6,
  safety: 1.2,
  freedom: 0.8,
};

// ---------------------------------------------------------------- floors
export interface FloorDef {
  id: number;
  key: string;
  name: string;
  cost: number;
  outdoor: boolean;
  desc: string;
}
export const FLOORS: FloorDef[] = [
  { id: 0, key: 'grass', name: 'Grass', cost: 0, outdoor: true, desc: 'Bare ground. Removes any floor.' },
  { id: 1, key: 'dirt', name: 'Dirt', cost: 2, outdoor: true, desc: 'Packed earth for yards and paths.' },
  { id: 2, key: 'concrete', name: 'Concrete', cost: 5, outdoor: false, desc: 'Cheap, hard-wearing poured slab.' },
  { id: 3, key: 'polished', name: 'Sealed Concrete', cost: 8, outdoor: false, desc: 'Dark sealed floor for cell blocks.' },
  { id: 4, key: 'tile', name: 'White Tile', cost: 10, outdoor: false, desc: 'Easy to clean. Showers and infirmary.' },
  { id: 5, key: 'checker', name: 'Checker Tile', cost: 10, outdoor: false, desc: 'Classic canteen and kitchen floor.' },
  { id: 6, key: 'wood', name: 'Wood', cost: 14, outdoor: false, desc: 'Warm planks for offices and chapels.' },
  { id: 7, key: 'carpet', name: 'Carpet', cost: 16, outdoor: false, desc: 'Soft office carpet.' },
  { id: 8, key: 'asphalt', name: 'Asphalt', cost: 6, outdoor: true, desc: 'Roads, parking and service yards.' },
  { id: 9, key: 'paving', name: 'Paving', cost: 8, outdoor: true, desc: 'Stone paths between buildings.' },
  { id: 10, key: 'court', name: 'Sports Court', cost: 12, outdoor: true, desc: 'Rubberised court for the yard.' },
];

// ---------------------------------------------------------------- walls
export const WALL_NONE = 0;
export const WALL_CONCRETE = 1;
export const WALL_BRICK = 2;
export const WALL_PERIMETER = 3;
export const WALL_FENCE = 4;
export const WALL_WINDOW = 5;
export interface WallDef {
  id: number;
  key: string;
  name: string;
  cost: number;
  height: number;
  thick: number;
  desc: string;
}
export const WALLS: WallDef[] = [
  { id: 0, key: 'none', name: 'None', cost: 0, height: 0, thick: 0, desc: '' },
  { id: 1, key: 'concrete', name: 'Concrete Wall', cost: 30, height: 1.3, thick: 0.26, desc: 'Standard interior and exterior wall.' },
  { id: 2, key: 'brick', name: 'Brick Wall', cost: 35, height: 1.3, thick: 0.26, desc: 'Red brick. Same strength, more character.' },
  { id: 3, key: 'perimeter', name: 'Perimeter Wall', cost: 80, height: 2.0, thick: 0.42, desc: 'Tall reinforced wall topped with razor wire.' },
  { id: 4, key: 'fence', name: 'Chain-link Fence', cost: 12, height: 1.5, thick: 0.06, desc: 'Cheap see-through barrier with barbed wire.' },
  { id: 5, key: 'window', name: 'Barred Window', cost: 45, height: 1.3, thick: 0.26, desc: 'Wall section with a barred window.' },
];

// ---------------------------------------------------------------- doors
export const DOOR_NONE = 0;
export const DOOR_STANDARD = 1;
export const DOOR_CELL = 2;
export const DOOR_STAFF = 3;
export const DOOR_GATE = 4;
export interface DoorDef {
  id: number;
  key: string;
  name: string;
  cost: number;
  staffOnly: boolean;
  desc: string;
}
export const DOORS: DoorDef[] = [
  { id: 0, key: 'none', name: 'None', cost: 0, staffOnly: false, desc: '' },
  { id: 1, key: 'door', name: 'Door', cost: 60, staffOnly: false, desc: 'Ordinary door. Anyone may pass.' },
  { id: 2, key: 'cell', name: 'Cell Door', cost: 120, staffOnly: false, desc: 'Barred sliding door. Locks during lockup and sleep.' },
  { id: 3, key: 'staff', name: 'Staff Door', cost: 150, staffOnly: true, desc: 'Reinforced. Only staff hold the key.' },
  { id: 4, key: 'gate', name: 'Security Gate', cost: 220, staffOnly: true, desc: 'Barred gate for fences and perimeter walls. Staff only.' },
];

// ---------------------------------------------------------------- objects
export type ObjCat = 'housing' | 'hygiene' | 'food' | 'leisure' | 'medical' | 'work' | 'security' | 'office' | 'outdoor';
export const OBJ_CATS: { id: ObjCat; name: string }[] = [
  { id: 'housing', name: 'Housing' },
  { id: 'hygiene', name: 'Hygiene' },
  { id: 'food', name: 'Food' },
  { id: 'leisure', name: 'Leisure' },
  { id: 'medical', name: 'Medical' },
  { id: 'work', name: 'Work & Study' },
  { id: 'security', name: 'Security' },
  { id: 'office', name: 'Office' },
  { id: 'outdoor', name: 'Outdoor' },
];
export type Pose = 'stand' | 'sit' | 'lie' | 'work' | 'exercise';
export interface ObjectDef {
  id: string;
  name: string;
  cat: ObjCat;
  /** footprint in tiles at rotation 0: w along X, d along Z. Front faces +Z. */
  w: number;
  d: number;
  cost: number;
  /** adds a pathing penalty so people walk around it */
  solid: boolean;
  /** how many people can use it at once */
  slots: number;
  pose?: Pose;
  /** height of the surface a user sits / lies on */
  seatH?: number;
  /** only makes sense outside */
  outdoor?: boolean;
  /** emits light at night: radius in tiles */
  light?: number;
  desc: string;
}

const O = (
  id: string,
  name: string,
  cat: ObjCat,
  w: number,
  d: number,
  cost: number,
  solid: boolean,
  slots: number,
  desc: string,
  extra: Partial<ObjectDef> = {},
): ObjectDef => ({ id, name, cat, w, d, cost, solid, slots, desc, ...extra });

export const OBJECTS: ObjectDef[] = [
  // housing
  O('bed', 'Bed', 'housing', 1, 2, 80, true, 1, 'A steel-framed prison bed. One per inmate.', { pose: 'lie', seatH: 0.34 }),
  O('bunk', 'Bunk Bed', 'housing', 1, 2, 140, true, 2, 'Sleeps two. Cheaper per head, less comfortable.', { pose: 'lie', seatH: 0.34 }),
  O('toilet', 'Toilet', 'housing', 1, 1, 60, true, 1, 'Stainless steel toilet and basin unit.', { pose: 'sit', seatH: 0.24 }),
  O('cell_desk', 'Cell Desk', 'housing', 1, 1, 45, true, 0, 'Small desk and stool. Makes a cell more bearable.'),
  O('locker', 'Locker', 'housing', 1, 1, 40, true, 0, 'Personal storage for an inmate or guard.'),
  // hygiene
  O('shower', 'Shower Head', 'hygiene', 1, 1, 70, false, 1, 'A shower with floor drain.', { pose: 'stand' }),
  O('sink', 'Sink', 'hygiene', 1, 1, 50, true, 0, 'Wash basin.'),
  O('laundry_machine', 'Washing Machine', 'hygiene', 1, 1, 300, true, 1, 'Industrial washer. Inmates can work here.', { pose: 'work' }),
  O('laundry_basket', 'Laundry Cart', 'hygiene', 1, 1, 30, true, 0, 'Wheeled cart of prison uniforms.'),
  // food
  O('cooker', 'Cooker', 'food', 1, 1, 400, true, 1, 'Industrial range. Cooks prepare meals here.', { pose: 'work' }),
  O('fridge', 'Fridge', 'food', 1, 1, 250, true, 0, 'Tall refrigerator for ingredients.'),
  O('kitchen_counter', 'Prep Counter', 'food', 1, 1, 90, true, 1, 'Stainless prep surface. Inmates can work here.', { pose: 'work' }),
  O('serving_counter', 'Serving Counter', 'food', 2, 1, 200, true, 3, 'Hot food is collected here at meal times.', { pose: 'stand' }),
  O('table', 'Canteen Table', 'food', 2, 1, 60, true, 0, 'A sturdy bolted-down table.'),
  O('bench', 'Bench', 'food', 2, 1, 40, false, 2, 'Seats two.', { pose: 'sit', seatH: 0.26 }),
  O('bin', 'Bin', 'food', 1, 1, 15, true, 0, 'Keeps the place tidy.'),
  // leisure
  O('tv', 'Television', 'leisure', 1, 1, 220, true, 4, 'Wall of daytime television. Watched from in front.', { pose: 'stand' }),
  O('sofa', 'Sofa', 'leisure', 2, 1, 150, false, 2, 'Worn but comfortable.', { pose: 'sit', seatH: 0.24 }),
  O('pool_table', 'Pool Table', 'leisure', 2, 1, 350, true, 2, 'The most popular thing in the common room.', { pose: 'stand' }),
  O('bookshelf', 'Bookshelf', 'leisure', 1, 1, 120, true, 1, 'Books for the library.', { pose: 'stand' }),
  O('chair', 'Chair', 'leisure', 1, 1, 25, false, 1, 'Plain plastic chair.', { pose: 'sit', seatH: 0.26 }),
  O('phone', 'Phone Booth', 'leisure', 1, 1, 180, true, 1, 'Lets inmates call home.', { pose: 'stand' }),
  O('weight_bench', 'Weight Bench', 'leisure', 1, 2, 160, true, 1, 'Bench press for the yard or gym.', { pose: 'exercise', seatH: 0.3 }),
  O('punching_bag', 'Punching Bag', 'leisure', 1, 1, 90, true, 1, 'A healthy outlet for aggression.', { pose: 'exercise' }),
  O('basketball_hoop', 'Basketball Hoop', 'leisure', 1, 1, 140, true, 4, 'Half-court hoop. Played in front.', { pose: 'exercise', outdoor: true }),
  O('pew', 'Pew', 'leisure', 2, 1, 70, false, 2, 'Chapel seating.', { pose: 'sit', seatH: 0.26 }),
  O('altar', 'Altar', 'leisure', 2, 1, 200, true, 0, 'Multi-faith altar for the chapel.'),
  O('visit_table', 'Visiting Table', 'leisure', 1, 3, 130, true, 1, 'Table with a stool either side. Inmate one side, visitor the other.', { pose: 'sit', seatH: 0.26 }),
  // medical
  O('medical_bed', 'Medical Bed', 'medical', 1, 2, 350, true, 1, 'Hospital bed for sick and injured inmates.', { pose: 'lie', seatH: 0.38 }),
  O('medicine_cabinet', 'Medicine Cabinet', 'medical', 1, 1, 180, true, 0, 'Locked cabinet of supplies.'),
  // work & study
  O('workshop_saw', 'Table Saw', 'work', 2, 1, 500, true, 1, 'Workshop machine. Inmates earn the prison money.', { pose: 'work' }),
  O('workshop_press', 'Plate Press', 'work', 1, 1, 450, true, 1, 'Stamps licence plates.', { pose: 'work' }),
  O('school_desk', 'School Desk', 'work', 1, 1, 60, false, 1, 'Desk and chair for a classroom.', { pose: 'sit', seatH: 0.26 }),
  O('blackboard', 'Blackboard', 'work', 2, 1, 80, true, 0, 'Free-standing teaching board.'),
  O('crates', 'Supply Crates', 'work', 1, 1, 20, true, 0, 'Stacked supplies for the storeroom.'),
  O('shelving', 'Storage Shelves', 'work', 2, 1, 90, true, 0, 'Heavy-duty racking.'),
  // security
  O('cctv', 'CCTV Camera', 'security', 1, 1, 200, true, 0, 'Pole-mounted camera. Watches an 8-tile radius when a monitor is manned.'),
  O('cctv_monitor', 'CCTV Console', 'security', 2, 1, 600, true, 1, 'Bank of monitors. Needs a guard on duty.', { pose: 'sit', seatH: 0.26 }),
  O('metal_detector', 'Metal Detector', 'security', 1, 1, 350, false, 0, 'Walk-through arch. Flags weapons and tools.'),
  O('guard_tower', 'Guard Tower', 'security', 2, 2, 1500, true, 1, 'Armed overwatch. Stops escapes in a wide radius.', { pose: 'stand', outdoor: true, light: 7 }),
  O('weapon_rack', 'Weapon Rack', 'security', 1, 1, 400, true, 0, 'Batons, shields and tasers for the armoury.'),
  // office
  O('office_desk', 'Office Desk', 'office', 2, 2, 220, true, 1, 'Desk, computer and chair.', { pose: 'sit', seatH: 0.26 }),
  O('filing_cabinet', 'Filing Cabinet', 'office', 1, 1, 70, true, 0, 'Inmate records in triplicate.'),
  O('plant', 'Potted Plant', 'office', 1, 1, 35, true, 0, 'A touch of green.'),
  O('vending', 'Vending Machine', 'office', 1, 1, 260, true, 0, 'Snacks and coffee for the staff room.', { light: 2 }),
  // outdoor
  O('lamp_post', 'Floodlight', 'outdoor', 1, 1, 120, true, 0, 'Lights the grounds at night.', { outdoor: true, light: 6 }),
  O('outdoor_bench', 'Park Bench', 'outdoor', 2, 1, 55, false, 2, 'Somewhere to sit in the yard.', { pose: 'sit', seatH: 0.26, outdoor: true }),
  O('tree', 'Tree', 'outdoor', 1, 1, 60, true, 0, 'A leafy tree.', { outdoor: true }),
  O('bush', 'Shrub', 'outdoor', 1, 1, 20, true, 0, 'Low hedge shrub.', { outdoor: true }),
  O('flower_bed', 'Flower Bed', 'outdoor', 1, 1, 25, true, 0, 'Brightens up the entrance.', { outdoor: true }),
  O('flagpole', 'Flagpole', 'outdoor', 1, 1, 150, true, 0, 'Flies the state flag.', { outdoor: true }),
  O('dumpster', 'Dumpster', 'outdoor', 2, 1, 80, true, 0, 'Rubbish goes here.', { outdoor: true }),
];
export const OBJ: Record<string, ObjectDef> = Object.fromEntries(OBJECTS.map((o) => [o.id, o]));

// ---------------------------------------------------------------- rooms
export interface RoomDef {
  id: number;
  key: string;
  name: string;
  color: number;
  /** each entry is a list of alternatives, at least one of which must be present */
  needs: string[][];
  minTiles: number;
  /** must be sealed by walls and doors */
  enclosed: boolean;
  desc: string;
}
export const ROOMS: RoomDef[] = [
  { id: 0, key: 'none', name: 'None', color: 0x000000, needs: [], minTiles: 0, enclosed: false, desc: 'Clear room designation.' },
  { id: 1, key: 'cell', name: 'Cell', color: 0xe8843a, needs: [['bed', 'bunk'], ['toilet']], minTiles: 4, enclosed: true, desc: 'Houses inmates. Needs a bed and a toilet, sealed with a cell door.' },
  { id: 2, key: 'dorm', name: 'Dormitory', color: 0xd9a441, needs: [['bed', 'bunk'], ['toilet']], minTiles: 12, enclosed: true, desc: 'Shared housing. Capacity equals the number of bed spaces.' },
  { id: 3, key: 'holding', name: 'Holding Cell', color: 0xc9b458, needs: [['bench'], ['toilet']], minTiles: 9, enclosed: true, desc: 'Temporary housing for new arrivals without a cell.' },
  { id: 4, key: 'solitary', name: 'Solitary', color: 0x8e5bd0, needs: [], minTiles: 2, enclosed: true, desc: 'Punishment cell for inmates who misbehave.' },
  { id: 5, key: 'canteen', name: 'Canteen', color: 0x4fb0e0, needs: [['serving_counter'], ['bench', 'chair']], minTiles: 20, enclosed: false, desc: 'Where inmates eat. Needs a serving counter and seating.' },
  { id: 6, key: 'kitchen', name: 'Kitchen', color: 0x3fc7b8, needs: [['cooker'], ['fridge']], minTiles: 12, enclosed: false, desc: 'Cooks prepare meals here. Needs a cooker and a fridge.' },
  { id: 7, key: 'showers', name: 'Showers', color: 0x62c6f2, needs: [['shower']], minTiles: 4, enclosed: false, desc: 'Communal showers.' },
  { id: 8, key: 'yard', name: 'Yard', color: 0x67c35c, needs: [], minTiles: 25, enclosed: false, desc: 'Outdoor exercise area. Fence it in!' },
  { id: 9, key: 'common', name: 'Common Room', color: 0xf0c94a, needs: [['tv', 'pool_table', 'sofa']], minTiles: 12, enclosed: false, desc: 'Recreation: TV, pool, sofas and phones.' },
  { id: 10, key: 'infirmary', name: 'Infirmary', color: 0xf06a6a, needs: [['medical_bed']], minTiles: 12, enclosed: false, desc: 'Doctors treat injured and sick inmates.' },
  { id: 11, key: 'laundry', name: 'Laundry', color: 0x8fb8f5, needs: [['laundry_machine']], minTiles: 9, enclosed: false, desc: 'Keeps uniforms clean. Inmate workplace.' },
  { id: 12, key: 'workshop', name: 'Workshop', color: 0xb58a5a, needs: [['workshop_saw', 'workshop_press']], minTiles: 16, enclosed: false, desc: 'Inmates manufacture goods for income.' },
  { id: 13, key: 'classroom', name: 'Classroom', color: 0x58d68d, needs: [['school_desk'], ['blackboard']], minTiles: 12, enclosed: false, desc: 'Education programmes. Needs a teacher.' },
  { id: 14, key: 'library', name: 'Library', color: 0xa67c52, needs: [['bookshelf']], minTiles: 9, enclosed: false, desc: 'Quiet reading for inmates.' },
  { id: 15, key: 'chapel', name: 'Chapel', color: 0xe6d9a8, needs: [['pew'], ['altar']], minTiles: 12, enclosed: false, desc: 'Worship and reflection. Calms inmates when a chaplain is present.' },
  { id: 16, key: 'visitation', name: 'Visitation', color: 0xf58fc0, needs: [['visit_table']], minTiles: 12, enclosed: false, desc: 'Families visit inmates here.' },
  { id: 17, key: 'reception', name: 'Reception', color: 0x9ad0c2, needs: [['office_desk']], minTiles: 9, enclosed: false, desc: 'New arrivals are processed here.' },
  { id: 18, key: 'security', name: 'Security Office', color: 0x4a6fd8, needs: [['office_desk', 'cctv_monitor']], minTiles: 9, enclosed: false, desc: 'Guard base. CCTV consoles go here.' },
  { id: 19, key: 'warden', name: "Warden's Office", color: 0x9b6b3a, needs: [['office_desk']], minTiles: 9, enclosed: false, desc: 'The Warden runs the prison from here.' },
  { id: 20, key: 'staffroom', name: 'Staff Room', color: 0x6fa8a0, needs: [['sofa', 'chair', 'vending']], minTiles: 9, enclosed: false, desc: 'Staff rest here when tired.' },
  { id: 21, key: 'storage', name: 'Storage', color: 0x8d8d8d, needs: [], minTiles: 6, enclosed: false, desc: 'Supplies and deliveries. Workmen wait here.' },
  { id: 22, key: 'psych', name: "Psychologist's Office", color: 0xc48fe0, needs: [['office_desk'], ['sofa', 'chair']], minTiles: 9, enclosed: false, desc: 'Therapy sessions calm angry inmates.' },
  { id: 23, key: 'armoury', name: 'Armoury', color: 0x596275, needs: [['weapon_rack']], minTiles: 4, enclosed: true, desc: 'Equips guards. Makes them far better in a fight.' },
];
export const ROOM_BY_KEY: Record<string, RoomDef> = Object.fromEntries(ROOMS.map((r) => [r.key, r]));
export const R = {
  cell: 1, dorm: 2, holding: 3, solitary: 4, canteen: 5, kitchen: 6, showers: 7, yard: 8, common: 9, infirmary: 10,
  laundry: 11, workshop: 12, classroom: 13, library: 14, chapel: 15, visitation: 16, reception: 17, security: 18,
  warden: 19, staffroom: 20, storage: 21, psych: 22, armoury: 23,
} as const;

// ---------------------------------------------------------------- staff
export type StaffRole = 'warden' | 'guard' | 'doctor' | 'cook' | 'janitor' | 'workman' | 'teacher' | 'psych' | 'chaplain';
export interface StaffDef {
  role: StaffRole;
  name: string;
  hire: number;
  wage: number;
  max?: number;
  desc: string;
}
export const STAFF: StaffDef[] = [
  { role: 'warden', name: 'Warden', hire: 1000, wage: 250, max: 1, desc: 'Runs the prison. Boosts income and keeps inmates calmer.' },
  { role: 'guard', name: 'Guard', hire: 500, wage: 100, desc: 'Patrols, breaks up fights, escorts inmates and stops escapes.' },
  { role: 'workman', name: 'Workman', hire: 400, wage: 70, desc: 'Builds everything you plan.' },
  { role: 'cook', name: 'Cook', hire: 400, wage: 80, desc: 'Prepares meals in the kitchen.' },
  { role: 'janitor', name: 'Janitor', hire: 300, wage: 60, desc: 'Cleans dirty rooms.' },
  { role: 'doctor', name: 'Doctor', hire: 900, wage: 180, desc: 'Heals the injured in the infirmary.' },
  { role: 'teacher', name: 'Teacher', hire: 600, wage: 120, desc: 'Runs classes during work hours.' },
  { role: 'psych', name: 'Psychologist', hire: 800, wage: 160, desc: 'Therapy sessions reduce anger.' },
  { role: 'chaplain', name: 'Chaplain', hire: 500, wage: 90, desc: 'Leads services in the chapel.' },
];
export const STAFF_BY_ROLE: Record<StaffRole, StaffDef> = Object.fromEntries(STAFF.map((s) => [s.role, s])) as Record<StaffRole, StaffDef>;

// ---------------------------------------------------------------- regime
export const ACTS = ['sleep', 'lockup', 'shower', 'eat', 'yard', 'free', 'work'] as const;
export type Activity = (typeof ACTS)[number];
export const ACT_LABEL: Record<Activity, string> = {
  sleep: 'Sleep', lockup: 'Lockup', shower: 'Shower', eat: 'Eat', yard: 'Yard', free: 'Free Time', work: 'Work',
};
export const ACT_COLOR: Record<Activity, string> = {
  sleep: '#3b4a7a', lockup: '#7a4b4b', shower: '#3aa7d6', eat: '#e0a030', yard: '#56b24f', free: '#c9c04a', work: '#b0764a',
};
export const DEFAULT_REGIME: Activity[] = [
  'sleep', 'sleep', 'sleep', 'sleep', 'sleep', 'sleep', // 0-5
  'shower', 'eat', 'work', 'work', 'work', 'yard', // 6-11
  'eat', 'free', 'work', 'work', 'work', 'yard', // 12-17
  'eat', 'free', 'free', 'lockup', 'sleep', 'sleep', // 18-23
];

// ---------------------------------------------------------------- security levels
export const SEC_NAME = ['Minimum', 'Medium', 'Maximum'];
export const SEC_COLOR = [0x5aa9e6, 0xf08a24, 0xd43d3d];
export const SEC_GRANT = [110, 150, 210];
