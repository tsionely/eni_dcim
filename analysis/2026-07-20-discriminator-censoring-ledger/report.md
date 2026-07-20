# Discriminator table + coverage-censoring ledger (first edition)

RESPONSE38 §1 / RESPONSE39 — ten already-labeled flights (6 archive phase6l + 4 metrology). Tip `bb0dbcf`.

**Pool:** 5 legal / 5 censored (2 scale-gate funnel, 3 no-certified-FULL funnel).

## 1. Discriminator table — what predicts certified terminal coverage

Primary observable from the f4 autopsy: **distance at which continuous certified FULL ends** (`certified_full_end_range_m`).

- Legal median end-range: **4.348 m** (max 5.279 m)
- Dropout funnel (`NO_CERTIFIED_FULL_BELOW_3P5`) median: **5.225 m** (min 5.187 m)
- Scale-gate funnel median end-range: **5.23059090261231** (not the kill — see scale_gate counts)

**f4 finding discriminates dropout vs legal (no overlap): False**

### Per-flight discriminators (excerpt)

| slot | era | mechanism | FULL ends at (m) | dies >4.5? | FULL gaps | scale_gate≤3.5 | ez_ok≤3.5 | |x| med≤5 |
|---|---|---|---:|---|---:|---:|---:|---:|
| F1 | archive | `NO_CERTIFIED_FULL_BELOW_3P5` | 5.290143068966311 | True | 1 | 0 | 0 | 0.3691060442405569 |
| F2 | archive | `LEGAL` | 3.8041822371409286 | False | 1 | 0 | 18 | 0.03442606711222922 |
| F3 | archive | `SCALE_GATE_FLIPPED_FAR_GATE_POST_GAP` | 5.190725455895457 | True | 1 | 1 | 0 | 0.18094431365045255 |
| F4 | archive | `LEGAL` | 4.347982401412674 | False | 1 | 0 | 13 | 0.2756721362510969 |
| F5 | archive | `NO_CERTIFIED_FULL_BELOW_3P5` | 5.187492645427993 | True | 1 | 0 | 0 | 0.37209739501013694 |
| F6 | archive | `LEGAL` | 2.9110505094641344 | False | 0 | 0 | 8 | 0.15548479138980872 |
| F7/f1 | metrology | `SCALE_GATE_FLIPPED_FAR_GATE_POST_GAP` | 5.270456349329163 | True | 1 | 11 | 0 | 3.883881217533713 |
| F8/f2 | metrology | `LEGAL` | 5.020451357538778 | True | 1 | 5 | 28 | 0.5843672722942566 |
| F9/f3 | metrology | `LEGAL` | 5.278756824277082 | True | 1 | 1 | 35 | 0.5656607120279307 |
| F10/f4 | metrology | `NO_CERTIFIED_FULL_BELOW_3P5` | 5.225145824776412 | True | 1 | 0 | 0 | 0.5807610819103869 |

### Population contrast (medians)

| feature | legal | censored | dropout funnel | scale funnel |
|---|---:|---:|---:|---:|
| `certified_full_end_range_m` | 4.348 | 5.225 | 5.225 | 5.231 |
| `n_full_gaps` | 1 | 1 | 1 | 1.000 |
| `speed_xy_median_le5_mps` | 1.662 | 0.419 | 0.514 | 0.210 |
| `lateral_abs_x_median_le5_m` | 0.276 | 0.372 | 0.372 | 2.032 |
| `bloom_undersized_frac` | 0.000 | 0.028 | 0.000 | 0.115 |
| `n_side_rows_le5` | 27 | 4 | 0 | 6.000 |
| `n_scale_gate_le_3p5` | 0 | 0 | 0 | 6.000 |
| `closest_certified_full_m` | 1.185 | 3.748 | 4.314 | 2.077 |

### P2 hold-through-band — table verdict

certified_full_end_range_m cleanly separates legal (median 4.347982401412674, max 5.278756824277082) from NO_CERTIFIED_FULL_BELOW_3P5 dropout funnel (median 5.225145824776412, min 5.187492645427993).

P2 (hold/slow when FULL drops before 4.5 m) is the tanks-visible profile decision that reads off this table: legal approaches keep continuous certified FULL into/below the 3.5 m band; dropout-censored approaches lose it above ~4.5 m.

**P2 supported by discriminator separation:** False.

SCALE_GATE_FLIPPED_FAR_GATE_POST_GAP flights CAN have continuous FULL deep into the band (or even below 3.5) — their kill is e_reject=scale_gate, not end-range. End-range is the dropout discriminator; scale_gate count is the scale-funnel discriminator.

## 2. Coverage-censoring ledger + Y_eligible

| era | n | legal | scale-gate | no-FULL≤3.5 | Y_eligible | any-censored rate |
|---|---:|---:|---:|---:|---:|---:|
| archive | 6 | 3 | 1 | 2 | 0.500 | 0.500 |
| metrology | 4 | 2 | 1 | 1 | 0.500 | 0.500 |
| all | 10 | 5 | 2 | 3 | 0.500 | 0.500 |

Y_eligible = legal-transition approaches / total approaches (RESPONSE38 §1; one attempt per flight in this census edition).

### Per-label rates

- `SCALE_GATE_FLIPPED_FAR_GATE_POST_GAP`: archive 0.167, metrology 0.250, all 0.200
- `NO_CERTIFIED_FULL_BELOW_3P5`: archive 0.333, metrology 0.250, all 0.300

Lift-package context: Y_eligible≈0.50 on both campaigns bounds cohort-4 treatment availability and harvest rate together — half of standard-profile approaches currently fail to produce a legal transition cluster, split across two honest funnels that must not be pooled.

## Deliverables

- `discriminator_table.csv`
- `coverage_censoring_ledger.csv`
- `censoring_per_flight.csv`
- `summary.json`
- `run_discriminator_ledger.py`

Extend when the full-archive sweep lands (RESPONSE37/38).

