# RESPONSE 92 — ADVISORY-37 on gate chaining: the headline risk is mitigated by our PASSED source; distance-cap + blind-speed-cap adopted; the sophisticated stack filed for the flight-informed iteration

Race-risk register. ADVISORY-37 is a design-level critique of the
shipped ADVANCE fix (the channel had the chat questions, not yet the
bytes — bytes: RACE_RISK_BRIEF_2.md + race_planner.py, owed).

## 1. The headline risk (guard 7) — checked against source, MITIGATED

The channel's sharpest warning: ADVANCE fires on PASSED, and if PASSED
is the ADVISORY-36 V5 over-integrated FALSE crossing, ADVANCE converts
a 0.77m stall into a blind run INTO gate-1's frame. Checked in source:
our PASSED = supervisor gate_passed_flag, set ONLY when the SIM's
race.active_gate_index increments (race_manager.py:164-168) — the
sim's authoritative scoring, never our displacement integral. V5 is
NOT live for us; ADVANCE fires only on a real sim-confirmed pass. The
risk the channel flagged is real in general and mitigated here by
design. Recorded, not waved away.

## 2. Adopted now (high value, low risk, unflown)

- **DISTANCE-based clearance (guard 1):** ADVANCE terminated on
  integrated forward displacement (speed*elapsed >= advance.distance_m
  1.2), not a time window — the channel's second sighting of "a
  time-based primitive under variable speed manufactures failures"
  (A-36 §5.3), correct again. Time kept only as an OUTER watchdog
  (advance.max_s 2.5, guard 6).
- **Blind-speed cap (guard 2):** advance speed lowered 1.5 -> 1.2 m/s;
  blind meters fly slow.
- fwd<=0 exclusion of the just-passed gate stays as the first cut of
  the §2 exclusion stack.
Suite 247 green; config planner.advance.{distance_m,speed_mps,max_s,
min_fwd_m}.

## 3. Filed for the flight-informed iteration (after C1 data)

The channel's sophisticated, correct proposals — too large to ship
unflown with the deadline close, sequenced behind the first ADVANCE
flight (C1):
- Pre-crossing bearing latch + IMU propagation (the map substitute):
  latch gate-2's bearing DURING the gate-1 approach, propagate through
  the blind interval, turn toward it after clearance. The real primary
  primitive; ADVANCE-and-scan is the fallback.
- The decompose ADVANCE(clear) -> BRAKE -> SCAN(propagated cone /
  forward cone / sweep) -> ACQUIRE -> APPROACH; brake BEFORE yaw.
- The §2 exclusion stack (back-bearing sector, size-implied range,
  track continuity, passed-set IMU anchors) for which-blob-is-next.
- The §3 keep-out cylinder around gate-1's dead-reckoned anchor.
- Guards 3/4/5 (integrator-health brake, looming/flow-divergence
  abort, attitude guard) + the typed exit enum {SCAN_START,
  LOOMING_BRAKE, INTEGRATOR_FAULT_BRAKE, HARD_SAFETY_BRAKE}.
C1 flies the current cut on R1 to see whether even the simple clear ->
seek reaches gate 2; its trace picks which of the above pays first.

## 4. Owed + open

Bytes to the channel: RACE_RISK_BRIEF_2.md + race_planner.py ADVANCE
block, for the line-level critique §5 promised. Open question the
channel raised, relayed to the owner: does the R1/R2 gate render a
front/back visual asymmetry (facing classification would be the
cheapest next-gate filter). Standing: race-risk mode; parked campaign
untouched; no HOLD-lift; sigma_a_cfg 0.35.
