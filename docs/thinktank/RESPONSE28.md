# RESPONSE 28 — R26 interim: the ladder is a behavior; two fixes from its own harness

Status of the advisory-16 gates after the first anchor replay
(Codex, 558b6db on 3c4c5d9) and the fix build (7657559, 181/181).

## 1. R26-1 LIVENESS: PASS — the before/after metric flipped

On the F2 deep-penetration window with forced FULL loss at frame 304:
**owner_term_side_rows = 16**, SIDE maintained TERM ownership to
**1.006m**, max admission 0.271 ≤ 0.30, phase unchanged. The metric
that read ZERO across three mute cohorts is nonzero for the ruled
reason. R26-4/5/6 (offset isolation, contradictory-sequence
invalidation, FULL-return upgrade) all PASS.

## 2. R26-2/3 sigma_a: first measurement FAILED — and indicted two bugs, both fixed

Measured sigma_a_rms = 1.956 m/s² (gate ~0.35). Diagnosis:

- **The feed-forward was not yet in the build** — so every COMMANDED
  servo correction (±0.6 m/s over fractions of a second) counted as
  "unmodeled" acceleration. The ruling's "mandatory, not optional"
  was proven empirically by its own gate. Now implemented: while SIDE
  maintains, v_z = anchor + (applied_now − applied_at_anchor).
- **A safety bug the harness caught in telemetry**: rate_anchor_age_s
  aged against the newest ACCEPTED exposure, so it FROZE the moment
  observations paused — keeping a stale anchor "young" precisely
  during blindness, the unsafe direction. Now ages against current
  time; SIDE observations still never reset it; pinned as a fixture.

The sigma_a rerun on 7657559 measures the true disturbance residual
(truth-v minus the feed-forward-corrected hold). The 0.35 verdict
gate is unchanged; the number decides.

## 3. Gate board

GREEN: R26-1, R26-4/5/6, S1, S2/S3/S6, L1-liveness, L1-accuracy,
ψ-age (DIAGNOSTIC_ONLY), certificate boundary (+status_at sync),
telemetry (12/13 closed; psi_age field rides the next perception
touch, non-blocking per the S4 disposition), consume-once, exact
pairing, armed latch, realistic seeding, conservative door.
OPEN: the corrected sigma_a column (rerun in flight), R26-2/3 formal
close, P4 wall-clock comparison.

If the corrected sigma_a lands under the gate, we will request the
cohort-4 HOLD lift in RESPONSE29 with the full board attached.
