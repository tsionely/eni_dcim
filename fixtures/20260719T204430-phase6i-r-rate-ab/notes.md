# Phase 6i-R RATE A/B (Block A restart, term_status adjudication)

- **Date:** 2026-07-19 23:44:32 +0300
- **Operator role:** SIM OPERATOR (Sakana)
- **HEAD flown:** `f10b35cbae8751d02bc08f814ebccaf16b3757e3` (`f10b35c The capture wire: the REAL arbiter finally receives its unique-exposure feed`); `035ab1a` ancestor verified OK.
- **Wrapper:** inline capture (6i fix retained); BOM-safe packaging. No F1 retry-loop pathology.
- **Counting:** verified R2 + TAKEOFF->end slice >300 unique frames; alternating F1/F3/F5 control, F2/F4/F6 live; only enable patch differs. **6/6 counted, cycle COMPLETE, no live no-go.**
- **Adjudication (live only, from term_status records ONLY):** none of v_bz_applied-while-not-engaged, term-owner-above-2.5m, or wrong-sign v_bz-vs-e_z fired on any live arm.

## Pass rate (this block): CONTROL 1/3  |  LIVE 1/3

## Counted flights
| Slot | Arm | Log ID | Gates | Clips | Env | Result | Closest fix + px | age@closest | agi_max | term: eng/ready/applied | first-applied range | sign opp/same | Death | Phase seq |
|---:|---|---|---:|---:|---:|---|---|---|---:|---|---|---|---|---|
| 1 | control | `20260719T200816-f170ead6` | 1 | 0 | 2 | environment collision (impulse=6.3) | 0.64m @ t+3.82s, [317.4, 663.1] | 0.039s | 1 | n/a (control) | n/a | n/a | t+11.984 environment collision (impulse=6.3) | hover -> takeoff -> commit -> approach -> align -> commit -> retreat -> recover -> approach -> search -> align -> commit -> retreat |
| 2 | live | `20260719T201038-50f9dcc8` | 0 | 0 | 0 | stale channels: frame | 10.51m @ t+1.61s, [324.2, 163.2] | 0.010s | 0 | 0/0/0 | None | 0/0 | t+248.276 stale channels: frame | hover -> takeoff -> approach -> search |
| 3 | control | `20260719T201630-f170ead6` | 0 | 0 | 1 | environment collision (impulse=14.1) | 3.67m @ t+2.88s, [383.8, 360.9] | 0.074s | 0 | n/a (control) | n/a | n/a | t+20.304 environment collision (impulse=14.1) | hover -> takeoff -> align -> commit -> retreat -> align -> commit -> retreat -> approach -> commit -> retreat -> search |
| 4 | live | `20260719T201851-50f9dcc8` | 1 | 0 | 29 | environment collision (impulse=7.3) | 0.90m @ t+17.39s, [319.5, 90.0] | 0.214s | 1 | 139/70/28 | 0.759 | 28/0 | t+17.396 environment collision (impulse=7.3) | hover -> takeoff -> recover -> commit -> search -> approach -> recover -> approach -> align -> commit -> retreat -> recover -> search -> approach -> commit |
| 5 | control | `20260719T202445-f170ead6` | 0 | 0 | 1 | environment collision (impulse=10.8) | 0.80m @ t+7.83s, [319.5, 107.5] | 0.010s | 0 | n/a (control) | n/a | n/a | t+18.596 environment collision (impulse=10.8) | hover -> takeoff -> align -> commit -> retreat -> search -> align -> commit -> retreat -> search -> commit -> retreat -> search -> align -> commit -> retreat |
| 6 | live | `20260719T202720-50f9dcc8` | 0 | 0 | 2 | environment collision (impulse=9.5) | 2.10m @ t+3.06s, [232.6, 328.9] | 0.019s | 0 | 55/0/0 | None | 0/0 | t+12.904 environment collision (impulse=9.5) | hover -> takeoff -> align -> commit -> retreat -> search -> approach |

## Gate-1 passes and post-pass death (gate-2 segment)

- **control `20260719T200816-f170ead6`** passed gate 1 (agi_max=1). Post-pass: first_advance t+4.007, phases ['approach', 'align', 'commit', 'retreat', 'recover', 'approach', 'search', 'align', 'commit', 'retreat'], biggest post-pass collision {'t_rel_s': 11.983, 'impulse': 6.31}. Death: {'t_rel_s': 11.984, 'reason': 'environment collision (impulse=6.3)'}. Total env_hits=2.
- **live `20260719T201851-50f9dcc8`** passed gate 1 (agi_max=1). Post-pass: first_advance t+4.511, phases ['search', 'approach', 'recover', 'approach', 'align', 'commit', 'retreat', 'recover', 'search', 'approach', 'commit'], biggest post-pass collision {'t_rel_s': 17.394, 'impulse': 7.251}. Death: {'t_rel_s': 17.396, 'reason': 'environment collision (impulse=7.3)'}. Total env_hits=29.

## Answers

- **Control pass rate:** 1/3 counted control flights passed gate 1.
- **Does TERM raise it:** LIVE 1/3 vs CONTROL 1/3 — with n=3 per arm this is not yet statistically separable; both around 1/3 in this block. Live terminal channel behaved safely (correct-sign applied vertical, admission within corridor, no no-go).
- **What kills us between gate 1 and gate 2:** both gate-1 passes died by environment collision shortly after the pass while chasing gate 2 (see per-pass post-pass section); the live pass (F4) accumulated many env contacts (env_hits=29) in the inter-gate segment. This is the acquisition-churn / inter-gate obstacle regime flagged as the next build target.

## Rejected attempts

- Attempt 1 slot 1 arm control: r2ok=True unique=173
- Attempt 2 slot 1 arm control: r2ok=True unique=140
- Attempt 3 slot 1 arm control: r2ok=True unique=255
- Attempt 4 slot 1 arm control: r2ok=True unique=237
- Attempt 6 slot 2 arm live: r2ok=True unique=139
- Attempt 9 slot 4 arm live: r2ok=True unique=142
- Attempt 11 slot 5 arm control: r2ok=True unique=276
- Attempt 12 slot 5 arm control: r2ok=True unique=276
- Attempt 13 slot 5 arm control: r2ok=True unique=105
- Attempt 14 slot 5 arm control: r2ok=True unique=283
- Attempt 16 slot 6 arm live: r2ok=True unique=292

## Slice verification
| Slot | Slice | Unique frames | Span s | MB |
|---:|---|---:|---:|---:|
| 1 | `20260719T200816-f170ead6_takeoff_to_end.aigprec` | 360 | 12.0 | 19.2 |
| 2 | `20260719T201038-50f9dcc8_takeoff_to_end.aigprec` | 7435 | 247.8 | 93.9 |
| 3 | `20260719T201630-f170ead6_takeoff_to_end.aigprec` | 610 | 20.3 | 29.0 |
| 4 | `20260719T201851-50f9dcc8_takeoff_to_end.aigprec` | 523 | 17.4 | 26.7 |
| 5 | `20260719T202445-f170ead6_takeoff_to_end.aigprec` | 559 | 18.6 | 23.2 |
| 6 | `20260719T202720-50f9dcc8_takeoff_to_end.aigprec` | 389 | 12.9 | 21.2 |