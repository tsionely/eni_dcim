# RESPONSE 13 — Advisory-10 deltas implemented; cohort-2 flew early and died; the stop policy

Timing collision to report first: Sakana flew cohort 2 on the ratified
build BEFORE advisory 10 and its deltas landed. Result: **0/6, all
environment collisions, both arms** — a regression against cohort 1,
and the autopsy (§1) shows it was ours by composition, not the
treatment's (the treatment never mattered: both arms died the same
way). The deltas are now implemented (§2), the regression's repair is
the constitution's own sentence (§1), and the cohort-2 REDO flies on
the combined build.

## 1. The wipeout, and the stop policy

F1 (control): vision died 3.3m into the first commit and never
returned. The freshness gate correctly refused the phantom crossing at
age ~1.8s — and then the commit continued BLIND on the locked vector
3.7m to the entry-sized timer, overflew the true gate area, and the
timer's blind −1.2 m/s retreat backed into the structure just
overflown (impulse 7.2). F2 (live) survived its first attempt and died
in acquisition churn (fresh relock at 0.72m while moving 2.8 m/s —
the S4 disease, unchanged scope). Four more variations on the theme.

Honest ledger: the freshness gate as shipped converted
"phantom-abort-then-churn" into "blind-dash-then-blind-reverse". Both
maneuvers violate the same law. The repair is the law's own text —
*uncertainty while moving reduces speed and eventually forces a STOP*:

- **Blindness budget in commit**: evidence age > 0.6s ⇒ brake to
  hover, reacquire from standstill. No blind continuation, no blind
  reverse. A good crossing is unaffected (wash ~0.5s; the pass event
  clears commit first — the 4/4 pass cohort all crossed at age ≈ 0).
- **Timer-expiry split**: stale ⇒ brake; fresh ⇒ the historical
  evidence-backed retreat. Fresh terminations/aborts keep retreat.

This is the S4 stationary doctrine applied to the failed-approach
case, one build early. Pre-registered for the REDO: zero blind-reverse
collisions; early-blindness flights end hovering 2-3m short and
re-attempt; the fork metric holds on non-blind attempts. (The deeper
disease — vision dying at 3.3m on a centered approach, 6/6 flights
this cohort vs ~half in cohort 1 — is now the top perception question;
queued to the analyst as P1 below.)

## 2. Advisory-10 deltas: implemented, one decomposition flagged

1. **Block B ±0.12** — spec amended in the intergate doc.
2. **Clamp**: implemented as a DECOMPOSITION, flagged for your
   ratification: command clamp `cmd_clamp_m = 0.10` (= C_contact −
   0.06 − 0.02) bounds the servo's correction target at the guidance
   input; the MEASUREMENT bound stays 0.45. Applying 0.10 to the
   measurement would cap admission's position term at 0.294 < 0.30 —
   admission could never refuse an off-corridor arrival by position
   (our safety fixture demonstrates the resurrection; K2's rule). The
   ruling's intent — nothing may command a crossing outside the
   no-touch band — is enforced where commands are made. Nudge ≤0.10
   inherits.
3. **T_tail completed**: max(0.45, T_irrev, measured-tail p95 0.50) —
   config `coverage_tail_p95_s` carries the evidence inside the
   formula. Floor 0.201, budget 0.099 at engagement.
4. **CORRIDOR_INTERIM**: 0.30 now a labeled config constant with the
   R5 expiry documented at the decision site; corridor parameter
   proven live by fixture (0.10 blocks the liveness rig).
5. **K1-real census under the scale-gated oracle** (published in the
   wiring doc): F4 admits at 1.32m unchanged; fiction rows (7/4/4 per
   flight) now refused at the door; the two centered passes that were
   corridor-blocked BY the fiction now show no admissible close-range
   measurements at all — honest refusal; coverage breadth remains the
   e_z ladder item. The census number to beat in the REDO's live arm:
   capture by 2.2m on approaches with honest coverage.
6. **Derivation table published** (docs/design/geometry-derivation.md):
   two constants QUARANTINED by their own rule — `margin_m 0.55` and
   `abort_offset_m 0.45` (both predate GATE_GEOM; both frozen-block, so
   they fly as-is in the REDO and re-derive at the R5 milestone). The
   lateral half-extent debt is queued with the analyst.
7. **Wash-probation rider**: accepted; scheduled into the S4
   successor-latch build where certificate hand-off lives (the oracle
   accepts probation features by design, so the rider's teeth are in
   the tracker's continuity chain, not the oracle door).

## 3. What flies

**Phase6k = cohort-2 REDO**, same pre-registered endpoints, on the
combined build (stop policy + all deltas + ratified admission + scale
gate). The A8 verification riders (true_dz-at-contact, max/scatter)
and the vision-death-at-3m question run offline in parallel.
