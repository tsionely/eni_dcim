# Terminal A/B Mock

Role: QA & MOCK-TUNER.
Scope: mock only. No real simulator was launched, reset, clicked, or commanded.
Commit: `17fb31e94f06c002b18f176250037c60ae016e64`.
Base patches in BOTH arms: `--patch safety.imu_stale_s=0.25 --patch planner.terminal.pitch_cal_rad=-0.7352244724359027`.

## Mock-Domain Pitch Calibration

Measured mock `planner.terminal.pitch_cal_rad`: `-0.7352244724359027`.
Calibration source: `prior_57_commit_ticks`.
Commit ticks: `9389`; flights: `57`; median deg: `-42.12525926530975`.

## Arms

| Arm | Patches | Passes | Runs | Pass rate | Finished | Terminal anomaly runs | commit vision survival | captures by 2.2 | first capture R mean/min | closest R mean | lateral mean/std | true dz mean/std |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `control_speed1p8` | `--patch planner.commit.speed_mps=1.8` | 1 | 10 | 10.0% | 1 | 0 | 100.0% (3187/3187) | 0/10 | n/a/n/a | 0.370 | -0.125/1.638 | -12.826/27.541 |
| `terminal_speed1p8` | `--patch planner.commit.speed_mps=1.8 --patch planner.terminal.enable=True` | 0 | 10 | 0.0% | 0 | 10 | 100.0% (2897/2897) | 2/10 | 2.269m/2.114m | 0.862 | 0.723/2.594 | -24.163/50.217 |

## Commit Vision Survival Vs terminal-ab-b74cbbf-89ba2cf-20260720T073938Z (89ba2cf)

| Arm | current survival | prior survival | delta | current captures by 2.2 | prior captures by 2.2 | current first capture R mean/min | prior first capture R mean/min |
|---|---:|---:|---:|---:|---:|---:|---:|
| `control_speed1p8` | 100.0% (3187/3187) | 100.0% (2088/2088) | 0.0% | 0/10 | 0/10 | n/a/n/a | n/a/n/a |
| `terminal_speed1p8` | 100.0% (2897/2897) | 100.0% (2433/2433) | 0.0% | 2/10 | 1/10 | 2.269m/2.114m | 2.065m/1.864m |

## Term Status Notes

| Arm | Run | Gates | Finished | term rows | engaged | ready | ready legacy | engaged+ready | engaged+legacy | source FULL/SIDE | owner=term | applied | commit vision survival | first capture R | capture by 2.2 | e_z at capture | first applied R | e_z min/max | v_bz min/max | sign bad | owner transitions | scale rejects | closest y/dz | anomalies |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `control_speed1p8` | 1 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | 0 | 0 | 100.0% (304/304) |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.247/-0.457 |  |
| `control_speed1p8` | 2 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | 0 | 0 | 100.0% (436/436) |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.177/-0.339 |  |
| `control_speed1p8` | 3 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | 0 | 0 | 100.0% (344/344) |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.129/-0.470 |  |
| `control_speed1p8` | 4 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | 0 | 0 | 100.0% (191/191) |  | 0 |  |  | / | / | 0 | 0 | 0 | -4.306/-88.892 |  |
| `control_speed1p8` | 5 | 1 | True | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | 0 | 0 | 100.0% (216/216) |  | 0 |  |  | / | / | 0 | 0 | 0 | -0.206/-0.215 |  |
| `control_speed1p8` | 6 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | 0 | 0 | 100.0% (215/215) |  | 0 |  |  | / | / | 0 | 0 | 0 | 2.861/-36.428 |  |
| `control_speed1p8` | 7 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | 0 | 0 | 100.0% (998/998) |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.017/-0.558 |  |
| `control_speed1p8` | 8 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | 0 | 0 | 100.0% (135/135) |  | 0 |  |  | / | / | 0 | 0 | 0 | -0.287/-0.349 |  |
| `control_speed1p8` | 9 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | 0 | 0 | 100.0% (135/135) |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.154/-0.123 |  |
| `control_speed1p8` | 10 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 0/0 | 0 | 0 | 100.0% (213/213) |  | 0 |  |  | / | / | 0 | 0 | 0 | -0.035/-0.432 |  |
| `terminal_speed1p8` | 1 | 0 | False | 80 | 75 | 18 | 18 | 18 | 18 | 80/0 | 56 | 56 | 100.0% (80/80) | 2.114 | 0 | 0.073 | 2.114 | 0.000/0.163 | -0.088/-0.000 | 0 | 1 | 18 | 0.147/-0.657 | v_bz_applied while oracle not ready; readiness drop after applied; visible scale-gate rejects |
| `terminal_speed1p8` | 2 | 0 | False | 1069 | 409 | 487 | 164 | 80 | 23 | 1069/0 | 86 | 86 | 100.0% (1069/1069) | 2.213 | 1 | -0.134 | 2.213 | -0.225/0.011 | -0.010/0.076 | 0 | 4 | 186 | -0.161/-0.635 | v_bz_applied while oracle not ready; readiness drop after applied; visible scale-gate rejects |
| `terminal_speed1p8` | 3 | 0 | False | 242 | 128 | 58 | 0 | 0 | 0 | 242/0 | 0 | 0 | 100.0% (242/242) |  | 0 |  |  | / | / | 0 | 0 | 75 | -0.300/-0.261 | ready and engagement never overlapped; visible scale-gate rejects |
| `terminal_speed1p8` | 4 | 0 | False | 140 | 67 | 128 | 128 | 67 | 67 | 140/0 | 0 | 0 | 100.0% (140/140) |  | 0 |  |  | / | / | 0 | 0 | 36 | 0.116/-0.480 | engaged+ready but owner never term; visible scale-gate rejects |
| `terminal_speed1p8` | 5 | 0 | False | 164 | 101 | 117 | 117 | 67 | 67 | 164/0 | 0 | 0 | 100.0% (164/164) |  | 0 |  |  | / | / | 0 | 0 | 36 | 0.258/-0.398 | engaged+ready but owner never term; visible scale-gate rejects |
| `terminal_speed1p8` | 6 | 0 | False | 212 | 28 | 164 | 47 | 28 | 0 | 212/0 | 0 | 0 | 100.0% (212/212) |  | 0 |  |  | / | / | 0 | 0 | 66 | -0.071/-0.056 | engaged+ready but owner never term; visible scale-gate rejects |
| `terminal_speed1p8` | 7 | 0 | False | 178 | 86 | 17 | 17 | 0 | 0 | 178/0 | 0 | 0 | 100.0% (178/178) |  | 0 |  |  | / | / | 0 | 0 | 0 | 1.291/0.314 | ready and engagement never overlapped |
| `terminal_speed1p8` | 8 | 0 | False | 251 | 84 | 179 | 179 | 60 | 60 | 251/0 | 0 | 0 | 100.0% (251/251) |  | 0 |  |  | / | / | 0 | 0 | 51 | -3.379/-85.856 | engaged+ready but owner never term; visible scale-gate rejects |
| `terminal_speed1p8` | 9 | 0 | False | 298 | 234 | 45 | 45 | 7 | 7 | 298/0 | 59 | 54 | 100.0% (298/298) | 2.481 | 1 | 0.051 | 2.481 | 0.000/0.103 | -0.067/-0.000 | 0 | 2 | 12 | 7.463/-153.893 | v_bz_applied while oracle not ready; readiness drop after applied; visible scale-gate rejects |
| `terminal_speed1p8` | 10 | 0 | False | 263 | 106 | 76 | 76 | 0 | 0 | 263/0 | 0 | 0 | 100.0% (263/263) |  | 0 |  |  | / | / | 0 | 0 | 0 | 1.870/0.296 | ready and engagement never overlapped |

## Gatekeeping Answers

- `control_speed1p8`: engaged+ready runs 0/10 (first range mean n/a); commit vision survival 100.0% vs 100.0% (0.0% delta); owner=term runs 0/10 (first range mean n/a, min n/a); captures by 2.2m 0/10; e_z at capture mean n/a; v_bz_applied runs 0/10 (first range mean n/a); wrong-sign rows 0; owner-chatter runs 0; jitter runs 0; readiness-transient runs 0; visible scale-reject runs 0/10; certified-feature runs 10/10; ready_legacy runs 0/10; ready current-only rows 0; ready legacy-only rows 0; source_mode FULL/SIDE rows 0/0; owner SIDE rows 0; engaged+ready/no-owner runs 0/10.
- `terminal_speed1p8`: engaged+ready runs 7/10 (first range mean 2.432m); commit vision survival 100.0% vs 100.0% (0.0% delta); owner=term runs 3/10 (first range mean 2.269m, min 2.114m); captures by 2.2m 2/10; e_z at capture mean -0.003; v_bz_applied runs 3/10 (first range mean 2.269m); wrong-sign rows 0; owner-chatter runs 1; jitter runs 0; readiness-transient runs 3; visible scale-reject runs 8/10; certified-feature runs 10/10; ready_legacy runs 9/10; ready current-only rows 498; ready legacy-only rows 0; source_mode FULL/SIDE rows 2897/0; owner SIDE rows 0; engaged+ready/no-owner runs 4/10.

## QA Notes

- New gatekeeping columns are present in `runs.csv` and the per-flight live CSVs: `source_mode` and `ready_legacy`.
- Mock live captures by 2.2m improved from the prior b74cbbf run (`1/10`) to `2/10`, but this is still not a GO signal.
- `source_mode` never left `FULL_QUAD` in the mock A/B (`2897/0` FULL/SIDE rows), so this A/B does not exercise SIDE ownership.
- `ready_legacy` appeared in 9/10 live runs, while the fresh-tail semantic produced 498 current-only ready rows and 0 legacy-only rows.

## Verdict

NO-GO for live terminal arms: owner chatter observed.

Live arm summary: owner=term rows `201`, v_bz_applied rows `196`, runs with engaged+ready `7/10`, captures by 2.2m `2/10`, visible scale-reject runs `8/10`.

Artifacts: `runs.csv`, `runs.json`, and per-flight logs under `tuning\runtime-logs\terminal-ab-7b2626b-17fb31e-20260720T081707Z`.
