# RESPONSE 18 — Invariants in; cohort-3 adjudicated against its own registration; the ladder is declared the next build

Both channels' rulings on RESPONSE16 are implemented and the cohort-3
endpoint report is in. The damper's registered claim FAILED its
primary endpoint and the symptom-freeze rider is honored — no
retuning. The evidence now names one build.

## 1. The signed damper invariants — implemented and fixtured

- **Invariant 1 (aggregate cap)**: the 0.35 cap and the 1.5 slew now
  bound trim PLUS sink insurance as one sum, at one limiter. The
  saturated-descent corner behaves exactly per the signed rule (the
  insurance consumes budget); the no-arm covered class is re-pinned
  in the non-saturated regime where it lives. Worst-case simultaneous-
  demand fixture added.
- **Invariant 2 (exclusivity + tracking)**: while TERM owns, the
  legacy vertical contributes nothing (structural — TERM's command
  replaces it) and the damper now TRACKS the applied command
  (`track_applied_vz`), so a pre-no-return handback resumes within
  one slew step of the applied value. Bumpless-handback fixture
  added. 171/171 green.
- **Authority stack, stated per the rider**: TERM carries its OWN
  limiter chain (vz_max 0.6, az slew, one attitude conversion); the
  damper cap governs the LEGACY channel only; the two never compose
  because ownership is exclusive by construction.

## 2. Cohort-3 against its registration — honest verdict

- Commit vision past 3m: **1/6** (cohort-1: 3/6, cohort-2: 0/6) —
  above the wipeout, NOT material. The registered claim failed.
- 4.3-4.8m blind-brake cluster: reduced, not vanished (1 flight, 2
  events).
- Fork metric: 0/3 triggers (no non-blind first commit reached 1.1m).
- What DID change: commit vertical std collapsed to 0.05-0.14 (from
  2.0-4.65 ptp), and the live arms penetrated to **0.65m / 0.85m /
  2.66m** — F2 reached the gate and contacted it 11 times (clip-budget
  abort). The fight moved from "eyes die at 4m" to "arrive slightly
  off at the plane" — with zero blind-reverse collisions and the stop
  policy holding.
- Adjudication: vz oscillation was A driver of FOV-leave, not THE
  driver. Per the symptom-freeze rider the damper's constants stay
  frozen; no opportunistic retune.

## 3. Why the ladder is now THE build

In both deep-penetration live flights the oracle was STARVED at the
moment it was needed: engaged 41/58 ticks, **ready = 0** — the
full-quad feature stream dies below ~2m (certification thinning,
measured), so admission had nothing honest to admit and TERM never
owned (treatment axis mute for the third cohort running). The clips
are legacy-attributable: the legacy aim delivers the airframe to the
plane ~0.1-0.2 off, exactly the error class the terminal channel
exists to null. Advisory 9 §3's second branch named this outcome in
advance: *"the deadlock's real cause is the missing e_z ladder below
full-quad range — and that ladder ships before live treatment."*

**Next build (post-cohort-3, pre-cohort-4): the e_z ladder**
(advisory-7 item 4): top-edge row + certified side-pair below
full-quad range, feeding the SAME oracle through the SAME validity
gates (identity, span×range consistency per available structure,
probation semantics per the tier-2 constraints), with the ladder rung
recorded per observation (term_source_mode finally ships). Fixtures:
the phase6l deep-penetration windows are the ready-made liveness set
(ready must light below 2m on F2/F4 replays); the successor-
certificate and projected-row fictions are the safety set.

## 4. A8 — the harvest and the point-mass finding

The contact-instant re-extraction is spec-honest and data-starved
(2/20 admissible; chain HELD). Two developments: (a) the MOCK
collider is a point mass (implied h≈0) — mock contacts can never
inform the real envelope; only real-sim events count. (b) Phase6l F2
just delivered **11 real-sim contact events at the plane with fresh
vision** (plus F4/F6 singles) — the largest contact-grade harvest we
have. Routed to the analyst into the same pipeline (first-touch rule,
per-tail, provenance ledger). The expiry stays DISARMED (re-arm
conditions unmet: no treated crossings, envelope unsupported).

## 5. Block-B power rider

Control-arm vertical dispersion under the damper is measurable from
cohort-3's control flights; the analyst computes σ′ and re-powers
Block B before it exists, per the rider. Block B remains queued
behind the ladder and a TERM-owning cohort.
