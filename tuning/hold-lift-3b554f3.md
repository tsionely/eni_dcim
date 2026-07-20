# HOLD-LIFT Run on 3b554f3

Role: QA & MOCK-TUNER. Scope stayed replay/mock only; no real simulator was launched.

Source target: `3b554f38c01b120edb461a01070b749d4dd1caeb`.
Repo HEAD used for tuning harness/artifacts: `39428378f4a914f29be9092f5072df3bf57b8f9c`.
Non-tuning delta from `3b554f3`: `[]`.

Artifacts:

- R26/SIGMA_A: `tuning/hold-lift-r26-3b554f3-3942837-20260720T115535Z/`
- P4 wall-clock: `tuning/hold-lift-p4-3b554f3-3942837-20260720T115546Z/`
- R26 reference provenance pin: `tuning/hold-lift-r26-3b554f3-35bfa6d-20260720T121704Z/`

## 0. Reference Provenance Pin Rerun

Rerun on repo HEAD `35bfa6d9d1bbd2bbce036c7fe3089d0d587c47b5` confirmed the previous `truth-v_z` reference was the believed-state `state.v_world` channel de-tilted into the stored level frame. That old channel is now audit-only because it carries the known caged-gravity sawtooth risk.

The ruling-specified reference is now computed as withheld FULL_QUAD oracle velocity: Theil-Sen slope over withheld full-quad `e_z` observations around each scoring instant, with `v_z_up = -slope(e_z)`. The fit uses p95 absolute sigma_a by age bin, excluding anchor age `<0.10s`; RMS is reported only as an audit number.

| Reference | n | p50 | p80 | p90 | p95 | p99 | RMS audit |
|---|---:|---:|---:|---:|---:|---:|---:|
| `old_state_v_world` | 16 | `0.957` | `2.536` | `3.495` | `4.455` | `4.455` | `1.956` |
| `withheld_full_oracle` | 16 | `1.463` | `1.905` | `2.247` | `2.340` | `2.565` | `1.614` |

Age-bin p95 comparison:

| Age bin | old p95 | oracle p95 |
|---|---:|---:|
| `0.10-0.20s` | `0.646` | `2.584` |
| `0.20-0.30s` | `4.455` | `1.905` |
| `0.30-0.50s` | `1.226` | `1.310` |

Verdict: the old reference substantially inflated the all-up p95 (`4.455 -> 2.340 m/s^2`) and the old RMS (`1.956`) was partly reference noise. However, the withheld-FULL oracle p95 is still well above the `0.35 m/s^2` drift-model gate, so R26-2/3 remains `FAIL` on this configuration rather than being cleared by the reference correction alone.

## 1. SIGMA_A Corrected With Percentile Envelope

Corrected sigma_a over runtime-authorized SIDE maintenance remains above the pre-registered gate.

- RMS: `1.956 m/s^2`.
- P95 absolute envelope: `4.455 m/s^2`.
- P95 by regime: switch-adjacent `0.646 m/s^2`; maintenance `4.455 m/s^2`.
- Advisory reading: `>0.35`, so the `(c)` floor governs. This is a configuration outcome, not a crisis.

Held-out coverage by age bin:

| Age bin | train n | heldout n | fit p95 sigma_a | heldout coverage | floor | corridor pass |
|---|---:|---:|---:|---:|---:|---|
| `0.10-0.20s` | 1 | 2 | `0.173` | `0.000` | `0.212m` | `True` |
| `0.20-0.30s` | 4 | 2 | `4.455` | `1.000` | `2.291m` | `False` |
| `0.30-0.50s` | 3 | 4 | `1.226` | `1.000` | `0.686m` | `False` |

Applied-command audit: recorded applied vertical command was flat at `0.333-0.333 m/s`, so `applied_now - applied_at_anchor = 0.000` in this F2 maintenance window.

## 2. R26-1 Re-Stamp And Age Distributions

R26-1 remains `PASS` on `3b554f3`:

- Legal transition: `anchor_drop_frame_304`.
- `owner_term_side_rows=16`.
- Hold depth: `1.006m`.
- Side max admission: `0.271 <= 0.30`.
- Phase changed rows: `0`.

Section 6 age distributions:

- Anchor age at transition: n=`1`, min/median/max `0.167/0.167/0.167s`.
- Max age while maintaining: `0.431s`; authorized max `0.431s`.
- Age at damping onset: `0.396s`.
- Worst continuous score: `0.270` (p95 `0.270`).

The runtime score gate did not cut the observed legal hold: worst continuous score stayed below the `0.30` corridor.

## 3. R26-2/R26-3 Formal Close

Age-sweep with measured RMS sigma_a:

| Anchor age | sigma_v | floor | corridor pass | observed age used |
|---:|---:|---:|---|---|
| `0.10s` | `0.220` | `0.292m` | `True` | `True` |
| `0.20s` | `0.404` | `0.471m` | `False` | `True` |
| `0.30s` | `0.595` | `0.660m` | `False` | `True` |
| `0.40s` | `0.789` | `0.852m` | `False` | `True` |
| `0.50s` | `0.983` | `1.046m` | `False` | `False` |

R26-3 command-change fixtures: all `PASS`, including `triangular_return`.

| Scenario | applied at anchor | applied now | measured feed-forward |
|---|---:|---:|---:|
| `constant` | `0.100` | `0.100` | `0.000` |
| `step_up_after_anchor` | `0.000` | `0.300` | `0.300` |
| `step_down_after_anchor` | `0.000` | `-0.200` | `-0.200` |
| `triangular_return` | `0.000` | `0.000` | `0.000` |

## 4. P4 Wall-Clock With Section 9 Columns

Definition: detector-only vs parallel-tracker builds replayed on the same recorded real-resolution frames; compare unique exposures processed, FULL fixes, SIDE rows, feature delivery age, detector/tracker timings, and P95/P99 frame processing time.

| Flight | Arm | Unique exposures | FULL fixes | accepted FULL | feature rows | SIDE rows | fallback SIDE | total wall ms | detector P95/P99 | tracker calls | tracker P95/P99 | feature age P95/P99 | frame mean/P95/P99/max |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `F2` | `detector_only` | 141 | 125 | 81 | 81 | 0 | 0 | `185.901` | `1.410/1.561` | 0 | `n/a/n/a` | `1.395/1.545` | `1.318/1.482/1.686/3.725` |
| `F2` | `parallel_tracker` | 141 | 125 | 81 | 108 | 27 | 9 | `418.374` | `1.575/1.722` | 34 | `7.186/9.958` | `8.300/8.711` | `2.967/8.286/8.694/12.457` |
| `F4` | `detector_only` | 120 | 115 | 64 | 64 | 0 | 0 | `155.483` | `1.370/1.647` | 0 | `n/a/n/a` | `1.465/1.636` | `1.296/1.441/1.674/1.848` |
| `F4` | `parallel_tracker` | 120 | 115 | 56 | 70 | 14 | 2 | `275.360` | `1.434/1.952` | 17 | `7.388/7.432` | `8.584/8.947` | `2.295/8.491/8.800/9.270` |

Result: parallel tracker preserved unique exposure and FULL-fix counts, added SIDE rows only in the parallel arm, and moved frame P95 from about `1.4-1.5ms` to about `8.3-8.5ms`.
