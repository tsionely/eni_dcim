# Phase 6a EXP-1 — regression control on old build 80c6d44

- **Date (local):** 2026-07-17 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Code flown:** `80c6d44f550eaf7f9e0dfa5823a35265b41d849f` (`80c6d44` — Stage watchdog arming: imu at start, frame at GO)
- **Command:** `scripts\fly_once.py --max-duration 300 --patch safety.flight_timeout_s=300`
- **Track:** verified `AI-GP VIRTUAL QUALIFIER R2 - TRAINING` row, click `[415,394]`, scene verified using the track-id reference.
- **Purpose:** regression control — check whether milestone-era build still passes gate 1 when current HEAD does not.

## Counted flights

| Flight | Log ID | Gates | Gate clips | Env hits | Result | Closest direct fix | Closest believed state | Vertical read | Post-miss behavior |
|---|---|---:|---:|---:|---|---|---|---|---|
| old-F1 | `20260717T153048-927a4c97` | 0 | 0 | 5 | env collision (impulse=2.4), 12.19s | 3.03 m @ t+2.34s, center `[366.5,159.75]` | 0.03 m @ t+3.53s, age 1.17s | gate slightly high/near-center (y≈160) ⇒ slight LOW/center | approach→commit→retreat→approach→recover; same active gate 0 |
| old-F2 | `20260717T153307-927a4c97` | 0 | 0 | 1 | env collision (impulse=1.0), 11.46s | 5.06 m @ t+1.62s, center `[246.5,301.5]` | 0.77 m @ t+3.14s, age 1.48s | gate low in frame (y≈302) ⇒ drone HIGH | approach→commit→retreat→search; same active gate 0 |

A stale/R2-not-verified launch attempt (`20260717T153201-927a4c97`, stale channels: imu) was rejected and not counted.

## EXP-1 verdict

The old milestone-era build **did not pass gate 1** in either of the two counted verified-R2 flights. It also did not record any gate clips. Therefore this control does **not** show "old passes, HEAD fails" under today's conditions; no regression-by-composition is proven by this two-flight sample.

## Slice verification

Exact TAKEOFF→end was under 10s unique video for both old-control flights, so both slices were widened to full-flight while still covering TAKEOFF→end.

| Flight | TAKEOFF mono_ns | Slice file | Window | Unique frames | ~sec @30fps | Unique after TAKEOFF | Size |
|---|---:|---|---|---:|---:|---:|---:|
| old-F1 | `712203351165700` | `20260717T153048-927a4c97_takeoff_to_end_full.aigprec` | full flight, covers TAKEOFF→end | 390 | 13.0s | 252 | 20.7 MB |
| old-F2 | `712342126807900` | `20260717T153307-927a4c97_takeoff_to_end_full.aigprec` | full flight, covers TAKEOFF→end | 373 | 12.4s | 238 | 16.2 MB |

Reflight cross-check decoded 390 / 373 unique frames.

## Calibration

Both counted old-control flights again showed exact-zero gyro bias:
`bias=[0. 0. 0.] level roll=+0.000 pitch=-0.311`.
