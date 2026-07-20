# Telemetry completeness audit (gate row 11)

- mandatory fields checked: 31
- PRESENT in code+sample log: 12
- **MISSING that block cohort-4 adjudication: 13**
- CODE_ONLY (shipped on HEAD, awaiting flight log): 4
- missing nice-to-have: 3

## Blocks cohort-4 (build must close)

| field | status | why |
|-------|:------:|-----|
| `gate_lock_epoch` | MISSING | epoch hygiene; wrong-epoch metrology adjudication |
| `psi_age` | MISSING | S4 disposition; orientation-prior age on side rung |
| `fresh_tail_n` | MISSING | ready predicate audit (n/span/gap of contiguous tail) |
| `fresh_tail_span_s` | MISSING | ready predicate audit |
| `fresh_tail_max_gap_s` | MISSING | ready predicate audit |
| `e_z_raw` | MISSING | pre-clamp / pre-admission measurement |
| `e_z_accepted` | MISSING | post-door accepted e (or null if rejected) |
| `sigma_e` | MISSING | admission corridor + crossing test |
| `sigma_v` | MISSING | admission / rate authority |
| `transition_fields` | MISSING | from/to source, reason, overlap median Δe at switch |
| `tau_s` | MISSING | admission horizon / guidance |
| `admission_score` | MISSING | corridor residual that passed/failed capture |
| `rate_anchor_valid` | MISSING | falsification monitor outcome |

## Nice-to-have gaps

| field | status | why |
|-------|:------:|-----|
| `ready_legacy` | CODE_ONLY | dual-readiness A/B; nice for semantic check |
| `t_tail_s` | MISSING | admission parameter; static config OK if logged once |
| `rate_anchor_exposure_id` | MISSING | nice; ties anchor to exposure |

## Full table

| field | blocks C4? | status | notes |
|-------|:----------:|:------:|-------|
| `gate_lock_epoch` | True | **MISSING** |  |
| `exposure_id` | True | **PRESENT** | proxy=feature.ts_ns (exact-exposure pairing) |
| `cert_status` | True | **PRESENT** |  |
| `psi_age` | True | **MISSING** |  |
| `fresh_tail_n` | True | **MISSING** | TerminalOracle.history_stats() computes; not on TermStatus |
| `fresh_tail_span_s` | True | **MISSING** | TerminalOracle.history_stats() computes; not on TermStatus |
| `fresh_tail_max_gap_s` | True | **MISSING** | TerminalOracle.history_stats() computes; not on TermStatus |
| `ready` | True | **PRESENT** |  |
| `ready_legacy` | False | **CODE_ONLY** | on TermStatus dataclass; older logs predate field; PRESENT in TermStatus on HEAD |
| `e_z_raw` | True | **MISSING** |  |
| `e_z_accepted` | True | **MISSING** | TermStatus.e_z is effective only |
| `e_z` | True | **PRESENT** |  |
| `sigma_e` | True | **MISSING** | oracle.sigmas_for_active() exists; not logged |
| `sigma_v` | True | **MISSING** | oracle.sigmas_for_active() exists; not logged |
| `source_mode` | True | **CODE_ONLY** | on TermStatus; phase6l sample may predate; PRESENT in TermStatus on HEAD — sampl |
| `transition_fields` | True | **MISSING** |  |
| `tau_s` | True | **MISSING** |  |
| `t_tail_s` | False | **MISSING** |  |
| `admission_score` | True | **MISSING** |  |
| `owner` | True | **PRESENT** |  |
| `shadow_owner` | False | **PRESENT** |  |
| `applied_owner` | True | **PRESENT** |  |
| `rate_source` | True | **CODE_ONLY** | PRESENT in TermStatus on HEAD — sample fixture predates field |
| `rate_anchor_age_s` | True | **CODE_ONLY** | PRESENT in TermStatus on HEAD — sample fixture predates field |
| `rate_anchor_valid` | True | **MISSING** | oracle.rate_anchor_valid exists; not on TermStatus |
| `rate_anchor_exposure_id` | False | **MISSING** |  |
| `feature.mode` | True | **PRESENT** |  |
| `feature.span_px` | True | **PRESENT** |  |
| `feature.y_top_px` | True | **PRESENT** |  |
| `engaged` | True | **PRESENT** |  |
| `v_bz_applied` | True | **PRESENT** |  |

TermStatus on HEAD: `['e_z', 'engaged', 'owner', 'rate_anchor_age_s', 'rate_source', 'ready', 'ready_legacy', 'source_mode', 'ts_ns', 'v_bz_applied', 'vz_up']`

The build closes the **blocks_c4** MISSING/CODE_ONLY rows (except CODE_ONLY fields already on TermStatus that only need a HEAD flight to appear in logs).

## Deliverables

- `telemetry_gap_table.csv`, `summary.json`, this report
