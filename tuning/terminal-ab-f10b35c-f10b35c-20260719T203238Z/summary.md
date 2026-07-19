# Terminal A/B Mock

Role: QA & MOCK-TUNER.
Scope: mock only. No real simulator was launched, reset, clicked, or commanded.
Commit: `f10b35cbae8751d02bc08f814ebccaf16b3757e3`.
Base harness patch: `safety.imu_stale_s=0.25`.

## Arms

| Arm | Patches | Passes | Runs | Pass rate | Finished | Terminal anomaly runs | closest R mean | lateral mean/std | true dz mean/std |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `control_speed1p8` | `--patch planner.commit.speed_mps=1.8` | 7 | 10 | 70.0% | 7 | 0 | 0.565 | -0.020/0.307 | 0.239/0.468 |
| `terminal_speed1p8` | `--patch planner.commit.speed_mps=1.8 --patch planner.terminal.enable=True` | 5 | 10 | 50.0% | 5 | 10 | 0.611 | -0.042/0.336 | 0.224/0.336 |

## Term Status Notes

| Arm | Run | Gates | Finished | term rows | engaged | ready | engaged+ready | owner=term | applied | first owner R | first applied R | e_z min/max | v_bz min/max | sign bad | owner transitions | closest y/dz | anomalies |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `control_speed1p8` | 1 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | -0.009/0.062 |  |
| `control_speed1p8` | 2 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | -0.057/0.067 |  |
| `control_speed1p8` | 3 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | -0.027/0.056 |  |
| `control_speed1p8` | 4 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | -0.020/0.056 |  |
| `control_speed1p8` | 5 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | 0.708/1.628 |  |
| `control_speed1p8` | 6 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | -0.032/0.055 |  |
| `control_speed1p8` | 7 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | 0.001/0.075 |  |
| `control_speed1p8` | 8 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | -0.662/0.283 |  |
| `control_speed1p8` | 9 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | -0.046/0.040 |  |
| `control_speed1p8` | 10 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | -0.052/0.068 |  |
| `terminal_speed1p8` | 1 | 0 | False | 251 | 161 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | 0.066/0.074 | engaged but oracle never ready |
| `terminal_speed1p8` | 2 | 0 | False | 136 | 71 | 124 | 71 | 0 | 0 |  |  | / | / | 0 | 0 | 0.122/0.054 | engaged+ready but owner never term |
| `terminal_speed1p8` | 3 | 0 | False | 156 | 86 | 16 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | -0.743/0.548 | ready and engagement never overlapped |
| `terminal_speed1p8` | 4 | 1 | True | 121 | 73 | 84 | 50 | 0 | 0 |  |  | / | / | 0 | 0 | -0.059/0.057 | engaged+ready but owner never term |
| `terminal_speed1p8` | 5 | 1 | True | 129 | 77 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | -0.074/0.070 | engaged but oracle never ready |
| `terminal_speed1p8` | 6 | 1 | True | 133 | 73 | 88 | 40 | 0 | 0 |  |  | / | / | 0 | 0 | -0.073/0.060 | engaged+ready but owner never term |
| `terminal_speed1p8` | 7 | 1 | True | 129 | 81 | 116 | 81 | 0 | 0 |  |  | / | / | 0 | 0 | -0.124/0.080 | engaged+ready but owner never term |
| `terminal_speed1p8` | 8 | 1 | True | 137 | 75 | 126 | 75 | 0 | 0 |  |  | / | / | 0 | 0 | -0.152/0.074 | engaged+ready but owner never term |
| `terminal_speed1p8` | 9 | 0 | False | 143 | 94 | 132 | 94 | 0 | 0 |  |  | / | / | 0 | 0 | -0.096/0.083 | engaged+ready but owner never term |
| `terminal_speed1p8` | 10 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 |  |  | / | / | 0 | 0 | 0.714/1.137 | terminal enabled but no term_status rows |

## Gatekeeping Answers

- `control_speed1p8`: engaged+ready runs 0/10 (first range mean n/a); owner=term runs 0/10 (first range mean n/a, min n/a); v_bz_applied runs 0/10 (first range mean n/a); wrong-sign rows 0; owner-chatter runs 0; jitter runs 0; readiness-transient runs 0; certified-feature runs 10/10; engaged+ready/no-owner runs 0/10.
- `terminal_speed1p8`: engaged+ready runs 6/10 (first range mean 2.465m); owner=term runs 0/10 (first range mean n/a, min n/a); v_bz_applied runs 0/10 (first range mean n/a); wrong-sign rows 0; owner-chatter runs 0; jitter runs 0; readiness-transient runs 0; certified-feature runs 10/10; engaged+ready/no-owner runs 6/10.

## Verdict

NO-GO for live terminal arms: the mock live arm never actuated.

Live arm summary: owner=term rows `0`, v_bz_applied rows `0`, runs with engaged+ready `6/10`.

Artifacts: `runs.csv`, `runs.json`, and per-flight logs under `tuning\runtime-logs\terminal-ab-f10b35c-f10b35c-20260719T203238Z`.
