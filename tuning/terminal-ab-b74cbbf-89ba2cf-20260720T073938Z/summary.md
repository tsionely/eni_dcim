# Terminal A/B Mock

Role: QA & MOCK-TUNER.
Scope: mock only. No real simulator was launched, reset, clicked, or commanded.
Commit: `89ba2cfbf51a1bc0104a92eb24acad677822e5a1`.
Base patches in BOTH arms: `--patch safety.imu_stale_s=0.25 --patch planner.terminal.pitch_cal_rad=-0.7352244724359027`.

## Mock-Domain Pitch Calibration

Measured mock `planner.terminal.pitch_cal_rad`: `-0.7352244724359027`.
Calibration source: `prior_57_commit_ticks`.
Commit ticks: `9389`; flights: `57`; median deg: `-42.12525926530975`.

## Arms

| Arm | Patches | Passes | Runs | Pass rate | Finished | Terminal anomaly runs | commit vision survival | captures by 2.2 | first capture R mean/min | closest R mean | lateral mean/std | true dz mean/std |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `control_speed1p8` | `--patch planner.commit.speed_mps=1.8` | 1 | 10 | 10.0% | 1 | 0 | 100.0% (2088/2088) | 0/10 | n/a/n/a | 0.901 | 1.021/2.388 | -5.639/11.453 |
| `terminal_speed1p8` | `--patch planner.commit.speed_mps=1.8 --patch planner.terminal.enable=True` | 1 | 10 | 10.0% | 1 | 10 | 100.0% (2433/2433) | 1/10 | 2.065m/1.864m | 1.064 | 1.249/3.714 | -8.078/23.853 |

## Commit Vision Survival Vs terminal-ab-46e9a64-46e9a64-20260720T063932Z (46e9a64)

| Arm | current survival | prior survival | delta | current captures by 2.2 | prior captures by 2.2 | current first capture R mean/min | prior first capture R mean/min |
|---|---:|---:|---:|---:|---:|---:|---:|
| `control_speed1p8` | 100.0% (2088/2088) | 100.0% (1106/1106) | 0.0% | 0/10 | 0/10 | n/a/n/a | n/a/n/a |
| `terminal_speed1p8` | 100.0% (2433/2433) | 100.0% (1602/1602) | 0.0% | 1/10 | 2/10 | 2.065m/1.864m | 2.405m/2.324m |

## Term Status Notes

| Arm | Run | Gates | Finished | term rows | engaged | ready | engaged+ready | owner=term | applied | commit vision survival | first capture R | capture by 2.2 | e_z at capture | first applied R | e_z min/max | v_bz min/max | sign bad | owner transitions | scale rejects | closest y/dz | anomalies |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `control_speed1p8` | 1 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% (169/169) |  | 0 |  |  | / | / | 0 | 0 | 0 | -0.765/-30.367 |  |
| `control_speed1p8` | 2 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% (3/3) |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.779/0.675 |  |
| `control_speed1p8` | 3 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% (385/385) |  | 0 |  |  | / | / | 0 | 0 | 0 | -0.010/-0.499 |  |
| `control_speed1p8` | 4 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% (195/195) |  | 0 |  |  | / | / | 0 | 0 | 0 | -0.182/-0.333 |  |
| `control_speed1p8` | 5 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% (157/157) |  | 0 |  |  | / | / | 0 | 0 | 0 | -0.028/-0.454 |  |
| `control_speed1p8` | 6 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% (321/321) |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.061/-0.252 |  |
| `control_speed1p8` | 7 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% (187/187) |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.002/0.129 |  |
| `control_speed1p8` | 8 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% (244/244) |  | 0 |  |  | / | / | 0 | 0 | 0 | 4.059/1.140 |  |
| `control_speed1p8` | 9 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% (128/128) |  | 0 |  |  | / | / | 0 | 0 | 0 | 7.015/-26.556 |  |
| `control_speed1p8` | 10 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% (299/299) |  | 0 |  |  | / | / | 0 | 0 | 0 | -0.723/0.124 |  |
| `terminal_speed1p8` | 1 | 0 | False | 446 | 287 | 175 | 112 | 48 | 48 | 100.0% (446/446) | 1.864 | 0 | -0.149 | 1.864 | -0.155/0.030 | -0.040/0.087 | 0 | 2 | 171 | 0.051/-0.475 | v_bz_applied while oracle not ready; v_bz sign flip jitter; readiness drop after applied; visible scale-gate rejects |
| `terminal_speed1p8` | 2 | 0 | False | 176 | 39 | 19 | 0 | 0 | 0 | 100.0% (176/176) |  | 0 |  |  | / | / | 0 | 0 | 59 | -0.718/-0.223 | ready and engagement never overlapped; visible scale-gate rejects |
| `terminal_speed1p8` | 3 | 0 | False | 590 | 187 | 79 | 0 | 0 | 0 | 100.0% (590/590) |  | 0 |  |  | / | / | 0 | 0 | 206 | 0.125/-0.458 | ready and engagement never overlapped; visible scale-gate rejects |
| `terminal_speed1p8` | 4 | 0 | False | 177 | 108 | 98 | 41 | 0 | 0 | 100.0% (177/177) |  | 0 |  |  | / | / | 0 | 0 | 30 | 12.322/-79.609 | engaged+ready but owner never term; visible scale-gate rejects |
| `terminal_speed1p8` | 5 | 0 | False | 114 | 69 | 103 | 69 | 0 | 0 | 100.0% (114/114) |  | 0 |  |  | / | / | 0 | 0 | 30 | -0.116/0.128 | engaged+ready but owner never term; visible scale-gate rejects |
| `terminal_speed1p8` | 6 | 1 | True | 245 | 184 | 124 | 86 | 55 | 55 | 100.0% (245/245) | 2.266 | 1 | -0.084 | 2.266 | -0.129/0.000 | -0.000/0.065 | 0 | 2 | 84 | 0.051/-0.634 | v_bz_applied while oracle not ready; readiness drop after applied; visible scale-gate rejects |
| `terminal_speed1p8` | 7 | 0 | False | 354 | 148 | 106 | 64 | 0 | 0 | 100.0% (354/354) |  | 0 |  |  | / | / | 0 | 0 | 120 | 0.045/-0.596 | engaged+ready but owner never term; visible scale-gate rejects |
| `terminal_speed1p8` | 8 | 0 | False | 209 | 140 | 72 | 15 | 0 | 0 | 100.0% (209/209) |  | 0 |  |  | / | / | 0 | 0 | 125 | -0.464/0.054 | engaged+ready but owner never term; visible scale-gate rejects |
| `terminal_speed1p8` | 9 | 0 | False | 122 | 70 | 107 | 70 | 0 | 0 | 100.0% (122/122) |  | 0 |  |  | / | / | 0 | 0 | 28 | 0.261/-0.678 | engaged+ready but owner never term; visible scale-gate rejects |
| `terminal_speed1p8` | 10 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | n/a (0/0) |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.928/1.714 | terminal enabled but no term_status rows |

## Gatekeeping Answers

- `control_speed1p8`: engaged+ready runs 0/10 (first range mean n/a); commit vision survival 100.0% vs 100.0% (0.0% delta); owner=term runs 0/10 (first range mean n/a, min n/a); captures by 2.2m 0/10; e_z at capture mean n/a; v_bz_applied runs 0/10 (first range mean n/a); wrong-sign rows 0; owner-chatter runs 0; jitter runs 0; readiness-transient runs 0; visible scale-reject runs 0/10; certified-feature runs 10/10; engaged+ready/no-owner runs 0/10.
- `terminal_speed1p8`: engaged+ready runs 7/10 (first range mean 2.446m); commit vision survival 100.0% vs 100.0% (0.0% delta); owner=term runs 2/10 (first range mean 2.065m, min 1.864m); captures by 2.2m 1/10; e_z at capture mean -0.117; v_bz_applied runs 2/10 (first range mean 2.065m); wrong-sign rows 0; owner-chatter runs 0; jitter runs 1; readiness-transient runs 2; visible scale-reject runs 9/10; certified-feature runs 10/10; engaged+ready/no-owner runs 5/10.

## QA Notes

- Code under test: `b74cbbf` source tree, launched from prior tuning-only HEAD `89ba2cf`.
- Baseline to beat: `46e9a64` live captures by 2.2m was `2/10`; current live captured `1/10`, so this did not beat baseline.
- Commit vision survival stayed complete in both arms: current control `100.0%`, current live `100.0%`, prior live `100.0%`.
- Live owner=term appeared in `2/10` runs with first-capture range mean/min `2.065m/1.864m`; only one of those captures was by `2.2m`.
- Applied sign rows stayed clean (`0` wrong-sign rows), but live remains blocked by one v_bz sign-flip jitter run plus visible scale-gate rejects in `9/10` live runs.

## Verdict

NO-GO for live terminal arms: v_bz sign-flip jitter observed.

Live arm summary: owner=term rows `103`, v_bz_applied rows `103`, runs with engaged+ready `7/10`, captures by 2.2m `1/10`, visible scale-reject runs `9/10`.

Artifacts: `runs.csv`, `runs.json`, and per-flight logs under `tuning\runtime-logs\terminal-ab-b74cbbf-89ba2cf-20260720T073938Z`.
