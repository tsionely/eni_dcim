# Phase 2b — Race-legal takeoff + rate-sign calibration

- **Date (local):** 2026-07-14 ~08:35-10:43 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Code commit:** `4f2d90b...` (branch `main`, clean pull; see manifest.json)
- **Ground rules honored:** no edits to `src/`, `config`, `simtools`, `tests`, or `docs`.
  All race-start and screenshot helpers were temp files in `%TEMP%` only.

## Single-instance verification
Exactly one simulator instance:
- `FlightSim.exe` PID 56276
- `DCGame-Win64-Shipping.exe` PID 49312
- engine owns `udp:14560` and `udp:5601`; no stray python at preflight.

## 1. control_probe --modes D — 3-axis rate sign calibration
Probe reset/armed and **waited for GO**. I started R1 while it was waiting; it printed `GO!`.

Measured signs:
| Axis command | Commanded | Measured | Sign conclusion |
|---|---:|---:|---|
| roll p | `+0.40` | `p=-0.970` | inverted -> `rate_sign_roll=-1` |
| pitch q | `+0.40` | `q=-0.962` | inverted -> `rate_sign_pitch=-1` |
| yaw r | `+0.40` | `r=-0.850` | inverted -> `rate_sign_yaw=-1` |

Other D observations:
- throttle-down handshake: motors 0.05, no response.
- lift thrust 0.6: accel_std=10.549, motors 0.60 -> RESPONSE.
- THROTTLE DOWN overlay cleared; drone visibly moved during lift/pulses.

## 2. control_probe --modes H — clean hover ladder
Probe reset/armed and **waited for GO**. I started R1 while it was waiting; it printed `GO!`.

Console ladder:
- thrust=0.40: accel_std=4.841, motors 0.40 -> RESPONSE
- thrust=0.45: accel_std=3.240, motors 0.45 -> RESPONSE
- thrust=0.50: accel_std=1.719, motors 0.50 -> RESPONSE
- thrust=0.55: accel_std=1.790, motors 0.55 -> RESPONSE
- thrust=0.60: accel_std=1.416, motors 0.60 -> RESPONSE
- thrust=0.65: accel_std=1.397, motors 0.65 -> RESPONSE

Visual ladder observation:
- THROTTLE DOWN overlay cleared.
- The drone was already moving at the first 0.40 step. It did **not** find a calm stationary hover.
- By the later steps it was still moving down the corridor (screens included as downscaled JPEGs).

Hover result used for fly_once patch:
- Lowest tested thrust with lift/motion is **0.40**. I used `control.att_rate.hover_thrust=0.40` in the main event because it is the lowest measured bracket.
- Caveat: true hover may be **below 0.40**, because 0.40 already produces motion.

## 3. Main event — patched fly_once --max-duration 60
Command patches applied:
```
--patch control.att_rate.rate_sign_roll=-1
--patch control.att_rate.rate_sign_pitch=-1
--patch control.att_rate.rate_sign_yaw=-1
--patch control.att_rate.hover_thrust=0.40
```

Result:
- `aborted=True`, `abort_reason="stale channels: frame"`
- duration 41.58s
- `gates_passed=0`, `gate_clips=0`, `env_hits=0`
- 0 loop overruns
- fresh log: `20260714T072732-8ff375f3`

### Stage-by-stage visual account
1. **Countdown hold:** FAILED. The first captured frame already shows
   **`Disqualified - Early Start 2688 ms`** and the drone moving at **49 km/h**.
   So even with the measured signs and `hover_thrust=0.40`, the pilot still releases/moves
   before the sim start is legal.
2. **Climb:** no clean climb. Next frames show the drone tumbling/rolling through the course
   at ~36-49 km/h, DSQ active.
3. **Search:** no stable search spin/hover. The vehicle is already disqualified and tumbling;
   the camera is mostly angled at walls/ceiling/void.
4. **Approach:** no meaningful gate approach. By later screenshots the sim has returned to
   the menu/event list after DSQ / stale stream; no gate was passed.

## Main conclusion for cloud agent
- **All rate signs should be -1** for this sim/control path.
- `hover_thrust=0.40` is still too much / not a legal launch setting; real hover may be below 0.40.
- The largest remaining blocker is **race-start legality**: the FSM still moves before the sim GO window is valid. `control_probe` correctly waits for GO, but `fly_once` still early-starts by 2688 ms in this run.
- After race-start timing is fixed, the next focus should be low-thrust ramp / true hover below 0.40, then only then evaluate search and approach.

## Fixture contents
- `report.txt` — full console for D, H, and patched main fly_once.
- `screens/` — downscaled JPEGs (~800px wide, quality 80) for D, H, and fly_once stages.
- `20260714T072732-8ff375f3-*` — fresh patched fly_once log/result/params.
- `manifest.json` — collector manifest.
- Recording note: collector skipped `vision.aigprec` (~606 MB); upload to Drive if needed (human/connector step).
