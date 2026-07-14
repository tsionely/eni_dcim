# Phase 1f — Control-authority probe

- **Date (local):** 2026-07-14 ~07:00-07:20 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385** (on-screen banner)
- **Code commit:** `0f2ca0d...` (branch `main`, clean pull; see manifest.json)
- **Ground rules honored:** no edits to `src/` / `config` / `simtools` / `tests` / `docs`.
  Race start and screenshots used temp helper scripts in `%TEMP%` only.

## Single-instance check
Exactly one simulator instance before probing:
- `FlightSim.exe` PID **56276**
- `DCGame-Win64-Shipping.exe` PID **49312**
- engine owns `udp:14560` and `udp:5601`
- no stray python clients before the run

## How I ran the probe
I restarted real R1 before each mode (`A`, `B`, `C`) to avoid ambiguity, because
`control_probe.py` calls `sim_reset()` per mode. This worked: after each restart,
the screenshots show a live race timer / race HUD, and the probe owned the 14550/5600
client ports.

## Per-mode operator observations

### Mode A — SET_ATTITUDE_TARGET thrust step
Console:
- throttle-down handshake: `accel_std=0.000`, motors all `0.05`, `no response`
- attitude thrust step: `accel_std=11.350`, `motor_span=0.600`, motors all `0.65`, `RESPONSE`

Visual observation:
- **THROTTLE DOWN overlay cleared** before/at the test window.
- **Drone visibly moved strongly.** Start screenshot: 0 km/h at the gate. Mid screenshot:
  **64 km/h**, camera surging forward toward/through the gate. Late screenshot: still moving
  fast (**~57 km/h**) with the start gate already out of view.
- No collision was reported by the probe.

Verdict: **Mode A works / has control authority.**

### Mode B — SET_POSITION_TARGET velocity climb
Console:
- throttle-down handshake: `accel_std=0.000`, motors all `0.05`, `no response`
- velocity climb: `accel_std=0.000`, `motor_span=0.000`, motors all `0.05`, `no response`

Visual observation:
- **THROTTLE DOWN overlay cleared**, but the drone stayed on the start pad.
- **No visible movement.** Mid screenshot: race timer active, `FLIGHT MODE ACRO`, speed **0 km/h**,
  same view of the gate/start pad.

Verdict: **Mode B does not work** (velocity commands appear ignored / not converted to motor output).

### Mode C — SET_ACTUATOR_CONTROL motor command
Console:
- throttle-down handshake: `accel_std=0.000`, motors all `0.05`, `no response`
- motor command: `accel_std=15.361`, `motor_span=0.650`, motors all `0.70`, `RESPONSE`

Visual observation:
- **THROTTLE DOWN overlay cleared**.
- **Drone visibly moved very strongly.** Mid screenshot: **88 km/h** and the scene/gate rapidly
  moving out of frame.
- No collision was reported by the probe.

Verdict: **Mode C works / has control authority.**

## Required follow-up fly_once (because A/C moved)
Ran `python scripts/fly_once.py --max-duration 45` immediately after the probe.

Result:
- `aborted=True`, `abort_reason="stale channels: frame"`, `duration_s=43.8`
- `gates_passed=0`, `gate_clips=0`, `env_hits=0`
- loop mostly clean: 10950 ticks, 3 overruns, max late 3314us

Visual observation for fly_once:
- **THROTTLE DOWN overlay remained visible** during the live race.
- **Drone stayed stationary at 0 km/h**, same as the Phase 1e fly_once observation.
- So the pilot still does not use the working interface/handshake correctly, even though
  the direct control probe proves that Mode A and Mode C can move the drone.

## Key conclusions for the cloud agent
1. **Working interfaces:** attitude-thrust (`SET_ATTITUDE_TARGET`) and direct motor
   (`SET_ACTUATOR_CONTROL`) both move the drone after throttle-down handshake. These are the
   viable control paths.
2. **Non-working interface:** velocity (`SET_POSITION_TARGET`) has no visible or telemetry response;
   motors remain at 0.05.
3. **Current pilot problem:** `fly_once` still gets stuck under `THROTTLE DOWN please` and never moves.
   The backend/FSM should switch away from velocity control and use the working attitude-thrust or
   motor command path with the proven throttle-down handshake.
4. `control_probe.py`'s direct modes are ground truth: the sim does accept control, so the problem is
   not the sim state; it is pilot command path / startup sequencing.

## Fixture contents
- `report.txt` — full console for modes A/B/C and the required fly_once.
- `screens/` — representative screenshots for A/B/C/fly_once visual truth.
- `20260714T041536-88e6e576-*` — fresh fly_once log/result/params from the required run.
- `manifest.json` — collector manifest.
- `recording` note: collector skipped `vision.aigprec` (~716 MB) from fly_once; upload to Drive
  `AI-GP Simulator/recordings` if needed (human/connector step).
