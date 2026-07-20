# HOLD-LIFT P4 Replay Timing

Definition: detector-only vs parallel-tracker builds replayed on the same recorded real-resolution frames; compare unique exposures processed, FULL fixes, SIDE rows, feature delivery age, P95/P99 frame processing time.

Role: QA & MOCK-TUNER. Scope: recorded-video replay only; no real simulator was launched.
Source commit: `3b554f38c01b120edb461a01070b749d4dd1caeb`.
Repo HEAD: `39428378f4a914f29be9092f5072df3bf57b8f9c`.
Non-tuning delta from `3b554f3`: `[]`.

| Flight | Arm | Unique exposures | FULL fixes | accepted FULL | feature rows | SIDE rows | fallback SIDE | total wall ms | detector P95/P99 | tracker calls | tracker P95/P99 | feature age P95/P99 | frame mean/P95/P99/max |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `F2` | `detector_only` | 141 | 125 | 81 | 81 | 0 | 0 | 185.901 | 1.410/1.561 | 0 | n/a/n/a | 1.395/1.545 | 1.318/1.482/1.686/3.725 |
| `F2` | `parallel_tracker` | 141 | 125 | 81 | 108 | 27 | 9 | 418.374 | 1.575/1.722 | 34 | 7.186/9.958 | 8.300/8.711 | 2.967/8.286/8.694/12.457 |
| `F4` | `detector_only` | 120 | 115 | 64 | 64 | 0 | 0 | 155.483 | 1.370/1.647 | 0 | n/a/n/a | 1.465/1.636 | 1.296/1.441/1.674/1.848 |
| `F4` | `parallel_tracker` | 120 | 115 | 56 | 70 | 14 | 2 | 275.360 | 1.434/1.952 | 17 | 7.388/7.432 | 8.584/8.947 | 2.295/8.491/8.800/9.270 |

Result: parallel tracker preserved the same unique exposure count as detector-only and added SIDE rows only in the parallel arm; use the table above for the P4 board entry.

Artifacts: `p4_summary.csv`, `p4_feature_rows.csv`, `summary.json`, and `summary.md`.
