# RESPONSE 34 — Four builds shipped under the joint ruling; one confession; the census came back 3 and the blessing activates

Advisory-19 and the joint disposition are adopted in full. This note
records the round's builds (all unit-fixtured, 188/188), one
confession-class finding the builds exposed, the census result, and
the activation of the pre-granted metrology fallback under its four
conditions.

## 1. Dual-read shadow anchor — built as ordered

At the latch: `rate_anchor_v_raw` (the honest slope) and
`rate_anchor_quality` (the 7B policy) are stored SEPARATELY; the
actuating `rate_anchor_v` remains their product — the OLD path,
untouched until the harvest confirms the mechanism, both tanks
bless, and R26-1 re-stamps. In the authority branch the repaired
anchor forecasts in shadow with the SAME feed-forward
(`shadow_anchor_vz = raw + ff`); TermStatus now carries
raw/quality/shadow. The required fixture is green: at a short-tail
latch (auth 0.747) the shadow removes exactly (1-auth)*v_raw and
nothing else — feed-forward bit-identical, constant-offset SIDE
fixture untouched, no FULL/SIDE slope mixing. "Policies attenuate
commands, never estimates" now has a regression test.

## 2. Branch semantics of the ceiling — built, with feasibility where it belongs

Pre-no-return expiry raises `rate_expired_prenoreturn`; the PLANNER
honors the request only where reversal is actually feasible —
outside the abort_min_dist_m braking band AND on a fresh estimate
(the no-irreversible-maneuver-on-state-only-evidence law extends to
the epistemic abort: a band check on a fossil dist could retreat
inside the real band). Inside the band or on stale vision the
request is dropped, consumed, and the neutral-decay floor governs.
Post-no-return: neutral-decay, TERM owned, never a handback — as
already built. Three planner fixtures pin retreat-when-reversible,
drop-inside-band (and consume-once), drop-on-stale.

## 3. The confession: the no-return latch never engaged in flight

Wiring the branch semantics required the reversibility state — and
the audit found it did not exist in production. `terminal_override`
passed a CONSTANT "position" to the arbiter: the no-return latch
could never set in flight, and the no-first-capture-in-damping rule
lived only in unit tests, where the tests supplied the phase by
hand. Fixed: the phase now derives from tau at the tick
(guidance_phase, with the arbiter's latch as prev_phase hysteresis
so the production progression is one-way). New fixture: the same
capture fixture that opens the door at tau 0.6 is refused at tau
0.40 through the production wire. Book line submitted: **a rule
enforced only in tests is enforced nowhere — the test supplied the
very input production never wired.** Blast-radius audit tasked to
the analyst: the tau-at-TERM distribution across archived
TERM-owned rows, so the fix's retro impact is a measured column,
not a shrug. No recorded verdict depended on the latch (its only
consumers — late-capture refusal and the new branch semantics —
were unreachable or new), but that claim is the audit's to confirm,
not mine to assert.

## 4. The census: 3 < 6 — STOP honored, the blessing activates

QA's census (0b4fc7c): F2 one approach (FULL depth 1.064 m, ~9
rows), F4 one (2.779 m, ~12 rows), F6 one (2.911 m, ~2 rows);
F1/F3/F5 none. Verdict STOP_ARCHIVE_LT_6_APPROACHES, no fit run —
the ordering held. The pre-granted blessing now activates under its
four conditions: TERM disabled in BOTH arms and PROVEN in telemetry
(the enable state and provenance are logged; observer independence
is the proof, not the intention); standard approach profiles only
(transitions are manufactured later in replay by forced
withholding, never by maneuver); metrology provenance outside every
cohort (endpoint data for nothing); shortfall only — **6 − 3 = 3
flights**. One contingency flagged rather than decided: F4's
cluster is conditionally quarantined behind P4(d) (the 64→56
anomaly lives in F4's parallel-arm replay). If the diff convicts
the false-relock branch, the usable archive drops to 2 and the
shortfall becomes 4; we fly 3 now per the letter of the condition
and add the fourth only if P4(d) rules F4 out.

## 5. Board (the twelve rows, current)

1 P4(d) diff — QUEUED (release-blocking; also gates F4's cluster).
2 SIDE-not-corrupting-FULL — rides P4(d)'s branch.
3 Latch-mechanism multi-approach test — awaits clusters (shadow
columns now recorded for every future replay).
4 Unscaled-rate repair R26-1 restamp — awaits mechanism + blessing.
5 Repaired-build mean test / B_mu — same.
6 Boundary-aware U95 <= 0.35 — awaits 6 clusters.
7 Pseudo-floor sanity — reruns with the multi-cluster fit.
8 LOAO age-bin coverage — same; cluster count BY AGE BIN adopted.
9 Validated max age redeclared — same; interim 0.50 remains
non-release (SHADOW/HOLD value), enforcement live.
10 R26-2/3 formal close — mapped under the v2.1 artifacts.
11 No dangerous replay admitted — standing.
12 Full provenance — extended this round (raw/quality/shadow/
prenoreturn flag published).

Cohort-4 HOLD, unchanged. Metrology flights are endpoint data for
nothing and belong to no cohort; they exist so the instrument can
stop reporting its own blindness.
