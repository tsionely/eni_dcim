# R1 AUTOPSY — 0/10 gates at defaults; the speed regime was wrong, and the record is now honest

DIAGNOSTIC — engineering note, race week. Not a criterion document.

## What happened

All 10 R1 runs pushed (3ff2cf1..667f313, fixtures/2026072*raceprep-r1-*).
Params verified: A vs B differ ONLY in `planner.terminal.enable` — the A/B
itself was clean. Result: **0 gates passed in all 10 runs, both configs.**

- Config A (terminal=true): 2 aborts "gate clip budget exceeded (11)" in
  recover, 3 environment collisions (hover/recover/search). Median wall
  time 8.9s. Timeline of run 1: takeoff -> RACING, first gate-frame
  contact within ~2.7s, 11 clips in ~3.2s, abort. The drone reaches gate
  1 fast and grinds its frame.
- Config B (terminal=false): 5 environment collisions (search/recover),
  median wall time 17.1s — survives longer, wanders, then hits the
  environment (run 7: 744 env hits, impulse 13.4 — sustained scraping).

## Root cause of the 0/10 — found in params, not in code

R1 flew `planner.commit.speed_mps = 2.5` — the **default** in
config/params_default.json. Every gate pass in the program's history flew
**1.8**, applied as a run patch that never entered the defaults:

| Cohort | Date | commit speed | Gate passes |
|---|---|---|---|
| phase6h-first-enable | Jul 19 | 1.8 | 2 |
| phase6i-r-rate-ab | Jul 19 | 1.8 | 2 (one terminal=true, one =false) |
| phase6k-cohort-2-redo | Jul 20 | 1.8 | 1 (terminal=false) |
| **race-prep R1** | **Jul 21** | **2.5 (default)** | **0** |

The R1 instruction said "do NOT change any other parameter", which
faithfully ran the untuned default. That instruction was the error, and
it was mine. The known-good regime lives in patches; R1b corrects this.

## The larger truth the archive forced

Scanning ALL results in fixtures/: **no run has ever finished the
track** (`finished: true` count: 0 of 166). Best ever: **1 gate**,
achieved 6 times, always at 1.8 m/s, followed by an environment
collision. The competition plan's premise ("the build flies full
R2-TRAINING") was recollection, not record. The plan is amended: the
race objective is MAXIMUM GATES PASSED, built up from a baseline that
reliably clears gate 1.

## R1 verdict under the pre-registered rule

Completion 0/5 vs 0/5 — tie. Tie-break by median time is meaningless
with zero completions. Crash disqualifies: both configs crashed at this
setting. **No winner; the defaults regime (2.5) is disqualified for
both.** Per the ladder logic: back off to the last known-good setting —
1.8 m/s — and re-run the A/B there (R1b, registered in
COMPETITION_PLAN.md before results).

## Standing facts for the week

- The A/B question is genuinely open at 1.8: phase6i passed one gate
  with terminal=true AND one with terminal=false.
- The post-gate-1 problem (environment collision shortly after a pass)
  is the next wall after R1b — no cohort has ever seen gate 2.
- Sakana process note: R1 run dirs carry no code_commit field; R1b
  run-summaries must include the flown commit hash.
