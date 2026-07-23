# RACE TALLY R1i

- Generated UTC: `2026-07-23T08:51:28.744102+00:00`
- Repo HEAD: `0bf62b0061b4967ed13a00b0a186c59c54c12555`
- `d95bbc2` ancestor: `True`
- Scope: replay/CSV only; no FlightSim/DCGame launched.
- R1i fixtures: `10` at this HEAD.
- Controls included: `R1d-control` and `R1h-control`.
- TRUE-WORLD dz: `aigp.planning.approach.true_world_dz`, latest-state pairing; dz column is populated only for closest approaches `<= 2.5m`.

## Group Summary
| group | status | runs | pass_rate | passes | gates_per_run | blind_NO_GATE_IN_VIEW | far_structure_hangar | near_structure | gate_clips | grinding_timeout | median_survival_time_s | median_commit_attempts | commit_attempts_per_flight | median_closest_range_m | close_dz_n_le_2p5 | median_true_world_dz_close_m | param_ok_runs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1d-control | OK | 5 | 0.2000 | 1 | 0;0;0;1;0 | 0 | 0 | 4 | 1 | 0 | 9.9691 | 2.0000 | 2;3;1;5;1 | 0.8851 | 4 | -0.0903 | 5 |
| R1h-control | OK | 10 | 0.1000 | 1 | 0;0;0;0;0;0;0;0;0;1 | 7 | 0 | 2 | 1 | 0 | 14.5340 | 2.0000 | 1;3;2;1;2;3;3;3;1;2 | 1.6149 | 8 | -0.0863 | 10 |
| R1i | OK | 10 | 0.0000 | 0 | 0;0;0;0;0;0;0;0;0;0 | 2 | 2 | 5 | 1 | 0 | 9.6803 | 2.0000 | 1;1;1;2;2;2;1;5;3;3 | 1.2885 | 9 | -0.0777 | 10 |

## Per-Flight Table
| group | run | gates_passed | abort_bucket | survival_time_s | commit_attempts | closest_range_m | true_world_dz_at_closest_if_le_2p5_m | param_integrity | killing_hit_class | abort_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1d-control | 1 | 0 | near_structure | 9.9691 | 2 | 0.7145 | -0.0458 | NOT_CHECKED_CONTROL | env_NEAR_STRUCTURE_unspecified | environment collision (impulse=1.3) |
| R1d-control | 2 | 0 | near_structure | 12.4403 | 3 | 1.3799 | -0.1349 | NOT_CHECKED_CONTROL | env_NEAR_gate_LOW_likely_floor_or_bottom | environment collision (impulse=8.6) |
| R1d-control | 3 | 0 | gate_clips | 7.6240 | 1 | 0.8851 | -0.3090 | NOT_CHECKED_CONTROL | gate_TOP_bar | gate clip budget exceeded (11) |
| R1d-control | 4 | 1 | near_structure | 18.7080 | 5 | 0.6933 | 0.3304 | NOT_CHECKED_CONTROL | env_NEAR_STRUCTURE_unspecified | environment collision (impulse=11.8) |
| R1d-control | 5 | 0 | near_structure | 7.1681 | 1 | 2.7202 |  | NOT_CHECKED_CONTROL | env_NEAR_STRUCTURE_unspecified | environment collision (impulse=3.6) |
| R1h-control | 1 | 0 | blind_NO_GATE_IN_VIEW | 11.7000 | 1 | 3.8023 |  | NOT_CHECKED_CONTROL | env_NO_GATE_IN_VIEW | environment collision (impulse=1.2) |
| R1h-control | 2 | 0 | gate_clips | 10.2528 | 3 | 1.3683 | 0.5064 | NOT_CHECKED_CONTROL | gate_OPENING_or_UNSPECIFIED | gate clip budget exceeded (11) |
| R1h-control | 3 | 0 | blind_NO_GATE_IN_VIEW | 17.0919 | 2 | 1.3882 | -0.2433 | NOT_CHECKED_CONTROL | env_NO_GATE_IN_VIEW | environment collision (impulse=4.9) |
| R1h-control | 4 | 0 | near_structure | 9.0121 | 1 | 0.9762 | -0.1006 | NOT_CHECKED_CONTROL | env_MID_STRUCTURE_intergate | environment collision (impulse=1.4) |
| R1h-control | 5 | 0 | blind_NO_GATE_IN_VIEW | 10.6642 | 2 | 2.0843 | 0.4227 | NOT_CHECKED_CONTROL | env_NO_GATE_IN_VIEW | environment collision (impulse=3.2) |
| R1h-control | 6 | 0 | blind_NO_GATE_IN_VIEW | 17.9160 | 3 | 1.0142 | -0.3374 | NOT_CHECKED_CONTROL | env_NO_GATE_IN_VIEW | environment collision (impulse=13.9) |
| R1h-control | 7 | 0 | blind_NO_GATE_IN_VIEW | 19.8320 | 3 | 1.8416 | -0.9877 | NOT_CHECKED_CONTROL | env_NO_GATE_IN_VIEW | environment collision (impulse=6.4) |
| R1h-control | 8 | 0 | blind_NO_GATE_IN_VIEW | 13.7961 | 3 | 1.8626 | 0.1817 | NOT_CHECKED_CONTROL | env_NO_GATE_IN_VIEW | environment collision (impulse=2.6) |
| R1h-control | 9 | 0 | blind_NO_GATE_IN_VIEW | 16.0242 | 1 | 4.5393 |  | NOT_CHECKED_CONTROL | env_NO_GATE_IN_VIEW | environment collision (impulse=2.9) |
| R1h-control | 10 | 1 | near_structure | 15.2720 | 2 | 0.8473 | -0.0721 | NOT_CHECKED_CONTROL | env_NEAR_gate_LOW_likely_floor_or_bottom | environment collision (impulse=7.9) |
| R1i | 1 | 0 | far_structure_hangar | 13.3280 | 1 | 1.5994 | 0.7280 | OK | env_FAR_STRUCTURE_or_hangar | environment collision (impulse=5.4) |
| R1i | 2 | 0 | near_structure | 5.8680 | 1 | 3.1044 |  | OK | env_NEAR_gate_LOW_likely_floor_or_bottom | environment collision (impulse=1.9) |
| R1i | 3 | 0 | gate_clips | 7.2760 | 1 | 0.8567 | -0.0777 | OK | gate_TOP_bar | gate clip budget exceeded (11) |
| R1i | 4 | 0 | far_structure_hangar | 7.8240 | 2 | 1.8961 | 0.7041 | OK | env_FAR_STRUCTURE_or_hangar | environment collision (impulse=1.1) |
| R1i | 5 | 0 | blind_NO_GATE_IN_VIEW | 9.4720 | 2 | 2.2515 | 0.7298 | OK | env_NO_GATE_IN_VIEW | environment collision (impulse=2.2) |
| R1i | 6 | 0 | blind_NO_GATE_IN_VIEW | 14.8120 | 2 | 0.6791 | 0.0322 | OK | env_NO_GATE_IN_VIEW | environment collision (impulse=1.1) |
| R1i | 7 | 0 | near_structure | 9.7284 | 1 | 1.2123 | -0.8768 | OK | env_NEAR_gate_LOW_likely_floor_or_bottom | environment collision (impulse=3.2) |
| R1i | 8 | 0 | near_structure | 28.1880 | 5 | 1.2829 | -0.9903 | OK | env_NEAR_gate_LOW_likely_floor_or_bottom | environment collision (impulse=2.0) |
| R1i | 9 | 0 | near_structure | 20.7789 | 3 | 1.2941 | -0.1612 | OK | env_NEAR_gate_LOW_likely_floor_or_bottom | environment collision (impulse=4.7) |
| R1i | 10 | 0 | near_structure | 9.6321 | 3 | 0.9371 | -0.2034 | OK | env_NEAR_gate_LOW_likely_floor_or_bottom | environment collision (impulse=2.4) |

## Registered Prediction Read
| prediction | r1i_value | control_value | verdict |
| --- | --- | --- | --- |
| blind_NO_GATE_IN_VIEW shrinks vs R1h 7/10 | 2 | 7 | PASS |
| blind_NO_GATE_IN_VIEW + far_structure_hangar shrinks vs R1h 7/10 | 4 | 7 | PASS |
| pass rate >= 2/10 | 0 | 2 | FAIL |

## Notes
- Abort split columns requested by the round are `blind_NO_GATE_IN_VIEW`, `near_structure`, `gate_clips`, and `grinding_timeout`. `far_structure_hangar` is retained as a supporting column because it occurred in two R1i runs.
- R1i param integrity flags any leftover R1h approach speeds (`1.5/1.0`); all `OK` means approach speeds are back to defaults (`3.0/1.5`).

## Files
- `runs.csv`
- `group_summary.csv`
- `prediction_read.csv`
- `generation_info.json`
