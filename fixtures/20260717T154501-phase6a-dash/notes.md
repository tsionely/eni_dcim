# Phase 6a EXP-2 — straight dash on HEAD/main

- **Date (local):** 2026-07-17 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Branch HEAD flown:** `d76762295e265da4df18cf0692a9210f74d044a5` (`d767622`, prior sim-run fixture commit)
- **Effective code base:** `1fc11fc` hotfix; commits after `1fc11fc` before this experiment were fixture-only sim-run commits.
- **Track:** verified `AI-GP VIRTUAL QUALIFIER R2 - TRAINING` row, click `[415,394]`, scene verified using the track-id reference.
- **Purpose:** straight-dash control — minimize steering and trust natural pad alignment.

## Command / patches

`python scripts/fly_once.py --max-duration 300 --patch safety.flight_timeout_s=300` plus:

- `--patch planner.approach.center_gain=0.0`
- `--patch planner.approach.yaw_center_gain=0.0`
- `--patch planner.commit.yaw_track_gain=0.0`
- `--patch planner.approach.aim_up_m=0.0`
- `--patch planner.commit.distance_m=6.5`

Commit phase engaged immediately after the first ~6m fix; both counted flights show `takeoff -> commit` directly.

## Counted flights

| Flight | Log ID | Gates | Gate clips | Env hits | Result | Closest direct fix | Closest believed state | Vertical read | Post-miss behavior |
|---|---|---:|---:|---:|---|---|---|---|---|
| dash-F1 | `20260717T153748-d946830d` | 0 | 0 | 1 | env collision (impulse=9.9), 14.08s | 2.30 m @ t+3.67s, center `[14.6,211.5]` | 1.01 m @ t+4.84s, age 1.20s | gate left edge / mid-low (y≈212) ⇒ slightly HIGH/left miss | commit→retreat→search→approach→hover; same active gate 0 |
| dash-F2 | `20260717T153903-d946830d` | 0 | 0 | 1 | env collision (impulse=4.4), 11.12s | **0.88 m** @ t+7.79s, center `[330.0,95.75]` | 0.99 m @ t+3.33s, age 1.20s | gate high in frame (y≈96) ⇒ drone LOW | commit→retreat→search→approach; same active gate 0 |

Two rejected attempts preceded counted dash-F1: one stale-frame abort, one verified-R2 flight that was too short for the >10s slice guard.

## EXP-2 verdict

Straight dash did **not** pass gate 1 in two counted flights. It did produce one useful near miss: dash-F2 reached a direct fix at 0.88 m with the gate high in the frame (LOW terminal read), but no gate pass and no clip.

## Slice verification

| Flight | TAKEOFF mono_ns | Slice file | Window | Unique frames | ~sec @30fps | Unique after TAKEOFF | Size |
|---|---:|---|---|---:|---:|---:|---:|
| dash-F1 | `712622721863600` | `20260717T153748-d946830d_takeoff_to_end.aigprec` | exact TAKEOFF→end | 326 | 10.9s | 325 | 18.2 MB |
| dash-F2 | `712697282446400` | `20260717T153903-d946830d_takeoff_to_end_full.aigprec` | full flight, covers TAKEOFF→end | 363 | 12.1s | 234 | 16.2 MB |

Reflight cross-check decoded 326 / 363 unique frames.

## Calibration

Both counted dash flights again showed exact-zero gyro bias:
`bias=[0. 0. 0.] level roll=+0.000 pitch=-0.311`.
