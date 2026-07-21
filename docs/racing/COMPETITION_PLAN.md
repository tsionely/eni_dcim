# COMPETITION PLAN — R2 race, start of next week (owner directive, 2026-07-21)

MISSION: win the race. The acceptance test for every decision this
week is SIM RUNS ON R2-TRAINING — gates passed, then time. No
criterion machinery on race decisions; engineering triage only.
The evaluation-side campaign (mechanism-2 / REG-1 / calibration /
conditional flight) is PARKED intact at its committed state and
resumes after the race. The shadow repair REMAINS SHADOW-ONLY and
is NOT shipped — nothing in this plan touches that law.

## Build and configs

- RACE BUILD = current main (frozen at the plan's commit). Code
  changes this week ONLY for crash-class bugs, each validated by
  3 clean sim runs before re-entering the config.
- CONFIG A: `planner.terminal.enable=true` (the campaign build as
  flown; terminal vertical channel active, known statistical
  drift concern in the final meters).
- CONFIG B: `planner.terminal.enable=false` (legacy path only —
  the pre-terminal build family; hedge against the TERM concern).
- The A/B is decided by DATA, not by the standing statistics
  campaign: the race needs the config that clears more gates,
  faster, this week, on this track.

## Phase R1 — baseline A/B (today + tomorrow)

Sakana: 5 full R2-TRAINING runs per config (10 total). Per run,
report: gates passed / total, wall time, aborts (with phase),
crashes, and push every log (unpushed flights do not exist).
Codex: tally table per config — completion rate, median time,
failure modes by gate.
DECISION RULE (registered now, before results): higher full-run
gate completion wins; tie -> faster median; a crash disqualifies
the config at that speed setting.

### R1 RESULT (recorded 2026-07-21, logs 3ff2cf1..667f313)

0/10 gates, both configs; both crash classes present. Under the rule
above: NO winner — the defaults regime is disqualified for both. Root
cause (docs/racing/R1_AUTOPSY.md): R1 flew the default
commit speed 2.5 m/s; every historical gate pass flew 1.8 via patch.
Archive truth surfaced: no run has EVER finished the track; best ever
is 1 gate (6 times, all at 1.8). Plan premise corrected: the race
objective is MAXIMUM GATES PASSED.

### R1-ALT RESULT (recorded 2026-07-21, logs 423085c..bcd4aa3)

Sakana's self-initiated alternating redo of R1, completed BEFORE the
R1b instruction reached the sim — still at the default 2.5 m/s (headers
confirm: only the terminal.enable patch flown). Data recorded: A
(terminal=true) 1 gate pass in 5; B (terminal=false) 2 in 5; all 10
aborted on environment collision; zero clip-budget aborts this round
(variance vs the first series noted). Combined at 2.5 across both
series: A 1/10, B 2/10. This does NOT decide the A/B (n small, regime
already disqualified) and does NOT replace R1b. Discipline note:
alternation + log-header.json with exact_head_flown adopted — keep.

## Phase R1b — the A/B rerun at the known-good regime (registered before results)

Same protocol as R1 with ONE added patch on both configs:
`planner.commit.speed_mps=1.8`. 5 runs per config, alternating
A,B,A,B,... SAME decision rule as R1, with one amendment registered
now: an abort-without-collision (e.g. clip-budget only) does NOT
disqualify; only a collision-class crash does. If both configs crash
in all runs again, the config with more gate passes, then the one
with fewer collision aborts, is the working baseline for triage — the
week continues on engineering, not on ladder steps. Run-summaries
must include the flown code_commit.

## Phase R2 — speed ladder (days 2-3)

On the winning config, raise speed in registered steps, 3 runs
per step: step 1 approach/dash +15%; step 2 +30%; step 3 commit
band tightening. ANY dropped gate -> back off one step and stay.
The knee of the reliability curve is the race setting.

## Phase R3 — consistency block (day 4)

10 runs at the locked config. Requirement: zero crashes and
completion no worse than the best R1/R2 block. Any regression ->
revert to the last stable setting, rerun.

## Phase R4 — freeze (24h before race)

No changes of any kind inside 24 hours. Race-day checklist:
build hash, config hash, SIM LOCK protocol, one warm-up run.

## Roles

- Sakana: all runs, SIM LOCK discipline unchanged, logs pushed.
- Codex: tally + failure-mode tables per block (replay/CSV only).
- Cursor: fast autopsy of any missed gate (informal, engineering
  notes — no criterion form needed this week).
- Advisory channels: invited to advise on RACE RISK (failure
  modes, config choices, freeze discipline). The parked
  campaign's agenda (ADVISORY-34 F7-F14 and the source round)
  resumes after the race.

## Honest scope notes

- Race-prep flights are COMPETITION OPERATIONS of the build that
  has flown throughout the program, under owner authority. They
  are not cohort-4 evidence flights and mint no release
  statistics; the cohort-4 HOLD and the repair-shipping question
  are untouched and resume post-race.
- If Config A wins the A/B, that is a race decision about THIS
  track and week — not a lift of any statistical gate.
