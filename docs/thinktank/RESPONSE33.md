# RESPONSE 33 — First read of the new instrument: HOLD as designed; the 0.437 decomposes into a signed offset with a named mechanism

The v2 release fit ran (CSV-only, 38f818e) and the pre-registered
decision table produced its first verdict: **HOLD,
DATA-INSUFFICIENT — n_clusters = 1.** No number was released, no
number was presumed; the instrument reported its own blindness.
That is the system the last three rulings built, working on its
first pull.

## 1. What the n=1 fit says (flagged, never adjudicated at n=1)

- Constrained Student-t point sigma_a = 0.143 (sigma_0 = 0.011);
  U95 formally equal at 0.143 but DEGENERATE — one cluster, not
  release-valid, exactly as the doctrine predicted for a
  single-approach bootstrap.
- **The 0.437 mystery is solved — and it was never noise.** The
  mean fit returns mu(a) = -0.588 + 0.619a, and the dominant
  regime (flat_no_ff, 13/16 rows) carries signed mean **-0.437**:
  the retired estimator's "sigma_ref = 0.437" was delta, a SIGNED
  DETERMINISTIC OFFSET, laundered into a variance by an instrument
  that could only see second moments (E[r^2] = delta^2 +
  noise^2). RESPONSE-30's decomposition hypothesis is confirmed in
  magnitude and now signed. Residual RMS after mean removal:
  0.053. Amendment-3 doctrine governs: repair or explicit B_mu —
  never into sigma.
- Intercept kill bar FIRED (real 0.011 vs pseudo floor 0.093,
  beyond max(0.03, 20%)): on one cluster the mean model can absorb
  floor-level scatter — the overfit signature the bar exists to
  catch. Clusters adjudicate.

## 2. The named mechanism (code evidence, prediction pre-registered)

The latch shrinks the measurement. At the legal transition
(`vertical_owner.py` latch block):

    auth = min(1.0, (span_full/0.3) * (n_full/10.0))
    rate_anchor_v = -slope_full * auth

The advisory-7B authority schedule is a SERVO-GAIN policy — "how
loudly v_z speaks" — correct where the FULL branch applies it live.
But the anchor latches the product as the frozen physics baseline,
so a transition caught with a short FULL tail (auth ~ 0.4-0.6)
under-predicts the true rate by (1-auth)*v_true for the anchor's
entire life: a signed deterministic offset, not drift. At terminal
climb rates ~0.7 m/s and auth ~ 0.4 this lands on the observed
-0.44. The b0 + b1*a structure follows: b0 = -(1-auth)*v_latch,
b1 = -(true rate evolution the frozen anchor cannot see).

"Freeze the measurement, not the physics" — the shrink is neither:
it freezes a POLICY-ATTENUATED measurement. The candidate repair is
to latch the honest slope and keep authority at the consumer (or
retire it for the anchor path); it changes SIDE-maintenance
behavior, so it ships only after the harvest confirms the mechanism
and both tanks bless it — R26-1's liveness stamp was earned under
the shrunk behavior and would need re-stamping.

Pre-registered test for the harvest (falsifiable, parameter-free):
per cluster, record auth_at_latch and the oracle rate at latch;
the mechanism predicts b0 ~ -(1-auth)*v_latch cluster by cluster.
If auth ~ 1.0 clusters still show b0 << 0, the mechanism is
refuted and the search continues (latch timing, caged reference,
sync).

## 3. The remedy, as pre-registered: grow independent approaches

Instruction issued to QA: census the recording archive for
approaches with certified FULL coverage below 3.5 m and
tracker-viable SIDE production; run the forced-withhold replay per
approach; ONE APPROACH = ONE CLUSTER (cut points travel together);
target >= 6 outer clusters, then the full v2.1 fit (boundary-aware
profile + LOAO + bootstrap, most conservative bound gates). Census
reports BEFORE the fit, so if the archive cannot reach six we know
early. Named fallback if it cannot: metrology-only recording
flights — TERM disabled in BOTH arms, nothing actuates, flights
exist to be replayed into clusters. Recording is not actuation, but
the option is the tanks' to bless, not ours to assume.

## 4. Board

P4 defined and read in RESPONSE-32 (three clauses green; the F4
8-row acceptance diff queued with this instruction). Runtime
validated-age ceiling shipped and unit-fixtured (182/182).
PENDING: archive census -> multi-cluster fit -> boundary-aware
U95; the mechanism test above; R26-2/3 formal close; P4 clause
(d). Cohort-4 HOLD unchanged. The deterministic-repair question is
explicitly parked until the harvest speaks — one cluster convicts
no one.
