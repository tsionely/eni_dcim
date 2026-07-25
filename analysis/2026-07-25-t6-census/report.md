# T6 exit census vs T5

HEAD: `cecfa39`.
T6 fixtures: **8/8**. Commit exits: **11**. Reached-gate (closest < 2 m): **6**.

## THE QUESTIONS

1. Did `corridor_abort` exits drop? **YES — corridor_abort dropped**: T5 3/3 (100%) → T6 5/6 (83%).
2. Did exit `down` move from −0.77 toward 0? **YES — down moved toward 0**: T5 median down=-0.768 m → T6 median down=-0.602 m (Δ=+0.166 m; corridor_abort exits).

## Direct comparison

| metric | T5 | T6 | Δ |
| --- | ---: | ---: | ---: |
| fixtures | 6 | 8 | |
| reached-gate exits | 3 | 6 | |
| corridor_abort (reached) | 3 | 5 | +2 |
| corridor_abort fraction | 1.000 | 0.833 | 0.167 |
| down median (corr / reached) | -0.768 | -0.602 | 0.166 |
| right median | 0.029 | -0.265 | |
| fwd median | 0.986 | 1.017 | |

## (1) T6 exit-reason histogram — reached-gate

| reason | n_reached | n_all |
| --- | ---: | ---: |
| `pass` | 1 | 1 |
| `stale_budget` | 0 | 3 |
| `relock_jump` | 0 | 0 |
| `geometric_behind` | 0 | 1 |
| `term_abort` | 0 | 0 |
| `corridor_abort` | 5 | 5 |
| `timer_expired` | 0 | 1 |

## (2) Per-exit down/right at reached-gate (T6)

| fixture | # | reason | right | down | fwd | age_s | closest_m |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| `20260725T221057-raceprep-t6-B-run2` | 1 | `corridor_abort` | -0.267 | -0.705 | 1.239 | 0.021 | 1.399 |
| `20260725T221738-raceprep-t6-B-run4` | 2 | `pass` | -0.006 | 0.051 | 0.215 | 0.266 | 0.221 |
| `20260725T221738-raceprep-t6-B-run4` | 3 | `corridor_abort` | -0.695 | -0.602 | 1.048 | 0.211 | 1.394 |
| `20260725T222348-raceprep-t6-B-run6` | 1 | `corridor_abort` | -0.265 | -0.439 | 0.941 | 0.036 | 1.072 |
| `20260725T222642-raceprep-t6-B-run7` | 1 | `corridor_abort` | 0.243 | -0.404 | 0.933 | 0.013 | 1.045 |
| `20260725T222937-raceprep-t6-B-run8` | 1 | `corridor_abort` | 0.088 | -0.883 | 1.017 | 0.015 | 1.349 |

## Per-fixture

| fixture | gates | n_exits | n_reached |
| --- | ---: | ---: | ---: |
| `20260725T220819-raceprep-t6-B-run1` | 0 | 0 | 0 |
| `20260725T221057-raceprep-t6-B-run2` | 0 | 2 | 1 |
| `20260725T221450-raceprep-t6-B-run3` | 0 | 0 | 0 |
| `20260725T221738-raceprep-t6-B-run4` | 1 | 3 | 2 |
| `20260725T222057-raceprep-t6-B-run5` | 0 | 2 | 0 |
| `20260725T222348-raceprep-t6-B-run6` | 0 | 2 | 1 |
| `20260725T222642-raceprep-t6-B-run7` | 0 | 1 | 1 |
| `20260725T222937-raceprep-t6-B-run8` | 1 | 1 | 1 |

## Artifacts

- `reached_exits.csv` / `all_exits.csv`
- `summary.json`
- `run_t6_census.py`

