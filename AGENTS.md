# Agent Runbook — Local Agents

## DEFINITION OF DONE — ALL ROLES

A task is done ONLY when your commit exists on **origin/main**. Verify after
every push:

    git log origin/main --oneline -1     # must show YOUR hash

Unpushed work does not exist for the team (three agents have now lost cycles
to this). If push is rejected: `git pull --rebase origin main` then push
again. The remote default branch is `main` — never `master`.

## SIM LOCK — one operator at a time

Exactly ONE agent may touch the real simulator at any moment (a duplicate
sim instance cost us all of Phase 1's measurements). Before starting any
real-sim cycle, whoever holds the operator role MUST:

1. Check the machine-level lock: if `C:\Temp\eni_dcim_sim.lock` exists and
   its owner process is alive — do NOT proceed; report instead.
2. Take it: `Set-Content C:\Temp\eni_dcim_sim.lock "<role> <PID> <timestamp>"`.
3. Release it when the cycle ends (delete the file), even on failure.

Agents in non-operator roles never launch, reset, click, or command the real
sim — regardless of the lock.

Three local roles are defined. State clearly in your commit messages which
role you act as. All coordinate with the cloud agent through git on `main`.

- **SIM OPERATOR** (Sakana): operates the simulator, runs probes and
  flights, collects fixtures. The operator runbook is the last section.
- **DATA ANALYST** (Cursor): works ONLY on recorded data — see below. Never
  runs the simulator while the operator is mid-cycle; never edits code,
  config, docs, or the operator's fixtures.
- **QA & MOCK-TUNER** (Codex): tests and tunes against the MOCK sim only —
  see below. Never touches the real simulator or the operator's cycle.

## QA & MOCK-TUNER role (Codex)

Mission: use spare CPU between real-sim cycles to (a) verify the pilot on
Windows and (b) pre-tune the att_rate cascade with mock campaigns — dozens of
flights per hour vs. one real race at a time.

Ground rules: write ONLY under `tuning/` (create it) and never modify
`src/`, `config/`, `simtools/`, `tests/`, `docs/`, or `fixtures/`. Runtime
parameter experiments go through `--patch` / campaign bounds, never config
edits. Commit prefix `[tuning]`. Suggested code/test changes are written as
unified diffs into `tuning/proposals/*.diff` + rationale — the cloud agent
reviews and applies.

Environment notes (from your first CI run):
- Your checkout lives under OneDrive — the `WinError 5` temp failures are
  OneDrive/AV file locking, not code bugs. **Re-clone OUTSIDE OneDrive**
  (e.g. `C:\dev\eni_dcim`) and run pytest with an explicit temp dir:
  `python -m pytest tests -q --basetemp=C:\Temp\pytest-eni`.
- Your commit af88a69 never reached origin — remember `git push` after
  committing (rebase if rejected, per the operator's flow).

Standing tasks:
1. **Windows verification**: `python -m pytest tests -q --basetemp=C:\Temp\pytest-eni`
   after every `git pull` of a cloud commit; report failures with full output
   in `tuning/windows-ci.md` (append per commit hash). The suite has only
   ever run on Linux — you are our Windows CI.
2. **Mock tuning campaigns**:
   `python scripts/run_campaign.py --flights 40 --optimizer cem --sim mock`
   (repeat with different seeds/optimizers). Copy `logs/results.sqlite` and a
   summary (best params per campaign, score progression) into
   `tuning/campaigns/<date>/`. Focus bounds: the att_rate gains + approach
   params in `DEFAULT_TUNE_BOUNDS` (src/aigp/main.py).
3. **Robustness hunts**: long mock runs hunting flakes — hover 10x
   (`aigp --mode mock` repeatedly), report any abort that is not
   "max duration" with its flight log attached.
4. **Review reports** (optional, read-only): findings on the pilot code go in
   `tuning/review-<date>.md` — flag, don't fix.

### CURRENT TASK: re-baseline v5 — never-sleep loop + FSM isolation

v4 found the real flaw in v3's fix: RateLoop still slept the last
sub-2.5ms stretch, and on your Windows ANY positive sleep costs a full
15.6ms tick — hence byte-identical overrun_frac. The loop now sleeps
ONLY when the wait exceeds a full timer tick and spins everything
shorter (costs CPU on win32; correctness first). Your campaign-side win
is already proven: stale-imu 0/4 with the auto-relax.

When the SIM LOCK clears:
1. **FSM isolation first**: run the two new failures 5x each, isolated:
   `python -m pytest tests/unit/test_fsm.py -q` (x5). They pass 5/5 on
   Linux; we need to know deterministic-vs-flaky on your box. If they
   fail deterministically, paste the FULL -vv assertion context into
   tuning/windows-ci.md — that's a real Windows bug I want.
2. CI full run (hover overrun now informational on win32 anyway).
3. Campaign 40 with the guard; --low-load fallback if needed.

### PREVIOUS: re-baseline v4 (found the sleep-floor flaw — good measurement)

Your v3 before/after (identical overrun_frac to 4 decimals) proved
timeBeginPeriod is a no-op on your Windows — modern timer coalescing
ignores it for background processes. This build goes deeper:
- process power-throttling opt-out (SetProcessInformation) + winmm
- RateLoop on win32 now SPINS the last 2.5ms instead of trusting sleep
- mock campaigns auto-relax safety.imu_stale_s to 0.25 (harness
  artifact, same as tests) — your stale-imu guard aborts should drop
- the hover overrun assertion is now Linux-only: Windows CI's verdict
  is chain correctness; report overrun_frac as telemetry, not pass/fail

Same drill when the SIM LOCK clears: CI before/after numbers, then the
campaign with the guard. If stale-imu STILL exceeds 10% after all this,
run the campaign with --low-load and note it — that machine's ceiling
is what it is, and campaign THROUGHPUT matters more than fidelity.

### PREVIOUS: re-baseline v3 (timer no-op diagnosed — good measurement)

Your v2 run diagnosed itself perfectly: overrun_frac 0.74 + heartbeat
timeouts + chronic stale-imu are all one root cause — Windows' default
15.6ms timer granularity vs our 4ms loop. The pilot now requests 1ms
timer resolution process-wide (aigp.core.scheduler, winmm
timeBeginPeriod). Re-run on the new HEAD when the operator's SIM LOCK
clears:

1. Windows CI: expect overrun_frac and the heartbeat timeouts to drop
   sharply. Report before/after numbers — this quantifies the fix.
2. Campaign with the same contamination guard (>10% stale-imu aborts
   the measurement — it worked exactly as designed in v2, keep it).
3. Your v2 default-verification glimpse (4 gates, one 2-gate finish,
   under 30% contamination) suggests the pilot is capable on Windows
   too — v3 should give the first clean Windows baseline.

### PREVIOUS: re-baseline v2 (2026-07-15, invalidated by its own guard —
### root cause fixed, see above)

Your 2026-07-15 re-baseline was received — good guard discipline on the
FlightSim detection. Its verdict is however OBSOLETE: it measured commit
5ec57ee (pre live-steered-commit), 25% of campaign flights died on
"stale channels: imu" (machine contention), and your own verification
showed best==default==0/20 — i.e. the CEM result was noise-fit. The
suggested patch is REJECTED (cloud re-ran your exact 2-gate track on
e8098e2: 4/4 first-gate, 3/4 FULL-TRACK finishes). Redo on current code:

1. Windows CI on e8098e2+, CLEAN machine (no FlightSim, nothing heavy):
   the 4 failures you saw (hover overrun 0.74, 3 heartbeat timeouts) need
   a clean-run verdict before we treat them as Windows bugs.
2. Campaign as before but: verify HEAD >= e8098e2; ABORT and restart the
   measurement if >10% of flights show "stale channels: imu"; log CPU
   state per batch. Expect nonzero finish rates now — if default gives 0%
   finishes on the 2-gate track, that itself is the P0 finding.
3. Keep the FlightSim guard exactly as you ran it.

### PREVIOUS: re-baseline (2026-07-15, superseded — see above)

docs/07 flipped the sensor model; the mock is now FAITHFUL to the real sim
(inverted gyro reporting, frozen z-gyro, straight commands, body-fixed
camera, epoch frame timestamps) and defaults changed. Your old campaign
results are obsolete — re-baseline everything:

1. **Windows CI first**: pull, `python -m pytest tests -q
   --basetemp=C:\Temp\pytest-eni` — the suite is 70/70 x3 on Linux; you are
   the Windows verdict. Report in `tuning/windows-ci.md`. Note
   test_single_gate_pass has a one-retry policy by design (~90% per-flight).
2. **Mock campaign, new defaults**: 40+ flights, CEM, bounds around the NEW
   defaults — most valuable axes now: `planner.approach.aim_up_m` (0.1-0.6),
   `planner.commit.distance_m` (1.5-3.5), `planner.commit.duration_s`
   (1.0-2.0), `estimation.vision_vel_blend` (0.1-0.3),
   `control.att_rate.vz_p`/`vz_i`. Score per docs/04. Report best-vs-default
   gate-pass rate over >=20 verification flights each.
3. **Flake hunt on the gate flight**: `--sim mock` single-gate flights x30,
   log every failure signature (timeout-in-THROTTLE_DOWN should be GONE —
   if you see one, that's a P0 report).

## DATA ANALYST role (Cursor)

Mission: exploit the large local recordings that never reach the cloud agent
(logs/*/vision.aigprec and recordings/*.aigprec, 0.6-1.3 GB each — the repo
only carries small slices).

Ground rules: write ONLY under `analysis/` (create it; it is committed) and
`fixtures/` (via `scripts/collect_artifacts.py` conventions). Commit prefix
`[analysis]`. Read-only everywhere else. Keep every committed file < 50 MB.

Standing tasks (in priority order, redone as new recordings appear):
1. **Detector evaluation at scale**: run the repo detector
   (`aigp.perception.gate_detector_hsv` via `aigp.main --mode replay` or your
   own harness reusing `ChunkAssembler`) over EVERY local recording; report
   per-recording: frames, detection rate, PnP-solve rate, distance/center
   stability, and — most valuable — save the N *hardest* frames (missed or
   low-confidence) as downscaled JPEGs under `analysis/hard_frames/`.
2. **Interesting-moment slices**: extract 20-40 MB slices around events
   (race GO, gate approaches, DSQ moments) with `scripts/slice_recording.py`
   into `fixtures/` with a manifest note of what each slice shows.
3. **Flight kinematics reports**: from `flight.jsonl` logs, plot/report IMU,
   setpoints vs estimates, FSM timelines (reuse `aigp.telemetry.plots`);
   write findings to `analysis/<date>-<topic>.md`.
4. **Cross-checks**: anything suspicious (frame gaps, clock jumps, decode
   failures) — document with data in your report; do NOT fix code, flag it.

### CURRENT TASK: the milestone autopsy + the inter-gate frontier

Gate 1 has been PASSED (fixtures/20260716T132549-phase3j-r2training-rerun,
flight 20260716T131137: first-attempt pass at default speeds, t=25.4,
then a hard env hit 13.5s later while chasing gate 2). Three studies:

1. **Extend the miss map** with phase3i + phase3j-rerun rows — including
   the PASS itself (its crossing vector is our first ground-truth
   "success" datapoint; everything else calibrates against it).
2. **Inter-gate segment study (the new frontier)**: from the milestone
   flight's log + slice — what happened between the pass (t=25.4) and
   the collision (t=38.9)? Track the gate-2 lock quality, the brief
   commit->retreat at t=31.6-31.8, and identify WHAT it hit (frames
   around the collision: pillar? parked aircraft?). R2 has obstacles
   between stations and the pilot flies straight lines.
3. **Cyan line as an obstacle-free corridor**: from all R2 slices — is
   the ribbon continuously visible/segmentable while flying BETWEEN
   gates (not just on approach)? Would following it have avoided the
   collision? This decides the phase4b navigation design.

### PREVIOUS: the crossing-miss map (convergence dashboard)

We are converging on the first pass fix-by-fix; the missing instrument
is a unified view of HOW EACH ATTEMPT MISSED, comparable across code
versions. Build it from ALL R2 fixtures (phase3c/3d/3e/3f, and 3g when
it lands):

1. **Crossing reconstruction per flight**: from flight.jsonl STATE
   messages (the lock-accepted, dead-reckoned pose — NOT raw detections,
   which include lock-rejected fixes and mislead), find the moment the
   gate plane is crossed or the closest approach, and record the miss
   vector (lateral m, vertical m relative to opening center).
2. **The dashboard**: one table + one scatter plot of miss vectors,
   colored by phase/code version. This shows whether cross-track (3f+)
   and altitude hold (3g) each shrank their axis, and what residual is
   left — the next fix gets aimed by this chart.
3. **Close-range PnP outlier autopsy**: the 2-4m range shows rare huge
   vertical jumps (max 4m in phase3f F1). Pull the exact frames that
   produced them from the slices — what does the detector see there
   (partial ring? banner? other gate through the opening)?

### PREVIOUS: pin the LATERAL frame offset (done: analysis/2026-07-15-lateral-offset)

The vertical phantom is fixed (mount_pitch=29); phase3d exposes a
LATERAL twin: vy_est reads -1..-3 m/s OPPOSITE to true motion during
approach (see flight 20260715T121747: vy_est -2..-3 while the gate
bearing converges rightward). Pin its mechanism on the phase3d slices +
flight.jsonl:

1. **Camera mount YAW/ROLL offsets**: from rest-phase frames across all
   phase3c/3d flights — gate azimuth in camera vs the known start-pad
   geometry (drone parked on the same pad, gate bearing repeatable), and
   frame-edge roll angle vs IMU gravity roll. Deliver offsets in deg
   with uncertainty, like the pitch calibration in docs/08.
2. **Phantom-vs-yaw-activity correlation**: from flight.jsonl, correlate
   the vy_est error signature against commanded yaw activity — tests the
   frozen-z/tilted-IMU coupling theory vs a static mount yaw offset
   (constant-with-speed => mount; grows-with-yaw-integral => coupling).
3. **Did mount_pitch=29 land?**: compare vertical crossing errors
   phase3c (pre) vs phase3d (post) — quantify, and recommend 24/29/34.

### PREVIOUS: R2 deep-dive on the phase3a slices (done: analysis/2026-07-14-r2-deepdive)

The committed slices (r2_f2/f3_slice_start.aigprec) show the R2 world:
red AI-GP gates, a glowing CYAN racing line through the whole track, red
"E" station signs and pink orb lights (false-positive candidates).

1. **Cyan racing-line study (highest value)**: measure the line's HSV
   bands across frames/lighting; how reliably can a cheap mask segment it?
   Does it always pass through the NEXT gate's opening? Deliverable:
   analysis report + recommended hue/sat/val bands + 10-20 annotated
   frames. This can unlock line-following navigation between gates.
2. **Detector false-positive audit**: run the repo detector over both
   slices; count detections that are NOT the active gate (other gates vs
   signs/lights). Does the ring test reject the "E" signs and orbs?
3. **Sensor-model audit on phase3a logs** (as before): repeat the docs/07
   correlations on the new flight.jsonl files; estimate per-axis
   gyro_scale.

### PREVIOUS (done by cloud in docs/08): R2 recon + sensor-model audit

Read docs/07 (the gyro-inversion finding came from correlation analysis of
the kind you do best — pixel motion vs IMU on phase2k). Then, on the new
phase3a recordings:

1. **R2 gate appearance study (top priority)**: from the R2-TRAINING vision
   recordings — what do R2 gates LOOK like? Color histograms, shapes, sizes,
   backgrounds, lighting. Save 30-50 representative frames (with and without
   gates visible) under `analysis/r2_frames/`. Recommend a detection
   strategy (HSV bands? edges? something else?) with measured evidence.
   This determines whether we can fly R2 at all.
2. **Sensor-model audit on phase3a-r1**: repeat the docs/07 correlations
   (Δpitch_gyro vs Δv_pixel, Δroll_gyro vs frame-edge angle, yaw-cmd vs Δu)
   on the NEW recording — confirm gyro_sign=-1 and yaw-cmd gain ~1.0 hold
   in flight, and estimate gyro_scale per axis (docs/07 saw ~1.0-1.1).
3. **Estimator truth-check**: from flight.jsonl, compare v_world/attitude
   estimates against pixel-derived motion around approach/commit; flag any
   phantom-velocity episodes (see docs/07 for the failure signatures).

# SIM OPERATOR Runbook

Instructions for an AI agent (Sakana, Claude Code, or any other) running on the
**Windows machine where FlightSim.exe is installed**. You are the *sim
operator* half of a two-agent team:

- **You (local agent)**: operate the real simulator, run flights, collect
  artifacts, commit them to this repo.
- **Cloud agent**: analyzes your artifacts, develops/fixes/upgrades the pilot
  code in `src/`, pushes code changes. It cannot reach the simulator — your
  artifacts are its only window into the real sim.

All coordination happens through git on branch `main`.

## Ground rules

1. **Never edit `src/`, `simtools/`, `tests/`, `docs/` or `config/`** — code
   and parameter changes are the cloud agent's job. If you believe a code
   change is needed, describe it in your run report instead.
2. **Only add files under `fixtures/`** (created by `scripts/collect_artifacts.py`).
3. Commit messages start with `[sim-run]`, e.g. `[sim-run] phase1 vs sim v1.0.3385`.
4. Always `git pull` before running — the cloud agent may have pushed fixes
   for issues found in your previous run.
5. Recording files larger than ~50 MB: do NOT commit; upload to the Google
   Drive folder `AI-GP Simulator/recordings` instead and mention the filename
   in your report.

## One-time setup

```powershell
cd $HOME\Documents
git clone https://github.com/tsionely/eni_dcim.git
cd eni_dcim
pip install -r requirements.txt
```

## Standard run cycle

1. `git pull`
2. Launch `FlightSim.exe` (latest sim version), log in, enter the qualifier
   so the drone is waiting on the start point.
3. Run the task for the current phase (see below), capturing console output:

   ```powershell
   python scripts/phase1_check.py --duration 60 2>&1 | Tee-Object -FilePath phase1_report.txt
   ```

4. Package the artifacts:

   ```powershell
   python scripts/collect_artifacts.py --label phase1 --report phase1_report.txt
   ```

5. Review the created `fixtures/<timestamp>-<label>/` folder, add your own
   `notes.md` there (what you observed: sim version, track, anomalies,
   suggested code changes).
6. Commit and push:

   ```powershell
   git add fixtures
   git commit -m "[sim-run] phase1 vs sim v<version>"
   git push
   ```

## CURRENT TASK: Phase 5b — BLOOM-PROOF DETECTOR IS IN; the story changed

The phase5 studies landed (thank you — both were decisive) and together
with the frames they OVERTURNED the working theory. Established facts:

1. **The committed `*_slice_start` fixtures are PAD footage.** The
   slicer stamps every packet mono_ns=1 and duplicates payloads ~8x;
   each slice holds ~1s of unique video from BEFORE takeoff (phase4c:
   FSM shows 45s THROTTLE_DOWN, takeoff at t=45s; the "commitwindow"
   slice covers t≈43-44s). The first gate stands ~6m from the launch
   pad — that is the real origin of the "no fixes below 5m" number.
   reflight.py now dedupes and takes frame timing from the flight log.
2. **The live flight log disproves total close blindness**: phase4c
   live detections reach 0.90m. But Cursor's real-approach bins show
   ~50% fix loss at 3-5m — and the cause is on the frames: the CYAN
   RIBBON'S GLOW washes the red ring to bright PINK (H~152 S~40-100
   V~248 — outside both red hue bands, under the sat floor), the AI-GP
   banner merges into the outline, and the bloom cuts the bottom bar,
   so the convex-4-gon test fails on a plainly visible ring.
3. **The believed state still runs away**: at the phase4c commit the
   state said 0.03m while live detections said ~2.0m; the drone then
   relocked far gates (13-45m) and died on hangar steel.

This build answers all three (all validated offline + unit + mock):
- washed-red mask branch + minAreaRect box fallback: 100% frame
  coverage on every committed slice (was 85-91%), rescuing exactly the
  bloom-washed/broken-ring frames. More close fixes = less coasting =
  less believed-state runaway.
- commit & retreat now YAW THE NOSE onto the (dead-reckoned) gate
  (planner.commit.yaw_track_gain=1.2): the frames showed the gate
  walking out the side of the fixed camera during the lateral strafe
  (edge_clip -> no_red), and retreat re-acquiring FAR gates. The camera
  now stays on target through the attempt and the retreat.

**VALIDATED on phase5-closerange-frames (Sakana's 20260716T212744
fixture — real approach footage, thank you, this was the decisive
material).** New-vs-old detector on the 127 unique close-range frames:
96% vs 87% coverage, ALL 2-5m gaps closed, fixes down to 1.34m (the
closest ever measured). Estimator replay over the F1 final approach:
every near fix accepted, every far-gate flicker (10-21m single frames
mid-approach) rejected, age <=0.16s, believed distance tracks measured
within ~0.2m all the way in — the believed-state runaway disappears
when fixes are continuous. What killed F1 on the old build, seen on
the frames: the drone arrived ~1m HIGH while believing LOW, looked at
the gate's BANNER from above at 1.3m (opening below the frame bottom —
the camera is tilted +11 deg UP), and overflew. The final ~1.3m is
structurally blind downward; the vertical axis is the open front.

**SIM OPERATOR (Sakana)** — phase5c: the terminal-ownership cycle.
phase5b-confirm verdict (superb cycle — verified track, honest slices,
the track-id reference is permanent gold): the drone now physically
REACHES the gate (F3: 0.88m closest, 4 gate clips) and retries the same
gate. The remaining failure, diagnosed from your F3 log: at terminal
range the NEXT gate (visible through the near gate's opening, threaded
by the racing line) STOLE the detector's candidate contest; the lock
followed it (believed 4.5m while honest fixes said 1.8m) and the drone
clipped the near frame chasing the far center; after the clip the stale
lock rejected reality and the flight died on hangar steel. Fixed in
HEAD: terminal ownership (prediction-consistent candidate boost beats
the cyan prior at close range) + a collision clears the gate lock + the
no-arm rule for blind-coast compensations.
1. `git pull` — HEAD must include "terminal ownership". SIM LOCK.
   R2-TRAINING via your verified row-selection procedure (screenshot
   the highlighted row; scene check per fixtures/track-id-reference).
2. Fly THREE valid flights, default speeds, max-duration 300.
   Watch specifically: in the final approach does it stay on the NEAR
   gate through the attempt (no last-second veer toward the next
   gate)? After any clip: does it re-acquire the SAME gate quickly?
   And the standing vertical question: attempts HIGH or LOW?
3. Slice TAKEOFF->end per your now-standard procedure (>10s unique
   frames, widen when needed).
4. Collect `--label phase5c-ownership`, push, VERIFY. Report per
   flight: gates passed / clips / closest / post-clip behavior /
   build SHA / track verification evidence.
5. Ops note: your calibration line read bias=[0. 0. 0.] on all three
   flights — exact zeros are suspicious (frozen countdown telemetry?).
   Harmless to yaw (dead z-gyro path) but report the line again this
   cycle; if still exactly zero we will move the calibration window.

**DATA ANALYST (Cursor)** — rerun the frame study on the NEW build:
1. Your run_phase5_study.py harness, HEAD build, over the full local
   recordings (local_pass_vision + any new phase5b material): fix rate
   per range bin old-vs-new detector (washed_red/box_fallback on vs
   off). Deliver: the same miss-reason table — expectation is
   partial_ring/no_red(bloom) largely converted to fixes; what remains
   (true edge_clip, exposure) sizes the NEXT perception task.
2. From the phase4c full log you already have: quantify the
   believed-vs-measured runaway during the commit (state.gate_rel vs
   detection range, t=44-52s) — that is our estimator-error ground
   truth for the velocity work.
3. NEW, P0 after the fixture: the VERTICAL axis. F1 arrived ~1m high
   while the state said LOW and overflew the gate (banner-view at
   1.3m). From the full recordings: reconstruct the true vertical
   offset vs believed during final approaches (the gate's image-space
   vertical position + PnP t is your measurement). Where does the
   vertical error come from — vision-velocity vz, blind_climb_bias
   double-compensation, altitude-hold reference error? One number per
   flight: vertical believed-vs-true at the last fix.
4. Think-tank measurement pack (docs/thinktank/RESPONSE.md §3, small
   adds to your existing harness): (a) for each sub-2m miss frame,
   does the red contour touch a border and WHICH one (P1); (b) pitch +
   gate-bbox bottom row at the last accepted fix per approach (P2/P3);
   (c) cyan availability histogram specifically in the last 5m; (d)
   fix-delta histogram + gate-normal sign-flip count (PnP flips vs
   real far gates — we see single-frame 10-21m fixes mid-approach);
   (e) Shi-Tomasi count / blur metric on lower half of close frames;
   (f) fraction of last-5m frames with a second gate visible.
5. Think-tank ROUND-3 pack (docs/thinktank/RESPONSE3.md — vertical):
   (a) R1: cyan-ribbon availability in the LAST 2m, split by image row
   vs the attitude-compensated horizon row (180 + 320·tan(11°+pitch));
   (b) R4: banner geometry — height band of the banner bottom edge
   above opening center, one-time from any far frame with a fix;
   (c) D5 disambiguation, one multiplication: for each single-frame
   far fix, R_reported·quad_width_px ≈ 512 px·m ⇒ real far gate,
   ≫512 ⇒ PnP flip/garbage on the near quad — sort F2's last-fix
   sign conflict (believed +0.31 vs true −0.95 at 1.67m) with it;
   (d) V6 moments: distribution of (crossing z − aim) across the new
   continuous-fix attempts — mean vs std decides any further bias;
   (e) balloon test: correlate vertical DR error growth with
   pitch/thrust transients (confirms/kills the blend-lag mechanism);
   (f) advisory #3 Test A RERUN with the measured geometry (your R4:
   banner bottom is +0.15m above OPENING CENTER, not ~0.9m — the first
   run's d*=0.8 was scoring against the wrong structure): split bar vs
   banner identity explicitly (banner = the wide strip whose bottom
   edge sits ~0.15m above center; top bar = the ring member above the
   opening), calibrate d* per structure from R4, then score
   W·y_T/l_T - d* against the full-pose reference in the 2.4-1.5m
   band. Bars unchanged: median bias <0.05m, P90 <0.15m, sign acc
   >99% when |ref|>0.15m. Note HEAD's new detector scale-gate kills
   flat strip-fit poses — use it to label which frames were bar vs
   banner (killed = strip-fit);
   (g) H3 census (think-tank round 4): per-frame visible-edge
   identity (left/right/top/bottom/banner) over the last 1.5m of F1
   and F2 — fixes the true source-transition order for the crossing-
   time filter AND doubles as V2 validation (last-surviving structure
   vs vertical state: banner-last ⇒ HIGH, F1's final second);
   (h) T3 kill test on the full F1 log: replay under HEAD's no-arm
   rule and confirm the double climb is structurally unreachable;
   (i) F2 arbitration pair, both one-liners: the 512 px·m product
   (R·quad_width_px) AND the row-consistency check (believed ty
   +0.31 at 1.67m predicts an opening-center row the actual mask
   must violently disagree with if truth was -0.95).
6. ROUND-4 pack (advisory-4 asks — priority order):
   (A2/R1 — HIGHEST-VALUE MEASUREMENT IN THE PROGRAM) cyan-ribbon
   availability in the last 2m of ALL committed takeoff->end slices
   (phase5c + phase5d), split by image row vs the attitude-compensated
   horizon row (180 + 320·tan(11°+pitch)): presence %, row-offset
   distribution, per flight. Why decisive: in our measured LOW
   geometry the ribbon rides ~0.45m ABOVE the camera => ~30px above
   the horizon row — in frame and glowing exactly when the ring is
   gone. This gates the closed-loop vertical reference (V1).
   (A1) label the three adversarial segments as the standing
   false-accept-zero suite, frame-id ranges per slice, committed as a
   manifest: F2 banner-fiction (t≈7.0-7.5 of 20260716T212408), the
   phase5d F2 post-retreat ceiling view, and the phase5b F3
   next-gate-steal (t≈6.9-7.3 of 20260717T091239).
   (A4) physical bar width w_bar in meters — one measurement from any
   far frame with a trusted fix.
   (A5) minimum inter-gate spacing on R2-TRAINING from any wide frame
   with two trusted fixes (pins the next-gate scale margin for the
   side-pair certificate).
7. ADVISORY-5 pack (aperture question — A6 is DECISIVE, do it first):
   (A6-i) RE-MEASURE the banner-bottom height reference: your R4
   number (+0.15 above 'opening_cy_px') is suspected of a reference
   slip — if opening_cy came from the banner-MERGED quad center it is
   displaced upward. Re-measure banner-bottom height against the
   opening center derived from the SIDE-BAR midpoint (or inner
   opening), on 2-3 independent far frames with trusted fixes. Report
   which reference the original used. Context: M1 re-scoring already
   failed the branch-A prediction (all six phase5c/5d terminal
   arrivals are low even in aperture coordinates), so we lean
   branch B — but A6-i decides.
   (A6-ii) one annotated ~2m frame: is a DISTINCT +0.8 top-inner edge
   observable from flyable heights, separate from the banner bottom?
   (A6-iii) solidity of the band between banner bottom and opening
   top (collision mesh evidence or clip-event correlation).
   (A7) rider on R1: ribbon height relative to the measured aperture
   center from one trusted fix.
   (A8) drone vertical half-extent including props (one number, from
   sim docs/params or clip-geometry inference).
   (A4 — PRIORITY BUMPED) bar width w_bar: now an executioner for the
   banner-edge impostor class (separation ratio 1.25 passes the scale
   gate; bar-ness is what kills it).

**QA (Codex)** — the regression suite, honest this time:
1. Pull HEAD; note reflight.py's fix (dedupe + log-based frame times) —
   your matrix numbers were per-decode, not per-frame; rerun the matrix
   on HEAD vs 9fe3702 with the fixed harness. Report per-slice: unique
   frames, fix rate old/new detector. (Ranges will all be ~6m — these
   are pad slices; that is expected now.)
2. Windows CI on HEAD. The 3 known-flaky FSM/heartbeat failures under
   load: if they reproduce, run those tests solo and report solo
   verdicts; overrun_frac=0.74 on your box during hover is worth one
   line of investigation (AIGP_NOSLEEP unset? — also note HEAD's frame
   dedupe removes ~90% of vision-path CPU, re-measure overrun on HEAD).
3. PRIORITY on HEAD with the GateCloseTracker: the cloud container is
   too saturated to run the 250Hz closed-loop mock reliably (control
   experiment: the clean previous build also fails 3/3 there), so YOUR
   machine is the arbiter for closed-loop now. Run
   tests/integration/test_mock_closed_loop.py solo-per-test 3x each and
   report pass rates for single_gate and first_gate_with_second_visible
   on HEAD vs 116b27e. If HEAD is not clearly >= the old build, bisect
   with --patch perception.close_tracker.enabled=false.

## PREVIOUS: Phase 4c — fast-fail launches + verified relock build

phase4b v2 verdict: the relock fix WORKS (F3 stayed local after misses —
no far-gate chase) and F3's closest state was 0.06m. Two ops/robustness
fixes in this build:
- watchdogs are armed at flight start: a no-race launch (0 frames, 0
  imu) now aborts in under a second instead of burning 300s "searching"
  on nothing (F2/F2b each wasted 5 minutes)
- keep launching flights until you get 3 VALID race attempts; the
  fast-fail makes dud launches cheap — just relaunch the race and rerun

1. `git pull` (HEAD must include "arm_all"). SIM LOCK. R2-TRAINING.
2. 3 VALID flights, default speeds:
   `python scripts/fly_once.py --max-duration 300
    --patch safety.flight_timeout_s=300`
   (a flight that aborts within seconds with "stale channels" = dud
   launch, not a pilot result — relaunch the race and retry)
3. Watch: gates passed; post-miss behavior staying local (it did in
   v2); retry cycles holding altitude.
4. Collect `--label phase4c-r2training-chain`, notes.md, push, VERIFY.

## PREVIOUS: Phase 4b — chain build: relock sanity + retry altitude

The milestone autopsy (analysis/2026-07-16-milestone-autopsy) measured
the gate-2 failure chain: closed to ~1m, crossed 0.9m beside the opening
(geometric termination + retreat fired correctly), then the RELOCK
accepted a 27m gate off to the side and the drone chased it into a
hangar steel truss. This build fixes both measured killers:
- relock DISTANCE SANITY: after losing a near gate, candidates much
  farther than the lost one are rejected (escape hatch after ~1s so we
  never fly blind forever); a pass still resets the cap for the
  legitimately-farther next gate
- retreat now carries the blind climb bias (phase4a bled 8-35 ground
  scrapes across retry cycles)
The PASS crossing vector is our ground truth: (+0.006, +0.100) — the
aim geometry is exactly right; do not touch aim params.

1. `git pull` (HEAD must include "relock" fix). SIM LOCK. R2-TRAINING.
2. 3 flights, DEFAULT speeds:
   `python scripts/fly_once.py --max-duration 300
    --patch safety.flight_timeout_s=300`
3. Watch: gates passed; after each pass, does it lock the RIGHT next
   gate; do retry cycles hold altitude now.
4. Slice every pass + 20s after; note WHERE any hard hit happens.
5. Collect `--label phase4b-r2training-chain`, notes.md, push, VERIFY.

## PREVIOUS: Phase 4a — FIRST PASS ACHIEVED; now chain the track

The first R2 gate pass is in. The mission changes: from "pass a gate"
to "complete the track". Everything needed for chaining is already in
the build — on_gate_passed re-arms the pipeline for the next gate, the
cyan-line prior picks the gate the racing line threads (its moment has
arrived: with several gates visible after a pass, the line
disambiguates), the two-gate mock test passes, and retreat/retry covers
misses per gate.

1. `git pull` (HEAD >= 43ef2b0). SIM LOCK. R2-TRAINING.
2. 3 flights, DEFAULT SPEEDS (the milestone pass was a first-attempt,
   default-speed run — 2.2s from takeoff to through the gate; the slow
   crutch is retired), longer window:
   `python scripts/fly_once.py --max-duration 300
    --patch safety.flight_timeout_s=300`
   Note: the milestone flight died 13.5s AFTER its pass with a hard env
   hit (impulse 15.5) while approaching gate 2 — R2 has obstacles
   (pillars, parked aircraft) between stations. Note WHERE it hits.
3. Per flight note: gates passed (the race HUD count), what happens
   AFTER each pass (does it find the next gate? how long does search
   take?), where the run ends.
4. Slices around EVERY pass + the 20s after it (the inter-gate segment
   is the new unknown — that data drives the next code cycle).
5. Collect `--label phase4a-r2training-chain`, notes.md, push, VERIFY.

## PREVIOUS: Phase 3j — sink compensation in the structurally blind meter

phase3i taught the geometry lesson: the +0.3m aim floor pushed the ring
out of the FOV bottom at 3.7-4.3m (vs 0.9m in 3h) — flying higher costs
sight. And the full ring CANNOT fit the FOV below ~1.4m, so the final
stretch is ALWAYS dead-reckoned. The real enemy is the ~0.5m SINK during
that blind stretch (+0.3 above aim at 4m -> -0.2 below center at the
bar). This build: aim floor reverted (visibility wins) + a climb bias
applied exactly and only while commit flies blind
(planner.commit.blind_climb_bias_mps=0.2), + geometric commit
termination already in (the clock can no longer cut a crossing short —
phase3h F3 lost a dead-centered pass to the 1.2s window).

1. `git pull` (HEAD must include "blind-phase sink"). SIM LOCK.
   R2-TRAINING. Your login/row-click helper fix from 3i is appreciated —
   keep it.
2. 3 flights, slow patch set. NOTE the commit window patch is now
   redundant (default duration_s=2.5, geometric termination) — drop
   `planner.commit.duration_s` from the patch set, keep the speeds.
3. Optional flight 4: no patches at all.
4. Collect `--label phase3j-r2training`, notes.md, push, VERIFY.

## PREVIOUS: Phase 3i — one axis left: cross 0.3m above center

phase3h was the closest cycle ever and every mechanism worked live:
retry confirmed (multiple approach->commit->retreat->approach), F1
crossed DEAD-CENTERED laterally (u=0.00) at 0.9m and F4 (default
speeds!) reached 0.21m — both caught the LOW side. The vertical bias is
now consistent: 0.2-0.45m LOW. This build stops tapering the aim to
zero: the aim point keeps a 0.3m floor above the opening center all the
way through (opening half-height is 0.8m — crossing +0.3 is safely
inside and clear of the measured bias).

1. `git pull` (HEAD must include "aim_up floor"). SIM LOCK. R2-TRAINING.
2. 3 flights, slow patch set (same as 3e-3h).
3. Optional flight 4: no patches (F4's 0.21m suggests default speeds
   are back in play).
4. If a flight crosses HIGH now: report the miss size — we bisect the
   floor (0.15) next cycle.
5. Collect `--label phase3i-r2training`, notes.md, push, VERIFY.

## PREVIOUS: Phase 3h — the endgame build (blackout fix + retry)

The analyst's crossing-miss map exposed the last-meter killer: at every
closest approach the state was 0.75-1.26s STALE — the dead-reckoned
prediction drifts, the fixed lock tolerance then rejects TRUE fixes as
"another gate", and the pilot flies its final meter blind on a drifted
state (phase3d f3 "crossed dead center" per state, collided in reality).
This build carries three weapons:
- age-aware lock tolerance (accepts fixes again as prediction ages) —
  kills the self-inflicted blackout
- retreat-and-retry: a blown commit backs off 2.5m and re-attempts
  instead of clipping and flailing (planner.retreat.enabled to A/B)
- absolute altitude hold (already in 3g; two-gate mock test now passes)

1. `git pull` (HEAD must include "age-aware" / "Retreat-and-retry").
   SIM LOCK. R2-TRAINING.
2. 3 flights, slow patch set (same as 3e/3f/3g).
3. Watch: does it RE-ATTEMPT after a miss (retreat = flying backward
   briefly)? Count attempts per flight. Any pass = the milestone.
4. Optional flight 4: default speeds, no patches.
5. Collect `--label phase3h-r2training`, notes.md, push, VERIFY.

## PREVIOUS: Phase 3g — slow set with ABSOLUTE altitude hold

phase3f verdict integrated: no constant lateral bias anymore (cross-track
did its job) and close-range PnP vertical is actually stable (p90 2cm
under 2m — the flips your closest-detection analysis saw were mid/far
outliers the lock already rejects; note your "direct detection" samples
include lock-REJECTED fixes, the state is what steers). The real slow-
flight killer: at 1.2 m/s the vision-velocity SNR collapses and vz
drifts -> ground. New in this commit: the vertical command now holds the
ABSOLUTE gate-relative height (gate vector rotated to world; drift-free
reference) in approach AND commit — no more integrating a drifting vz.

1. `git pull` (HEAD must include "altitude hold"). SIM LOCK. R2-TRAINING.
2. Same slow patch set, 3 flights:
   `python scripts/fly_once.py --max-duration 150
    --patch planner.approach.speed_far_mps=1.2
    --patch planner.approach.speed_near_mps=0.8
    --patch planner.commit.speed_mps=1.2
    --patch planner.commit.duration_s=2.5`
3. Optional flight 4: default speeds (no patches at all) — if altitude
   hold works, the normal-speed approach may now be the better one.
4. Collect `--label phase3g-r2training`, notes.md, push, VERIFY.

## PREVIOUS: Phase 3f — slow approach WITH cross-track nulling

phase3e flight 3 (slow) got a near-centered dead-reckoned state at 1.45m
(u -0.04, v -0.03) and lost it in the last meter — precisely the failure
the new cross-track term fixes (center_gain was defined but wired to
NOTHING until commit 82ea6c8; approach/commit now null lateral meters
directly). Your mount A/B verdict (34 over-corrects) is adopted: default
stays 29. Fly the same slow set on the NEW code:

1. `git pull` (verify HEAD >= 82ea6c8). SIM LOCK. R2-TRAINING.
2. 3 flights, same slow patch set as phase3e:
   `python scripts/fly_once.py --max-duration 150
    --patch planner.approach.speed_far_mps=1.2
    --patch planner.approach.speed_near_mps=0.8
    --patch planner.commit.speed_mps=1.2
    --patch planner.commit.duration_s=2.5`
3. Optional flight 4 if 1-3 miss laterally by a constant margin:
   add `--patch planner.approach.center_gain=1.0` (stronger nulling).
4. Collect `--label phase3f-r2training-slow`, notes.md, push, VERIFY.

## PREVIOUS: Phase 3e — SLOW approach (phantom starves at low speed)

phase3d confirmed the altitude fix (failure signature is no longer
uniformly high/top) and exposed the LAST blocker: a persistent LATERAL
phantom velocity (vy_est -1..-3 m/s opposite to true motion) during
approach, scaling with speed/yaw activity — same disease as the pitch
phantom, lateral axis. Until the analyst pins the lateral frame offset,
starve the phantom: fly SLOW. At 1.2 m/s the phantom shrinks to ~0.5 m/s
and the servo can hold the opening.

1. `git pull`. SIM LOCK (good discipline last cycle — keep it).
   R2-TRAINING.
2. THE SLOW FLIGHT, 3 times:
   `python scripts/fly_once.py --max-duration 150
    --patch planner.approach.speed_far_mps=1.2
    --patch planner.approach.speed_near_mps=0.8
    --patch planner.commit.speed_mps=1.2
    --patch planner.commit.duration_s=2.5`
   A pass at ANY speed is the milestone. Note crossing side as usual.
3. Optional flight 4 — the mount-pitch A/B that phase3d skipped (its F4
   was a stale re-report of the old roll-scale flight):
   slow patches as above PLUS `--patch perception.camera.mount_pitch_deg=24`
   if flights 1-3 still cross high, or =34 if they cross low.
4. Collect `--label phase3e-r2training-slow`, notes.md, push, VERIFY.

## PREVIOUS: Phase 3d — R2-TRAINING with the camera mount modeled

phase3c telemetry closed the case on the "always crosses high" mystery:
the planner COMMANDED descent, the estimator CLAIMED descent (+1..+3
m/s), and the gate still dove in the image — the drone never actually
descended. Root cause: the camera's optical axis sits ~29deg ABOVE the
IMU x-axis (rest-frame calibration: optical +11deg above horizon, IMU x
-17.8deg), and the unmodeled offset converted forward speed into phantom
descent (~V*sin(29) = 1.2-1.5 m/s at approach speed — exactly what the
logs show). Defaults now carry perception.camera.mount_pitch_deg=29 and
the mock mirrors both sensor frames. The roll-scale patch from phase3c
flight 4 is REJECTED (made things worse laterally, weak evidence base).

1. `git pull`. Single engine instance, SIM LOCK (the lock file was
   MISSING during your phase3c run while campaigns wanted the machine —
   please create/remove it every cycle). R2-TRAINING.
2. `python scripts/fly_once.py --max-duration 120`, DEFAULT params,
   3 flights. Watch: approach should now hold/gain the RIGHT altitude
   (no more sailing over the gate); note crossing side as before.
3. Optional flight 4 A/B on the calibration value:
   `--patch perception.camera.mount_pitch_deg=24` (if flights 1-3 cross
   LOW, the true offset is smaller; if still high, try 34).
4. Collect with `--label phase3d-r2training`, notes.md per flight, push,
   VERIFY on origin.

## PREVIOUS: Phase 3c — R2-TRAINING with live-steered commit

phase3b flight 1 was a near-pass: locked on the right gate, flew at it,
crossed 0.6m HIGH and clipped the top bar (docs/08 + telemetry). Fixed in
this commit: the commit window now keeps steering on the dead-reckoned
gate pose all the way through (no more stale locked vector), the aim-up
insurance tapers to ~0 at the gate, and the target-lock tolerance scales
with range (a mid-commit quad jump at 1m is now rejected).

1. `git pull`. Single engine instance, SIM LOCK, R2-TRAINING.
2. `python scripts/fly_once.py --max-duration 120`, DEFAULT params, 3
   flights. Watch per flight:
   - Where it crosses relative to the opening (high/low/left/right) —
     even on a clip, WHICH bar it touched is the key datapoint.
   - Whether commit visibly corrects vertically in the last meters.
3. Optional flight 4, A/B from the analyst's R2 deep-dive (roll gyro
   under-reports ~0.74x on both phase3a flights):
   `--patch estimation.gyro_scale_roll=0.75`
4. Collect with `--label phase3c-r2training` (slices around every
   crossing attempt), notes.md, push, VERIFY on origin.

## PREVIOUS: Phase 3b — R2-TRAINING with target lock + velocity resets

phase3a was a breakthrough recon: the corrected sensor model HELD on the
real sim (nose pointed at the gate, reached 1.4m from it in 3s), R2 gates
are red and detectable (1649 detections, conf 1.0), and docs/08 lists the
three failures that prevented a pass — all fixed in this commit: phantom
ground velocity (zeroed at takeoff), mid-commit target switching between
gates (gate lock), and post-collision velocity spikes (zeroed on impact).

1. `git pull` (verify docs/08-sikum-r2-recon.md exists). Single engine
   instance, SIM LOCK as usual. Load R2-TRAINING.
2. Fly `python scripts/fly_once.py --max-duration 120` with DEFAULT params,
   3 times. What to watch per flight:
   - Takeoff should now be GENTLE (no more -38deg charge off the pad).
   - Approach speed moderate (~2-3 m/s), nose on the gate, no target jumps.
   - Any gate pass: note WHICH gate and the race timer.
   - If the vision stream is dead again (phase3a flight 1): restart the
     race from the menu once; if still dead, note it and move on.
3. Optional 4th flight if all 3 look stable:
   `--patch planner.approach.speed_far_mps=4.0` (a faster attempt).
4. Collect with `--label phase3b-r2training` (slices around every gate
   approach; full recordings >50MB to Drive), notes.md per flight, push,
   VERIFY on origin.

## PREVIOUS: Phase 3a — THE SENSOR-TRUTH FLIGHT + R2-TRAINING recon

**Read docs/07 first. Everything you knew about the signs is superseded:**
the camera-vs-gyro correlation on YOUR phase2k recordings proved the GYRO
reports inverted (z frozen) while the COMMAND channel was always straight.
The old rate_sign=-1 "fix" was two wrongs canceling in hover — and in
approach the yaw centering was steering AWAY from the gate. Defaults now
encode the corrected model (gyro_sign=-1, rate_sign=+1, cmd-fed yaw, gate
dead-reckoning, aim-up). On the faithful mock this flies 9/10 through the
gate. Your job: prove it on the real sim, then bring back R2-TRAINING data.

ALL flights this cycle are on **R2-TRAINING** — the competition-deciding
track. It validates the corrected sensor model AND brings back the R2 data
in one cycle.

1. `git pull` (verify you see commit with docs/07). Single engine instance,
   SIM LOCK as usual. Load the sim on R2-TRAINING.
2. **Flight A — DEFAULT params, no patches**:
   `python scripts/fly_once.py --max-duration 120`
   Watch for: stable takeoff, the nose turning TOWARD the gate during
   approach (this was backwards until today), a committed pass attempt.
   Any gate pass = history. Note attitude quality, yaw behavior during
   search, altitude over time.
   - EXPECTED RISK: R2 gates are photorealistic, possibly NOT red rings —
     the detector may see nothing and the drone will hover/search. That is
     still a SUCCESSFUL recon: the vision recording is the deliverable.
   - Keep `record_vision` on (default). Every R2 frame is gold for the
     detector work.
3. **Flights B-C — repeat** `fly_once.py --max-duration 120`, default
   params, 2 more times (consistency check; note run-to-run differences).
4. If Flight A shows an immediate tumble (visibly worse than the phase2k
   hover): abort the cycle, collect, and report — do NOT improvise sign
   patches; the analyst verifies the sensor model from your recording.
5. Optional A/B if time remains (one flight each):
   `--patch estimation.vision_yaw=true` and
   `--patch planner.approach.aim_up_m=0.5`.
6. Collect with `--label phase3a-r2training` (INCLUDE vision-recording
   slices around any gate sighting; full files >50MB go to Drive per ground
   rule 5), add notes.md per flight (what the drone did, gates detected
   y/n, gates passed y/n, anomalies), push, VERIFY on origin.

## PREVIOUS: Phase 2f — hover-only stabilization ladder (superseded by
## docs/07: the E verdict below was WRONG — the gyro, not the command
## channel, is the inverted side)

## PREVIOUS: Phase 2e — the breakthrough cycle (E verdict + gyro-fix flight)

Cloud analysis of ALL evidence: both sign choices (+1 and -1 on commands)
tumble — which is only consistent if the GYRO is the inverted party: a
poisoned estimator destabilizes the cascade regardless of command sign. The
gyro-side fix is now pre-wired as params, so ONE cycle can both verify and
fly the fix:

1. `git pull`. Single engine instance.
2. `python scripts/control_probe.py --modes E` (twice) — paste the verdict
   blocks verbatim. Expected under the gyro hypothesis: physical NOSE-UP
   with negative gyro reading.
3. THE BREAKTHROUGH FLIGHT — gyro-corrected configuration:
   python scripts/fly_once.py --max-duration 90 ^
     --patch estimation.gyro_sign=-1 ^
     --patch estimation.gyro_scale=0.42 ^
     --patch control.att_rate.rate_sign_roll=1 ^
     --patch control.att_rate.rate_sign_pitch=1 ^
     --patch control.att_rate.rate_sign_yaw=1 ^
     --patch control.att_rate.hover_thrust=0.35
   (If E surprisingly says NOSE-DOWN / commands-inverted instead: fly with
   defaults plus only the hover patch.)
   Watch for: stable climb, level-ish hover, search spin — describe/shoot
   every stage. If it holds attitude at all, this is the breakthrough; gates
   come right after.
4. Collect with `--label phase2e`, push, VERIFY on origin (see DEFINITION OF
   DONE above).

## PREVIOUS: Phase 2d — the decisive sign experiment

Phase-2c: countdown hold WORKED (no DSQ — milestone!), but the drone still
tumbles right after liftoff even with the -1 command signs. That is strong
evidence the -1-on-commands theory is wrong: if commands were the inverted
side, flipping them should have stabilized the loop. New hypothesis: the GYRO
is the inverted party (probe D measured the *gyro*, which would read inverted
even for correctly-executed commands), and flipping commands re-created
positive feedback.

Probe mode E settles it without screenshots or estimators: open-loop RAW
pitch pulse, then a quiet hover window where the ACCELEROMETER (gravity
direction) reveals the true physical rotation. It prints the verdict.

Run this cycle:

1. `git pull`. Single engine instance.
2. `python scripts/control_probe.py --modes E` (it waits for GO — start a
   race). Copy the printed "open-loop verdict" block verbatim into the
   report. Run it TWICE for confidence.
3. Nothing else — no fly_once this cycle; the cloud agent flips the correct
   sign (command vs gyro parsing) based on E and only then flying continues.
4. Collect with `--label phase2d`, push.

## PREVIOUS: Phase 2c — the first legal takeoff

Phase-2b analysis (cloud side) — both blockers decoded from your data:

- The DSQ mystery is SOLVED: race_start_boot_time_ms updates at COUNTDOWN
  start with a *future* timestamp (your log: start=9,367,936 while the clock
  read 9,365,155 — exactly the 2,688ms of the DSQ). The pilot launched on the
  change instead of waiting for the scheduled moment. Fixed: GO now requires
  the sim clock to REACH the scheduled start.
- Your 3-axis sign table (all -1) is now the CONFIG DEFAULT, and the mock
  mirrors the inverted convention — no --patch needed for signs anymore.
- Probe H ladder extended down to 0.25-0.50 (you saw lift already at 0.40).

Run this cycle:

1. `git pull`. Single engine instance.
2. `python scripts/control_probe.py --modes H` — find the lowest thrust step
   that lifts and the highest that doesn't; note both.
3. Main event: `python scripts/fly_once.py --max-duration 60 --patch control.att_rate.hover_thrust=<your bracket>`
   (no sign patches needed). Start the race when prompted-by-waiting; the
   pilot should now HOLD through the countdown and lift at the actual GO.
   Describe per stage: countdown hold (no DSQ?), climb, search spin,
   approach. Screenshots downscaled as before.
4. Collect with `--label phase2c`, notes.md, commit, push.

## PREVIOUS: Phase 2b — race-legal takeoff + rate-sign calibration

Phase-2a analysis (cloud side): the pilot MOVES now, and the three failure
modes are all addressed:

- Early-start DSQ: the FSM now holds zero thrust in THROTTLE_DOWN until the
  race actually starts (a CHANGE in race_start_boot_time_ms; the flag itself
  is sticky). control_probe also waits for GO before each mode now.
- Inverted pitch-rate: per-axis sign params exist
  (control.att_rate.rate_sign_roll/pitch/yaw, default +1). Mode D now pulses
  ALL THREE axes to pin the convention down.
- hover_thrust: probe H data was contaminated by the tumble; re-measure.
- NEW: `--patch KEY=VALUE` on fly_once/aigp lets you override params per run
  WITHOUT editing config (allowed under the ground rules).

Run this cycle:

1. `git pull`. Single engine instance.
2. `python scripts/control_probe.py --modes D` — it resets, arms, WAITS FOR
   GO (start the race when prompted), lifts, then pulses roll/pitch/yaw one
   at a time. Record the measured sign per axis.
3. `python scripts/control_probe.py --modes H` — same GO flow; note the
   thrust step where it lifts/holds cleanly now that it starts race-legal.
4. Main event — fly_once with the signs measured in (2), e.g. if pitch (and
   only pitch) is inverted:
   `python scripts/fly_once.py --max-duration 60 --patch control.att_rate.rate_sign_pitch=-1 --patch control.att_rate.hover_thrust=<H result>`
   Start the race when the pilot reaches THROTTLE_DOWN (it waits for GO).
   Describe per stage: countdown hold? clean climb? stable search spin?
   approach toward gate 1?
5. Collect with `--label phase2b`, notes.md with the sign table + visual
   account, commit `[sim-run] phase2b race-legal flight`, push.

## PREVIOUS: Phase 2a — first real controlled flight (att_rate pilot)

Phase-1f verdicts (cloud side): velocity setpoints are DEAD on the real sim;
attitude-thrust and motor commands work. The pilot was rebuilt around the
attitude-rate cascade as the primary backend:

- control.backend default is now "att_rate"; throttle-down handshake extended
  to 3s (the 1.5s handshake didn't clear the overlay in your fly_once)
- the estimator now measures VELOCITY FROM VISION (derivative of the static
  gate's relative pose) — the key feedback that made the cascade fly cleanly
  in the mock (full simulated gate pass end-to-end)
- control_probe gained mode D (rate-response pulse) and H (hover-thrust
  ladder) to calibrate the cascade against the real sim

Run this cycle:

1. `git pull`. Single engine instance.
2. During a real race: `python scripts/control_probe.py --modes H` — note at
   which thrust step the drone lifts/holds (brackets hover_thrust), then
   `--modes D` — does the pitch-rate pulse register on ygyro?
3. The main event: `python scripts/fly_once.py --max-duration 60` during a
   real race. Expected: handshake clears the overlay, drone climbs ~1.5s,
   then searches/approaches the first gate. Describe (screenshots) what it
   does — even a wobbly hover or a crash into the first gate is a milestone;
   note against WHICH behavior phase (takeoff/search/approach) things break.
4. Collect with `--label phase2a` (include probe outputs in the report),
   notes.md with visual account per stage, commit `[sim-run] phase2a first
   controlled flight`, push.

## PREVIOUS: Phase 1f — control-authority probe (which interface moves the drone?)

Phase-1e analysis (cloud side):

- Your vision slice was put to work: the detector was rewritten for the REAL
  Round-1 scene (red gate rings, dark warehouse) — **100% detection on all
  658 real frames**, stable PnP. Perception is no longer a blocker.
- "THROTTLE DOWN please" is now handled: the FSM gained a THROTTLE_DOWN state
  (zero-thrust hold after arming) and the census NaN crash + gyro_z-only
  liveness checks are fixed.
- Remaining unknown: WHICH control interface the sim actually honors once the
  handshake clears. That is this cycle.

Run this cycle:

1. `git pull`. Single engine instance as usual.
2. Start a real race, then run (capture with Tee-Object):
   `python scripts/control_probe.py`
   It resets/arms per mode, does the throttle-down handshake, then tests
   attitude-thrust (A), velocity (B) and motor (C) commands in turn. For EACH
   mode note: did the THROTTLE DOWN overlay clear? did the drone visibly
   move/lift? (screenshots welcome). If a sim reset kicks it out of the race,
   restart the race between modes and say so in notes.md.
3. If any mode moves the drone — immediately also run
   `python scripts/fly_once.py --max-duration 45` (the pilot now does the
   handshake itself) and describe what happens on screen.
4. Collect with `--label phase1f --report <report>`, notes.md with per-mode
   observations, commit `[sim-run] phase1f control probe`, push.

## PREVIOUS: Phase 1e — in-flight IMU verdict + real-vision fixtures

Phase-1d analysis (cloud side): vision on 5600 WORKS during an active race
(20k frames @224Hz, clean decode). The "frozen" IMU now reads mean≈0 with a
single clean instance — exactly what a PARKED drone with a noise-free sim IMU
looks like. The earlier absurd constants came from the orphan/menu states.
Remaining question: does the IMU respond to actual MOTION? Nobody has flown
the drone during a race yet.

Run this cycle:

1. `git pull`. Verify a single engine process (as in 1d).
2. **The flight test**: start
   `python scripts/fly_once.py --max-duration 45 2>&1 | Tee-Object -FilePath phase1e_report.txt`
   and START A REAL RACE (your RACE automation) right as it connects. The
   pilot will arm and try to climb. Note in notes.md what the drone VISIBLY
   does on screen (climbs? sits still? drifts?) — that observation is as
   valuable as the logs.
3. `python scripts/mavlink_census.py --duration 60` (new) during another race
   window — it inventories EVERY message type with per-field value liveness,
   in case live telemetry hides somewhere we don't parse. Append output to
   the report.
4. Slice the big Phase-1d recording into a committable fixture (new tool):
   `python scripts/slice_recording.py recordings/phase1-20260713T200814.aigprec fixtures_slice.aigprec --start-s 10 --max-mb 40`
   and place `fixtures_slice.aigprec` in your fixture folder. (The full
   1.29 GB file still goes to Drive — human step, flagged for the user.)
5. Collect with `--label phase1e`, notes.md (include the visual observation!),
   commit `[sim-run] phase1e in-flight IMU + vision fixtures`, push.

Note: phase1_check now caps its recording at 200 MB by default
(--record-cap-mb) — race-rate vision is ~20 MB/s.

## PREVIOUS: Phase 1d — clean single-instance race validation

Phase-1c analysis (cloud side) reframed everything:

- 14560/5601 never answer pokes (idle or racing) → they are most likely the
  sim's own OUTBOUND source sockets (14560 -> client:14550 telemetry,
  5601 -> client:5600 vision), not services to connect to. The connect-mode
  hypothesis is dropped; the classic topology stands.
- Every earlier "frozen telemetry" measurement was taken either with the
  ORPHANED second sim process still alive, or with the sim at the menu/idle.
  Frozen values are plausibly just idle/menu placeholder telemetry.
- The one measurement never taken: 14550/5600 liveness DURING an active race
  with exactly ONE sim process. That is this cycle.

Run this cycle:

1. `git pull`. Verify exactly ONE engine process:
   `Get-Process | Where-Object {$_.Name -match 'FlightSim|DCGame'}` — kill
   orphans, document PIDs in notes.md.
2. Start `python scripts/phase1_check.py --duration 90 2>&1 | Tee-Object -FilePath phase1d_report.txt`
   and WHILE IT RUNS drive the sim into a real active race (your RACE
   automation). The check now prints a per-10s liveness window
   (`imu=... (ALIVE/frozen, std=...) frames+=N race_started=...`) — the
   idle->racing transition will be visible live. Note in notes.md the exact
   moment (which 10s window) the race became active.
3. If frames appear: let it finish — the recording it writes is our first
   real vision fixture. If IMU goes ALIVE too: rerun
   `python scripts/frame_probe.py` (bias-aware v2) for a clean frame verdict.
4. If vision is STILL silent during a clean single-instance race: capture
   where the sim's 5601 socket sends:
   `pktmon filter add -p 5601; pktmon start --etw -m real-time -c 30` (admin),
   stop with `pktmon stop`, note destination IP:port seen.
5. `python scripts/collect_artifacts.py --label phase1d --report phase1d_report.txt`
   (it now skips stale artifacts from previous cycles), add notes.md, commit
   `[sim-run] phase1d clean race validation`, push.

## Phase tasks (general roadmap)

The full roadmap with acceptance criteria is in `docs/05-avney-derech.md`
(Hebrew). Summary of what to run per phase:

| Phase | Commands | Success signal |
|---|---|---|
| **1 — connectivity** | `scripts/phase1_check.py --duration 60`, then `scripts/fly_once.py --max-duration 20`, then `scripts/frame_probe.py` | `PHASE-1 CHECK PASSED`; frame_probe prints body_x vs body_y verdict |
| 2 — hover | `scripts/fly_once.py --max-duration 40` ×10 | 10/10 no-collision hovers |
| 3 — one gate | `scripts/fly_once.py --max-duration 60` ×10 on a single-gate track | ≥8/10 `gates_passed >= 1` |
| 4 — full track | same, full track | ≥7/10 `finished: true` |
| 5 — tuning | `scripts/run_campaign.py --flights 20 --optimizer cem --sim real` | campaign completes unattended |

After each run, collect + push artifacts even on failure — failures are the
most valuable data.

## What the artifacts contain

`scripts/collect_artifacts.py` copies into `fixtures/<timestamp>-<label>/`:

- `report.txt` — the console output you captured
- `probe.json` — frame_probe IMU samples (if present)
- latest flight log dir: `flight.jsonl`, `result.json`, `params.json`
- `recording.zip` — the newest `.aigprec` vision recording (if ≤ 50 MB)
- `manifest.json` — what was collected, sizes, and the git commit of the code
  that flew
