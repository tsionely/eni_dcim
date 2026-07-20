# Evidence-state × action legality (advisory-11 §0 — the constitutional table)

Every handler of an irreversible verb diffs against this table before
shipping. The cohort-2 wipeout happened because a handler enumerated
legal actions for *fresh* and left *stale/blind* unenumerated — the
table makes the enumeration mandatory.

Evidence states: **FRESH** = believed corroborated by vision within
`entry_max_age_s` (0.6s). **STALE** = believed present but older.
**BLIND** = no believed (expired / never acquired).

| action \ evidence | FRESH | STALE | BLIND |
|---|---|---|---|
| continue commit vector | ✔ | ✘ (brake) | ✘ (brake) |
| brake-to-hover | ✔ (allowed anywhere) | ✔ THE stale/blind action | ✔ |
| retreat at speed | ✔ (evidence-backed: fresh crossing, corridor breach, timer w/ fresh believed) | ✘ (was the F1 killer) | ✘ |
| slow retrace (inbound tangent) | — (not needed) | ✔ after blind-hold timeout (4.5s) | ✔ after blind-hold timeout |
| terminate attempt (geometric) | ✔ (fresh crossing only) | ✘ (phantom class) | ✘ |
| relock / accept new target | ✔ via acquisition-path semantics (estimator relock, reacquire guard) | ✘ (no commit/align entry on stale) | ✔ from standstill search only |
| enter commit/align | ✔ (entry freshness gate) | ✘ | ✘ |
| terminal capture (TERM) | ✔ (certified + ready + admission) | ✘ (arbiter feature_age ≤ 0.10) | ✘ |
| aborts / corridor breach counting | ✔ (fresh-vision breaches only) | ✘ | ✘ |

Consequences already encoded: the blindness budget in commit
(stale/blind ⇒ brake), the timer-expiry split (stale ⇒ brake, fresh ⇒
retreat), the blind-hover timeout (4.5s ⇒ slow retrace along the
inbound tangent, yaw-accum-compensated), the entry freshness gate, the
fresh-only geometric termination and corridor breaches, the TERM
capture predicate.

THE RULE (verbatim, advisory 8/S4): uncertainty while moving reduces
speed and eventually forces a stop; it never expands the set of
actions allowed to take control.
