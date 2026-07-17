# RESPONSE to ADVISORY 2 (last-meter vertical channel) — triage & data

Paste back to think-tank #1. Since your last turn the build moved: the
close tracker (projected-edge normal search, translation-only, SVD-
truncated observability) shipped and is validated on synthetic clipping
+ the real final-approach slice; two real flights on the new detector
landed (fixes to 1.34/1.50m live material); and the teammate analyst
attributed the F1 vertical miss from the full logs. Several of your
items are therefore already answered by data — including one your own
kill test settles.

## 1. The F1 vertical miss is now attributed (changes V5/V6's premise)

From the full flight log (analyst study, 2026-07-17): at the last close
fix (1.50 m) believed and true vertical AGREE — both ty ≈ −0.33 m
(aircraft LOW). The +1m HIGH overfly develops entirely in the post-fix
coast: altitude-hold climbs toward aim_up on a dead-reckoned state with
no stop signal, and the blind-climb sink insurance (armed at fix-age
>0.4s, active in 30% of commit samples) adds MORE climb on top — a
double compensation tuned for the old long-blind era. **Not a
believed-LOW-while-HIGH estimator inversion at the fix.** Fix already
shipped: commit's bias 0.2→0.1 m/s, arming age 0.4→0.7 s, retreat keeps
its own compensation.

The OPEN vertical mystery is F2: at its last fix (1.67 m) believed ty
= +0.31 while true = −0.95 — a sign conflict AT the fix itself, i.e., a
detection/PnP-level error, not drift. Suspect: banner-as-gate or a PnP
flip on a partial quad. Your §4 D5 disambiguation (R·ℓ_px ≈ 512 px·m)
is adopted verbatim to sort this class.

## 2. V5 (leak audit) — killed by arithmetic, per your own criterion

Our leak is 0.05 s⁻¹. Over the ≤0.9 s blind window that decays w by
≤4.4% — it cannot lag a climb into a believed-LOW of ~1 m, let alone
flip a sign. The mechanism you describe would need to live in the
vision-velocity BLEND dynamics instead (per-fix blend 0.18 → w
convergence lag during climb onset), which is worth one measurement,
folded into the balloon-correlation test you specified (assigned). The
leak stays as-is; "no correlation ⇒ hypothesis dies" — it died at the
parameter table.

## 3. Vertical holdout harness — built, first numbers

reflight --blind-last-s now scores the vertical channel (camera ty)
against the below-cutoff real fixes, alongside range. F1 final
approach, harness conditions (short pre-blind vision history — upper
bounds):

| blind window | range error (end / max) | vertical ty error (end / max) |
|---|---|---|
| 0.6 s | +1.77 / 1.77 m | +0.00 / 0.26 m |
| 1.0 s | +4.23 / 4.23 m | −0.25 / 0.56 m |

Two conclusions. (a) Vertical dead-reckoning is roughly inside your
§1 budget (0.26 m worst over 0.6 s vs ±0.8 m opening). (b) The weak
axis under blind coast is ALONG-TRACK, not vertical — believed range
runs away 3–7× faster than believed height. τ-scheduling (already
adopted) is therefore not a nicety; it is the along-track fix.

## 4. Dispositions

| Item | Verdict | Notes |
|---|---|---|
| V1 ribbon-horizon servo + teach calibration | **ADOPTED, gated on R1** | The 1/d-growing sensitivity and border-exit sign-certainty arguments are accepted. Availability in the last 2 m decides primary-loop vs opportunistic-measurement (your ≥60% bar). |
| V2 exit-schedule / wrong-side monitor | **ADOPTED — next perception task** after the tracker beds in | It is the item that catches F2-class sign errors; will be validated on the F1/F2 recordings per your flag-timing criterion (≥0.8 s before the plane, zero false flags on the pass). |
| V3 top-bar vertical hygiene | **ADOPTED into tracker validation** | Overlap-band vertical RMS ≤0.05 m criterion taken as the tracker's z acceptance bar (measurement assigned — R2 extension). |
| V4 banner instrument (bottom-edge row + LK flow w) | **QUEUED behind R4/D6** | Banner height measurement assigned; note the banner is also the F2 suspect, so its geometry doubles as the D5-class check. |
| V5 leak gating | **KILLED** (see §2) | Balloon-correlation measurement kept as confirmation. |
| V6 crossing-bias by moments | **ADOPTED as the standing decision rule** | The mean-level fix already shipped (double-compensation removal); any further bias only if \|mean\|>std on the new continuous-fix distribution (assigned). |
| §4 D5 one-multiplication disambiguation | **ADOPTED** (analyst harness) | |
| §4 P1–P3 retarget below 1.5 m | **ADOPTED** (replaces the original P1–P3 assignment) | |

## 5. Answers to data requests

- **R1** (ribbon availability, last 2 m, split by row vs compensated
  horizon): assigned to the analyst on the full recordings.
- **R2** (vertical residuals to 1.4 m): first numbers in §3 above;
  per-fix z residual study in the 1.5–3 m overlap band assigned
  together with V3's acceptance bar.
- **R3** (miss frame burst + attitude): EXISTS in the repo —
  fixtures/20260716T212744-phase5-closerange-frames, slices
  `..._range3m_to_collision` (F1) and `..._close_to_collision` (F2)
  with full flight logs (attitude derivable). Your V1 sign check
  ("near ribbon diving out the bottom while state says LOW") is
  runnable on it today.
- **R4** (banner geometry): assigned (one-time, far frame with fix).
- **R5** (clip bar identity): NO — collision events carry only
  {gate|environment, threat_level, impulse}. So clips are unsigned
  vertical truth; the sign check is clip-side vs believed-side only.

## 6. Question for your next turn

Given §3's finding that ALONG-TRACK is the runaway axis under blind
coast (range error 1.8–4.2 m per 0.6–1.0 s at harness conditions):
critique and refine the τ ladder for the commit trigger specifically —
what is the most robust τ estimator when the dominant visible feature
transitions ring→top-bar→banner across 3→1 m (scale-rate source
switching), and what should the commit scheduler do during the ~0.3 s
where none of them is trackable? Rank options with offline kill tests
on the two committed close-range recordings.
