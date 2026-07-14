# Phase 3a — R2-TRAINING recon flights (DEFAULT params)

- **Date (local):** 2026-07-14 ~23:12-23:33 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Code commit:** `0d57506...` (branch `main`, clean pull; see manifest.json)
- **docs/07 confirmed:** `docs/07-mahapach-hachushim.md` exists and was read before this run. It documents the corrected sensor model: gyro reports inverted, command channel straight, body-fixed camera, epoch frame timestamps.
- **User override:** although AGENTS Phase 3a still mentions an R1 validation, the user explicitly requested **ALL flights on R2-TRAINING**. I ran 3 R2-TRAINING flights only, default params, no patches.
- **Simulator lifecycle:** launched fresh FlightSim for this cycle.

## Flight 1 — R2-TRAINING default
ID: `20260714T201758-58cd98ad`

Result:
- `aborted=True`, `abort_reason="flight timeout"`
- duration 120.0s
- `gates_passed=0`, `env_hits=0`
- loop overruns: 133 / 30000 (0.44%)

Telemetry/vision:
- `vision.aigprec` size: **0 MB**
- no `frame` messages, no `detection` messages
- phases: `hover` 2253, `takeoff` 75, `search` 3673
- speed estimate stayed 0 km/h in sampled states

Operator note:
- This looks like R2-TRAINING did not produce the UDP vision stream in this first attempt, even though the race helper clicked R2-TRAINING and RACE.
- Still useful as a negative/control data point: no frames/detections on this run.

## Flight 2 — R2-TRAINING default
ID: `20260714T202447-58cd98ad`

Result:
- `aborted=True`, `abort_reason="environment collision (impulse=4.1)"`
- duration 24.9s
- `gates_passed=0`, `env_hits=1`
- `vision.aigprec`: **142.57 MB** (full file too large for repo)

Telemetry/vision:
- frames: 393
- detection messages: 235
- phases: `hover` 945, `takeoff` 75, `approach` 172, `commit` 53
- max active gate index: 0
- speed around 3s: ~6-7 km/h by log estimate

Operator note:
- This is a successful R2 recon capture: vision stream exists and detector produced nonzero detections.
- It collided during/after an approach/commit attempt; no gate pass.
- Full recording should go to Drive if needed; fixture contains a 38.5MB slice.

## Flight 3 — R2-TRAINING default
ID: `20260714T202743-58cd98ad`

Result:
- `aborted=True`, `abort_reason="environment collision (impulse=5.0)"`
- duration 22.3s
- `gates_passed=0`, `gate_clips=1`, `env_hits=7`
- `vision.aigprec`: **224.68 MB** (full file too large for repo)

Telemetry/vision:
- frames: 2233
- detection messages: 1649
- phases: `hover` 907, `takeoff` 75, `approach` 75, `commit` 20, `recover` 40
- max active gate index: 0
- speed around 3s: ~76-77 km/h by log estimate

Operator note:
- This is the best R2 recon capture in this cycle: many frames and detections.
- Detector did see something in R2 (contrary to the worst-case expectation of no gates), but it did not produce a successful gate pass.
- Full recording should go to Drive if needed; fixture contains a 38.5MB slice.

## Recording/slice deliverables
Full recordings are too large for git:
- F2 full: ~142.57 MB
- F3 full: ~224.68 MB

Committed slices:
- `r2_f2_slice_start.aigprec` — 38.5 MB, start of F2 recording
- `r2_f3_slice_start.aigprec` — 38.5 MB, start of F3 recording

These slices are the main deliverable for DATA ANALYST R2 gate appearance study.

## Overall conclusions
1. R2-TRAINING recording objective succeeded for Flights 2 and 3.
2. R2 does produce usable UDP vision in at least some runs.
3. The current detector produced nonzero detection messages on R2 (235 and 1649), so R2 gates or gate-like objects are not completely invisible to the current pipeline.
4. No gates were passed; both useful R2 attempts ended in environment collision.
5. Flight 1 had no vision stream; this inconsistency should be noted by analyst/cloud (possible menu/race-start state issue or intermittent R2 stream startup).

## Fixture contents
- `report.txt` — full console for all 3 flights, slice commands, summary table.
- Three flight logs/results/params for F1/F2/F3.
- `r2_f2_slice_start.aigprec`, `r2_f3_slice_start.aigprec` — committable recording slices.
- `screens/` — a few downscaled helper screenshots from the R2 attempts.
- `manifest.json` — collector manifest (plus manual additions noted here).
