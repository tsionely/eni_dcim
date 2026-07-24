# TALLY T4 vs T3 - Missing At HEAD

- Generated UTC: `2026-07-24T12:01:13+00:00`
- Repo HEAD: `6975cfc8ee29d8eef2fc6e1199ac67cde29c212e`
- Scope: replay/CSV only; no FlightSim/DCGame launched or controlled; FlightSim and SIM lock not touched.
- Result: `fixtures/*raceprep-t4-B-*` is `MISSING_AT_HEAD`; per instruction, the full two-group tally was not run.

## Fixture Availability
| group | glob | fixtures_at_head | status |
| --- | --- | --- | --- |
| T4 | `*raceprep-t4-B-*` | 0 | MISSING_AT_HEAD |
| T3 | `*raceprep-t3-B-*` | 8 | AVAILABLE |

## Registered T4 Predictions
| prediction | t4_value | control_value | verdict |
| --- | --- | --- | --- |
| gate-clip-budget aborts approximately 0 in T4 | MISSING_AT_HEAD | T3 available, not retallied because T4 missing | NOT_JUDGED_MISSING_T4 |
| previously-clipped flights continue past the frame | MISSING_AT_HEAD | T3 available, not retallied because T4 missing | NOT_JUDGED_MISSING_T4 |
| gate passes >= 2/8 | MISSING_AT_HEAD | T3 available, not retallied because T4 missing | NOT_JUDGED_MISSING_T4 |
| no new abort class | MISSING_AT_HEAD | T3 available, not retallied because T4 missing | NOT_JUDGED_MISSING_T4 |

## Notes
- T3 control fixtures are available (`8` runs), but T4 has `0` fixture directories at this HEAD.
- Gate-clip counts, peak `v_world`, catastrophic class, survival, commit attempts, last-clip `gate_rel.t`, param integrity, and true-world dz were not evaluated because T4 is missing.
- Expected T4 params remain: defaults + `planner.commit.speed_mps=1.8`, `planner.commit.vz_cap_mps=1.2`, `planner.terminal.enable=false`, `safety.imu_stale_s=0.6`, `estimation.vel_clamp_mps=12`, `safety.gate_clip_debounce_s=0.3`.

## Files
- `fixture_availability.csv`
- `prediction_read.csv`
- `generation_info.json`
