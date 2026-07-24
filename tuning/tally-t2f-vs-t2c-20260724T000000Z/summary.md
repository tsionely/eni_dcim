# TALLY T2f vs T2c

- Generated UTC: `2026-07-24T06:10:03.650087+00:00`
- Repo HEAD: `5e349386fbd1f249e4fd021f5bef4340782a697e`
- Scope: replay/CSV only; no FlightSim/DCGame launched or controlled.
- SIM lock was present but treated as simulator-launch-only per user instruction.
- TRUE-WORLD dz: `aigp.planning.approach.true_world_dz`, latest-state pairing; dz column populated only for closest approaches `<= 2.5m`.
- Missing groups at HEAD: `T2f-geom-term`.

## Group Summary
| group | status | runs | pass_rate | passes | gates_per_run | class_A_retreat_on_phantom | stale_frame | stale_imu | environment_collision | gate_clips | grinding_timeout | median_survival_time_s | median_commit_attempts | commit_attempts_per_run | median_closest_range_m | close_dz_n_le_2p5 | median_true_world_dz_close_m | param_ok_runs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T2c-control | OK | 8 | 0.1250 | 1 | 0;0;0;0;0;1;0;0 | 0 | 7 | 0 | 0 | 1 | 0 | 34.8840 | 2.0000 | 2;2;2;1;0;2;2;2 | 0.8881 | 6 | -0.0138 | 8 |
| T2f-geom-term | MISSING_AT_HEAD | 0 |  |  |  |  |  |  |  |  |  |  |  |  |  | 0 |  | 0 |

## Per-Flight Table
| group | run | gates_passed | abort_class | survival_time_s | commit_attempts | closest_range_m | true_world_dz_at_closest_if_le_2p5_m | closest_phase | param_integrity | abort_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T2c-control | 1 | 0 | stale_frame | 27.5800 | 2 | 3.8075 |  | commit | OK | stale channels: frame(0.500s) |
| T2c-control | 2 | 0 | stale_frame | 35.1043 | 2 | 0.7842 | -0.0781 | recover | OK | stale channels: frame(0.500s) |
| T2c-control | 3 | 0 | stale_frame | 52.5800 | 2 | 0.6549 | 0.0150 | recover | OK | stale channels: frame(0.504s) |
| T2c-control | 4 | 0 | stale_frame | 34.7200 | 1 | 2.4882 | 0.0687 | commit | OK | stale channels: frame(0.500s) |
| T2c-control | 5 | 0 | stale_frame | 31.1281 | 0 | 6.1383 |  | approach | OK | stale channels: frame(0.504s) |
| T2c-control | 6 | 1 | stale_frame | 35.0480 | 2 | 0.7334 | -0.0311 | commit | OK | stale channels: frame(0.504s) |
| T2c-control | 7 | 0 | stale_frame | 35.2160 | 2 | 0.9920 | -0.1475 | recover | OK | stale channels: frame(0.504s) |
| T2c-control | 8 | 0 | gate_clips | 19.7742 | 2 | 0.6710 | 0.0035 | commit | OK | gate clip budget exceeded (11) |

## Registered Prediction Read
| prediction | t2f_value | control_value | verdict |
| --- | --- | --- | --- |
| passes >=3/8 vs control 1/8 | MISSING_AT_HEAD | 1 | NOT_JUDGED_MISSING_T2F |
| class-A retreat-on-phantom ZERO in T2f | MISSING_AT_HEAD | 0 | NOT_JUDGED_MISSING_T2F |
| untreated classes persist | MISSING_AT_HEAD | stale_frame=7; gate_clips=1; environment_collision=0 | NOT_JUDGED_MISSING_T2F |
| no new abort class | MISSING_AT_HEAD | classes=gate_clips;stale_frame | NOT_JUDGED_MISSING_T2F |

## Param Integrity
- T2c expected: defaults + `planner.commit.speed_mps=1.8`, `planner.commit.vz_cap_mps=1.2`, `planner.terminal.enable=false`, `safety.imu_stale_s=0.6`.
- T2f expected: T2c expected set + `planner.commit.geom_term_z_m=-0.9`, `planner.commit.geom_term_fresh_s=0.3`.
- T2f cannot be checked because no `fixtures/*raceprep-t2f-B-*` directories exist at this HEAD.

## Files
- `runs.csv`
- `group_summary.csv`
- `prediction_read.csv`
- `generation_info.json`
