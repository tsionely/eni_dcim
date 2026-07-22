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

### R1b RESULT (recorded 2026-07-22, logs ea7af54..f7d9089)

Flown CORRECTLY (headers confirm both patches, 1.8 + A/B). Result:
**0/10 gates — zero passes, both configs** (A: 4 collision aborts + 1
clip-budget; B: 5 collision aborts). Worse than the disqualified 2.5
series (3/10 passed gate 1). Decision-rule output: tie at zero — the
A/B question is SUSPENDED; the signal is build-level, not config-level.

Root-cause hypothesis (registered): every historical gate pass flew
build 46e9a64 (Jul 20 morning). Since then 21 flight-code commits
(~950 lines: race_planner +155, vertical_owner +574, perception
pipeline +81, app.py, close_tracker, certificate) landed and NONE flew
until R1b. Config B's collapse implicates shared-path changes, not the
terminal channel alone. Competing hypothesis: day-to-day sim drift.

## Phase R1c — bisect anchor flight (registered before results)

One experiment decides between the hypotheses: fly the LAST
GATE-PASSING BUILD, today, at the same setting.

Sakana: checkout 46e9a644ef4e24a5229a74a49b0ba33b73c1bb80 (pushed
ancestor — "unpushed flights do not exist" is satisfied), 6 runs at
`planner.commit.speed_mps=1.8`, alternating terminal.enable
true/false as before. PREDICTIONS registered now: if >=1 gate pass in
6 -> regression is inside the 21-commit window -> bisect it (each step
~5 runs; ~4 steps bound it). If 0/6 -> the build is not the cause ->
environment/sim-drift triage. Either way the race build question
reopens: the frozen build may move to the last gate-passing lineage.
Crash-class triage under the plan's own rules; no criterion machinery.

### THE VERTICAL FINDING (recorded 2026-07-22, computed from raw logs)

Measured across all 20 race-week runs (R1-ALT + R1b): the drone
arrives at the gate BELOW center in 20/20 runs (camera-frame ty at
closest approach: -0.07..-1.50 m; lateral tx small, mixed sign — the
lateral axis is healthy). All three gate passes were the runs with
the smallest vertical deficit (0.19-0.55 m). At COMMIT ENTRY the
deficit is 0.8-4.7 m (every run, every entry). The legacy commit
vertical damper (`planner.commit.vz_cap_mps=0.35`, new in the
21-commit window, active in BOTH configs — race_planner.py
`_damp_commit_vz`) allows closing at most ~0.9 m during a full
commit. Arithmetic: a centered arrival is impossible unless align
hands over nearly-closed; align phases observed at 0.3-1.5 s exit
with the deficit still open. Codex's approach-time collapse and the
build-identity check (R1-ALT and R1b flew IDENTICAL src/config —
verified by tree diff) are consistent with this.

## Phase R1d — commit climb-authority A/B (registered before results)

On CURRENT main, config B only (terminal off, pure legacy path),
speed 1.8: 5 runs with `--patch planner.commit.vz_cap_mps=1.2`.
Control = the five R1b-B runs (cap 0.35) already flown. PREDICTIONS
registered now: if the cap is the binding wall, the vertical deficit
at closest approach shrinks and >=1 gate pass appears in 5; if
results are unchanged, the wall is upstream (align handover / the
vertical estimate) and the triage moves there. Config patch only —
no code change, freeze intact. Runs sequence AFTER R1c.

### R1c RESULT + the two-layer vertical truth (recorded 2026-07-22)

R1c (old build 46e9a64 at 1.8, logs d15a032..30dc261): **1/6 gate
passes** (A-run5). The registered prediction fired (>=1 pass ->
window implicated) but the honest strength note is recorded with it:
1/6 vs the new build's 0/10 is statistically weak, and the old build
ALSO arrives low (ty at closest -0.18..-1.34) with the same 0.7-4.3m
commit-entry deficits. B-run4 anomaly: 120s flight timeout with
18,551 env hits (sustained grinding) — logged as its own failure
class. The low-arrival pattern is NOT new-build-specific.

Estimate-vs-measurement audit (state.gate_rel vs detection rel_pose,
paired within 0.3s, medians over align/commit ticks): in some runs
the fused vertical estimate is OPTIMISTICALLY biased 1-2m (deep-fail
R1b-B-run4: believed -0.36m low during commit while measuring -2.58m;
R1b-B-run2: -1.10 vs -2.02); in others the bias is ~0 (R1b-A-run5
+0.01; old-build pass R1c-A-run5 +0.06). BOTH builds show instances.
Two stacked defects, now named:
  (1) VERTICAL ESTIMATE sometimes lies optimistically during
      align/commit (both builds — the deeper, older wall; likely why
      the historical rate never beat ~28%);
  (2) the new 0.35 commit vz cap blocks closure even when the
      estimate is honest (new build only — R1d's target).

R1d CODICIL (registered before R1d results): R1d (cap 1.2) is
predicted to recover closure in honest-estimate runs only. Partial
improvement with low-arrival residuals = defect (1) is the remaining
wall, and the next lever is estimate-side (e.g. vision_blend), config
first, code only if unavoidable (crash-class justification required).

### R1d RESULT (recorded 2026-07-22, logs after fc093a7)

Flown correctly (cap 1.2, speed 1.8, config B; params verified).
**1/5 gate passes** (run 4) vs control R1b-B 0/5. The registered
codicil's "partial improvement" branch FIRED: climb authority
restored closure where the estimate is honest (run 4's successive
commit entries -2.48 -> -0.70 show deficits being closed between
attempts), but median closest-approach ty did NOT shrink (-0.600 vs
control -0.532) — in lying-estimate runs the drone still doesn't
know to climb. Per the codicil: the remaining wall is defect (1),
the estimate; the next lever is estimate-side, config only.

## Phase R1e — vision-blend estimate fix (registered before results)

Mechanism: estimation.vision_blend (default 0.6) is the per-detection
position-fix blend (state_estimator.py _apply_position_fix: fused =
0.6*measured + 0.4*transported-old). The optimistic 1-2m bias lives
in the transported term; 0.9 snaps the estimate to the measurement.
Sakana: 5 runs, config B, speed 1.8, cap 1.2, PLUS
`--patch estimation.vision_blend=0.9`. Control = R1d (blend 0.6).
PREDICTIONS registered now: (a) the paired est-vs-meas vertical bias
(state.gate_rel ty minus detection ty) collapses toward 0 in all
runs; (b) median closest-approach ty improves toward -0.3 or better;
(c) pass rate >= 2/5. Branch reads: (a) fires but not (b)/(c) ->
residual is control/aim side; (a) does not fire -> the bias is
transport-side (next levers: vision_vel_blend, vel_leak). Known
accepted risk: less jitter smoothing at high blend — the commit
damper absorbs it at 1.8.

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
