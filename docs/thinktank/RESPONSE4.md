# RESPONSE to ADVISORY #3 (last-meter vertical from the top bar)

Paste back to think-tank #2. Verdict: **adopted** — ranks 1+2 as one
integrated work item, folded into the GateCloseTracker (its projection
machinery is the g(·) your two-state factor specifies; its
frozen-orientation policy is already the one you require). Dispositions,
corrections, and what already shipped below.

## 1. Already in the repo (same day)

`src/aigp/planning/vertical_terminal.py` + unit tests: the closed-form
oracle e_z = W·y_T/ℓ_T − d*, the row-only fallback, the crossing-error
forecast e× = e_z − τ_eff·v_z, the bounded velocity-closure command, and
the position→damping→freeze schedule — pure functions, wired in only
when the tracker's top-bar identity stage lands. Your rank-5 rejection
is demonstrated IN CODE as a test: holding the bar on a fixed image row,
a vehicle centered at 3 m is implied >0.5 m toward the top edge by 1 m —
the exact class of the observed overfly. Scale invariance and both
miss-signature signs are asserted numerically.

## 2. Corrections / constraints from our side

1. **W convention.** Our PnP model treats 1.6 m as the OUTER ring square
   (the acquisition detector measures outer contour corners; the outline
   has historically included the banner-merge). Your d*/W ≈ 0.5 assumes
   W = opening. We therefore treat d* strictly as a CALIBRATED quantity
   (from the assigned banner/bar geometry measurement, R4) — never the
   0.5 default. Your own §1.1 note ("compute, don't assume") is taken
   literally.
2. **Committed test material.** The repo's close-range recordings are
   one known-HIGH approach (F1, banner-view frames to the collision) and
   one known-TRUE-LOW approach (F2, whose last fix also carries a sign
   CONFLICT — believed +0.31 vs true −0.95 at 1.67 m). The clean pass's
   close frames exist only on the analyst's machine. So: Tests B/E run
   on repo material now; Test A's 2.4→1.34 m overlap band runs at the
   analyst on full recordings; everything re-runs when the current
   confirmation cycle delivers takeoff-window slices (the pad-slice
   problem is fixed operationally).
3. **F2 elevates your Test E.** The sign-conflict-at-fix is suspected
   banner-as-gate; your banner-substitution kill test and identity gate
   list (row innovation, edge polarity, thickness, ordering, span
   consistency) are adopted as the ACCEPTANCE GATE of the tracker's
   top-bar stage, not merely a release test.
4. **τ_actuator is unmeasured** — we will measure thrust-step response
   before trusting τ_eff margins; until then the freeze thresholds stay
   at your provisional values and Test I runs with ±one-frame latency
   perturbation as specified.
5. **Unique-exposure discipline** (§2 warning): enforced at the RX layer
   since the dedupe fix — all derivative histories are keyed by frame
   id/timestamp by construction.

## 3. Kill tests

A–I adopted verbatim as the release gate, with your provisional bars.
Sequencing: E and B first (repo material, they arbitrate the two known
failure signatures), then A/C/D at the analyst, F on any recording with
a pass event, G–I before the first live flight with the law active.

## 4. Where this sits in the plan

The build currently in confirmation flights carries: bloom-proof
detector (96% close coverage), camera-on-target yaw, close tracker
(partial-edge position fixes), single climb compensation. The vertical
terminal channel is the next perception+guidance work item, implemented
as: tracker top-bar identity stage (your gates) → de-rotation to the
pass frame → two-state [e_z, Z] factor → visual v_z (robust slope over
unique exposures) → e× forecast → velocity-closure collective command →
your §6 envelope with the moments-based go/no-go. One work item, one
replay gate.

No new question this round — the ball is in our implementation court;
we return with Test B/E numbers.
