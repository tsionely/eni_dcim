# Certificate-inheritance audit — span×range honesty (P2)

Population: unique-exposure `feature` records with `cert_status=certified`, `mode=BAR_FULL`, believed `|gate_rel| >= 0.5m`. Fiction test: `span_px · R ∉ [300, 800]` px·m (nominal 512).

## Verdict

- Samples: **18617** across 400 logs
- Outside band: **741** (4.0%)
- Below 1.2m outside: **194/227** (85.5%)
- **Above 2m outside: 380/18048 (2.1%) — YES, threatens admission**
- Known-case fid hits in outside set: 144

## Bins by believed range

| bin (m) | n | outside | frac | prod med | p10 | p90 |
|---|---:|---:|---:|---:|---:|---:|
| 0.5-1.0 | 158 | 146 | 92.4% | 40 | 18 | 93 |
| 1.0-1.2 | 69 | 48 | 69.6% | 74 | 41 | 609 |
| 1.2-1.5 | 138 | 77 | 55.8% | 121 | 32 | 584 |
| 1.5-2.0 | 204 | 90 | 44.1% | 397 | 52 | 507 |
| 2.0-2.5 | 233 | 50 | 21.5% | 477 | 128 | 576 |
| 2.5-3.0 | 240 | 34 | 14.2% | 503 | 209 | 567 |
| 3.0-4.0 | 696 | 34 | 4.9% | 503 | 399 | 552 |
| 4.0-6.0 | 4133 | 104 | 2.5% | 504 | 419 | 547 |
| 6.0-10 | 11679 | 107 | 0.9% | 493 | 480 | 518 |
| >=10 | 1067 | 51 | 4.8% | 517 | 365 | 653 |

## Implication

The 512 px·m oracle-door gate (e16d506) targets successor-wearing-the-certificate fiction concentrated at close range. If outside fraction above 2m is nonzero, admission (not only close tracking) needs the same honesty check.

## Worst flights by outside count

| fid | n | outside | frac | min R_out | max R_out |
|---|---:|---:|---:|---:|---:|
| `20260719T151227-49448448` | 642 | 69 | 11% | 0.57 | 6.72 |
| `20260719T201630-f170ead6` | 858 | 60 | 7% | 0.67 | 7.66 |
| `20260719T202720-50f9dcc8` | 597 | 57 | 10% | 0.68 | 2.62 |
| `20260719T201851-50f9dcc8` | 942 | 54 | 6% | 1.32 | 19.54 |
| `20260719T162853-f170ead6` | 219 | 35 | 16% | 1.24 | 6.43 |
| `20260719T163649-f170ead6` | 720 | 33 | 5% | 1.32 | 4.42 |
| `20260719T173427-50f9dcc8` | 621 | 33 | 5% | 0.60 | 4.33 |
| `20260719T202445-f170ead6` | 504 | 27 | 5% | 0.54 | 7.35 |
| `20260719T160039-f170ead6` | 251 | 19 | 8% | 0.54 | 2.91 |
| `20260719T164548-f170ead6` | 191 | 19 | 10% | 0.95 | 3.31 |
| `20260719T161634-f170ead6` | 198 | 17 | 9% | 1.87 | 11.25 |
| `20260719T151118-49448448` | 143 | 15 | 10% | 0.75 | 2.15 |
| `20260719T164153-f170ead6` | 280 | 15 | 5% | 0.55 | 11.22 |
| `20260719T161859-f170ead6` | 147 | 14 | 10% | 2.17 | 3.26 |
| `20260719T162358-f170ead6` | 158 | 14 | 9% | 1.01 | 23.78 |

## Deliverables

- `cert-inheritance.md`, `summary.json`, `outside_samples.csv`
