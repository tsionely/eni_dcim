# Phase 2g — Rerun hover ladder config B exactly

- **Date (local):** 2026-07-14 ~15:00 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Code commit:** `a82109f...` (branch `main`, clean pull; see manifest.json)
- **Ground rules honored:** no code/config/docs edits. Race-start/screenshot helper was temp only.

## Single-instance verification
Exactly one simulator instance:
- `FlightSim.exe` PID 56276
- `DCGame-Win64-Shipping.exe` PID 49312
- engine owns `udp:14560` and `udp:5601`
- no stale Python processes at preflight.

## Exact command run
```powershell
python scripts/fly_once.py --max-duration 45 --patch planner.force_hover=true --patch control.att_rate.rate_p=1.2 --patch control.att_rate.rate_max_rps=1.5 --patch control.att_rate.tilt_max_rad=0.2 --patch control.att_rate.hover_thrust=0.30 --patch planner.takeoff.climb_mps=0.5
```

## Calibration line
The new calibration line printed:
```text
gyro bias calibrated over 114 samples: [ 1.99791978e-38 -7.76833794e-38  1.72097041e-37]; level ref roll=+0.115 pitch=+0.047
```
This did **not** match the expected `pitch ~= -0.31`; measured level reference pitch was near zero/slightly positive (`+0.047`).

## Result
- `aborted=True`
- `abort_reason="environment collision (impulse=33.3)"`
- duration `33.94s`
- `gates_passed=0`, `env_hits=1`
- loop clean: 0 overruns
- fresh log: `20260714T120153-73ed53b1`

FSM/log phases:
- `ARMING -> THROTTLE_DOWN`
- `THROTTLE_DOWN -> TAKEOFF` reason `race GO`
- `TAKEOFF -> RACING` reason `takeoff complete`
- `RACING -> ABORTED` reason `environment collision (impulse=33.3)`
- setpoint phases: `hover` 1623 samples, `takeoff` 75 samples

## Visual hover / drift observation
No actual hover was observed.

- **Countdown hold:** good. First screenshot shows countdown `2`, speed **0 km/h**, no DSQ.
- **Post-GO / climb:** by ~3.3s after start, drone was already moving at **51 km/h**. This is not a gentle climb/hover.
- **Mid-run drift:** by ~8.4s, speed was **113 km/h**, still in ACRO mode, moving rapidly down the corridor.
- **Late run:** visual stream then showed menu/desktop/focus-loss after the collision/reset. The flight result confirms environment collision.

## Altitude / oscillation notes
- No stable 5s hover interval, so no reliable hover oscillation frequency can be estimated.
- The behavior is dominated by forward/diagonal translational acceleration rather than a visible hover oscillation.
- Approximate altitude/stability: the craft appears to leave the launch position and drift/accelerate rapidly rather than hold altitude; by 8s it is still moving fast, not stationary.

## Interpretation for cloud agent
- The exact config B does **not** produce the expected actual hover in this rerun.
- The level reference is suspicious: expected pitch around `-0.31`, but printed `+0.047`.
- The legal GO/coundown hold remains fixed, but post-GO stabilization still fails into high-speed drift/collision.
- The next investigation likely should focus on why the level reference calibration differs from expected and why force-hover commands still produce strong translation.

## Fixture contents
- `report.txt` — full console output for the exact run.
- `screens/` — downscaled JPEG screenshots (~800px/q80) documenting countdown, acceleration, late failure.
- `20260714T120153-73ed53b1-*` — fresh flight log/result/params.
- `manifest.json` — collector manifest.
- Recording note: collector skipped `vision.aigprec` (~437 MB); upload to Drive if needed.
