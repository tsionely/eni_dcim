# R26 Anchor Run

Role: QA & MOCK-TUNER.
Scope: recorded-video replay plus synthetic oracle micro-replays only; no real simulator was launched.
Source commit: `3c4c5d9263bbbde30c1332614b974d2fe6978b1e`.
Repo HEAD: `3c4c5d9263bbbde30c1332614b974d2fe6978b1e`.
Non-tuning delta from `3c4c5d9`: `[]`.

## R26-1 Liveness

| Trial | Drop frame | First capture R | TERM/SIDE rows | Side captures | Side max score | Min side R | Transitions | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `anchor_drop_frame_304` | 304 | 1.903 | 16 | 1 | 0.271 | 1.006 | 1 | `PASS` |
| `anchor_drop_frame_306` | 306 | 1.903 | 0 | 0 | n/a | n/a | 0 | `FAIL` |
| `anchor_drop_frame_308` | 308 | 1.903 | 0 | 0 | n/a | n/a | 0 | `FAIL` |

Overall R26-1 verdict: `PASS`.

## R26-2/3 Sigma-a

| Anchor age bin | n | age range | rate error RMS | sigma_a RMS | sigma_a centered |
|---|---:|---|---:|---:|---:|
| `all` | 16 | 0.167-0.431 | 0.498 | 1.956 | 1.719 |
| `0p10-0p20` | 3 | 0.167-0.194 | 0.104 | 0.537 | 0.223 |
| `0p20-0p30` | 6 | 0.229-0.299 | 0.724 | 3.009 | 2.235 |
| `0p30-0p50` | 7 | 0.333-0.431 | 0.337 | 0.926 | 0.693 |
| `gte0p50` | 0 | n/a-n/a | n/a | n/a | n/a |

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
| 1.956 | 1.046 | `False` | `True` |
| 2.000 | 1.068 | `False` | `False` |
| 3.000 | 1.565 | `False` | `False` |

Overall R26-2/3 verdict: `FAIL`.

## R26-4/5/6 Replays

| Scenario | Verdict | Final source | Final rate source | Final anchor age | Anchor valid |
|---|---|---|---|---:|---|
| `R26-4-side-offset` | `PASS` | `SIDE_PAIR` | `FULL_RATE_ANCHOR` | 0.240 | `True` |
| `R26-5-contradiction` | `PASS` | `SIDE_PAIR` | `ANCHOR_INVALID` | 0.280 | `False` |
| `R26-6-full-return` | `PASS` | `FULL_QUAD` | `FULL_QUAD` | 0.000 | `False` |

Telemetry coverage: `True` for rate_source/rate_anchor_age_s in every generated term row.
Anchor-age telemetry note: code `rate_anchor_age_s` range 0.167-0.167; elapsed anchor age range 0.167-0.431; frozen-age flag `True`.

Artifacts: `features_f2.csv`, `anchor_trial_rows.csv`, `anchor_trial_summary.csv`, `anchor_transitions.csv`, `sigma_a_rows.csv`, `sigma_a_summary.csv`, `floor_table.csv`, `r26_micro_rows.csv`, `r26_micro_summary.csv`, and `summary.json`.
