# RESPONSE 23 — L1's greens, the chatter reclassified, the flag rulings implemented

Consolidates the L1/A-B round and both channels' flag rulings.
176/176; the paired-tail patch and the interim precautions are in the
build.

## 1. L1 on the real recordings — two gates GREEN, one starvation found

- **Liveness (F2): GREEN.** Readiness lights at 1.903m (14 rows below
  2m) — and `ready_legacy` = 0 in every one of them: the fresh-tail
  semantic is the difference, demonstrated on the recorded failure it
  was built for.
- **Accuracy (F2): GREEN.** Closest metric row 1.006m reads
  e_z = −0.145 against the contact-implied −0.162 — **1.7cm residual,
  correct sign**. The ladder sees the error the clips recorded.
- **The remaining dark zone**: sub-1m rows are all sparse-top
  row-only (shadow); `drop_full_below_2m` shows SIDE does not step up
  when full dies. Diagnosis: the detector covers 125/141 frames so
  the close tracker (SIDE's only producer) runs rarely; rung-2 is
  starved of production opportunities, not broken. F4 (the hard case)
  stays dark. Earned sigmas: n=2 overlap rows — NOT earned;
  measured inter-source bias −0.090 sits at the hard step limit and
  is itself the strongest argument for a per-rung d*-analog
  calibration before the rung matures.

## 2. The mock A/B — best terminal performance yet; the NO-GO dissolves

3/10 runs owned (201 rows, 196 applied), captures at 2.11-2.43m, e_z
at capture −0.003, zero wrong-sign. The "owner chatter" NO-GO
reclassifies on row inspection: run 02's four transitions are TWO
CLEAN ATTEMPTS (release at R=2.99/3.28 with engagement closed — the
attempt-end handback working); run 09's release at 1.19m is a fresh
corridor abort ending the attempt while TERM owned (legal,
pre-latch). **QA instrument patch requested: owner-transition
counting must segment by attempt epoch** — the "one statistic, two
truths" class, now in gatekeeping. The remaining honest gap to K1 is
mock believed-drift scale-rejects (8/10 runs) — a mock-domain
ceiling, noted with the point-mass asterisk.

## 3. Flag rulings — implemented

- **Paired-tail freshness (binding clarification): patched.** The
  switch now requires the maximal recent suffix of pairs with
  adjacent gap ≤ 0.12s and newest ≤ 0.12s — all three pairs current,
  stale overlap evidence cannot authorize a switch.
- **Upward command allowance = 0 (interim): implemented.** The
  terminal command clamp is now asymmetric [−0.10, 0]: no TERM
  command may drive the airframe's top toward a contested envelope;
  arresting a sink stays legal; the downward arm is the program's
  one evidence-backed clamp (0.10 ≤ 0.162 − 0.06). The old
  LOW-arrival-climbs fixture is superseded and re-pinned to the new
  law. Reverts only via the freeze-exception channel with forensics.
- **h_up ≤ 0.64 premise: revoked** as ruled; the 0.744 rows stand as
  an UNRESOLVED CONTRADICTION FIXTURE (A/B/C classification tasked);
  the non-contact ledger (every clean crossing = a one-sided bound;
  the first clean pass already caps h_up < 0.70) is adopted as a
  permanent spec and tasked to the analyst.
- **Block B: original RETIRED (underpowered); BLOCK_B2_TERM_AUTHORITY
  approved for re-registration** — TERM-owned eligibility decided
  before challenge assignment, {−0.12, 0} arms (downward-only per the
  interim), absolute scoring |crossing − center| ≤ 0.10, n ≥ 4 owned
  injected crossings, power from TERM-owned response variance.
  Registration doc follows with the cohort-4 report template.

## 4. Cohort-4 gate board

GREEN: S2/S3/S6 (unit), L1-liveness, L1-accuracy, paired-tail patch,
conservative door, probation-out, dual readiness, retro column (N=1).
OPEN: earned side sigmas (needs overlap volume — the per-rung
calibration question folds in), ψ-age fields + S4, full telemetry
set, certificate-boundary audit, S1, S5 (ran; SIDE never active —
re-read after the rung-production question), the 0.744 forensics +
non-contact ledger, brake-pitch columns. The ladder's cohort-4 value
under the conservative door is OWNERSHIP PERSISTENCE below 2m —
exactly where three cohorts died — and the maintenance path runs on
the active source's sigmas, which is why the earned row stays
critical-path.
