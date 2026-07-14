# Phase 2j — Mahony-off / level-ref hover variants

- **Date (local):** 2026-07-14 ~16:16-16:40 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Code commit:** `da38639...` (branch `main`, clean pull; see manifest.json)
- **Ground rules honored:** no code/config/docs edits. Race-start/screenshot helper was temp only.

## Shared base command
Both variants used exact config-B hover baseline:
```powershell
python scripts/fly_once.py --max-duration 45 --patch planner.force_hover=true --patch control.att_rate.rate_p=1.2 --patch control.att_rate.rate_max_rps=1.5 --patch control.att_rate.tilt_max_rad=0.2 --patch control.att_rate.hover_thrust=0.30 --patch planner.takeoff.climb_mps=0.5
```

## Variant 1: `--patch estimation.mahony_kp=0`

Calibration:
```text
gyro bias calibrated over 115 samples: [-3.87568325e-02  2.90300772e-02  6.05359674e-09]; level ref roll=-0.766 pitch=+0.232
live calibration (180 samples): bias=[0. 0. 0.] level roll=+0.000 pitch=-0.311
```

Result:
- `aborted=True`, `abort_reason="max duration"`
- duration 45.00s
- `gates_passed=0`, `env_hits=7`
- 1 loop overrun
- log: `20260714T132005-1429a43c` (local only; collect_artifacts copied the later V2 log)

Visual behavior / speed:
- countdown hold good: 0 km/h at countdown `2`, no DSQ.
- ~3s: **38 km/h**
- ~8-10s: **41 km/h** (screenshot at ~8.4s)
- ~18.5s: **34 km/h**
- Later screenshots lost sim focus after the run, but the in-race frames show sustained drift rather than hover.

Hover verdict:
- **Not a hover**, but this is the slower/better of the two variants.
- It has a slow-ish continuous drift, not explosive tumble. This may be the first run where attitude is closer to stable and velocity trim is becoming the dominant problem.
- No clear oscillation frequency visible; the motion is mostly translational drift at ~30-40 km/h.

## Variant 2: `--patch estimation.mahony_kp=0 --patch control.att_rate.use_level_ref=false`

Calibration:
```text
gyro bias calibrated over 114 samples: [0.05155063 0.09013469 0.02922129]; level ref roll=-0.141 pitch=-1.048
live calibration (180 samples): bias=[0. 0. 0.] level roll=+0.000 pitch=-0.311
```

Result:
- `aborted=True`, `abort_reason="max duration"`
- duration 45.00s
- `gates_passed=0`, `env_hits=0`
- 0 loop overruns
- fresh log collected: `20260714T132354-80030858`

Visual behavior / speed:
- countdown hold good: 0 km/h at countdown `2`, no DSQ.
- ~3s: **57 km/h**
- ~18.6s: **103 km/h**
- Later screenshots eventually captured post-run/menu/desktop state.

Hover verdict:
- **Not a hover**; worse than Variant 1. Disabling the level reference causes faster drift/acceleration.

## Overall conclusion
Neither variant achieved an actual stationary hover.

- Variant 1 (`mahony_kp=0`) is closer: it reduces runaway speed to roughly 30-40 km/h drift and may mean the attitude loop is finally mostly holding, with remaining velocity/trim drift.
- Variant 2 (`use_level_ref=false`) is worse: 57 km/h at ~3s and ~103 km/h by ~18s.

The best next direction appears to be based on Variant 1: keep `mahony_kp=0` and `use_level_ref=true`, then add velocity/position trim or further reduce/ramp hover thrust. If the goal is "SLOW drift is success", Variant 1 is the closest, but it is still not slow enough to call a hover.

## Fixture contents
- `report.txt` — full console for both variants.
- `screens/` — downscaled JPEGs for both variants.
- `20260714T132354-80030858-*` — fresh Variant 2 flight log/result/params (collector copied newest log).
- `manifest.json` — collector manifest.
- Recording note: collector skipped `vision.aigprec` (~656 MB); upload to Drive if needed.
