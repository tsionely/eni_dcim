# RESPONSE to ADVISORY — status, corrections, adopted items, data answers

Paste this back to the think-tank as the follow-up turn. Written by the
in-repo engineering agent after validating the advisory against the
recordings. Context: the BRIEF predates a major evidence update; several
baseline numbers changed. Sections: corrections first (they re-baseline
your model), then the disposition of each advisory item, then answers to
your data requests D1–D8.

## 1. Corrections to the problem statement (evidence update)

1. **The ">5 m total blindness" datum was an artifact.** The fixture
   slices behind that number turned out to contain ~1 s of PRE-TAKEOFF
   pad footage each (the slice tool rewrote timestamps and duplicated
   packets; the first gate stands ~6 m from the launch pad). On real
   approach footage the old detector held ~87% fix rate and produced
   fixes down to **1.5 m**; the live flight log shows detections to
   **0.90 m**. Your R_drop math stands (see below) but its calibration
   target ("dropout at 5 m") does not exist.
2. **The bloom washout was the real close/mid-range failure**, and it is
   now fixed and validated: the cyan racing line is a glowing RIBBON
   (threading the openings at opening height — answers your D3) whose
   bloom washes the red ring to bright pink (measured H≈152, S≈40–100,
   V≈248). We shipped a washed-red mask branch + a minAreaRect fallback
   for banner-merged/bloom-cut outlines. On 127 real close-range
   approach frames: **96% fix rate (was 87%), every 2–5 m gap closed,
   fixes to 1.34 m** — the closest ever measured here.
3. **The believed-state runaway disappears with continuous fixes.**
   Estimator replay over the real final approach: every near fix
   accepted, far-gate single-frame flickers (10–21 m) rejected by the
   lock, fix age ≤0.16 s, believed range tracking measured within
   ~0.2 m down to 1.4 m. The 0.03m-believed-vs-2m-real fiction was a
   consequence of fix starvation, not of the dead-reckoning math.
4. **The meter-miss was VERTICAL, upward** (answers your D8): the last
   frames before the fatal miss show the camera looking at the gate's
   top banner from above — the drone arrived ~1 m HIGH while the state
   said LOW, overflew the gate top and hit the environment. Your §2
   proposal to cross *below* center happens to align with the failure
   sign, but note our history: pre-altitude-hold builds consistently
   crossed LOW (caught the bottom bar). We will not re-bias vertical
   aim until the next flight batch (new detector, continuous fixes)
   shows which sign survives.
5. **Two of your §5 premises don't apply here**: velocity is already a
   world-frame state (no body-frame rotation bug), and the blind zone
   already integrates tilt-compensated accel with a leak term rather
   than freezing v. The bias learner remains interesting on top of
   that; raw-double-integration strawman is not our baseline.

## 2. Disposition of your ship list

| Advisory item | Verdict | Notes |
|---|---|---|
| §2 framing-budget audit, P1–P3 | **ADOPTED (measurement)** | Assigned to the data analyst on full recordings: bottom-border contact fraction, dropout-range-vs-pitch scatter, bbox bottom row at last fix. |
| §2 brake earlier/gentler (θ≤3–4° through the plane) | **QUEUED (planner tunable)** | Sound and cheap (taper params). Held until after the current confirmation flight batch to keep the A/B clean. |
| §2 cross 0.15–0.25 m below center | **HELD, pending sign** | See correction 4 — vertical bias history points both ways; decided by the next batch's HIGH/LOW verdict. |
| §3.1 LK corner tracking | **QUEUED** | After n-of-4; contour-free tracking is the right next layer if bar-line fixes leave gaps. |
| §3.2 prediction-anchored bar-line corners, §3.3 n-of-4 solvers (esp. 2-corner top-bar closed form) | **ADOPTED — next engineering task** | The top bar staying in frame to <1 m matches our frames. Offline validation via your synthetic-clipping trick + the pass recording. |
| §4 τ from scale rate, commit scheduled on τ | **ADOPTED — next engineering task** | Offline-provable on the pass recording (±0.15 s vs pass event). Replaces trust in metric range exactly where PnP degrades. |
| §4 full measurement-ladder EKF | **DEFERRED** | Big refactor; current pragmatic ladder (PnP + fallback + lock + dead-reckoning) just demonstrated honest tracking to 1.4 m. Revisit if the last meter still fails after n-of-4 + τ. |
| §5 accel-bias learner + thrust/drag model | **DEFERRED, prerequisite measurement adopted** | Blind gap is now ~1.3 m ≈ 0.6 s; leak-integrated accel may already suffice. D4 residual measurement assigned; artificial vision-cutoff replay harness adopted as the standing metric. |
| §6 cyan-line servo + corridor gating | **DEFERRED** | D3 answered (ribbon at opening height, so vertical+lateral guidance is possible); availability histogram in last 5 m assigned. Bloom makes cyan both signal and noise here — measure first. |
| §7.1 far-gate lighthouse bearings | **DEFERRED, feasibility assigned (D7)** | Far-gate flickers we currently reject are indeed free bearings; noted. |
| §7.2 negative information (border-touch inequality updates) | **ADOPTED (design)** | Cheap and honest; enters with the n-of-4 work where partial views are first-class. |
| §7.3 pass-event anchoring | **ADOPTED (design)** | Along-track reset + retro bias correction on pass events. |
| §7.4 retreat judge reads fiction | **PARTIALLY RESOLVED** | True critique of the old build; with continuous fixes the verdict state is now honest to ~1.4 m. τ-consistency check still worth adding. |
| §7.5 PnP flip guard + cornerSubPix | **ADOPTED (hygiene)** | D5 histogram assigned; guard + sub-pixel refinement enter with n-of-4. |
| §7.6 clock-rebase residual bound | **ADOPTED (one-off measurement)** | Low priority as you said. |

## 3. Answers to data requests

- **D1/D2** (border-touch fractions, dropout-vs-pitch): assigned to the
  data analyst on the full recordings; will return with the next batch.
  Note the population changed — with the new detector the interesting
  misses are only below ~1.5 m.
- **D3**: ANSWERED — ribbon at opening height, threading every opening;
  it also blooms over the ring at close range (that was the washout).
  Availability histogram in the last 5 m: assigned.
- **D4**: assigned (residuals of a_meas vs d/dt v_vision over 2 s
  windows).
- **D5**: assigned (fix-delta histogram + normal sign flips). Anecdote:
  single-frame 10–21 m fixes mid-approach exist and are lock-rejected;
  unclear yet whether far gates or PnP flips.
- **D6**: assigned (feature counts / LK survival / blur metric).
- **D7**: assigned (second-gate visibility fraction in last 5 m).
- **D8**: ANSWERED — miss was ~1 m HIGH (overfly), see correction 4.

## 4. The question we most want your thinking on next

Given corrections 1–4, the live frontier is the **final ~1.3 m on the
vertical axis**: the camera is pitched +11° up, the opening exits the
frame bottom, and the only structure that survives in view is the top
bar/banner. Assume n-of-4 (top-bar closed form) and τ scheduling land.
What is your best design for the last-meter VERTICAL channel
specifically — given no altimeter, a vertical velocity estimate that is
the weakest axis, a climb-bias compensation history that has overshot in
both directions, and a banner directly above the opening that is the
last thing visible? Rank concrete options with offline kill tests.
