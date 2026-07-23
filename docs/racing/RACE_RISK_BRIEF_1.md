# RACE RISK BRIEF 1 — the crossing problem (for both advisory channels)

Per RESPONSE-89's invitation: race-risk advisory mode, engineering
triage, no criterion machinery. The parked campaign is untouched.

## Where the program stands (all measured, all pushed)

- Race sim v1.0.3390; interface diff read (one opt-in bit, we fly
  legacy); launch chain automated and proven (event templates 1.000).
- Owner directive: train on the R1 event (simple/high-contrast arena)
  inside the race sim; reliability gate >=7/10 gate-1 before any
  speed work; then transfer to R2-TRAINING.
- R1 baseline (6 runs): 0/6 gates. Failure anatomy: (a) vision is
  NOT the problem — 500-784 detections/run, full behavioral cycles;
  (b) 4/6 flights died to a ~100ms IMU transport hiccup against the
  50ms staleness trigger (fix registered: 0.25s, block T2a flying);
  (c) THE CROSSING PROBLEM — the open wall, below.

## The crossing problem, precisely

Across the entire program (~120 flights, three sims/eras), the drone
frequently reaches the gate vicinity but almost never completes a
crossing: best-ever is gate 1 a handful of times, never gate 2.
Sharpest instance (R1 baseline run 2): closest approach **0.77m from
gate center, true-world dz +0.04m, lateral +0.06m** — essentially
centered at under a meter — and no crossing; the flight later died
elsewhere. Approaches stall or divert in the final meter; commit
windows expire; retreat/recover cycles begin; blind searches follow.

Config levers already tried at length on R2 (all recorded in
COMPETITION_PLAN.md): commit speed 2.5 vs 1.8, vz cap 0.35 vs 1.2,
vision blend, vel leak both directions, slow-blind approach, terminal
corridor. None moved gate completion beyond ~1 pass per 5-10 runs.

## What is asked of the channels

ADVISORY-ONLY, one question, hostile eyes welcome: **what
distinguishes a completed crossing from a sub-1m stall, and what
would you instrument or change in the final meter to convert them?**
Specifically useful angles:
- The commit window's expiry/abort interplay in the last 0.5-1.0m
  (fixed-duration windows, brake bands, the abort_min_dist corridor).
- Detection continuity through the crossing plane (the gate leaves
  FOV at crossing — what governs the last commanded second?).
- Whether the near-centered stalls share a signature the logs can
  discriminate (the fixtures are all pushed; name what to extract
  and the lead or the analyst will compute it).

Evidence pointers: fixtures/*t2r1-B-run2 (the 0.77m stall),
fixtures/*r1k-off-run3 (a completed gate-1 pass on the same sim,
for contrast), fixtures/*raceprep-r1j3390-val-run2 (mechanism-rich
flight), and the pooled autopsy in
analysis/2026-07-22-pooled-collision-geometry/.

Conservative-on-conflict governs as always; dispositions come to the
lead; nothing here lifts any HOLD or touches the parked campaign.
