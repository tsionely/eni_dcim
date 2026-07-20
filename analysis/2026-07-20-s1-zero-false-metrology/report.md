# S1 — Zero false metrology

**Verdict: PASS**

- false metric accepts: **0** (req 0)
- false TERM_READY: **0** (req 0)
- wrong-epoch metrology accepts: **0** (req 0)
- close-range scale fictions stressed: 14
- cert re-anchor anomaly (status_at NONE / _status held): **2** — does not feed metrology; patch addendum queued

Door under test: `terminal_observe` scale gate (span×tz vs 0.59–1.56·fx·W), probation-out (`cert_status != certified`), row-only shadow modes, and `SidePairCertificate` promote_floor 1.6 + `on_relock_or_collision` on R-jumps.

## Per flight

| fid | fiction | false_metric | false_ready | wrong_epoch | reanchor |
|-----|--------:|-------------:|------------:|------------:|---------:|
| `20260719T201630-f170ead6` | 4 | 0 | 0 | 0 | 1 |
| `20260719T202445-f170ead6` | 7 | 0 | 0 | 0 | 1 |
| `20260719T202720-50f9dcc8` | 3 | 0 | 0 | 0 | 0 |

Pinned unit numbers: 103px@1.0m rejected=True; 388px@1.32m accepted=True.

Projected-row injection (ROW_ONLY×certified×{103,200,388}px): **0 accepts** / 6 trials.

## Deliverables

- `close_window_rows.csv`, `summary.json`, this report
