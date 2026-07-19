# GATE_GEOM — audited geometry constants (single owner)

Every geometric constant the planner/terminal channel consumes lives
here with its provenance. Numbers without a fixture citation do not
get consumed — that is the lesson this file exists to enforce.

## Gate-1 opening (R2-TRAINING)

| Constant | Value | Provenance |
|---|---|---|
| Opening center height above pad camera | **1.35 m** | Independent audit 0bf8fcd: pad rest-like cohort n=8867, median 1.350, p10–p90 1.23–1.37 (analysis/2026-07-19-true-vertical-audit) |
| Pin (unit + live) | 1.372 / 1.374 m | rel_pose t=[0.015,−3.217,5.525], q=I, level_pitch=−0.311; first detection of 20260717T153903 |
| Opening half-size | 0.8 m | 1.6 m outer-square PnP model (perception.gate) |
| Side-bar width w_bar | 0.188 m | Cursor A4 correction (099dc07); the 0.81 figure was bloom |
| Distance from pad | ~6.1–6.4 m | slant R of pad detections across phase6a/6b fixtures |
| Pad↔gate-1 alignment | naturally aligned | ballistic-pass forensics (20260716T131137) + dash-F2 lateral-centered arrival |

The historical "3.11 m" opening height was the tilted-frame phantom
(rest-zeroed attitude, sin 17.8°·R mixing) — see
docs/thinktank/ROUND5_BRIEF.md. Any analysis reproducing it is
composing the level reference incorrectly.

## Gate 2+ — UNKNOWN

The post-close far-lock cohort (n=608) is attitude-contaminated
(median −1.48 m, std 3.9) and is NOT a measurement. Do not consume.
Minimum inter-gate spacing: 5.71 m (Cursor, advisory-4 pack).

## Open keystones feeding this file

- **A6** (banner reference / solidity): BLOCKED on vision coverage —
  committed slices are pad/takeoff windows with no far-range frames
  (69 visions attempted). Needs a dedicated far-range recording from
  the operator (rider queued in AGENTS.md). Until it lands: no aim
  re-base, R4's +0.147 m stays un-reverified.
- **A8** (drone vertical half-extent): sets the effective aperture
  margin and the re-derived abort threshold.

## F2 abort mechanism — the precise record (phase6b)

The corridor abort that killed the WOULD_HAVE_CLEARED approach
(20260719T075333, retreat t=7.883 s, R=1.31 m) fired on
**body-frame vertical + aim-up stacking**: old code measured
d_body[2] − aim_up = −0.46 − 0.25 → corridor offset 0.72 > 0.45 for
4+ ticks. Under true_world_dz the same state reads 0.12 − 0.25 →
offset 0.16 — no abort. (Raw dz alone never crossed the threshold —
the stacking with the aim point did; recorded here because RESPONSE9's
"+0.58 phantom" shorthand compressed this.)
