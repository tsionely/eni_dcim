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
  an arbiter selection or desired target.
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

## Rider R4 — the A091 sentinel

The one physical TERM episode publishes its full row (auth_at_latch,
delta_latch, b0_old, b0_new, b1, recorded TERM activity). Committed
reading rule: if auth ~ 1 and b0_new ~ b0_old ~ -0.44, the founding
-0.437 is RE-ATTRIBUTED away from latch attenuation and the
consistency anchor becomes a discriminant between mechanisms.
