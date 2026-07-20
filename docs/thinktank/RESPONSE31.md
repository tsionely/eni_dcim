# RESPONSE 31 — The release number is U95: all four amendments adopted; the fit re-runs under clusters

Advisory-17 and the parallel ruling are convergent and adopted in
full. The ratio estimator is retired from the release path (it
remains in the book as the estimator whose design taught us WHY it
had to retire: Var = sigma_a^2 + sigma_ref^2/a^2 is
reference-dominated at exactly the ages that matter). The
variance-regression family is ratified in principle; the 61ffbaa
number (sigma_a = 0.000, CI 0.000/0.000/0.000) is NOT the release
number — a bootstrap CI of identical zeros from resampled ROWS of
clustered data is itself the tell that rows were treated as
independent when they are not. The fit re-runs under the four
amendments before any number touches the gate.

## 1. The four amendments, as adopted

1. **Intercept is a combined floor, not "reference noise".**
   sigma_0^2 absorbs reference noise + anchor-latch noise + sync
   error + covariance. The pseudo-transition sanity test runs on
   FULL-only stretches with non-overlapping anchor/evaluation
   windows: the real fit's intercept must not sit materially below
   the pseudo-transition floor. This also absorbs the RESPONSE-30 §2
   caveat: the 0.437 breach stops being "sigma_ref out of band" and
   becomes a decomposition question the mean-fit answers.
2. **Row-level OLS is prohibited.** The release instrument is a
   robust constrained fit (nonnegative sigma_0^2, sigma_a^2;
   Student-t scale model preferred, constrained robust r^2-vs-a^2
   provisionally acceptable) with a CLUSTER bootstrap — resampling
   flights / FULL-to-SIDE transition episodes, never rows.
3. **The mean is fitted, not assumed zero.** mu(a) = b0 + b1*a on
   SIGNED residuals, plus per-command-regime signed tables
   (up / down / triangular / slew-limited / saturated). This
   SUBSUMES the delta-decomposition already tasked in RESPONSE-30 §2
   — same CSV, now with the ruling's structure. A persistent b1 is a
   deterministic model failure: repaired or carried as a separate
   signed bias allowance, never laundered into sigma.
4. **Release statistic = one-sided U95(sigma_a) <= 0.35.** The point
   estimate is insufficient by construction. Decision table honored:
   point <= 0.35 with U95 > 0.35 is HOLD-data-insufficient — the
   remedy is more independent transitions (the recording archive can
   supply replay transitions; no flight is needed to grow clusters).

Plus, adopted verbatim: leave-one-flight-out coverage by age bin
(0-0.1 / 0.1-0.2 / 0.2-0.3 / 0.3-0.4 / 0.4-0.5 / >0.5) with a
declared max VALIDATED age; the model-form kill test with the
monotone B_rate_drift(age) fallback bound and its modified score
formula if per-bin coverage fails in a structured way.

## 2. Runtime compliance — already true, now pinned as policy

- Reference noise is EVALUATION-ONLY. The runtime maintenance score
  uses sigma_v_maint^2 = 0.10^2 + (age * sigma_a_cfg)^2 and nothing
  from the reference channel. Verified against vertical_owner.py as
  shipped — no change required.
- No extrapolation beyond the validated max age: the runtime already
  neutral-decays (the (c) floor) when the score gate or the
  age <= tau+0.5 cap fails; once the LOFO table declares the
  validated max age, the config ceiling and cap are re-read against
  it before any HOLD lift.
- sigma_a_cfg stays at the conservative 0.35 ceiling until U95
  replaces it. The score formula itself is unchanged by the ruling.

## 3. Board

GREEN (unchanged): R26-1 re-stamped, R26-4/5/6, causal feed-forward,
exposure-aligned lookup, wall-time aging, runtime score gate,
S1/S2/S3/S6, L1 both, psi-age, cert boundary, telemetry 12/13, retro
column, dual readiness.
PENDING: the amended fit (QA, instruction issued with this note —
U95, mu(a) + regimes, pseudo-transition floor, LOFO table); R26-2/3
formal close under it; P4 wall-clock. Cohort-4 stays HOLD until all
three land and both tanks read the twelve-row board green.
