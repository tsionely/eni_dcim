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

## CURRENT TASK: Phase 1b — vision diagnosis + frame re-probe

Your Phase-1 fixtures (`fixtures/20260713T190414-phase1/`) were analyzed.
Findings: MAVLink healthy; the race DID start during the armed flight yet
zero vision datagrams reached udp:5600; the frame_probe verdict was
unreliable (the drone was spinning at -1 rad/s during the step). New
diagnostic tools were pushed — run this cycle:

1. `git pull`, launch the sim, enter the qualifier as usual.
2. Vision diagnosis (capture all output with Tee-Object):
   - `python scripts/vision_probe.py --duration 30` (passive port scan 5595-5615)
   - `python scripts/vision_probe.py --duration 30 --arm` (same, during an armed flight)
   - If both report no traffic: run `netstat -ano | findstr 5600`; search the
     sim install dir:
     `Get-ChildItem <simdir> -Recurse -Include *.ini,*.json,*.cfg | Select-String -Pattern '5600|[Vv]ideo|[Ss]tream'`
     and check Windows Defender Firewall inbound rules for python.exe (UDP).
     Record everything you find in notes.md.
   - Note: during your own R1 run you captured 4 frames with your external
     capture tooling — state clearly in notes.md HOW those were captured
     (UDP stream? screen capture?) and under what sim state (race running?).
3. Frame re-probe with the rewritten `scripts/frame_probe.py` (now records
   all phases, checks for uncommanded spin, and prints a world_yaw_offset
   estimate). If it warns the verdict is unreliable, note the spin behavior.
4. `python scripts/collect_artifacts.py --label phase1b --report <report>`,
   add notes.md, commit `[sim-run] phase1b vision+frame diagnosis`, push.

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
