# Phase 5 — close-range frame collection on R2-TRAINING

- **Date (local):** 2026-07-16 / 2026-07-17 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Flight code commit:** `9fe3702` — Phase 5 replay-driven development
- **Track:** R2-TRAINING (selected by text-template matching the `R2 - TRAINING` label; visually verified by hangar + cyan ribbon before each counted flight)
- **Task:** fly two default-speed R2 flights, max-duration 300, and collect final-approach close-range frames/slices.

## Launch method
The first naive fly_once-first attempts aborted on the IMU watchdog before the helper could click RACE. To preserve the intent (fly_once starts before RACE) and still catch the live GO edge, I used this sequence:
1. Fresh simulator.
2. Pre-open the R2-TRAINING race dialog by text-matching the R2-TRAINING row (no pilot running yet).
3. Start `fly_once`.
4. Wait for `Connected. Starting IO agents...` where possible, then click RACE immediately.

This gives a real live GO edge (no 46s GO-timeout) and avoids fixed row coordinates. Both counted flights were R2-verified by cyan-ribbon screenshot.

## Valid flights

### F1 — `20260716T203450-2ca531c3`
- Launch style: pre-opened R2 dialog, then fly_once, then RACE.
- Result: `environment collision (impulse=3.3)`, duration 9.4s, gates 0.
- Telemetry: frames 2628, detections 1001, imu 1200.
- Phase runs: `hover -> takeoff -> approach -> commit -> retreat -> search`.
- Range thresholds from direct detections:
  - <=8m at t+1.0s
  - <=5m at t+5.4s
  - <=3m at t+6.9s
  - <=2m at t+7.2s
  - <=1m: no direct fix
- Closest direct: 1.50m at t+7.3s, center-x / LOW.
- Closest state: 0.03m at t+7.8s, LEFT / LOW, age 0.49s.
- Collision: t+10.4s.
- Slices:
  - `20260716T203450-2ca531c3_range5m_to_3m.aigprec` (start-s 5.0)
  - `20260716T203450-2ca531c3_range3m_to_collision.aigprec` (start-s 6.7)

### F2 — `20260716T212408-2ca531c3`
- Launch style: R2 dialog pre-opened, fly_once started, waited for `Connected`, then RACE clicked immediately.
- Result: `environment collision (impulse=3.7)`, duration 6.6s, gates 0.
- Telemetry: frames 1985, detections 946, imu 846.
- Phase runs: `hover -> takeoff -> approach -> commit`.
- Range thresholds from direct detections:
  - <=8m at t+1.0s
  - <=5m at t+7.1s
  - <=3m at t+7.1s
  - <=2m at t+7.2s
  - <=1m: no direct fix
- Closest direct: 1.67m at t+7.3s, center-x / HIGH.
- Closest state: 1.98m at t+7.5s, center-x / LOW, age 0.94s.
- Collision: t+7.5s.
- Slices:
  - `20260716T212408-2ca531c3_initial_to_5m.aigprec` (start-s 0)
  - `20260716T212408-2ca531c3_close_to_collision.aigprec` (start-s 4.0)

## Notes for the cloud
- These slices are intentionally close-range/final-approach focused, not pass windows.
- Direct detections still stop above 1m in these flights (closest direct 1.50m and 1.67m), while dead-reckoned state can report much closer (0.03m in F1). This supports the Phase 5 hypothesis: the close-range detector is the blocker.
- Full recordings are large: F1 ~562 MB, F2 ~269 MB; not committed. The four focused slices are ~28.9 MB each.

## Fixture contents
- `report.txt` — operator run log.
- `phase5_closerange_analysis.txt` — range-threshold and close-fix analysis.
- logs/results/params for both valid flights.
- Four close-range `.aigprec` slices.
- `screens/` — R2 verification plus representative approach screenshots.
