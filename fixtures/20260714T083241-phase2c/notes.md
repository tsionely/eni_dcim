# Phase 2c — First legal takeoff attempt

- **Date (local):** 2026-07-14 ~11:09-11:32 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Code commit:** `4506a78...` (branch `main`, clean pull; see manifest.json)
- **Ground rules honored:** no edits to `src/`, `config`, `simtools`, `tests`, or `docs`.
  Race-start/screenshot helpers were temp files in `%TEMP%` only.

## Single-instance verification
Exactly one simulator instance:
- `FlightSim.exe` PID 56276
- `DCGame-Win64-Shipping.exe` PID 49312
- engine owns `udp:14560` and `udp:5601`
- defaults now have `rate_sign_roll/pitch/yaw=-1` and `hover_thrust=0.5`

## 1. control_probe --modes H (new 0.25-0.50 ladder)
Probe reset/armed, waited for GO, and I started R1 while it was waiting. It printed `GO!`.

Console ladder:
- `thrust=0.25`: accel_std=1.507, motor_span=0.207, **collisions=83**, motors ~0.25 -> RESPONSE
- `thrust=0.30`: accel_std=1.259, collisions=0, motors 0.30 -> RESPONSE
- `thrust=0.35`: accel_std=2.015, collisions=0, motors 0.35 -> RESPONSE
- `thrust=0.40`: accel_std=2.975, collisions=0, motors 0.40 -> RESPONSE
- `thrust=0.45`: accel_std=2.045, collisions=0, motors 0.45 -> RESPONSE
- `thrust=0.50`: accel_std=1.604, collisions=0, motors 0.50 -> RESPONSE

Visual observation:
- THROTTLE DOWN overlay cleared.
- At `0.25`, the sim quickly returned to/menu state in the screenshots and collision count was huge (83).
  This looks like ground contact/skittering or a reset, not a clean hover.
- After the `0.25` collision/reset, later ladder screenshots are contaminated by being at/near menu state,
  so the ladder does **not** cleanly bracket hover.

Hover bracket conclusion:
- Highest no-lift step: **not found** in tested range (even 0.25 produced a response).
- Lowest lift/response step: **0.25**, but it is collision-heavy and not usable.
- I selected `hover_thrust=0.30` for the main event as the lowest non-collision ladder step, with the caveat
  that true stable hover is still unresolved and may be <0.25 or needs a gentler ramp.

## 2. Main event: fly_once --max-duration 60 --patch control.att_rate.hover_thrust=0.30
No sign patches were used; signs are defaults now.

Result:
- `aborted=True`, `abort_reason="stale channels: frame"`
- duration 42.08s
- `gates_passed=0`, `gate_clips=0`, `env_hits=0`
- 0 loop overruns
- fresh log: `20260714T081945-bb5494d6`

FSM/log facts:
- `ARMING -> THROTTLE_DOWN`
- `THROTTLE_DOWN -> TAKEOFF` with reason `race GO`
- `TAKEOFF -> RACING` with reason `takeoff complete`
- `RACING -> ABORTED` with reason `stale channels: frame`
This confirms the scheduled-start GO gate worked from the FSM side.

## Stage-by-stage visual account
1. **Countdown hold:** SUCCESS. First screenshot shows countdown `2`, speed **0 km/h**, no DSQ. This is a major improvement over Phase 2b.
2. **Lift / climb at GO:** FAIL / unstable. By ~3.2s after race start the camera is already tumbling, speed **100 km/h**. No clean hover/climb.
3. **Search:** no stable search spin. By ~13s, the drone is still tumbling/fast, speed **118 km/h**, with no controlled attitude or search behavior.
4. **Approach:** no meaningful gate-1 approach. Later screenshots show the sim back at menu/event list (one also captured the Windows Start menu/desktop after sim focus was lost). `gates_passed=0`.

## Main conclusion
Phase 2c achieved the first **legal countdown hold**: no early-start DSQ, and the FSM waits until scheduled GO. However, takeoff is still too aggressive/unstable: the drone rockets/tumbles immediately after GO and the run aborts when the vision stream becomes stale.

Likely next work for cloud agent:
1. Lower/reshape takeoff thrust/ramp. `hover_thrust=0.30` is still too aggressive in the current takeoff controller.
2. Add an explicit low-thrust ramp / attitude stabilization before forward/search commands.
3. Re-run H ladder in a way that isolates each thrust step in a fresh race, because the current single-run ladder becomes contaminated after 0.25 collision/reset.

## Fixture contents
- `report.txt` — console for H ladder and patched fly_once.
- `screens/` — downscaled JPEGs (~800px wide, q80) for H ladder and fly_once stages.
- `20260714T081945-bb5494d6-*` — fresh patched fly_once log/result/params.
- `manifest.json` — collector manifest.
- Recording note: collector skipped `vision.aigprec` (~519 MB); upload to Drive if needed (human/connector step).
