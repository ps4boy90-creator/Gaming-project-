// edit.jsx — "The United States Military, By The Numbers" (60s motion presentation)
// Renders with higgsedit: `higgsedit build edit.jsx` then `higgsedit render proj --engine node`
const W = 1920, H = 1080;
const M = 140;

const BG    = "#05070C";
const INK   = "#EEF2F7";
const DIM   = "#78879A";
const ACC   = "#E5B23C";
const STEEL = "#3F6FA8";
const LINE  = "#16202D";

const MONO = "JetBrains Mono";
const SANS = "Inter";
const DISP = "Anton";

const LEAD = 1.2;          // cold open before the voice-over starts
const VO_DUR = 55.08;      // measured length of the Seed Audio 1.0 read
const ENDCARD = 3.5;
const TOTAL = LEAD + VO_DUR + ENDCARD;   // 59.79s

let icon; // injected by higgsedit at build time
const fit = (d, span) => Math.min(d, span * 0.92);

const inFade = (dur, at = 0) => ({
  property: "opacity",
  keyframes: [{ at, value: 0 }, { at: at + fit(0.3, dur), value: 1 }],
});

const rise = (dur, at = 0, dist = 34) => ({
  property: "offsetY",
  keyframes: [{ at, value: dist }, { at: at + fit(0.45, dur), value: 0, easing: "house" }],
});

const kicker = (label, dur) => (
  <text x={M} y={232} width={1000} fontFamily={MONO} fontSize={26} letterSpacing={7}
        color={ACC} animate={[inFade(dur), rise(dur, 0, 16)]}>
    {label}
  </text>
);

const bigNum = (value, dur, size = 210, color = INK) => (
  <text x={M} y={286} width={1000} fontFamily={DISP} fontSize={size} lineHeight={1.05}
        color={color}
        motion={{ by: "character", from: { y: 70, opacity: 0 }, overlap: 0.72,
                  duration: 0.5, easing: "house" }}>
    {value}
  </text>
);

const rule = (dur, y = 566, w = 880) => (
  <rect x={M} y={y} width={w} height={7} fill={ACC}
        mask={{ shape: "rectangle", x: 0, y: 0, width: w, height: 7 }}
        animate={[{ property: "maskWidth", from: 0, to: w, at: 0.34,
                   duration: fit(0.6, dur), easing: "house" }]} />
);

const caption = (txt, dur, y = 610, color = DIM, size = 33) => (
  <text x={M} y={y} width={900} fontFamily={SANS} fontSize={size} fontWeight={400}
        lineHeight={1.35} letterSpacing={0.4} color={color}
        animate={[inFade(dur, 0.3), rise(dur, 0.3, 22)]}>
    {txt}
  </text>
);

const RX = 1080, RW = 700;

const barRows = (rows, dur) => {
  const out = [];
  rows.forEach((r, i) => {
    const y = 300 + i * 132;
    const w = Math.max(24, Math.round(RW * r.frac));
    const d = 0.42 + i * 0.13;
    out.push(
      <text key={"l" + i} x={RX} y={y} width={RW - 200} fontFamily={MONO} fontSize={25}
            letterSpacing={3} color={DIM} animate={[inFade(dur, d)]}>{r.label}</text>,
      <text key={"v" + i} x={RX} y={y - 4} width={RW} align="right" fontFamily={DISP}
            fontSize={42} color={r.color || INK} animate={[inFade(dur, d)]}>{r.value}</text>,
      <rect key={"t" + i} x={RX} y={y + 52} width={RW} height={12} fill={LINE} radius={6}
            animate={[inFade(dur, d)]} />,
      <rect key={"b" + i} x={RX} y={y + 52} width={w} height={12} fill={r.color || ACC}
            mask={{ shape: "rectangle", x: 0, y: 0, width: w, height: 12 }}
            animate={[{ property: "maskWidth", from: 0, to: w, at: d + 0.1,
                       duration: fit(0.75, dur), easing: "house" }]} />,
    );
  });
  return out;
};

const chipRows = (rows, dur, top = 306) => {
  const out = [];
  rows.forEach((r, i) => {
    const y = top + i * 92;
    const d = 0.42 + i * 0.12;
    out.push(
      <rect key={"m" + i} x={RX} y={y + 8} width={9} height={34} fill={ACC}
            animate={[inFade(dur, d)]} />,
      <text key={"t" + i} x={RX + 34} y={y} width={RW - 34} fontFamily={SANS} fontSize={34}
            fontWeight={600} color={INK}
            animate={[inFade(dur, d), rise(dur, d, 18)]}>{r}</text>,
    );
  });
  return out;
};

const beat = (dur, children) => (
  <group name="beat" animate={[{ property: "opacity",
      keyframes: [{ at: 0, value: 0 }, { at: fit(0.26, dur), value: 1 }] }]}>
    {children}
  </group>
);

// Beat durations come from Whisper word timings on the voice-over.
const BEATS = [
  { id: "open", dur: 8.15, build: (d) => beat(d, [
      <text x={M} y={300} width={1200} fontFamily={MONO} fontSize={28} letterSpacing={9}
            color={ACC} animate={[inFade(d), rise(d, 0, 16)]}>U.S. ARMED FORCES // 2026</text>,
      <text x={M} y={356} width={1400} fontFamily={DISP} fontSize={158} lineHeight={1.02}
            color={INK}
            motion={{ by: "word", from: { y: 80, opacity: 0 }, overlap: 0.68,
                      duration: 0.55, easing: "house" }}>THE UNITED STATES</text>,
      <text x={M} y={520} width={1400} fontFamily={DISP} fontSize={158} lineHeight={1.02}
            color={ACC}
            motion={{ by: "character", from: { y: 80, opacity: 0 }, overlap: 0.78,
                      duration: 0.5, easing: "house" }}>MILITARY</text>,
      rule(d, 706, 980),
      <text x={M} y={748} width={1180} fontFamily={SANS} fontSize={34} lineHeight={1.35}
            color={DIM} animate={[inFade(d, 0.5), rise(d, 0.5, 22)]}>
        The most expensive and most technologically advanced fighting force ever assembled.
      </text>,
      icon("shield", { x: 1420, y: 330, size: 380, color: "#0F1723",
                       animate: [{ property: "opacity",
                         keyframes: [{ at: 0, value: 0 }, { at: 0.9, value: 1 }] }] }),
    ]) },

  { id: "personnel", dur: 7.50, build: (d) => beat(d, [
      kicker("01 / PERSONNEL", d),
      bigNum("1,300,000", d, 196),
      rule(d),
      caption("Active-duty service members across six branches - Army, Navy, Air Force, Marine Corps, Space Force and Coast Guard.", d),
      <text x={M} y={760} width={900} fontFamily={DISP} fontSize={74} color={ACC}
            animate={[inFade(d, 0.75), rise(d, 0.75, 24)]}>+764,900</text>,
      <text x={M} y={854} width={900} fontFamily={MONO} fontSize={25} letterSpacing={4}
            color={DIM} animate={[inFade(d, 0.85)]}>RESERVE AND NATIONAL GUARD (FY26 AUTHORIZED)</text>,
      ...barRows([
        { label: "ARMY",      value: "455,824", frac: 1.00, color: ACC },
        { label: "NAVY",      value: "341,496", frac: 0.75, color: STEEL },
        { label: "AIR FORCE", value: "318,983", frac: 0.70, color: STEEL },
      ], d),
    ]) },

  { id: "budget", dur: 5.65, build: (d) => beat(d, [
      kicker("02 / BUDGET", d),
      bigNum("$1 TRILLION", d, 152),
      rule(d),
      caption("FY2026 national defense - $838.7B in appropriations plus $150B in reconciliation funding. More than the next nine nations combined.", d),
      ...barRows([
        { label: "UNITED STATES",           value: "~$1.0T",  frac: 1.00, color: ACC },
        { label: "NEXT 9 NATIONS COMBINED", value: "~$0.97T", frac: 0.97, color: STEEL },
      ], d),
    ]) },

  { id: "air", dur: 7.30, build: (d) => beat(d, [
      kicker("03 / AIR POWER", d),
      bigNum("13,000+", d, 210),
      rule(d),
      caption("Military aircraft in service - the largest air fleet on Earth, roughly 2,950 of them combat aircraft.", d),
      ...chipRows([
        "1,300+ F-35 Lightning II delivered",
        "F-22 Raptor - air dominance",
        "B-2 Spirit and B-21 Raider entering service",
        "Global airlift and aerial refueling",
      ], d),
      icon("plane", { x: 1700, y: 806, size: 92, color: "#16212F",
                      animate: [{ property: "opacity",
                        keyframes: [{ at: 0, value: 0 }, { at: 0.8, value: 1 }] }] }),
    ]) },

  { id: "sea", dur: 8.10, build: (d) => beat(d, [
      kicker("04 / SEA POWER", d),
      bigNum("11", d, 264),
      rule(d),
      caption("Nuclear-powered aircraft carriers - more than the rest of the world combined, each a mobile airbase in international waters.", d),
      ...chipRows([
        "~300 battle-force ships",
        "64 submarines",
        "77 guided-missile destroyers",
        "Carrier strike groups forward-deployed",
      ], d),
      icon("ship", { x: 1700, y: 806, size: 92, color: "#16212F",
                     animate: [{ property: "opacity",
                       keyframes: [{ at: 0, value: 0 }, { at: 0.8, value: 1 }] }] }),
    ]) },

  { id: "nuclear", dur: 7.00, build: (d) => beat(d, [
      kicker("05 / STRATEGIC DETERRENT", d),
      bigNum("~5,000", d, 210),
      rule(d),
      caption("Nuclear warheads in the total inventory - roughly 1,770 of them deployed on the triad.", d),
      ...(() => {
        const cols = [
          { k: "AIR",  ic: "plane",  t: "B-52 / B-2 / B-21" },
          { k: "SEA",  ic: "anchor", t: "OHIO-CLASS SSBN" },
          { k: "LAND", ic: "rocket", t: "MINUTEMAN III SILOS" },
        ];
        const out = [];
        cols.forEach((c, i) => {
          const y = 316 + i * 176;
          const dd = 0.45 + i * 0.16;
          out.push(
            <rect key={"bx" + i} x={RX} y={y} width={RW} height={142} fill="#0E1622"
                  radius={14} strokeWidth={2} strokeColor="#1D2A3A"
                  animate={[inFade(d, dd)]} />,
            icon(c.ic, { x: RX + 34, y: y + 42, size: 58, color: ACC,
                         animate: [inFade(d, dd + 0.06)] }),
            <text key={"k" + i} x={RX + 124} y={y + 34} width={RW - 150} fontFamily={DISP}
                  fontSize={52} color={INK} animate={[inFade(d, dd + 0.06)]}>{c.k}</text>,
            <text key={"t" + i} x={RX + 126} y={y + 94} width={RW - 150} fontFamily={MONO}
                  fontSize={24} letterSpacing={2} color={DIM}
                  animate={[inFade(d, dd + 0.12)]}>{c.t}</text>,
          );
        });
        return out;
      })(),
    ]) },

  { id: "space", dur: 5.85, build: (d) => beat(d, [
      kicker("06 / SPACE AND CYBER", d),
      bigNum("SPACE FORCE", d, 138),
      rule(d),
      caption("Tracks tens of thousands of objects in orbit. GPS, satellite communications and missile warning guide every strike below.", d),
      <group name="radar" x={1180} y={330} width={420} height={420} origin="center"
             animate={[
               { property: "opacity", keyframes: [{ at: 0, value: 0 }, { at: 0.5, value: 0.9 }] },
               { property: "rotation", keyframes: [{ at: 0, value: 0 }, { at: 5.3, value: 360 }],
                 easing: "linear" },
             ]}>
        {icon("radar", { x: 0, y: 0, size: 420, color: ACC })}
      </group>,
      ...[0, 1, 2, 3, 4, 5].map((i) => (
        <rect key={"d" + i} x={1120 + (i % 3) * 250} y={800 + Math.floor(i / 3) * 46}
              width={14} height={14} radius={7} fill={i % 2 ? STEEL : ACC}
              animate={[{ property: "opacity",
                keyframes: [{ at: 0.5 + i * 0.09, value: 0 },
                            { at: 0.8 + i * 0.09, value: 1 }] }]} />
      )),
    ]) },

  { id: "reach", dur: 6.74, build: (d) => beat(d, [
      kicker("07 / GLOBAL REACH", d),
      bigNum("750", d, 260),
      rule(d),
      caption("Overseas base sites in roughly 80 countries - no other power comes close.", d),
      <text x={M} y={758} width={1000} fontFamily={DISP} fontSize={78} color={ACC}
            motion={{ by: "word", from: { y: 40, opacity: 0 }, overlap: 0.7,
                      duration: 0.5, easing: "house" }}>ANYWHERE. WITHIN HOURS.</text>,
      <group name="globe" x={1200} y={330} width={400} height={400} origin="center"
             animate={[
               { property: "opacity", keyframes: [{ at: 0, value: 0 }, { at: 0.55, value: 0.95 }] },
               { property: "scale", keyframes: [{ at: 0, value: 0.9 },
                 { at: 0.7, value: 1, easing: "house" }] },
             ]}>
        {icon("globe", { x: 0, y: 0, size: 400, color: STEEL })}
      </group>,
      ...[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
        <rect key={"p" + i} x={1140 + (i % 4) * 176} y={806 + Math.floor(i / 4) * 52}
              width={12} height={12} radius={6} fill={ACC}
              animate={[{ property: "opacity",
                keyframes: [{ at: 0.6 + i * 0.07, value: 0 },
                            { at: 0.85 + i * 0.07, value: 1 }] }]} />
      )),
    ]) },

  { id: "endcard", dur: ENDCARD, build: (d) => beat(d, [
      <text x={0} y={412} width={W} align="center" fontFamily={DISP} fontSize={104}
            color={INK}
            motion={{ by: "word", from: { y: 44, opacity: 0 }, overlap: 0.7,
                      duration: 0.5, easing: "house" }}>THE UNITED STATES MILITARY</text>,
      <text x={0} y={548} width={W} align="center" fontFamily={MONO} fontSize={28}
            letterSpacing={10} color={ACC}
            animate={[inFade(d, 0.35)]}>BY THE NUMBERS / 2026</text>,
      <text x={0} y={628} width={W} align="center" fontFamily={SANS} fontSize={23}
            color={DIM} animate={[inFade(d, 0.6)]}>
        Sources: DoD Comptroller / FY2026 NDAA / U.S. Navy / Lockheed Martin / Bulletin of the Atomic Scientists / SIPRI
      </text>,
    ]) },
];

export default async ({ project, icon: iconFn }) => {
  icon = iconFn;
  const p = await project({ dir: "proj", size: "1920x1080", fps: 30, background: BG });

  const vo = await p.add("vo.wav");
  p.cut(vo, { at: LEAD, from: 0, dur: VO_DUR });

  // persistent HUD frame behind every beat
  p.compose([
    <rect x={0} y={0} width={W} height={H} fill={{ kind: "radial", angle: 0, stops: [
      { offset: 0, color: "#0B1220" }, { offset: 1, color: BG } ] }} />,
    <rect x={0} y={0} width={W} height={2} fill={LINE} />,
    <rect x={0} y={H - 2} width={W} height={2} fill={LINE} />,
    <rect x={M} y={150} width={W - 2 * M} height={2} fill={LINE} />,
    <rect x={M} y={H - 150} width={W - 2 * M} height={2} fill={LINE} />,
    <rect x={M} y={150} width={3} height={40} fill={ACC} />,
    <rect x={W - M - 3} y={H - 190} width={3} height={40} fill={ACC} />,
    <text x={M} y={98} width={800} fontFamily={MONO} fontSize={23} letterSpacing={6}
          color={DIM}>UNITED STATES ARMED FORCES</text>,
    <text x={W - M - 800} y={98} width={800} align="right" fontFamily={MONO} fontSize={23}
          letterSpacing={6} color={DIM}>CAPABILITY BRIEF / FY2026</text>,
    <rect x={M} y={H - 96} width={W - 2 * M} height={4} fill={LINE} />,
    <rect x={M} y={H - 96} width={W - 2 * M} height={4} fill={ACC}
          mask={{ shape: "rectangle", x: 0, y: 0, width: W - 2 * M, height: 4 }}
          animate={[{ property: "maskWidth", from: 0, to: W - 2 * M, at: 0,
                     duration: TOTAL - 0.2, easing: "linear" }]} />,
  ], { at: 0, dur: TOTAL, name: "hud" });

  let at = 0;
  for (const b of BEATS) {
    p.compose(b.build(b.dur), { at, dur: b.dur, name: b.id });
    at += b.dur;
  }

  await p.frame(3.4,  "renders/f01-open.png");
  await p.frame(11.5, "renders/f02-personnel.png");
  await p.frame(18.5, "renders/f03-budget.png");
  await p.frame(25.0, "renders/f04-air.png");
  await p.frame(33.0, "renders/f05-sea.png");
  await p.frame(40.5, "renders/f06-nuclear.png");
  await p.frame(47.0, "renders/f07-space.png");
  await p.frame(53.0, "renders/f08-reach.png");
  await p.frame(58.5, "renders/f09-end.png");
};
