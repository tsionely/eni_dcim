# Phase 1e — In-flight IMU verdict + real-vision fixtures

- **Date (local):** 2026-07-13 ~23:24-23:35 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385** (on-screen banner reads "AI GP 1.0.3385")
- **Code commit that flew:** `feba643...` (branch `main`, clean pull; see manifest.json).
- **Ground rules honored:** no edits to `src/`/`config/`/`simtools/`/`tests/`/`docs/`.
  Race start + screenshots + the nan-safe census were temp scripts in `%TEMP%` (NOT in repo).

## Single-instance verification
One sim only: `FlightSim.exe` **PID 56276** + engine `DCGame-Win64-Shipping.exe`
**PID 49312**. No orphans. Engine owns udp:14560 + udp:5601.

## 1. FLIGHT TEST — fly_once --max-duration 45 during a real race

- Pilot: connected, **armed**, "gyro bias calibrated over 114 samples: [0,0,0]".
- Result: `aborted=true, abort_reason="max duration", gates_passed=0, gate_clips=0,
  env_hits=0, duration_s=45.0`, loop clean (11250 ticks, 0 overruns).

### What the drone VISIBLY does on screen (screenshots every 2.5s)
**It never moves.** Full sequence (start pad camera, FLIGHT MODE ANGLE):
- t=0: start-gate countdown ("2"), **`THROTTLE DOWN please`** overlay, **0 km/h**, cam 20deg.
- t=16s (shot 6): identical view, still **0 km/h**, `THROTTLE DOWN please` still shown.
- t=32s (shot 11): identical view, still **0 km/h**, `THROTTLE DOWN please` still shown.
The race timer runs (00:00 -> 00:31.9) so the race IS live, but the drone **sits on the
start pad the entire time — no lift-off, no drift, no rotation, 0 km/h throughout.**

**Interpretation:** the sim persistently asks for `THROTTLE DOWN` — i.e. its arm/start
handshake wants the throttle brought to minimum first (to spin up / release the motors),
and the pilot's velocity backend never satisfies that gate, so the motors never engage and
the vehicle stays inert. This is why every race so far shows gates=0 and no motion.

## 2. MAVLink census during a race

`scripts/mavlink_census.py --duration 60` collected 13,402 msgs (4 (type,src) pairs) but
**CRASHED in its own summary**: `ValueError: inf or nan encountered in data`
(`statistics.pstdev`, line 84) — HIGHRES_IMU baro/mag fields are NaN. **Repo-script bug**
(reported below; not fixed here). I re-ran a **nan-safe ad-hoc census** (temp, not in repo)
during another race:

```
HIGHRES_IMU            src=(1,200) 115.4Hz
   LIVE:    time_usec, xacc, xgyro, yacc, ygyro, zacc
   frozen:  fields_updated, id, zgyro
   nan/inf: abs_pressure, diff_pressure, pressure_alt, temperature, xmag, ymag, zmag (all NaN)
ACTUATOR_OUTPUT_STATUS src=(1,200)  93.8Hz   LIVE: time_usec   frozen: active
HEARTBEAT              src=(1,200)  10.0Hz   LIVE: base_mode, system_status   frozen: autopilot/custom_mode/type/...
ENCAPSULATED_DATA      src=(1,200)   4.1Hz   frozen: seqnr
ENCAPSULATED_DATA payload type ids: {1: 184}
```

### KEY CORRECTION to the "frozen IMU" story
The IMU is **NOT fully frozen**. `xacc, yacc, zacc, xgyro, ygyro` all vary (std > 1e-5);
only **`zgyro` is pinned/frozen**. Every prior "FROZEN" verdict (phase1_check / phase1d)
keys its liveness check on **gyro_z**, which happens to be the single frozen axis — so the
verdict was misleading. Caveat: the drone did NOT visibly move this race, so the accel/gyro
variation is most likely small noise/jitter, not translation; a true IMU-responds-to-motion
verdict still needs a race where the **motors actually spin** (see the THROTTLE DOWN issue).

Also confirmed: **only 4 message types** on 14550 even during a race — no hidden live
telemetry source. `ENCAPSULATED_DATA` carries a single payload type id `1` at 4 Hz (its
`seqnr` field is frozen in the parsed header; the real content is in `.data`).

## 3. Vision fixture (sliced)
`slice_recording.py recordings/phase1-20260713T200814.aigprec fixtures_slice.aigprec
--start-s 10 --max-mb 40` -> **fixtures_slice.aigprec: 38.5 MB, 28,885 datagrams**
(committed in this fixture — first real vision data in the repo).

## 4. Recordings for Google Drive (too big to commit — human step)
- `recordings/phase1-20260713T200814.aigprec` — **~1.29 GB** (Phase-1d full race vision).
- `logs/20260713T202513-ea4b5f0c/vision.aigprec` — **~826 MB** (this cycle's fly_once flight).
Upload both to Drive `AI-GP Simulator/recordings`. I have no Drive connector in this session.

## 5. Suggested fixes (cloud agent — NOT applied here)
1. **THROTTLE DOWN handshake (top priority).** The vehicle never spins motors — the sim
   wants throttle-to-min to arm/start. The velocity/att-rate backend must perform the
   sim's start handshake (drop to min throttle, then ramp) before commanding climb.
   Until then every race is inert (gates=0, 0 km/h).
2. **Fix `mavlink_census.py`:** guard `statistics.pstdev` against NaN/inf (filter finite
   values); HIGHRES_IMU baro+mag are always NaN and crash the summary.
3. **IMU liveness must not key on gyro_z alone** (it's the frozen axis). Use accel or
   multi-axis; re-verify motion response once motors actually spin.

## 6. Files in this fixture
- `report.txt` — full console: preflight, fly_once flight + helper timestamps, both census runs (crash + nan-safe), slice.
- `fixtures_slice.aigprec` — 38.5 MB real race-vision slice (committable).
- `20260713T202513-ea4b5f0c-*` — THIS cycle's fly_once flight log (flight.jsonl 4.6 MB has IMU+state).
- `probe.json` — **STALE** (phase1b frame_probe; no frame_probe this cycle — IMU/motor issue makes it pointless).
- `manifest.json` — collector manifest; note `recording_skipped` (826 MB flight vision -> Drive).
