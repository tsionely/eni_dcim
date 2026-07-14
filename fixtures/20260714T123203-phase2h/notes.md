# Phase 2h — Exact config-B hover rerun with live level calibration

- **Date (local):** 2026-07-14 ~15:00-15:32 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Code commit:** `a82109f...` (branch `main`, clean pull; see manifest.json)
- **Ground rules honored:** no code/config/docs edits. Race-start/screenshot helper was temp only.

## Exact command run
```powershell
python scripts/fly_once.py --max-duration 45 --patch planner.force_hover=true --patch control.att_rate.rate_p=1.2 --patch control.att_rate.rate_max_rps=1.5 --patch control.att_rate.tilt_max_rad=0.2 --patch control.att_rate.hover_thrust=0.30 --patch planner.takeoff.climb_mps=0.5
```

## Calibration lines
Initial calibration printed:
```text
gyro bias calibrated over 115 samples: [-0.00529973 -0.00074947 -0.00440466]; level ref roll=+0.091 pitch=+0.333
```

NEW live calibration line printed at/near TAKEOFF transition:
```text
live calibration (2072 samples): bias=[-0.00369183 -0.00052488 -0.00306136] level roll=+0.063 pitch=+0.140
```

Expected pitch was around `-0.31`, but measured live calibration pitch was **+0.140** (positive, not negative).

## Result
- `aborted=True`
- `abort_reason="max duration"`
- duration 45.00s
- `gates_passed=0`, `env_hits=0`
- loop clean: 0 overruns
- fresh log: `20260714T122243-73ed53b1`

FSM/log facts:
- `ARMING -> THROTTLE_DOWN`
- `THROTTLE_DOWN -> TAKEOFF` reason `race GO`
- `TAKEOFF -> RACING` reason `takeoff complete`
- `RACING -> ABORTED` reason `max duration`
- setpoint phases: `hover` 2176 samples, `takeoff` 75 samples

## Visual behavior / hover assessment
No actual hover was observed.

- **Countdown hold:** legal and clean. First screenshot: countdown `2`, **0 km/h**, no DSQ.
- **Early post-GO:** at ~3.3s, drone already moving **54 km/h** down the course; this is not gentle climb/hover.
- **Mid-run:** at ~8.5s, speed **113 km/h**; still accelerating/drifting rapidly.
- **Later:** at ~29s, speed **136 km/h** with camera looking up/sideways; no stable hover. It survives to max-duration but as uncontrolled high-speed drift, not hovering.

## Altitude stability and slow drift
- There is no stable altitude hold. The craft translates rapidly away from the launch point.
- Drift is not slow; it is high-speed forward/diagonal drift/acceleration.
- No meaningful oscillation frequency can be estimated because the dominant motion is runaway translation rather than hover oscillation.

## Operator conclusion
The new live calibration line appeared, but did **not** match the expected `pitch ~ -0.31`; it printed `pitch=+0.140`.
The exact config-B rerun did not produce actual hover. Countdown/GO sequencing is good, but the force-hover controller still launches into high-speed drift.

## Fixture contents
- `report.txt` — full console output including calibration line and result.
- `screens/` — downscaled screenshots (~800px/q80) for countdown, acceleration, late drift.
- `20260714T122243-73ed53b1-*` — fresh flight log/result/params.
- `manifest.json` — collector manifest.
- Recording note: collector skipped `vision.aigprec` (~734 MB); upload to Drive if needed.
