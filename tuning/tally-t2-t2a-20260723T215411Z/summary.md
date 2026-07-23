# TALLY T2-R1 + T2a

- Generated UTC: `2026-07-23T21:54:12.706390+00:00`
- Repo HEAD: `80c4d03d8cfd8b3da411f71e754e8ced649fdc29`
- Scope: replay/CSV only; no FlightSim/DCGame launched or controlled.
- SIM lock was present but treated as simulator-launch-only per user instruction.
- TRUE-WORLD dz: `aigp.planning.approach.true_world_dz`, latest-state pairing; dz column populated only for closest approaches `<= 2.5m`.

## Group Summary
| group | status | runs | pass_rate | passes | gates_per_run | stale_imu | environment_collision | gate_clips | grinding_timeout | median_survival_time_s | median_commit_attempts | commit_attempts_per_run | median_closest_range_m | close_dz_n_le_2p5 | median_true_world_dz_close_m | param_ok_runs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T2-baseline | OK | 6 | 0.0000 | 0 | 0;0;0;0;0;0 | 4 | 2 | 0 | 0 | 32.3060 | 2.0000 | 2;2;2;2;4;2 | 1.5974 | 4 | -0.4900 | 6 |
| T2a-imu0p25 | OK | 6 | 0.3333 | 2 | 1;0;0;1;0;0 | 6 | 0 | 0 | 0 | 44.2906 | 1.5000 | 1;2;1;2;4;1 | 0.8575 | 6 | -0.0177 | 6 |

## Per-Flight Table
| group | run | gates_passed | abort_class | survival_time_s | commit_attempts | closest_range_m | true_world_dz_at_closest_if_le_2p5_m | param_integrity | killing_hit_class | abort_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T2-baseline | 1 | 0 | environment_collision | 29.5920 | 2 | 1.2419 | -0.4496 | OK | env_NO_GATE_IN_VIEW | environment collision (impulse=12.0) |
| T2-baseline | 2 | 0 | environment_collision | 27.5640 | 2 | 0.7748 | 0.0358 | OK | env_NO_GATE_IN_VIEW | environment collision (impulse=3.8) |
| T2-baseline | 3 | 0 | stale_imu | 33.7440 | 2 | 1.0144 | -0.6220 | OK | gate_BOTTOM_bar | stale channels: imu |
| T2-baseline | 4 | 0 | stale_imu | 33.8760 | 2 | 4.6879 |  | OK |  | stale channels: imu |
| T2-baseline | 5 | 0 | stale_imu | 46.2920 | 4 | 1.9530 | -0.5303 | OK |  | stale channels: imu |
| T2-baseline | 6 | 0 | stale_imu | 30.8680 | 2 | 5.6537 |  | OK |  | stale channels: imu |
| T2a-imu0p25 | 1 | 1 | stale_imu | 30.7160 | 1 | 0.6620 | -0.0416 | OK |  | stale channels: imu |
| T2a-imu0p25 | 2 | 0 | stale_imu | 51.0680 | 2 | 0.8984 | -0.0732 | OK | gate_OPENING_or_UNSPECIFIED | stale channels: imu |
| T2a-imu0p25 | 3 | 0 | stale_imu | 51.4298 | 1 | 1.7185 | 0.0250 | OK |  | stale channels: imu |
| T2a-imu0p25 | 4 | 1 | stale_imu | 36.6360 | 2 | 0.7055 | 0.0061 | OK | gate_SIDE_bar | stale channels: imu |
| T2a-imu0p25 | 5 | 0 | stale_imu | 52.5360 | 4 | 0.8166 | -0.2460 | OK |  | stale channels: imu |
| T2a-imu0p25 | 6 | 0 | stale_imu | 37.5132 | 1 | 1.4352 | 0.1671 | OK |  | stale channels: imu |

## Registered Prediction Read
| prediction | t2a_value | control_value | verdict |
| --- | --- | --- | --- |
| stale-imu abort class -> 0/6 | 6 | 0 | FAIL |
| median survival rises vs T2 baseline | 44.2906 | 32.3060 | PASS |
| commit attempts per flight rise vs T2 baseline | 1.5000 | 2.0000 | FAIL |
| >=1 gate pass in 6 | 2 | 1 | PASS |

## Files
- `runs.csv`
- `group_summary.csv`
- `prediction_read.csv`
- `generation_info.json`
