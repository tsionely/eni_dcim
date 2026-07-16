# Phase 3i — R2-TRAINING slow set with +0.3m aim-up floor

- **Date (local):** 2026-07-16 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385** (`AI GP 1.0.3385` in HUD)
- **Flight code commit:** `9d741b0` — `aim_up floor: cross 0.3m above center instead of tapering to zero`
- **SIM LOCK:** created at `C:\Temp\eni_dcim_sim.lock` before sim launch.
- **Track:** R2-TRAINING.
- **Task:** 3 slow-patch flights; optional no-patch flight; if any flight crosses HIGH, report the miss size.

## Slow patch set
```powershell
--patch planner.approach.speed_far_mps=1.2
--patch planner.approach.speed_near_mps=0.8
--patch planner.commit.speed_mps=1.2
--patch planner.commit.duration_s=2.5
```

## Summary verdict
- **No gate pass yet** (`gates_passed=0` on all valid flights).
- The +0.3m aim-up floor did **not** over-correct into a close HIGH crossing. The closest direct/state samples for all valid slow flights are still **center-x and LOW or center-y**.
- There are some **far/early HIGH samples**, but not at closest approach. I reported those miss sizes below; they are not clean gate-plane HIGH crossings.
- Optional default/no-patch was attempted multiple times but did not produce a valid race after the login/no-race GUI issues; I include that as an operational anomaly, not as a pilot result.

## Valid slow flights

### F1 slow valid replacement
ID: `20260716T113216-8edfeec4`
- Result: `environment collision (impulse=1.5)`
- Duration: `35.6s`
- `gates_passed=0`, `gate_clips=0`, `env_hits=17`
- Phase sequence: `hover -> takeoff -> approach -> commit -> retreat -> recover -> approach`
- Attempts: 2 approach runs, 1 commit, 1 retreat
- Closest direct detection: `dist=3.80m`, `u=+0.08`, `v=+0.63` -> **center-x / LOW**
- Closest steering state: `dist=1.23m`, `u=-0.07`, `v=+0.28`, age `1.47s` -> **center-x / LOW**
- HIGH report: closest HIGH direct sample was far/early at `dist=5.68m`, `v=-0.35`, image miss ~0.35 half-frame, rel `t_y=-3.68m`. Closest HIGH state sample was `dist=3.67m`, `v=-0.16`, gate_rel_y `-0.32m`, age `0.15s`. This is not a close gate-plane HIGH crossing.

### F2 slow valid original
ID: `20260716T031114-8edfeec4`
- Result: `environment collision (impulse=1.3)`
- Duration: `28.2s`
- `gates_passed=0`, `gate_clips=0`, `env_hits=1`
- Phase sequence: `hover -> takeoff -> approach -> commit -> retreat -> search -> approach`
- Attempts: 2 approach runs, 1 commit, 1 retreat
- Closest direct detection: `dist=3.66m`, `u=+0.13`, `v=+0.92` -> **center-x / LOW**
- Closest steering state: `dist=1.55m`, `u=+0.01`, `v=+0.07`, age `1.19s` -> **center-x / center-y**
- HIGH report: closest HIGH direct sample was far/early at `dist=6.59m`, `v=-0.36`, image miss ~0.36 half-frame, rel `t_y=-4.24m`. Closest HIGH state sample was `dist=4.28m`, `v=-0.16`, gate_rel_y `-0.38m`, age `0.24s`. No close HIGH crossing.

### F3 slow valid direct-click replacement
ID: `20260716T114244-8edfeec4`
- Result: `environment collision (impulse=1.3)`
- Duration: `26.7s`
- `gates_passed=0`, `gate_clips=0`, `env_hits=1`
- Phase sequence: `hover -> takeoff -> approach -> search -> approach -> hover`
- Attempts: 2 approach runs, no commit/retreat on this run
- Closest direct detection: `dist=4.28m`, `u=-0.01`, `v=+0.61` -> **center-x / LOW**
- Closest steering state: `dist=2.25m`, `u=-0.00`, `v=+0.13`, age `1.21s` -> **center-x / center-y**
- HIGH report: closest HIGH direct sample was far/early at `dist=6.01m`, `v=-0.77`, image miss ~0.77 half-frame, rel `t_y=-4.72m`. Closest HIGH state sample was `dist=3.15m`, `v=-0.29`, gate_rel_y `-0.51m`, age `1.49s`. No close HIGH crossing.

## Operational anomalies / invalid attempts
Several early/replacement attempts did not enter a valid race because the sim was blocked by a pre-filled **LOGIN** modal or because the old left-side R2 row click did not open the race dialog:
- `20260716T030847-8edfeec4`, `20260716T031450-8edfeec4`, `20260716T031753-8edfeec4`, `20260716T032056-fc86a160`, `20260716T113354-8edfeec4`, `20260716T113657-fc86a160`: `flight timeout`, no frames/detections, race_start stayed `-1`.
- `20260716T031209-8edfeec4`, `20260716T031246-fc86a160`, `20260716T115412-fc86a160`: stale-frame / no-race behavior.

Fix applied during this cycle: the GUI helper now submits the login modal and uses the observed R2 row center (`x≈1000,y≈392`) plus Race button (`x≈1650,y≈866`). That produced the final valid F3 slow run. Screenshot `login_modal_or_no_race_timeout.jpg` documents the login/no-race issue.

## Interpretation for next cycle
- The +0.3m floor is **not too high** at closest approach; closest valid samples remain LOW or centered vertically.
- Compared with Phase 3h, the problem looks less like bottom-bar clipping and more like **not reaching a stable close commit**: closest direct detections are still 3.7-4.3m out, while closest state is 1.2-2.3m with ~1.2-1.5s age.
- The useful next diagnostic is likely why valid 3i flights do not sustain close detections/commit after aim-up: final state is centered/low, but commit/retreat does not convert to pass.

## Fixture contents
- `report.txt` — full console output, including invalid/no-race attempts and corrected direct-click run.
- `phase3i_r2training_closest.txt` — closest direct/state analysis, attempts, HIGH miss samples.
- logs/results/params for the 3 valid slow flights and the final optional default invalid attempt.
- 3 recording start-slices (`*_r2i_slice_start.aigprec`), one for each valid slow flight, ~28.88 MB each.
- `screens/` — downscaled screenshots for valid flights plus login/no-race anomaly.
- Full recordings (150-327 MB for valid slow flights) exceed the git fixture size limit and remain local / Drive candidates.
