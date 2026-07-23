# RACE TALLY R1h

- Generated UTC: `2026-07-23T05:56:31.518966+00:00`
- Repo HEAD: `c599a0b8b4f2fd33929b9d31f5b52e47ef047c8d`
- Scope: replay/CSV only; no FlightSim/DCGame launched.
- R1h fixtures: `10` at this HEAD; prediction read: `ADJUDGED`.
- Controls included: `R1f-B-control` and `R1d-control`.
- TRUE-WORLD dz: `aigp.planning.approach.true_world_dz`, latest-state pairing; dz column is populated only for closest approaches `<= 2.5m`.

## Group Summary
| group | status | runs | pass_rate | passes | blind_NO_GATE_IN_VIEW | far_structure_hangar | blind_structure_total | near_structure | clips | grinding | median_survival_time_s | median_commit_attempts | commit_attempts_per_flight | median_closest_range_m | close_dz_n_le_2p5 | median_true_world_dz_close_m | param_ok_runs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1f-B-control | OK | 5 | 0.0000 | 0 | 0 | 1 | 1 | 3 | 0 | 1 | 12.6283 | 2.0000 | 1;2;3;2;1 | 2.0173 | 3 | -0.2921 | 5 |
| R1d-control | OK | 5 | 0.2000 | 1 | 0 | 0 | 0 | 4 | 1 | 0 | 9.9691 | 2.0000 | 2;3;1;5;1 | 0.8851 | 4 | -0.0903 | 5 |
| R1h | OK | 10 | 0.1000 | 1 | 7 | 0 | 7 | 2 | 1 | 0 | 14.5340 | 2.0000 | 1;3;2;1;2;3;3;3;1;2 | 1.6149 | 8 | -0.0863 | 10 |

## Per-Flight Table
| group | run | gates_passed | abort_bucket | survival_time_s | commit_attempts | closest_range_m | true_world_dz_at_closest_if_le_2p5_m | killing_hit_class | abort_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1d-control | 1 | 0 | near_structure | 9.9691 | 2 | 0.7145 | -0.0458 | env_NEAR_STRUCTURE_unspecified | environment collision (impulse=1.3) |
| R1d-control | 2 | 0 | near_structure | 12.4403 | 3 | 1.3799 | -0.1349 | env_NEAR_gate_LOW_likely_floor_or_bottom | environment collision (impulse=8.6) |
| R1d-control | 3 | 0 | clips | 7.6240 | 1 | 0.8851 | -0.3090 | gate_TOP_bar | gate clip budget exceeded (11) |
| R1d-control | 4 | 1 | near_structure | 18.7080 | 5 | 0.6933 | 0.3304 | env_NEAR_STRUCTURE_unspecified | environment collision (impulse=11.8) |
| R1d-control | 5 | 0 | near_structure | 7.1681 | 1 | 2.7202 |  | env_NEAR_STRUCTURE_unspecified | environment collision (impulse=3.6) |
| R1f-B-control | 2 | 0 | blind_FAR_STRUCTURE_or_hangar | 7.4841 | 1 | 4.3234 |  | env_FAR_STRUCTURE_or_hangar | environment collision (impulse=4.2) |
| R1f-B-control | 4 | 0 | near_structure | 12.6283 | 2 | 1.3366 | -0.2921 | env_NEAR_gate_LATERAL_likely_pillar_or_side_struct | environment collision (impulse=2.3) |
| R1f-B-control | 6 | 0 | near_structure | 11.9960 | 3 | 0.9486 | -0.3095 | env_NEAR_STRUCTURE_unspecified | environment collision (impulse=7.3) |
| R1f-B-control | 8 | 0 | grinding | 120.0040 | 2 | 4.0415 |  | env_NO_GATE_IN_VIEW | flight timeout |
| R1f-B-control | 10 | 0 | near_structure | 13.3801 | 1 | 2.0173 | 0.4369 | env_MID_STRUCTURE_intergate | environment collision (impulse=7.3) |
| R1h | 1 | 0 | blind_NO_GATE_IN_VIEW | 11.7000 | 1 | 3.8023 |  | env_NO_GATE_IN_VIEW | environment collision (impulse=1.2) |
| R1h | 2 | 0 | clips | 10.2528 | 3 | 1.3683 | 0.5064 | gate_OPENING_or_UNSPECIFIED | gate clip budget exceeded (11) |
| R1h | 3 | 0 | blind_NO_GATE_IN_VIEW | 17.0919 | 2 | 1.3882 | -0.2433 | env_NO_GATE_IN_VIEW | environment collision (impulse=4.9) |
| R1h | 4 | 0 | near_structure | 9.0121 | 1 | 0.9762 | -0.1006 | env_MID_STRUCTURE_intergate | environment collision (impulse=1.4) |
| R1h | 5 | 0 | blind_NO_GATE_IN_VIEW | 10.6642 | 2 | 2.0843 | 0.4227 | env_NO_GATE_IN_VIEW | environment collision (impulse=3.2) |
| R1h | 6 | 0 | blind_NO_GATE_IN_VIEW | 17.9160 | 3 | 1.0142 | -0.3374 | env_NO_GATE_IN_VIEW | environment collision (impulse=13.9) |
| R1h | 7 | 0 | blind_NO_GATE_IN_VIEW | 19.8320 | 3 | 1.8416 | -0.9877 | env_NO_GATE_IN_VIEW | environment collision (impulse=6.4) |
| R1h | 8 | 0 | blind_NO_GATE_IN_VIEW | 13.7961 | 3 | 1.8626 | 0.1817 | env_NO_GATE_IN_VIEW | environment collision (impulse=2.6) |
| R1h | 9 | 0 | blind_NO_GATE_IN_VIEW | 16.0242 | 1 | 4.5393 |  | env_NO_GATE_IN_VIEW | environment collision (impulse=2.9) |
| R1h | 10 | 1 | near_structure | 15.2720 | 2 | 0.8473 | -0.0721 | env_NEAR_gate_LOW_likely_floor_or_bottom | environment collision (impulse=7.9) |

## Registered Prediction Read
| prediction | r1h_value | control_value | verdict |
| --- | --- | --- | --- |
| blind_structure_total shrinks vs R1f-B-control | 7 | 1 | FAIL |
| median_survival_time_s rises vs R1f-B-control | 14.5340 | 12.6283 | PASS |
| blind_structure_total shrinks vs R1d-control | 7 | 0 | FAIL |
| median_survival_time_s rises vs R1d-control | 14.5340 | 9.9691 | PASS |
| passes >= 2/10 | 1 | 2 | FAIL |

## Notes
- `blind_structure_total` is `blind_NO_GATE_IN_VIEW + far_structure_hangar`, matching the plan language that paired NO_GATE_IN_VIEW with far-hangar contacts.
- `near_structure` collects env near-gate/near-structure/mid-structure collisions.
- `clips` collects gate/clip-budget aborts; `grinding` is timeout with sustained environment contact.

## Files
- `runs.csv`
- `group_summary.csv`
- `prediction_read.csv`
- `generation_info.json`
