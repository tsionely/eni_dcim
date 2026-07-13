# Agent Runbook — Local Sim Operator

Instructions for an AI agent (Sakana, Claude Code, or any other) running on the
**Windows machine where FlightSim.exe is installed**. You are the *sim
operator* half of a two-agent team:

- **You (local agent)**: operate the real simulator, run flights, collect
  artifacts, commit them to this repo.
- **Cloud agent**: analyzes your artifacts, develops/fixes/upgrades the pilot
  code in `src/`, pushes code changes. It cannot reach the simulator — your
  artifacts are its only window into the real sim.

All coordination happens through git on branch `main`.

## Ground rules

1. **Never edit `src/`, `simtools/`, `tests/`, `docs/` or `config/`** — code
   and parameter changes are the cloud agent's job. If you believe a code
   change is needed, describe it in your run report instead.
2. **Only add files under `fixtures/`** (created by `scripts/collect_artifacts.py`).
3. Commit messages start with `[sim-run]`, e.g. `[sim-run] phase1 vs sim v1.0.3385`.
4. Always `git pull` before running — the cloud agent may have pushed fixes
   for issues found in your previous run.
5. Recording files larger than ~50 MB: do NOT commit; upload to the Google
   Drive folder `AI-GP Simulator/recordings` instead and mention the filename
   in your report.

## One-time setup

```powershell
cd $HOME\Documents
git clone https://github.com/tsionely/eni_dcim.git
cd eni_dcim
pip install -r requirements.txt
```

## Standard run cycle

1. `git pull`
2. Launch `FlightSim.exe` (latest sim version), log in, enter the qualifier
   so the drone is waiting on the start point.
3. Run the task for the current phase (see below), capturing console output:

   ```powershell
   python scripts/phase1_check.py --duration 60 2>&1 | Tee-Object -FilePath phase1_report.txt
   ```

4. Package the artifacts:

   ```powershell
   python scripts/collect_artifacts.py --label phase1 --report phase1_report.txt
   ```

5. Review the created `fixtures/<timestamp>-<label>/` folder, add your own
   `notes.md` there (what you observed: sim version, track, anomalies,
   suggested code changes).
6. Commit and push:

   ```powershell
   git add fixtures
   git commit -m "[sim-run] phase1 vs sim v<version>"
   git push
   ```

## CURRENT TASK: Phase 1e — in-flight IMU verdict + real-vision fixtures

Phase-1d analysis (cloud side): vision on 5600 WORKS during an active race
(20k frames @224Hz, clean decode). The "frozen" IMU now reads mean≈0 with a
single clean instance — exactly what a PARKED drone with a noise-free sim IMU
looks like. The earlier absurd constants came from the orphan/menu states.
Remaining question: does the IMU respond to actual MOTION? Nobody has flown
the drone during a race yet.

Run this cycle:

1. `git pull`. Verify a single engine process (as in 1d).
2. **The flight test**: start
   `python scripts/fly_once.py --max-duration 45 2>&1 | Tee-Object -FilePath phase1e_report.txt`
   and START A REAL RACE (your RACE automation) right as it connects. The
   pilot will arm and try to climb. Note in notes.md what the drone VISIBLY
   does on screen (climbs? sits still? drifts?) — that observation is as
   valuable as the logs.
3. `python scripts/mavlink_census.py --duration 60` (new) during another race
   window — it inventories EVERY message type with per-field value liveness,
   in case live telemetry hides somewhere we don't parse. Append output to
   the report.
4. Slice the big Phase-1d recording into a committable fixture (new tool):
   `python scripts/slice_recording.py recordings/phase1-20260713T200814.aigprec fixtures_slice.aigprec --start-s 10 --max-mb 40`
   and place `fixtures_slice.aigprec` in your fixture folder. (The full
   1.29 GB file still goes to Drive — human step, flagged for the user.)
5. Collect with `--label phase1e`, notes.md (include the visual observation!),
   commit `[sim-run] phase1e in-flight IMU + vision fixtures`, push.

Note: phase1_check now caps its recording at 200 MB by default
(--record-cap-mb) — race-rate vision is ~20 MB/s.

## PREVIOUS: Phase 1d — clean single-instance race validation

Phase-1c analysis (cloud side) reframed everything:

- 14560/5601 never answer pokes (idle or racing) → they are most likely the
  sim's own OUTBOUND source sockets (14560 -> client:14550 telemetry,
  5601 -> client:5600 vision), not services to connect to. The connect-mode
  hypothesis is dropped; the classic topology stands.
- Every earlier "frozen telemetry" measurement was taken either with the
  ORPHANED second sim process still alive, or with the sim at the menu/idle.
  Frozen values are plausibly just idle/menu placeholder telemetry.
- The one measurement never taken: 14550/5600 liveness DURING an active race
  with exactly ONE sim process. That is this cycle.

Run this cycle:

1. `git pull`. Verify exactly ONE engine process:
   `Get-Process | Where-Object {$_.Name -match 'FlightSim|DCGame'}` — kill
   orphans, document PIDs in notes.md.
2. Start `python scripts/phase1_check.py --duration 90 2>&1 | Tee-Object -FilePath phase1d_report.txt`
   and WHILE IT RUNS drive the sim into a real active race (your RACE
   automation). The check now prints a per-10s liveness window
   (`imu=... (ALIVE/frozen, std=...) frames+=N race_started=...`) — the
   idle->racing transition will be visible live. Note in notes.md the exact
   moment (which 10s window) the race became active.
3. If frames appear: let it finish — the recording it writes is our first
   real vision fixture. If IMU goes ALIVE too: rerun
   `python scripts/frame_probe.py` (bias-aware v2) for a clean frame verdict.
4. If vision is STILL silent during a clean single-instance race: capture
   where the sim's 5601 socket sends:
   `pktmon filter add -p 5601; pktmon start --etw -m real-time -c 30` (admin),
   stop with `pktmon stop`, note destination IP:port seen.
5. `python scripts/collect_artifacts.py --label phase1d --report phase1d_report.txt`
   (it now skips stale artifacts from previous cycles), add notes.md, commit
   `[sim-run] phase1d clean race validation`, push.

## Phase tasks (general roadmap)

The full roadmap with acceptance criteria is in `docs/05-avney-derech.md`
(Hebrew). Summary of what to run per phase:

| Phase | Commands | Success signal |
|---|---|---|
| **1 — connectivity** | `scripts/phase1_check.py --duration 60`, then `scripts/fly_once.py --max-duration 20`, then `scripts/frame_probe.py` | `PHASE-1 CHECK PASSED`; frame_probe prints body_x vs body_y verdict |
| 2 — hover | `scripts/fly_once.py --max-duration 40` ×10 | 10/10 no-collision hovers |
| 3 — one gate | `scripts/fly_once.py --max-duration 60` ×10 on a single-gate track | ≥8/10 `gates_passed >= 1` |
| 4 — full track | same, full track | ≥7/10 `finished: true` |
| 5 — tuning | `scripts/run_campaign.py --flights 20 --optimizer cem --sim real` | campaign completes unattended |

After each run, collect + push artifacts even on failure — failures are the
most valuable data.

## What the artifacts contain

`scripts/collect_artifacts.py` copies into `fixtures/<timestamp>-<label>/`:

- `report.txt` — the console output you captured
- `probe.json` — frame_probe IMU samples (if present)
- latest flight log dir: `flight.jsonl`, `result.json`, `params.json`
- `recording.zip` — the newest `.aigprec` vision recording (if ≤ 50 MB)
- `manifest.json` — what was collected, sizes, and the git commit of the code
  that flew
