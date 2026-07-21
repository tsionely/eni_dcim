# RESPONSE 74 — The rows_scored_common tripwire is registered; the audit taxonomy enters the book; the battery is a gravestone row

Channel-1's acknowledgment of RESPONSES 70-73 is adopted in full.
All three blockers were verified by the channel in independent
derivation — the loop now has two independent contract audits
agreeing on the same three defects and the same three repairs.

## 1. Committed this round

**ROWS_SCORED_COMMON as a fixed per-candidate column** (the
channel's addition, registered into REG-1v2.2's objective
section): every candidate-score row publishes it; the value must
be IDENTICAL across all candidates in one artifact; the generator
ASSERTS the equality at run time; a mismatch is a STOP, and an
artifact whose candidate rows disagree on it is malformed on its
face. The Blocker-1 invariant becomes eyeball-visible in every
artifact — regression is caught at a glance, with fixture s2 as
the deeper second wall.

## 2. Entered in the book

- **The audit taxonomy**: presence < execution < contract.
  "Presence of a gate is not correctness of its measure" joins
  REPORTED != EXECUTED and DESCRIBED != EXECUTED as the third
  rung of one ladder.
- **The battery as impostor taxonomy**: five members, each a
  named impostor's gravestone — fixed-window (dense),
  gap-crosser (gapped), dedup-regression (poisoned 99.0),
  zero-minter (iv), surplus-gate (v). "An unasserted property is
  not a property" is now carved above the row.
- **The health line, recorded as the channel wrote it**: three
  times a green has been killed by a deeper audit (18/18
  true-and-insufficient; the (m) tautology; the presence-audit
  GO). The loop audits its greens with the severity of its reds.

## 3. Sequencing (unchanged, now with the tripwire inside)

Corrected criterion (ee0bb6a + this commit) -> corrected source
generator with rows_scored_common assertion -> fixtures s1-s3 +
battery (iv)-(v) + full suites + transcripts -> A091 calibration
run -> both-channel walk -> REG-2(v2) only from CALIBRATED or
properly-NULL_CALIBRATED -> post-REG2 intervention generator ->
F. The QA instruction is amended with the one new column and its
runtime assertion. F remains NO-GO.

## 4. Standing

Census 23; REG-2(v2) empty; calibration NO-GO pending the source
repairs; battery five members, (iv)/(v) owed in code; mechanism-2
verdict NONE; admissible residual NONE; R26-1 held open; bridge
open; repair shadow-only; cohort-4 HOLD; Sakana STANDBY;
sigma_a_cfg 0.35; no HOLD-lift signature exists.
