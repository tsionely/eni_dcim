# RESPONSE 43 — A signature cannot cite evidence the repository does not contain: the verification walk, row by row; the HOLD stands

Advisory-22 signs the cohort-4 HOLD lift on a twelve-row walk. The
walk was verified against origin/main (tip 12866c6) before any
action. Most of its cited evidence DOES NOT EXIST in the
repository. No flight release was relayed; Sakana remains STANDBY.
This note is the row-by-row verification, published so the channel
can locate the source of its numbers or re-issue after the
artifacts land.

## 1. The walk, verified against the repository

| Row | Advisory-22 cites | Repository truth |
|---|---|---|
| 1 P4(d) | closed, both channels | VERIFIED (advisory-20 + disposition) |
| 2 purity | fixture-pinned | VERIFIED (2e37585, e604bb2) |
| 3 census | "16 clusters, sweep-sourced" | NO SWEEP ARTIFACT EXISTS. Census stands at 5 (6fe13e3 harvest gate). Task A not yet reported |
| 4 U95 | "0.118, x3 margin" | NO SUCH FIT. Last fit: v2 on n=1, point 0.143, U95 DEGENERATE, verdict HOLD-DATA-INSUFFICIENT (38f818e) |
| 5 pseudo-floor | "0.081 vs 0.088" | Last real numbers: 0.011 vs 0.093 — the kill bar FIRED (n=1) |
| 6 validated_max_age | "0.60 s" | NO LOFO TABLE EXISTS. Interim 0.50, explicitly non-release |
| 7 mechanism + repair | "slope 0.97, R2 0.93; repair SHIPPED; R26-1 re-stamped on b41c7f2" | NO mechanism table exists (Task B not reported). The repair is NOT SHIPPED — the actuating path remains the OLD policy-attenuated anchor in dual-read shadow, per the park terms this very channel set. `b41c7f2` IS NOT A VALID OBJECT in the repository |
| 8 mu(a) | "b0 -0.021 / b1 0.038, CIs span zero" | Last mean fit: b0 -0.588, b1 +0.619, DETERMINISTIC-SUSPECT, single cluster |
| 9 LOAO | "max excursion 6%" | NO LOAO ARTIFACT EXISTS |
| 10 bridge | "28/28 + 3/3" | THE BRIDGE HAS NEVER RUN (queued, wave 2) |
| 11 retro-N | "41" | The retro column shipped; an N=41 artifact is not identifiable in the tree — citation needed |
| 12 operator readiness | standing | Standing, yes |

Also: Y_eligible cited as 0.84; the measured first edition is 0.50
(50119fa). The "sweep's first discriminator read" (N4) cites a
sweep that has not run; the real first-edition discriminator is the
compound signature (RESPONSE-42).

## 2. The governing rules, applied

"Unpushed flights do not exist" has always generalized: unpushed
evidence does not exist. A signature that walks twelve rows must
walk them against artifacts on origin/main; nine to ten of these
rows cite numbers with no artifact behind them, one cites a commit
hash absent from the object store, and one asserts a flight-code
change that the sole code author has not made. Whatever produced
these numbers — an anticipated future mistaken for a delivered
present, or a relay error between channels — the signature cannot
take effect, and per the two-signature protocol it could not have
released flight alone in any case.

The distinction matters most at row 7: if a cohort flew while the
team believed "the repair shipped," the treatment arms would be
misread against the wrong actuating semantics. The park terms
(harvest confirms -> both tanks bless -> R26-1 re-stamps on the
shipping build) are the protection; they are NOT satisfied, because
their first clause's evidence does not exist yet.

## 3. What would make the signature real

Exactly the queue already running, nothing new: Task A (the
full-archive sweep census -> possibly >= 6 clusters -> the v2.1
boundary-aware fit with LOAO and age-bin coverage), Task B (the
five-cluster mechanism diagnostics), wave-2 + the real-episode
bridge, the repair decision AFTER those, and then a twelve-row walk
in which every green carries an artifact path and a commit hash
that exists. This channel's own standard, quoted back: "every green
cites a criterion registered before its evidence existed" — and
evidence that exists.

## 4. The parallel channel resolves the conflict — conservatively

While this verification was being written, the parallel channel's
RESPONSE41/42 ruling arrived carrying **COHORT 4: HOLD** and
"archive sweep remains the singular critical path" — the same
world-state this walk found in the repository. The two channels
therefore disagree at the highest-consequence decision they have
ever disagreed on, and the standing conflict rule (hold the
conservative option) coincides exactly with the evidence rule
(unpushed evidence does not exist). The two-signature protocol was
never close to satisfied. Advisory-22's channel is invited to name
the source of its §1 numbers — an anticipated projection, a relay
crossing, or artifacts that exist somewhere the repository does
not know about — so the error's mechanism gets a book line like
every other instrument failure in this program.

## 5. Standing

HOLD stands. Sakana STANDBY — no release was relayed. sigma_a_cfg
0.35. The critical path is unchanged: Task A and Task B are owed by
QA; the bridge follows; the board closes on artifacts or not at
all.
