# Terminal A/B Mock

Role: QA & MOCK-TUNER.
Scope: mock only. No real simulator was launched, reset, clicked, or commanded.
Commit: `e16d5068cabf6579c38304ed2eb3c98a1587e5b2`.
Base patches in BOTH arms: `--patch safety.imu_stale_s=0.25 --patch planner.terminal.pitch_cal_rad=-0.7352244724359027`.

## Mock-Domain Pitch Calibration

Measured mock `planner.terminal.pitch_cal_rad`: `-0.7352244724359027`.
Calibration source: `prior terminal-ab 23813aa/f10b35c/be0c779 mock logs at 1.8; setpoint.phase=commit`.
Commit ticks: `9389`; flights: `57`; median deg: `-42.12525926530975`.

## Arms

| Arm | Patches | Passes | Runs | Pass rate | Finished | Terminal anomaly runs | closest R mean | lateral mean/std | true dz mean/std |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `control_speed1p8` | `--patch planner.commit.speed_mps=1.8` | 9 | 10 | 90.0% | 9 | 0 | 0.099 | 0.006/0.075 | 0.052/0.045 |
| `terminal_speed1p8` | `--patch planner.commit.speed_mps=1.8 --patch planner.terminal.enable=True` | 4 | 10 | 40.0% | 4 | 10 | 0.068 | -0.051/0.085 | 0.025/0.076 |

## Term Status Notes

| Arm | Run | Gates | Finished | term rows | engaged | ready | engaged+ready | owner=term | applied | first capture R | capture by 2.2 | e_z at capture | first applied R | e_z min/max | v_bz min/max | sign bad | owner transitions | scale rejects | closest y/dz | anomalies |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `control_speed1p8` | 1 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.098/0.040 |  |
| `control_speed1p8` | 2 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.087/0.070 |  |
| `control_speed1p8` | 3 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.073/0.064 |  |
| `control_speed1p8` | 4 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.025/0.059 |  |
| `control_speed1p8` | 5 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.078/0.108 |  |
| `control_speed1p8` | 6 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 0 | -0.086/0.075 |  |
| `control_speed1p8` | 7 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 0 | -0.044/0.058 |  |
| `control_speed1p8` | 8 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 0 | -0.000/0.070 |  |
| `control_speed1p8` | 9 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 0 | -0.128/-0.071 |  |
| `control_speed1p8` | 10 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 0 | -0.046/0.043 |  |
| `terminal_speed1p8` | 1 | 0 | False | 170 | 101 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 133 | -0.051/0.081 | engaged but oracle never ready; visible scale-gate rejects |
| `terminal_speed1p8` | 2 | 1 | True | 162 | 99 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 126 | 0.084/0.050 | engaged but oracle never ready; visible scale-gate rejects |
| `terminal_speed1p8` | 3 | 0 | False | 167 | 123 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 112 | -0.122/0.119 | engaged but oracle never ready; visible scale-gate rejects |
| `terminal_speed1p8` | 4 | 0 | False | 611 | 267 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 610 | -0.055/-0.071 | engaged but oracle never ready; visible scale-gate rejects |
| `terminal_speed1p8` | 5 | 1 | True | 161 | 93 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 131 | -0.089/0.055 | engaged but oracle never ready; visible scale-gate rejects |
| `terminal_speed1p8` | 6 | 0 | False | 147 | 85 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 131 | 0.037/0.113 | engaged but oracle never ready; visible scale-gate rejects |
| `terminal_speed1p8` | 7 | 1 | True | 157 | 94 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 118 | -0.150/0.077 | engaged but oracle never ready; visible scale-gate rejects |
| `terminal_speed1p8` | 8 | 0 | False | 232 | 95 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 93 | -0.127/-0.025 | engaged but oracle never ready; visible scale-gate rejects |
| `terminal_speed1p8` | 9 | 0 | False | 146 | 85 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 109 | -0.120/-0.106 | engaged but oracle never ready; visible scale-gate rejects |
| `terminal_speed1p8` | 10 | 1 | True | 157 | 84 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 140 | 0.088/-0.042 | engaged but oracle never ready; visible scale-gate rejects |

## Gatekeeping Answers

- `control_speed1p8`: engaged+ready runs 0/10 (first range mean n/a); owner=term runs 0/10 (first range mean n/a, min n/a); captures by 2.2m 0/10; e_z at capture mean n/a; v_bz_applied runs 0/10 (first range mean n/a); wrong-sign rows 0; owner-chatter runs 0; jitter runs 0; readiness-transient runs 0; visible scale-reject runs 0/10; certified-feature runs 10/10; engaged+ready/no-owner runs 0/10.
- `terminal_speed1p8`: engaged+ready runs 0/10 (first range mean n/a); owner=term runs 0/10 (first range mean n/a, min n/a); captures by 2.2m 0/10; e_z at capture mean n/a; v_bz_applied runs 0/10 (first range mean n/a); wrong-sign rows 0; owner-chatter runs 0; jitter runs 0; readiness-transient runs 0; visible scale-reject runs 10/10; certified-feature runs 10/10; engaged+ready/no-owner runs 0/10.

## Verdict

NO-GO for live terminal arms: the mock live arm never actuated.

Live arm summary: owner=term rows `0`, v_bz_applied rows `0`, runs with engaged+ready `0/10`, captures by 2.2m `0/10`.

Interpretation: Task 1 confirms the mock-domain pitch calibration is far from the real graze trim (`-0.7352244724359027` rad vs `-0.33`). With that calibration patched into both arms, the previous clamp/owner artifact is gone, but this `e16d506` A/B still does not reach treatment: the oracle never becomes ready in the live arm because visible scale-gate rejection fires in `10/10` live runs. The per-flight term_status CSVs show `span_x_range` below the 300 lower bound on the live samples, so K1 fails before ownership: first-capture range is n/a, capture by 2.2m is `0/10`, and no `e_z_at_capture` or sign check is available.

Artifacts: `runs.csv`, `runs.json`, and per-flight logs under `tuning\runtime-logs\terminal-ab-e16d506-e16d506-20260720T054614Z`.
