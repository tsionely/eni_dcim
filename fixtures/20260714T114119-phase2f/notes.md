# Phase 2f — Hover-only stabilization ladder

- **Date (local):** 2026-07-14 ~12:45-14:41 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Code commit:** `5703c18...` (branch `main`, clean pull; see manifest.json)
- **Ground rules honored:** no edits to `src/`, `config`, `simtools`, `tests`, or `docs`.
- **Important:** per runbook, I did **not** use any old Phase 2e gyro patches. Only the prescribed hover-only patches a/b/c were used.

## Single-instance verification
Exactly one simulator instance:
- `FlightSim.exe` PID 56276
- `DCGame-Win64-Shipping.exe` PID 49312
- engine owns `udp:14560` and `udp:5601`
- no stale python processes before the ladder.

## Attempt A
Command shape:
```
planner.force_hover=true
control.att_rate.rate_p=2.5
control.att_rate.rate_max_rps=1.5
control.att_rate.tilt_max_rad=0.2
control.att_rate.hover_thrust=0.30
planner.takeoff.climb_mps=0.5
```
Result:
- `aborted=True`, `abort_reason="stale channels: frame"`
- duration 15.23s
- `gates_passed=0`, `env_hits=0`
- log: `20260714T110032-62997d9b`

Visible behavior:
- countdown/race start happened, but it did **not** hold a stable hover.
- only one helper shot was printed before the run died, then later screenshots show the sim/menu state.
- no 5s hover hold observed.

Oscillation/failure note:
- This is a quick loss/stale-frame failure, not a usable hover sample. If there was oscillation, it happened too fast/early to estimate frequency visually.

## Attempt B
Command shape: same as A, but `control.att_rate.rate_p=1.2`.

Result:
- `aborted=True`, `abort_reason="max duration"`
- duration 45.00s
- `gates_passed=0`, `env_hits=0`
- log: `20260714T110643-02cf6940`

Visible behavior:
- countdown hold was legal (0 km/h at countdown).
- it **did not hover**. By ~5.8s it was moving at **49 km/h**.
- by ~28.6s it was moving/tumbling at **119 km/h**.
- It survived to max-duration, but as an uncontrolled/fast drift, not a stationary or level hover.

Oscillation/failure note:
- No clean hover oscillation frequency could be estimated; the vehicle appears to drift/accelerate away rather than oscillate around a fixed hover point.
- If there is an oscillatory component, it is masked by translational drift and camera tumbling.

## Attempt C
Command shape: same as A, but `control.att_rate.hover_thrust=0.22`.

Result:
- `aborted=True`, `abort_reason="environment collision (impulse=8.0)"`
- duration 25.54s
- `gates_passed=0`, `env_hits=1`
- log: `20260714T113457-36aa6178`

Visible behavior:
- countdown hold was legal (0 km/h at countdown).
- after GO it did **not** hold hover; by ~3.3s it was already at **67 km/h** and displaced down the corridor.
- later it collided/reset; the result reports an environment collision impulse 8.0.

Oscillation/failure note:
- No stable hover interval. The vehicle accelerates away and collides; no reliable oscillation frequency visible.

## Overall Phase 2f conclusion
No configuration in the prescribed ladder visibly held a hover for ~5s+.

- A: fast stale-frame failure (~15s), no hover.
- B: no crash/stale until max duration, but **not hover** — fast drift/tumble, 49→119 km/h.
- C: lower hover thrust still moves rapidly and ends in collision.

The best of the three in terms of run completion is **B** (`rate_p=1.2`, hover=0.30), but it is not a hover hold. The core problem is not only oscillation; there is still uncontrolled translation/attitude drift immediately after GO even in force-hover mode.

Suggested next work for cloud agent (not applied here):
1. Add/verify attitude-hold target is level in world/vehicle frame during `planner.force_hover`.
2. Further reduce thrust/ramp and/or apply active damping before any translational motion.
3. Add telemetry-based hover metrics to logs (altitude/attitude/speed estimate) so the operator does not rely only on screenshots for hover hold vs drift.

## Fixture contents
- `report.txt` — full console for attempts A/B/C.
- `screens/` — downscaled JPEGs (~800px/q80) for A/B/C visual evidence.
- `20260714T113457-36aa6178-*` — fresh attempt C flight log/result/params copied by collector (latest log). Attempt A/B logs remain in local `logs/` but were not collected automatically.
- `manifest.json` — collector manifest.
- Recording note: collector skipped `vision.aigprec` (~288 MB); upload to Drive if needed.
