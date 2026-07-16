# Phase 4a — R2-TRAINING chain attempt

- **Date (local):** 2026-07-16 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385** (`AI GP 1.0.3385` in HUD)
- **Flight code commit:** `f332244` — current Phase 4a task after pull (includes `fbf24b1` and the `43ef2b0` RX scheduler fix)
- **SIM LOCK:** created at `C:\Temp\eni_dcim_sim.lock` before sim launch.
- **Track:** R2-TRAINING.
- **Label:** `phase4a-r2training-chain`

## Important task note
The user prompt mentioned slow speed patches, but after `git pull`, the **current `AGENTS.md` Phase 4a task changed to DEFAULT SPEEDS** (`f332244 Phase 4a: default speeds`). I followed the current task text:

```powershell
python scripts/fly_once.py --max-duration 300 --patch safety.flight_timeout_s=300
```

No speed patches were applied.

## Summary verdict
- 3 valid default-speed R2-TRAINING chain attempts were run: F1, F2b replacement, F3.
- **No gates passed in this run set** (`gates_passed=0` for all selected valid flights).
- Therefore there are **no pass + 20s windows** to slice. I committed no-pass start/attempt slices for the three valid flights instead, clearly named `*_r2a_nopass_start_slice.aigprec`.
- The earlier milestone default pass from Phase 3j rerun did not reproduce in these three Phase 4a attempts.

## Valid selected flights

### F1 default chain
ID: `20260716T133531-927a4c97`
- Result: `environment collision (impulse=1.6)`
- Duration: `28.1s`
- `gates_passed=0`, `gate_clips=0`, `env_hits=8`
- Phase sequence: `hover -> takeoff -> approach -> commit -> retreat -> recover`
- Attempts: approach=1, commit=1, retreat=1, recover=1
- Closest direct: `dist=4.92m`, center-x / LOW
- Closest state: `dist=1.20m`, center-x / LOW, age `1.19s`
- Ending: hard environment collision during/after commit/retreat; no Gate 1 pass.

### F2b default chain replacement
ID: `20260716T134842-927a4c97`
- Result: `environment collision (impulse=1.7)`
- Duration: `33.2s`
- `gates_passed=0`, `gate_clips=0`, `env_hits=35`
- Phase sequence: `hover -> takeoff -> approach -> commit -> recover -> approach -> commit -> retreat -> approach -> commit -> retreat -> recover`
- Attempts: approach=3, commit=3, retreat=2, recover=2
- Closest direct: `dist=1.96m`, RIGHT / center-y
- Closest state: `dist=0.18m`, center-x / HIGH, age `0.89s` (very stale/dead-reckoned near gate)
- Visual: screenshots show a centered/visible gate and cyan line, but the run never registered a pass.
- Ending: repeated contacts / hard environment collision after several commit/retry cycles.

### F3 default chain
ID: `20260716T134309-927a4c97`
- Result: `environment collision (impulse=1.6)`
- Duration: `34.6s`
- `gates_passed=0`, `gate_clips=1`, `env_hits=21`
- Phase sequence: `hover -> takeoff -> approach -> recover -> approach -> search -> approach -> recover -> approach`
- Attempts: approach=4, commit=0, search=1, recover=2
- Closest direct: `dist=1.23m`, RIGHT / center-y
- Closest state: `dist=2.08m`, RIGHT / HIGH, age `0.49s`
- Ending: gate clip + environment collisions, no pass.

## Excluded invalid/no-race context
- `20260716T133703-927a4c97` — original F2 timed out for 300s with no frames/detections and `race_start=-1`; it is included only as invalid/no-race context, not one of the three selected valid flights.

## Post-pass behavior
None of the selected valid flights passed Gate 1, so there was no post-pass behavior to observe and no pass+20s slices to make.

## Interpretation for next cycle
- Current default-speed chain build did not reproduce the previous Gate 1 pass in this sample.
- Failures are still before chain navigation: Gate 1 is reached/seen, but the vehicle collides/clips before an official pass.
- F2b is the most useful no-pass attempt: multiple approach/commit/retry cycles with a centered visible gate and cyan line, but no pass; likely best for analyzing why the pass stamp failed.

## Fixture contents
- `report.txt` — full console output, including the invalid original F2 and valid replacement F2b.
- `phase4a_r2training_chain_analysis.txt` — per-flight phase sequence, closest direct/state fixes, collision timing, and pass-event status.
- logs/results/params for F1, F2b, F3, plus invalid F2 context.
- 3 no-pass start/attempt recording slices (`*_r2a_nopass_start_slice.aigprec`), ~28.88 MB each.
- `screens/` — downscaled screenshots for F1/F2b/F3.
- Full recordings (167-274 MB for selected flights) exceed the git fixture size limit and remain local / Drive candidates.
