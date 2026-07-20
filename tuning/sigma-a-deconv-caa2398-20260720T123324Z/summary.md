# SIGMA_A Deconvolution

Scope: existing `caa2398` tuning residuals only; no replay, campaign, or real simulator run.
Repo HEAD: `caa23980f0ffb5e5d1a000a67d905abcb0bcc35f`.
Source artifact: `C:\Users\tsion\Projects\eni_dcim_qa\tuning\hold-lift-r26-3b554f3-35bfa6d-20260720T121704Z`.

Model: regress `r_v^2` against `age^2`: intercept -> `sigma_ref^2`, slope -> `sigma_a^2`.
Primary estimator: per-sample Theil-Sen robust line on oracle-reference residuals. OLS is included as sensitivity.

## Primary Fit

| Group | n | age range | slope raw | sigma_a | sigma_a 95% CI | sigma_ref | sigma_ref 95% CI | gate | ref sanity |
|---|---:|---|---:|---:|---|---:|---|---|---|
| `all` | 16 | 0.167-0.431 | 0.000 | 0.000 | 0.000/0.000/0.000 | 0.437 | 0.437/0.437/0.521 | `True` | `False` |
| `switch_adjacent` | 3 | 0.167-0.194 | 0.000 | 0.000 | 0.000/0.000/0.000 | 0.437 | 0.437/0.437/0.437 | `True` | `False` |
| `maintenance` | 13 | 0.229-0.431 | 0.000 | 0.000 | 0.000/0.000/0.000 | 0.437 | 0.437/0.437/0.577 | `True` | `False` |

## OLS Sensitivity

| Group | n | slope raw | sigma_a | sigma_ref | gate | ref sanity |
|---|---:|---:|---:|---:|---|---|
| `all` | 16 | -0.772 | 0.000 | 0.491 | `True` | `False` |
| `switch_adjacent` | 3 | 0.000 | 0.000 | 0.437 | `True` | `False` |
| `maintenance` | 13 | -1.017 | 0.000 | 0.523 | `True` | `False` |

## Age-Bin Counts

| Age bin | n | age range | mean r_v^2 | residual RMS | legacy ratio p95 |
|---|---:|---|---:|---:|---:|
| `0p10-0p20` | 3 | 0.167-0.194 | 0.191 | 0.437 | 2.584 |
| `0p20-0p30` | 6 | 0.229-0.299 | 0.191 | 0.437 | 1.905 |
| `0p30-0p50` | 7 | 0.333-0.431 | 0.140 | 0.374 | 1.310 |
| `gte0p50` | 0 | n/a-n/a | n/a | n/a | n/a |

## Verdict

- Deconvolved `sigma_a`: `0.000` with bootstrap CI `0.000/0.000/0.000`.
- Deconvolved `sigma_ref`: `0.437` with bootstrap CI `0.437/0.437/0.521`.
- Drift gate by deconvolved sigma_a: `True` (`<=0.35 m/s^2`).
- Sigma_ref sanity window `0.15-0.30 m/s`: `False`.

Interpretation: the age-growth slope is non-positive in these residuals, so the true drift term clamps to zero under the deconvolution model. The remaining error behaves like reference/anchor-rate offset rather than age-growing acceleration drift; however the fitted sigma_ref is above the expected oracle-slope noise band and should be called out for advisor ratification.
