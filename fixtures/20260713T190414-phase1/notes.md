# Phase 1 — Sim Operator Notes

- **Date (local):** 2026-07-13 ~22:01 Asia/Jerusalem (report timestamps are UTC)
- **Sim version:** AI-GP Simulator **v1.0.3385**
  - Executable: `C:\Users\tsion\Downloads\AI-GP Simulator v1.0.3385 (1)\AIGP_3385\FlightSim.exe`
- **Code commit that flew:** `f8d7041038d0586e4d2b7c7515e9fe83cc0cadbb` (branch `main`, clean `git pull` before run)
- **Runner:** scripts executed exactly as per AGENTS.md; no `src/`, `config/`, `simtools/`, `tests/`, or `docs/` files were modified.

## Overall verdict

**PHASE-1 CHECK FAILED** — MAVLink/telemetry path is fully healthy, but the vision
stream produced **zero frames** and the recording is empty.

## phase1_check.py --duration 60

| stream | count | rate | max gap |
|---|---|---|---|
| imu | 6832 | 113.9 Hz | 11 ms |
| frame | 0 | 0.0 Hz | 0 ms |
| race | 480 | 8.0 Hz | 253 ms |
| heartbeat | 1192 | 19.9 Hz | 103 ms |
| actuator | 5529 | 92.1 Hz | 14 ms |

- vision decode: ok=0 failed=0 pending_partials=0
- timesync: synced=True, std=0.24 ms (well under 5 ms limit)
- race status: active_gate_index=0, started=False, finished=False
- recording: `recordings/phase1-20260713T190142.aigprec` (0 datagrams)

Acceptance: PASS telemetry-window, PASS IMU flowing, **FAIL frames decoded**,
PASS race status, PASS timesync std, **FAIL recording non-empty**.

## fly_once.py --max-duration 20

- Result: `aborted=true`, `abort_reason="max duration"`, `gates_passed=0`,
  `gate_clips=0`, `env_hits=0`, `duration_s=20.0`.
- Loop health excellent: 5000 ticks, 0 overruns, max_late_us=0.
- Interpretation: with no vision frames the pilot never acquires a gate, so it
  runs until the duration cap. Consistent with the vision-stream failure above.
- Flight log: `20260713T190311-db4c58dd/` (flight.jsonl 6743 lines).

## frame_probe.py

- step-phase mean specific force: **body_x=-2.62, body_y=-12.36**
- |body_y| is dominant -> the sim applied the post-yaw `+x` command in
  **LOCAL_NED**, i.e. it did **not** honor MAV_FRAME_BODY_NED.
- 341 IMU samples saved to `logs/frame_probe/probe.json`.

## Anomalies / environment

- Two `FlightSim.exe` instances were present at start (one pre-existing since
  ~19:57, plus one I launched). I stopped the duplicate I started and ran
  against the single remaining instance to avoid double-streaming on
  udp:14550 / udp:5600.
- The drone was at the pre-race start point the whole time
  (`started=False`); the operator was not able to enter/advance the qualifier
  into a running race, which may be why no camera frames were emitted.

## Suggested code/config changes (for the cloud agent — NOT applied here)

1. **Vision frame drought (top priority).** No frames decoded on udp:5600 while
   MAVLink is perfect. Possible causes to investigate: (a) the sim only emits
   the camera stream once the race is `started` (this run was passive/pre-race),
   (b) vision port/binding change in v1.0.3385, or (c) local firewall on UDP
   5600. If the stream is race-gated, Phase-1 acceptance for "frames decoded"
   may need the drone actually racing, or a probe that starts the race.
2. **Velocity frame = NED, not body.** frame_probe shows LOCAL_NED behavior in
   v1.0.3385. `config/params_default.json` currently has
   `control.velocity.frame="body"`; consider `"ned"` with yaw compensation
   (docs/02). Not changed here per the ground rules.

## Files in this fixture
- `report.txt` — full captured console output (all three scripts)
- `probe.json` — frame_probe IMU samples
- `20260713T190311-db4c58dd-{flight.jsonl,result.json,params.json}` — fly_once log
- `recording.zip` — empty vision recording (0 datagrams; kept for completeness)
- `manifest.json` — collector manifest
