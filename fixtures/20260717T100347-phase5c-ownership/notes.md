# Phase 5c — terminal-ownership cycle (VERIFIED R2-TRAINING)

- **Date (local):** 2026-07-17 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Operator workspace:** `C:\Users\tsion\Projects\eni_dcim_phase1` (Option A real team clone)
- **Code flown:** `34d4f6b6b4476162dff0a9d7ee1f798528fe90e0` (`34d4f6b` — "Terminal ownership + collision lock-clear: the F3 autopsy fixes")
- **Command:** `scripts\fly_once.py --max-duration 300 --patch safety.flight_timeout_s=300`
- **SIM LOCK:** `C:\Temp\eni_dcim_sim.lock` held (owner `phase5c-ownership pid=70684`).
- **Launch procedure:** verified-row select (no pilot) → `fly_once` → RACE on `Connected. Starting IO agents...`.

## Track verification (per flight)

All three used the deterministic template selector on the ACTIVE EVENTS list;
the bottom row `AI-GP VIRTUAL QUALIFIER R2 - TRAINING` was selected at click
`[415,394]`. Row template scores and the in-sim R2 scene (hangar floor, station
pillars, traffic posts, parked jets, cyan ribbon) were verified before each
counted flight — evidence in `track_verification/`.

| Flight | Row scores R1 / R2sub / R2train | Click | Post-RACE cyan px | Track |
|---|---|---|---:|---|
| F1 | 0.99970 / 0.99977 / 0.99959 | [415,394] | 74,583 | R2-TRAINING ✓ |
| F2 | 0.99960 / 0.99975 / 0.99965 | [415,394] | 127,381 | R2-TRAINING ✓ |
| F3 | 0.97611 / 0.99971 / 0.99976 | [415,394] | 208,222 | R2-TRAINING ✓ |

`RaceStatus` exposes only `active_gate_index` (no total-gate count). All three
flights stayed at `active_gate_index=0`.

## Flights (build 34d4f6b)

| Flight | Log ID | Result | Gates / active_gate | Clips / env | Closest direct fix | Closest believed state | Near-gate ownership / post-clip | High/Low |
|---|---|---|---:|---:|---|---|---|---|
| F1 | `20260717T095722-a560c093` | env collision (impulse=1.4), 13.86s | 0 / 0..0 | 1 clip / 4 env | 1.46 m @ t+3.5s (gate center px [169,178]) | 0.41 m, age 0.43s | **Stayed on same gate; multiple re-approaches:** approach→commit→retreat→approach→commit→recover→search→approach; active gate never advanced | center near mid-frame (~178/360) |
| F2 | `20260717T095851-a560c093` | env collision (impulse=3.7), 10.34s | 0 / 0..0 | 0 clips / 2 env | 1.83 m @ t+6.8s (gate center px [172,96]) | 0.84 m, age 1.21s | approach→commit→retreat→hover collision; same gate | gate HIGH in frame (y≈96) ⇒ drone LOW |
| F3 | `20260717T100017-a560c093` | env collision (impulse=11.0), 12.69s | 0 / 0..0 | 0 clips / 1 env | **0.90 m** @ t+9.2s (gate center px [322,85]) | 0.06 m, age 1.20s | approach→commit→retreat→long re-approach; same gate | gate HIGH in frame (y≈85) ⇒ drone LOW |

## Answers to the watch-items

- **Does it stay on the NEAR gate through the attempt?** Yes — this is the
  visible change vs phase5b. In all three flights `active_gate_index` stayed 0
  and the believed-vs-direct gap narrowed markedly: phase5b F1 believed 0.04 m
  while honest direct was only 3.75 m (far-gate runaway); here the honest direct
  fixes reach 1.46 / 1.83 / 0.90 m, i.e. the lock is holding the near gate much
  further in rather than jumping to the far center. reflight fix histograms show
  real fixes in the 1.0-2.0 m bins (F1: 1 @1-1.5, 3 @1.5-2; F3: 1 @0.5-1,
  1 @1-1.5), which phase5b lacked.
- **Post-clip same-gate re-acquisition?** Yes. F1 clipped once then went
  retreat→approach→commit again and kept `active_gate_index=0`; F1 shows the
  richest retry chain (two commit attempts + recover + search + a third
  approach) all on the same gate — consistent with the collision-clears-lock +
  terminal-ownership fixes.
- **HIGH or LOW?** At the closest terminal fixes the gate sits HIGH in the image
  (F2 y≈96, F3 y≈85 of 360; camera tilted up ~11°), i.e. the drone is BELOW the
  opening ⇒ attempts read **LOW** at terminal range. Mid-approach the spectator
  frames show the drone climbing high toward the ceiling truss, then dropping
  onto/short of the gate line — the vertical channel is still the open axis.
- **Calibration line (requested):** identical on all three flights —
  `gyro bias calibrated over 116-118 samples: [0. 0. 0.]; level ref roll=+0.000 pitch=-0.311`
  and `live calibration (180 samples): bias=[0. 0. 0.] level roll=+0.000 pitch=-0.311`.
  **Still exactly `bias=[0. 0. 0.]`** on all three — the suspicious zeros persist
  on 34d4f6b, matching the phase5b observation (likely frozen countdown
  telemetry during the calibration window). Flagging for the calibration-window
  move.

## Slice verification (TAKEOFF → end)

TAKEOFF located from the FSM `dst="TAKEOFF"` line per flight; slices deduped by
vision payload then decoded/deduped by `frame_id` and cross-checked with
`scripts/reflight.py`.

| Flight | TAKEOFF mono_ns | Slice file | Window | Unique frames | ~sec @30fps | Unique after TAKEOFF | Size |
|---|---:|---|---|---:|---:|---:|---:|
| F1 | `692195295198500` | `20260717T095722-a560c093_takeoff_to_end.aigprec` | exact TAKEOFF→end | 319 | 10.6s | 318 | 13.9 MB |
| F2 | `692284542471500` | `20260717T095851-a560c093_takeoff_to_end_full.aigprec` | full flight, covers TAKEOFF→end (takeoff-only was 7.0s) | 340 | 11.3s | 210 | 15.5 MB |
| F3 | `692370436025500` | `20260717T100017-a560c093_takeoff_to_end_full.aigprec` | full flight, covers TAKEOFF→end (takeoff-only was 9.3s) | 412 | 13.7s | 278 | 21.8 MB |

reflight unique-frame counts matched (319 / 340 / 412). Closest replay fix:
F1 1.46 m, F2 1.83 m, F3 0.90 m.

## Full recordings (not committed — too large)

- F1 `logs/20260717T095722-a560c093/vision.aigprec` (~610 MB)
- F2 `logs/20260717T095851-a560c093/vision.aigprec` (~560 MB)
- F3 `logs/20260717T100017-a560c093/vision.aigprec` (~688 MB)

Committed deduped slices are the intended analysis artifacts.
