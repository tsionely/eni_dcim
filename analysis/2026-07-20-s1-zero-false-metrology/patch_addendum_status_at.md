# Patch addendum — certificate `status_at` vs `_status` (from S1)

Found during S1 replay on successor fictions (201630/202445): two events
where `status_at(ts)` returned `none` (chain age > gap) while `_status`
remained `certified`. `on_full_quad` then took the MAINTAIN branch and
re-anchored below `promote_floor` (1.6m) on a scale-fiction quad.

**Metrology impact:** none — scale gate still refused every fiction
(`false_metric_accepts=0`). S1 gate PASSES.

**Recommended one-liner (cloud):** at the top of `on_full_quad`, if
`status_at(ts_ns) == NONE`, treat as fresh identity (apply promote_floor
gate) even when `_status` is still CERTIFIED/PROBATION — or sync
`_status = NONE` whenever `status_at` would return NONE.

Not applied under analyst ground rules.
