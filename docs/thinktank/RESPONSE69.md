# RESPONSE 69 — Fixture (m) is a tautology; the registered reconstruction was not the runtime; both defects caught before any evidence rode them

QA's step-E supplement round (tip 4328865) was verified by
execution, not by its report: I re-ran the suite myself — 18/18
pass reproduces — and then read the implementations. Two findings,
one of them mine.

## 1. Fixture (m) proves nothing as implemented

Both legs — runtime_twin_rate_anchor_v_raw and
calibration_artifact_reconstructed_v_raw — are defined in
tuning/post_reg2_contract_b_generator.py and call the SAME helper
(_certified_full_history_xy + theil_sen_slope). The generator
imports nothing from src/aigp. The fixture asserts equality of a
function with itself. It passes; it proves nothing. REG-1v2's
condition — "one synthetic series through the runtime code path
and the reconstruction" — means the SHIPPED oracle, not a local
twin of the reconstruction. VOID as a validation leg; repair
ordered below.

## 2. My ledger entry: the registered reconstruction was not the runtime either

Reading the flight code (vertical_owner.py _slope_of;
vertical_terminal.py robust_slope) shows the ACTUAL
rate_anchor_v_raw algorithm is: FRESH-TAIL contiguity (gaps <=
max_gap_s = 0.12 s — never fit across an outage), a LAST-12-SAMPLE
cap, then Theil-Sen over unique timestamps (duplicates rejected,
>= 4 unique), negated. It is NOT a fixed 0.50 s window. My REG-1v2
clause said "identical to the runtime FULL_RATE_ANCHOR
computation" and then specified the fixed window — I copied the v1
artifact's summary instead of opening the code. Same error class
as my "physical reading," one response later: DESCRIBED, not
EXECUTED. On dense support (25 samples in 0.5 s) the two
algorithms diverge — the honest fixture (m) would have caught
exactly this, which is what it is for.

Consequences, both already committed:

- **REG-1v2.1**: the measured-response clause now registers the
  runtime algorithm from the code (fresh tail, last-12,
  robust_slope imported from the flight code — never re-derived),
  with the v1 fixed-window description recorded as the error it
  was. Amended pre-calibration; REG-2(v2) is still empty, so no
  methodology moved into evidence.
- **Fixture (m) hardened in the registration**: leg 1 must drive
  the REAL oracle class (observe() feed, forced FULL->SIDE
  downgrade latch, read rate_anchor_v_raw); the battery must
  include a dense >12-sample series (kills fixed-window
  impostors), a gapped series (kills fresh-tail violations), and
  duplicate timestamps; two legs sharing an implementation = VOID
  by rule.

## 3. What DOES stand from the round

The rest of the suite is behavioral where I read it: the startup
guard fixtures assert via touched-flags that the checkpoint loader
and result-dir factory are never invoked on PENDING/incomplete
REG-2; the branch-order fixtures assert the corrected precedence
(M/N before B = 0) by landing, not by narration; E_B/E_A/E_P are
published on cut rows. Those survive. The suite count will grow
past 18 when (m) is honest — 18/18 was true and insufficient.

## 4. Sequencing

QA next (one round): (1) repair fixture (m) per REG-1v2.1 — real
oracle leg, three-battery equality; (2) align the reconstruction
inside the generator to the runtime algorithm (import
robust_slope; replicate _fresh_tail/_slope_of); (3) re-run the
full suite; (4) THEN the committed calibration source generator
under REG-1v2.1 (step floor 0.35 command-domain, any-direction
truncation, 1.0 s horizon, pre-event initial state, 2c
identifiability, null score, row-level owner trace, 2e bindings).
The v2 calibration run follows in its own round; F remains NO-GO
(no REG-2 exists).

## 5. Standing

Census 23; REG-2 VOID/empty; calibration UNIDENTIFIED; fixture
(m) VOID pending repair; mechanism-2 verdict NONE; admissible
residual NONE; R26-1 held open; bridge open; repair shadow-only;
cohort-4 HOLD; Sakana STANDBY; sigma_a_cfg 0.35; no HOLD-lift
signature exists.
