# CRITERION REGISTRATION — Second-mechanism (unmodeled legacy actuation) adjudication thresholds

Registered BEFORE the prediction table or intervention run exists
(channel-1 ruling A, rider R1: thresholds derive from REGISTERED
CONSTANTS, never from the observed distribution, never from the
advisory channel). The prediction-table and intervention artifacts'
generator commits must carry this commit as an ancestor.

## Derivation rules (each threshold cites its registered constant)

- **NEAR-ZERO legacy vertical activity**: RMS(recorded applied
  vertical in the withheld window) < **0.05 m/s** — the program's
  registered indistinguishable-from-zero rate constant (the
  transition rate-sign deadband, RESPONSE-19 era; also the oracle
  jump floor). Not derived from any observed activity distribution.
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
  evaluation feeding the RECORDED legacy plant-applied vertical
  stream into the feed-forward. CONFIRMED if per-cluster |b1| mass
  collapses under the intervention — specifically: the count of
  clusters with |b1| > 0.35 falls by at least half AND every
  near-zero-activity cluster sits below 0.35 after intervention.
  SURVIVES-INTERVENTION => REFUTED regardless of the correlation
  table. The POST-INTERVENTION residual is the admissible drift
  measurement for any subsequent fit.
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

- **PLANT SIGNAL**: the exact logged APPLIED vertical command /
  plant input stream (per-era field named in the artifact) — never
  an arbiter selection or desired target. **(Amendment after the
  first intervention run, BEFORE any rerun: the run fed
  `rate_feed_forward_mps` — an internal feed-forward column of
  precisely the prohibited class — and its stream failed physical
  plausibility in BOTH signs. The plant signal is the LOGGED
  SETPOINT VERTICAL, setpoint.v_body[2], converted to world-up by
  the adapter's own equation v_up = -v_bz * cos(level_pitch) *
  cos(level_roll), with the conversion derived in writing in the
  artifact — TYPED per the STREAM CONTRACT below as a COMMANDED
  VELOCITY REFERENCE (Contract B), resolving the wording that
  simultaneously prohibited "desired targets" and selected a
  setpoint: the prohibition targets INTERNAL/arbiter fields; the
  logged innermost command enters only through the declared
  response model, never raw subtraction.)**
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
of freedom — the A114 classification rode one). Cluster
aggregation publishes BOTH the any-cut count (with cuts-per-
approach disclosed, since more cuts mean more threshold chances)
and a support-weighted proportion; neither is adjudicative alone.
The committed all-approach baseline is **5/23** (3/20 confirmatory,
2/3 discovery-overlap); the 4/22 figure survives only as a LABELED
post-hoc sensitivity (zero-stream approach excluded — an exclusion
no registered rule authorizes, kept as the sensitivity it is).

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
  missing-reference term (the integrated applied vertical the
  feed-forward never saw); **SECONDARY**: RMS / integrated absolute
  activity.
- **UNITS**: cut-level observations; physical approach = outer
  cluster for every bound and bootstrap.
- **NEGATIVE CONTROLS**: true zero-command windows; near-hover
  windows per the committed 0.05 constant; unrelated horizontal
  channels where appropriate.
- **PRIMARY FALSIFICATION**: near-zero applied legacy activity with
  persistent large WITHIN-CUT slope refutes (the branch above).
- **COUNTERFACTUAL ENDPOINT**: recompute the residual with the
  causal applied reference included; publish whether within-cut
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

## Guard line (channel-1, binding): the intervention is evaluation-side FOREVER

The intervention modifies the EVALUATION HARNESS only. No branch of
mechanism-2 — confirmed, refuted, or contributory — authorizes any
flight-code change: the zero/None ring purity is a FEATURE (the
same law that makes the flight code right is the law that makes the
archive evaluation under-modeled), and the "fix" belongs to the
evaluation side permanently.

## Rider R4 — the A091 sentinel

The one physical TERM episode publishes its full row (auth_at_latch,
delta_latch, b0_old, b0_new, b1, recorded TERM activity). Committed
reading rule: if auth ~ 1 and b0_new ~ b0_old ~ -0.44, the founding
-0.437 is RE-ATTRIBUTED away from latch attenuation and the
consistency anchor becomes a discriminant between mechanisms.
(FIRED in the 55ba6da round: auth = 1.0, b0 identical at -0.4449 —
the re-attribution stands recorded in RESPONSE-58.)

**Mechanism-2's own A091 prediction (channel-1, committed before
the valid-stream run):** on A091 the rings were POPULATED — TERM
was the actor, the feed-forward was not empty — so mechanism-2
predicts its within-cut b1 is SMALL and INTERVENTION-INDIFFERENT.
If that holds while its -0.44 intercept persists, the founding
number belongs to a THIRD structure, and A091 is the first cell
where the post-two-mechanisms residual shows its face.
