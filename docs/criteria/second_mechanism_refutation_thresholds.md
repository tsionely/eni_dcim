# CRITERION REGISTRATION — Second-mechanism (unmodeled legacy actuation) adjudication thresholds

Registered BEFORE the prediction table or intervention run exists
(channel-1 ruling A, rider R1: thresholds derive from REGISTERED
CONSTANTS, never from the observed distribution, never from the
advisory channel). The prediction-table and intervention artifacts'
generator commits must carry this commit as an ancestor.

## Derivation rules (each threshold cites its registered constant)

- **NEAR-ZERO legacy vertical activity**: RMS of the
  MODEL-PREDICTED LEGACY CONTRIBUTION (Contract B dynamic
  transform) in the withheld window < **0.05 m/s** — the program's
  registered indistinguishable-from-zero rate constant (the
  transition rate-sign deadband, RESPONSE-19 era; also the oracle
  jump floor). Not derived from any observed activity distribution.
  **(Q-TYPE, channel-2 on R60-63: the quantity that defines Q is
  the model-predicted contribution — the physically missing term
  the falsification claim is about; the raw-reference RMS is
  published alongside as a DESCRIPTOR, never the Q gate.)**
- **LARGE |b1|**: |b1| > **0.35 m/s^2** — the release gate constant
  itself. b1 carries sigma_a's units; a deterministic slope
  exceeding the ENTIRE stochastic release budget is "large" by the
  gate's own definition, no new number invented.
- **K (refutation count)**: **2** independent approaches — the
  program's registered consecutive-breach falsification convention
  (the anchor falsification monitor's k = 2).

## Cut-aware amendment (channel-2 §4-§5, pre-evidence)

All slope quantities in this criterion are **WITHIN-CUT slopes**,
never pooled per-approach b1 — the pooled slope mixes within-cut
age evolution with between-cut intercept/age covariance and is NOT
identified as drift (demonstrated: A071 pooled -0.65/-1.20 vs
within-cut +0.25; A074 pooled +1.70 vs within-cut -0.43). The
observation unit is the CUT (approach_id, cut_id, auth_at_latch,
v_latch, within-cut b0/b1, age support, rows); the physical
approach remains the OUTER independent cluster for all uncertainty;
no median may erase low-authority cuts (A071's median auth 1.0 hid
two cuts at 0.23/0.47 with v_latch ~ -3 m/s).

## The committed branches

- **REFUTED** if >= 2 approaches contain cuts with auth_at_latch
  >= 0.999 AND near-zero legacy activity (RMS < 0.05) AND
  |within-cut b1| > 0.35. (Real drift in quiet windows the
  mechanism cannot explain.) Consequence, pre-registered by the
  channel and adopted: 0.35 itself becomes a CONTESTED CONSTANT and
  the validated-age machinery re-derives before any release walk.
- **CORRELATION IS A FILTER ONLY (rider R2)**: the |b1|-vs-activity
  table is in-sample by construction (the hypothesis was born from
  these b1 values). It can kill the mechanism (refutation branch
  above) but can never confirm it.
- **THE INTERVENTION IS THE JUDGE (rider R2)**: rerun the residual
  evaluation with the MODEL-PREDICTED CAUSAL LEGACY CONTRIBUTION
  included (per the SIGNAL CHAIN below — the only normative signal
  instruction in this file). The reading is the machine decision
  table:
  **MACHINE DECISION TABLE v2 (channel-2 on R60-63 — SET-BASED,
  replacing the net-count table, whose D = B - A could hide an
  intervention that created new large approaches behind a resolved
  one). Evaluated STRICTLY TOP-DOWN; the first matching branch
  wins, making the branches mutually exclusive and exhaustive by
  construction. Define, over physical approaches under the
  committed approach classifier (estimability section):**

      S_B = approaches classified large BEFORE intervention
            (estimable cuts only);  B = |S_B|
      S_A = approaches classified large AFTER intervention
            (estimable cuts only, common support)
      R   = |S_B \ S_A|   resolved baseline-large approaches
      S   = |S_B intersect S_A|   surviving baseline-large approaches
      N   = |S_A \ S_B|   NEWLY large approaches

  **COMMON SUPPORT IS CUT-PAIRED (channel-2 on R64 §2 — the
  approach-level M had two holes: a baseline-large cut with a
  missing after-estimate could masquerade as a resolved approach
  behind a surviving small cut, and missing after-support on a
  baseline-SMALL approach could hide newly introduced harm).
  Define, per approach j, with the PAIRED CUT KEY
  (approach_id, cut_id, registered age/event support key):**

      C_B(j) = estimable before-intervention cuts of j
      C_A(j) = estimable after-intervention cuts of j
      C_P(j) = cuts of j with valid PAIRED before-and-after support

      M_RESOLUTION = count of baseline-large CUTS (each cut whose
            |b1| > 0.35 made its approach large) lacking a valid
            paired after-estimate — an approach may leave S_A ONLY
            through paired evidence on the cuts that put it there
      M_HARM = count of before-evaluable approaches (large or
            small) lacking enough paired after-support to
            determine newly-large status — absence of after-data
            is never proof of no new harm

  Zero-valued command references are evaluable and NEVER enter
  either count; only absence/invalidity does. EVERY support loss
  carries a typed exit reason (ABSENT_INPUT, BURN_IN, CLIPPED,
  OWNERSHIP_SPLIT, AGE_LOSS, ESTIMABILITY_FAIL) — listed per cut,
  never silent. A labeled conservative rerun mode may instead
  score every missing baseline-large cut as STILL LARGE; missing
  baseline-small support has no such conversion — nothing proves
  absent harm except paired data.

      Q   = independent near-zero-activity approaches retaining an
            estimable large WITHIN-CUT slope after intervention
            (activity per the Q-TYPE rule above)
      K   = 2

      1. input validity fails -> INVALID_INPUT
      2. B = 0                -> NO_REGISTERED_REMAINDER_TO_EXPLAIN
                                 (NOT_APPLICABLE; never confirmation)
      3. M_RESOLUTION > 0
         or M_HARM > 0        -> HOLD_INCOMPLETE_INTERVENTION_SUPPORT
      4. N > 0                -> REFUTED_OR_HARMFUL_INTERVENTION
      5. Q >= K               -> REFUTED
      6. 0 < Q < K            -> HOLD_INCONCLUSIVE_QUIET_BREACH
      7. R >= ceil(B/2)       -> CONFIRMED_SUFFICIENT_FOR_EVALUATOR
      8. 0 < R < ceil(B/2)    -> CONTRIBUTORY_NOT_SUFFICIENT
      9. R = 0                -> REFUTED_AS_REGISTERED_REMAINDER_EXPLANATION

  (Branches 3-4 clear M_RESOLUTION = M_HARM = 0 and N = 0 before
  any counting branch, so by branch 7 the net difference equals R
  and cannot hide a transition — and every resolution is PAIRED
  evidence on the cuts that made the approach large. B = 0
  short-circuits at branch 2 — with no registered remainder to
  explain there is no target, hence NOT_APPLICABLE, never
  CONFIRMED. The last label rejects mechanism-2 as the registered
  remainder explanation without claiming the physical effect is
  nonexistent in every regime. S and N are published per approach
  ID, not only as counts.)
  **MACHINE FIXTURE REQUIREMENTS (binding — the exhaustiveness
  claim is HELD until these are committed and green; a table is
  machine-exhaustive when its edge cases have been RUN):** the
  generator's fixture suite must contain, minimum: (a) missing
  baseline-large cut with another surviving small cut in the same
  approach -> HOLD, never resolved; (b) missing after-support on a
  baseline-SMALL approach -> HOLD via M_HARM; (c) a newly large
  approach -> branch 4; (d) B = 0 -> branch 2; (e) one quiet
  breach and (f) two quiet breaches -> branches 6 and 5; (g)
  explicit-zero input vs absent input distinguished; (h) A091
  byte-identical no-op; (i) mixed-owner split; (j) every
  residual-admissibility branch emitted; (k) a Theil-Sen/OLS
  boundary disagreement flagged; and (l) the PRECEDENCE FIXTURE
  (channel-1): one synthetic input satisfying TWO branch
  predicates simultaneously must land in the EARLIER branch, and
  the fixture asserts the landing — "by construction" is a claim
  about the evaluator, provable in one executed edge case; and
  (m) the RUNTIME-TWIN EQUIVALENCE fixture (channel-1 on R66,
  provenance-ratification condition): one synthetic e_meas series
  driven through BOTH code paths — the runtime rate_anchor_v_raw
  path and the calibration reconstruction — equality asserted by
  execution, because no overlapping archive support exists to
  prove the equivalence observationally.**
  **BOUNDARY-OPTIMUM VERDICT CONTINGENCY (channel-1 on R66,
  pre-committed BEFORE the intervention runs, so the restart
  cannot be chosen after seeing which verdict appeared): a
  truncated response model under-subtracts, which blurs both
  non-confirmation directions — CONTRIBUTORY becomes ambiguous
  (partial mechanism, or truncated model?) and a REFUTED-family
  outcome can be MANUFACTURED (slope survival from under-removal,
  not physics). Therefore, while the BOUNDARY_OPTIMUM flag rides:
  any outcome in the mechanism-adjudicating branches other than
  CONFIRMED_SUFFICIENT_FOR_EVALUATOR — that is, REFUTED,
  HOLD_INCONCLUSIVE_QUIET_BREACH, CONTRIBUTORY_NOT_SUFFICIENT,
  REFUTED_AS_REGISTERED_REMAINDER_EXPLANATION, and
  REFUTED_OR_HARMFUL_INTERVENTION — is INTERIM, not final: the
  ONE-TIME lawful registration restart (grid extension via the
  Section-2 void clause; rationale independent of the 23 already
  exists — the calibration's own truncated faces) executes, and
  the intervention reruns under the extended registration before
  any verdict becomes final. The process branches INVALID_INPUT,
  NO_REGISTERED_REMAINDER_TO_EXPLAIN, and
  HOLD_INCOMPLETE_INTERVENTION_SUPPORT keep their own repairs and
  do not consume the restart. CONFIRMED stands A FORTIORI:
  confirmation under a limited model — with N > 0 firing earlier
  in the top-down order and the sign/frame negative controls
  guarding — is the stronger evidence, not the weaker. The
  artifact carries this as a typed column (verdict_finality:
  FINAL / INTERIM_PENDING_RESTART), never a footnote.**
  **RESIDUAL ADMISSIBILITY, TYPED FOR EVERY BRANCH (supersedes the
  earlier blanket sentence AND the earlier partial typing):**
  INVALID_INPUT -> residual INADMISSIBLE, no verdict;
  NO_REGISTERED_REMAINDER_TO_EXPLAIN -> no residual claim of any
  type is generated;
  HOLD_INCOMPLETE_INTERVENTION_SUPPORT -> residual INADMISSIBLE,
  no verdict until support is repaired or the missing approaches
  are conservatively scored as still-large in a rerun;
  REFUTED_OR_HARMFUL_INTERVENTION -> residual INADMISSIBLE;
  REFUTED -> residual INADMISSIBLE as a mechanism-corrected drift
  measurement;
  HOLD_INCONCLUSIVE_QUIET_BREACH -> residual DIAGNOSTIC_ONLY — no
  release fit, no gate conclusion; additional mechanism naming or
  replication required before any further use;
  CONTRIBUTORY_NOT_SUFFICIENT -> residual DIAGNOSTIC_ONLY (next
  naming round's input; never a release fit or gate conclusion);
  CONFIRMED_SUFFICIENT_FOR_EVALUATOR -> residual becomes a
  CANDIDATE evaluator-corrected statistical input — still not
  flight-release evidence, still behind the bridge and the
  repaired-shipping-build re-earn.
  **THE MIDDLE CELL (channel-1 amendment, committed before any
  valid-stream run): PARTIAL COLLAPSE — some clusters drop,
  near-zero clusters end compliant, but fewer than half of the
  >0.35 clusters fall — is dispositioned
  CONTRIBUTORY-NOT-SUFFICIENT: the post-intervention residuals
  become the next naming round's INPUT, no gate conclusion is drawn
  from a partial result, and refutation retains its own K=2
  condition (partial is never refutation). All under the standing
  DO-NOT-MOVE default.**

## Rider R3 — the live-twin declaration (code-side, declared here)

What the runtime records, from the shipped wiring: the oracle's
achieved ring (note_applied) records the TERM CHANNEL-APPLIED
world-up command (post-slew, achieved, prior-tick), only on
SIDE-active TERM ticks, never a synthetic zero; planner
track_applied_vz records the TERM-applied body command only while
TERM owns. LEGACY-tick verticals are recorded in flight logs
(setpoint stream) but are NOT fed to any feed-forward ring — by the
zero/None law, absence is absence. Therefore in archive replays of
never-TERM flights the runtime-model feed-forward is EMPTY and the
entire legacy actuation is unmodeled BY CONSTRUCTION — the
mechanism, if confirmed, is evaluation-side, not a flight-code
defect. The HARNESS must declare which stream its evaluation fed as
"applied" (its own disclosure, part of the adjudicative round);
mixed-ownership windows are analyzed per rider R3.

## Full specification fields (channel-2 §6, committed before the activity table or counterfactual exists)

- **SIGNAL CHAIN (channel-2 on R60-63 — the ONE normative signal
  instruction. Every earlier "plant-applied stream", "APPLIED
  vertical command / plant input", or feed-the-feed-forward wording
  anywhere in this file is VOID and superseded by this block; a
  generator following any other signal sentence fails ancestry in
  substance):**

      RAW LOG FIELD:         setpoint.v_body[2]
      TYPE:                  COMMANDED VELOCITY REFERENCE
                             (not achieved motion, not plant input)
      FRAME TRANSFORM:       v_up = -v_bz * cos(level_pitch)
                                          * cos(level_roll)
                             (derived in writing in the artifact)
      DYNAMIC TRANSFORM:     the pre-registered closed-loop
                             response model —
                             docs/criteria/legacy_response_model_registration.md,
                             which must be numerically COMPLETE
                             (REG-2) before the generator commit
      INTERVENTION QUANTITY: model-predicted causal legacy
                             contribution
      PROHIBITED:            raw subtraction; internal feed-forward
                             fields (the rate_feed_forward_mps
                             class); arbiter-selection fields;
                             treating the setpoint as achieved
                             motion

  (History, non-normative: the first run fed
  `rate_feed_forward_mps` — an internal column of precisely the
  prohibited class — and its stream failed physical plausibility
  in both signs; VOID_INVALID_INPUT. The prohibition on "desired
  targets" targets INTERNAL/arbiter fields; the logged innermost
  command enters only through the declared response model.)
- **STREAM CONTRACT (channel-2 correction — the zero-lag
  positive-correlation gate is WITHDRAWN):** my earlier sign-only
  correlation pre-check repeated the exact error class this
  program had just adjudicated — a closed-loop command may
  legitimately anti-correlate with current motion (braking,
  overshoot arrest), so zero-lag corr > 0 is neither necessary nor
  sufficient. Replaced by the typed contract:
  **CONTRACT B — COMMANDED VELOCITY REFERENCE.**
  setpoint.v_body[2] is the innermost LOGGED command this
  architecture delivers to the velocity-tracking backend; it is a
  COMMANDED REFERENCE, not achieved motion, and is typed as such.
  The counterfactual residual therefore derives through a DECLARED
  closed-loop response model, not by raw subtraction. Validity
  requirements, all published BEFORE the judge:
  1. source provenance (producer, consumer, log field, control
     stage);
  2. frame/sign derivation in writing
     (v_up = -v_bz * cos(level_pitch) * cos(level_roll));
  3. causal timing (exposure/control alignment, registered
     prior-tick semantics, no future leakage);
  4. typed field semantics (commanded target / post-limiter /
     actuator input / achieved motion are DIFFERENT signals, named);
  5. LAG-AWARE response window: predeclared from the physical
     calibration source — the A091 down-step episode's measured
     command-to-response delay — never from whichever lag fits the
     23 discovery approaches; if uncalibratable, the registered
     prior-tick semantics apply with a published zero-lag
     sensitivity band, both shown;
  6. per-era field presence/missingness published before the
     intervention read;
  7. negative controls: true zero-command windows, unrelated
     channels, and a sign/frame-inversion fixture.
  **QUIET-CELL EXEMPTION (channel-1, retained under the new
  contract): clusters below the registered 0.05 RMS activity floor
  are exempt from the lag-aware response check — a near-zero
  stream has nothing to validate against, and these are precisely
  the mechanism's quiet prediction cells. Zero is
  intervention-evaluable; only absence is off support.**

## Slope-estimability rules (channel-2 §6 — committed before any adjudicative slope count)

A cut enters threshold counting only with: >= 4 unique ages (the
registered Theil-Sen minimum), age span >= 0.15 s (the registered
readiness span), and >= 4 rows. One- and two-row cuts are LISTED
and excluded from counts (a two-point line has no residual degrees
of freedom — the A114 classification rode one).

**SLOPE ESTIMATOR, FIXED (channel-2 on R60-63 — committed before
the rerun; the generator may not choose an estimator after seeing
which one produces a favorable branch):** the adjudicative
within-cut slope is **THEIL-SEN** — the median of pairwise slopes
over row pairs with DISTINCT ages (identical-age pairs are
excluded: slope undefined); an even pairwise count takes the mean
of the two middle values. The estimator is chosen because the
registered >= 4-unique-ages minimum was already named in its
terms, and channel-2's independent recomputation confirms the
APPROACH-LEVEL classification agrees across estimators on the
existing checkpoint — but the cut-level classifications are NOT
identical: one boundary disagreement exists
(20260720T062804-c38fd469:A1:cut04 — Theil-Sen b1 ~ -0.2303, OLS
b1 ~ -0.4916) and must be flagged, not narrated away; the 4/23
set is stable because another qualifying cut carries that
approach. Per-cut OLS is published alongside as a cross-estimator
stability DESCRIPTOR; every cut where the two estimators disagree
across the 0.35 boundary is FLAGGED in the artifact. Approach-level uncertainty continues to run through the
physical-approach outer cluster (bootstrap/LOAO), never per-cut.

**APPROACH CLASSIFIER, FIXED (channel-2 on R60-63 — the machine
table requires a binary large/not-large per approach; committed
here, before the rerun):**

    large_approach = at least one ESTIMABLE cut in the approach
                     has |b1_theil_sen| > 0.35

The support-weighted proportion is retained as a SECONDARY
stability/concentration descriptor with cuts-per-approach
disclosed (more cuts mean more threshold chances) — published
always, adjudicative never. This supersedes the earlier "neither
is adjudicative alone" sentence, which named two summaries and no
classifier: the any-cut rule is now the committed adjudicative
classifier; the weighted quantity remains its disclosed context.

**BASELINE TYPING (channel-2 on R60-63 — three numbers, three
types, never interchangeable):**

    5/23  HISTORICAL PRE-ESTIMABILITY MECHANICAL OUTPUT —
          provenance only; entered the record before the
          estimability rules existed. Never the machine table's B.
    4/23  channel-2's independent recomputation under THESE rules
          on the committed 1,638-row checkpoint (177 cuts, 149
          estimable; the fifth approach's only large slope rode a
          two-row cut). Denominator stays 23 — the zero-stream
          approach is NOT excluded. Status: PENDING
          POST-CRITERION ARTIFACT AUTHENTICATION.
    4/22  unauthorized zero-stream-excluded sensitivity — labeled,
          never a board number.

The machine variable B is derived FRESH from estimable cuts by the
post-criterion generator at run time; it may not be hard-coded,
and no narrative may state it as five.

## Component-to-runtime mapping (channel-1 central ruling — committed BEFORE any A/B/C/D read)

Before decomposition numbers are read, the mapping of components to
runtime terms is FIXED, in both directions:

- **WITHIN-CUT drift over an anchor's life** (fit B's residual
  slope family) is the runtime's actual exposure — it and ONLY it
  scores against the 0.35 sigma_a gate.
- **BETWEEN-CUT intercept structure** (what fit B removes) maps to
  the ANCHOR/ZERO-AGE terms — the sigma_0 / latch-quality /
  admission machinery — because live operation re-anchors and
  resets it. It is PRICED THERE EXPLICITLY (pseudo-floor family),
  never dropped.
- Both error directions are barred by this pre-commitment: no
  laundering of between-cut structure INTO the gate
  (over-conservatism is also an error), and no silent removal of a
  genuine within-cut component FROM it (under-conservatism). The
  mapping cannot be chosen after seeing which mapping passes.

## Cut-table hypothesis (flagged pre-table, channel-1)

To be answered by the cut-level table, not assumed: are the cuts
the unattenuated repair WORSENED (A071-class, b0_shadow +0.86)
precisely the low-auth / large-|v_latch| cuts? If yes, the
authority schedule was wrongly SUPPRESSING bad latched slopes, and
the repair's refinement direction is a LATCH-QUALITY ADMISSION
(latch or refuse; never attenuate) — the per-channel-trust
doctrine completing itself. Hypothesis status until the table
speaks.
- **COMMAND SEMANTICS**: 0.0 is observed zero activity; None/absent
  is missing input; no truthiness filter may merge them.
- **TIMING**: exact withheld-window boundaries; prior-tick and
  exposure alignment; no future-command leakage.
- **PRIMARY PREDICTOR**: a SIGNED, physically derived
  missing-contribution term (the integrated MODEL-PREDICTED legacy
  contribution the feed-forward never saw — Contract B chain);
  **SECONDARY**: RMS / integrated absolute model-predicted
  contribution, with raw-reference RMS as descriptor.
- **UNITS**: cut-level observations; physical approach = outer
  cluster for every bound and bootstrap.
- **NEGATIVE CONTROLS**: true zero-command windows; near-hover
  windows per the committed 0.05 constant; unrelated horizontal
  channels where appropriate.
- **PRIMARY FALSIFICATION**: near-zero MODEL-PREDICTED legacy
  contribution with persistent large WITHIN-CUT slope refutes (the
  branch above).
- **COUNTERFACTUAL ENDPOINT**: recompute the residual with the
  model-predicted causal legacy contribution included (Contract B
  chain, registered response model); publish whether within-cut
  slopes and the conservative U95 collapse. The counterfactual is
  FRESH EVIDENCE GENERATION — post-criterion generator mandatory
  even with no simulator rerun.
- **DISCOVERY DISCLOSURE**: all slope/intercept values already
  viewed before this registration are listed in the artifact; the
  23 approaches are DISCOVERY DATA for this mechanism — a same-data
  result guides engineering, and can NEVER by itself validate a
  shipping repair (the bridge and the repaired-shipping-build
  re-earn remain mandatory regardless of outcome).
- **NESTED DRIVER DECOMPOSITION** (pre-registered attribution
  instrument): fits A (raw shadow residual), B (cut-intercept-
  adjusted), C (slope/activity-adjusted), D (both) — each with
  point sigma_a, profile U95, approach-bootstrap U95, LOAO, and
  cross-fitted mean adjustment (never fit-and-evaluate on the same
  rows). Driver attribution is read from this decomposition, never
  from visual association.

## MECHANISM-2 AUTHORITY BOUNDARY (channel-2 on R60-63 — supersedes the "evaluation-side FOREVER" heading and paragraph)

The intervention modifies the EVALUATION HARNESS only. Mechanism-2
evidence does not authorize a flight-code change. A different,
independently named mechanism (e.g., the separately filed
latch-quality-admission hypothesis) may do so only through its own
criterion, its own evidence, both-channel approval, and full
shipping-build revalidation. The zero/None ring purity remains a
FEATURE: the same law that makes the flight code right is the law
that makes the archive evaluation under-modeled — but "forever" is
not this criterion's to rule; authority boundaries are per
mechanism, per evidence path.

## Rider R4 — the A091 sentinel

The one physical TERM episode publishes its full row (auth_at_latch,
delta_latch, b0_old, b0_new, b1, recorded TERM activity). Committed
reading rule: if auth ~ 1 and b0_new ~ b0_old ~ -0.44, the founding
-0.437 is RE-ATTRIBUTED away from latch attenuation and the
consistency anchor becomes a discriminant between mechanisms.
(FIRED in the 55ba6da round: auth = 1.0, b0 identical at -0.4449 —
the re-attribution stands recorded in RESPONSE-58.)

**Mechanism-2's A091 prediction — REFORMULATED (channel-2 on R59;
the "small b1" clause is DELETED: it was undefined, written after
the baseline slopes were viewed, and contradicted by A091's own
cut table, whose pre-intervention within-cut slopes -0.99/-1.31/
-1.50/-0.84 all exceed 0.35). The registered prediction is a
STRUCTURAL NO-OP, ownership-gated:** on A091's TERM-owned support
the mechanism-2 correction term == 0.0 EXACTLY, before-residual
rows == after-residual rows, and every fitted quantity is
unchanged. The harness MUST ownership-gate the intervention — a
legacy setpoint that remains logged while TERM owns may not be
injected as though legacy control physically acted; mixed-owner
intervals split before the sentinel is read. A NONZERO correction
on genuinely TERM-owned support indicates harness contamination or
ownership misclassification, never mechanism confirmation. A091's
absolute post-intervention b1 is DESCRIPTIVE evidence about
whatever remains after mechanisms 1 and 2 — never a mechanism-2
pass condition. If the no-op is confirmed and the -0.44-class
intercept persists, the classification is
UNATTRIBUTED_POST_M1_M2_SIGNED_STRUCTURE — a residual class, not
yet a physical mechanism; and if A091's large within-cut slopes
persist too, the third structure may be AGE-DEPENDENT, not
intercept-only.

**Row-level proof (channel-2 on R60-63, binding):** the sentinel
artifact proves the no-op at ROW level, never by rounded fit
equality alone. It publishes: exact command-event/row keys; owner
state per row; the correction term per row (exactly 0.0 on
TERM-owned rows); before/after residual equality per row; slice
SHA-256 before and after; and every mixed-owner exclusion listed
with its reason. The A091 CALIBRATION interval (which feeds the
response-model registration) and the SENTINEL interval are
identified separately and may not be the same rows wearing two
hats.

**Guard-scope wording (channel-2, binding):** no outcome of the
mechanism-2 intervention, BY ITSELF, authorizes a flight-code
change; any flight-code change requires an independently named
mechanism, criterion-before-evidence ancestry, and full
shipping-build revalidation. (The separately filed latch-quality-
admission hypothesis keeps its own path under exactly those
terms.)
