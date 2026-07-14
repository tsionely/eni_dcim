# Phase 2k — Vision-velocity hover trim + follow-up search run

- **Date (local):** 2026-07-14 ~16:57-17:36 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Code commit:** `2cc8df9...` (branch `main`, clean pull; see manifest.json)
- **Ground rules honored:** no code/config/docs edits. Race-start/screenshot helper was temp only.

## Preflight / interference note
At first, tuning/analysis Python jobs had bound the real sim ports `14550/5600`.
- PID 45720 (`run_campaign.py --sim mock --low-load`) was stopped after approval; it then disappeared.
- PID 15792 (`tuning\run_trim_campaign.py`) could not be terminated gracefully, so I did **not** force-kill it. After waiting 60s it released the ports naturally.
- Then the real sim ports were free and the Phase 2k run proceeded.

## Run 1: exact Phase 2j Variant 1 (force_hover)
Command shape:
```powershell
python scripts/fly_once.py --max-duration 45 --patch planner.force_hover=true --patch control.att_rate.rate_p=1.2 --patch control.att_rate.rate_max_rps=1.5 --patch control.att_rate.tilt_max_rad=0.2 --patch control.att_rate.hover_thrust=0.30 --patch planner.takeoff.climb_mps=0.5 --patch estimation.mahony_kp=0
```

Calibration:
```text
gyro bias calibrated over 115 samples: [2.07837526e-04 1.20679397e-06 4.24006430e-07]; level ref roll=+0.018 pitch=-0.414
live calibration (180 samples): bias=[0. 0. 0.] level roll=+0.000 pitch=-0.311
```

Result:
- `aborted=True`, `abort_reason="max duration"`
- duration 45.00s
- `env_hits=0`, `gates_passed=0`
- fresh hover log included: `20260714T141416-1429a43c`

Controller-estimated speeds (from `state.v_world`, relative to race GO):
- ~3s: **28.7 km/h**
- ~10s: **71.3 km/h**
- ~20s: **5.4 km/h**
- ~40s: no 40s state sample; nearest valid state was ~26.34s with **1.3 km/h**

Visual interpretation:
- Countdown hold was legal.
- Early in the run it moved/drifted, but the controller's vision-velocity estimate later decayed near zero.
- This satisfied the instruction's conditional threshold (`<15 km/h`), so I immediately ran the non-force-hover follow-up.

Caveat:
- The image-view helper timed out during inspection, so the exact speeds above are from the fresh flight log, not hand-read HUD numbers. The included downscaled screenshots show the visual context.

## Run 2: follow-up WITHOUT force_hover (search/approach enabled)
Command shape: same as Run 1 but **without** `planner.force_hover=true`:
```powershell
python scripts/fly_once.py --max-duration 45 --patch control.att_rate.rate_p=1.2 --patch control.att_rate.rate_max_rps=1.5 --patch control.att_rate.tilt_max_rad=0.2 --patch control.att_rate.hover_thrust=0.30 --patch planner.takeoff.climb_mps=0.5 --patch estimation.mahony_kp=0
```

Calibration:
```text
gyro bias calibrated over 114 samples: [-8.20692629e-03  3.74402910e-01 -1.26659870e-07]; level ref roll=-3.074 pitch=+0.452
live calibration (180 samples): bias=[0. 0. 0.] level roll=+0.000 pitch=-0.311
```

Result:
- `aborted=True`, `abort_reason="environment collision (impulse=9.7)"`
- duration 40.10s
- `env_hits=1`, `gates_passed=0`
- fresh search log included: `20260714T142516-d195adf3`

Setpoint phases:
- `hover`: 913 samples
- `takeoff`: 76 samples
- `approach`: 1016 samples

Controller-estimated speeds (relative to race GO):
- ~3s: **207.4 km/h**
- ~10s: **91.6 km/h**
- ~20s: **69.8 km/h**
- ~40s: no 40s state sample; nearest valid state was ~21.82s with **54.3 km/h**

Visual/behavior interpretation:
- Without force_hover, the pilot entered approach mode, but velocity became extremely high very quickly.
- It did **not** approach gate 1 in a controlled way; it collided/aborted.

## Main conclusion
The new vision-velocity fix does appear to let the force-hover run's estimated speed trim down below 15 km/h by ~20s/last valid state — this is a major improvement over prior runaway-only runs.

However, when `force_hover` is removed and approach is enabled, the controller accelerates violently and collides. The force-hover behavior is close to useful trim; the approach/search transition is not yet safe.

## Fixture contents
- `report.txt` — full console output for both runs and speed tables.
- `screens/` — downscaled screenshots for hover run and non-force-hover follow-up.
- `20260714T141416-1429a43c-*` — force-hover run log/result/params.
- `20260714T142516-d195adf3-*` — non-force-hover follow-up log/result/params.
- `manifest.json` — collector manifest.
- Recording note: collector skipped large `vision.aigprec`; upload to Drive if needed.
