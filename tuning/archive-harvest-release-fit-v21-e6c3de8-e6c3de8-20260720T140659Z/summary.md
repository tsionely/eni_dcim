# Archive Harvest Release Fit v2.1

Scope: recorded replay/CSV only; no FlightSim/DCGame launch.
Repo HEAD: `e6c3de8a906ab7aa75af5a71cb1f6da4c2439011`.
Source target: `e6c3de8` -> `e6c3de8a906ab7aa75af5a71cb1f6da4c2439011`.

## Step 1 Census

| flight_id | approaches | FULL depth | est. rows | status |
|---|---:|---:|---:|---|
| `20260720T071008-5b501b4c` | 0 | n/a | 0 | NO_APPROACH |
| `20260720T071112-cd18c5fb` | 1 | 1.064 | 9 | OK |
| `20260720T071220-5b501b4c` | 0 | n/a | 0 | NO_APPROACH |
| `20260720T071333-cd18c5fb` | 1 | 2.779 | 12 | OK |
| `20260720T071439-5b501b4c` | 0 | n/a | 0 | NO_APPROACH |
| `20260720T071545-cd18c5fb` | 1 | 2.911 | 2 | OK |
| `20260720T133443-9aa0ef5c` | 0 | n/a | 0 | NO_APPROACH |
| `20260720T134522-9aa0ef5c` | 1 | 2.627 | 7 | OK |
| `20260720T135008-9aa0ef5c` | 1 | 1.315 | 8 | OK |

Census verdict: `STOP_ARCHIVE_LT_6_APPROACHES`.

## Census Diagnostics

| flight_id | full any <3.5 | full e_z ok <3.5 | side certified | row-only side | reason |
|---|---:|---:|---:|---:|---|
| `20260720T071008-5b501b4c` | 0 | 0 | 0 | 0 | `NO_CERTIFIED_FULL_BELOW_3P5` |
| `20260720T071112-cd18c5fb` | 18 | 18 | 9 | 2 | `OK` |
| `20260720T071220-5b501b4c` | 1 | 0 | 0 | 1 | `FULL_BELOW_3P5_NOT_EZ_USABLE` |
| `20260720T071333-cd18c5fb` | 13 | 13 | 12 | 1 | `OK` |
| `20260720T071439-5b501b4c` | 0 | 0 | 0 | 0 | `NO_CERTIFIED_FULL_BELOW_3P5` |
| `20260720T071545-cd18c5fb` | 8 | 8 | 2 | 0 | `OK` |
| `20260720T133443-9aa0ef5c` | 11 | 0 | 0 | 4 | `FULL_BELOW_3P5_NOT_EZ_USABLE` |
| `20260720T134522-9aa0ef5c` | 33 | 28 | 8 | 6 | `OK` |
| `20260720T135008-9aa0ef5c` | 36 | 35 | 8 | 1 | `OK` |

Stopped before fitting because fewer than six independent approaches were available.
