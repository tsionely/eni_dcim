# Phase 3b — R2-TRAINING default flights after docs/08 fixes

- **Date (local):** 2026-07-15 ~00:00-00:25 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Code commit:** `0d57506...` (branch `main`, clean pull; see manifest.json)
- **docs/08 confirmed:** `docs/08-sikum-r2-recon.md` exists and was read. It says R2 gates are red/visible, cyan racing line exists, detector works, and phase3b should retest R2 with fixes.
- **User instruction:** all flights on R2-TRAINING, default params, no patches. I ran 3 default R2-TRAINING flights.
- **Simulator lifecycle:** fresh FlightSim launched for this cycle and closed after push.

## Flight 1 — R2-TRAINING default
ID: `20260714T210518-58cd98ad`

Result:
- `aborted=True`, `abort_reason="gate clip budget exceeded (11)"`
- duration 22.1s
- `gates_passed=0`, `gate_clips=12`, `env_hits=0`
- `vision.aigprec`: **259.20 MB** full recording

Telemetry/vision:
- frames: 2512
- detections: 2011
- collisions messages: 12 (clip/collision topic count in log)
- phases: `hover` 911, `takeoff` 75, `approach` 77, `commit` 30, `recover` 12
- max active gate index: 0
- estimated speeds: ~9.8 km/h around t+3s; low after clip/end in last valid state.

Operator account:
- This is a strong R2 detector/navigation attempt: it got to approach and commit and clipped the gate repeatedly, but did not pass.
- Nose appears to track a real gate/target; failure mode is too-close/gate-clip budget, not blindness.

## Flight 2 — R2-TRAINING default
ID: `20260714T210844-58cd98ad`

Result:
- `aborted=True`, `abort_reason="environment collision (impulse=1.4)"`
- duration 21.1s
- `gates_passed=0`, `env_hits=1`
- `vision.aigprec`: **221.59 MB** full recording

Telemetry/vision:
- frames: 2198
- detections: 1665
- phases: `hover` 911, `takeoff` 76, `approach` 67
- max active gate index: 0
- estimated speed around t+3s: ~26.4 km/h

Operator account:
- Reached approach, detected gates, but collided before commit/pass.
- Approach speed looked moderate-to-fast; no visible gate pass.

## Flight 3 — R2-TRAINING default
ID: `20260714T211404-58cd98ad`

Result:
- `aborted=True`, `abort_reason="environment collision (impulse=3.2)"`
- duration 24.6s
- `gates_passed=0`, `env_hits=1`
- `vision.aigprec`: **299.64 MB** full recording

Telemetry/vision:
- frames: 2769
- detections: 2212
- phases: `hover` 907, `takeoff` 75, `approach` 128
- max active gate index: 0
- estimated speeds: ~9.2 km/h around t+3s, ~2.5 km/h around t+6s, ~9.9 km/h near last valid approach states.

Operator account:
- Most promising of the three on speed: approach stayed low/moderate by log estimates.
- Still ended in environment collision and no gate pass.

## Overall Phase 3b observations
1. R2 detector/data is very much alive: all three flights had large vision recordings and many detections.
2. No `gates_passed > 0` yet; Phase-3 milestone not reached in this cycle.
3. The updated R2 fixes appear to make the pilot engage real R2 gates and enter approach/commit. Flight 1 specifically hit gate-clip budget, which suggests it is aiming at a gate but not threading the opening cleanly.
4. The expected qualitative behavior was partly achieved: takeoff works, approach happens, and the nose seems to lock on a gate/target; pass still fails due to clipping/collision.

## Recording deliverables
Full recordings are too large for git:
- F1 full: ~259 MB
- F2 full: ~222 MB
- F3 full: ~300 MB

Committed slices (all under 50 MB each):
- `20260714T210518-58cd98ad_r2_slice_start.aigprec` — 33.69 MB
- `20260714T210844-58cd98ad_r2_slice_start.aigprec` — 33.69 MB
- `20260714T211404-58cd98ad_r2_slice_start.aigprec` — 33.69 MB

These slices plus full local recordings are the main R2 evidence for DATA ANALYST.

## Fixture contents
- `report.txt` — full console, summaries, slice commands.
- logs/results/params for all 3 flights.
- 3 R2 recording slices.
- `screens/` — downscaled screenshots from start/mid/late of each flight.
- `manifest.json` — collector manifest.
