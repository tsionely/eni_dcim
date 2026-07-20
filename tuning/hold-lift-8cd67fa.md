# HOLD-LIFT Run on 8cd67fa

Role: QA & MOCK-TUNER. Scope stayed replay/mock only; no real simulator was launched.

Source/repo build for both replays: `8cd67fa41240f5c3f6e289ebea5837a911a32234` (`8cd67fa`, code equivalent to `7657559` plus docs).

Artifacts:

- R26/SIGMA_A: `tuning/hold-lift-r26-8cd67fa-8cd67fa-20260720T110628Z/`
- P4 replay timing: `tuning/hold-lift-p4-8cd67fa-8cd67fa-20260720T110640Z/`

## 1. SIGMA_A Corrected

Feed-forward-corrected sigma_a over SIDE maintenance windows remains above the pre-registered gate:

- Corrected sigma_a RMS: `1.956 m/s^2`.
- Anchor-only comparison: `1.956 m/s^2`.
- Advisory-16B reading: `>0.35`, so the `(c)` floor governs. This is a configuration outcome, not a crisis.
- Floor row where measured lands: `sigma_a=1.956`, `floor=1.046m`, corridor pass `False`.

Regime split:

| Regime | n | age range | sigma_a RMS |
|---|---:|---|---:|
| `switch_adjacent` | 3 | `0.167-0.194s` | `0.537 m/s^2` |
| `maintenance` | 13 | `0.229-0.431s` | `2.154 m/s^2` |

Applied-command audit: logged applied vertical command was flat at `0.333-0.333 m/s`, so `applied_now - applied_at_anchor = 0.000`; the feed-forward path has no correction to subtract in this recorded window.

## 2. R26-1 Re-Stamp

R26-1 remains `PASS` on current `8cd67fa` code:

- Legal transition: `anchor_drop_frame_304`.
- `owner_term_side_rows=16`.
- Hold depth: SIDE maintained TERM down to `1.006m`.
- `side_shadow_capture_rows=1`.
- Max admission: `0.271 <= 0.30`.
- Phase changed rows: `0`.

Anchor-age telemetry is fixed in the current columns:

- Now-based `rate_anchor_age_s`: `0.167-0.431s`.
- Frozen/no-now diagnostic: `0.167-0.167s`.
- Elapsed anchor age: `0.167-0.431s`.

## 3. R26-2/3 Formal Close

The anchor-age sweep is monotonic with the corrected sigma_a:

| Anchor age | sigma_v | floor | corridor pass |
|---:|---:|---:|---|
| `0.10s` | `0.220` | `0.292m` | `True` |
| `0.20s` | `0.404` | `0.471m` | `False` |
| `0.30s` | `0.595` | `0.660m` | `False` |
| `0.40s` | `0.789` | `0.852m` | `False` |
| `0.50s` | `0.983` | `1.046m` | `False` |

Observed anchor use stayed within `0.431s`; no observed SIDE-maintenance sample used a stale anchor beyond the validated tail.

## 4. P4 Definition And Result

Definition: detector-only vs parallel-tracker builds replayed on the same recorded real-resolution frames; compare unique exposures processed, FULL fixes, SIDE rows, feature delivery age, P95/P99 frame processing time.

| Flight | Arm | Unique exposures | FULL fixes | accepted FULL | SIDE rows | feature age P95/P99 ms | frame P95/P99 ms |
|---|---|---:|---:|---:|---:|---:|---:|
| `F2` | `detector_only` | 141 | 125 | 81 | 0 | `1.408/1.485` | `1.505/1.656` |
| `F2` | `parallel_tracker` | 141 | 125 | 81 | 27 | `8.230/8.468` | `8.175/8.464` |
| `F4` | `detector_only` | 120 | 115 | 64 | 0 | `1.453/1.589` | `1.414/1.476` |
| `F4` | `parallel_tracker` | 120 | 115 | 56 | 14 | `8.403/8.956` | `8.287/8.838` |

Result: parallel tracker preserved the same unique exposure count and FULL-fix count, added SIDE rows only in the parallel arm, and increased P95 frame processing from about `1.4-1.5ms` to about `8.2-8.3ms`.
