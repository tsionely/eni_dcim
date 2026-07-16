# AI-GP Autonomous Racing Drone — External Think-Tank Brief

**Your role:** you are an external advisory "thinking team" for this project.
You have no access to the repository, the simulator, or the flight
recordings — everything you need to know is in this document. Your job is
to propose *approaches and algorithms*, not code. Every idea you produce
will be validated by the in-repo engineering agent against real flight
recordings (an offline replay harness) before a single line changes.

Be concrete, be skeptical of your own suggestions, and prefer ideas that
are testable offline on recorded frames.

---

## 1. Mission

Autonomous 4-motor racing drone in the **AI-GP** simulator competition.
Zero human intervention after launch. The drone must fly through a
sequence of square gates; the competition track is **R2-TRAINING** (a dark
hangar with steel trusses and parked jets as obstacles). Winning = passing
ALL gates, then best lap time. We are currently optimizing for *passing
gates reliably* — speed comes later.

**Sensors available: IMU + one fixed forward FPV camera. No GPS, no
altimeter, no magnetometer, no ground-truth pose. Ever.**

## 2. Platform truth (all items verified from recorded data)

| Fact | Value |
|---|---|
| Camera | 640×360, ~90° horizontal FOV, fixed mount |
| Camera axis | pitched **+29° above** the IMU x-axis |
| IMU mounting | pitched **−17.8°** relative to the airframe (so camera ≈ +11° above airframe forward axis) |
| Gyro reporting | **sign-inverted** on roll & pitch (sim bug; we compensate) |
| Gyro z (yaw) | **frozen/dead** on the wire — yaw is reconstructed from the commanded yaw rate (~1:1 verified) |
| Command channel | honest (normal signs) — attitude-rate + thrust setpoints |
| Attitude estimate | gyro-only integration (Mahony kp=0) + takeoff anchor; accelerometer feedback corrupted pitch during braking, so it's off |
| Frame timestamps | different clock domain than IMU (unix epoch vs boot time); rebased by EMA offset |
| Control loop | 250 Hz; vision fixes arrive at up to ~224 Hz when the detector fires |
| Gates | red square rings, opening ~**1.6 m × 1.6 m** (approx; being re-measured), several visible at once down the track |
| Racing line | a **cyan spline** painted through the track; when visible it threads the *next* gate's opening 100% of the time (measured), but it's only visible in ~26% of inter-gate frames |
| Collision events | the sim reports gate clips and environment hits; also "gate passed" events (our only crossing ground truth) |

## 3. Current pipeline (works up to a point)

1. **Detector** (classical CV): HSV red mask → external contours →
   `approxPolyDP` → accept only **convex 4-gons** → rectangularity +
   area scoring, ×3 boost if the cyan line passes through the candidate's
   opening → PnP with the known 1.6 m gate size → relative pose
   (translation t, normal) in camera frame.
2. **Estimator**: gyro-only attitude; velocity from vision (relative
   transport of consecutive gate fixes with frame-time attitude history);
   gate-relative position dead-reckoned between fixes
   (ṫ = −(ω×t) − v); target-lock logic so a far gate flashing into
   frame cannot steal the lock from the near gate.
3. **Planner**: approach (speed tapered 3.0→1.5 m/s inside 4 m, lateral
   centering, altitude hold from the gate reference) → **commit** at 2 m
   (fly through, live-steered while fixes last) → retreat-and-retry if
   the crossing is judged off-center.

**Achieved so far:** stable hover, reliable takeoff, target lock, first
clean gate pass (crossing offset +0.006 m lateral / +0.100 m vertical),
retreat-and-retry keeping attempts local. **Not achieved:** passing gate 2
and beyond consistently.

## 4. THE problem — the wall we need you to think about

We replayed real recorded flights offline through the exact detector and
estimator (a "reflight" harness that feeds recorded frames + IMU through
the code). Measurement from the latest close-approach recording:

- **221 gate fixes produced — every single one at range > 5 m.
  Zero fixes below 5 m.**
- Geometry predicted a blind stretch of ~1.4 m before crossing; the real
  blind stretch is **> 5 m — 3.5× longer**.
- During those last 5 m the state is pure dead-reckoning from a
  vision-derived velocity that stops updating. At the crossing plane, the
  believed lateral miss was **0.03 m** while the drone actually missed by
  a meter or more (no gate-clip events, no pass event = clean miss).
  **The crossing-time state is fiction.**

So: the drone aims well from far away, goes blind at 5 m, and drifts off
during the final approach — every failure to pass traces back to this.

### Why the detector goes blind (hypotheses, not yet fully confirmed)

- H1: the ring partially exits the FOV → the contour is clipped at the
  image border → never a convex 4-gon → rejected. (The camera also looks
  +11° above the flight axis, so a centered approach pushes the gate low
  in frame.)
- H2: at close range other gates/red objects merge with the ring in the
  red mask (morphological closing, 5×5 kernel) → not a clean quad.
- H3: perspective at off-axis approach makes the quad non-convex or the
  `approxPolyDP` corner count ≠ 4.
- H4: motion blur / red saturation in the dark hangar at close range.
- A teammate agent is currently labeling frame-by-frame WHY each close
  frame fails; assume a mix of H1–H3 dominates.

## 5. Ideas already tried and REJECTED by data (don't re-suggest)

- Mahony accelerometer feedback (kp>0): corrupted pitch ~10° during
  braking → off.
- Vision-derived yaw correction: too noisy, caused a bang-bang
  oscillator → commanded-rate feed-through instead.
- Raising the aim point (aim_up floor 0.3 m): pushed the ring out of
  frame at 3.7–4.3 m → made blindness *worse*; reverted.
- Count-based relock escape (N far fixes): opened in 0.11 s at 224 Hz
  and sent the drone chasing a 27 m gate into hangar steel → time-based
  (2.5 s) instead.
- "Camera mount is 34° not 29°": A/B tested on recordings, 29 wins.

## 6. Questions for you

**Q1 — Close-range detection.** How would you extract a usable gate fix
from a *partial* ring (2–3 corners visible, contour clipped by the image
border)? Options we're weighing: predicted-pose-anchored corner
refinement (project the dead-reckoned gate into the image, search locally
for corners/edges), line-segment fitting on the red mask + intersection
corners, homography from 2 corners + known gate size + attitude. What
would you do, and what failure modes should we expect?

**Q2 — Crossing without full pose.** Below some range, full PnP may be
impossible. Is there a robust *visual-servoing* formulation (IBVS on
whatever features remain: one corner, one edge, the red blob centroid,
optical-flow divergence) that keeps the drone centered through the plane
without a metric pose? How would you blend it with the dead-reckoned
state, and how do you decide which source to trust when?

**Q3 — The last-5m velocity problem.** Our velocity estimate comes from
vision fixes, so it freezes exactly when we go blind. With only a
(biased, tilt-compensated) accelerometer and known thrust commands, what
is the least-bad way to propagate velocity for ~1.5–2 s so the
dead-reckoning drifts less? (Accel double-integration? Thrust+drag model?
Optical flow from the raw image even without gate detection?)

**Q4 — Using the cyan racing line at close range.** The cyan spline
threads every gate opening and is often visible when the ring is not.
How would you turn a partially-visible painted line into a steering
signal for the final 5 m (line-following in image space? fit a curve and
servo on its vanishing direction?), and how do you avoid it hijacking the
approach when it belongs to the *next* segment after the gate?

**Q5 — Anything we're not seeing.** Given everything above, what would
you try that we haven't listed? Assume classical CV / lightweight
estimation (this must run in real time in Python at 250 Hz control,
~30–60 FPS vision on a normal PC; no GPU training pipelines mid-race,
though offline-trained tiny models are allowed if inference is cheap).

## 7. Rules of engagement

1. Advisory only — propose approaches, pseudo-code at most.
2. Every proposal must be **testable offline on recorded frames** —
   state explicitly what measurement would prove it works or kill it.
3. Rank your own suggestions by (expected impact × implementation
   simplicity); we ship the top one first.
4. If information here is insufficient to answer, say exactly what
   measurement or frame sample you need — the team can produce it and
   paste results back into this conversation.
