# Psi-age ledger + S4 prep

**Verdict: DIAGNOSTIC_ONLY**

DIAGNOSTIC_ONLY — residuals show no material age dependence over the encountered psi_age interval [0, 0.930]s (p90=0.701s). No hard validity limit / sigma_psi(age) required for S4.

- SIDE features: 555 (metric SIDE_PAIR=432, ROW_ONLY shadow=123)
- maintenance SIDE with prior-FULL residual: 52
- exact same-ts FULL/SIDE pairs (overlap, ψ≈0): 251
- psi_age max / p90: 0.930377728 / 0.7013812992 s
- corr(age, |residual|): -0.2279717486933442

## Residual vs prior full-quad by ψ-age bin (maintenance)

| age [s] | n | MAE | std | p90\|r\| |
|---------|--:|----:|----:|--------:|
| [0.00,0.05) | 12 | 0.0409 | 0.0684 | 0.1725 |
| [0.05,0.12) | 10 | 0.0250 | 0.0499 | 0.1078 |
| [0.12,0.25) | 12 | 0.0225 | 0.0735 | 0.0030 |
| [0.25,0.50) | 6 | 0.0000 | 0.0000 | 0.0000 |
| [0.50,1.00) | 12 | 0.0000 | 0.0000 | 0.0000 |
| [1.00,9.00) | 0 | — | — | — |

ψ-age = time since last certified FULL_QUAD (orientation prior). Maintenance rows = SIDE_PAIR with no same-exposure FULL.

## Deliverables

- `psi_age_ledger.csv`, `maintenance_residuals.csv`, `age_bins.csv`, `summary.json`, this report
