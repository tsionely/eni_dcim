# RESPONSE 30 — sigma_a = 0.000: the drift gate lives; one honest caveat routed with it

Deconvolution on the caa2398 residuals (61ffbaa; no new replay):

    Theil-Sen fit of r_v^2 ~ age^2 (oracle reference):
      sigma_a   = 0.000 m/s^2   (bootstrap CI 0.000/0.000/0.000;
                                 OLS sensitivity agrees — slope <= 0)
      sigma_ref = 0.437 m/s     (CI 0.437/0.437/0.521)

## 1. The drift verdict

Under the pre-registered reading (advisory-16B §3): sigma_a <= 0.2 —
**comfortable; (a) confirmed**. The entire 1.956/2.340 was reference
noise divided by small ages, exactly as the estimator-design note
predicted. The FULL_RATE_ANCHOR's physics hold over the maintenance
lifetime: floor at h=0.5 with sigma_v(age)=sigma_v_full stays ~0.186,
budget ~0.114. Ratification of the variance-regression estimator is
requested formally (the 0.35 gate itself never moved).

## 2. The caveat, not buried: sigma_ref = 0.437 breaches its sanity band

Expected 0.15-0.30 (measured oracle-slope noise); got 0.437. The
intercept absorbs BOTH reference noise AND any CONSTANT anchor-rate
offset: sigma_ref^2 = noise^2 + delta^2. If noise ~0.28, the residual
implies delta ~0.33 m/s of mean anchor-vs-true rate offset — which
would tax the crossing MEAN (h*delta ~0.17m) rather than the drift
term. Testable on the same CSV: the per-age-bin MEAN of r_v (not
squared) estimates delta directly, and its sign/stability says
whether it is a real anchor bias (e.g., the anchor latching a
transient) or reference asymmetry. Tasked to QA; the number rides the
HOLD-lift package. Until it lands, the runtime maintenance score
keeps the configured sigma_a ceiling (0.35) — strictly conservative
against a delta of this size at maintenance ages.

## 3. Board

GREEN: R26-1 (re-stamped), R26-4/5/6, causal ff, exposure-aligned
lookup, wall-time aging, runtime score gate, S1/S2/S3/S6, L1 both,
ψ-age, cert boundary, telemetry 12/13, retro column, dual readiness.
PENDING: delta decomposition (above), R26-2/3 formal close under the
ratified estimator, P4 wall-clock (harness in progress). The lift
request follows the last three.
