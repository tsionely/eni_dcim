# TALLY T3 vs T2c/T2f - Missing At HEAD

- Generated UTC: `2026-07-24T09:24:28+00:00`
- Repo HEAD: `ff82e1f448719c1bb22053af235b183082399bd3`
- Scope: replay/CSV only; no FlightSim/DCGame launched or controlled; FlightSim and SIM lock not touched.
- Result: `fixtures/*raceprep-t3-B-*` is `MISSING_AT_HEAD`; per instruction, the full three-group tally was not run.

## Fixture Availability
| group | glob | fixtures_at_head | status |
| --- | --- | --- | --- |
| T3 | `*raceprep-t3-B-*` | 0 | MISSING_AT_HEAD |
| T2c | `*raceprep-t2c-B-*` | 8 | AVAILABLE |
| T2f | `*raceprep-t2f-B-*` | 8 | AVAILABLE |

## Registered T3 Predictions
| prediction | t3_value | verdict |
| --- | --- | --- |
| peak |v_world| <= 12 m/s in all T3 runs | MISSING_AT_HEAD | NOT_JUDGED_MISSING_T3 |
| catastrophic vz-divergence class -> 0 in T3 | MISSING_AT_HEAD | NOT_JUDGED_MISSING_T3 |
| median survival rises vs control | MISSING_AT_HEAD | NOT_JUDGED_MISSING_T3 |
| gate passes >= 3/8 | MISSING_AT_HEAD | NOT_JUDGED_MISSING_T3 |

## Notes
- Available controls at this HEAD: `T2c=8`, `T2f=8`.
- T3 param integrity, peak `v_world`, catastrophic class, survival, passes, and true-world dz were not evaluated because there are zero T3 fixture directories.
- Expected T3 params remain: defaults + `planner.commit.speed_mps=1.8`, `planner.commit.vz_cap_mps=1.2`, `planner.terminal.enable=false`, `safety.imu_stale_s=0.6`, `estimation.vel_clamp_mps=12`.

## Files
- `fixture_availability.csv`
- `prediction_read.csv`
- `generation_info.json`
