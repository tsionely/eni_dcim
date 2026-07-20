# RESPONSE 19 — The ladder core is built; one pre-registered semantic; the release gates' division of labor

Both channels' ladder rulings are implemented in their common core.
This note records what shipped, one semantic change pre-registered
under the ladder's own release gate, and which gates remain offline
work before cohort 4.

## 1. Shipped (unit-fixtured, 174/174, smoke clean)

- **Source identity is explicit end-to-end**: the pipeline's
  full-quad features are `FULL_QUAD`; the close tracker's features —
  whose depth is the OBSERVED certified side-pair separation, never
  believed range — are `SIDE_PAIR` (sparse-top variants are
  `SIDE_PAIR_ROW_ONLY` and stay in SHADOW: telemetry, never
  metrology). One label per measurement model. TermStatus now carries
  `source_mode`.
- **Per-source histories** in the oracle; a slope is NEVER fitted
  across a source boundary (gate S3 pinned: a +0.08 inter-source bias
  with identical true slope leaves v_z unchanged through the switch).
- **Transition rules as ruled**: downgrade FULL→SIDE only when {full
  stale} ∧ {side independently mature} ∧ {overlap consistency
  |Δe| ≤ max(0.10, 3σ_side)}; upgrade back on 3 consecutive
  consistent full-quad observations (gate S2-unit pinned, both
  directions); a consistency-gated source step receives a ONE-SHOT
  jump-guard grace (a measurement-model change, not a physical jump —
  and not an ownership/phase event).
- **Source-indexed sigmas**: admission now takes (σ_e, σ_v) from the
  active rung — full-quad keeps its measured 0.05/0.10; the side rung
  starts at margined ×1.5 analogs (0.075/0.15) until the R5 library
  matures per-rung rows. Sigmas are source constants.
- **Observer independence across sources** (gate S6 pinned): rungs
  mature with TERM disabled; enable toggles reset nothing; shadow
  modes never grow metrology history.

## 2. Pre-registered semantic: readiness runs on the CONTIGUOUS fresh tail

Implementing L1's own bar ("ready lights below 2m on the F2/F4
replays") exposed a latent semantic: the readiness gap statistic ran
over the WHOLE per-attempt history, so a single mid-approach outage
(one wash, one bloom flicker) permanently vetoed readiness for the
rest of the attempt — a plausible contributor to ready=0 in the very
windows where certified features existed. Changed, pre-registered
here: n/span/gap and the Theil-Sen window now run on the contiguous
fresh tail (the gap-chain ≤0.12s ending at the newest sample). The
advisory-7 predicate is unchanged in its numbers; it now interrogates
the evidence that is actually contiguous, and a slope can never span
an outage (which also serves S3). Safety unchanged: an outage still
zeroes readiness until a fresh 6-sample/0.15s tail rebuilds.

## 3. Release-gate division of labor (live flight stays BLOCKED until done)

- **Built and green (unit)**: S2 (switch consistency + hysteresis +
  no-spike), S3 (offset-not-velocity), S6 (independence).
- **QA (mock + replay harness)**: L1 deep-penetration replays of
  phase6l F2/F4 — ready-below-2m + the ACCURACY fixture (the ladder's
  e_z must read the ~0.1-0.2m offset the eleven contacts prove);
  S5 dropout/late-promotion sweeps; S2's full source-removal replay.
- **Analyst**: S1 zero-false-metrology on the successor-certificate
  and projected-row fixtures (the scale gate handles span×range; S1
  additionally proves no false TERM_READY); S4 geometry metamorphic
  (crop-and-project); the §4 certificate-boundary audit (first-cert
  ≥1.6m / maintain-below-1.4m — verify the existing certificate
  enforces it, else it queues as a tracker patch).
- Remaining build items behind the gates: the ψ-age record on the
  side rung and the full mandatory-telemetry expansion (the core
  term_source_mode + sigmas shipped; the long field list rides the
  next telemetry pass).

## 4. Also adopted from the two rulings

Brake-pitch file reopened (the §1 hypothesis): the analyst's
loss-frame table gains {pitch at loss, bbox bottom row, exit border};
if pitch adjudicates, the ten-rounds-queued fix (decelerate by 5-6m,
θ ≤ 3-4° through commit) is the follow-up build. A8 episode rule
adopted (first touch per ≥100ms-separated episode — the F2 harvest
becomes clustered episodes, not eleven samples, and not one). Mock
point-mass asterisk recorded. Block-B re-power proceeding on
flights-as-units. Cohort-4 protocol as ruled: ladder in BOTH arms,
treatment = terminal.enable only, TERM-informative iff an owned,
provenance-valid, nonzero-command crossing exists.
