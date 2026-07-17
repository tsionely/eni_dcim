# Track-ID reference — R1 vs R2-TRAINING (AI-GP sim v1.0.3385)

**Captured:** 2026-07-17 Asia/Jerusalem, by SIM OPERATOR (Sakana).
**Why:** Scene appearance alone is a WEAK discriminator — both R1 and
R2-TRAINING are dark warehouses with red square AI-GP gates and a cyan
racing-line ribbon (per phase1e recon). This is the permanent reference for
identifying the track in every future report.

## Event list (deterministic selection)
The FLY → ACTIVE EVENTS list has exactly three rows, top→bottom:
1. `AI-GP VIRTUAL QUALIFIER R1`            (row center ≈ y235, click [415,236])
2. `AI-GP VIRTUAL QUALIFIER R2 - SUBMISSION` (row center ≈ y314) — do NOT fly (real submission)
3. `AI-GP VIRTUAL QUALIFIER R2 - TRAINING` (row center ≈ y394, click [415,394])

Selection is verified by template-matching each row's label text (all three
match ≈1.00 on the live event list) and clicking the intended row's matched
box center. `*_row_highlight.jpg` shows the hover/selection state on the
R2-TRAINING row before the dialog is opened. The race dialog itself is
generic ("PLEASE ENSURE YOUR AUTOMATED PILOT IS READY" + RACE) and does NOT
name the event, so trust the verified selected row, never the dialog.

## Distinguishing features of the FLOWN scene

### R1 (`r1_scene_*.jpg`)
- Black void / zero-g "space-station" corridor — NO warehouse floor, NO
  ceiling-truss lighting grid over a hangar, NO station pillars.
- Environment is made of pale wireframe/greebled box structures floating in
  black on both sides of a narrow cyan tube corridor.
- Multiple stacked red AI-GP gates recede straight down the corridor; the
  next gates are visible small and far along the tube.
- No traffic-light posts, no parked jets, no "Station NN" signage.

### R2-TRAINING (`r2training_scene_*.jpg`)
- Dark HANGAR with a real floor, bright ceiling-truss lighting grid, and
  tall dark PILLARS labelled "Station 03/04/05/18/19/22/23" etc.
- Red/green TRAFFIC-LIGHT posts stand on tripods at the start line
  (green = go), and PARKED JETS/aircraft sit between the station bays.
- The first red square AI-GP gate stands close ahead on the pad (~6 m),
  with the cyan ribbon running down the hangar centre through the gates.
- "AI-GP" banner tops each gate with sponsor logos (JobsOhio, ANDURIL, DCL).

**Quickest check:** station-number pillars + traffic-light posts + parked
jets ⇒ R2-TRAINING. Floating wireframe boxes in black with no floor/pillars
⇒ R1.

## Telemetry-based ID
- The sim `RaceStatus` message exposes `active_gate_index` and
  `last_gate_race_time` but **no total-gate-count field**, so gate count is
  not directly available from the flight log. Track ID from the log is
  therefore best derived from the recorded vision (scene features above);
  each flight report also records the verified selected row and the observed
  `active_gate_index` range.
- The window title is `AI-GP Simulator vX.Y.Z` (does not encode the event).

## Files
- `r1_eventlist.jpg` — full event list (all three rows visible).
- `r1_race_dialog.jpg`, `r2training_race_dialog.jpg` — the generic race dialog.
- `r2training_row_highlight.jpg` — verified R2-TRAINING row selection state.
- `r1_scene_01..03.jpg`, `r2training_scene_01..03.jpg` — loaded scenes
  (no flight), start-pad view, cam 20°.
