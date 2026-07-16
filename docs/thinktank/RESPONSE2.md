# RESPONSE to ADVISORY #2 (architecture review) — validation & adoption

Paste back to the second think-tank as the follow-up turn. Same protocol:
corrections from data first, then dispositions, then the numbers you asked
for. Read together with RESPONSE.md (sent to advisory #1) — the baseline
corrections there apply here too (the ">5m total blindness / 221 fixes"
datum was a pad-footage artifact; real approach footage shows fixes to
1.34m at 96% frame coverage on the current build).

## 1. Your duplicate-frame suspicion: CONFIRMED and FIXED — best catch of the round

You inferred it from the BRIEF's "224 Hz fixes" alone. Measured: the sim
rebroadcasts every exposure ~8-9x (~280 frame messages/s vs ~30 unique/s).
Until today the pipeline decoded and detected all of them and the
estimator ingested each exposure ~9x as independent measurements; a
frozen stream also kept feeding the frame watchdog. Fixed at the RX layer
(dedupe by frame id BEFORE the JPEG decode — also removes ~90% of the
vision-path CPU, which may explain a teammate's 74% control-loop overrun
report). Your prescription "one estimator update per unique exposure" is
now enforced by construction.

## 2. Architecture verdict

Your chain — acquire → model-based close tracking → partial constraints →
uncertainty-aware fusion → bearing servo — is accepted as the target
architecture, with one correction to its premise: the acquisition
detector no longer "goes from full pose to zero information" at the
border; the current build (washed-red mask + box fallback + yaw-on-target
+ continuous-fix lock) already tracks honestly to ~1.4m on real footage.
The remaining true gap is the final ~1.3m, which is structurally blind
DOWNWARD (camera +11° up; the opening exits the frame bottom; the top
bar/banner is the last visible structure), and the vertical axis is where
the last real flight died (~1m HIGH while believing LOW).

Adopted as the next engineering task (single work item, merged from both
advisories): **GateCloseTracker** — projected-model edge tracking with 1D
normal searches + M-estimator, updating translation only (orientation
gated on two non-parallel lines), with your observability ladder (a
single line is a 1D measurement, not a failure) and prediction-anchored
ROI capped at ~20-25 px. The n-of-4 corner solvers from advisory #1 fold
into this as the corner-rich special case. Offline validation: synthetic
border-clipping on trusted far frames + the pass recording ±0.05m
reproduction + your ≥90%-partial-measurement-coverage criterion from
handoff to 1-1.5m.

## 3. Pseudo-dropout harness: built, first baseline number

`scripts/reflight.py --blind-last-s T` now hides vision from the
estimator for the final T seconds and scores dead-reckoning against what
the detector actually measured (with a continuity filter so single-frame
far-gate flickers don't pollute the reference).

First baseline on the real final-approach recording (old-build flight,
F1 range3m-to-collision): **0.6s blind → believed-minus-measured range
error +2.2m at the end of the window.** Caveat: the committed slice gives
the estimator only ~1.2s of vision history before the cutoff, so
vision-velocity is barely converged — treat as an upper bound; the
full-recording version (proper history) is assigned to the data analyst.
Either way it makes your point: the last second cannot ride
dead-reckoning with the current velocity estimator, which elevates your
propagator ladder (bias-learned IMU, thrust/drag blend) from "deferred"
to "next after the close tracker".

## 4. Other dispositions (delta vs advisory #1's table)

- **Bearing servo (b × b* formulation, desired bearing from pass
  direction, attitude-compensated aim pixel)**: adopted as the design for
  the VISUAL_CORRIDOR phase; enters with the close tracker. Your framing
  "align the bearing, don't move the world aim point" is noted as the
  clean answer to our aim_up history.
- **State machine split (ACQUIRE/TRACK_APPROACH/VISUAL_CORRIDOR/
  PASS_THROUGH)**: adopted; maps onto our approach/commit with the
  corridor phase inserted. gate-passed event already exists and is
  authoritative.
- **Safe-envelope go/no-go (|mu|+2sigma inside margin)**: adopted in
  principle; needs the directional-covariance plumbing, enters with the
  tracker's partial updates.
- **Camera latency estimation**: adopted as a one-off measurement
  (cross-correlate derotated flow vs gyro/commanded yaw) — assigned.
- **Cyan corridor (first-intersection stop, zero-hijack precision
  criterion)**: agreed and deferred behind availability measurement;
  your "precision over recall / zero next-segment picks" is the accepted
  release bar.
- **Close-range mask branch (drop 5x5 closing, continuous likelihood,
  border-touching contours kept)**: partially shipped already (washed
  branch keeps border-touching components via the box fallback); the
  closing-kernel removal joins the close tracker work.
- **Tiny segmentation model**: agreed — Plan B only, same placement
  (feeds the line tracker, never the controller).

## 5. Numbers you asked for

- Duplicate audit: ~280 msg/s, ~30 unique exposures/s, dup factor 8-9x —
  fixed (see §1).
- Unique-frame close-range coverage (current build, 127 real approach
  frames): 96%, fixes to 1.34m, box-fallback used on 3 frames, all 2-5m
  gaps closed.
- Lock behavior against flicker: single-frame 10-21m fixes mid-approach
  are rejected by distance-sanity gating; fix age stayed ≤0.16s through
  the real approach; believed range tracked measured within ~0.2m to
  1.4m. (Whether those flickers are PnP flips or genuine far gates is
  being measured — D5 from advisory #1.)
- Pseudo-dropout baseline: §3.

## 6. The question for your next turn

Same as posed to advisory #1, now sharpened by your ladder: design the
last-meter VERTICAL channel. Constraints: no altimeter; vz is the weakest
estimated axis; the opening exits the frame bottom at ~1.5-2.4m (worse
with pitch-up braking); the top bar + banner above it are the last
visible structures; history shows both LOW crossings (pre-altitude-hold)
and a HIGH overfly (last flight). Given the close tracker will deliver
"top bar row + length" almost to the plane: rank concrete vertical-
guidance laws on that single feature (e.g., servo the top-bar row to the
attitude-compensated aim row vs estimate height-below-bar from bar length
and hold it), each with an offline kill test on the recordings we have.
