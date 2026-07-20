# Certificate-boundary audit

**Verdict: NOT_EQUIVALENT** — implementation does **not** match the pinned promote≥1.6 / maintain-only 1.4–1.6 / continuity-only <1.4 semantics, and does not clear on gate-lock epoch changes.

## Findings

### F1_promote_floor_is_1p4_not_1p6 — NOT_EQUIVALENT

SidePairCertificate.terminal_floor_m defaults to 1.4 (certificate.py ctor ~L39–47). Promotion from PROBATION→CERTIFIED requires z_prior_m > terminal_floor (L85–87). There is NO 1.6m promotion floor: a broken chain can be re-promoted to CERTIFIED anywhere in (1.4, ∞), including the maintain-only band (1.4, 1.6].

Lines: `src/aigp/perception/certificate.py:39-47`, `src/aigp/perception/certificate.py:85-87`

### F2_on_full_quad_bypasses_range_floors — NOT_EQUIVALENT

on_full_quad() sets _status=CERTIFIED unconditionally (L54–58) with no range argument. Pipeline calls it on prediction-consistent full quads (pipeline.py ~L66–74) at ANY range — including <1.4m and 1.4–1.6m. That is a NEW certification / re-anchor path, not maintain-only.

Lines: `src/aigp/perception/certificate.py:54-58`, `src/aigp/perception/pipeline.py:66-74`

### F3_on_relock_or_collision_never_wired — NOT_EQUIVALENT

on_relock_or_collision() clears the certificate (L60–64) and is unit-tested, but Grep shows ZERO production callers outside tests/unit/test_certificate.py. Gate-lock epoch changes and successor transitions in state_estimator / planner do NOT clear the cert. A plausible side-pair update() can therefore MAINTAIN or even re-enter PROBATION/CERTIFIED across a target change — exactly the inheritance failure the pin forbids.

Lines: `src/aigp/perception/certificate.py:60-64`, `tests/unit/test_certificate.py:97`

### F4_geometry_alone_reopens_probation_below_1p4 — PARTIAL

update() when chain is broken but scale/barness/support look right sets PROBATION (L90–94) at ANY z_prior, including <1.4m. Promotion to CERTIFIED is blocked below 1.4 (F1), but a NEW probationary identity can still be opened from NONE by geometry alone after a chain gap — weaker than 'continuity-only / no new identity/epoch'.

Lines: `src/aigp/perception/certificate.py:90-94`, `src/aigp/perception/certificate.py:80-87`

### F5_maintain_path_above_floor_ok — ALIGNED

When already CERTIFIED and chain+invariants hold, status stays CERTIFIED without re-checking a 1.6 floor (L80–89 clean-streak branch only promotes from PROBATION). Maintenance of an established certificate is therefore allowed in 1.4–1.6 once held — matching the maintain half of the pin — but see F1/F2 for illegal NEW promotes.

Lines: `src/aigp/perception/certificate.py:80-89`

### F6_tracker_feeds_update_with_prior_z — ALIGNED_WIRING

GateCloseTracker.track() calls certificate.update with z_prior_m=float(prior.t[2]) (close_tracker.py ~L201–205). Range gating therefore uses believed prior depth, which is the correct input IF the floors were 1.6/1.4 as pinned.

Lines: `src/aigp/perception/close_tracker.py:201-205`

## Patch spec

See `patch_spec.md` (unified intent + test pins). Not applied under the analyst ground rule — cloud/engineering owns `src/`.

## Deliverables

- `summary.json`, `patch_spec.md`, this report
