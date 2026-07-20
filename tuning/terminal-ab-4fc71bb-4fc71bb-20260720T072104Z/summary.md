# Terminal A/B Mock

Role: QA & MOCK-TUNER.
Scope: mock only. No real simulator was launched, reset, clicked, or commanded.
Commit: `4fc71bb671d2d33a518606a7a869f9a8c8203622`.
Base patches in BOTH arms: `--patch safety.imu_stale_s=0.25 --patch planner.terminal.pitch_cal_rad=-0.7352244724359027`.

## Mock-Domain Pitch Calibration

Measured mock `planner.terminal.pitch_cal_rad`: `-0.7352244724359027`.
Calibration source: `prior_57_commit_ticks`.
Commit ticks: `9389`; flights: `57`; median deg: `-42.12525926530975`.

## Arms

| Arm | Patches | Passes | Runs | Pass rate | Finished | Terminal anomaly runs | commit vision survival | captures by 2.2 | closest R mean | lateral mean/std | true dz mean/std |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `control_speed1p8` | `--patch planner.commit.speed_mps=1.8` | 0 | 10 | 0.0% | 0 | 0 | 100.0% (3315/3315) | 0/10 | 1.055 | 0.402/0.899 | -5.525/16.350 |
| `terminal_speed1p8` | `--patch planner.commit.speed_mps=1.8 --patch planner.terminal.enable=True` | 0 | 10 | 0.0% | 0 | 8 | 100.0% (1465/1465) | 0/10 | 1.586 | 0.197/1.414 | -1.799/4.160 |

## Commit Vision Survival Vs terminal-ab-46e9a64-46e9a64-20260720T063932Z (46e9a64)

| Arm | current survival | prior survival | delta | current captures by 2.2 | prior captures by 2.2 |
|---|---:|---:|---:|---:|---:|
| `control_speed1p8` | 100.0% (3315/3315) | 100.0% (1106/1106) | 0.0% | 0/10 | 0/10 |
| `terminal_speed1p8` | 100.0% (1465/1465) | 100.0% (1602/1602) | 0.0% | 0/10 | 2/10 |

## Term Status Notes

| Arm | Run | Gates | Finished | term rows | engaged | ready | engaged+ready | owner=term | applied | commit vision survival | first capture R | capture by 2.2 | e_z at capture | first applied R | e_z min/max | v_bz min/max | sign bad | owner transitions | scale rejects | closest y/dz | anomalies |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `control_speed1p8` | 1 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% (154/154) |  | 0 |  |  | / | / | 0 | 0 | 0 | 2.927/-54.544 |  |
| `control_speed1p8` | 2 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% (268/268) |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.115/-0.367 |  |
| `control_speed1p8` | 3 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% (180/180) |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.258/-0.212 |  |
| `control_speed1p8` | 4 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% (14/14) |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.500/0.544 |  |
| `control_speed1p8` | 5 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% (789/789) |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.044/-0.175 |  |
| `control_speed1p8` | 6 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% (178/178) |  | 0 |  |  | / | / | 0 | 0 | 0 | -0.655/1.311 |  |
| `control_speed1p8` | 7 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% (1030/1030) |  | 0 |  |  | / | / | 0 | 0 | 0 | -0.023/-0.728 |  |
| `control_speed1p8` | 8 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% (165/165) |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.496/0.013 |  |
| `control_speed1p8` | 9 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% (157/157) |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.356/-0.320 |  |
| `control_speed1p8` | 10 | 0 | False | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% (380/380) |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.004/-0.770 |  |
| `terminal_speed1p8` | 1 | 0 | False | 393 | 221 | 99 | 32 | 54 | 54 | 100.0% (393/393) | 2.135 | 0 | -0.085 | 2.135 | -0.085/0.034 | -0.042/0.066 | 0 | 2 | 185 | 0.121/-0.387 | v_bz_applied while oracle not ready; v_bz sign flip jitter; readiness drop after applied; visible scale-gate rejects |
| `terminal_speed1p8` | 2 | 0 | False | 159 | 90 | 126 | 81 | 0 | 0 | 100.0% (159/159) |  | 0 |  |  | / | / | 0 | 0 | 44 | 0.305/-0.200 | engaged+ready but owner never term; visible scale-gate rejects |
| `terminal_speed1p8` | 3 | 0 | False | 14 | 0 | 0 | 0 | 0 | 0 | 100.0% (14/14) |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.123/1.040 |  |
| `terminal_speed1p8` | 4 | 0 | False | 131 | 98 | 107 | 84 | 0 | 0 | 100.0% (131/131) |  | 0 |  |  | / | / | 0 | 0 | 34 | -0.201/-0.653 | engaged+ready but owner never term; visible scale-gate rejects |
| `terminal_speed1p8` | 5 | 0 | False | 16 | 0 | 4 | 0 | 0 | 0 | 100.0% (16/16) |  | 0 |  |  | / | / | 0 | 0 | 0 | -0.447/0.361 | ready and engagement never overlapped |
| `terminal_speed1p8` | 6 | 0 | False | 26 | 0 | 13 | 0 | 0 | 0 | 100.0% (26/26) |  | 0 |  |  | / | / | 0 | 0 | 0 | -0.348/0.467 | ready and engagement never overlapped |
| `terminal_speed1p8` | 7 | 0 | False | 207 | 139 | 29 | 0 | 0 | 0 | 100.0% (207/207) |  | 0 |  |  | / | / | 0 | 0 | 92 | -2.389/-10.838 | ready and engagement never overlapped; visible scale-gate rejects |
| `terminal_speed1p8` | 8 | 0 | False | 357 | 175 | 10 | 0 | 0 | 0 | 100.0% (357/357) |  | 0 |  |  | / | / | 0 | 0 | 241 | 0.312/-0.108 | ready and engagement never overlapped; visible scale-gate rejects |
| `terminal_speed1p8` | 9 | 0 | False | 157 | 91 | 131 | 76 | 0 | 0 | 100.0% (157/157) |  | 0 |  |  | / | / | 0 | 0 | 45 | 3.659/-9.149 | engaged+ready but owner never term; visible scale-gate rejects |
| `terminal_speed1p8` | 10 | 0 | False | 5 | 0 | 0 | 0 | 0 | 0 | 100.0% (5/5) |  | 0 |  |  | / | / | 0 | 0 | 0 | 0.833/1.475 |  |

## Gatekeeping Answers

- `control_speed1p8`: engaged+ready runs 0/10 (first range mean n/a); commit vision survival 100.0% vs 100.0% (0.0% delta); owner=term runs 0/10 (first range mean n/a, min n/a); captures by 2.2m 0/10; e_z at capture mean n/a; v_bz_applied runs 0/10 (first range mean n/a); wrong-sign rows 0; owner-chatter runs 0; jitter runs 0; readiness-transient runs 0; visible scale-reject runs 0/10; certified-feature runs 10/10; engaged+ready/no-owner runs 0/10.
- `terminal_speed1p8`: engaged+ready runs 4/10 (first range mean 2.483m); commit vision survival 100.0% vs 100.0% (0.0% delta); owner=term runs 1/10 (first range mean 2.135m, min 2.135m); captures by 2.2m 0/10; e_z at capture mean -0.085; v_bz_applied runs 1/10 (first range mean 2.135m); wrong-sign rows 0; owner-chatter runs 0; jitter runs 1; readiness-transient runs 1; visible scale-reject runs 6/10; certified-feature runs 10/10; engaged+ready/no-owner runs 3/10.

## QA Notes

- Commit vision survival stayed saturated at `100.0%` in both arms, unchanged from `46e9a64`; with this threshold, vision freshness was not the differentiating bottleneck.
- Gate outcomes regressed versus `46e9a64`: control `6/10 -> 0/10`, terminal live `4/10 -> 0/10`.
- K1 regressed in the live arm: captures by 2.2m `2/10 -> 0/10`.
- Terminal authority did actuate once, at R=`2.135m`, but that run had `v_bz_applied while oracle not ready`, `v_bz sign flip jitter`, readiness drop, and scale rejects.

## Verdict

NO-GO for live terminal arms: v_bz sign-flip jitter observed.

Live arm summary: owner=term rows `54`, v_bz_applied rows `54`, runs with engaged+ready `4/10`, captures by 2.2m `0/10`, visible scale-reject runs `6/10`.

Artifacts: `runs.csv`, `runs.json`, and per-flight logs under `tuning\runtime-logs\terminal-ab-4fc71bb-4fc71bb-20260720T072104Z`.
