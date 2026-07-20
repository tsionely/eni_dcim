# R5 empirical envelope prep (P3)

Pre-registered (RESPONSE12 / e16d506): per unique live-arm exposure, predicted tail miss `e_x = e_z − h_tail·v_z` with `h_tail = min(τ, 0.45)` vs observed true-axis crossing miss; containment of `|e_x| + 2σ_x + 0.06`. Failures raise `sigma_model` — **never the corridor**.

## phase6j landed? **False**

Cold cohort empty until phase6j lands. Warm numbers are PREP only — not the registered R5 verdict.

## Warm prep (phase6i-R live passes)

```json
{
  "cohort": "warm_phase6i_r",
  "n": 77,
  "containment_rate": 0.935064935064935,
  "n_miss_small_env": 1,
  "median_claimed": 0.6445362404707371,
  "median_abs_obs": 0.4100012710778283,
  "median_abs_ex": 0.45
}
```

### Per flight

| fid | obs_miss | n_exp | containment | small-env misses |
|---|---:|---:|---:|---:|
| `20260719T200816-f170ead6` | -0.053581572003063356 | 26 | 100% | 0 |
| `20260719T201851-50f9dcc8` | 0.4100012710778283 | 51 | 90% | 1 |

## Cold cohort (phase6j)

```json
{
  "cohort": "cold_phase6j",
  "n": 0,
  "containment_rate": null,
  "n_miss_small_env": 0
}
```

## Re-run recipe (when phase6j lands)

```text
python analysis/2026-07-20-r5-envelope-prep/run_r5_envelope_prep.py
# auto-discovers fixtures/*phase6j* live-arm logs into cold cohort
```

## Deliverables

- `r5-envelope-prep.md`, `summary.json`, `warm_exposures.csv`
