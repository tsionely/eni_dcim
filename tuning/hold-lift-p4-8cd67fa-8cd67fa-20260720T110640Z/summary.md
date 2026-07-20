# HOLD-LIFT P4 Replay Timing

Definition: detector-only vs parallel-tracker builds replayed on the same recorded real-resolution frames; compare unique exposures processed, FULL fixes, SIDE rows, feature delivery age, P95/P99 frame processing time.

Role: QA & MOCK-TUNER. Scope: recorded-video replay only; no real simulator was launched.
Source commit: `8cd67fa41240f5c3f6e289ebea5837a911a32234`.
Repo HEAD: `8cd67fa41240f5c3f6e289ebea5837a911a32234`.
Non-tuning delta from `8cd67fa`: `[]`.

| Flight | Arm | Unique exposures | FULL fixes | accepted FULL | SIDE rows | feature age P95/P99 ms | frame P95/P99 ms |
|---|---|---:|---:|---:|---:|---:|---:|
| `F2` | `detector_only` | 141 | 125 | 81 | 0 | 1.408/1.485 | 1.505/1.656 |
| `F2` | `parallel_tracker` | 141 | 125 | 81 | 27 | 8.230/8.468 | 8.175/8.464 |
| `F4` | `detector_only` | 120 | 115 | 64 | 0 | 1.453/1.589 | 1.414/1.476 |
| `F4` | `parallel_tracker` | 120 | 115 | 56 | 14 | 8.403/8.956 | 8.287/8.838 |

Result: parallel tracker preserved the same unique exposure count as detector-only and added SIDE rows only in the parallel arm; use the table above for the P4 board entry.

Artifacts: `p4_summary.csv`, `p4_feature_rows.csv`, `summary.json`, and `summary.md`.
