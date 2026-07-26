# FRONT-B1 — vertical alignment read

HEAD: `cf937bc`.
Fixtures: **7/10** (`raceprep-b1-B`). Final-1.5m commit attempts: **10** (PASS=3, FAIL=7).

PASS label = race HUD gate increment associated to the prior commit window (slack ≤2s after commit end). On this baseline the score always lands *after* `corridor_abort` — never inside the commit window. Geometric `fwd≤0` is NOT used (false positives on retries).

## Detection source proxy

Logs have no `detection.source`. Proxy: `confidence < 0.55` → `close_tracker` (matches estimator position-only path); `confidence ≥ 0.55` + nearby `feature.mode=FULL_QUAD` → `full_quad`; high conf without FULL_QUAD nearby → `full_quad_unconfirmed`.

## (1) Does `down` JUMP at full-quad → close-tracker handoff?

**NO material jump** — 2 handoff(s), |Δdown| median=0.026 m (0 with |Δ|>0.15 m). Handoff is not the vertical killer.
- PASS handoffs: 0/3; jump median=— m
- FAIL handoffs: 2/7; jump median=-0.017 m

## (2) THE DECIDING SPLIT — estimate vs control

**MIXED/UNCLEAR** primary on FAIL (5/7; CONTROL 2, ESTIMATE 0). Residuals stay small (median 0.001 m) — belief is smooth — while some fails climb through center (down→0/+) with adequate command integral. Low arrival is not an estimate jump.

| mechanism | PASS | FAIL |
| --- | ---: | ---: |
| ESTIMATE-driven | 0 | 0 |
| CONTROL-driven | 3 | 2 |
| MIXED/UNCLEAR | 0 | 5 |

Scores: handoff |Δdown|>0.15 or smooth-track residual>0.20 → estimate; control_deficit (needed climb − commanded climb integral)>0.25 and inadequate climb while down stays low → control. `v_body[2]` negative = climb (NED down-positive).

## (3) PASS vs FAIL final-meter vertical

PASS attempts abort still **~1.350 m out** at `down≈-0.789` (exits: {'corridor_abort': 3}), then the race counter ticks 0.930 s later (coast-through after corridor abort). FAIL attempts that continue closer reach median closest `0.700` m with `down≈-0.334` (exits: {'stale_budget': 3, '?': 3, 'corridor_abort': 1}).

| metric | PASS | FAIL |
| --- | ---: | ---: |
| n attempts | 3 | 7 |
| closest range (median) | 1.350 | 0.700 |
| down @ closest (median) | -0.789 | -0.334 |
| down @ entry (median) | -0.788 | -0.478 |
| down median in window | -0.789 | -0.378 |
| mean v_cmd_vz | -1.200 | -1.019 |
| climb_cmd integral (m) | 0.048 | 0.425 |
| control_deficit (m) | 0.762 | -0.084 |
| residual vs smooth track | 0.001 | 0.054 |
| frac close_tracker ticks | 0.000 | 0.000 |
| race-pass lag after commit (s) | 0.930 | — |

## Per-attempt

| fixture | # | label | exit | mechanism | closest | down | deficit | resid | handoffΔ |
| --- | ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `20260725T233817-raceprep-b1-B-run1` | 1 | **FAIL** | stale_budget | MIXED/UNCLEAR | 0.177 | 0.170 | -0.192 | -0.026 | — |
| `20260725T234134-raceprep-b1-B-run2` | 1 | **PASS** | corridor_abort | CONTROL-driven | 1.230 | -0.771 | 0.579 | -0.010 | — |
| `20260725T234134-raceprep-b1-B-run2` | 2 | **FAIL** | — | MIXED/UNCLEAR | 0.679 | -0.334 | -0.089 | 0.133 | -0.043 |
| `20260725T234407-raceprep-b1-B-run3` | 1 | **PASS** | corridor_abort | CONTROL-driven | 1.386 | -0.789 | 0.762 | 0.004 | — |
| `20260725T234407-raceprep-b1-B-run3` | 2 | **FAIL** | stale_budget | MIXED/UNCLEAR | 0.700 | 0.200 | -0.400 | — | — |
| `20260725T234642-raceprep-b1-B-run4` | 2 | **FAIL** | stale_budget | CONTROL-driven | 0.883 | -0.418 | 0.364 | — | — |
| `20260725T234851-raceprep-b1-B-run5` | 1 | **PASS** | corridor_abort | CONTROL-driven | 1.350 | -0.906 | 0.922 | 0.001 | — |
| `20260725T234851-raceprep-b1-B-run5` | 2 | **FAIL** | corridor_abort | CONTROL-driven | 1.400 | -0.552 | 0.579 | — | — |
| `20260725T235104-raceprep-b1-B-run6` | 1 | **FAIL** | — | MIXED/UNCLEAR | 0.339 | -0.014 | -0.084 | — | — |
| `20260726T000452-raceprep-b1-B-run7` | 1 | **FAIL** | — | MIXED/UNCLEAR | 0.778 | -0.498 | 0.192 | — | 0.008 |

## Per-fixture gates

| fixture | gates_passed | n_final_meter_attempts |
| --- | ---: | ---: |
| `20260725T233817-raceprep-b1-B-run1` | 0 | 1 |
| `20260725T234134-raceprep-b1-B-run2` | 1 | 2 |
| `20260725T234407-raceprep-b1-B-run3` | 1 | 2 |
| `20260725T234642-raceprep-b1-B-run4` | 0 | 1 |
| `20260725T234851-raceprep-b1-B-run5` | 1 | 2 |
| `20260725T235104-raceprep-b1-B-run6` | 0 | 1 |
| `20260726T000452-raceprep-b1-B-run7` | 0 | 1 |

## Artifacts

- `final_meter_ticks.csv` — per-tick down / vz / source
- `attempts.csv` — per-attempt summary
- `summary.json`
- `run_frontb1_vertical.py`

