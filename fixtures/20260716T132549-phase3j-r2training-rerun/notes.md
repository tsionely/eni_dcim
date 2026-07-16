# Phase 3j rerun — R2-TRAINING after RX scheduler fix

- **Date (local):** 2026-07-16 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385** (`AI GP 1.0.3385` in HUD)
- **Flight code commit:** `43ef2b0` — `Fix phase3j grounding: my no-sleep loop starved the pilot's RX threads`
- **Task build under test:** includes `bbe3aee` blind-commit climb bias + aim taper restored + geometric commit termination.
- **SIM LOCK:** created at `C:\Temp\eni_dcim_sim.lock` before sim launch.
- **Track:** R2-TRAINING.
- **Label:** `phase3j-r2training-rerun`

## Slow patch set used
Only the slow speed patches were used. The old `planner.commit.duration_s` patch was intentionally **not** used.

```powershell
--patch planner.approach.speed_far_mps=1.2
--patch planner.approach.speed_near_mps=0.8
--patch planner.commit.speed_mps=1.2
```

## Headline
- The scheduler/RX starvation fix worked: unlike the blocked Phase 3j cycle, the rerun produced sustained frame/detection logs and real R2 flight behavior.
- **Milestone:** the optional default/no-patch flight passed **Gate 1**: `gates_passed=1`.
- The 3 slow-speed-only attempts did not pass. Two were normal environment-collision attempts; one launched and reached approach/commit/retreat but later aborted on `stale channels: frame` after 27s.

## Selected flight results

### F1 slow replacement — live launch, then frame-stale after approach/commit/retreat
ID: `20260716T131630-8edfeec4`
- Result: `stale channels: frame`
- Duration: `27.3s`
- `gates_passed=0`, `gate_clips=0`, `env_hits=0`
- Loop overruns: `21` (`loop_overrun_frac=0.00307`, max late `5449us`)
- Topics: 135 frames, 120 detections, 1064 IMU, 1367 states
- Phase sequence: `hover -> takeoff -> approach -> commit -> retreat`
- Attempts: approach=1, commit=1, retreat=1
- Closest direct: `dist=1.66m`, `u=+0.09`, `v=+0.26` -> **center-x / LOW**
- Closest state: `dist=0.45m`, `u=+0.11`, `v=-0.57`, age `0.61s` -> **center-x / HIGH**

Interpretation: this was a real launched slow flight and got into commit/retreat, but the frame stream died later. The closest direct observation still looked slightly LOW; the stale/dead-reckoned state was very close but HIGH.

### F2 slow original valid
ID: `20260716T130659-8edfeec4`
- Result: `environment collision (impulse=1.6)`
- Duration: `29.2s`
- `gates_passed=0`, `env_hits=3`
- Topics: 2169 frames, 1661 detections
- Phase sequence: `hover -> takeoff -> approach -> commit -> retreat`
- Attempts: approach=1, commit=1, retreat=1
- Closest direct: `dist=2.99m`, `u=+0.16`, `v=+0.84` -> **RIGHT / LOW**
- Closest state: `dist=0.89m`, `u=-0.16`, `v=+0.27`, age `1.19s` -> **LEFT / LOW**

Interpretation: slow still misses low/lateral and then collides/retries, no pass.

### F3 slow replacement valid
ID: `20260716T131802-8edfeec4`
- Result: `environment collision (impulse=5.0)`
- Duration: `32.1s`
- `gates_passed=0`, `env_hits=1`
- Topics: 2419 frames, 1409 detections
- Phase sequence: `hover -> takeoff -> approach -> search -> approach`
- Attempts: approach=2, commit=0, retreat=0
- Closest direct: `dist=4.25m`, `u=-0.04`, `v=+0.88` -> **center-x / LOW**
- Closest state: `dist=2.13m`, `u=+0.01`, `v=+0.14`, age `1.20s` -> **center-x / center-y**

Interpretation: did not reach commit; still no pass. Direct closest again shows LOW.

### F4 optional default/no-patch — **Gate 1 pass milestone**
ID: `20260716T131137-2ca531c3`
- Result: `environment collision (impulse=15.5)` after the pass
- Duration: `38.9s`
- **`gates_passed=1`**
- `gate_clips=0`, `env_hits=1`
- Topics: 4396 frames, 2057 detections
- Phase sequence: `hover -> takeoff -> approach -> commit -> approach -> commit -> retreat -> approach -> search -> approach`
- Attempts: approach=4, commit=2, retreat=1
- Closest direct: `dist=3.30m`, `u=-0.03`, `v=+0.54` -> **center-x / LOW**
- Closest state: `dist=0.10m`, `u=+0.08`, `v=+3.37`, age `1.08s` -> off-frame LOW/dead-reckoned near gate

Interpretation: default speed is now viable again. It completed Gate 1, then collided later. This is the first R2-TRAINING gate pass in the local sim cycle.

## Excluded/no-race/timeouts
- `20260716T130355-8edfeec4`: timeout, no frames/detections, `race_start=-1`.
- `20260716T130833-8edfeec4`: timeout with many frames/detections but `race_start=-1`; not counted as a valid race.

## Overall interpretation
- The `43ef2b0` scheduler fix solved the pilot-side RX starvation enough for real R2 flights again.
- The default/no-patch controller produced the milestone gate pass. The slow-speed patch set still appears too sluggish/low: closest direct observations in slow flights remain LOW, and slow runs do not complete Gate 1.
- For the next cycle, default-speed behavior deserves priority. If using slow speeds, the low/direct miss remains; however, default may now be the better regime with geometric commit termination + blind climb bias.

## Fixture contents
- `report.txt` — full console output for rerun and replacement flights.
- `phase3j_rerun_r2training_analysis.txt` — per-flight topic counts, phase sequences, closest direct/state fixes.
- logs/results/params for selected flights: F1 slow, F2 slow, F3 slow, F4 default milestone pass.
- logs/results for excluded/no-race/timeouts for context.
- 4 recording start-slices (`*_r2j_rerun_slice_start.aigprec`), ~28.88 MB each.
- `screens/` — downscaled screenshots from slow flights and default pass attempt.
- Full recordings (124-496 MB) exceed the git fixture size limit and remain local / Drive candidates.
