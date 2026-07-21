# Repaired-Criterion Round D-H Disposition

- generated_at_utc: `20260721T043448Z`
- generator_commit: `72dc0029a2cc306cd6dde1bc30abb7cdd0dd5d10`
- requested_minimum_tip: `4056acb` (ancestor of HEAD: `True`)
- active_criterion_commit: `9a85c7365994e87941636ccd567a87f42c417a21`
- legacy_response_model_registration_commit: `9a85c7365994e87941636ccd567a87f42c417a21`
- REG-2 numeric block complete: `False`
- sim_lock_at_start: `False`
- FlightSim/DCGame at start: `none observed`

## Decision

**NO_GO_PENDING_REG2.** The current criterion materially supersedes the older `4056acb` wording. It requires `setpoint.v_body[2]` to be transformed to world-up and passed through a numerically complete, pre-registered Contract B closed-loop response model before any intervention residual or verdict field can be emitted. The registration file is still REG-1 with `PENDING_CALIBRATION` values, so running the judge now would create inadmissible output.

Typed consequence: missing/unsupported Contract B input is reported as `INVALID_INPUT` / `OFF_SUPPORT`; it is never zero-filled, and failed gates emit no admissible residual field.

## D-H Disposition

| Task | Status | Admissible residual? | Disposition |
| --- | --- | --- | --- |
| D | `RECORDED_NO_NUMERIC_JUDGE` | `NO` | disposition only; no stale generator rerun under pre-REG2 state |
| E | `BLOCKED_FOR_ADJUDICATIVE_BOARD_NUMBER` | `NO` | previous diagnostic cross-tab remains descriptive; adjudicative B/A/D/Q waits for REG-2-capable generator |
| F | `NO_GO_PENDING_REG2` | `NO` | intervention judge not run; legacy_response_model_registration numeric block is still pending calibration |
| G | `NO_GO_PENDING_REG2` | `NO` | no decomposition verdict generated from inadmissible residuals |
| H | `THIS_ARTIFACT_TO_BE_MANIFESTED` | `NO` | add this D-H no-go disposition to manifest and verify after commit |

## Required Next Valid Step

Produce and commit REG-2 for `docs/criteria/legacy_response_model_registration.md`: fill `g`, `tau`, `L`, calibration artifact path/SHA-256, interval keys, residual RMS, and profile box from the disjoint A091 calibration interval. Only a generator commit descending from that REG-2 commit can run F/G adjudicatively.
