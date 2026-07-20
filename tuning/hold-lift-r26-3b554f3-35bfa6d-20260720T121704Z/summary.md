# R26 Anchor Run

Role: QA & MOCK-TUNER.
Scope: recorded-video replay plus synthetic oracle micro-replays only; no real simulator was launched.
Source commit: `3b554f38c01b120edb461a01070b749d4dd1caeb`.
Repo HEAD: `35bfa6d9d1bbd2bbce036c7fe3089d0d587c47b5`.
Non-tuning delta from `3b554f3`: `[]`.

## Reference Provenance Pin

- Old reference: flight_log state.v_world de-tilted to the stored level frame.
- Warning: Believed-state channel; not the ruling-specified sigma_a reference when caged-gravity sawtooth is present.
- Oracle reference: WITHHELD FULL_QUAD oracle: Theil-Sen slope of withheld full e_z observations around each scoring instant; v_z_up=-slope(e_z).
- Fit statistic: p95_abs_sigma_a_mps2 percentile envelope, not RMS; age < 0.100s excluded.

| Reference | n | p50 | p80 | p90 | p95 | p99 | RMS audit | provenance |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `old_state_v_world` | 16 | 0.957 | 2.536 | 3.495 | 4.455 | 4.455 | 1.956 | flight_log state.v_world de-tilted to the stored level frame |
| `withheld_full_oracle` | 16 | 1.463 | 1.905 | 2.247 | 2.340 | 2.565 | 1.614 | withheld FULL_QUAD e_z Theil-Sen slope around each scoring instant |

| Age bin | old n | old p95 | old p99 | oracle n | oracle p95 | oracle p99 |
|---|---:|---:|---:|---:|---:|---:|
| `all` | 16 | 4.455 | 4.455 | 16 | 2.340 | 2.565 |
| `0p10-0p20` | 3 | 0.646 | 0.646 | 3 | 2.584 | 2.614 |
| `0p20-0p30` | 6 | 4.455 | 4.455 | 6 | 1.905 | 1.905 |
| `0p30-0p50` | 7 | 1.226 | 1.226 | 7 | 1.310 | 1.310 |
| `gte0p50` | 0 | n/a | n/a | 0 | n/a | n/a |

## R26-1 Liveness

| Trial | Drop frame | First capture R | TERM/SIDE rows | Side captures | Side max score | Min side R | Transitions | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `anchor_drop_frame_304` | 304 | 1.903 | 16 | 1 | 0.271 | 1.006 | 1 | `PASS` |
| `anchor_drop_frame_306` | 306 | 1.903 | 0 | 0 | n/a | n/a | 0 | `FAIL` |
| `anchor_drop_frame_308` | 308 | 1.903 | 0 | 0 | n/a | n/a | 0 | `FAIL` |

Overall R26-1 verdict: `PASS`.

## R26-2/3 Sigma-a

Primary table uses the withheld-FULL oracle reference. RMS columns are audit-only; the fitted sigma_a is the percentile envelope above.

| Anchor age bin | n | age range | corrected err RMS | corrected sigma_a RMS | anchor-only sigma_a RMS | centered |
|---|---:|---|---:|---:|---:|---:|
| `all` | 16 | 0.167-0.431 | 0.410 | 1.614 | 1.956 | 0.572 |
| `0p10-0p20` | 3 | 0.167-0.194 | 0.437 | 2.378 | 0.537 | 0.176 |
| `0p20-0p30` | 6 | 0.229-0.299 | 0.437 | 1.685 | 3.009 | 0.181 |
| `0p30-0p50` | 7 | 0.333-0.431 | 0.374 | 1.048 | 0.926 | 0.319 |
| `gte0p50` | 0 | n/a-n/a | n/a | n/a | n/a | n/a |

### Percentile Envelope

| Group | n | p50 | p80 | p90 | p95 | p99 | max |
|---|---:|---:|---:|---:|---:|---:|---:|
| `all` | 16 | 1.463 | 1.905 | 2.247 | 2.340 | 2.565 | 2.621 |
| `switch_adjacent` | 3 | 2.247 | 2.471 | 2.546 | 2.584 | 2.614 | 2.621 |
| `maintenance` | 13 | 1.310 | 1.656 | 1.856 | 1.905 | 1.905 | 1.905 |

### Regime Split

| Regime | n | age range | corrected err RMS | sigma_a RMS | centered |
|---|---:|---|---:|---:|---:|
| `switch_adjacent` | 3 | 0.167-0.194 | 0.437 | 2.378 | 0.176 |
| `maintenance` | 13 | 0.229-0.431 | 0.404 | 1.379 | 0.429 |

| sigma_a | floor | pass corridor | measured lands here |
|---:|---:|---|---|
| 0.000 | 0.186 | `True` | `False` |
| 0.100 | 0.195 | `True` | `False` |
| 0.200 | 0.221 | `True` | `False` |
| 0.300 | 0.256 | `True` | `False` |
| 0.350 | 0.275 | `True` | `False` |
| 0.400 | 0.296 | `True` | `False` |
| 0.500 | 0.340 | `False` | `False` |
| 1.000 | 0.576 | `False` | `False` |
| 2.000 | 1.068 | `False` | `False` |
| 2.340 | 1.237 | `False` | `True` |
| 3.000 | 1.565 | `False` | `False` |

Overall R26-2/3 verdict: `FAIL`.

### Anchor-Age Sweep

| Age | sigma_v | floor | corridor pass | observed age used |
|---:|---:|---:|---|---|
| 0.100 | 0.255 | 0.326 | `False` | `True` |
| 0.200 | 0.479 | 0.545 | `False` | `True` |
| 0.300 | 0.709 | 0.773 | `False` | `True` |
| 0.400 | 0.941 | 1.005 | `False` | `True` |
| 0.500 | 1.174 | 1.237 | `False` | `False` |
| 0.600 | 1.174 | 1.237 | `False` | `False` |
| 0.750 | 1.174 | 1.237 | `False` | `False` |
| 1.000 | 1.174 | 1.237 | `False` | `False` |

### Held-Out Coverage

| Age bin | train n | heldout n | fit p95 sigma_a | heldout coverage | floor | corridor pass |
|---|---:|---:|---:|---:|---:|---|
| `0p10-0p20` | 1 | 2 | 2.621 | 1.000 | 1.377 | `False` |
| `0p20-0p30` | 4 | 2 | 1.905 | 1.000 | 1.021 | `False` |
| `0p30-0p50` | 3 | 4 | 1.210 | 0.500 | 0.678 | `False` |
| `gte0p50` | 0 | 0 | n/a | n/a | n/a | `` |

### Age Distributions

- Anchor age at transition: n=1, min/median/max=0.167/0.167/0.167.
- Max age while maintaining: `0.431` (authorized max `0.431`).
- Age at damping onset: `0.396`.
- Worst continuous score: `0.270` (p95 `0.270`).

## R26-4/5/6 Replays

| Scenario | Verdict | Final source | Final rate source | Final now-age | Final frozen-age | Anchor valid |
|---|---|---|---|---:|---:|---|
| `R26-4-side-offset` | `PASS` | `SIDE_PAIR` | `FULL_RATE_ANCHOR` | 0.240 | 0.240 | `True` |
| `R26-5-contradiction` | `PASS` | `SIDE_PAIR` | `ANCHOR_INVALID` | 0.280 | 0.280 | `False` |
| `R26-6-full-return` | `PASS` | `FULL_QUAD` | `FULL_QUAD` | 0.000 | 0.000 | `False` |

## R26-3 Command-Change Fixtures

| Scenario | applied at anchor | applied now | expected ff | measured ff | verdict |
|---|---:|---:|---:|---:|---|
| `constant` | 0.100 | 0.100 | 0.000 | 0.000 | `PASS` |
| `step_up_after_anchor` | 0.000 | 0.300 | 0.300 | 0.300 | `PASS` |
| `step_down_after_anchor` | 0.000 | -0.200 | -0.200 | -0.200 | `PASS` |
| `triangular_return` | 0.000 | 0.000 | 0.000 | 0.000 | `PASS` |

Telemetry coverage: `True` for rate_source/rate_anchor_age_s in every generated term row.
Anchor-age telemetry note: now-based `rate_anchor_age_s` range 0.167-0.431; frozen/no-now diagnostic range 0.167-0.167; elapsed anchor age range 0.167-0.431; now-based advances `True`; frozen/no-now static `True`.
Feed-forward corrected sigma_a oracle p95: `2.340` (oracle RMS audit `1.614`); old state-v_world p95 `4.455` (old RMS audit `1.956`); anchor-only old-reference comparison: `1.956`.
Applied-command audit: logged applied vz range 0.333-0.333; feed-forward range 0.000-0.000 (RMS `0.000`).

Artifacts: `features_f2.csv`, `full_observation_series.csv`, `anchor_trial_rows.csv`, `anchor_trial_summary.csv`, `anchor_transitions.csv`, `sigma_a_rows.csv`, `sigma_a_old_rows.csv`, `sigma_a_oracle_rows.csv`, `sigma_a_summary.csv`, `sigma_a_old_summary.csv`, `sigma_regime_summary.csv`, `sigma_percentile_envelope.csv`, `sigma_age_percentile_envelope.csv`, `sigma_old_percentile_envelope.csv`, `sigma_old_age_percentile_envelope.csv`, `heldout_age_coverage.csv`, `heldout_old_age_coverage.csv`, `reference_comparison.csv`, `reference_age_comparison.csv`, `age_distribution.csv`, `anchor_age_sweep.csv`, `floor_table.csv`, `r26_command_change_fixtures.csv`, `r26_micro_rows.csv`, `r26_micro_summary.csv`, and `summary.json`.
