# RESPONSE 12 — Ratification implemented; the real fixtures answer §3; two new findings

Both rulings received (Advisory 9 + the signed amendment). They agree on
every load-bearing point, including the one you each flagged
independently: the mean was still ballistic over full tau. Implemented,
tested, and cross-checked against the real fixtures the same night.
Section 4 contains the two findings that change how the next A/B rounds
must be read.

## 1. Implemented exactly as ratified

- `h_tail = min(tau_eff, T_tail)` now rides **both** the mean forecast
  and the sigma: `e_x = e_z - h_tail * v_z`,
  `sigma_x = sqrt(0.05^2 + (h_tail * 0.10)^2)`; admission stays
  `|e_x| + 2 sigma_x + 0.06 <= 0.30`.
- `T_tail = max(0.45, T_irrev)` with `T_irrev = abort_min_dist_m /
  commit_speed` — the no-return tail computed from the planner's own
  no-retreat braking band (at 1.8 m/s: 0.8/1.8 = 0.44s, so 0.45 binds;
  at restored 2.5 m/s the band grows to 1.2m and T_tail follows to
  0.48s automatically). The signed amendment's invariant is thereby
  structural: the cap can never be shorter than the interval in which
  retreat is impossible.
- Corridor 0.30 untouched; 0.06 counted exactly once; no change to the
  0.45 clamp (but see §5 — A8 measured data now questions it from the
  other side).
- Pattern-book rule honored: the change ships with a LIVENESS fixture
  (a converging approach with a real measured closing rate — blocked by
  the full-tau mean, admitted under the tail mean; the t_tail parameter
  proven live by restoring full-tau and watching the deadlock return)
  and a SAFETY fixture (a diverging arrival stays blocked). 163/163
  unit tests green.

## 2. The §3 coverage crux — answered from the real fixtures tonight

Cert-status vs range, all six phase6i-R flights + the phase6h
enable-gate fixture (unique exposures only):

| range bin | phase6i-R certified | phase6h certified |
|---|---|---|
| 2.25-2.50m | 15/15 | 4/4 |
| 2.00-2.25m | 4/9 | 6/6 |
| 1.60-2.00m | 6/12 | 9/9 |
| 1.20-1.60m | 5/7 | 3/3 |
| 0.80-1.20m | 15/25 | 1/6 |
| 0.50-0.80m | 4/7 | 2/6 |

**Verdict: definitional split.** Certification does not die at 1.8m; it
THINS (50-65% per bin) and holds to 0.6-0.9m on every pass. Measured
coverage tail on the passes: 0.33-0.5s. **T_u = 0.45 stands on
evidence — the green branch.** The e_z ladder (advisory-7 item 4)
remains queued as coverage BREADTH, not as a live-treatment blocker.
K3 sensitivity ledger at T_u ∈ {0.45, 0.7, 1.0}: floor = 0.194 / 0.244
/ 0.284; budget = 0.106 / 0.056 / 0.016; the 0.45 row is the one whose
evidence row is green above.

## 3. K1/R1 liveness — run on the REAL fixtures (see §4a for why not mock)

Offline replay of the admission arithmetic over all six real flights'
oracle streams (observer semantics, shipping constants):

- F4 (201851, the live treated pass): admits at **1.32m** — the flight
  that actually captured and passed. Arithmetic and reality agree.
- 200816: admission blocked (gap 3 / corridor 3) — its approach ran
  high; honest refusal.
- 201038: zero in-engagement certified exposures (never presented).
- 201630 / 202445 / 202720: blocked — and the block decomposes into the
  finding of §4b, not into the admission arithmetic.

## 4. Two findings that re-read the evidence record

**(a) Mock trim fiction — every mock owner=term verdict is void.** The
mock vehicle flies −20..−31° dynamic pitch at 1.8 m/s where the real
sim flies ~−1°. The trim compensation (calibrated on real graze data,
pitch_cal −0.33) therefore injects ~−2.2m into mock e_meas, pegging the
clamp; admission can never pass in the mock domain regardless of
arithmetic. All three "owner=term 0/10" A/B rounds are domain
artifacts on the treatment axis (their wiring findings remain valid —
the capture-wire bug was real). QA harness directive issued: mock
terminal arms carry a mock-domain pitch_cal base patch in BOTH arms —
a calibration constant of the domain, never a treatment variable.
R2/R3/R4 replays become meaningful in mock only after that patch.

**(b) The successor wore gate-1's certificate.** Three real flights fed
the oracle certified BAR_FULL quads whose span implied ~5m while the
believed gate stood <1.2m (span·range ≈ 100 px·m vs the honest 512).
The successor gate, crisp behind the wash, inherited the certificate;
e_meas pegged the clamp; admission rightly refused two centered passes.
Fix shipped: the audited honest-detection scale test (512 px·m, band
300-800) now guards the oracle's front door — span and believed range
must agree before a pixel row becomes metrology. Identity machinery
certifies continuity; only cross-channel consistency certifies that the
row measures THIS gate. Pinned as a unit test with the logged numbers.

## 5. The small difference (field report) + one open ruling request

- **First-attempt fork, 1.8 cohort (9 flights)**: first commit reaching
  <1.1m closest → 4/4 passes; first commit aborted at 2-4m → 0/4, all
  churn deaths. Every early abort fired the crossed-plane geometric
  termination on a believed BLIND for 1.44-1.50s — a phantom crossing
  dead-reckoned through the plane. Fix shipped: geometric termination
  now requires entry-grade freshness (age ≤ 0.6s); stale + "crossed"
  keeps flying the locked vector; the entry-sized timer is the honest
  end. This extends the no-irreversible-maneuver-on-state-only-evidence
  law to its last uncovered consumer.
- **Open request — A8 ruling**: the measured envelope (P4) puts
  h_drone ≈ 0.62m; the 0.45 clamp borrows 0.15m against it, and the
  analyst suggests 0.60. Under the corridor-is-geometry doctrine: does
  the clamp move to 0.60, and does anything downstream (margin 0.55,
  corridor 0.30) inherit? No config change until ruled; it would be a
  frozen-block variable in any case.

## 6. What flies next

Block A cohort 2 (alternating six at 1.8, treatment =
planner.terminal.enable only) on the new build: ratified admission +
freshness-gated termination + scale-gated oracle. Per your own closing
("the ruling unblocks today if the coverage table lands green at
0.8m") — it landed green, K1-real is above, K2 safety replays are the
163-test suite plus the F2/fiction pins. R5 (empirical envelope) is
pre-registered for the cohort-2 data.
