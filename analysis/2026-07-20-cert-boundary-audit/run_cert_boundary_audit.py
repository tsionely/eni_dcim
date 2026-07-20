"""P4 — Certificate-boundary audit vs pinned cohort-4 semantics.

Pinned (RESPONSE22):
  ≥1.6m  — new side-pair certificate may be PROMOTED
  1.4–1.6m — established certificate may be MAINTAINED, not newly promoted
  <1.4m  — continuity maintenance only; no new identity/epoch
  Never inherit cert across gate-lock epoch / successor merely because
  side geometry looks plausible.

Read-only audit of certificate.py + close_tracker.py + pipeline wiring.
Deliverable: PROVEN-EQUIVALENT with line refs, OR precise patch spec.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

# Line refs are for origin/main @ 2aa8b9c (verify after pull).
AUDIT = {
    "head_cited": "2aa8b9c",
    "pinned_semantics": {
        "promote_new_min_m": 1.6,
        "maintain_band_m": [1.4, 1.6],
        "continuity_only_below_m": 1.4,
        "no_inherit_across_gate_lock_epoch": True,
        "no_inherit_across_successor_on_geometry_alone": True,
    },
    "implementation": {
        "certificate_py": "src/aigp/perception/certificate.py",
        "close_tracker_py": "src/aigp/perception/close_tracker.py",
        "pipeline_py": "src/aigp/perception/pipeline.py",
        "tests": "tests/unit/test_certificate.py",
    },
    "findings": [
        {
            "id": "F1_promote_floor_is_1p4_not_1p6",
            "severity": "NOT_EQUIVALENT",
            "detail": (
                "SidePairCertificate.terminal_floor_m defaults to 1.4 "
                "(certificate.py ctor ~L39–47). Promotion from PROBATION→"
                "CERTIFIED requires z_prior_m > terminal_floor (L85–87). "
                "There is NO 1.6m promotion floor: a broken chain can be "
                "re-promoted to CERTIFIED anywhere in (1.4, ∞), including "
                "the maintain-only band (1.4, 1.6]."
            ),
            "lines": [
                "src/aigp/perception/certificate.py:39-47",
                "src/aigp/perception/certificate.py:85-87",
            ],
            "pinned_requires": "new promotion only at range >= 1.6m",
        },
        {
            "id": "F2_on_full_quad_bypasses_range_floors",
            "severity": "NOT_EQUIVALENT",
            "detail": (
                "on_full_quad() sets _status=CERTIFIED unconditionally "
                "(L54–58) with no range argument. Pipeline calls it on "
                "prediction-consistent full quads (pipeline.py ~L66–74) "
                "at ANY range — including <1.4m and 1.4–1.6m. That is a "
                "NEW certification / re-anchor path, not maintain-only."
            ),
            "lines": [
                "src/aigp/perception/certificate.py:54-58",
                "src/aigp/perception/pipeline.py:66-74",
            ],
            "pinned_requires": (
                "full-quad anchor/promotion also respects >=1.6 for NEW "
                "identity; below 1.6 only maintain an already-held cert"
            ),
        },
        {
            "id": "F3_on_relock_or_collision_never_wired",
            "severity": "NOT_EQUIVALENT",
            "detail": (
                "on_relock_or_collision() clears the certificate (L60–64) "
                "and is unit-tested, but Grep shows ZERO production "
                "callers outside tests/unit/test_certificate.py. "
                "Gate-lock epoch changes and successor transitions in "
                "state_estimator / planner do NOT clear the cert. A "
                "plausible side-pair update() can therefore MAINTAIN or "
                "even re-enter PROBATION/CERTIFIED across a target change "
                "— exactly the inheritance failure the pin forbids."
            ),
            "lines": [
                "src/aigp/perception/certificate.py:60-64",
                "tests/unit/test_certificate.py:97",
            ],
            "pinned_requires": (
                "certificate must never be inherited across gate-lock "
                "epoch or successor transition"
            ),
        },
        {
            "id": "F4_geometry_alone_reopens_probation_below_1p4",
            "severity": "PARTIAL",
            "detail": (
                "update() when chain is broken but scale/barness/support "
                "look right sets PROBATION (L90–94) at ANY z_prior, "
                "including <1.4m. Promotion to CERTIFIED is blocked below "
                "1.4 (F1), but a NEW probationary identity can still be "
                "opened from NONE by geometry alone after a chain gap — "
                "weaker than 'continuity-only / no new identity/epoch'."
            ),
            "lines": [
                "src/aigp/perception/certificate.py:90-94",
                "src/aigp/perception/certificate.py:80-87",
            ],
            "pinned_requires": (
                "below 1.4m: maintain under continuity gates only; "
                "no new identity/epoch"
            ),
        },
        {
            "id": "F5_maintain_path_above_floor_ok",
            "severity": "ALIGNED",
            "detail": (
                "When already CERTIFIED and chain+invariants hold, status "
                "stays CERTIFIED without re-checking a 1.6 floor (L80–89 "
                "clean-streak branch only promotes from PROBATION). "
                "Maintenance of an established certificate is therefore "
                "allowed in 1.4–1.6 once held — matching the maintain "
                "half of the pin — but see F1/F2 for illegal NEW promotes."
            ),
            "lines": [
                "src/aigp/perception/certificate.py:80-89",
            ],
        },
        {
            "id": "F6_tracker_feeds_update_with_prior_z",
            "severity": "ALIGNED_WIRING",
            "detail": (
                "GateCloseTracker.track() calls certificate.update with "
                "z_prior_m=float(prior.t[2]) (close_tracker.py ~L201–205). "
                "Range gating therefore uses believed prior depth, which "
                "is the correct input IF the floors were 1.6/1.4 as pinned."
            ),
            "lines": [
                "src/aigp/perception/close_tracker.py:201-205",
            ],
        },
    ],
}


def patch_spec() -> str:
    return """# Patch spec — certificate boundary (NOT applied; analyst deliverable)

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
"""


def main() -> None:
    verdict = "NOT_EQUIVALENT"
    n_bad = sum(1 for f in AUDIT["findings"]
                if f["severity"] == "NOT_EQUIVALENT")
    summary = {
        "ask": "certificate-boundary audit (cohort-4 gate)",
        "verdict": verdict,
        "n_not_equivalent": n_bad,
        "n_aligned": sum(1 for f in AUDIT["findings"]
                         if f["severity"].startswith("ALIGNED")),
        "audit": AUDIT,
        "patch_spec_path": str(OUT / "patch_spec.md"),
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    (OUT / "patch_spec.md").write_text(patch_spec(), encoding="utf-8")

    lines = [
        "# Certificate-boundary audit",
        "",
        f"**Verdict: {verdict}** — implementation does **not** match the "
        "pinned promote≥1.6 / maintain-only 1.4–1.6 / continuity-only <1.4 "
        "semantics, and does not clear on gate-lock epoch changes.",
        "",
        "## Findings",
        "",
    ]
    for f in AUDIT["findings"]:
        lines += [
            f"### {f['id']} — {f['severity']}",
            "",
            f["detail"],
            "",
            "Lines: " + ", ".join(f"`{x}`" for x in f["lines"]),
            "",
        ]
    lines += [
        "## Patch spec",
        "",
        "See `patch_spec.md` (unified intent + test pins). Not applied "
        "under the analyst ground rule — cloud/engineering owns `src/`.",
        "",
        "## Deliverables",
        "",
        "- `summary.json`, `patch_spec.md`, this report",
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": verdict, "n_not_equivalent": n_bad},
                     indent=2))


if __name__ == "__main__":
    main()
