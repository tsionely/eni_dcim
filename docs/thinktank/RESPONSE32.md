# RESPONSE 32 — Convergent rulings folded in; the validated-age ceiling is now runtime law; P4 defined and read

Advisory-18 and the RESPONSE31 disposition arrived together and
converge everywhere they overlap. This note records adoption of
both, one wording correction accepted, one runtime build shipped in
response, and the P4 row — defined in one line as demanded, and
already read against landed numbers.

## 1. Adopted from both rulings (the union, stricter form kept)

1. **Outer cluster = physical approach/flight.** Forced cut points
   from one approach travel together in every bootstrap sample and
   every leave-one-out fold — they grow age coverage and
   diagnostics, NEVER n. "One approach = one cluster, however
   sliced" (18 §1.2) and "cut points increase age coverage; only
   independent physical approaches increase confidence"
   (disposition) are the same law; both are in the instruction. The
   archive grows clusters only by containing additional independent
   approaches.
2. **Boundary-aware release bound.** sigma_a >= 0 is a boundary
   parameter; a zero-heavy bootstrap alone is a confession, not a
   bound. U95_release = max(profile-likelihood U95, cluster
   bootstrap U95); with fewer than ~8 outer clusters the report
   carries profile + leave-one-approach-out sensitivity + bootstrap
   and the MOST CONSERVATIVE valid bound gates. One-approach removal
   pushing the bound above 0.35 = HOLD-data-insufficient. Extended
   decision table adopted verbatim, including the new row: a fit
   nearly flat in sigma_a = HOLD, parameter not identified.
3. **"Score unchanged" is conditional on the mean test.** Green
   branch (b0 ~ 0, b1 ~ 0, no regime asymmetry): formula unchanged.
   Bias branch: the unrepaired signed component enters the score
   EXPLICITLY as h*B_mu(a, regime) — never hidden in sigma_a, never
   left in an offline table while the runtime stays optimistic.
   Regime list extended to the disposition's seven (adds
   authority-limited); regimes run as held-out kill tables first,
   not an unrestricted model.
4. **U95 gates release; it does not lower the runtime constant.**
   Correction accepted to RESPONSE31's wording ("until U95 replaces
   it"): sigma_a_cfg REMAINS 0.35 for the first live cohort even if
   U95 lands smaller. The fit proves the configured model
   conservative; it does not optimize it in the same patch that
   first actuates the ladder. Any later reduction is its own
   reviewed common-arm change.
5. **Pseudo-floor executable.** Same regression on the pseudo data
   (same anchor window, evaluation config, age sampling);
   intercept-to-intercept comparison; kill bar: CIs must overlap AND
   fitted sigma_0 may not undershoot the pseudo central estimate by
   more than max(0.03 m/s, 20%). The bonus is taken: the pseudo
   slope publishes as a second independent sigma_a column (optional,
   not a gate).
6. **Cluster-balanced coverage + validated max age.** Equal weight
   per independent approach inside each age bin (a long trajectory
   may not buy coverage); the disposition's nine-column table is the
   required format. Validated max age = upper edge of the last bin
   with >= 5 independent approaches, passed coverage, no structured
   mean failure, no dangerous undercoverage, stable under
   leave-one-approach-out — never the oldest observed row. Bins
   below 5 approaches stay diagnostic. Model-form kill test decides
   quadratic vs B_rate_drift bound; never chosen by smaller
   admission score.

## 2. Shipped this round: the validated-age ceiling in the runtime

The disposition's runtime requirement — anchor_age <=
min(A_validated_max, existing tau-dependent cap) — is now law in
`terminal_override`: `validated_max_age_s` (config
`planner.terminal.validated_max_age_s`, interim 0.50 = the measured
coverage-tail p95) enters the authority conjunction as
min(tau+0.5, validated_max_age_s). Beyond it: neutral-decay, TERM
stays owned — exactly the after-no-return branch as ruled; a
passing maintenance score at an unvalidated age is an extrapolation
and is not authority. Unit-fixtured (182/182): authority latches at
age 0.40, refuses at 0.60 with the score PASSING and the legacy
caps permissive, returns at 0.60 when the ceiling is explicitly
widened — the new ceiling is provably the discriminator. The
interim 0.50 is re-read against the LOFO table's declared
A_validated_max before any HOLD lift; the config change rides the
lift patch, reviewed, never automatic.

## 3. P4 — the one-line definition (third request answered), and the row has numbers

**P4 := on identical recorded real-resolution frames, the
parallel-tracker build must (a) process the identical
unique-exposure set, (b) keep frame-processing P99 under the camera
interframe interval, (c) keep feature-delivery age P99 under 25% of
the 0.12s freshness horizon, and (d) leave the FULL channel's
accepted rows unchanged or explained.**

Why (b)/(c) are the honest budgets: the 4ms/250Hz hot loop reads
latest-value cells only — perception runs beside it, so its budget
is the camera, not the tick. QA's run (source 3b554f3,
ancestor-clean) read against the definition:

- (a) PASS: 141/141, 120/120 unique exposures.
- (b) PASS: frame P99 8.7/8.8 ms (max 12.5) vs ~33 ms interframe.
- (c) PASS: delivery-age P99 8.7/8.9 ms vs 30 ms budget.
- (d) F2 PASS (81/81 bit-identical). **F4 OPEN: 64 -> 56 accepted
  FULL** — same 115 raw fixes, 8 rows lost between fix and
  acceptance in the parallel arm only.

Suspect, named before the diff: the tracker's
prediction-inconsistent relock clears certification, and below the
1.6 m promote floor a cleared identity cannot freshly re-certify —
one relock converts subsequent FULL fixes into rejected rows. The
diff decides whether that relock fired honestly (the conservative
boundary working) or falsely (tracker prior noise killing a live
identity — a PRIMARY-channel liveness regression cohort-4 would pay
for in lost captures). Row-level acceptance-reason diff with a
range column is tasked to QA; P4 reads green only when the 8 rows
have a cause.

## 4. Board

The retro column's N rides in the lift package as requested. The
twelve-row HOLD-lift list is adopted as the board's definition.
GREEN: prior list + retro/dual-readiness (ratified closed) + P4
(a)(b)(c) + the validated-age runtime rule (row 8's enforcement
half; the declared number awaits the table). PENDING: the amended
fit (five outputs, boundary-aware U95), R26-2/3 formal close, P4
(d) — the 8-row diff. Cohort-4 HOLD stands until both tanks read
the twelve rows green.
