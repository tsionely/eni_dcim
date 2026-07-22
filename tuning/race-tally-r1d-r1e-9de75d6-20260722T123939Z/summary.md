# Race Tally R1d + R1e Bias

Scope: replay/CSV only. No FlightSim/DCGame process was launched. Analysis ran at repo HEAD `9de75d6` after `git pull --rebase origin main`.

Metric definitions:
- Closest camera-frame `ty` is `detection.data.rel_pose.t[1]` at the minimum Euclidean range detection row.
- Commit-entry `ty` is the latest detection camera-frame `ty` at or before each transition into setpoint phase `commit`; all entries are listed per run.
- Bias column is median `state.gate_rel.t[1] - detection.rel_pose.t[1]`, paired by nearest detection within `0.3s`, over state ticks whose latest setpoint phase is `align` or `commit`.
- Parameter integrity checks the four expected fields: speed, terminal enable, commit vz cap, and vision blend.

## Answer

- Climb authority: R1b-B cap 0.35 was 0/5 with median commit-entry ty -2.177m; R1d cap 1.2 was 1/5 with median commit-entry ty -1.236m. The commit-entry deficit moved toward zero and one gate pass appeared.
- Blend 0.9 / R1e: pass rate 0/5, median closest ty -0.733m, median commit-entry ty -0.892m. Commit-entry ty moved further toward zero, but pass rate fell back to zero and closest ty worsened versus R1d.
- Bias prediction: median per-run bias was R1b-B 0.015m, R1d 0.020m, R1e 0.732m. R1e did NOT collapse the per-run bias toward zero; by this registered column it worsened, with large-positive-bias run count 2 -> 0 -> 3.
- Deficit/pass relation: raising climb authority helped the commit-entry deficit and produced one pass in R1d. Raising vision_blend to 0.9 did not improve pass rate, did not improve closest-approach ty, and did not satisfy the bias-collapse prediction.

## Three-Group Summary

| group | status | runs | pass_rate | total_gates | expected_vz_cap_mps | expected_vision_blend | median_closest_camera_ty_m | median_abs_closest_camera_ty_m | median_all_commit_entry_camera_ty_m | median_run_bias_state_minus_detection_ty_m | median_abs_run_bias_state_minus_detection_ty_m | large_positive_bias_run_count_gt_0p5m | bias_pair_count | param_ok_runs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1b-B-new-cap0.35-blend0.6 | OK | 5 | 0/5 | 0 | 0.350 | 0.600 | -0.532 | 0.532 | -2.177 | 0.015 | 0.015 | 2 | 1003 | 5 |
| R1d-new-cap1.2-blend0.6 | OK | 5 | 1/5 | 1 | 1.200 | 0.600 | -0.600 | 0.600 | -1.236 | 0.020 | 0.020 | 0 | 915 | 5 |
| R1e-new-cap1.2-blend0.9 | OK | 5 | 0/5 | 0 | 1.200 | 0.900 | -0.733 | 0.733 | -0.892 | 0.732 | 0.732 | 3 | 616 | 5 |

## Question Columns

| group | pass_rate | expected_vz_cap_mps | expected_vision_blend | median_closest_camera_ty_m | median_all_commit_entry_camera_ty_m | median_run_bias_state_minus_detection_ty_m | median_abs_run_bias_state_minus_detection_ty_m | large_positive_bias_run_count_gt_0p5m |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1b-B-new-cap0.35-blend0.6 | 0/5 | 0.350 | 0.600 | -0.532 | -2.177 | 0.015 | 0.015 | 2 |
| R1d-new-cap1.2-blend0.6 | 1/5 | 1.200 | 0.600 | -0.600 | -1.236 | 0.020 | 0.020 | 0 |
| R1e-new-cap1.2-blend0.9 | 0/5 | 1.200 | 0.900 | -0.733 | -0.892 | 0.732 | 0.732 | 3 |

## Per-Run Table

| group | run | gates | abort | phase | cap | blend | closest_ty | closest_phase | commit_entry_ty_list | bias_median | bias_abs | bias_n | param |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1b-B-new-cap0.35-blend0.6 | 2 | 0 | collision | recover | 0.35 | 0.6 | -0.928 | align | -2.132406;-0.231888;-2.049884 | 0.771 | 0.772 | 163 | OK |
| R1b-B-new-cap0.35-blend0.6 | 4 | 0 | collision | approach | 0.35 | 0.6 | -1.090 | align | -3.483094;-4.726794 | 1.275 | 1.275 | 121 | OK |
| R1b-B-new-cap0.35-blend0.6 | 6 | 0 | collision | recover | 0.35 | 0.6 | -0.508 | retreat | -0.866969 | 0.007 | 0.023 | 118 | OK |
| R1b-B-new-cap0.35-blend0.6 | 8 | 0 | collision | search | 0.35 | 0.6 | -0.532 | commit | -2.912034 | 0.015 | 0.068 | 218 | OK |
| R1b-B-new-cap0.35-blend0.6 | 10 | 0 | collision | approach | 0.35 | 0.6 | -0.200 | retreat | -2.221708;-2.350904;-0.580429 | 0.012 | 0.074 | 383 | OK |
| R1d-new-cap1.2-blend0.6 | 1 | 0 | collision | recover | 1.2 | 0.6 | -0.298 | recover | -2.610162;-0.796000 | 0.026 | 0.089 | 176 | OK |
| R1d-new-cap1.2-blend0.6 | 2 | 0 | collision | commit | 1.2 | 0.6 | -0.677 | commit | -2.050947;-0.647062;-1.761634 | 0.019 | 0.107 | 225 | OK |
| R1d-new-cap1.2-blend0.6 | 3 | 0 | clip_budget | recover | 1.2 | 0.6 | -0.600 | commit | -0.996050 | -0.001 | 0.034 | 131 | OK |
| R1d-new-cap1.2-blend0.6 | 4 | 1 | collision | recover | 1.2 | 0.6 | -0.246 | recover | -2.184585;-0.636664;-4.420137;-0.331371;-1.324143 | 0.113 | 0.333 | 260 | OK |
| R1d-new-cap1.2-blend0.6 | 5 | 0 | collision | commit | 1.2 | 0.6 | -1.334 | commit | -1.148296 | 0.020 | 0.060 | 123 | OK |
| R1e-new-cap1.2-blend0.9 | 1 | 0 | collision | recover | 1.2 | 0.9 | -2.101 | commit | -0.567156 | 0.732 | 0.732 | 55 | OK |
| R1e-new-cap1.2-blend0.9 | 2 | 0 | collision | search | 1.2 | 0.9 | -0.724 | commit | -0.679447 | 0.008 | 0.031 | 174 | OK |
| R1e-new-cap1.2-blend0.9 | 3 | 0 | clip_budget | recover | 1.2 | 0.9 | -0.733 | recover | -2.129317 | 0.888 | 0.888 | 141 | OK |
| R1e-new-cap1.2-blend0.9 | 4 | 0 | collision | recover | 1.2 | 0.9 | -0.955 | align | -1.881036 | 0.007 | 0.050 | 126 | OK |
| R1e-new-cap1.2-blend0.9 | 5 | 0 | collision | search | 1.2 | 0.9 | -0.446 | approach | -2.192759;-0.445524;-0.892013 | 1.996 | 1.996 | 120 | OK |

## Failure Modes

| group | failed_gate | abort_phase | abort_class | count | runs |
| --- | --- | --- | --- | --- | --- |
| R1b-B-new-cap0.35-blend0.6 | 1 | approach | collision | 2 | 4,10 |
| R1b-B-new-cap0.35-blend0.6 | 1 | recover | collision | 2 | 2,6 |
| R1b-B-new-cap0.35-blend0.6 | 1 | search | collision | 1 | 8 |
| R1d-new-cap1.2-blend0.6 | 1 | commit | collision | 2 | 2,5 |
| R1d-new-cap1.2-blend0.6 | 1 | recover | clip_budget | 1 | 3 |
| R1d-new-cap1.2-blend0.6 | 1 | recover | collision | 1 | 1 |
| R1d-new-cap1.2-blend0.6 | 2 | recover | collision | 1 | 4 |
| R1e-new-cap1.2-blend0.9 | 1 | recover | clip_budget | 1 | 3 |
| R1e-new-cap1.2-blend0.9 | 1 | recover | collision | 2 | 1,4 |
| R1e-new-cap1.2-blend0.9 | 1 | search | collision | 2 | 2,5 |

## Missing Groups

| group | packet | pattern | expected_count | status | analysis_head |
| --- | --- | --- | --- | --- | --- |

## Artifacts

- `runs.csv`: per-run tally with closest ty, commit-entry ty list, and per-run bias median.
- `commit_entries.csv`: one row per commit entry.
- `bias_pairs_align_commit.csv`: all state/detection pairs used for the bias calculation.
- `group_summary.csv`: three-group aggregate table.
- `failure_modes.csv`: failed-gate attribution by phase and abort class.
- `missing_groups.csv`: availability at this pulled HEAD; should be empty for this full run.
