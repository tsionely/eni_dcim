# SIGMA_A Release Fit v2

Scope: CSV-only on existing `caa2398` oracle-reference residuals; no replay, campaign, FlightSim, or DCGame launch.
Repo HEAD: `7c3b875492e6c9cd68023f12c3b9736bf1dfd49a`.
Source artifact: `C:\Users\tsion\Projects\eni_dcim_qa\tuning\hold-lift-r26-3b554f3-35bfa6d-20260720T121704Z`.
Response note read: `C:\Users\tsion\Projects\eni_dcim_qa\docs\thinktank\RESPONSE31.md`.

## Release Columns

| n_flights | n_clusters | n_rows | point sigma_a | U95(sigma_a) | sigma_0 | pseudo floor sigma_0 | b0 | b1 | max validated age | verdict |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 1 | 1 | 16 | 0.143 | 0.143 | 0.011 | 0.093 | -0.588 | 0.619 | `none` | `HOLD, DATA-INSUFFICIENT` |

DATA-INSUFFICIENT check: `n_clusters=1; release requires >= 6 independent clusters.`
Estimated additional clusters needed: `5`.

## Constrained Robust Fit

| Estimator | nu | sigma_0 | sigma_a | U95 | bootstrap valid | note |
|---|---:|---:|---:|---:|---|---|
| `student_t_scale_nu5_constrained` | 5.000 | 0.011 | 0.143 | 0.143 | `False` | DATA-INSUFFICIENT: cluster bootstrap degenerate/prohibited for release |
| `RETIRED-AS-RELEASE_theil_sen_r2_vs_a2_raw` | n/a | 0.437 | 0.000 | n/a | `False` | sensitivity only; retired as release instrument |

## Mean Fit

| b0 | b0 CI | b1 | b1 CI | residual RMS after mean | deterministic note |
|---:|---|---:|---|---:|---|
| -0.588 | -0.588/-0.588/-0.588 | 0.619 | 0.619/0.619/0.619 | 0.053 | DETERMINISTIC-SUSPECT: point b1 is nonzero, but cluster CI is invalid with one cluster; do not fold this signed trend into sigma. |

## Command Regimes

| Regime | n | age range | signed mean | signed median | RMS |
|---|---:|---|---:|---:|---:|
| `up` | 0 | n/a-n/a | n/a | n/a | n/a |
| `down` | 0 | n/a-n/a | n/a | n/a | n/a |
| `triangular` | 0 | n/a-n/a | n/a | n/a | n/a |
| `slew_limited` | 3 | 0.396-0.431 | -0.262 | -0.296 | 0.266 |
| `saturated` | 0 | n/a-n/a | n/a | n/a | n/a |
| `flat_no_ff` | 13 | 0.167-0.361 | -0.437 | -0.437 | 0.437 |

Mean/regime deterministic read: the point mean fit has a nonzero signed age slope and the non-empty regimes have nonzero signed means. With one cluster this is not release-stable, but it is reported as a deterministic-model suspect and is not folded into sigma.

## Pseudo-Transition Intercept Floor

| n | sigma_0 | sigma_a | real sigma_0 below floor | note |
|---:|---:|---:|---|---|
| 256 | 0.093 | 0.000 | `True` | FULL-only pseudo anchors/evaluations use non-overlapping 0.35s windows. |

Pseudo-floor read: real sigma_0 below the FULL-only pseudo floor is a sanity blocker unless additional clusters overturn it.

## LOFO Coverage

| Age bin | n | n flights | coverage | worst flight | status |
|---|---:|---:|---:|---|---|
| `0p00-0p10` | 0 | 0 | n/a | `` | DATA-INSUFFICIENT: need >=2 flights for LOFO |
| `0p10-0p20` | 3 | 1 | n/a | `20260720T071112-cd18c5fb` | DATA-INSUFFICIENT: need >=2 flights for LOFO |
| `0p20-0p30` | 6 | 1 | n/a | `20260720T071112-cd18c5fb` | DATA-INSUFFICIENT: need >=2 flights for LOFO |
| `0p30-0p40` | 6 | 1 | n/a | `20260720T071112-cd18c5fb` | DATA-INSUFFICIENT: need >=2 flights for LOFO |
| `0p40-0p50` | 1 | 1 | n/a | `20260720T071112-cd18c5fb` | DATA-INSUFFICIENT: need >=2 flights for LOFO |
| `gt0p50` | 0 | 0 | n/a | `` | DATA-INSUFFICIENT: need >=2 flights for LOFO |

## Model-Form Kill Test And Fallback

LOFO monotonic degradation cannot be tested with one flight. The fallback bound below is an in-sample/advisory-only monotone ceiling.

| Age bin | n | raw p95 | isotonic B_rate_drift |
|---|---:|---:|---:|
| `0p00-0p10` | 0 | n/a | 0.000 |
| `0p10-0p20` | 3 | 0.046 | 0.046 |
| `0p20-0p30` | 6 | 0.034 | 0.046 |
| `0p30-0p40` | 6 | 0.073 | 0.073 |
| `0p40-0p50` | 1 | 0.128 | 0.128 |
| `gt0p50` | 0 | n/a | 0.128 |

## Verdict

`HOLD, DATA-INSUFFICIENT`: n_clusters=1 < 6; cluster bootstrap U95 is degenerate/not release-valid.

The point estimate is below the gate, but the release statistic is not releasable because the current artifact has one independent transition cluster. The next action is to add at least five more independent replay transition clusters from the archive, not to squeeze the fit.
