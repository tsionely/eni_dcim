# Valid-Stream Intervention NO-GO

Scope: DIAGNOSTIC, replay/CSV only; no FlightSim/DCGame launch.

Repo HEAD: `3d0f3770b42cad60f559cdbf2008fbf229a814b1`.
Criterion commit: `9a85c7365994e87941636ccd567a87f42c417a21`.
Required minimum tip: `4d4827c`.
Response-model registration: `docs/criteria/legacy_response_model_registration.md` at `9a85c7365994e87941636ccd567a87f42c417a21`.

## Decision

`NO_GO_PENDING_REG2`: the Contract-B first-order response model is still numerically incomplete.
The registration file still contains pending numeric fields, so the generator stops before any intervention residual or verdict field is emitted.

Typed result: `INVALID_INPUT`, residual `INADMISSIBLE`, no `post_intervention_residual_field`.

## Generator Fix

- The active valid-stream generator now hard-gates REG-2 before residual fields.
- Missing/unsupported input stays typed as invalid/off-support, never a synthetic zero.
- TERM-owned support remains a structural no-op for mechanism-2 correction.

## Required Next Valid Step

Commit REG-2 in `docs/criteria/legacy_response_model_registration.md` with `g`, `tau`, `L`, calibration artifact path/SHA-256, interval keys, RMS, and profile box. Then rerun this generator from a descendant commit.

