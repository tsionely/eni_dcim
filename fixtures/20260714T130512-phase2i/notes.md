# Phase 2i — Exact config-B hover rerun after true resting frame fix

- **Date (local):** 2026-07-14 ~15:54-16:05 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Code commit:** `a601c42...` (branch `main`, clean pull; see manifest.json)
- **Ground rules honored:** no code/config/docs edits. Race-start/screenshot helper was temp only.

## Exact command run
```powershell
python scripts/fly_once.py --max-duration 45 --patch planner.force_hover=true --patch control.att_rate.rate_p=1.2 --patch control.att_rate.rate_max_rps=1.5 --patch control.att_rate.tilt_max_rad=0.2 --patch control.att_rate.hover_thrust=0.30 --patch planner.takeoff.climb_mps=0.5
```

## Calibration lines
Initial calibration printed:
```text
gyro bias calibrated over 115 samples: [-2.97603786e-01  1.40095308e-01 -7.45058060e-08]; level ref roll=-0.901 pitch=+0.266
```

NEW live calibration line printed:
```text
live calibration (180 samples): bias=[0. 0. 0.] level roll=+0.000 pitch=-0.311
```

This matches the expected true resting frame pitch (~`-0.31`).

## Result
- `aborted=True`
- `abort_reason="environment collision (impulse=8.3)"`
- duration 37.98s
- `gates_passed=0`, `env_hits=1`
- 0 loop overruns
- fresh log: `20260714T125600-73ed53b1`

FSM/log facts:
- `ARMING -> THROTTLE_DOWN`
- `THROTTLE_DOWN -> TAKEOFF` reason `race GO`
- `TAKEOFF -> RACING` reason `takeoff complete`
- `RACING -> ABORTED` reason `environment collision (impulse=8.3)`
- setpoint phases: `hover` 1824 samples, `takeoff` 76 samples

## Visual stage behavior
1. **Countdown hold:** good. First screenshot shows countdown `2`, speed **0 km/h**, no DSQ.
2. **Climb / immediate post-GO:** not a gentle climb/hover. By ~3.3s, speed **58 km/h**, camera already rolled/tilted, looking off-axis.
3. **Hover check:** failed. At ~10.6s, speed **68 km/h** and still drifting/tumbling; no stable altitude or stationary hover interval.
4. **Late run:** at ~28.5s, speed **126 km/h**, camera angled sideways/up, then later environment collision (impulse 8.3).

## Hover/altitude stability and drift
- No actual hover observed despite correct live calibration pitch.
- Drift is fast, not slow: 58 km/h by ~3s, 68 km/h by ~10s, 126 km/h by ~28s.
- No meaningful hover oscillation frequency can be measured; dominant behavior is runaway translation/tumbling.

## Operator conclusion
The live calibration fix worked: `pitch=-0.311` now appears exactly as expected. However, exact config-B still does not hover; the post-GO force-hover controller accelerates/drifts rapidly and ends in a collision. The remaining issue is control tuning/force-hover behavior after GO, not countdown timing or resting-frame calibration.

## Fixture contents
- `report.txt` — full console output including calibration line and result.
- `screens/` — downscaled screenshots (~800px/q80) showing countdown, acceleration, late drift.
- `20260714T125600-73ed53b1-*` — fresh flight log/result/params.
- `manifest.json` — collector manifest.
- Recording note: collector skipped `vision.aigprec` (~567 MB); upload to Drive if needed.
