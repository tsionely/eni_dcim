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

## The committed branches

- **REFUTED** if >= 2 approaches with auth_at_latch >= 0.999 AND
  near-zero legacy activity (RMS < 0.05) AND |b1| > 0.35. (Real
  drift in quiet windows the mechanism cannot explain.) Consequence,
  pre-registered by the channel and adopted: 0.35 itself becomes a
  CONTESTED CONSTANT and the validated-age machinery re-derives
  before any release walk.
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

## Rider R4 — the A091 sentinel

The one physical TERM episode publishes its full row (auth_at_latch,
delta_latch, b0_old, b0_new, b1, recorded TERM activity). Committed
reading rule: if auth ~ 1 and b0_new ~ b0_old ~ -0.44, the founding
-0.437 is RE-ATTRIBUTED away from latch attenuation and the
consistency anchor becomes a discriminant between mechanisms.
