# Race Tally R1c + R1d Vertical Offset

Scope: replay/CSV only. No FlightSim/DCGame process was launched. Analysis ran at repo HEAD `9471260` after `git pull --rebase origin main`.

Metric definition: `camera-frame ty` is `detection.data.rel_pose.t[1]` as logged. Negative values are preserved; in this packet, closer to zero means less measured vertical deficit. Closest approach is the detection row with minimum Euclidean norm of `rel_pose.t`. Commit-entry ty uses the latest detection at or before each transition into setpoint phase `commit`; `commit_entries.csv` includes the detection age for every entry.

Groups requested:
- R1c old build, speed 1.8, no `planner.commit.vz_cap_mps` key: `fixtures/*raceprep-r1c-*`.
- R1b-B new build, speed 1.8, `planner.commit.vz_cap_mps=0.35`: `fixtures/*raceprep-r1b-B-*`.
- R1d new build, speed 1.8, `planner.commit.vz_cap_mps=1.2`: `fixtures/*raceprep-r1d-*`.

## Answer So Far

- R1c old/no-cap: pass rate 1/6, median closest camera ty -0.408m, median |ty| 0.408m, median all commit-entry ty -2.021m.
- R1b-B new/cap0.35: pass rate 0/5, median closest camera ty -0.532m, median |ty| 0.532m, median all commit-entry ty -2.177m.
- Partial read: moving from old/no-cap to new/cap0.35 worsened the closest-approach vertical offset slightly (more negative ty, farther from zero) and pass rate dropped from 1/6 to 0/5; build changed too, so this is not an isolated cap effect.
- R1d new/cap1.2 fixtures are missing at this pulled HEAD, so the climb-authority question is not closed yet. The table has a MISSING_AT_HEAD row for that group.

## Group Summary

| group | status | runs | pass_rate | total_gates | collision_aborts | clip_budget_aborts | timeout_aborts | expected_vz_cap_mps | median_closest_camera_ty_m | median_abs_closest_camera_ty_m | median_first_commit_entry_ty_m | median_last_commit_entry_ty_m | median_all_commit_entry_ty_m | median_abs_all_commit_entry_ty_m | median_approach_phase_duration_s | param_ok_runs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1c-old-no-vz-cap | OK | 6 | 1/6 | 1 | 4 | 1 | 1 | ABSENT | -0.408 | 0.408 | -2.582 | -1.480 | -2.021 | 2.021 | 0.380 | 6 |
| R1b-B-new-cap0.35 | OK | 5 | 0/5 | 0 | 5 | 0 | 0 | 0.350 | -0.532 | 0.532 | -2.222 | -2.050 | -2.177 | 2.177 | 0.642 | 5 |
| R1d-new-cap1.2 | MISSING_AT_HEAD | 0 |  |  |  |  |  | 1.200 |  |  |  |  |  |  |  |  |

## Per-Run Table

| group | run | cfg | gates | abort | phase | failed_gate | cap | closest_range | closest_ty | closest_phase | commit_entry_ty_list | approach_s | param |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1c-old-no-vz-cap | 1 | A | 0 | clip_budget | recover | 1 | ABSENT | 0.646 | -0.177 | retreat | -2.675141;-0.559843;-1.467505 | 0.080 | OK |
| R1c-old-no-vz-cap | 2 | B | 0 | collision | hover | 1 | ABSENT | 0.751 | -0.296 | commit | -3.231583;-2.880181 | 0.557 | OK |
| R1c-old-no-vz-cap | 3 | A | 0 | collision | recover | 1 | ABSENT | 2.293 | -0.450 | commit | -2.020903 | 0.100 | OK |
| R1c-old-no-vz-cap | 4 | B | 0 | timeout | hover | 1 | ABSENT | 1.919 | -1.343 | align | -4.431064;-1.491950 | 0.280 | OK |
| R1c-old-no-vz-cap | 5 | A | 1 | collision | search | 2 | ABSENT | 1.041 | -0.388 | commit | -1.190339;-3.045765;-0.197964 | 0.480 | OK |
| R1c-old-no-vz-cap | 6 | B | 0 | collision | recover | 1 | ABSENT | 0.797 | -0.427 | recover | -2.489428;-0.373760 | 0.520 | OK |
| R1b-B-new-cap0.35 | 2 | B | 0 | collision | recover | 1 | 0.35 | 1.212 | -0.928 | align | -2.132406;-0.231888;-2.049884 | 0.240 | OK |
| R1b-B-new-cap0.35 | 4 | B | 0 | collision | approach | 1 | 0.35 | 1.487 | -1.090 | align | -3.483094;-4.726794 | 0.642 | OK |
| R1b-B-new-cap0.35 | 6 | B | 0 | collision | recover | 1 | 0.35 | 0.999 | -0.508 | retreat | -0.866969 | 0.900 | OK |
| R1b-B-new-cap0.35 | 8 | B | 0 | collision | search | 1 | 0.35 | 2.070 | -0.532 | commit | -2.912034 | 0.000 | OK |
| R1b-B-new-cap0.35 | 10 | B | 0 | collision | approach | 1 | 0.35 | 0.650 | -0.200 | retreat | -2.221708;-2.350904;-0.580429 | 4.118 | OK |

## Failure Modes

| group | failed_gate | abort_phase | abort_class | count | runs |
| --- | --- | --- | --- | --- | --- |
| R1b-B-new-cap0.35 | 1 | approach | collision | 2 | 4,10 |
| R1b-B-new-cap0.35 | 1 | recover | collision | 2 | 2,6 |
| R1b-B-new-cap0.35 | 1 | search | collision | 1 | 8 |
| R1c-old-no-vz-cap | 1 | hover | collision | 1 | 2 |
| R1c-old-no-vz-cap | 1 | hover | timeout | 1 | 4 |
| R1c-old-no-vz-cap | 1 | recover | clip_budget | 1 | 1 |
| R1c-old-no-vz-cap | 1 | recover | collision | 2 | 3,6 |
| R1c-old-no-vz-cap | 2 | search | collision | 1 | 5 |

## Missing Groups

| group | packet | pattern | expected_count | status | analysis_head |
| --- | --- | --- | --- | --- | --- |
| R1d-new-cap1.2 | R1d | fixtures/*raceprep-r1d-* | 5 | MISSING_AT_HEAD | 9471260 |

## Artifacts

- `runs.csv`: per-run race tally with closest ty and commit-entry ty list.
- `commit_entries.csv`: one row per commit entry, including camera-frame ty and detection age.
- `group_summary.csv`: pass rate and vertical-offset aggregates per requested group.
- `failure_modes.csv`: failed-gate attribution by phase and abort class.
- `missing_groups.csv`: group availability at this pulled HEAD.
