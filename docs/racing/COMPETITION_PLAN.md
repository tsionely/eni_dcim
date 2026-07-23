# COMPETITION PLAN — R2 race, start of next week (owner directive, 2026-07-21)

## THE VQ1 TELEMETRY PIVOT (owner directive + organizer email, 2026-07-23)

The organizers re-released the LEGACY VQ1 SIMULATOR WITH FULL
TELEMETRY (sensor outputs, downstream telemetry, state estimation);
the VQ2 sim stays vision-only and also contains the VQ1 track under
VQ2 (no-telemetry) rules. The owner directs: work on TECHNIQUE AND
STABILITY, pass gates on R1 first. Adopted in full. The strategic
read: telemetry is the CALIBRATION INSTRUMENT this program never had
— every estimation defect of the week (velocity amnesia/hallucination,
vertical scatter, frame phantoms) becomes directly measurable against
truth. The race remains vision-only; telemetry grounds development,
never the submission.

Phases (AMENDED by owner decision 2026-07-23: no extra download —
the R1 event inside the installed 3390 sim is the training ground,
vision-only, race-identical rules; T0/T1 telemetry phases SKIPPED,
revivable only if the owner later downloads VQ1):
- T2 R1 GATE TECHNIQUE (active): single-gate pass rate on the 3390
  sim's R1 event ("simple, high-contrast, desaturated" per the
  organizers — detection-friendliest arena). The RELIABILITY GATE
  (>=7/10 gate-1) lives HERE. Baseline block first, then targeted
  technique work driven by its failure profile.
- T3 TRANSFER: the tuned config back on R2-TRAINING, same sim —
  measures the R1-to-R2 gap; the blind-hold flag question re-enters
  here if still open.

### T2-R1 BASELINE RESULT (recorded 2026-07-23, 6 runs to 47523d1)

0/6 gates — but the failure anatomy is NEW and measured:
- BLINDNESS HYPOTHESIS REFUTED: the red-HSV detector sees R1 gates
  richly (500-784 detections/run; full approach->commit->retreat
  cycles). Vision is not the R1 problem.
- NEAR-GATE APPROACHES HAPPEN: run 2 reached 0.77m essentially
  centered (true-world dz +0.04, tx +0.06) and still did not cross;
  runs 1,3 reached 1.0-1.2m with small offsets. The CROSSING itself
  is the unsolved step, not the approach.
- THE HAIR-TRIGGER: 4/6 flights died to "stale channels: imu" that
  is a ~100ms transport HICCUP against safety.imu_stale_s=0.05 —
  at abort the IMU gap was only ~0.1s, streams otherwise alive.
  R2's early collisions masked this; R1's longer flights (median
  32s) expose it. Detections stop 8-16s before these aborts — the
  hiccup lands during long blind searches.

## Phase T2b — level blind crossing + the de-trigger (registered before results)

SEQUENCING CORRECTION (recorded live): T2a turned out to be mid-air
when this registered — it COMPLETES as the single-variable imu-only
control arm (better attribution than the fold). T2b flies after it.
Original fold rationale kept below for the record: ADVISORY-36's
frame (discrete veto) + the crossing autopsy (7cbce47: the stall
drifted +0.47m upward in the final blind 0.5s chasing a fossil dz;
passes arrive near-level with vision to the plane) convict the blind
vertical chase. Adopted config-gated: planner.commit.blind_vz_zero
(RESPONSE91). R1, 8 runs, config B core (1.8 + cap 1.2) +
safety.imu_stale_s=0.25 + blind_vz_zero=true. TWO patches knowingly:
observables are DISJOINT (stale-imu abort class vs crossing
completion) so attribution survives the fold. PREDICTIONS: stale-imu
aborts 0/8; >=2/8 gate passes; blind-window terminal dz toward the
pass band (+-0.12m). FAILURE READ: if vision-to-the-plane remains
the separator and passes stay rare, the next lever is perception
continuity in the last meter (close-tracker band), not control.

### T2a + T2b RESULTS + THE 0.252 FORENSICS (recorded 2026-07-23)

T2a (imu 0.25): **2/6 gates** (first multi-pass block ever), 0 env
collisions, median survival 44.3s — and 6/6 stale-imu deaths.
T2b (adds blind_vz_zero): **2/8 gates**, no gain over control — the
blind-vz-zero lever earned nothing at this n and STAYS default OFF
(prediction ">=2/8" met by the letter at exactly 2/8; the control
comparison is the honest verdict). Codex tally 5a3b96f verified.

THE FORENSICS, four layers deep, all pushed evidence: the IMU
stream is CONTINUOUS to the abort (max inter-arrival gap 0.05s),
timestamps advance to the last sample, the loop never stalled
(max_late 32ms), the bus cell is seq-correct — and the instrumented
watchdog reports the gap as EXACTLY imu(0.252s), six times
identical. And the codebase already knows this disease:
main.py:118 — Windows mock flights "die 10-30% on stale channels:
imu" without a widened threshold; the 0.25 floor was installed for
the mock long ago. VERDICT: a Windows-side delivery artifact in
the 0.25-0.3 band, not a dead sensor — the stream is log-proven
alive at the kill moment.

## Phase T2c — the decisive threshold step (registered before results)

R1, 8 runs, config B core (1.8 + cap 1.2) + `safety.imu_stale_s=0.6`
(blind_vz_zero dropped — no gain measured). THE DISCRIMINATOR: if
stale-imu deaths VANISH -> bounded delivery artifact, runway bought,
the reliability gate is attacked on gates alone; if they RECUR at
imu(0.602s) -> an accumulating starvation exists and the hunt moves
into code with feed-side counters. Risk note: 0.6s on a truly dead
sensor is a training-sim risk only; the race-day threshold is
re-decided at freeze with the artifact's measured band in hand.

## Phase T2a — de-trigger the safety, re-baseline (flying; completes as T2b's imu-only control arm)

Same 6-run block, ONE added patch: `safety.imu_stale_s=0.25` (250ms;
a sim-training tolerance — 5 missed IMU periods at ~100Hz killed
flights, 25 is a real fault). PREDICTIONS: stale-imu abort class ->
0/6; median survival rises; commit attempts per flight rise; >=1
gate pass in 6. FAILURE READ: if crossings still never complete from
sub-1m centered approaches, the next target is the final-meter
mechanics (commit window/brake/abort corridor) with the R1 arena as
the clean lab.
R1k (3390 blind-hold A/B) is PAUSED, not canceled — it re-enters at
T3 if the flag question is still open. All prior plan sections below
remain the record; the reliability gate transfers to T2.

R1K PARTIAL RECORD (5 of 10 flown, stopped by Sakana honoring the
pause mid-block — correct precedence, plan over chat): OFF runs
1,3,5 -> gates 0,1,0 (run 3: THE FIRST GATE PASS ON 3390, impulse
14.8 abort after); ON runs 2,4 -> gates 0,0. All environment
collisions. Note for T1: survival times on 3390 (21-30s) run longer
than the 3385-era band (8-17s) — worth a truth-referenced look at
what changed. No A/B conclusion from n=5; the flag question moves
to T3 as registered.

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

### R1e RESULT + RECORD CORRECTION (recorded 2026-07-22)

R1e (blend 0.9): **0/5**; all three registered predictions FAILED
(bias medians per run +0.73/+0.79/+1.93 in three runs — WORSE, not
collapsed; closest ty -0.733 — worse; 0/5). Codex's independent
tally (97932b8) agrees. Registered branch read applied: the high
blend passes detector jitter straight into the estimate. **blend
reverts to 0.6; R1e's lever is dead.**

RECORD CORRECTION, entered by name: the "vertical finding" and all
camera-frame ty numbers in the R1b/R1c/R1d records above are
FRAME-CONTAMINATED. rel_pose is mount-corrected but still attitude-
and rest-tilt-rotated; the codebase's own fossils (approach.py
true_world_dz docstring; phase3h: 49 of 88 "LOW" labels were truly
HIGH) warn about exactly this phantom, and I walked into it anyway.
Recomputed at closest approach with the flight code's own
true_world_dz (state-paired q_att/level_*):

  R1-ALT 2.5:   median +0.10m HIGH, per-run spread -1.49..+1.36
  R1b 1.8:      median  0.18m low,  spread -1.29..+0.96
  R1c old:      median  0.18m low,  spread -1.04..+0.50
  R1d cap1.2:   median  0.14m low,  spread -0.81..+0.33
  R1e blend0.9: median +0.26m HIGH, spread -0.56..+2.99

THE REAL PICTURE: there is NO large systematic vertical bias. The
enemy is VARIANCE — ±1-1.5m run-to-run vertical scatter against a
0.8m half-height ring. Passes are the runs where scatter lands
inside. The align "descend while low" observation dissolves in the
same correction (align acts on true_world_dz — its frame was right;
my metric's was wrong). R1d's 1/5-vs-0/5 outcome and its
commit-entry closure stand as outcome data; the cap-1.2 patch is
kept (weak positive, no observed harm).

## Phase R1f — the terminal A/B at the tuned regime (registered before results)

Final-meter scatter is precisely what the GateCloseTracker + the
terminal vertical channel were BUILT to null — and the terminal A/B
is the plan's original R1 question, now askable at the tuned regime.
Sakana: 10 runs alternating A,B,A,B,... ALL at speed 1.8 + cap 1.2 +
blend 0.6 (default); A adds terminal.enable=true, B =false. B doubles
as R1d replication. DECISION: the original R1 rule (more gate passes
wins; collision-aborts tiebreak against; clip-budget aborts do not
disqualify). PREDICTION registered: if the terminal channel does its
job, A shows smaller |true-world dz| scatter at closest approach and
a higher pass rate than B. Codex tally adds a true-world dz column
(the align/commit bias metric is retired with the correction).

### R1f RESULT + THE ENGAGEMENT FAMINE (recorded 2026-07-22)

R1f: **0/10, both configs** (A: 2 clip-budget + 3 collision; B: 4
collision + 1 grinding timeout, 18,661 env hits — second instance of
that class). Decision rule: tie at zero again. But the validity
check found the real story: **config A was never meaningfully A.**
term_status audit across R1f-A: the terminal channel ENGAGES
logically (38-106 ticks/run) but `term_command_applied` was zero in
4 of 5 runs. Application follows OWNERSHIP; ownership follows the
admission door (vertical_owner.py: certified + ready + FULL_QUAD,
then |e_x| + 2*sigma + 0.06 <= corridor_interim 0.30). Measured
admission scores: clustered at ~0.65 (= the 0.45 e_z clamp + margin
— the believed crossing error saturates its clamp), vs corridor
0.30; pass fraction 0.00 in 4 runs; run 9 dipped to 0.262 -> 18
owner=term ticks, command applied. The door is working as designed —
and the design (ratified conservatively in the advisory era) admits
only crossings that are already nearly good. The rescue channel
declines exactly the flights that need rescuing. The entire week's
A/B was therefore A≈B, explaining every tie.

## Phase R1g — corridor experiment (registered before results)

Config A + `--patch planner.terminal.corridor_interim_m=0.7` (admits
the measured ~0.65 typical scores), with speed 1.8 + cap 1.2.
5 runs, A-only; control = R1f-A (corridor 0.30, 0/5, 2 clip-aborts).
PREDICTIONS registered: owner=term ticks appear in >=4/5 runs; the
harm channel to watch is clip-budget aborts rising (TERM misacting
near the frame); success = >=1 pass or median |true-world dz| at
closest approach shrinking vs R1f-A. Registered scope note: this is
a race-ops config patch under owner authority; the shadow repair
stays unshipped; no release statistics are minted; the criterion
campaign's HOLD is untouched.

### R1g RESULT + THE A/B CLOSED + THE AUTOPSY PIVOT (recorded 2026-07-22)

R1g (corridor 0.7, A-only): **0/5, all environment collisions, zero
clips** (the registered harm channel stayed silent). Prediction
FAILED: owner=term in only 1/5 runs (run 5: 26 owned+applied ticks,
admission min 0.65 <= 0.70 — the corridor lever works when reached).
In 4/5 runs there was not a single engaged+ready tick: the binding
famine is UPSTREAM — the FULL_QUAD certified-identity + oracle-ready
preconditions — and that is perception-side, not openable by config.

**A/B DECISION (race): CONFIG B.** Not because B beat A — every
block tied at zero — but because A cannot be made real this week:
the terminal channel's identity famine caps ownership at ~1 run in
5 regardless of corridor. The race flies the simpler equal
performer. (Registered honestly as an engineering closure of the R1
question, not a decision-rule victory.)

CURSOR'S POOLED AUTOPSY (56 fixtures, analysis/
2026-07-22-pooled-collision-geometry/): the dominant killer is
BLIND WANDERING INTO STRUCTURE after losing the gate — 17
NO_GATE_IN_VIEW + 6 far-hangar of 54 aborting hits, in
search/recover; second cluster near-gate structure while locked
(10+6, low/floor outnumbering top when in view); explicit gate-clip
aborts only 8 (top bar 3 > bottom 1). The grinding class (2 runs)
presses against far structure at threat level 1, which never aborts
(threshold 2), until timeout. The gate frame is NOT the main enemy;
losing the gate at speed is.

## Phase R1h — slow-blind survivability (registered before results)

The autopsy's lever: don't fly fast blind. Config B, 10 runs (the
5-run blocks have repeatedly fooled us — n doubles):
  planner.commit.speed_mps=1.8, planner.commit.vz_cap_mps=1.2 (kept)
  planner.approach.speed_far_mps=1.5   (from 3.0 — the blind-fast phase)
  planner.approach.speed_near_mps=1.0  (from 1.5)
  planner.retreat.speed_mps=0.8        (from 1.2 — blind by design)
PREDICTIONS registered: the blind-structure abort class (17+6/54
pooled) shrinks as a fraction; median survival time rises; more
commit attempts per flight survive; pass rate >= 2/10. Failure
read: if passes do not rise despite longer survival, the arrival
scatter itself is the residual wall and the next step is a
perception/consistency lever, not speed.

### R1h RESULT + THE PHANTOM-HOVER MEASUREMENT (recorded 2026-07-23)

R1h: **1/10** (prediction >=2/10 FAILED); blind-structure deaths
GREW to 7/10 (vs 1 in R1f-B); survival rose (14.5s median); arrivals
when they happened were nearly centered (true-world dz median
-0.086m within 2.5m). Codex tally e492f0b verified. The slow-blind
lever INVERTED: drift accumulates with TIME, and slowing doubles
blind time. Approach speeds revert to defaults (far 3.0 / near 1.5).

THE DECISIVE MEASUREMENT: in the final 2s before the killing
collision, commanded horizontal speed = 0.00 in 9/10 runs — search
phase, gate age stale/infinite, the planner commanding hover — and
the vehicle translates into steel anyway. Mechanism named: when
vision velocity disappears, estimation.vel_leak (0.05) decays the
velocity estimate to zero; the controller believes it is stopped
while the real velocity carried from the last maneuver glides on
unopposed. PHANTOM HOVER. This, not gate geometry, is the
program's dominant killer (7/10 here; 23/54 pooled).

## Phase R1i — estimator amnesia test (registered before results)

Config B at the best-measured regime (R1d: approach defaults,
commit 1.8, cap 1.2) + `--patch estimation.vel_leak=0.01` (5x less
amnesia — the controller keeps believing its IMU-integrated
velocity when blind, and therefore actually brakes it). 10 runs.
PREDICTIONS registered: blind-structure death class shrinks vs
R1h's 7/10 AND vs R1d-era rates; pass rate >= 2/10. FAILURE READ
registered: if blind deaths persist with commanded-zero mechanics
intact, the drift source is attitude-bias not velocity amnesia, and
the next candidate is the CODE-CLASS brake (counter-velocity pulse
on search entry from last-known vision velocity) under the plan's
crash-class rule: it targets the measured dominant crash mechanism,
with 3 clean validation runs before entering any config.

### R1i RESULT + THE ESTIMATOR'S TWO FAILURE MODES (recorded 2026-07-23)

R1i (vel_leak 0.01): **0/10** — prediction failed, and the death
profile INVERTED: believed velocity at death 0.7-6.05 m/s (run 9
believed 6 m/s), deaths moved from blind search into ACTIVE phases
(takeoff/align/commit), median survival DROPPED to ~9.6s. Named:
leak 0.05 = AMNESIA (phantom-hover glide on forgotten velocity);
leak 0.01 = HALLUCINATION (runaway IMU integration the controller
fights). The horizontal velocity estimate has no truth anchor when
the gate is not close; no leak value fixes both ends. vel_leak
reverts to 0.05.

## THE CRASH-CLASS FIX — blind_hold (code, 2026-07-23)

Under the plan's registered rule (code changes for crash-class bugs
only, 3 clean validation runs): the dominant measured crash
mechanism (23/54 pooled, 7/10 R1h — blind glide into structure on a
zero command) is severed at the actuation end. Setpoint gains a
`blind_hold` flag; the gate-is-None search setpoints raise it (the
retrace variant, which commands real known-clear motion, does NOT);
the attitude backend on blind_hold stops chasing the horizontal
velocity estimate entirely — LEVEL attitude hold, drag brakes the
vehicle, yaw spin and the vertical loop keep their authority,
horizontal PID integrators reset. Files:
src/aigp/core/messages.py, src/aigp/planning/race_planner.py,
src/aigp/control/attitude_rate_backend.py; tests
tests/unit/test_attitude_rate_backend.py (5, incl. the
fiction-independence assertion: identical commands whether the
estimator believes 0 or 3 m/s) + 3 planner-side flag tests. Full
unit suite 229 green.

## Phase R1j — the blind-hold validation block (registered before results)

Sakana, in order:
1. VALIDATION TRIO: 3 runs, config B, patches ONLY commit 1.8 +
   cap 1.2 (all-default estimator). Clean = no new abort class, no
   ground contact in search, teleme try shows blind_hold=true ticks
   in any search stretch. Any non-clean run -> STOP, report, the
   fix does not enter the config.
2. If trio clean: 10-run block, same config. PREDICTIONS registered:
   blind NO_GATE_IN_VIEW death class < 3/10 (was 7/10 in R1h-era
   profile and 17+6/54 pooled); grinding class 0; pass rate >= 2/10;
   commit attempts per flight rise (retries survive the searches).
FAILURE READ: if blind deaths shrink but passes do not rise, the
remaining wall is arrival scatter and the freeze decision is made
on the best measured config as-is.

### R1j VALIDATION AMENDMENT (2026-07-23, spec repair, registered
before any further validation flight)

Validation run 1 (be1c5a0) stopped the trio CORRECTLY under the
letter of the protocol and exposed a defect in the protocol's own
clean-definition: it demanded blind_hold ticks in search from a
flight that aborted (known class, gate-clip budget, 7.76s) before
any search stretch existed — a vacuous condition, not a mechanism
failure. Field verification: blind_hold serializes in all 389
setpoint records (false, correctly — no search occurred); no new
abort class; no harm. AMENDED DEFINITION, registered now:
- A validation run is HARM-CLEAN if: no new abort class, no
  collision during a blind_hold stretch, no ground contact in
  search. (A run with no search stretch can be harm-clean.)
- A validation run is MECHANISM-EXERCISING if it contains a search
  stretch with blind_hold=true ticks.
- The trio COMPLETES when 3 harm-clean runs exist of which >=1 is
  mechanism-exercising. Any harm -> hard stop, fix does not enter.
- Cap: 6 validation runs total; if the cap is hit harm-free but
  search never occurred, stop and report (that itself is data).
Run 1 counts as harm-clean #1. This is a spec repair, not a
retry-for-outcome: no run is discarded, and the harm bar is
unchanged.

## SIM-UPDATE PROTOCOL (2026-07-23, owner notice: simulator update issued)

The owner reports a simulator update, being uploaded to Drive. Until
it is examined and installed:
1. ALL FLIGHTS HOLD — including the amended R1j validation. Runs on
   the pre-update sim no longer inform the race if the race runs on
   the updated sim.
2. On installation: verify sim version/build in the log headers;
   then RE-BASELINE — the amended R1j validation trio first (same
   harm/mechanism definitions), then a 10-run block on the
   best-known config (B, 1.8 + cap 1.2, blind_hold build). Compare
   the failure profile against the old-sim pooled data; carry over
   only re-confirmed conclusions.
3. Every pre-update measurement in this plan is marked OLD-SIM ERA
   evidence. Decisions stand, but their evidentiary weight on the
   new sim is zero until re-confirmed.
4. If the update ships patch notes, they are read FIRST — physics,
   track, and interface changes reprioritize everything above.

OLD-SIM-ERA NOTE: validation run 2 (ccc5fe8) was airborne before
the hold reached the sim. Recorded honestly: MECHANISM EXERCISED —
105 blind_hold=true ticks, all in search, the new code path's first
flight — with 1 gate passed and the week's richest flight (20.9s,
second commit attempt reached); AND one collision occurred during a
blind_hold stretch, which fails the registered harm-clean letter.
The definitions are NOT amended post-hoc. Entry adjudication moves
wholesale to the v1.0.3390 re-baseline trio under the same
unchanged definitions; run 2 is old-sim-era evidence only.

IDENTIFIED (2026-07-23): the update is "AI-GP Simulator
v1.0.3390.zip" (2.0 GB, Drive). Installed base is v1.0.3385 (the
version the velocity_backend frame probe and ALL 100+ archived runs
were measured on). INSTALL ORDER: extract to a NEW directory
alongside 3385 — never overwrite. INVENTORY before any flight:
version strings, changed-file diff vs 3385 (names, sizes, hashes),
any README/CHANGELOG/notes inside the zip — pushed to the repo
before the first 3390 flight.

INVENTORY READ (2026-07-23, 82d1b5e): the 3390 diff is MICRO —
DCGame exe +2,560 bytes, the 4.5GB content pak -2,048 bytes; no
patch notes shipped; outer README unchanged (June 26, still names
example v2). Profile of a point fix, not a physics/track overhaul —
unverified until flown. THE open interface question: the pilot
example jumped v2 -> v4 (requirements unchanged: pymavlink/opencv/
numpy). ORDERED: both example source trees committed and diffed
before any flight; the trio releases only after the interface diff
reads clean (or after adaptation if it does not).

INTERFACE DIFF VERDICT (2026-07-23, trees at 2c23a95): the pilot
example v2->v4 diff contains ONE semantic change — sim revision 3390
adds an OPT-IN extension bit (SET_ATTITUDE_TARGET.type_mask bit 16,
"DCL_BODY_RATES_RADS"): set -> body rates interpreted as true
physical rad/s; unset -> legacy behaviour preserved. All other
example files identical. Our io layer sends only
ATTITUDE_TARGET_TYPEMASK_ATTITUDE_IGNORE (bit 7) — bit 16 unset —
so the build gets LEGACY behaviour on 3390 automatically.
DECISION: the race flies LEGACY (no opt-in) — every tuned sign and
gain in the att_rate cascade was calibrated against legacy; opting
in days before the race is a retune the freeze forbids. The opt-in
(a saner physical interface that officially confirms our phase2a
inverted-pitch measurement was a SIM defect) is filed as the first
POST-RACE improvement. No code change required.
**FLIGHTS RELEASED: the amended R1j validation trio flies on 3390.**

ROLLBACK STATUS AMENDED (owner report, 2026-07-23): 3385 is no
longer downloadable from the competition site and no
allowed/forbidden statement exists. REGISTERED ASSUMPTION: the race
runs on v1.0.3390. 3385 is retained as LOCAL DIAGNOSTIC ARCHIVE
ONLY — comparison runs and regression triage — never a race-day
option: flying a version the organizers withdrew is a
disqualification risk taken blind. All tuning, validation, and the
freeze target 3390 from here on.

### R1j-3390 TRIO VERDICT + THE GATED CONSEQUENCE (2026-07-23)

The 3390 launch chain works end-to-end (val-run2: PID-based window
discovery, event templates 1.000, RACE click, race GO, live IMU,
RACING). Val-run1: harm-clean, non-exercising (the missing RACE
click — orchestrator defect, fixed at 07695a7). Val-run2: mechanism
exercised in real flight (125 blind_hold search ticks) AND the first
collision occurred inside a blind_hold stretch — **NOT harm-clean by
the registered letter. Sakana's hard stop honored: THE TRIO FAILED;
the fix does not enter the default config.** No post-hoc amendment.

CONSEQUENCE EXECUTED literally: blind_hold is now CONFIG-GATED,
default OFF (`planner.search.blind_hold_enable`, params_default
false; race_planner gates all three flag sites; planner tests updated
— default-off asserted, enabled-path asserted; suite 230 green).
The default build behaves pre-fix; the mechanism remains available
under an explicit patch for outcome-judged evaluation.

## Phase R1k — 3390 baseline A/B on the blind-hold flag (registered before results)

The race-config decision on the race sim, judged by OUTCOMES (the
per-tick harm letter served its purpose in validation and is not the
race criterion). 10 runs, config B core (1.8 + cap 1.2), alternating:
  odd runs  FLAG OFF (default — pre-fix behavior)
  even runs FLAG ON  (--patch planner.search.blind_hold_enable=true)
DECISION RULE (registered now): more gate passes wins; tie -> fewer
collision aborts; tie -> longer median survival; clip-budget aborts
do not disqualify. The winner is the RACE CONFIG for the freeze path
(reliability gate still governs any speed work). This block doubles
as the 3390 baseline for the reliability-gate assessment.

## RELIABILITY GATE (owner question, 2026-07-22, binding)

The owner asked the right question: no speed work while gate 1 is
unreliable. REGISTERED AS A HARD GATE: the speed ladder (R2 below)
is LOCKED until BOTH hold in a 10-run block at the frozen config:
  (a) gate-1 passage in >= 7/10 runs;
  (b) at least one run passes gate 2.
Until then the week's work is reliability only, in this order:
gate-1 scatter (R1f), then the post-gate-1 collision (no run in
program history has ever seen gate 2). Slow-and-through beats
fast-and-crashed: scoring is gates first, time second.

## Phase R2 — speed ladder (days 2-3) [LOCKED behind the reliability gate]

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
