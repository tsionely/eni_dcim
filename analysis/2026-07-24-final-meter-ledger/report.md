# Final-meter ledger — 2026-07-24

## Provenance and scope

This analysis implements the user-requested +1.0 m-aligned control-tick
ledger and the extraction list in `C:/Users/tsion/Downloads/ADVISORY_36.md`
§4.  The literal memo titled **“RACE-RISK ADVISORY 1”**, including the
requested A–D labels, was not present on disk; A–D are therefore applied
from the user task, not attributed to a nonexistent local document.

Every ledger is sampled at setpoint ticks, using a state or detection
forward-fill only when it is no older than 20 ms.  Plane distance uses a
unit-ish PnP normal when available, reoriented so camera-forward is positive
(the recorded normals point camera-ward); otherwise it uses `t[2]`.
`true_world_dz` reproduces the crossing-autopsy quaternion/rest-tilt
calculation.  Lateral and vertical margins use the documented 0.8 m
half-opening proxy.

## Verdicts

| Fixture / approach | Class | Deciding values |
| --- | --- | --- |
| `stall_t2r1_B_run2` / 1 | A, proxy / inconclusive | `s_min=+0.488 m`; closest lateral `+0.086 m`, true-world dz `+0.469 m` (margins `+0.714`, `+0.331 m`). No eligible rho ticks because the along-plane command was not positive above 0.3 m/s. It remained in `commit`, did not record a withdrawal, and no logged exit enum exists. This cannot discriminate the requested A/B/C mechanisms; the required forced non-pass label is retained explicitly as a proxy. |
| `pass_r1k_off_run3` / 1 | **D scoring-order** | Race counter incremented at `510888613945600 ns`, after the ledger had entered `retreat`; the last ledger plane value before it was `+0.730 m` (>0.2 m). Closest margins were lateral `+0.698 m`, vertical `+0.186 m`; one rho sample was `-7.985` and command withdrew. This is not a geometrically verified PASS under the stated rule (`s <= 0` at counter increment). |
| `pass_r1k_off_run3` / 2 | A command-withdrawal | `rho=1.417` mean (`0.200` below 0.5), command withdrew before closest, and phase entered `retreat`; `s_min=+0.665 m`. Closest margins: lateral `+0.307 m`, vertical `-0.293 m`. |
| `pass_r1k_off_run3` / 3 | A command-withdrawal | Phase entered `recover` at `s_min=+0.633 m`; command at closest was `0.000 m/s`. Rho is unobservable (zero eligible ticks). Closest margins: lateral `+0.125 m`, vertical `+0.639 m`. |
| `pass_r1k_off_run3` / 4 | A, proxy / inconclusive | `s_min=+0.431 m`, no eligible rho ticks, no withdrawal, final phase `commit`, and no logged exit enum. Closest margins: lateral `-0.194 m`, vertical `-0.180 m`. |
| `stall_r1j3390_val_run2` / 1 | A, proxy / runner-up B | Final `recover` and withdrawal occurred at `s_min=+0.650 m`; mean `rho=0.036`, median `0.120`, and all five eligible ticks were below 0.5. The B condition is not asserted because ≥0.8 m/s command did not persist through most of the full interval. Closest margins: lateral `+0.457 m`, vertical `-0.167 m`. |

The `r1j3390` exit census is one aligned approach: `RECOVER=1`.  There were
no additional contiguous segments satisfying the near/approach definition
that crossed downward through +1.0 m.

## Discriminating observations

The pass-named fixture does contain the observed gate count increment, but it
does **not** satisfy the requested geometric PASS criterion.  Its recorded
state transitions to retreat at a still-positive plane estimate; the race
counter follows while the most recent ledger sample is +0.730 m in front of
the plane.  That makes scoring-order / state-order the cleanest classification
for its first approach, not a proof that the raw estimated plane coordinate is
accurate.

The two mechanism-rich stalls closest to a useful tracking measurement are
not alike.  `r1j3390` has a very low measured-vs-commanded along-plane ratio
(`rho=0.036`), but loses the sustained ≥0.8 m/s command condition needed to
call B without qualification.  The T2R1 stall lacks a valid positive-command
rho interval altogether, so the log cannot establish plant non-tracking.

## UNLOGGED instrumentation backlog

1. Per-tick commit-predicate vector and sustain counter — the primary
   ADVISORY_36 discriminator for a flickering predicate.
2. Active speed cap and the rule/band that bound it.
3. Planner exit-cause enum, including commit-window expiry and corridor/min-
   distance causes.
4. Explicit approach-axis / plane-normal convention.
5. Opening dimensions and active aim-up target.  Current offsets and margins
   are proxies, not a logged collision-aperture clearance.

The generated `summary.json`, tick ledgers, and paired traces retain these as
literal `UNLOGGED` fields rather than fabricating them from unrecorded planner
state.
