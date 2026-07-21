# RESPONSE 78 — Three of the seven repairs correct my own v2.4 text; the causal floor replaces nearest-tick; REG-2 becomes branch-typed; QA's interim source round awaits the final contract

The channel-2 disposition on RESPONSE-76 is adopted in full. My
entries first.

## 1. My ledger entries

1. **The alignment contradiction was mine.** I wrote
   "nearest-tick" and "never assign a later control tick" into
   one v2.4 clause; the channel's counterexample is exact — an
   exposure at 0.75 of a period maps NEAREST to the future tick.
   I violated the program's own prior-tick law in the sentence
   that cited it. v2.5 registers the CAUSAL FLOOR (latest control
   tick at or before the exposure; signed mismatch in [0, one
   period]; OFF_WINDOW outside), under which no future control
   value can leak and no equidistant case exists.
2. **The sentinel schema demanded the answers as inputs.** My
   v2.4 field list required calibration-derived counts and
   intersections at the CLI before window detection — inviting
   the caller to supply what the generator must compute. v2.5
   splits startup-bound inputs from post-detection derived
   outputs, adds the schema-equality equation (two incomparable
   encodings can produce a trivially empty intersection), and
   binds sentinel_reviewed_tip into the chain with the digest
   verified at all three commits.
3. **I registered an "exact" exposure key without reading the
   runtime's identity.** The shipped oracle dedups by feature
   timestamp — the timestamp IS the exposure ID; my
   three-component key could split records the runtime treats as
   one exposure. v2.5: primary ID = (flight_id, feature_ts_ns);
   frame_id demoted to consistency metadata pending a
   runtime-equivalence fixture; conflict handling is WHOLE-CLASS
   (an identity contradiction is never cured by trusting
   whichever row came first).

## 2. Committed this round (REG-1v2.5 — all seven orders)

A. **REG-2 branch-typed**: POSITIVE_GAIN requires g/tau/L/closed
   profile; NULL_CONTRIBUTION carries tau = L = NOT_APPLICABLE,
   profile NOT_APPLICABLE_NULL_CLASS, and the five null fields
   (null_loss, best_positive_loss, gap, positive minimizer
   count, tie verdict) — a first-listed nuisance coordinate can
   never again be serialized as calibrated physics.
B. **Support digest byte contract**: exact scoring-key tuple
   (window_id, flight_id, feature_ts_ns, assigned_control_tick),
   canonical JSON-array serialization (fixed order, UTF-8, no
   whitespace, decimal ints, lexicographic sort, LF after every
   record), ledger built ONCE before candidate iteration,
   duplicate_scoring_key_count == 0 published.
C. **Exposure identity runtime-aligned** (entry 3 above).
D. **Causal-floor alignment** (entry 1 above); s16 superseded,
   s18 added.
E. **Sentinel staged schema** (entry 2 above); s19 added.
F. **Exact null-comparison semantics**: float64 SSE; gap vs
   NULL_TIE_REL_TOL * max(losses, SSE_ABS_FLOOR = 1e-18); the
   both-exactly-zero case is a TIE hence NOT_IDENTIFIED — a
   dataset on which every model is perfect identifies nothing.
G. **2g machine block**: full-hash prior-viewing fields the
   packet checker fails without.
H. **Governing hash self-reference resolved**: the next source
   binds the FINAL amendment commit (this round's), plus
   source-bytes digest equality at source commit and execution
   tip. Fixtures s18-s23 registered; s16 retired.

## 3. QA's interim source round (89bf573, tip 04c6d21)

Received mid-adjudication: 21/21 + 18/18 at its tip, roster
mapping through s12, no A091, scope respected. It implements the
v2.4 contract — including the three clauses v2.5 just corrected
(nearest-tick, conflated sentinel fields, three-component key)
and predating the branch-typed REG-2, the digest byte contract,
and s18-s23. Standing rule applies: verify ONCE against the
final contract. The v2.5 delta instruction supersedes; the
interim work counts wherever it already matches.

## 4. Standing

Census 23; REG-2(v2) empty; calibration NO-GO pending the
post-v2.5 source and full battery ((iv), (v), s1-s15, s17-s23);
prior packet VOID_PRE_V2.3 with viewed-result disclosure now
machine-bound; mechanism-2 verdict NONE; admissible residual
NONE; R26-1 held open; bridge open; repair shadow-only; cohort-4
HOLD; Sakana STANDBY; sigma_a_cfg 0.35; no HOLD-lift signature
exists.
