# The geometry derivation table (advisory-10 §1, before cohort-2 reflight)

Every constant in the geometric chain re-derives from the measured base
set or is explicitly labeled. **A constant that cannot show its
derivation is quarantined.** Base set (all measured):

| symbol | value | provenance |
|---|---|---|
| opening half-extent (d*) | 0.80 m | GATE_GEOM v1, graze-validated (~6cm) |
| h_drone (vertical half-extent) | 0.62 m | A8, 11 graze contacts (P4) — riders pending: true_dz-at-contact confirmation + max/scatter |
| w_bar | 0.188 m | GATE_GEOM v1 |
| oracle absolute calibration | 0.06 m | d* validation tolerance (nine graze points) |
| rail slack | 0.02 m | advisory-10 ruling constant |

## Derived chain

| constant | value | derivation | status |
|---|---|---|---|
| C_contact | 0.18 | 0.80 − h_drone(0.62) | DERIVED — the no-touch band |
| cmd_clamp_m | 0.10 | C_contact − 0.06 − 0.02 | DERIVED (config `planner.terminal.cmd_clamp_m`) — bounds the servo's correction target; a wrong e_z displaces the commanded crossing by at most the no-touch band minus guards |
| corridor_interim_m | 0.30 | **CORRIDOR_INTERIM** — time-boxed operational band; expiry = cohort-2 R5 sigma library, then corridor := C_contact = 0.18 with evidence-based sigmas (projected floors 0.141 margined / 0.114 raw — passable) | INTERIM, LABELED |
| Block B injection | ±0.12 | must stay inside C_contact (±0.20 was a commanded clip); ~2.4σ vs ~0.05 delivery noise, power preserved | DERIVED (spec change, see intergate doc) |
| nudge authority | ≤0.10 | inherits cmd_clamp | DERIVED |
| admission guard | 0.06 | oracle absolute calibration, counted exactly once | MEASURED |
| abort_min_dist_m | max(0.8, v²/2a + t_react·v) | physics (advisory-6 formula) | DERIVED |
| T_irrev | abort_min/v | no-return tail from the band above | DERIVED |
| coverage_tail_p95_s | 0.50 | measured coverage tails 0.33–0.5 s on cohort-1 passes | MEASURED |
| engage_range_m | 2.5 | 2× the 1.27m authority budget at 1.8 m/s (phase6g capture-at-entry lesson) | DERIVED |
| crossing threshold | −0.4 / +0.3 | hysteresis pair around the plane, sized vs DR drift over the wash (~0.5s · drift) | OPERATIONAL — re-derive against measured DR drift at R5 milestone |
| e_z_clamp_m (measurement bound) | 0.45 | NOT geometric — measurement-domain sanity bound; kept honest ABOVE the corridor so admission and the continuous test can SEE and refuse an off-corridor arrival (clamping measurement to 0.10 would blind the epistemology exactly where it must block — safety fixture pins this) | MEASUREMENT-DOMAIN, LABELED |
| margin_m (guidance safe_to_continue) | 0.55 | predates GATE_GEOM; no derivation from the base set | **QUARANTINED** — candidate re-derivation at R5: C_pass-based band with evidence sigmas |
| abort_offset_m (commit corridor) | 0.45 | half-opening 0.80 − h_drone... = 0.18 would be doctrinal; 0.45 predates A8 | **QUARANTINED** — re-derivation owed: 0.18 + retreat-reachability term; frozen until ruled (flight-behavior constant, mid-block) |
| lateral half-extent | — | UNMEASURED — the lateral servo/corridor runs on the vertical number's assumptions | **DEBT** (advisory-10 §1) — extraction queued with the analyst |

## Notes

- The two QUARANTINED rows are flight-behavior constants inside a
  frozen block: they fly AS-IS in the cohort-2 redo (changing them
  mid-cohort would violate freeze discipline) and their re-derivation
  is pre-registered for the R5 milestone alongside the corridor expiry.
- The decomposition of the ruled "clamp 0.45 → 0.10" into
  {command clamp 0.10, measurement bound 0.45} is an implementation
  interpretation flagged for advisory ratification in RESPONSE13 §2:
  applying 0.10 to the measurement would make the admission corridor's
  position term unable to exceed 0.294 — admission could never refuse
  an off-corridor arrival by position, which the safety fixture
  demonstrates. The ruling's intent (nothing may command a crossing
  outside the no-touch band) is enforced at the command site.
