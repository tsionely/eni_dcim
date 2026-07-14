# Phase 2a — First real controlled flight (att_rate pilot)

- **Date (local):** 2026-07-14 ~07:43-08:03 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Code commit:** `87f60e4...` (branch `main`, clean pull; see manifest.json)
- **Ground rules honored:** no edits to `src/`, `config/`, `simtools`, `tests`, `docs`.
  Race-start/screenshot helpers were temp files only.

## Single-instance verification
Exactly one simulator instance:
- `FlightSim.exe` PID 56276
- `DCGame-Win64-Shipping.exe` PID 49312
- engine owns `udp:14560` and `udp:5601`; no stray python before run.
- Config now defaults `control.backend = "att_rate"`, `hover_thrust = 0.5`.

## Probe 1: control_probe --modes H (hover-thrust ladder)
Ran during a real R1 race.

Console results:
- handshake: motors 0.05, no response
- thrust=0.40: accel_std=4.939, motors 0.40 -> RESPONSE
- thrust=0.45: accel_std=2.775, motors 0.45 -> RESPONSE
- thrust=0.50: accel_std=1.730, motors 0.50 -> RESPONSE
- thrust=0.55: accel_std=1.954, motors 0.55 -> RESPONSE
- thrust=0.60: accel_std=1.488, motors 0.60 -> RESPONSE
- thrust=0.65: accel_std=1.155, motors 0.65 -> RESPONSE

Visual observation:
- THROTTLE DOWN overlay cleared.
- The drone **lifted/moved already at the first 0.40 thrust step**; the ladder did not
  find a stable hover. By the 0.50-ish window, screenshot shows **71 km/h** and the drone
  already deep in the course. 0.65 keeps it moving fast.

Interpretation:
- Hover thrust is **below or near 0.40** in this ACRO/ANGLE launch condition, or the sim
  has strong forward/launch dynamics. `hover_thrust=0.5` is too high for "hover" in the
  launch corridor; it causes rapid acceleration rather than a stationary hold.

## Probe 2: control_probe --modes D (rate response)
Ran during another real R1 race.

Console results:
- handshake: motors 0.05, no response
- lift (thrust 0.6): accel_std=12.358, motors ~0.60 -> RESPONSE
- pitch-rate pulse: commanded `q=+0.40`, measured `q=-0.974`

Visual observation:
- THROTTLE DOWN overlay cleared.
- Drone moved; screenshot during the pulse shows **~18 km/h**.

Interpretation:
- Rate commands are honored, but **pitch-rate sign appears inverted**: commanded +q gives
  measured -q. This likely needs sign correction in the attitude-rate backend.

## Main event: fly_once --max-duration 60
Ran during a real R1 race with stage screenshots.

Result:
- `aborted=True`, `abort_reason="stale channels: frame"`, duration 46.09s
- `gates_passed=0`, `gate_clips=0`, `env_hits=0`
- 1 loop overrun / 11523 ticks
- fresh flight log: `20260714T045635-b9a568ab`

Visual stage account:
1. **Handshake / start:** first screenshot immediately after RACE shows **"Disqualified - Early Start 2321 ms"**. The drone is already moving/tumbling at **24 km/h** before a valid race start. This means the new pilot/handshake is releasing thrust too early relative to the sim's start window.
2. **Climb/takeoff:** the next screenshot is not a clean climb — the drone is already tumbling/rocketing at **114 km/h** with DSQ active.
3. **Search:** no stable search phase observed. The vehicle is uncontrolled/disqualified before a search behavior can be evaluated.
4. **Approach:** no meaningful approach phase. It never makes a controlled first-gate approach; gates_passed remains 0.
5. **End:** the run eventually aborts as `stale channels: frame`, likely after the race/vision stream ended or became invalid post-DSQ.

Milestone achieved:
- The att_rate pilot **does command real motion now**, unlike Phase 1e/1f fly_once, but it is not race-valid yet: it starts too early and accelerates/tumbles immediately.

## Key recommendations for cloud agent (not applied here)
1. **Race start timing / throttle handshake:** add a race-start gate that holds zero/min thrust until the RACE countdown/start is actually valid. The current pilot causes an **early start DSQ by 2321 ms**.
2. **Lower hover/thrust assumptions:** H ladder suggests 0.40 already moves strongly; `hover_thrust=0.5` is too high for controlled hover/launch. Need a lower initial thrust/ramp and/or attitude compensation.
3. **Pitch-rate sign correction:** D probe measured `q=-0.974` for commanded `q=+0.40`; likely sign inversion in pitch-rate command path.
4. **Stage sequencing:** only after fixing early start and sign/thrust should search/approach be judged. Current failure is before search.

## Fixture contents
- `report.txt` — full console for H, D, and main fly_once.
- `screens/` — representative screenshots: H thrust ladder, D pulse, and fly_once stages (early DSQ/tumble/end).
- `20260714T045635-b9a568ab-*` — fresh fly_once log/result/params from the main event.
- `manifest.json` — collector manifest.
- Recording note: collector skipped `vision.aigprec` (~722 MB); upload to Drive `AI-GP Simulator/recordings` if needed (human/connector step).
