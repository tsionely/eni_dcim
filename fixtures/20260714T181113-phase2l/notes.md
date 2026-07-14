# Phase 2l — Vision-velocity fix: hover confirmation + gate attempt

- **Date (local):** 2026-07-14 ~18:31-18:55 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Code commit:** `4d683cc...` (branch `main`, clean pull; see manifest.json)
- **Simulator lifecycle:** started from no sim running, launched a fresh FlightSim instance for this cycle (FlightSim PID 34952, DCGame PID 53876).
- **Ground rules honored:** no code/config/docs edits. Race-start/screenshot helper was temp only.

## Flight 1 — exact Phase 2k force_hover command
Command:
```powershell
python scripts/fly_once.py --max-duration 45 --patch planner.force_hover=true --patch control.att_rate.rate_p=1.2 --patch control.att_rate.rate_max_rps=1.5 --patch control.att_rate.tilt_max_rad=0.2 --patch control.att_rate.hover_thrust=0.30 --patch planner.takeoff.climb_mps=0.5 --patch estimation.mahony_kp=0
```

Calibration:
```text
gyro bias calibrated over 115 samples: [0. 0. 0.]; level ref roll=+0.000 pitch=-0.311
live calibration (180 samples): bias=[0. 0. 0.] level roll=+0.000 pitch=-0.311
```

Result:
- `aborted=True`, `abort_reason="max duration"`
- duration 45.00s
- `gates_passed=0`, `env_hits=15`
- fresh log: `20260714T153715-1429a43c`

Controller-estimated speeds from `state.v_world` relative to race GO:
- ~3s: **12.3 km/h**
- ~10s: **150.5 km/h**
- ~20s: **6.8 km/h**
- ~40s: no state sample; nearest valid state at ~26.76s: **7.2 km/h**

Visual/stage account:
- Countdown hold legal.
- Early motion was moderate/low compared with earlier runs (~12 km/h at 3s by log), but speed estimate spiked around 10s.
- Later estimates settle under 15 km/h, but `env_hits=15` means it is not a clean hover. It appears to contact or skim environment while trying to stabilize.
- Since it settled below the requested threshold, I ran the required non-force-hover gate attempt.

## Flight 2 — gate attempt (drop force_hover, add vision_vel_world_frame=true)
Command:
```powershell
python scripts/fly_once.py --max-duration 45 --patch control.att_rate.rate_p=1.2 --patch control.att_rate.rate_max_rps=1.5 --patch control.att_rate.tilt_max_rad=0.2 --patch control.att_rate.hover_thrust=0.30 --patch planner.takeoff.climb_mps=0.5 --patch estimation.mahony_kp=0 --patch estimation.vision_vel_world_frame=true
```

Calibration:
```text
gyro bias calibrated over 115 samples: [-1.70576895e-04  1.22514291e-04 -4.36557457e-11]; level ref roll=+0.016 pitch=-0.606
live calibration (180 samples): bias=[0. 0. 0.] level roll=+0.000 pitch=-0.311
```

Result:
- `aborted=True`, `abort_reason="max duration"`
- duration 45.00s
- `gates_passed=0`, max active gate index 0
- `env_hits=0`
- phases: `hover` 910 samples, `takeoff` 76, `approach` 1265
- fresh log: `20260714T154340-77aba731`

Controller-estimated speeds from `state.v_world` relative to race GO:
- ~3s: **11.7 km/h**
- ~10s: **61.7 km/h**
- ~20s: **454.5 km/h**
- ~40s: no state sample; nearest valid state at ~26.8s: **509.4 km/h**

Visual/stage account:
- Countdown hold legal.
- Hover-out/takeoff begins controlled enough to enter the planner phases.
- The pilot enters **approach** phase (unlike force_hover), but speed grows violently after the transition.
- No gate pass; active gate index remained 0 and `gates_passed=0`.
- No collision was reported in the result, but the speed estimate becomes extreme; approach is not safe/stable yet.

## Overall conclusion
The vision-velocity fix helps the force-hover mode trim estimated speed back down after transients, but the run still reports many environment contacts. The gate attempt enters approach but accelerates violently and never passes gate 1.

Phase-3 milestone (`gates_passed > 0`) was **not reached** in this cycle.

## Fixture contents
- `report.txt` — full console output and speed tables.
- `screens/` — downscaled screenshots and HUD crops for hover + gate attempt.
- `20260714T153715-1429a43c-*` — force-hover log/result/params.
- `20260714T154340-77aba731-*` — gate-attempt log/result/params.
- `manifest.json` — collector manifest.
- Recording note: collector skipped a large `vision.aigprec` (~683 MB); upload to Drive if needed.
