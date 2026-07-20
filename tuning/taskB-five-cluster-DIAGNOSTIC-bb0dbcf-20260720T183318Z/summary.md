# TASK B - Five-Cluster Diagnostic Suite

DIAGNOSTIC ONLY: may falsify the repair; may not lift HOLD, declare a validated age, or release sigma_a.

- Selected clusters: `5`.
- Missing legal-five ids: `none`.
- Sample rows: `119`.
- Mechanism regression slope/intercept: `0.804` / `-0.011`.
- R26-1 restamp verdict: `FAIL`.

| cluster | auth | delta_latch | b0 old | b0 new | old-new | target -delta | error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `20260720T071112-cd18c5fb:A1` | 0.220 | 1.122 | -0.683 | 0.231 | -0.913 | -1.122 | 0.208 |
| `20260720T071333-cd18c5fb:A1` | 1.000 | 0.000 | -0.020 | -0.020 | 0.000 | -0.000 | 0.000 |
| `20260720T071545-cd18c5fb:A1` | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| `20260720T134522-9aa0ef5c:A1` | 1.000 | 0.000 | 0.006 | 0.006 | 0.000 | -0.000 | 0.000 |
| `20260720T135008-9aa0ef5c:A1` | 1.000 | 0.000 | -0.017 | 0.016 | -0.033 | -0.000 | -0.033 |

Artifacts are prefixed `DIAGNOSTIC_` and include selected clusters, anchor-policy samples, delta-latch mechanism table, b0 regime-invariance table, pseudo-floor diagnostics, R26-1 restamp rows, and command/admission old-vs-new comparison.
