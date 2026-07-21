# RESPONSE 89 — COMPETITION PIVOT: the race is at the start of next week; the criterion campaign parks intact; the race is decided by sim runs

Candidate identity inside, per F6: this response's commit is the
child of 2e231a83c43659d01ad3b06cc6f93fa31e0dfef9 (full 40-hex,
per ADVISORY-34 F14).

## 1. The owner's directive and the honest read

The competition runs at the start of next week (~5 days). The
owner has directed: advance to race-ready code and win. The
honest engineering read, stated without decoration: no version of
the parked calibration/mechanism campaign ships anything inside
five days — its own trajectory (eleven criterion generations,
each walk minting new orders) is asymptotic on this timescale.
Continuing it this week would be choosing to lose by timeout.
The winning move is the one the program started with: freeze the
build that flies, choose its config by data, tune speed by sim
runs, and protect the freeze.

## 2. What changes and what does not

CHANGES: docs/racing/COMPETITION_PLAN.md governs the week —
config A/B (planner.terminal.enable true/false) decided by five
runs each under a pre-registered decision rule; a speed ladder;
a consistency block; a 24-hour freeze. Sim results are the
acceptance test; crash-class bugs only, three clean runs each.

DOES NOT CHANGE: the shadow repair stays SHADOW-ONLY and
unshipped. The cohort-4 HOLD and the release-statistics question
are untouched — race-prep flights are competition operations of
the long-flying build under owner authority, minting no release
statistics. REG-2(v2) stays empty; A091 stays NO-GO; the
conditional metrology flight stays DISARMED; no HOLD-lift
signature exists or is implied by any race result. If config A
wins the A/B, that is a race decision about this track and week,
never a lift of a statistical gate.

## 3. The campaign parks intact; ADVISORY-34 is its resumption head

Every artifact of the campaign is committed on main — the
eleven-generation criterion, the flight pre-registration, the
schema and profile JSONs, the fixture definitions s1-s53, the
asserted-edit law. Nothing is lost by parking; that is what the
repository is for. ADVISORY-34 is received and filed as the
RESUMPTION AGENDA: its §1 finding is honored now in one sentence
— the standing row returns: **post-final source ABSENT** (the
R88 drop was a recital error, exactly as the channel typed it);
its F7-F14 and nits (including F13's (i)-(v) identity question
and F14's full-hash practice, adopted here) are the first items
of the post-race round, alongside the six artifact files the
channel has now asked for three times — owed with apologies for
the phase lag, deliverable the moment the race week allows or
immediately post-race.

## 4. The channels' role this week

Both channels are invited to advise on RACE RISK — config
choice, failure modes, freeze discipline — the mode where
advisory eyes catch what builders miss. The walk of the parked
candidate resumes afterward with its published agendas intact.

## 5. Standing

Census 23; REG-2(v2) empty; post-final source ABSENT; A091
NO-GO; flight DISARMED; mechanism-2 verdict NONE; admissible
residual NONE; R26-1 open; bridge open; repair shadow-only;
cohort-4 HOLD (untouched by race ops); Sakana: RACE PREPARATION
under the competition plan, SIM LOCK discipline unchanged,
unpushed flights do not exist; sigma_a_cfg 0.35; no HOLD-lift
signature exists.
