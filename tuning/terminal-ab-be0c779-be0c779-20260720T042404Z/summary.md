# Terminal A/B Mock

Role: QA & MOCK-TUNER.
Scope: mock only. No real simulator was launched, reset, clicked, or commanded.
Commit: `be0c77931e58771e1b3abed3a2e817c4a1bd95a5`.
Base harness patch: `safety.imu_stale_s=0.25`.

## Arms

| Arm | Patches | Passes | Runs | Pass rate | Finished | Terminal anomaly runs | closest R mean | lateral mean/std | true dz mean/std |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `control_speed1p8` | `--patch planner.commit.speed_mps=1.8` | 7 | 10 | 70.0% | 7 | 0 | 0.597 | 0.048/0.187 | 0.229/0.450 |
| `terminal_speed1p8` | `--patch planner.commit.speed_mps=1.8 --patch planner.terminal.enable=True` | 6 | 10 | 60.0% | 6 | 10 | 0.360 | -0.044/0.066 | 0.122/0.198 |

## Term Status Notes

| Arm | Run | Gates | Finished | term rows | engaged | ready | engaged+ready | owner=term | applied | first owner R | first applied R | e_z min/max | v_bz min/max | sign bad | owner transitions | closest y/dz | anomalies |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `control_speed1p8` | 1 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | 0.540/1.575 |  |
| `control_speed1p8` | 2 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | -0.043/0.071 |  |
| `control_speed1p8` | 3 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | -0.099/0.079 |  |
| `control_speed1p8` | 4 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | -0.087/0.054 |  |
| `control_speed1p8` | 5 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | 0.059/0.060 |  |
| `control_speed1p8` | 6 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | -0.052/0.086 |  |
| `control_speed1p8` | 7 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | 0.103/0.072 |  |
| `control_speed1p8` | 8 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | -0.148/0.068 |  |
| `control_speed1p8` | 9 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | 0.124/0.164 |  |
| `control_speed1p8` | 10 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | 0.083/0.060 |  |
| `terminal_speed1p8` | 1 | 0 | False | 367 | 51 | 233 | 51 | 0 | 0 |  |  | / | / | 0 | 0 | -0.119/0.715 | engaged+ready but owner never term |
| `terminal_speed1p8` | 2 | 0 | False | 176 | 96 | 165 | 96 | 0 | 0 |  |  | / | / | 0 | 0 | -0.071/0.055 | engaged+ready but owner never term |
| `terminal_speed1p8` | 3 | 1 | True | 115 | 56 | 97 | 48 | 0 | 0 |  |  | / | / | 0 | 0 | 0.094/0.074 | engaged+ready but owner never term |
| `terminal_speed1p8` | 4 | 1 | True | 151 | 100 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | -0.130/0.075 | engaged but oracle never ready |
| `terminal_speed1p8` | 5 | 0 | False | 118 | 98 | 108 | 98 | 0 | 0 |  |  | / | / | 0 | 0 | -0.067/0.064 | engaged+ready but owner never term |
| `terminal_speed1p8` | 6 | 1 | True | 132 | 86 | 119 | 86 | 0 | 0 |  |  | / | / | 0 | 0 | -0.025/0.047 | engaged+ready but owner never term |
| `terminal_speed1p8` | 7 | 1 | True | 128 | 119 | 115 | 115 | 0 | 0 |  |  | / | / | 0 | 0 | -0.105/0.055 | engaged+ready but owner never term |
| `terminal_speed1p8` | 8 | 0 | False | 127 | 82 | 114 | 82 | 0 | 0 |  |  | / | / | 0 | 0 | 0.001/0.042 | engaged+ready but owner never term |
| `terminal_speed1p8` | 9 | 1 | True | 132 | 87 | 10 | 2 | 0 | 0 |  |  | / | / | 0 | 0 | 0.021/0.049 | engaged+ready but owner never term |
| `terminal_speed1p8` | 10 | 1 | True | 147 | 81 | 135 | 81 | 0 | 0 |  |  | / | / | 0 | 0 | -0.039/0.044 | engaged+ready but owner never term |

## Gatekeeping Answers

- `control_speed1p8`: engaged+ready runs 0/10 (first range mean n/a); owner=term runs 0/10 (first range mean n/a, min n/a); v_bz_applied runs 0/10 (first range mean n/a); wrong-sign rows 0; owner-chatter runs 0; jitter runs 0; readiness-transient runs 0; certified-feature runs 10/10; engaged+ready/no-owner runs 0/10.
- `terminal_speed1p8`: engaged+ready runs 9/10 (first range mean 2.468m); owner=term runs 0/10 (first range mean n/a, min n/a); v_bz_applied runs 0/10 (first range mean n/a); wrong-sign rows 0; owner-chatter runs 0; jitter runs 0; readiness-transient runs 0; certified-feature runs 10/10; engaged+ready/no-owner runs 9/10.

## Verdict

NO-GO for live terminal arms: the mock live arm never actuated.

Live arm summary: owner=term rows `0`, v_bz_applied rows `0`, runs with engaged+ready `9/10`.

Interpretation: the live arm improved raw mock reliability and closest-approach dispersion versus control, but not through the terminal vertical treatment. The admission/ownership path still failed to hand off: certified features were present in `10/10` live runs and `engaged+ready` occurred in `9/10` around `2.468m`, yet the real owner stayed `alt` and no body-z override was applied.

Artifacts: `runs.csv`, `runs.json`, and per-flight logs under `tuning\runtime-logs\terminal-ab-be0c779-be0c779-20260720T042404Z`.
