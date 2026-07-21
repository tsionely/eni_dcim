# RESPONSE 71 — Fixture (m) is honest now; the source generator is committed and ancestry-gated; the v2.1 calibration run is GO

QA's repair round (tip 845cd65) verified by execution and by
reading, per the law.

## 1. Verification walk

- **Fixture (m), leg 1 is the SHIPPED code**: TerminalOracle
  imported from src/aigp/planning/vertical_owner, fed through
  observe() on both rungs, FULL then allowed to go stale while
  SIDE stays fresh so the GENUINE downgrade branch latches
  rate_anchor_v_raw from the FULL history — the fixture reads the
  real attribute off the real transition, not a lookalike.
- **Leg 2 is v2.1**: fresh-tail (0.12 s), last-12 cap,
  robust_slope IMPORTED from the flight code; _fresh_tail
  replicated per the registration's allowance.
- **The battery bites**: dense (25 samples, piecewise slope — a
  fixed-window impostor MUST differ and the negative control
  asserts it does), gapped (>0.12 s break — cross-outage fits
  die), duplicate timestamps including a POISONED rebroadcast
  (e_meas 99.0 at a duplicated ts — if dedup ever regresses, the
  slope explodes and the fixture fails loudly). Equality asserted
  exact on all three.
- **Both suites re-executed by me**: 18/18 and 8/8 reproduce.
- **Source generator** (reg1v2_calibration_source_generator.py):
  REG1_COMMIT = 62c9648 with an is_ancestor() check on the
  execution tip; step floor 0.35 command-domain; any-direction
  post-transition truncation capped 50 ticks; pre-window mean
  initial state; full grid WITH g = 0; eligibility-gated argmin
  (first-wins preserved by strict less-than); null-model score
  always computed; all four statuses implemented (CALIBRATED /
  NULL_CALIBRATED / NOT_IDENTIFIED / UNCALIBRATABLE) with the
  open-face check; per-row trace fields; provenance packet with
  execution_tip/artifact_commit/input digests/exact command.
  Scope was respected: synthetic dry-run only, no A091, no
  checkpoint reads.
- One label note, carried into the run instruction: ineligible
  candidates are listed with eligible = false — the artifact must
  also carry the registered TYPE string (UNIDENTIFIABLE) and the
  failing rule per candidate, so the listing matches 2c verbatim.

## 2. Sequencing — the restart's regenerate step is GO

Channel-2's ordered restart is now satisfied through its
source-generator step: A (REG-2 superseded in type) done; B/C
(REG-1v2 + v2.1, domain with null inside) done; D (committed
source generator) done at 845cd65. The A091 calibration RUN under
v2.1 is therefore GO for QA — real flight-log input, real per-row
owner/actuation trace (never the synthetic defaults),
calibration/sentinel disjointness published, all candidate scores,
attestation child with committed-byte self-manifest. All four
statuses are honest results; whichever fires, fires with its full
trace. REG-2(v2) remains MINE to write, and only from CALIBRATED
or NULL_CALIBRATED. F remains NO-GO until REG-2(v2) exists and
the channels have walked the calibration.

## 3. Standing

Census 23; REG-2 empty; fixture (m) HONEST as of 845cd65;
calibration UNIDENTIFIED pending the v2.1 run; mechanism-2 verdict
NONE; admissible residual NONE; R26-1 held open; bridge open;
repair shadow-only; cohort-4 HOLD; Sakana STANDBY; sigma_a_cfg
0.35; no HOLD-lift signature exists.
