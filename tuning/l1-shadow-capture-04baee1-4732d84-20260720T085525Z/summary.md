# L1 Shadow Capture Addendum

Role: QA & MOCK-TUNER.
Scope: recorded video replay only; no real simulator was launched, reset, clicked, or commanded.
Source commit under test: `04baee11e3d42d1519e718ce3c11d17e2577ee31`.
Repo HEAD while running: `4732d84fe79c834bf75666c8d72b02769a654b3c`.
Non-tuning delta from `04baee1`: `[]`.
Runtime patches: `[]`.

## Inputs

- `F2` `20260720T071112-cd18c5fb`: 141 frames, detector fixes 125, tracker fixes 13, feature rows 90.
- `F4` `20260720T071333-cd18c5fb`: 120 frames, detector fixes 115, tracker fixes 2, feature rows 58.
- `F6` `20260720T071545-cd18c5fb`: 104 frames, detector fixes 103, tracker fixes 1, feature rows 87.

## Shadow Capture Bar

| Sweep | Flight | Commit rows | Ready | Capture rows | Captures <=2.2m | First capture R | First source | TERM rows | TERM/SIDE rows | Min score | Sigma abort rows | Transitions | Held full->side |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| `baseline` | `F2` | 25 | 5 | 1 | 1 | 1.903 | `FULL_QUAD` | 14 | 0 | 0.221 | 1 | 0 | `False` |
| `baseline` | `F4` | 26 | 21 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.639 | 0 | 0 | `False` |
| `baseline` | `F6` | 11 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `F2` | 25 | 4 | 2 | 2 | 1.064 | `FULL_QUAD` | 2 | 0 | 0.266 | 1 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `F4` | 26 | 21 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.639 | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `F6` | 11 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `F2` | 25 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `F4` | 26 | 21 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.639 | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `F6` | 11 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `F2` | 25 | 14 | 1 | 1 | 1.903 | `FULL_QUAD` | 14 | 0 | 0.221 | 1 | 0 | `False` |
| `drop_full_below_1p5m` | `F4` | 26 | 21 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.639 | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `F6` | 11 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `F2` | 25 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `F4` | 26 | 21 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.639 | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `F6` | 11 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |

## Transition Log

No full->side source transition was observed.

## Verdict

NO-PASS: shadow capture or full->side hold was not observed in this recorded-video replay set. Treat this as a liveness gap, not a real sim run.

Artifacts: `features.csv`, `observer_timeline.csv`, `shadow_capture_timeline.csv`, `shadow_capture_summary.csv`, `shadow_source_transitions.csv`, `observer_source_transitions.csv`, and `summary.json`.
