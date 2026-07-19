# Terminal A/B Mock

Role: QA & MOCK-TUNER.
Scope: mock only. No real simulator was launched, reset, clicked, or commanded.
Commit: `23813aaa9d6aa32cb5e4464ce995a6eb782d526b`.
Base harness patch: `safety.imu_stale_s=0.25`.

## Arms

| Arm | Patches | Passes | Runs | Pass rate | Finished | Terminal anomaly runs |
|---|---|---:|---:|---:|---:|---:|
| `control_speed1p8` | `--patch planner.commit.speed_mps=1.8` | 7 | 10 | 70.0% | 7 | 0 |
| `terminal_speed1p8` | `--patch planner.commit.speed_mps=1.8 --patch planner.terminal.enable=True` | 4 | 10 | 40.0% | 4 | 1 |

Interpretation: the enable arm produced `term_status` rows and often reached
`engaged`/`ready`, but `owner=term` and `v_bz_applied` stayed at zero in all
10 runs. The terminal channel was rehearsed in telemetry but did not take
vertical authority in this mock A/B.

## Term Status Notes

| Arm | Run | Gates | Finished | term rows | engaged | ready | owner=term | applied | anomalies |
|---|---:|---:|---|---:|---:|---:|---:|---:|---|
| `control_speed1p8` | 1 | 1 | True | 0 | 0 | 0 | 0 | 0 |  |
| `control_speed1p8` | 2 | 1 | True | 0 | 0 | 0 | 0 | 0 |  |
| `control_speed1p8` | 3 | 1 | True | 0 | 0 | 0 | 0 | 0 |  |
| `control_speed1p8` | 4 | 1 | True | 0 | 0 | 0 | 0 | 0 |  |
| `control_speed1p8` | 5 | 1 | True | 0 | 0 | 0 | 0 | 0 |  |
| `control_speed1p8` | 6 | 1 | True | 0 | 0 | 0 | 0 | 0 |  |
| `control_speed1p8` | 7 | 1 | True | 0 | 0 | 0 | 0 | 0 |  |
| `control_speed1p8` | 8 | 0 | False | 0 | 0 | 0 | 0 | 0 |  |
| `control_speed1p8` | 9 | 0 | False | 0 | 0 | 0 | 0 | 0 |  |
| `control_speed1p8` | 10 | 0 | False | 0 | 0 | 0 | 0 | 0 |  |
| `terminal_speed1p8` | 1 | 0 | False | 103 | 82 | 0 | 0 | 0 | engaged but oracle never ready |
| `terminal_speed1p8` | 2 | 1 | True | 124 | 85 | 80 | 0 | 0 |  |
| `terminal_speed1p8` | 3 | 0 | False | 143 | 82 | 7 | 0 | 0 |  |
| `terminal_speed1p8` | 4 | 1 | True | 134 | 76 | 91 | 0 | 0 |  |
| `terminal_speed1p8` | 5 | 1 | True | 125 | 73 | 114 | 0 | 0 |  |
| `terminal_speed1p8` | 6 | 0 | False | 177 | 89 | 33 | 0 | 0 |  |
| `terminal_speed1p8` | 7 | 0 | False | 153 | 87 | 141 | 0 | 0 |  |
| `terminal_speed1p8` | 8 | 0 | False | 180 | 119 | 135 | 0 | 0 |  |
| `terminal_speed1p8` | 9 | 1 | True | 131 | 77 | 8 | 0 | 0 |  |
| `terminal_speed1p8` | 10 | 0 | False | 119 | 79 | 105 | 0 | 0 |  |

Artifacts: `runs.csv`, `runs.json`, and per-flight logs under `tuning\runtime-logs\terminal-ab-23813aa-20260719T190107Z`.
