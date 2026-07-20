# Discriminator table + coverage-censoring ledger (first edition)

RESPONSE38 §1 / RESPONSE39 — ten already-labeled flights (6 archive phase6l + 4 metrology). Tip `bb0dbcf`.

**Pool:** 5 legal / 5 censored (2 scale-gate funnel, 3 no-certified-FULL funnel).

## 1. Discriminator table — what predicts certified terminal coverage

**First-streak** `certified_full_end_range_m` (f4 autopsy metric) is reported for continuity but **does not alone discriminate** — legal metrology f2/f3 gap near ~5 m then re-acquire below 3.5 m.

- Legal first-streak median/min/max: **4.348** / 2.911 / 5.279 m
- Dropout first-streak median/min/max: **5.225** / 5.187 / 5.290 m
- **First-streak alone separates dropout vs legal:** False

**Discriminators that do separate** (all 3 dropout vs all 5 legal):

- `closest_certified_full_m`: legal max 2.911 m, dropout min 3.748 m (cut 3.5 m) → True
- `recovered_certified_full_le_3p5` (any ez_ok FULL ≤3.5 m): True
- `compound_dropout_signature` (dies >4.5 m AND no certified FULL ≤3.5 m): **True**

### Per-flight discriminators (excerpt)

| slot | era | mechanism | 1st streak (m) | dies>4.5 | recovered≤3.5 | compound | closest FULL | ez_ok≤3.5 |
|---|---|---|---:|---|---|---|---:|---:|
| F1 | archive | `NO_CERTIFIED_FULL_BELOW_3P5` | 5.290143068966311 | True | False | True | 4.314456083022236 | 0 |
| F2 | archive | `LEGAL` | 3.8041822371409286 | False | True | False | 1.064305018103599 | 18 |
| F3 | archive | `SCALE_GATE_FLIPPED_FAR_GATE_POST_GAP` | 5.190725455895457 | True | False | False | 1.24343725135097 | 0 |
| F4 | archive | `LEGAL` | 4.347982401412674 | False | True | False | 2.7790967938171347 | 13 |
| F5 | archive | `NO_CERTIFIED_FULL_BELOW_3P5` | 5.187492645427993 | True | False | True | 4.5730690923464765 | 0 |
| F6 | archive | `LEGAL` | 2.9110505094641344 | False | True | False | 2.9110505094641344 | 8 |
| F7/f1 | metrology | `SCALE_GATE_FLIPPED_FAR_GATE_POST_GAP` | 5.270456349329163 | True | False | False | 2.9111323319150393 | 0 |
| F8/f2 | metrology | `LEGAL` | 5.020451357538778 | True | True | False | -0.8334916678566519 | 28 |
| F9/f3 | metrology | `LEGAL` | 5.278756824277082 | True | True | False | 1.185409259667424 | 35 |
| F10/f4 | metrology | `NO_CERTIFIED_FULL_BELOW_3P5` | 5.225145824776412 | True | False | True | 3.748470846892272 | 0 |

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
| `n_full_ez_ok_le_3p5` | 18 | 0 | 0 | 0.000 |
| `recovered_certified_full_le_3p5` (rate true) | 1.00 | 0.00 | 0.00 | 0.00 |
| `compound_dropout_signature` (rate true) | 0.00 | 0.60 | 1.00 | 0.00 |

### P2 hold-through-band — table verdict (5 lines)

- certified_full_end_range_m (first streak) is reported but does NOT alone separate legal from dropout: legal f2/f3 also end first streak at 5.279 m after a gap yet re-acquire certified FULL <=3.5 m.
- closest_certified_full_m does separate: legal max 2.911 m vs dropout min 3.748 m (cut 3.5 m).
- recovered_certified_full_le_3p5 (n_full_ez_ok_le_3p5>0): all 5/5 legal True, all 3/3 dropout False.
- compound_dropout_signature (FULL dies >4.5 m AND never certified FULL <=3.5 m): separates every dropout flight from every legal flight: True.
- P2 supported: hold/re-anchor when FULL drops before 4.5 m is the intervention that turns a dropout trajectory into legal re-acquire (metrology f2/f3 already do this spontaneously without pooling scale-gate funnel).

**P2 supported (compound signature separates):** True.

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

