# Patch spec — certificate boundary (NOT applied; analyst deliverable)

## Goal
Make SidePairCertificate + PerceptionAgent wiring PROVEN-EQUIVALENT to:
- NEW promote / NEW full-quad anchor only at z >= 1.6m
- 1.4 <= z < 1.6: MAINTAIN established CERTIFIED/PROBATION under
  continuity invariants; never elevate NONE→PROBATION→CERTIFIED as a
  fresh identity; never on_full_quad into CERTIFIED if previously NONE
- z < 1.4: continuity maintain only (chain_ok + invariants); no new
  identity/epoch (block NONE→PROBATION and PROBATION→CERTIFIED; block
  on_full_quad unless already CERTIFIED/PROBATION for this epoch)
- Clear certificate on every gate-lock epoch change and successor
  transition (wire on_relock_or_collision)

## Diff sketch (src/)

### 1) certificate.py — dual floors + epoch-aware API

```python
# ctor
promote_floor_m: float = 1.6   # NEW promotion / NEW full-quad anchor
terminal_floor_m: float = 1.4  # below: continuity-only

def on_full_quad(self, ts_ns: int, z_m: float | None = None) -> None:
    # NEW anchor only at/above promote_floor.
    # If already CERTIFIED/PROBATION in-epoch and z in maintain band,
    # refresh timestamp only (maintain).
    if self._status == NONE:
        if z_m is None or z_m < self.promote_floor:
            return  # refuse fresh certification
        self._status = CERTIFIED
    elif z_m is not None and z_m < self.terminal_floor:
        # continuity refresh only if already held
        pass
    else:
        self._status = CERTIFIED  # maintain/re-anchor held identity
    self._last_ok_ns = ts_ns
    self._clean_streak = 0

def update(...):
    ...
    if chain_ok and all(others):
        self._last_ok_ns = ts_ns
        if self._status == PROBATION:
            self._clean_streak += 1
            if (self._clean_streak >= self.promote_after
                    and z_prior_m >= self.promote_floor):  # was >1.4
                self._status = CERTIFIED
        elif self._status == NONE:
            # Do NOT open PROBATION from geometry alone below promote_floor
            if z_prior_m >= self.promote_floor:
                self._status = PROBATION
                self._clean_streak = 0
            # else: stay NONE (continuity-only refuses new identity)
    elif all(others):
        # broken chain
        if self._status == NONE and z_prior_m < self.promote_floor:
            return NONE  # refuse geometry-only rebirth
        self._last_ok_ns = ts_ns
        self._status = PROBATION
        self._clean_streak = 0
```

### 2) pipeline.py — pass range into on_full_quad; clear on lock change

```python
r_fix = float(np.linalg.norm(detection.rel_pose.t))
if prior is None or abs(r_fix - prior) <= 0.4 * prior:
    self.tracker.certificate.on_full_quad(detection.ts_ns, z_m=r_fix)
```

Wire estimator/planner events:
- On gate lock clear / relock accept / collision / gate_passed successor:
  `perception.tracker.certificate.on_relock_or_collision()`
  (bus signal or direct call from the owner of the lock epoch)

### 3) tests/unit/test_certificate.py — pin the floors

- Promote PROBATION→CERTIFIED at z=1.5 after streak → stays PROBATION
- Promote at z=1.7 after streak → CERTIFIED
- on_full_quad from NONE at z=1.5 → stays NONE
- on_full_quad from NONE at z=1.7 → CERTIFIED
- on_relock clears; subsequent geometry at 2.0 without full quad →
  at most PROBATION only after promote_floor path, never silent inherit
- Below 1.4: CERTIFIED+chain maintains; NONE stays NONE on perfect pair

## Acceptance
Unit suite green; cohort-4 gate row "certificate-boundary audit" →
PROVEN-EQUIVALENT with updated line refs.
