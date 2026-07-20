# TASK A - Full-Archive Retroactive Census

Scope: replay/CSV only; no FlightSim/DCGame launch.
Repo HEAD: `bb0dbcf36cac8a7e100d480dc0de8fcad6b12821`.

## Eligibility First

- Fixture directories enumerated: `61`.
- Eligible recordings: `115`.

## Expanded Census

- Current-perception clusters found: `23`.
- Census verdict: `PASS_GE_6`.
- Release fit run: `True`.

| failure_reason | rows |
| --- | ---: |
| `FULL_BELOW_3P5_NOT_EZ_USABLE` | 24 |
| `NO_CERTIFIED_FULL_BELOW_3P5` | 53 |
| `NO_CLOSE_FEATURE_EPOCH_LE4P5` | 45 |
| `NO_LEGAL_FULL_RATE_ANCHOR` | 3 |
| `NO_LEGAL_SIDE_MAINTENANCE_INTERVAL` | 10 |
| `NO_PARALLEL_SIDE_PRODUCTION` | 20 |
| `OK` | 23 |

## Release Fit v2.1

| clusters | rows | point sigma_a | profile U95 | bootstrap U95 | U95 release | verdict |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 23 | 1638 | 1.307 | 1.400 | 1.735 | 1.735 | `HOLD, DATA-INSUFFICIENT` |

Artifacts: `eligibility_dirs.csv`, `replay_targets.csv`, `features_archive.csv`, `flight_meta.csv`, `expanded_census_clusters.csv`, `censored_approach_diagnostics.csv`, `censoring_ledger.csv`, `cluster_age_bin_counts.csv`, and release-fit CSVs when authorized.
