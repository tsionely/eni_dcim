# Phase 4c — R2-TRAINING chain (staged watchdog build)

- **Date (local):** 2026-07-16 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Flight code commit:** `80c6d44` — "Stage watchdog arming: imu at start, frame at GO"
- **SIM LOCK:** `C:\Temp\eni_dcim_sim.lock` held during the cycle.
- **Track:** R2-TRAINING, DEFAULT speeds, `--max-duration 300 --patch safety.flight_timeout_s=300`.
- **Result:** 3 VALID flights obtained; **0 gates passed**; each ends in an environment collision after a local re-approach.

## Operator fixes applied this cycle
1. **Row selection by TEXT, not fixed x,y.** The event-list order changed (old coords opened R1). New helper template-matches the on-screen label "AI-GP VIRTUAL QUALIFIER R2 - TRAINING" and clicks the matched row (match score ~1.000 on all counted flights).
2. **Visual R2 verification before a flight counts.** After clicking RACE, the helper screenshots the loaded scene and measures cyan-ribbon pixels; R2 (hangar + parked jets + glowing cyan ribbon) yields tens-to-hundreds of thousands of cyan px. A flight is only counted if verified R2.
   - This caught and REJECTED one attempt (`r2c_f_2`) where the R2 label matched at only 0.42 (event list not showing the R2 row / different screen) — skipped pre-flight, sim relaunched, retried.

## Smoke test (STEP 2)
`python scripts/fly_once.py --max-duration 60` on verified R2:
- THROTTLE_DOWN survived; the flight reached takeoff and flew ~27s (then a mid-flight `stale channels: frame`). It did **not** abort with stale channels before RACE — the launch-kill regression is fixed on `80c6d44`.

## Valid flights (all R2 verified)

### F1 — 20260716T164931-927a4c97
- Track verified: R2 (cyan px 141328).
- Result: `environment collision (impulse=11.5)`, dur 70.7s, gates 0, env 1.
- Telemetry: frames 21624, detections 10993, imu 8283.
- Phase runs: `hover -> takeoff -> approach -> commit -> retreat -> search -> approach -> search -> hover` (2 approaches, 1 commit, 1 retreat — local re-approach, no far-gate chase).
- Closest state 0.16m (LEFT/LOW, age 1.50s); closest direct 2.66m LEFT/HIGH.
- Where it ended: env collision at t+71.7s after a second local approach/search — no pass, no gate-index advance.

### F2 — 20260716T165306-927a4c97
- Track verified: R2 (cyan px 92960).
- Result: `environment collision (impulse=9.6)`, dur 61.4s, gates 0, env 1.
- Telemetry: frames 18546, detections 11898, imu 7229.
- Phase runs: `hover -> takeoff -> approach -> commit -> retreat -> search -> approach` (local re-approach).
- **Closest state 0.03m** (RIGHT/LOW, age 0.68s) — closest of the cycle; closest direct 0.90m center-x/HIGH.
- Where it ended: env collision at t+62.4s at close range to the gate region; no pass.

### F3 — 20260716T165535-927a4c97
- Track verified: R2 (cyan px 73312).
- Result: `environment collision (impulse=3.4)`, dur 59.9s, gates 0, env 1.
- Telemetry: frames 16973, detections 11018, imu 7053.
- Phase runs: `hover -> takeoff -> approach -> commit -> retreat -> approach -> hover` (local re-approach).
- Closest state 0.06m (LEFT/LOW, age 1.06s); closest direct 3.17m center-x/LOW.
- Where it ended: env collision at t+60.9s (two threat-2 impulses ~3.4/3.8) after the local re-approach; no pass.

## Verdicts for the cloud
- **Relock stays local (confirmed again):** every flight re-approaches the same gate after a miss (approach->commit->retreat->approach), with `max_active_gate_idx=0` and no far-gate chase.
- **Still not passing gate 1:** closest states are 0.03-0.16m but all end in an environment collision rather than an official pass; retries do not convert.
- **Retry altitude:** only 1 env hit per flight (vs phase4a's 8-35 ground scrapes), consistent with the retreat climb-bias holding altitude better across cycles.

## Operational anomaly + recommendation
- All three valid flights logged `THROTTLE_DOWN -> TAKEOFF: GO timeout -- proceeding` at ~t+46s. Cause: the helper clicks RACE **before** `fly_once` starts, so the pilot misses the live GO edge and proceeds on its 45s GO-timeout (still flies a real approach/commit/retreat, just delayed).
- Now that watchdogs are staged (imu at start, frame at GO), the cleaner sequence is to **start `fly_once` first, then click RACE** so the pilot catches the live GO. I kept RACE-before-fly_once this cycle because it reliably produced valid telemetry; flagging for the next cycle to capture true GO timing.

## Fixture contents
- `report.txt` — full console output (smoke + all attempts, incl. the rejected wrong-screen attempt).
- `phase4c_r2training_chain_analysis.txt` — per-flight phase runs, closest fixes, collisions, fsm.
- logs/results/params for the 3 valid flights.
- 3 commit-window recording slices (`*_r2c_commitwindow_slice.aigprec`, start-s 44, ~28.9 MB each) capturing approach/commit/collision.
- `screens/` — per flight: R2 verification frame + early/mid/late/end frames.
- Full recordings are 1.7-1.95 GB each (60-70s flights); far over the git limit — local / Drive candidates.
