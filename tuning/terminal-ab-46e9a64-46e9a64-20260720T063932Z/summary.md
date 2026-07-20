# Terminal A/B Mock

Role: QA & MOCK-TUNER.
Scope: mock only. No real simulator was launched, reset, clicked, or commanded.
Commit: `46e9a644ef4e24a5229a74a49b0ba33b73c1bb80`.
Base patches in BOTH arms: `--patch safety.imu_stale_s=0.25 --patch planner.terminal.pitch_cal_rad=-0.7352244724359027`.

## Mock-Domain Pitch Calibration

Measured mock `planner.terminal.pitch_cal_rad`: `-0.7352244724359027`.
Calibration source: `prior_57_commit_ticks`.
Commit ticks: `9389`; flights: `57`; median deg: `-42.12525926530975`.

## Arms

| Arm | Patches | Passes | Runs | Pass rate | Finished | Terminal anomaly runs | closest R mean | lateral mean/std | true dz mean/std |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `control_speed1p8` | `--patch planner.commit.speed_mps=1.8` | 6 | 10 | 60.0% | 6 | 0 | 0.771 | 0.110/0.246 | 0.196/0.321 |
| `terminal_speed1p8` | `--patch planner.commit.speed_mps=1.8 --patch planner.terminal.enable=True` | 4 | 10 | 40.0% | 4 | 10 | 0.322 | -0.051/0.159 | -0.038/0.299 |

## Term Status Notes

| Arm | Run | Gates | Finished | term rows | engaged | ready | engaged+ready | owner=term | applied | first capture R | capture by 2.2 | e_z at capture | first applied R | e_z min/max | v_bz min/max | sign bad | owner transitions | scale rejects | closest y/dz | anomalies |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `control_speed1p8` | 1 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.006/-0.018 |  |
| `control_speed1p8` | 2 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 0 | -0.028/0.064 |  |
| `control_speed1p8` | 3 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.028/0.026 |  |
| `control_speed1p8` | 4 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 0 | -0.084/0.046 |  |
| `control_speed1p8` | 5 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.019/0.035 |  |
| `control_speed1p8` | 6 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.684/0.796 |  |
| `control_speed1p8` | 7 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.042/0.020 |  |
| `control_speed1p8` | 8 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.002/0.026 |  |
| `control_speed1p8` | 9 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.491/0.875 |  |
| `control_speed1p8` | 10 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 0 | -0.061/0.089 |  |
| `terminal_speed1p8` | 1 | 1 | True | 111 | 66 | 81 | 48 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 3 | 0.174/0.069 | engaged+ready but owner never term; visible scale-gate rejects |
| `terminal_speed1p8` | 2 | 0 | False | 162 | 131 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 25 | -0.070/0.067 | engaged but oracle never ready; visible scale-gate rejects |
| `terminal_speed1p8` | 3 | 0 | False | 143 | 63 | 26 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 11 | -0.367/0.237 | ready and engagement never overlapped; visible scale-gate rejects |
| `terminal_speed1p8` | 4 | 1 | True | 153 | 74 | 141 | 74 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 14 | -0.065/0.066 | engaged+ready but owner never term; visible scale-gate rejects |
| `terminal_speed1p8` | 5 | 1 | True | 140 | 87 | 0 | 0 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 14 | 0.070/0.059 | engaged but oracle never ready; visible scale-gate rejects |
| `terminal_speed1p8` | 6 | 0 | False | 294 | 123 | 55 | 6 | 65 | 65 | 2.487 | 1 | 0.124 | 2.487 | 0.000/0.124 | -0.065/-0.000 | 0 | 2 | 102 | -0.240/-0.564 | v_bz_applied while oracle not ready; readiness drop after applied; visible scale-gate rejects |
| `terminal_speed1p8` | 7 | 0 | False | 150 | 90 | 64 | 15 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 17 | -0.105/0.122 | engaged+ready but owner never term; visible scale-gate rejects |
| `terminal_speed1p8` | 8 | 0 | False | 179 | 121 | 62 | 18 | 39 | 39 | 2.324 | 1 | 0.140 | 2.324 | 0.140/0.323 | -0.127/-0.067 | 0 | 2 | 70 | -0.085/-0.687 | v_bz_applied while oracle not ready; readiness drop after applied; visible scale-gate rejects |
| `terminal_speed1p8` | 9 | 1 | True | 124 | 68 | 113 | 68 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 9 | 0.153/0.123 | engaged+ready but owner never term; visible scale-gate rejects |
| `terminal_speed1p8` | 10 | 0 | False | 146 | 89 | 132 | 89 | 0 | 0 |  | 0 |  |  | / | / | 0 | 0 | 16 | 0.021/0.123 | engaged+ready but owner never term; visible scale-gate rejects |

## Gatekeeping Answers

- `control_speed1p8`: engaged+ready runs 0/10 (first range mean n/a); owner=term runs 0/10 (first range mean n/a, min n/a); captures by 2.2m 0/10; e_z at capture mean n/a; v_bz_applied runs 0/10 (first range mean n/a); wrong-sign rows 0; owner-chatter runs 0; jitter runs 0; readiness-transient runs 0; visible scale-reject runs 0/10; certified-feature runs 10/10; engaged+ready/no-owner runs 0/10.
- `terminal_speed1p8`: engaged+ready runs 7/10 (first range mean 2.473m); owner=term runs 2/10 (first range mean 2.405m, min 2.324m); captures by 2.2m 2/10; e_z at capture mean 0.132; v_bz_applied runs 2/10 (first range mean 2.405m); wrong-sign rows 0; owner-chatter runs 0; jitter runs 0; readiness-transient runs 2; visible scale-reject runs 10/10; certified-feature runs 10/10; engaged+ready/no-owner runs 5/10.

## QA Notes

- Scaled 320x180 mock band mirrored from `46e9a64`: honest product `256 px*m`, accepted range `151.04..399.36 px*m`.
- Live captures occurred only in runs 6 and 8: R=`2.486857m`, e_z=`0.123694`, v_bz=`-0.064291`; R=`2.324012m`, e_z=`0.139723`, v_bz=`-0.066600`.
- Sign check passed where terminal acted: `0` applied sign-mismatch rows and `0` vz_up sign-mismatch rows.
- K1 failed: captures by 2.2m were `2/10`, below the `>=7/10` bar.
- Scale-gate rejects remained visible in `10/10` live runs, `281` rows total. In the two capture runs, rejects before capture were `0`, so the remaining rejects are late/no-capture evidence rather than pre-capture clamp evidence.

## Verdict

NO-GO for live terminal gatekeeping: authority wiring actuated with correct sign, but K1/scale-gate criteria failed.

Live arm summary: owner=term rows `104`, v_bz_applied rows `104`, runs with engaged+ready `7/10`, captures by 2.2m `2/10`.

Visible scale-reject runs: `10/10`.

Artifacts: `runs.csv`, `runs.json`, and per-flight logs under `tuning\runtime-logs\terminal-ab-46e9a64-46e9a64-20260720T063932Z`.
