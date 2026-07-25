# T5 exit-reason census

HEAD: `c8337f0`.
Fixtures: **6**. Commit exits: **7**. Reached-gate (closest < 2 m): **3**. Near-misses (reached ∧ reason≠pass): **3**.

## (1) Exit-reason histogram — reached-gate attempts

| reason | n_reached | n_all |
| --- | ---: | ---: |
| `pass` | 0 | 0 |
| `stale_budget` | 0 | 4 |
| `relock_jump` | 0 | 0 |
| `geometric_behind` | 0 | 0 |
| `term_abort` | 0 | 0 |
| `corridor_abort` | 3 | 3 |
| `timer_expired` | 0 | 0 |

## (3) Dominant near-miss exit cause

**`corridor_abort`** — 3/3 near-misses (100%).
At exit (believed): fwd median=0.986 m, range [0.982, 1.066]; right median=0.029 m; down median=-0.768 m; age median=0.002 s.

## (2) Per-exit believed geometry (reached-gate)

| fixture | # | reason | right | down | fwd | age_s | closest_m |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| `20260725T214934-raceprep-t5-B-run4` | 1 | `corridor_abort` | 0.029 | -0.768 | 0.982 | 0.001 | 1.247 |
| `20260725T215259-raceprep-t5-B-run5` | 1 | `corridor_abort` | 0.026 | -0.885 | 0.986 | 0.024 | 1.325 |
| `20260725T215552-raceprep-t5-B-run6` | 1 | `corridor_abort` | 0.594 | -0.533 | 1.066 | 0.002 | 1.332 |

## Per-fixture

| fixture | gates | n_exits | n_reached |
| --- | ---: | ---: | ---: |
| `20260725T214011-raceprep-t5-B-run1` | 1 | 0 | 0 |
| `20260725T214257-raceprep-t5-B-run2` | 1 | 1 | 0 |
| `20260725T214624-raceprep-t5-B-run3` | 0 | 3 | 0 |
| `20260725T214934-raceprep-t5-B-run4` | 1 | 1 | 1 |
| `20260725T215259-raceprep-t5-B-run5` | 0 | 1 | 1 |
| `20260725T215552-raceprep-t5-B-run6` | 0 | 1 | 1 |

## Artifacts

- `reached_exits.csv` / `all_exits.csv`
- `summary.json`
- `run_exit_census.py`

Note: `gate_rel_t` is the *believed* camera-frame pose at exit
(right/down/fwd). True-world reconstruction is not in the
`commit_exit` record; age is the freshness of that believed pose.

