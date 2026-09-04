# The United States Military — By The Numbers (60s motion brief)

A one-minute 1080p motion-graphics presentation on US military scale, technology and
capability, with a Seed Audio 1.0 voice-over.

- **Output:** 1920×1080, 30 fps, 59.80 s, H.264 + AAC 48 kHz stereo
- **Voice-over:** Seed Audio 1.0 (ByteDance) — see [`voiceover-script.md`](voiceover-script.md)
- **Visuals:** deterministic motion graphics rendered with `higgsedit` from a single
  script, [`edit.jsx`](edit.jsx). No stock footage, no generated video clips — every
  frame is a pure function of timeline time.
- **Figures and citations:** [`SOURCES.md`](SOURCES.md)

## Design

Dark HUD-style capability brief. Amber (`#E5B23C`) carries the headline number and
every "now" accent; steel blue (`#3F6FA8`) carries comparison data; off-white is body
ink. Anton for display numerals, Inter for prose, JetBrains Mono for kickers and data
labels. A persistent frame — rules, corner ticks, header, and a progress rail that
fills across the full minute — sits behind all nine beats so the cuts feel like pages
of one document rather than separate slides.

Each data beat shares one grid: kicker → headline number → amber rule → caption on the
left; a chart, fact list, or diagram on the right.

## Rebuilding

Requires `higgsedit` (preinstalled in the Higgsfield sandbox) and the voice-over as
`vo.wav` beside the script.

```bash
higgsedit init proj --size 1920x1080 --fps 30
higgsedit fonts add proj Anton "Inter:400" "Inter:600" "Inter:700" "JetBrains Mono:500"
higgsedit build edit.jsx                      # writes the timeline + proof frames
higgsedit render proj --engine node --out renders/final.mp4
```

`edit.jsx` is the whole edit: re-running it reproduces the timeline exactly. Beat
durations at the top of the file come from Whisper word timings on `vo.wav`; if the
voice-over is regenerated, re-measure and update `EDGES` / the `BEATS` durations.

## Verification performed

- `higgsedit build` compiles all nine compositions with no refusals.
- Per-frame pixel analysis confirms no content outside the safe margins, no
  left/right column collisions, and a clear gap between every headline number and its
  rule.
- `higgsedit sweep --every 0.5` over the encoded master: 120 frames sampled, **0 blank
  or flat frames**.
- `ffprobe` confirms the delivered duration, dimensions, frame count and audio stream.
