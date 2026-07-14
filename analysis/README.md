# Analysis artifacts (DATA ANALYST)

This directory is the DATA ANALYST commit surface (see `AGENTS.md`).

## Reports

| file | standing task |
|---|---|
| `20260714-detector-eval-at-scale.md` | #1 detector eval at scale |
| `hard_frames/` | #1/#2 hardest-frame mining |
| `20260714-interesting-slices.md` | #2 interesting-moment slices |
| `20260714-flight-kinematics.md` | #3 flight kinematics |
| `plots/` | #3 plots |
| `20260714-cross-checks.md` | #4 cross-checks |

## Harnesses (re-runnable)

- `eval_detector_scale.py` — full recording sweep + hard frames
- `remine_hard_frames.py` — diversified hard-frame remine
- `report_flight_kinematics.py` — flight.jsonl plots/reports
- `make_interesting_slices.py` — write `fixtures/<stamp>-analysis-slices/`

Point `--recordings-root` / `--logs-root` at the operator checkout that holds
the large `.aigprec` files (not committed).
