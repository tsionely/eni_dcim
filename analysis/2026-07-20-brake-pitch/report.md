# Brake-pitch adjudication (cohorts 1–3)

**Verdict:** FILE_CLOSES — bottom-edge exits occur without brake nose-up (pitch<3° majority); FOV/geometry dominates; queued brake-pitch fix not justified by this table

- pitch_adjudicates: **False**
- queued fix (decel 5–6m, θ≤3–4°): **False**
- n in 3–4.5m band with pitch+border: 6 (bottom=4, side=0, none=2)
- mean pitch bottom vs other: -3.8324059334663456 vs -4.276961505652821

R_drop ref (cam elev 11.2°): 6°→3.7m, 8°→4.5m.

## Loss-frame table

| cohort | slot | arm | R_near | pitch° | bbox_bottom | exit | brake≥3° | mode |
|--------|-----:|-----|-------:|-------:|------------:|:----:|:--------:|------|
| cohort1 | 1 | control | 2.42 | -10.7 | 359 | bottom | False | held_or_reacq |
| cohort1 | 2 | live | nan | nan | nan | none | False | no_commit |
| cohort1 | 3 | control | 3.67 | 0.1 | 453 | bottom | False | fov_leave |
| cohort1 | 4 | live | 1.08 | -0.7 | 451 | bottom+side | False | fov_leave |
| cohort1 | 5 | control | 4.96 | -1.9 | 359 | bottom | False | fov_leave |
| cohort1 | 6 | live | 5.28 | -4.4 | 359 | bottom | False | held_or_reacq |
| cohort2 | 1 | control | 4.04 | -6.4 | 359 | bottom | False | fov_leave |
| cohort2 | 2 | live | 4.24 | -1.9 | 359 | bottom | False | fov_leave |
| cohort2 | 3 | control | 1.90 | 3.0 | 359 | bottom | True | fov_leave |
| cohort2 | 4 | live | 2.93 | -2.7 | 359 | bottom | False | fov_leave |
| cohort2 | 5 | control | 4.40 | -6.0 | 333 | none | False | far_gate_contest |
| cohort2 | 6 | live | 1.81 | -2.3 | 359 | bottom+side | False | fov_leave |
| cohort3 | 1 | control | nan | nan | nan | none | False | no_commit |
| cohort3 | 2 | live | 1.44 | -1.4 | 359 | bottom | False | fov_leave |
| cohort3 | 3 | control | 4.26 | -7.1 | 359 | bottom | False | fov_leave |
| cohort3 | 4 | live | 1.91 | -3.5 | 359 | bottom | False | fov_leave |
| cohort3 | 5 | control | nan | 2.3 | nan | bottom | False | fov_leave |
| cohort3 | 6 | live | 3.25 | -2.5 | 321 | none | False | detector_drop_or_lock_reject |

Pitch is from `q_att` (live attitude). Logged `level_pitch` is the frozen rest calibration (−17.8°) and is **not** used.

## Deliverables

- `loss_frame_brake_pitch.csv`, `summary.json`, this report
