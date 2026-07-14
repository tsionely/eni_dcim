# Agent Runbook — Local Agents

Three local roles are defined. State clearly in your commit messages which
role you act as. All coordinate with the cloud agent through git on `main`.

- **SIM OPERATOR** (Sakana): operates the simulator, runs probes and
  flights, collects fixtures. The operator runbook is the last section.
- **DATA ANALYST** (Cursor): works ONLY on recorded data — see below. Never
  runs the simulator while the operator is mid-cycle; never edits code,
  config, docs, or the operator's fixtures.
- **QA & MOCK-TUNER** (Codex): tests and tunes against the MOCK sim only —
  see below. Never touches the real simulator or the operator's cycle.

## QA & MOCK-TUNER role (Codex)

Mission: use spare CPU between real-sim cycles to (a) verify the pilot on
Windows and (b) pre-tune the att_rate cascade with mock campaigns — dozens of
flights per hour vs. one real race at a time.

Ground rules: write ONLY under `tuning/` (create it) and never modify
`src/`, `config/`, `simtools/`, `tests/`, `docs/`, or `fixtures/`. Runtime
parameter experiments go through `--patch` / campaign bounds, never config
edits. Commit prefix `[tuning]`. Suggested code/test changes are written as
unified diffs into `tuning/proposals/*.diff` + rationale — the cloud agent
reviews and applies.

Environment notes (from your first CI run):
- Your checkout lives under OneDrive — the `WinError 5` temp failures are
  OneDrive/AV file locking, not code bugs. **Re-clone OUTSIDE OneDrive**
  (e.g. `C:\dev\eni_dcim`) and run pytest with an explicit temp dir:
  `python -m pytest tests -q --basetemp=C:\Temp\pytest-eni`.
- Your commit af88a69 never reached origin — remember `git push` after
  committing (rebase if rejected, per the operator's flow).

Standing tasks:
1. **Windows verification**: `python -m pytest tests -q --basetemp=C:\Temp\pytest-eni`
   after every `git pull` of a cloud commit; report failures with full output
   in `tuning/windows-ci.md` (append per commit hash). The suite has only
   ever run on Linux — you are our Windows CI.
2. **Mock tuning campaigns**:
   `python scripts/run_campaign.py --flights 40 --optimizer cem --sim mock`
   (repeat with different seeds/optimizers). Copy `logs/results.sqlite` and a
   summary (best params per campaign, score progression) into
   `tuning/campaigns/<date>/`. Focus bounds: the att_rate gains + approach
   params in `DEFAULT_TUNE_BOUNDS` (src/aigp/main.py).
3. **Robustness hunts**: long mock runs hunting flakes — hover 10x
   (`aigp --mode mock` repeatedly), report any abort that is not
   "max duration" with its flight log attached.
4. **Review reports** (optional, read-only): findings on the pilot code go in
   `tuning/review-<date>.md` — flag, don't fix.

## DATA ANALYST role (Cursor)

Mission: exploit the large local recordings that never reach the cloud agent
(logs/*/vision.aigprec and recordings/*.aigprec, 0.6-1.3 GB each — the repo
only carries small slices).

Ground rules: write ONLY under `analysis/` (create it; it is committed) and
`fixtures/` (via `scripts/collect_artifacts.py` conventions). Commit prefix
`[analysis]`. Read-only everywhere else. Keep every committed file < 50 MB.

Standing tasks (in priority order, redone as new recordings appear):
1. **Detector evaluation at scale**: run the repo detector
   (`aigp.perception.gate_detector_hsv` via `aigp.main --mode replay` or your
   own harness reusing `ChunkAssembler`) over EVERY local recording; report
   per-recording: frames, detection rate, PnP-solve rate, distance/center
   stability, and — most valuable — save the N *hardest* frames (missed or
   low-confidence) as downscaled JPEGs under `analysis/hard_frames/`.
2. **Interesting-moment slices**: extract 20-40 MB slices around events
   (race GO, gate approaches, DSQ moments) with `scripts/slice_recording.py`
   into `fixtures/` with a manifest note of what each slice shows.
3. **Flight kinematics reports**: from `flight.jsonl` logs, plot/report IMU,
   setpoints vs estimates, FSM timelines (reuse `aigp.telemetry.plots`);
   write findings to `analysis/<date>-<topic>.md`.
4. **Cross-checks**: anything suspicious (frame gaps, clock jumps, decode
   failures) — document with data in your report; do NOT fix code, flag it.

# SIM OPERATOR Runbook

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

## CURRENT TASK: Phase 2d — the decisive sign experiment

Phase-2c: countdown hold WORKED (no DSQ — milestone!), but the drone still
tumbles right after liftoff even with the -1 command signs. That is strong
evidence the -1-on-commands theory is wrong: if commands were the inverted
side, flipping them should have stabilized the loop. New hypothesis: the GYRO
is the inverted party (probe D measured the *gyro*, which would read inverted
even for correctly-executed commands), and flipping commands re-created
positive feedback.

Probe mode E settles it without screenshots or estimators: open-loop RAW
pitch pulse, then a quiet hover window where the ACCELEROMETER (gravity
direction) reveals the true physical rotation. It prints the verdict.

Run this cycle:

1. `git pull`. Single engine instance.
2. `python scripts/control_probe.py --modes E` (it waits for GO — start a
   race). Copy the printed "open-loop verdict" block verbatim into the
   report. Run it TWICE for confidence.
3. Nothing else — no fly_once this cycle; the cloud agent flips the correct
   sign (command vs gyro parsing) based on E and only then flying continues.
4. Collect with `--label phase2d`, push.

## PREVIOUS: Phase 2c — the first legal takeoff

Phase-2b analysis (cloud side) — both blockers decoded from your data:

- The DSQ mystery is SOLVED: race_start_boot_time_ms updates at COUNTDOWN
  start with a *future* timestamp (your log: start=9,367,936 while the clock
  read 9,365,155 — exactly the 2,688ms of the DSQ). The pilot launched on the
  change instead of waiting for the scheduled moment. Fixed: GO now requires
  the sim clock to REACH the scheduled start.
- Your 3-axis sign table (all -1) is now the CONFIG DEFAULT, and the mock
  mirrors the inverted convention — no --patch needed for signs anymore.
- Probe H ladder extended down to 0.25-0.50 (you saw lift already at 0.40).

Run this cycle:

1. `git pull`. Single engine instance.
2. `python scripts/control_probe.py --modes H` — find the lowest thrust step
   that lifts and the highest that doesn't; note both.
3. Main event: `python scripts/fly_once.py --max-duration 60 --patch control.att_rate.hover_thrust=<your bracket>`
   (no sign patches needed). Start the race when prompted-by-waiting; the
   pilot should now HOLD through the countdown and lift at the actual GO.
   Describe per stage: countdown hold (no DSQ?), climb, search spin,
   approach. Screenshots downscaled as before.
4. Collect with `--label phase2c`, notes.md, commit, push.

## PREVIOUS: Phase 2b — race-legal takeoff + rate-sign calibration

Phase-2a analysis (cloud side): the pilot MOVES now, and the three failure
modes are all addressed:

- Early-start DSQ: the FSM now holds zero thrust in THROTTLE_DOWN until the
  race actually starts (a CHANGE in race_start_boot_time_ms; the flag itself
  is sticky). control_probe also waits for GO before each mode now.
- Inverted pitch-rate: per-axis sign params exist
  (control.att_rate.rate_sign_roll/pitch/yaw, default +1). Mode D now pulses
  ALL THREE axes to pin the convention down.
- hover_thrust: probe H data was contaminated by the tumble; re-measure.
- NEW: `--patch KEY=VALUE` on fly_once/aigp lets you override params per run
  WITHOUT editing config (allowed under the ground rules).

Run this cycle:

1. `git pull`. Single engine instance.
2. `python scripts/control_probe.py --modes D` — it resets, arms, WAITS FOR
   GO (start the race when prompted), lifts, then pulses roll/pitch/yaw one
   at a time. Record the measured sign per axis.
3. `python scripts/control_probe.py --modes H` — same GO flow; note the
   thrust step where it lifts/holds cleanly now that it starts race-legal.
4. Main event — fly_once with the signs measured in (2), e.g. if pitch (and
   only pitch) is inverted:
   `python scripts/fly_once.py --max-duration 60 --patch control.att_rate.rate_sign_pitch=-1 --patch control.att_rate.hover_thrust=<H result>`
   Start the race when the pilot reaches THROTTLE_DOWN (it waits for GO).
   Describe per stage: countdown hold? clean climb? stable search spin?
   approach toward gate 1?
5. Collect with `--label phase2b`, notes.md with the sign table + visual
   account, commit `[sim-run] phase2b race-legal flight`, push.

## PREVIOUS: Phase 2a — first real controlled flight (att_rate pilot)

Phase-1f verdicts (cloud side): velocity setpoints are DEAD on the real sim;
attitude-thrust and motor commands work. The pilot was rebuilt around the
attitude-rate cascade as the primary backend:

- control.backend default is now "att_rate"; throttle-down handshake extended
  to 3s (the 1.5s handshake didn't clear the overlay in your fly_once)
- the estimator now measures VELOCITY FROM VISION (derivative of the static
  gate's relative pose) — the key feedback that made the cascade fly cleanly
  in the mock (full simulated gate pass end-to-end)
- control_probe gained mode D (rate-response pulse) and H (hover-thrust
  ladder) to calibrate the cascade against the real sim

Run this cycle:

1. `git pull`. Single engine instance.
2. During a real race: `python scripts/control_probe.py --modes H` — note at
   which thrust step the drone lifts/holds (brackets hover_thrust), then
   `--modes D` — does the pitch-rate pulse register on ygyro?
3. The main event: `python scripts/fly_once.py --max-duration 60` during a
   real race. Expected: handshake clears the overlay, drone climbs ~1.5s,
   then searches/approaches the first gate. Describe (screenshots) what it
   does — even a wobbly hover or a crash into the first gate is a milestone;
   note against WHICH behavior phase (takeoff/search/approach) things break.
4. Collect with `--label phase2a` (include probe outputs in the report),
   notes.md with visual account per stage, commit `[sim-run] phase2a first
   controlled flight`, push.

## PREVIOUS: Phase 1f — control-authority probe (which interface moves the drone?)

Phase-1e analysis (cloud side):

- Your vision slice was put to work: the detector was rewritten for the REAL
  Round-1 scene (red gate rings, dark warehouse) — **100% detection on all
  658 real frames**, stable PnP. Perception is no longer a blocker.
- "THROTTLE DOWN please" is now handled: the FSM gained a THROTTLE_DOWN state
  (zero-thrust hold after arming) and the census NaN crash + gyro_z-only
  liveness checks are fixed.
- Remaining unknown: WHICH control interface the sim actually honors once the
  handshake clears. That is this cycle.

Run this cycle:

1. `git pull`. Single engine instance as usual.
2. Start a real race, then run (capture with Tee-Object):
   `python scripts/control_probe.py`
   It resets/arms per mode, does the throttle-down handshake, then tests
   attitude-thrust (A), velocity (B) and motor (C) commands in turn. For EACH
   mode note: did the THROTTLE DOWN overlay clear? did the drone visibly
   move/lift? (screenshots welcome). If a sim reset kicks it out of the race,
   restart the race between modes and say so in notes.md.
3. If any mode moves the drone — immediately also run
   `python scripts/fly_once.py --max-duration 45` (the pilot now does the
   handshake itself) and describe what happens on screen.
4. Collect with `--label phase1f --report <report>`, notes.md with per-mode
   observations, commit `[sim-run] phase1f control probe`, push.

## PREVIOUS: Phase 1e — in-flight IMU verdict + real-vision fixtures

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
