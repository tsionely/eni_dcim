# T7 exit census vs T5 / T6

HEAD: `baabce7`.
T7 fixtures: **8/8**. Commit exits: **12**. Reached-gate (closest < 2 m): **5**.

## THE TWO QUESTIONS

1. Did `corridor_abort` drop sharply (offset 0.7)? **YES — corridor_abort eliminated**: T5 3/3 → T6 5/6 → T7 0/5.
2. Did gate-clip aborts rise? **YES — gate clips rose**: T6 clips_sum=4 (clip-budget aborts=0) → T7 clips_sum=6 (clip-budget aborts=0/8). 0.7 may be past the physical envelope (clip instead of abort).

## Direct comparison

| metric | T5 | T6 | T7 |
| --- | ---: | ---: | ---: |
| fixtures | 6 | 8 | 8 |
| gate passes (sum/block) | 3/6 | 2/8 | 2/8 |
| reached-gate exits | 3 | 6 | 5 |
| corridor_abort / reached | 3/3 | 5/6 | 0/5 |
| corridor_abort fraction | 1.000 | 0.833 | 0.000 |
| median down @ reached exit | -0.768 | -0.521 | -0.662 |
| gate_clips sum | 3 | 4 | 6 |
| clip-budget aborts | 0 | 0 | 0 |

## (5) Next-lever target

**NEW DOMINANT EXIT: `stale_budget`** — 3/5 near-misses (corridor_frac=0.000, gates=2/8).
Geometry at exit: down median=-0.740, right median=-0.203, fwd median=0.754, age median=0.617 s.

## (1) Exit-reason histogram — reached-gate

| reason | n_reached | n_all |
| --- | ---: | ---: |
| `pass` | 0 | 0 |
| `stale_budget` | 3 | 9 |
| `relock_jump` | 0 | 0 |
| `geometric_behind` | 0 | 0 |
| `term_abort` | 0 | 0 |
| `corridor_abort` | 0 | 0 |
| `timer_expired` | 2 | 3 |

## (2) Per reached-gate exit geometry

| fixture | # | reason | right | down | fwd | age_s | closest_m |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| `20260725T224000-raceprep-t7-B-run1` | 1 | `stale_budget` | -0.187 | -0.869 | 1.564 | 0.617 | 1.799 |
| `20260725T224000-raceprep-t7-B-run1` | 2 | `stale_budget` | -0.203 | -0.649 | -0.139 | 0.610 | 0.694 |
| `20260725T224331-raceprep-t7-B-run2` | 1 | `timer_expired` | -0.170 | -0.662 | 1.194 | 0.000 | 1.102 |
| `20260725T224331-raceprep-t7-B-run2` | 2 | `timer_expired` | 0.032 | -0.343 | 0.965 | 0.000 | 1.025 |
| `20260725T225148-raceprep-t7-B-run7` | 1 | `stale_budget` | -0.979 | -0.740 | 0.754 | 0.619 | 1.440 |

## Gate clips per run

| fixture | gates | gate_clips | clip-budget abort | abort_reason |
| --- | ---: | ---: | --- | --- |
| `20260725T224000-raceprep-t7-B-run1` | 0 | 0 | False | stale channels: frame(0.500s) |
| `20260725T224331-raceprep-t7-B-run2` | 0 | 1 | False | stale channels: frame(0.500s) |
| `20260725T224518-raceprep-t7-B-run3` | 0 | 1 | False | stale channels: frame(0.504s) |
| `20260725T224701-raceprep-t7-B-run4` | 1 | 2 | False | stale channels: frame(0.504s) |
| `20260725T224836-raceprep-t7-B-run5` | 0 | 0 | False | stale channels: frame(0.500s) |
| `20260725T225011-raceprep-t7-B-run6` | 0 | 0 | False | stale channels: frame(0.504s) |
| `20260725T225148-raceprep-t7-B-run7` | 1 | 1 | False | environment collision (impulse=12.9) |
| `20260725T225415-raceprep-t7-B-run8` | 0 | 1 | False | stale channels: frame(0.500s) |

## Artifacts

- `reached_exits.csv` / `all_exits.csv`
- `summary.json`
- `run_t7_census.py`

