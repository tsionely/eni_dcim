# Race Tally R1f

Scope: replay/CSV only. No FlightSim/DCGame process was launched. Analysis checked `origin/main` at `0c6e8f4` after `git pull --rebase origin main`.

## Status

No R1f fixtures were present at this HEAD: `fixtures/*raceprep-r1f-*` matched `0` directories.

Because no R1f logs are available, no pass rate, true-world dz, abort split, or A-vs-B scatter verdict can be computed yet. The registered prediction that A's true-world dz spread is tighter remains `UNJUDGED_NO_R1F_FIXTURES`.

## Method Locked For Re-run

- Retired columns: camera-frame `ty` and align/commit state-minus-detection bias are not used.
- Vertical metric: TRUE-WORLD dz at closest approach.
- Required implementation: import `aigp.planning.approach.true_world_dz` with `PYTHONPATH=src`.
- Pairing rule: for each detection, use the latest preceding state carrying `q_att`, `level_roll`, and `level_pitch`; compute `true_world_dz(RelPose(t=detection.rel_pose.t, normal=detection.rel_pose.normal), q_att, level_roll, level_pitch)`.
- Closest approach: detection row with minimum Euclidean range of `rel_pose.t`; report true-world dz at that same row.
- Per config: pass rate, median true-world dz, min..max spread, collision aborts, clip-budget aborts.
- Scatter comparison: A spread vs B spread; prediction is A tighter.

## Config Summary

| config | status | runs | pass_rate | median_true_world_dz_m | spread_true_world_dz_m | collision_aborts | clip_budget_aborts | prediction_A_tighter_verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | MISSING_AT_HEAD | 0 |  |  |  |  |  | UNJUDGED_NO_R1F_FIXTURES |
| B | MISSING_AT_HEAD | 0 |  |  |  |  |  | UNJUDGED_NO_R1F_FIXTURES |

## Artifacts

- `config_summary.csv`: empty A/B shell with `MISSING_AT_HEAD` status.
- `runs.csv`: empty per-run schema using true-world dz columns only.
- `scatter_comparison.csv`: empty A-vs-B spread comparison row.
